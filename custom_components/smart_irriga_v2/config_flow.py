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
    CONF_ACTIVATION_MODE,
    CONF_HUMIDITY_SENSOR,
    CONF_HUMIDITY_THRESHOLD,
    CONF_IRRIGATION_DURATION,
    CONF_NUM_PUMPS,
    CONF_PUMP_FLOW_RATE,
    CONF_PUMP_SWITCH,
    CONF_PUMPS,
    CONF_SCHEDULE_DAYS,
    CONF_SCHEDULE_TIME,
    CONF_ZONE_NAME,
    DEFAULT_FLOW_RATE,
    DEFAULT_HUMIDITY_THRESHOLD,
    DEFAULT_IRRIGATION_DURATION,
    DEFAULT_NUM_PUMPS,
    DEFAULT_ZONE_NAME,
    DOMAIN,
    MAX_FLOW_RATE,
    MIN_FLOW_RATE,
    MODE_HUMIDITY,
    MODE_MANUAL,
    MODE_SCHEDULE,
)

_LOGGER = logging.getLogger(__name__)

_MODE_OPTIONS = [
    {"value": MODE_MANUAL, "label": "Manuel"},
    {"value": MODE_SCHEDULE, "label": "Planification"},
    {"value": MODE_HUMIDITY, "label": "Capteur d'humidité"},
]

