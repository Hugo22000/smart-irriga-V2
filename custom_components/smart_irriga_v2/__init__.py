"""The Smart Irrigation V2 integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_change,
)

from .const import (
    CONF_ACTIVATION_MODE,
    CONF_HUMIDITY_SENSOR,
    CONF_HUMIDITY_THRESHOLD,
    CONF_IRRIGATION_DURATION,
    CONF_NUM_PUMPS,
    CONF_PUMPS,
    CONF_PUMP_FLOW_RATE,
    CONF_PUMP_HUMIDITY_SENSOR,
    CONF_PUMP_SWITCH,
    CONF_SCHEDULE_DAYS,
    CONF_SCHEDULE_TIME,
    CONF_ZONE_ACTIVE,
    CONF_ZONE_NAME,
    DEFAULT_HUMIDITY_THRESHOLD,
    DEFAULT_IRRIGATION_DURATION,
    DOMAIN,
    MODE_HUMIDITY,
    MODE_MANUAL,
    MODE_SCHEDULE,
    PLATFORMS,
    SERVICE_SET_ZONE_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)
_DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

_SERVICE_SCHEMA = vol.Schema({
    vol.Required("entry_id"): cv.string,
    vol.Required(CONF_ACTIVATION_MODE): vol.In([MODE_MANUAL, MODE_SCHEDULE, MODE_HUMIDITY]),
    vol.Required(CONF_IRRIGATION_DURATION): vol.All(vol.Coerce(int), vol.Range(min=1, max=3600)),
    vol.Optional(CONF_ZONE_ACTIVE): cv.boolean,
    vol.Optional(CONF_SCHEDULE_TIME): cv.string,
    vol.Optional(CONF_SCHEDULE_DAYS): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_HUMIDITY_SENSOR): cv.string,
    vol.Optional(CONF_HUMIDITY_THRESHOLD): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
})


def _conf(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Return value from options first, then data, then default."""
    val = entry.options.get(key)
    if val is None:
        val = entry.data.get(key)
    return val if val is not None else default


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Smart Irrigation V2 from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"total_volume": 0.0, "irrigating": False}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Per-pump humidity sensors work regardless of zone mode
    _setup_per_pump_humidity(hass, entry)

    mode = _conf(entry, CONF_ACTIVATION_MODE, MODE_MANUAL)
    if mode == MODE_SCHEDULE:
        _setup_schedule(hass, entry)
    elif mode == MODE_HUMIDITY:
        _setup_humidity(hass, entry)

    # Register service once for the whole domain
    if not hass.services.has_service(DOMAIN, SERVICE_SET_ZONE_OPTIONS):
        async def _handle_set_zone_options(call: ServiceCall) -> None:
            target_entry = hass.config_entries.async_get_entry(call.data["entry_id"])
            if not target_entry or target_entry.domain != DOMAIN:
                raise HomeAssistantError(
                    f"Zone introuvable : entry_id={call.data['entry_id']}"
                )
            current = dict(target_entry.options or target_entry.data)
            for key in [
                CONF_ACTIVATION_MODE, CONF_SCHEDULE_TIME, CONF_SCHEDULE_DAYS,
                CONF_HUMIDITY_SENSOR, CONF_HUMIDITY_THRESHOLD, CONF_IRRIGATION_DURATION,
                CONF_ZONE_ACTIVE,
            ]:
                if key in call.data:
                    current[key] = call.data[key]
            hass.config_entries.async_update_entry(target_entry, options=current)
            _LOGGER.debug(
                "set_zone_options applied to %s: %s", target_entry.title, call.data
            )

        hass.services.async_register(
            DOMAIN, SERVICE_SET_ZONE_OPTIONS, _handle_set_zone_options, schema=_SERVICE_SCHEMA
        )

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN].pop(entry.entry_id)

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unloaded and not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_SET_ZONE_OPTIONS)

    return unloaded


