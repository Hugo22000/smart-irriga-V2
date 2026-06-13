"""Switch platform for Smart Irrigation V2."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_PUMPS, CONF_PUMP_SWITCH


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    pumps = list(entry.options.get(CONF_PUMPS) or entry.data.get(CONF_PUMPS, []))
    entities = []
    
    for i, pump in enumerate(pumps):
        switch_entity_id = pump.get(CONF_PUMP_SWITCH)
        if switch_entity_id:
            entities.append(IrrigationPumpSwitch(entry, i, pump))
    
    async_add_entities(entities)


class IrrigationPumpSwitch(SwitchEntity):
    """Represents a switch for an irrigation pump."""

    def __init__(self, entry: ConfigEntry, pump_index: int, pump_config: dict) -> None:
        """Initialize the switch."""
        self._entry = entry
        self._pump_index = pump_index
        self._pump_config = pump_config
        self._attr_name = f"{entry.title} Pump {pump_index + 1}"
        self._attr_unique_id = f"{entry.entry_id}_pump_{pump_index}_switch"
        self._attr_icon = "mdi:pump"
        self._switch_entity_id = pump_config.get(CONF_PUMP_SWITCH)

    @property
    def is_on(self) -> bool:
        """Return true if the pump is on."""
        if self._switch_entity_id and self.hass:
            entity_state = self.hass.states.get(self._switch_entity_id)
            return entity_state and entity_state.state == "on"
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the pump on."""
        if self._switch_entity_id and self.hass:
            await self.hass.services.async_call(
                "switch", "turn_on", {"entity_id": self._switch_entity_id}
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the pump off."""
        if self._switch_entity_id and self.hass:
            await self.hass.services.async_call(
                "switch", "turn_off", {"entity_id": self._switch_entity_id}
            )
