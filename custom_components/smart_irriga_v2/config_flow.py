"""Config flow for Smart Irrigation V2."""
from __future__ import annotations

import logging
import voluptuous as vol
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_ZONE_NAME,
    CONF_NUM_PUMPS,
    CONF_PUMPS,
    CONF_PUMP_SWITCH,
    CONF_PUMP_FLOW_RATE,
    DEFAULT_ZONE_NAME,
    DEFAULT_NUM_PUMPS,
    MIN_FLOW_RATE,
    MAX_FLOW_RATE,
    DEFAULT_FLOW_RATE,
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Irrigation V2."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._zone_name: str = DEFAULT_ZONE_NAME
        self._num_pumps: int = DEFAULT_NUM_PUMPS
        self._pumps_config: list[dict[str, Any]] = []
        self._current_pump_index: int = 0

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step: ask for zone name and number of pumps."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._zone_name = user_input[CONF_ZONE_NAME]
            self._num_pumps = int(user_input[CONF_NUM_PUMPS])
            self._pumps_config = []
            self._current_pump_index = 0
            return await self.async_step_pumps()

        schema = vol.Schema(
            {
                vol.Required(CONF_ZONE_NAME, default=DEFAULT_ZONE_NAME): str,
                vol.Required(
                    CONF_NUM_PUMPS, default=DEFAULT_NUM_PUMPS
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=3, step=1, mode="slider"
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_pumps(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the step: configure each pump one at a time."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._pumps_config.append({
                CONF_PUMP_SWITCH: user_input[CONF_PUMP_SWITCH],
                CONF_PUMP_FLOW_RATE: int(user_input[CONF_PUMP_FLOW_RATE]),
            })
            self._current_pump_index += 1
            if self._current_pump_index >= self._num_pumps:
                return await self._async_create_entry()

        schema = vol.Schema(
            {
                vol.Required(CONF_PUMP_SWITCH): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch")
                ),
                vol.Required(
                    CONF_PUMP_FLOW_RATE, default=DEFAULT_FLOW_RATE
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_FLOW_RATE,
                        max=MAX_FLOW_RATE,
                        step=5,
                        mode="box",
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="pumps",
            data_schema=schema,
            description_placeholders={
                "pump_number": str(self._current_pump_index + 1),
                "total_pumps": str(self._num_pumps),
            },
            errors=errors,
        )

    async def _async_create_entry(self) -> FlowResult:
        """Create the config entry."""
        data = {
            CONF_ZONE_NAME: self._zone_name,
            CONF_NUM_PUMPS: self._num_pumps,
            CONF_PUMPS: self._pumps_config,
        }
        return self.async_create_entry(
            title=f"{self._zone_name} ({self._num_pumps} pumps)",
            data=data,
        )
