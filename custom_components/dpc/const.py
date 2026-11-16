"""Constants for Dpc."""

from collections.abc import Iterable, Mapping
from datetime import timedelta
from enum import StrEnum
import logging
from typing import Any, Final

from aiodpc import AlertLevel, Criticality, Day, Precipitation, RiskType
from homeassistant.const import Platform

from .version import __version__

VERSION: Final = __version__
"""Version of the integration: the release tag, written by the release workflow."""

LOGGER = logging.getLogger(__package__)
PLATFORMS: Final[list[str]] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.IMAGE,
    Platform.GEO_LOCATION,
]

# Base component constants
DOMAIN = "dpc"
ISSUE_URL = (
    "https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues"
)
NAME = "Dipartimento Protezione Civile"
MANUFACTURER = "Italian Government"

# Config
CONF_DAYS: Final = "days"
CONF_MUNICIPALITY = "municipality"
CONF_WARNING_LEVEL = "warning_level"


class PlaceDay(StrEnum):
    """A day of the bulletins that a place shows, as its options name it.

    The values are the keys the integration has always given the days, in the
    data of the coordinator and in the unique IDs of the entities of each day
    (``aftertomorrow`` in one word).
    """

    TODAY = "today"
    TOMORROW = "tomorrow"
    AFTER_TOMORROW = "aftertomorrow"

    @property
    def day(self) -> Day:
        """Return the day as aiodpc names it."""
        return Day[self.name]

    @property
    def object_id(self) -> str:
        """Return the day in entity IDs: today, tomorrow or after_tomorrow."""
        return self.name.lower()


# Defaults
DEFAULT_NAME = "DPC"
DEFAULT_WARNING_LEVEL = AlertLevel.YELLOW.value
DEFAULT_RADIUS = 50  # Km
DEFAULT_SCAN_INTERVAL = 30  # min

DEFAULT_DAYS: Final = [PlaceDay.TODAY]
"""Days a new place shows: today. The options add the others."""

DAYS_BEFORE_THE_OPTION: Final = [PlaceDay.TODAY, PlaceDay.TOMORROW]
"""Days of the places added before the days option.

2026.11.0 had the binary sensors of the risks of today and tomorrow.
"""

SAME_MUNICIPALITY_KM: Final = 80.0
"""Distance within which two places with the same municipality name share it.

A few municipalities have the same name, far apart: Peglio is in Lombardy and
in the Marche. Two places in Rome, the largest municipality, are less than
60 km apart, while the nearest homonyms, the two Livo, are about 130 km apart.
"""

VIA_DEVICE_ID_VERSION: Final = (2026, 8)
"""First Home Assistant version whose devices link to their parent by its ID.

Home Assistant 2026.8 added ``via_device_id`` to the device info and
deprecated ``via_device``, the identifier of the parent: 2026.10 no longer
declares it, and 2027.8 removes it. Before 2026.8, only ``via_device`` exists.
"""

RETRY_INTERVAL: Final = timedelta(minutes=10)
"""Interval of the next update after a bulletin could not be fetched."""

LATEST_ID_CHECK_INTERVAL: Final = 60.0
"""Seconds during which the places share a check of the latest bulletin ID."""

WARNING_LEVELS: Final = [level.value for level in AlertLevel if level.is_alert]
"""Warning levels offered in the options: 2 yellow, 3 orange, 4 red.

Green, no alert, would turn the binary sensors on all the time; places that
chose it before keep it, until they choose another level.
"""

PLATFORMS_OFF_BY_DEFAULT: Final = frozenset({Platform.GEO_LOCATION})
"""Kinds of entities a place shows only when its options turn them on: the
phenomena, many entities that come and go with every bulletin."""


def platform_shown(options: Mapping[str, Any], platform: str) -> bool:
    """Return whether a place shows a kind of entities, by its options."""
    shown: bool = options.get(platform, platform not in PLATFORMS_OFF_BY_DEFAULT)
    return shown