async def start_irrigation(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Turn on all pumps and schedule auto-stop after the configured duration."""
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if entry_data is None:
        _LOGGER.warning("start_irrigation called but entry_data not found for %s", entry.title)
        return
    if entry_data.get("irrigating"):
        _LOGGER.debug("Irrigation already running for %s, skipping", entry.title)
        return

    entry_data["irrigating"] = True
    duration = int(_conf(entry, CONF_IRRIGATION_DURATION, DEFAULT_IRRIGATION_DURATION))
    pumps = list(entry.options.get(CONF_PUMPS) or entry.data.get(CONF_PUMPS, []))

    if not pumps:
        _LOGGER.warning("No pumps configured for zone %s", entry.title)
        entry_data["irrigating"] = False
        return

    for pump in pumps:
        switch_id = pump.get(CONF_PUMP_SWITCH)
        if switch_id:
            _LOGGER.debug("Turning on switch %s for zone %s", switch_id, entry.title)
            await hass.services.async_call(
                "switch", "turn_on", {"entity_id": switch_id}, blocking=True
            )
        else:
            _LOGGER.warning("Pump has no switch entity configured: %s", pump)
        entry_data["total_volume"] = (
            entry_data.get("total_volume", 0.0) + pump.get(CONF_PUMP_FLOW_RATE, 0)
        )

    async def _stop_pumps() -> None:
        for pump in pumps:
            switch_id = pump.get(CONF_PUMP_SWITCH)
            if switch_id:
                await hass.services.async_call(
                    "switch", "turn_off", {"entity_id": switch_id}, blocking=True
                )
        if entry_data is not None:
            entry_data["irrigating"] = False
            entry_data.pop("stop_cancel", None)
        _LOGGER.debug("Irrigation stopped for %s", entry.title)

    @callback
    def _stop_callback(now) -> None:
        hass.async_create_task(_stop_pumps())

    cancel = async_call_later(hass, duration, _stop_callback)
    entry_data["stop_cancel"] = cancel
    _LOGGER.debug("Irrigation started for %s (%ss)", entry.title, duration)


def _setup_schedule(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register a daily time-based listener to start irrigation."""
    schedule_time = _conf(entry, CONF_SCHEDULE_TIME, "08:00:00")

    try:
        parts = str(schedule_time).split(":")
        hour, minute = int(parts[0]), int(parts[1])
    except (ValueError, IndexError, AttributeError):
        _LOGGER.error("Invalid schedule time '%s' for zone %s", schedule_time, entry.title)
        return

    @callback
    def _on_time(now) -> None:
        if not _conf(entry, CONF_ZONE_ACTIVE, True):
            _LOGGER.debug("Schedule fired but zone %s is inactive, skipping", entry.title)
            return
        # Read days dynamically so card changes without reload are picked up
        current_days = list(_conf(entry, CONF_SCHEDULE_DAYS, []) or [])
        day_numbers = {_DAY_MAP[d] for d in current_days if d in _DAY_MAP}
        if day_numbers and now.weekday() not in day_numbers:
            _LOGGER.debug(
                "Schedule fired for %s but today (%s) not in configured days %s",
                entry.title, now.strftime("%A"), current_days,
            )
            return
        _LOGGER.info("Scheduled irrigation starting for zone %s at %s", entry.title, now.strftime("%H:%M"))
        hass.async_create_task(start_irrigation(hass, entry))

    cancel = async_track_time_change(hass, _on_time, hour=hour, minute=minute, second=0)
    entry.async_on_unload(cancel)
    _LOGGER.info(
        "Schedule listener registered at %02d:%02d for zone %s (days: %s)",
        hour, minute, entry.title, _conf(entry, CONF_SCHEDULE_DAYS, []),
    )


def _setup_humidity(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register a zone-level state-change listener on the humidity sensor."""
    sensor_id = _conf(entry, CONF_HUMIDITY_SENSOR, None)
    threshold = float(_conf(entry, CONF_HUMIDITY_THRESHOLD, DEFAULT_HUMIDITY_THRESHOLD))

    if not sensor_id:
        _LOGGER.warning("Humidity mode enabled but no sensor configured for %s", entry.title)
        return

    @callback
    def _on_state_change(event) -> None:
        if not _conf(entry, CONF_ZONE_ACTIVE, True):
            return
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in ("unavailable", "unknown", ""):
            return
        try:
            if float(new_state.state) < threshold:
                hass.async_create_task(start_irrigation(hass, entry))
        except (ValueError, TypeError):
            pass

    cancel = async_track_state_change_event(hass, [sensor_id], _on_state_change)
    entry.async_on_unload(cancel)
    _LOGGER.debug("Humidity listener registered on %s (threshold %s%%)", sensor_id, threshold)


def _setup_per_pump_humidity(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register independent humidity listeners for pumps that have a per-pump sensor."""
    pumps = list(entry.options.get(CONF_PUMPS) or entry.data.get(CONF_PUMPS, []))
    threshold = float(_conf(entry, CONF_HUMIDITY_THRESHOLD, DEFAULT_HUMIDITY_THRESHOLD))

    for pump in pumps:
        sensor_id = pump.get(CONF_PUMP_HUMIDITY_SENSOR)
        if not sensor_id:
            continue

        def _make_listener(bound_pump: dict):
            @callback
            def _on_pump_humidity_change(event) -> None:
                if not _conf(entry, CONF_ZONE_ACTIVE, True):
                    return
                new_state = event.data.get("new_state")
                if new_state is None or new_state.state in ("unavailable", "unknown", ""):
                    return
                try:
                    if float(new_state.state) < threshold:
                        hass.async_create_task(_start_single_pump(hass, entry, bound_pump))
                except (ValueError, TypeError):
                    pass
            return _on_pump_humidity_change

        cancel = async_track_state_change_event(hass, [sensor_id], _make_listener(pump))
        entry.async_on_unload(cancel)
        _LOGGER.debug(
            "Per-pump humidity listener on %s for switch %s (zone %s)",
            sensor_id, pump.get(CONF_PUMP_SWITCH), entry.title,
        )


async def _start_single_pump(hass: HomeAssistant, entry: ConfigEntry, pump: dict) -> None:
    """Turn on a single pump and schedule auto-stop after the configured duration."""
    switch_id = pump.get(CONF_PUMP_SWITCH)
    if not switch_id:
        return

    duration = int(_conf(entry, CONF_IRRIGATION_DURATION, DEFAULT_IRRIGATION_DURATION))

    _LOGGER.debug("Starting single pump %s for zone %s", switch_id, entry.title)
    await hass.services.async_call("switch", "turn_on", {"entity_id": switch_id}, blocking=True)

    async def _stop_pump() -> None:
        await hass.services.async_call("switch", "turn_off", {"entity_id": switch_id}, blocking=True)
        _LOGGER.debug("Single pump %s stopped for zone %s", switch_id, entry.title)

    @callback
    def _stop_callback(now) -> None:
        hass.async_create_task(_stop_pump())

    async_call_later(hass, duration, _stop_callback)
