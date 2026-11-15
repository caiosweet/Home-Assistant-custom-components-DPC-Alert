"""Config flow for Dpc: the place to monitor, on a map or from a zone."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from aiodpc import AlertZone, DpcClient, DpcError, DpcLocationError, Location
import homeassistant.helpers.config_validation as cv

try:  # Home Assistant 2026.9 and newer validate with probatio
    import probatio as vol
except ImportError:  # pragma: no cover - older versions, back to 2025.2
    import voluptuous as vol  # type: ignore[no-redef]
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
from homeassistant.util.location import distance

from .const import (
    CONF_MUNICIPALITY,
    CONF_WARNING_LEVEL,
    DEFAULT_NAME,
    DEFAULT_RADIUS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WARNING_LEVEL,
    DOMAIN,
    LOGGER,
    MIN_DISTANCE_BETWEEN_PLACES,
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
        self._placeholders: dict[str, str] = {}
        """Placeholders of the errors of the place, e.g. the nearby place."""

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
            CONF_NAME: self.hass.config.location_name or DEFAULT_NAME,
            CONF_LOCATION: {
                CONF_LATITUDE: self.hass.config.latitude,
                CONF_LONGITUDE: self.hass.config.longitude,
            },
        }
        return self.async_show_form(
            step_id="map",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or home),
            errors=errors,
            description_placeholders=self._placeholders,
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
            description_placeholders=self._placeholders,
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
        """Check a place and keep it; return the errors, if any.

        Aborts the flow when the place is already configured. A place less
        than 1 km from another one is refused too: its bulletins would be the
        same. So is a name already given to another place.
        """
        latitude, longitude = round(latitude, 6), round(longitude, 6)
        await self.async_set_unique_id(f"{latitude:.6f}_{longitude:.6f}")
        self._abort_if_unique_id_configured()
        if (nearby := self._nearby_place(latitude, longitude)) is not None:
            self._placeholders = {"place": nearby.title}
            return {"base": "place_nearby"}
        if self._name_in_use(name):
            return {CONF_NAME: "name_exists"}

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

    def _nearby_place(
        self, latitude: float, longitude: float
    ) -> config_entries.ConfigEntry | None:
        """Return a configured place less than 1 km away, if any."""
        for entry in self._async_current_entries(include_ignore=False):
            other_latitude = entry.data.get(CONF_LATITUDE)
            other_longitude = entry.data.get(CONF_LONGITUDE)
            if other_latitude is None or other_longitude is None:
                continue
            meters = distance(latitude, longitude, other_latitude, other_longitude)
            if meters is not None and meters < MIN_DISTANCE_BETWEEN_PLACES:
                return entry
        return None

    def _name_in_use(self, name: str) -> bool:
        """Return whether another place has this name, ignoring case."""
        wanted = name.strip().casefold()
        return any(
            wanted
            in {
                entry.title.strip().casefold(),
                str(entry.data.get(CONF_NAME, "")).strip().casefold(),
            }
            for entry in self._async_current_entries(include_ignore=False)
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> DpcOptionsFlowHandler:
        """Return the options flow of a place."""
        return DpcOptionsFlowHandler()


class DpcOptionsFlowHandler(config_entries.OptionsFlow):
    """Options of a place."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and save the options of the place."""
        options = dict(self.config_entry.options)
        if user_input is not None:
            return self.async_create_entry(data=options | user_input)

        municipality = options.get(CONF_MUNICIPALITY, "")
        try:
            alert_zone = await async_get_alert_zone(
                self.hass,
                self.config_entry.data[CONF_LATITUDE],
                self.config_entry.data[CONF_LONGITUDE],
            )
        except DpcError as err:
            LOGGER.debug("No municipalities to offer, any can be typed: %s", err)
            municipalities: Iterable[str] = ()
        else:
            municipalities = alert_zone.municipalities

        schema: dict[vol.Marker, Any] = {
            vol.Required(platform, default=options.get(platform, True)): bool
            for platform in sorted(PLATFORMS)
        }
        schema |= {
            vol.Optional(
                CONF_MUNICIPALITY,
                default="",
                description={"suggested_value": municipality},
            ): municipality_selector(municipalities, municipality),
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): cv.positive_int,
            vol.Optional(
                CONF_WARNING_LEVEL,
                default=options.get(CONF_WARNING_LEVEL, DEFAULT_WARNING_LEVEL),
            ): vol.In(WARNING_LEVELS),
            vol.Required(
                CONF_RADIUS,
                default=options.get(CONF_RADIUS, DEFAULT_RADIUS),
            ): vol.All(vol.Coerce(float), vol.Range(min=0)),
        }
        return self.async_show_form(step_id="user", data_schema=vol.Schema(schema))
