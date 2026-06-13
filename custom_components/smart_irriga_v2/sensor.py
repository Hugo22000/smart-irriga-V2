"""Sensor platform for Smart Irrigation V2."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_PUMPS, CONF_PUMP_SWITCH, CONF_PUMP_FLOW_RATE, SENSOR_WATER_VOLUME


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    pumps = entry.data.get(CONF_PUMPS, [])
    async_add_entities([WaterVolumeSensor(entry, pumps)])


class WaterVolumeSensor(SensorEntity):
    """Represents a water volume sensor for the irrigation zone."""

    def __init__(self, entry: ConfigEntry, pumps: list[dict]) -> None:
        """Initialize the sensor."""
        self._entry = entry
        self._pumps = pumps
        self._attr_name = f"{entry.title} Water Volume"
        self._attr_unique_id = f"{entry.entry_id}_{SENSOR_WATER_VOLUME}"
        self._attr_native_value = 0.0
        self._attr_native_unit_of_measurement = UnitOfVolume.MILLILITERS
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:water"
        self._last_update: datetime = datetime.now()

    async def async_added_to_hass(self) -> None:
        """Restore accumulated volume from shared storage."""
        stored = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {})
        self._attr_native_value = stored.get("total_volume", 0.0)
        self._last_update = datetime.now()

    @property
    def state(self) -> float:
        """Return the current water volume."""
        return self._attr_native_value

    async def async_update(self) -> None:
        """Accumulate volume based on pump flow rates and elapsed run time."""
        now = datetime.now()
        elapsed_seconds = (now - self._last_update).total_seconds()
        self._last_update = now

        for pump in self._pumps:
            switch_id = pump.get(CONF_PUMP_SWITCH)
            flow_rate = pump.get(CONF_PUMP_FLOW_RATE, 0)
            if switch_id:
                state = self.hass.states.get(switch_id)
                if state and state.state == "on":
                    self._attr_native_value += flow_rate * elapsed_seconds

        domain_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id)
        if domain_data is not None:
            domain_data["total_volume"] = self._attr_native_value