_DAY_OPTIONS = [
    {"value": "mon", "label": "Lundi"},
    {"value": "tue", "label": "Mardi"},
    {"value": "wed", "label": "Mercredi"},
    {"value": "thu", "label": "Jeudi"},
    {"value": "fri", "label": "Vendredi"},
    {"value": "sat", "label": "Samedi"},
    {"value": "sun", "label": "Dimanche"},
]


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Irrigation V2."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        self._zone_name: str = DEFAULT_ZONE_NAME
        self._num_pumps: int = DEFAULT_NUM_PUMPS
        self._pumps_config: list[dict[str, Any]] = []
        self._current_pump_index: int = 0
        self._mode: str = MODE_MANUAL
        self._duration: int = DEFAULT_IRRIGATION_DURATION
        self._schedule_time: str = "08:00:00"
        self._schedule_days: list[str] = []
        self._humidity_sensor: str = ""
        self._humidity_threshold: int = DEFAULT_HUMIDITY_THRESHOLD

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> PumpOptionsFlow:
        """Return the options flow."""
        return PumpOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._zone_name = user_input[CONF_ZONE_NAME]
            self._num_pumps = int(user_input[CONF_NUM_PUMPS])
            self._pumps_config = []
            self._current_pump_index = 0
            return await self.async_step_pumps()

        schema = vol.Schema({
            vol.Required(CONF_ZONE_NAME, default=DEFAULT_ZONE_NAME): str,
            vol.Required(CONF_NUM_PUMPS, default=DEFAULT_NUM_PUMPS): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=3, step=1, mode="box")
            ),
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_pumps(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._pumps_config.append({
                CONF_PUMP_SWITCH: user_input[CONF_PUMP_SWITCH],
                CONF_PUMP_FLOW_RATE: int(user_input[CONF_PUMP_FLOW_RATE]),
            })
            self._current_pump_index += 1
            if self._current_pump_index >= self._num_pumps:
                return await self.async_step_mode()

        schema = vol.Schema({
            vol.Required(CONF_PUMP_SWITCH): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="switch")
            ),
            vol.Required(CONF_PUMP_FLOW_RATE, default=DEFAULT_FLOW_RATE): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_FLOW_RATE, max=MAX_FLOW_RATE, step=5, mode="box"
                )
            ),
        })

        return self.async_show_form(
            step_id="pumps",
            data_schema=schema,
            description_placeholders={
                "pump_number": str(self._current_pump_index + 1),
                "total_pumps": str(self._num_pumps),
            },
            errors=errors,
        )

    async def async_step_mode(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._mode = user_input[CONF_ACTIVATION_MODE]
            self._duration = int(user_input[CONF_IRRIGATION_DURATION])
            if self._mode == MODE_SCHEDULE:
                return await self.async_step_schedule()
            if self._mode == MODE_HUMIDITY:
                return await self.async_step_humidity()
            return await self._async_create_entry()

        schema = vol.Schema({
            vol.Required(CONF_ACTIVATION_MODE, default=self._mode): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_MODE_OPTIONS,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Required(CONF_IRRIGATION_DURATION, default=self._duration): selector.NumberSelector(
                selector.NumberSelectorConfig(min=10, max=3600, step=10, mode="box")
            ),
        })

        return self.async_show_form(step_id="mode", data_schema=schema)

    async def async_step_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._schedule_time = user_input[CONF_SCHEDULE_TIME]
            self._schedule_days = user_input[CONF_SCHEDULE_DAYS]
            return await self._async_create_entry()

        schema = vol.Schema({
            vol.Required(CONF_SCHEDULE_TIME, default=self._schedule_time): selector.TimeSelector(),
            vol.Required(CONF_SCHEDULE_DAYS, default=self._schedule_days): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_DAY_OPTIONS,
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        })

        return self.async_show_form(step_id="schedule", data_schema=schema)

    async def async_step_humidity(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._humidity_sensor = user_input[CONF_HUMIDITY_SENSOR]
            self._humidity_threshold = int(user_input[CONF_HUMIDITY_THRESHOLD])
            return await self._async_create_entry()

        schema = vol.Schema({
            vol.Required(CONF_HUMIDITY_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(CONF_HUMIDITY_THRESHOLD, default=self._humidity_threshold): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=5, mode="box")
            ),
        })

        return self.async_show_form(step_id="humidity", data_schema=schema)

    async def _async_create_entry(self) -> FlowResult:
        data: dict[str, Any] = {
            CONF_ZONE_NAME: self._zone_name,
            CONF_NUM_PUMPS: self._num_pumps,
            CONF_PUMPS: self._pumps_config,
            CONF_ACTIVATION_MODE: self._mode,
            CONF_IRRIGATION_DURATION: self._duration,
        }
        if self._mode == MODE_SCHEDULE:
            data[CONF_SCHEDULE_TIME] = self._schedule_time
            data[CONF_SCHEDULE_DAYS] = self._schedule_days
        elif self._mode == MODE_HUMIDITY:
            data[CONF_HUMIDITY_SENSOR] = self._humidity_sensor
            data[CONF_HUMIDITY_THRESHOLD] = self._humidity_threshold

        return self.async_create_entry(title=self._zone_name, data=data)


class PumpOptionsFlow(config_entries.OptionsFlow):
    """Allow modifying the number of pumps, their switch, flow rate and activation mode."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._existing_pumps: list[dict[str, Any]] = list(
            config_entry.options.get(CONF_PUMPS)
            or config_entry.data.get(CONF_PUMPS, [])
        )
        self._num_pumps: int = (
            int(config_entry.options.get(CONF_NUM_PUMPS, 0))
            or len(self._existing_pumps)
            or int(config_entry.data.get(CONF_NUM_PUMPS, DEFAULT_NUM_PUMPS))
        )
        self._mode: str = (
            config_entry.options.get(CONF_ACTIVATION_MODE)
            or config_entry.data.get(CONF_ACTIVATION_MODE, MODE_MANUAL)
        )
        self._duration: int = int(
            config_entry.options.get(CONF_IRRIGATION_DURATION)
            or config_entry.data.get(CONF_IRRIGATION_DURATION, DEFAULT_IRRIGATION_DURATION)
        )
        self._schedule_time: str = (
            config_entry.options.get(CONF_SCHEDULE_TIME)
            or config_entry.data.get(CONF_SCHEDULE_TIME, "08:00:00")
        )
        self._schedule_days: list[str] = list(
            config_entry.options.get(CONF_SCHEDULE_DAYS)
            or config_entry.data.get(CONF_SCHEDULE_DAYS, [])
        )
        self._humidity_sensor: str = (
            config_entry.options.get(CONF_HUMIDITY_SENSOR)
            or config_entry.data.get(CONF_HUMIDITY_SENSOR, "")
        )
        self._humidity_threshold: int = int(
            config_entry.options.get(CONF_HUMIDITY_THRESHOLD)
            or config_entry.data.get(CONF_HUMIDITY_THRESHOLD, DEFAULT_HUMIDITY_THRESHOLD)
        )
        self._updated_pumps: list[dict[str, Any]] = []
        self._current_pump_index: int = 0

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for new number of pumps, mode and duration."""
        if user_input is not None:
            self._num_pumps = int(user_input[CONF_NUM_PUMPS])
            self._mode = user_input[CONF_ACTIVATION_MODE]
            self._duration = int(user_input[CONF_IRRIGATION_DURATION])
            self._updated_pumps = []
            self._current_pump_index = 0
            return await self.async_step_pumps()

        schema = vol.Schema({
            vol.Required(CONF_NUM_PUMPS, default=self._num_pumps): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=3, step=1, mode="box")
            ),
            vol.Required(CONF_ACTIVATION_MODE, default=self._mode): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_MODE_OPTIONS,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Required(CONF_IRRIGATION_DURATION, default=self._duration): selector.NumberSelector(
                selector.NumberSelectorConfig(min=10, max=3600, step=10, mode="box")
            ),
        })

        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_pumps(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._updated_pumps.append({
                CONF_PUMP_SWITCH: user_input[CONF_PUMP_SWITCH],
                CONF_PUMP_FLOW_RATE: int(user_input[CONF_PUMP_FLOW_RATE]),
            })
            self._current_pump_index += 1
            if self._current_pump_index >= self._num_pumps:
                if self._mode == MODE_SCHEDULE:
                    return await self.async_step_schedule()
                if self._mode == MODE_HUMIDITY:
                    return await self.async_step_humidity()
                return self._create_options_entry()

        existing = (
            self._existing_pumps[self._current_pump_index]
            if self._current_pump_index < len(self._existing_pumps)
            else {}
        )
        current_switch = existing.get(CONF_PUMP_SWITCH)
        current_flow = existing.get(CONF_PUMP_FLOW_RATE, DEFAULT_FLOW_RATE)

        switch_field = (
            vol.Required(CONF_PUMP_SWITCH, default=current_switch)
            if current_switch
            else vol.Required(CONF_PUMP_SWITCH)
        )

        schema = vol.Schema({
            switch_field: selector.EntitySelector(
                selector.EntitySelectorConfig(domain="switch")
            ),
            vol.Required(CONF_PUMP_FLOW_RATE, default=current_flow): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_FLOW_RATE, max=MAX_FLOW_RATE, step=5, mode="box"
                )
            ),
        })

        return self.async_show_form(
            step_id="pumps",
            data_schema=schema,
            description_placeholders={
                "pump_number": str(self._current_pump_index + 1),
                "total_pumps": str(self._num_pumps),
            },
        )

    async def async_step_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._schedule_time = user_input[CONF_SCHEDULE_TIME]
            self._schedule_days = user_input[CONF_SCHEDULE_DAYS]
            return self._create_options_entry()

        schema = vol.Schema({
            vol.Required(CONF_SCHEDULE_TIME, default=self._schedule_time): selector.TimeSelector(),
            vol.Required(CONF_SCHEDULE_DAYS, default=self._schedule_days): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=_DAY_OPTIONS,
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        })

        return self.async_show_form(step_id="schedule", data_schema=schema)

    async def async_step_humidity(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._humidity_sensor = user_input[CONF_HUMIDITY_SENSOR]
            self._humidity_threshold = int(user_input[CONF_HUMIDITY_THRESHOLD])
            return self._create_options_entry()

        humidity_sensor_field = (
            vol.Required(CONF_HUMIDITY_SENSOR, default=self._humidity_sensor)
            if self._humidity_sensor
            else vol.Required(CONF_HUMIDITY_SENSOR)
        )

        schema = vol.Schema({
            humidity_sensor_field: selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(CONF_HUMIDITY_THRESHOLD, default=self._humidity_threshold): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=5, mode="box")
            ),
        })

        return self.async_show_form(step_id="humidity", data_schema=schema)

    def _create_options_entry(self) -> FlowResult:
        options: dict[str, Any] = {
            CONF_NUM_PUMPS: self._num_pumps,
            CONF_PUMPS: self._updated_pumps,
            CONF_ACTIVATION_MODE: self._mode,
            CONF_IRRIGATION_DURATION: self._duration,
        }
        if self._mode == MODE_SCHEDULE:
            options[CONF_SCHEDULE_TIME] = self._schedule_time
            options[CONF_SCHEDULE_DAYS] = self._schedule_days
        elif self._mode == MODE_HUMIDITY:
            options[CONF_HUMIDITY_SENSOR] = self._humidity_sensor
            options[CONF_HUMIDITY_THRESHOLD] = self._humidity_threshold
        return self.async_create_entry(title="", data=options)
