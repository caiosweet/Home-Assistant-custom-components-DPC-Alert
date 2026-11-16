"""Config flow for Dpc: the place to monitor, on a map or from a zone."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from aiodpc import AlertZone, DpcClient, DpcError, DpcLocationError, Location
from aiodpc.geo import distance_km
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
    CONF_DAYS,
    CONF_MUNICIPALITY,
    CONF_WARNING_LEVEL,
    DEFAULT_DAYS,
    DEFAULT_RADIUS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WARNING_LEVEL,
    DOMAIN,
    LOGGER,
    PLATFORMS,
    SAME_MUNICIPALITY_KM,
    WARNING_LEVELS,
    PlaceDay,
    platform_shown,
)

ZONE_DOMAIN = "zone"
HOME_ZONE = "zone.home"

CONF_ENTITIES = "entities"
"""The field of the kinds of entities a place shows. Each kind is kept as the
option of its platform (``binary_sensor: true``), as it has always been."""


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


def coordinates(place: Mapping[str, Any]) -> tuple[float, float]:
    """Return the (latitude, longitude) of the data of a place."""
    return place[CONF_LATITUDE], place[CONF_LONGITUDE]


def place_with_municipality(
    hass: HomeAssistant,
    municipality: str,
    *,
    at: tuple[float, float],
    other_than: str | None = None,
) -> config_entries.ConfigEntry | None:
    """Return the place that already has the municipality of a place, if any.

    The municipality identifies a place: two places with the same municipality
    would get the same bulletins. Any name of it counts: "Bozen" is
    "Bolzano/Bozen". A place far away has another municipality of the same
    name, such as the Peglio of the Marche for a place in Lombardy (see
    :data:`SAME_MUNICIPALITY_KM`).
    """
    names = municipality_names(municipality)
    return next(
        (
            entry
            for entry in hass.config_entries.async_entries(DOMAIN, include_ignore=False)
            if entry.entry_id != other_than
            and names & municipality_names(entry.options.get(CONF_MUNICIPALITY) or "")
            and distance_km(at, coordinates(entry.data)) <= SAME_MUNICIPALITY_KM
        ),
        None,
    )


def display_schema(options: Mapping[str, Any]) -> vol.Schema:
    """Return the form of what a place shows: its days and kinds of entities."""
    return vol.Schema(
        {
            # No day is a choice too: the place keeps its own entities
            vol.Required(
                CONF_DAYS, default=list(options.get(CONF_DAYS, DEFAULT_DAYS))
            ): SelectSelector(
                SelectSelectorConfig(
                    options=list(PlaceDay),
                    multiple=True,
                    translation_key=CONF_DAYS,
                    mode=SelectSelectorMode.LIST,
                )
            ),
            vol.Required(
                CONF_ENTITIES,
                default=[
                    platform
                    for platform in sorted(PLATFORMS)
                    if platform_shown(options, platform)
                ],
            ): SelectSelector(
                SelectSelectorConfig(
                    options=sorted(PLATFORMS),
                    multiple=True,
                    translation_key=CONF_ENTITIES,
                    mode=SelectSelectorMode.LIST,
                )
            ),
        }
    )


def display_options(user_input: Mapping[str, Any]) -> dict[str, Any]:
    """Return the options of what a place shows, from its form."""
    shown = user_input[CONF_ENTITIES]
    return {
        CONF_DAYS: user_input[CONF_DAYS],
        **{platform: platform in shown for platform in PLATFORMS},
    }


def alerts_schema(options: Mapping[str, Any]) -> vol.Schema:
    """Return the form of the alerts of a place: their level, radius and updates."""
    level = options.get(CONF_WARNING_LEVEL, DEFAULT_WARNING_LEVEL)
    return vol.Schema(
        {
            vol.Required(
                CONF_WARNING_LEVEL,
                # A level no longer offered (green) starts from the default
                default=str(
                    level if level in WARNING_LEVELS else DEFAULT_WARNING_LEVEL
                ),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[str(level) for level in WARNING_LEVELS],
                    translation_key=CONF_WARNING_LEVEL,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_RADIUS, default=options.get(CONF_RADIUS, DEFAULT_RADIUS)
            ): vol.All(vol.Coerce(float), vol.Range(min=0)),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): cv.positive_int,
        }
    )


def alerts_options(user_input: Mapping[str, Any]) -> dict[str, Any]:
    """Return the options of the alerts of a place, from its form.

    The warning level is kept as a number, as it has always been.
    """
    return {**user_input, CONF_WARNING_LEVEL: int(user_input[CONF_WARNING_LEVEL])}


class DpcFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Dpc: a place and its municipality.

    The place is named after its DPC alert zone, and its municipality, one of
    the zone, identifies it.
    """

    VERSION = 2
    # A change that older versions of the integration can still load bumps the
    # minor version: since Home Assistant 2026.7, an entry of a higher major
    # version fails to load, so going back to an older release would break it.
    # 2: the days of the place (CONF_DAYS).
    MINOR_VERSION = 2

    def __init__(self) -> None:
        """Initialize the flow."""
        self._place: dict[str, Any] = {}
        self._alert_zone: AlertZone | None = None
        self._options: dict[str, Any] = {}
        """The options chosen so far, step after step."""

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
            last_step=False,
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
            last_step=False,
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
                other := place_with_municipality(
                    self.hass, municipality, at=coordinates(self._place)
                )
            ) is not None:
                errors[CONF_MUNICIPALITY] = "municipality_in_use"
                placeholders["municipality"] = other.options[CONF_MUNICIPALITY]
            else:
                self._options = {CONF_MUNICIPALITY: municipality}
                return await self.async_step_display()

        return self.async_show_form(
            step_id="municipality",
            last_step=False,
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

    async def async_step_display(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose what the place shows: its days and kinds of entities."""
        if user_input is not None:
            self._options |= display_options(user_input)
            return await self.async_step_alerts()
        return self.async_show_form(
            step_id="display", data_schema=display_schema({}), last_step=False
        )

    async def async_step_alerts(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the warning level, the radius of the phenomena and the updates."""
        assert self._alert_zone is not None
        if user_input is not None:
            return self.async_create_entry(
                title=self._alert_zone.name,
                data=self._place,
                options=self._options | alerts_options(user_input),
            )
        return self.async_show_form(
            step_id="alerts", data_schema=alerts_schema({}), last_step=True
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
    """Options of a place: a menu of the steps of its setup, each saved on its own.

    The municipality, what the place shows, and its alerts: the user goes to the
    one to change, with no need to go back.
    """

    def __init__(self) -> None:
        """Initialize the options flow."""
        self._municipalities: tuple[str, ...] | None = None
        """Municipalities of the alert zone of the place; None when unknown."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show what can be changed."""
        return self.async_show_menu(
            step_id="init", menu_options=["place", "display", "alerts"]
        )

    def _saved(self, options: Mapping[str, Any]) -> ConfigFlowResult:
        """Save the options of a step with the others of the place."""
        return self.async_create_entry(data={**self.config_entry.options, **options})

    def _municipality(self, typed: str) -> str | None:
        """Return a typed municipality as DPC lists it, or None if not listed.

        When the list could not be fetched, any name is accepted as typed.
        """
        if not municipality_names(typed):
            return None
        if self._municipalities is None:
            return typed.strip()
        return listed_municipality(self._municipalities, typed)

    async def async_step_place(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the municipality of the place, among those of its alert zone."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        typed = self.config_entry.options.get(CONF_MUNICIPALITY) or ""
        if user_input is None:
            try:
                alert_zone = await async_get_alert_zone(
                    self.hass, *coordinates(self.config_entry.data)
                )
            except DpcError as err:
                LOGGER.debug("No municipalities to offer, any can be typed: %s", err)
            else:
                self._municipalities = alert_zone.municipalities
        else:
            typed = user_input[CONF_MUNICIPALITY]
            municipality = self._municipality(typed)
            if municipality is None:
                errors[CONF_MUNICIPALITY] = "municipality_not_listed"
            elif (
                other := place_with_municipality(
                    self.hass,
                    municipality,
                    at=coordinates(self.config_entry.data),
                    other_than=self.config_entry.entry_id,
                )
            ) is not None:
                errors[CONF_MUNICIPALITY] = "municipality_in_use"
                placeholders["municipality"] = other.options[CONF_MUNICIPALITY]
            else:
                return self._saved({CONF_MUNICIPALITY: municipality})

        return self.async_show_form(
            step_id="place",
            data_schema=vol.Schema(
                {
                    # Shown as entered, after an error
                    vol.Required(
                        CONF_MUNICIPALITY, description={"suggested_value": typed}
                    ): municipality_selector(self._municipalities or (), typed),
                }
            ),
            errors=errors,
            description_placeholders=placeholders,
            last_step=True,
        )

    async def async_step_display(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose what the place shows: its days and kinds of entities."""
        if user_input is not None:
            return self._saved(display_options(user_input))
        return self.async_show_form(
            step_id="display",
            data_schema=display_schema(self.config_entry.options),
            last_step=True,
        )

    async def async_step_alerts(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the warning level, the radius of the phenomena and the updates."""
        if user_input is not None:
            return self._saved(alerts_options(user_input))
        return self.async_show_form(
            step_id="alerts",
            data_schema=alerts_schema(self.config_entry.options),
            last_step=True,
        )
