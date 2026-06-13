"""Button platform for Smart Irrigation V2."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, BUTTON_START_IRRIGATION
from . import start_irrigation


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    async_add_entities([StartIrrigationButton(entry)])


class StartIrrigationButton(ButtonEntity):
    """Button to start irrigation manually (overrides any active mode)."""

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_name = f"{entry.title} Start Irrigation"
        self._attr_unique_id = f"{entry.entry_id}_{BUTTON_START_IRRIGATION}"
        self._attr_icon = "mdi:water-pump"

    async def async_press(self) -> None:
        """Start irrigation immediately regardless of the configured mode."""
        domain_data = self.hass.data.get(DOMAIN, {})
        entry_data = domain_data.get(self._entry.entry_id)
        if entry_data is not None:
            entry_data["irrigating"] = False
        await start_irrigation(self.hass, self._entry)
