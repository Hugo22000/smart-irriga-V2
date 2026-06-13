"""The Smart Irrigation V2 integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_change,
)

from .const import (
    CONF_HUMIDITY_SENSOR,
    CONF_HUMIDITY_THRESHOLD,
    CONF_IRRIGATION_DURATION,
    CONF_PUMPS,
    CONF_PUMP_FLOW_RATE,
    CONF_PUMP_SWITCH,
    CONF_ACTIVATION_MODE,
    CONF_SCHEDULE_DAYS,
    CONF_SCHEDULE_TIME,
    DEFAULT_HUMIDITY_THRESHOLD,
    DEFAULT_IRRIGATION_DURATION,
    DOMAIN,
    MODE_HUMIDITY,
    MODE_MANUAL,
    MODE_SCHEDULE,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)
_DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


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

    mode = _conf(entry, CONF_ACTIVATION_MODE, MODE_MANUAL)
    if mode == MODE_SCHEDULE:
        _setup_schedule(hass, entry)
    elif mode == MODE_HUMIDITY:
        _setup_humidity(hass, entry)

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN].pop(entry.entry_id)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


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
        _LOGGER.debug("Irrigation stopped for %s", entry.title)

    @callback
    def _stop_callback(now) -> None:
        hass.async_create_task(_stop_pumps())

    async_call_later(hass, duration, _stop_callback)
    _LOGGER.debug("Irrigation started for %s (%ss)", entry.title, duration)


def _setup_schedule(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register a daily time-based listener to start irrigation."""
    schedule_time = _conf(entry, CONF_SCHEDULE_TIME, "08:00:00")
    schedule_days = list(_conf(entry, CONF_SCHEDULE_DAYS, []) or [])

    try:
        parts = str(schedule_time).split(":")
        hour, minute = int(parts[0]), int(parts[1])
    except (ValueError, IndexError, AttributeError):
        _LOGGER.error("Invalid schedule time: %s", schedule_time)
        return

    day_numbers = {_DAY_MAP[d] for d in schedule_days if d in _DAY_MAP}

    @callback
    def _on_time(now) -> None:
        if day_numbers and now.weekday() not in day_numbers:
            return
        hass.async_create_task(start_irrigation(hass, entry))

    cancel = async_track_time_change(hass, _on_time, hour=hour, minute=minute, second=0)
    entry.async_on_unload(cancel)
    _LOGGER.debug("Schedule listener registered at %02d:%02d for %s", hour, minute, entry.title)


def _setup_humidity(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register a state-change listener on the humidity sensor."""
    sensor_id = _conf(entry, CONF_HUMIDITY_SENSOR, None)
    threshold = float(_conf(entry, CONF_HUMIDITY_THRESHOLD, DEFAULT_HUMIDITY_THRESHOLD))

    if not sensor_id:
        _LOGGER.warning("Humidity mode enabled but no sensor configured for %s", entry.title)
        return

    @callback
    def _on_state_change(event) -> None:
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
