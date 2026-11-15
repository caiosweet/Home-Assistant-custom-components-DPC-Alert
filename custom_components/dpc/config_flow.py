"""Config flow for Dpc: the place to monitor, on a map or from a zone."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from aiodpc import AlertZone, DpcClient, DpcError, DpcLocationError, Location
from aiodpc.municipalities import municipality_names
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

from .const import (
    CONF_MUNICIPALITY,
    CONF_WARNING_LEVEL,
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
    """Return a picker of the municipalities of an alert zone, with a search.

    It accepts typed text too, which the flows check against the list: the
    search needs it, and any name can be typed when DPC cannot be reached.
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


def listed_municipality(municipalities: Iterable[str], municipality: str) -> str | None:
    """Return a municipality as DPC lists it, e.g. "Bolzano/Bozen" for "bozen"."""
    names = municipality_names(municipality)
    return next(
        (listed for listed in municipalities if names & municipality_names(listed)),
        None,
    )


def place_with_municipality(
    hass: HomeAssistant, municipality: str, *, other_than: str | None = None
) -> config_entries.ConfigEntry | None:
    """Return the place that already has a municipality, if any.

    The municipality identifies a place: two places with the same municipality
    would get the same bulletins. Any name of it counts: "Bozen" is
    "Bolzano/Bozen".
    """
    names = municipality_names(municipality)
    for entry in hass.config_entries.async_entries(DOMAIN, include_ignore=False):
        if entry.entry_id != other_than and names & municipality_names(
            entry.options.get(CONF_MUNICIPALITY) or ""
        ):
            return entry
    return None


class DpcFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Dpc: a place and its municipality.

    The place is named after its DPC alert zone, and its municipality, one of
    the zone, identifies it.
    """

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
                location[CONF_LATITUDE], location[CONF_LONGITUDE]
            )
            if not errors:
                return await self.async_step_municipality()

        schema = vol.Schema(
            {
                vol.Required(CONF_LOCATION): LocationSelector(
                    LocationSelectorConfig(radius=False)
                ),
            }
        )
        home = {
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
                    zone.attributes[ATTR_LATITUDE], zone.attributes[ATTR_LONGITUDE]
                )
                if not errors:
                    return await self.async_step_municipality()

        schema = vol.Schema(
            {
                vol.Required(CONF_ZONE): EntitySelector(
                    EntitySelectorConfig(domain=ZONE_DOMAIN)
                ),
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
        errors: dict[str, str] = {}
        placeholders = {"zone": self._alert_zone.name}
        if user_input is not None:
            municipality = listed_municipality(
                self._alert_zone.municipalities, user_input[CONF_MUNICIPALITY]
            )
            if municipality is None:
                errors[CONF_MUNICIPALITY] = "municipality_not_listed"
            elif (
                other := place_with_municipality(self.hass, municipality)
            ) is not None:
                errors[CONF_MUNICIPALITY] = "municipality_in_use"
                placeholders["municipality"] = other.options[CONF_MUNICIPALITY]
            else:
                return self.async_create_entry(
                    title=self._alert_zone.name,
                    data=self._place,
                    options={CONF_MUNICIPALITY: municipality},
                )

        return self.async_show_form(
            step_id="municipality",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MUNICIPALITY): municipality_selector(
                        self._alert_zone.municipalities
                    )
                }
            ),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def _async_set_place(
        self, latitude: float, longitude: float
    ) -> dict[str, str]:
        """Check a place with DPC and keep it; return the errors, if any.

        Aborts the flow when the place is already configured.
        """
        latitude, longitude = round(latitude, 6), round(longitude, 6)
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
            CONF_NAME: self._alert_zone.name,
            CONF_LATITUDE: latitude,
            CONF_LONGITUDE: longitude,
        }
        return {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> DpcOptionsFlowHandler:
        """Return the options flow of a place."""
        return DpcOptionsFlowHandler()


class DpcOptionsFlowHandler(config_entries.OptionsFlow):
    """Options of a place."""

    def __init__(self) -> None:
        """Initialize the options flow."""
        self._municipalities: tuple[str, ...] | None = None
        """Municipalities of the alert zone of the place; None when unknown."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Fetch the municipalities of the alert zone, then show the options."""
        try:
            alert_zone = await async_get_alert_zone(
                self.hass,
                self.config_entry.data[CONF_LATITUDE],
                self.config_entry.data[CONF_LONGITUDE],
            )
        except DpcError as err:
            LOGGER.debug("No municipalities to offer, any can be typed: %s", err)
        else:
            self._municipalities = alert_zone.municipalities
        return await self.async_step_user()

    def _municipality(self, typed: str) -> str | None:
        """Return a typed municipality as DPC lists it, or None if not listed.

        When the list could not be fetched, any name is accepted as typed.
        """
        if not municipality_names(typed):
            return None
        if self._municipalities is None:
            return typed.strip()
        return listed_municipality(self._municipalities, typed)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and save the options of the place."""
        options = dict(self.config_entry.options)
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        if user_input is not None:
            municipality = self._municipality(user_input[CONF_MUNICIPALITY])
            if municipality is None:
                errors[CONF_MUNICIPALITY] = "municipality_not_listed"
            elif (
                other := place_with_municipality(
                    self.hass, municipality, other_than=self.config_entry.entry_id
                )
            ) is not None:
                errors[CONF_MUNICIPALITY] = "municipality_in_use"
                placeholders["municipality"] = other.options[CONF_MUNICIPALITY]
            else:
                return self.async_create_entry(
                    data=options | user_input | {CONF_MUNICIPALITY: municipality}
                )
            # Show the options as entered
            options |= user_input

        municipality = options.get(CONF_MUNICIPALITY) or ""
        schema: dict[vol.Marker, Any] = {
            vol.Required(platform, default=options.get(platform, True)): bool
            for platform in sorted(PLATFORMS)
        }
        schema |= {
            vol.Required(
                CONF_MUNICIPALITY, description={"suggested_value": municipality}
            ): municipality_selector(self._municipalities or (), municipality),
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
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders=placeholders,
        )
