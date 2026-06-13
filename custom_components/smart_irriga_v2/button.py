"""Button platform for Smart Irrigation V2."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, BUTTON_START_IRRIGATION, CONF_PUMPS, CONF_PUMP_SWITCH, CONF_PUMP_FLOW_RATE


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    async_add_entities([StartIrrigationButton(entry)])


class StartIrrigationButton(ButtonEntity):
    """Button to start irrigation manually."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the button."""
        self._entry = entry
        self._attr_name = f"{entry.title} Start Irrigation"
        self._attr_unique_id = f"{entry.entry_id}_{BUTTON_START_IRRIGATION}"
        self._attr_icon = "mdi:water-pump"

    async def async_press(self) -> None:
        """Turn on all pumps and accumulate the dispensed volume."""
        pumps = self._entry.data.get(CONF_PUMPS, [])
        domain_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {})

        for pump in pumps:
            switch_entity_id = pump.get(CONF_PUMP_SWITCH)
            if switch_entity_id:
                await self.hass.services.async_call(
                    "switch", "turn_on", {"entity_id": switch_entity_id}
                )
            domain_data["total_volume"] = domain_data.get("total_volume", 0.0) + pump.get(CONF_PUMP_FLOW_RATE, 0)
