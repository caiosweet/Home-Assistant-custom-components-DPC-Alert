"""Adds config flow for Dpc."""

from datetime import timedelta

import homeassistant.helpers.config_validation as cv
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
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DpcApiClient
from .const import (
    CONF_MUNICIPALITY,
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
        errors = {}

        if user_input is not None:
            latitude = round(user_input[CONF_LATITUDE], 6)
            longitude = round(user_input[CONF_LONGITUDE], 6)
            if self._is_location_configured(latitude, longitude):
                return self.async_abort(reason="already_configured")

            is_valid = await self._async_validate_coordinates(latitude, longitude)
            if is_valid is False:
                errors["base"] = "coordinates_outside"
            elif is_valid is None:
                errors["base"] = "cannot_connect"
            else:
                unique_id = f"{latitude:.6f}_{longitude:.6f}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        name_default = DEFAULT_NAME
        latitude_default = self.hass.config.latitude
        longitude_default = self.hass.config.longitude
        if user_input is not None:
            name_default = user_input.get(CONF_NAME, name_default)
            latitude_default = user_input.get(CONF_LATITUDE, latitude_default)
            longitude_default = user_input.get(CONF_LONGITUDE, longitude_default)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                        default=(name_default),  # {self.hass.config.location_name}
                    ): str,
                    vol.Required(CONF_LATITUDE, default=(latitude_default)): cv.latitude,
                    vol.Required(
                        CONF_LONGITUDE, default=(longitude_default)
                    ): cv.longitude,
                }
            ),
            errors=errors,
        )

    def _is_location_configured(self, latitude: float, longitude: float) -> bool:
        """Check if a config entry already exists for this location."""
        for entry in self._async_current_entries():
            entry_lat = entry.data.get(CONF_LATITUDE)
            entry_lon = entry.data.get(CONF_LONGITUDE)
            if entry_lat is None or entry_lon is None:
                continue
            if round(entry_lat, 6) == latitude and round(entry_lon, 6) == longitude:
                return True
        return False

    async def _async_validate_coordinates(
        self, latitude: float, longitude: float
    ) -> bool | None:
        session = async_get_clientsession(self.hass)
        client = DpcApiClient(
            location_name="Validation",
            latitude=latitude,
            longitude=longitude,
            municipality="",
            radius=DEFAULT_RADIUS,
            session=session,
            update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL),
        )
        return await client.async_validate_coordinates()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DpcOptionsFlowHandler(config_entry)


class DpcOptionsFlowHandler(config_entries.OptionsFlow):
    """Dpc config flow options handler."""

    def __init__(self, config_entry):
        """Initialize HACS options flow."""
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
                    CONF_MUNICIPALITY,
                    default="",
                    description={"suggested_value": self.options.get(CONF_MUNICIPALITY, "")},
                ): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): cv.positive_int,
                vol.Optional(
                    CONF_WARNING_LEVEL,
                    default=self.options.get(CONF_WARNING_LEVEL, DEFAULT_WARNING_LEVEL),
                ): vol.In(list(WARNING_ALERT.values())),
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