PLATFORM_DAYS: Final[Mapping[str, frozenset[PlaceDay]]] = {
    Platform.BINARY_SENSOR: frozenset({PlaceDay.TODAY, PlaceDay.TOMORROW}),
    Platform.IMAGE: frozenset({PlaceDay.TODAY, PlaceDay.TOMORROW}),
    Platform.GEO_LOCATION: frozenset(PlaceDay),
    Platform.SENSOR: frozenset(PlaceDay),
}
"""The days that have entities of each kind: the risks and the maps only today
and tomorrow, as only the vigilance bulletin covers the day after tomorrow and
DPC publishes no map of it; the phenomena and the sensors every day."""

PLATFORMS_OF_THE_PLACE: Final = frozenset({Platform.SENSOR})
"""Kinds of entities the place has without days: its highest alert and
precipitation, its zones and its bulletins."""


def shows_entities(days: Iterable[str], platforms: Iterable[str]) -> bool:
    """Return whether a place with these days and kinds of entities has any.

    Without one, a place would be a device without entities, which shows
    nothing: the setup and the options do not accept it.
    """
    chosen_days = set(days)
    return any(
        platform in PLATFORMS_OF_THE_PLACE
        or not chosen_days.isdisjoint(PLATFORM_DAYS[platform])
        for platform in platforms
    )


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

# The attributes left: what is not an entity of its own. States and values are
# the English keys of aiodpc, which Home Assistant translates.

ATTR_DIRECTION = "direction"
ATTR_ID = "id"
ATTR_IMAGE_URL = "image_url"
ATTR_LAST_CHECK = "last_check"
ATTR_LINK = "link"
ATTR_PHENOMENON = "phenomenon"
ATTR_RISKS = "risks"
ATTR_TOTAL_ALERTS = "total_alerts"

RISK_TRANSLATION_KEYS: Final[Mapping[RiskType, str]] = {
    RiskType.HYDRAULIC: "hydraulic_risk",
    RiskType.THUNDERSTORMS: "thunderstorm_risk",
    RiskType.HYDROGEOLOGICAL: "hydrogeological_risk",
}
"""Translation key of the binary sensor of each risk; its level adds ``_level``."""

ALERT_LEVEL_STATES: Final = [
    str(level) for level in AlertLevel if level is not AlertLevel.UNKNOWN
]
"""States of the alert levels of a day: green, yellow, orange, red."""

PRECIPITATION_STATES: Final = [
    str(amount) for amount in Precipitation if amount is not Precipitation.UNKNOWN
]
"""States of the precipitation of a day: none, light, ... very_heavy."""

HIGHEST_ALERT_STATES: Final = [
    str(level.code) for level in AlertLevel if level is not AlertLevel.UNKNOWN
]
"""States of the highest alert of a place: its numbers, 1 green to 4 red.

Numbers, as the sensor has always had, so that automations comparing them
keep working; Home Assistant shows the texts of the levels.
"""

HIGHEST_PRECIPITATION_STATES: Final = [
    str(amount.code) for amount in Precipitation if amount is not Precipitation.UNKNOWN
]
"""States of the highest precipitation of a place: 1 none to 5 very heavy."""

CRITICALITY_STATES: Final = [
    str(Criticality.ABSENT),
    *(
        f"{criticality}_{risk}"
        for criticality in (
            Criticality.ORDINARY,
            Criticality.MODERATE,
            Criticality.HIGH,
        )
        for risk in RiskType
    ),
]
"""States of the criticality of a day: absent, or a criticality and the risk the
DPC map shows, e.g. moderate_hydrogeological."""

FRONTEND_URL: Final = f"/{DOMAIN}/frontend/{VERSION}"
"""URL of the modules of the frontend, loaded by the frontend of every user.

The browsers keep the modules in their cache: the version in the path makes
them load the modules again when the integration is updated, and the card
imports the dashboard strategy by a relative path, which keeps the version.
"""

FRONTEND_MODULES: Final = ("dpc-dashboard.js", "dpc-card.js")
"""The modules of the frontend: the dashboard strategy and the card."""
