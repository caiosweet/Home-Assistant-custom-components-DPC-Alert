"""Adds config flow for Dpc."""
from email.policy import default

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    CONF_RADIUS,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_COMUNE,
    CONF_WARNING_LEVEL,
    DEFAULT_NAME,
    DEFAULT_RADIUS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WARNING_LEVEL,
    DOMAIN,
    PLATFORMS,
    WARNING_ALERT,
)


class DpcFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Dpc."""

    VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_NAME])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                        default=(DEFAULT_NAME),  # {self.hass.config.location_name}
                    ): str,
                    vol.Required(CONF_LATITUDE, default=(self.hass.config.latitude)): cv.latitude,
                    vol.Required(
                        CONF_LONGITUDE, default=(self.hass.config.longitude)
                    ): cv.longitude,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DpcOptionsFlowHandler(config_entry)


class DpcOptionsFlowHandler(config_entries.OptionsFlow):
    """Dpc config flow options handler."""

    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)
        self.data = dict(config_entry.data)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self.options.update(user_input)
            return await self._update_options()

        schema = {
            vol.Required(x, default=self.options.get(x, True)): bool for x in sorted(PLATFORMS)
        }
        schema.update(
            {
                vol.Optional(
                    CONF_COMUNE,
                    default="",
                    description={"suggested_value": self.options.get(CONF_COMUNE, "")},
                ): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): cv.positive_int,
                vol.Optional(
                    CONF_WARNING_LEVEL,
                    default=self.options.get(CONF_WARNING_LEVEL, DEFAULT_WARNING_LEVEL),
                ): vol.In(WARNING_ALERT.values()),
                vol.Required(
                    CONF_RADIUS,
                    default=self.options.get(CONF_RADIUS, DEFAULT_RADIUS),
                ): vol.Coerce(float),
            }
        )
        return self.async_show_form(step_id="user", data_schema=vol.Schema(schema))

    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(
            title="",
            data=self.options,
        )
