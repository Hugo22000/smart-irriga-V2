"""Button platform for Smart Irrigation V2."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BUTTON_START_IRRIGATION,
    BUTTON_STOP_IRRIGATION,
    CONF_PUMPS,
    CONF_PUMP_SWITCH,
    DOMAIN,
)
from . import start_irrigation


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    async_add_entities([
        StartIrrigationButton(entry),
        StopIrrigationButton(entry),
    ])


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


class StopIrrigationButton(ButtonEntity):
    """Button to immediately stop irrigation and cancel the auto-stop timer."""

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_name = f"{entry.title} Stop Irrigation"
        self._attr_unique_id = f"{entry.entry_id}_{BUTTON_STOP_IRRIGATION}"
        self._attr_icon = "mdi:stop-circle-outline"

    async def async_press(self) -> None:
        """Cancel the running timer and turn off all pump switches."""
        entry_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id)

        # Cancel auto-stop timer if one is pending
        if entry_data is not None:
            cancel = entry_data.pop("stop_cancel", None)
            if cancel:
                cancel()

        # Turn off all pump switches
        pumps = list(self._entry.options.get(CONF_PUMPS) or self._entry.data.get(CONF_PUMPS, []))
        for pump in pumps:
            switch_id = pump.get(CONF_PUMP_SWITCH)
            if switch_id:
                await self.hass.services.async_call(
                    "switch", "turn_off", {"entity_id": switch_id}, blocking=True
                )

        if entry_data is not None:
            entry_data["irrigating"] = False
