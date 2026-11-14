"""Config flow for Dpc: the place to monitor, on a map or from a zone."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from aiodpc import AlertZone, DpcClient, DpcError, DpcLocationError, Location
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_LATITUDE,
    CONF_LOCATION,
    CONF_LONGITUDE,
    CONF_NAME,
    CONF_RADIUS,
    CONF_SCAN_INTERVAL,
    CONF_ZONE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    LocationSelector,
    LocationSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_MUNICIPALITY,
    CONF_WARNING_LEVEL,
    DEFAULT_NAME,
    DEFAULT_RADIUS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WARNING_LEVEL,
    DOMAIN,
    LOGGER,
    PLATFORMS,
    WARNING_LEVELS,
)

ZONE_DOMAIN = "zone"
HOME_ZONE = "zone.home"


async def async_get_alert_zone(
    hass: HomeAssistant, latitude: float, longitude: float
) -> AlertZone:
    """Return the DPC alert zone of a place, with its municipalities.

    Raises :class:`aiodpc.DpcLocationError` when DPC does not cover the place,
    or another :class:`aiodpc.DpcError` when DPC cannot be reached.
    """
    client = DpcClient(async_get_clientsession(hass))
    return await client.get_alert_zone(Location(latitude, longitude))


def municipality_selector(
    municipalities: Iterable[str], current: str = ""
) -> SelectSelector:
    """Return a picker of the municipalities of an alert zone.

    Any other name can be typed too, e.g. a municipality listed in another
    zone, or any name when the zone could not be fetched.
    """
    options = {*municipalities, *([current] if current else [])}
    return SelectSelector(
        SelectSelectorConfig(
            options=sorted(options, key=str.casefold),
            custom_value=True,
            mode=SelectSelectorMode.DROPDOWN,
            sort=False,
        )
    )


class DpcFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Dpc."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the flow."""
        self._place: dict[str, Any] = {}
        self._alert_zone: AlertZone | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask how to give the place to monitor: on a map or from a zone."""
        return self.async_show_menu(step_id="user", menu_options=["map", "zone"])

    async def async_step_map(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the place on a map, which starts at home."""
        errors: dict[str, str] = {}
        if user_input is not None:
            location = user_input[CONF_LOCATION]
            errors = await self._async_set_place(
                user_input[CONF_NAME],
                location[CONF_LATITUDE],
                location[CONF_LONGITUDE],
            )
            if not errors:
                return await self.async_step_municipality()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_LOCATION): LocationSelector(
                    LocationSelectorConfig(radius=False)
                ),
            }
        )
        home = {
            CONF_NAME: DEFAULT_NAME,
            CONF_LOCATION: {
                CONF_LATITUDE: self.hass.config.latitude,
                CONF_LONGITUDE: self.hass.config.longitude,
            },
        }
        return self.async_show_form(
            step_id="map",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or home),
            errors=errors,
        )

    async def async_step_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Use the place of a zone, such as Home."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if (zone := self.hass.states.get(user_input[CONF_ZONE])) is None:
                errors[CONF_ZONE] = "zone_not_found"
            else:
                errors = await self._async_set_place(
                    user_input.get(CONF_NAME) or zone.name,
                    zone.attributes[ATTR_LATITUDE],
                    zone.attributes[ATTR_LONGITUDE],
                )
                if not errors:
                    return await self.async_step_municipality()

        schema = vol.Schema(
            {
                vol.Required(CONF_ZONE): EntitySelector(
                    EntitySelectorConfig(domain=ZONE_DOMAIN)
                ),
                vol.Optional(CONF_NAME): str,
            }
        )
        return self.async_show_form(
            step_id="zone",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or {CONF_ZONE: HOME_ZONE}
            ),
            errors=errors,
        )

    async def async_step_municipality(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the alert zone of the place and choose its municipality."""
        assert self._alert_zone is not None
        if user_input is not None:
            return self.async_create_entry(
                title=self._place[CONF_NAME],
                data=self._place,
                options={CONF_MUNICIPALITY: user_input.get(CONF_MUNICIPALITY, "")},
            )

        return self.async_show_form(
            step_id="municipality",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_MUNICIPALITY): municipality_selector(
                        self._alert_zone.municipalities
                    )
                }
            ),
            description_placeholders={"zone": self._alert_zone.name},
        )

    async def _async_set_place(
        self, name: str, latitude: float, longitude: float
    ) -> dict[str, str]:
        """Check a place with DPC and keep it; return the errors, if any.

        Aborts the flow when the place is already configured.
        """
        latitude, longitude = round(latitude, 6), round(longitude, 6)
        if self._is_location_configured(latitude, longitude):
            raise AbortFlow("already_configured")
        await self.async_set_unique_id(f"{latitude:.6f}_{longitude:.6f}")
        self._abort_if_unique_id_configured()

        try:
            self._alert_zone = await async_get_alert_zone(
                self.hass, latitude, longitude
            )
        except DpcLocationError:
            return {"base": "coordinates_outside"}
        except DpcError as err:
            LOGGER.debug("The DPC alert zones could not be fetched: %s", err)
            return {"base": "cannot_connect"}
        self._place = {
            CONF_NAME: name,
            CONF_LATITUDE: latitude,
            CONF_LONGITUDE: longitude,
        }
        return {}

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

        municipality = self.options.get(CONF_MUNICIPALITY, "")
        try:
            alert_zone = await async_get_alert_zone(
                self.hass, self.data[CONF_LATITUDE], self.data[CONF_LONGITUDE]
            )
        except DpcError as err:
            LOGGER.debug("No municipalities to offer, any can be typed: %s", err)
            municipalities: Iterable[str] = ()
        else:
            municipalities = alert_zone.municipalities

        schema = {
            vol.Required(x, default=self.options.get(x, True)): bool
            for x in sorted(PLATFORMS)
        }
        schema.update(
            {
                vol.Optional(
                    CONF_MUNICIPALITY,
                    default="",
                    description={"suggested_value": municipality},
                ): municipality_selector(municipalities, municipality),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): cv.positive_int,
                vol.Optional(
                    CONF_WARNING_LEVEL,
                    default=self.options.get(CONF_WARNING_LEVEL, DEFAULT_WARNING_LEVEL),
                ): vol.In(WARNING_LEVELS),
                vol.Required(
                    CONF_RADIUS,
                    default=self.options.get(CONF_RADIUS, DEFAULT_RADIUS),
                ): vol.All(vol.Coerce(float), vol.Range(min=0)),
            }
        )
        return self.async_show_form(step_id="user", data_schema=vol.Schema(schema))

    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(
            title="",
            data=self.options,
        )
