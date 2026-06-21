"""Sensor platform for Smart Irrigation V2."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ACTIVATION_MODE,
    CONF_HUMIDITY_SENSOR,
    CONF_HUMIDITY_THRESHOLD,
    CONF_IRRIGATION_DURATION,
    CONF_PUMPS,
    CONF_PUMP_FLOW_RATE,
    CONF_PUMP_SWITCH,
    CONF_SCHEDULE_DAYS,
    CONF_SCHEDULE_TIME,
    CONF_ZONE_ACTIVE,
    DEFAULT_HUMIDITY_THRESHOLD,
    DEFAULT_IRRIGATION_DURATION,
    DOMAIN,
    MODE_HUMIDITY,
    MODE_MANUAL,
    MODE_SCHEDULE,
    SENSOR_NEXT_IRRIGATION,
    SENSOR_WATER_VOLUME,
)

_DAY_MAP = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

_DAY_LABELS = {
    "mon": "Lundi", "tue": "Mardi", "wed": "Mercredi",
    "thu": "Jeudi", "fri": "Vendredi", "sat": "Samedi", "sun": "Dimanche",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    pumps = list(entry.options.get(CONF_PUMPS) or entry.data.get(CONF_PUMPS, []))
    async_add_entities([
        WaterVolumeSensor(entry, pumps),
        IrrigationScheduleSensor(entry),
    ])


class WaterVolumeSensor(SensorEntity):
    """Represents a water volume sensor for the irrigation zone."""

    def __init__(self, entry: ConfigEntry, pumps: list[dict]) -> None:
        self._entry = entry
        self._pumps = pumps
        self._attr_name = f"{entry.title} Water Volume"
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_WATER_VOLUME}"
        self._attr_native_value = 0.0
        self._attr_native_unit_of_measurement = "cL"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:water"
        self._last_update: datetime = datetime.now()

    async def async_added_to_hass(self) -> None:
        stored = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {})
        self._attr_native_value = stored.get("total_volume", 0.0)
        self._last_update = datetime.now()

    @property
    def state(self) -> float:
        return self._attr_native_value

    async def async_update(self) -> None:
        now = datetime.now()
        elapsed_seconds = (now - self._last_update).total_seconds()
        self._last_update = now

        for pump in self._pumps:
            switch_id = pump.get(CONF_PUMP_SWITCH)
            flow_rate = pump.get(CONF_PUMP_FLOW_RATE, 0)
            if switch_id:
                state = self.hass.states.get(switch_id)
                if state and state.state == "on":
                    self._attr_native_value += flow_rate / 60.0 * elapsed_seconds

        domain_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id)
        if domain_data is not None:
            domain_data["total_volume"] = self._attr_native_value


class IrrigationScheduleSensor(SensorEntity):
    """Shows next irrigation datetime and exposes schedule/humidity config as attributes."""

    _attr_icon = "mdi:calendar-clock"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_name = f"{entry.title} Next Irrigation"
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_NEXT_IRRIGATION}"

    def _conf(self, key: str, default):
        return self._entry.options.get(key) or self._entry.data.get(key, default)

    @property
    def native_value(self) -> datetime | None:
        if self._conf(CONF_ACTIVATION_MODE, MODE_MANUAL) != MODE_SCHEDULE:
            return None
        schedule_time = self._conf(CONF_SCHEDULE_TIME, "08:00:00")
        schedule_days = list(self._conf(CONF_SCHEDULE_DAYS, []) or [])
        return _next_irrigation_dt(schedule_time, schedule_days)

    @property
    def extra_state_attributes(self) -> dict:
        mode = self._conf(CONF_ACTIVATION_MODE, MODE_MANUAL)
        pumps = list(self._conf(CONF_PUMPS, []) or [])

        try:
            entry_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {})
            irrigating = entry_data.get("irrigating", False)
        except Exception:
            irrigating = False

        days = list(self._conf(CONF_SCHEDULE_DAYS, []) or [])
        switches = [p.get(CONF_PUMP_SWITCH) for p in pumps if p.get(CONF_PUMP_SWITCH)]
        total = sum(p.get(CONF_PUMP_FLOW_RATE, 0) for p in pumps)
        pump_states = [self.hass.states.get(sw) for sw in switches]
        pumps_available = (
            all(s is not None and s.state != "unavailable" for s in pump_states)
            if switches else None
        )

        return {
            "activation_mode":     mode,
            "entry_id":            self._entry.entry_id,
            "schedule_time":       self._conf(CONF_SCHEDULE_TIME, None),
            "schedule_days":       [_DAY_LABELS.get(d, d) for d in days],
            "schedule_days_raw":   days,
            "humidity_sensor":     self._conf(CONF_HUMIDITY_SENSOR, None),
            "humidity_threshold":  self._conf(CONF_HUMIDITY_THRESHOLD, DEFAULT_HUMIDITY_THRESHOLD),
            "irrigation_duration": self._conf(CONF_IRRIGATION_DURATION, DEFAULT_IRRIGATION_DURATION),
            "irrigating":          irrigating,
            "pump_switches":       switches,
            "total_flow_rate":     float(total) if switches else None,
            "pumps_available":     pumps_available,
            "zone_active":         self._conf(CONF_ZONE_ACTIVE, True),
        }


def _next_irrigation_dt(schedule_time: str, schedule_days: list[str]) -> datetime | None:
    """Return the next irrigation datetime (timezone-aware) or None."""
    if not schedule_days:
        return None
    try:
        parts = schedule_time.split(":")
        hour, minute = int(parts[0]), int(parts[1])
    except (ValueError, IndexError, AttributeError):
        return None

    day_numbers = {_DAY_MAP[d] for d in schedule_days if d in _DAY_MAP}
    if not day_numbers:
        return None

    now = dt_util.now()
    for delta in range(8):
        candidate = now + timedelta(days=delta)
        if candidate.weekday() not in day_numbers:
            continue
        candidate_dt = candidate.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate_dt > now:
            return candidate_dt

    return None
