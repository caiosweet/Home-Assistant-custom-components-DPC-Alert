"""Constants for Dpc."""

from collections.abc import Mapping
from datetime import timedelta
from enum import StrEnum
import logging
from typing import Final

from aiodpc import AlertLevel, Precipitation, RiskType
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

RETRY_INTERVAL: Final = timedelta(minutes=10)
"""Interval of the next update after a bulletin could not be fetched."""

LATEST_ID_CHECK_INTERVAL: Final = 60.0
"""Seconds during which the places share a check of the latest bulletin ID."""

WARNING_LEVELS: Final = [
    level.value for level in AlertLevel if level is not AlertLevel.UNKNOWN
]
"""Warning levels offered in the options: 1 green, 2 yellow, 3 orange, 4 red."""

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

# The values below are attributes of the binary sensors as they have always been,
# in Italian as DPC writes them, so automations and templates keep working.

ALERT_TEXTS: Final[Mapping[AlertLevel, str]] = {
    AlertLevel.UNKNOWN: "",
    AlertLevel.GREEN: "NESSUNA ALLERTA",
    AlertLevel.YELLOW: "ALLERTA GIALLA",
    AlertLevel.ORANGE: "ALLERTA ARANCIONE",
    AlertLevel.RED: "ALLERTA ROSSA",
}

RISK_NAMES: Final[Mapping[RiskType, str]] = {
    RiskType.HYDRAULIC: "Idraulico",
    RiskType.THUNDERSTORMS: "Temporali",
    RiskType.HYDROGEOLOGICAL: "Idrogeologico",
}

ATTR_ALERT = "alert"
ATTR_ID = "id"
ATTR_EXPIRES = "expires"
ATTR_IMAGE_URL = "image_url"
ATTR_INFO = "info"
ATTR_LAST_UPDATE = "last_update"
ATTR_LEVEL = "level"
ATTR_LINK = "link"
ATTR_MAX_LEVEL = "max_level"
ATTR_PUBLICATION_DATE = "publication_date"
ATTR_RISK = "risk"
ATTR_TOTAL_ALERTS = "total_alerts"
ATTR_TOTAL_PHENOMENA = "total_phenomena"
ATTR_ZONE_NAME = "zone_name"

# The states and attributes of the day sensors, map images and phenomena use
# the values of aiodpc instead: English names that Home Assistant translates.

ATTR_DAY = "day"
ATTR_DESCRIPTION = "description"
ATTR_DIRECTION = "direction"
ATTR_PHENOMENON = "phenomenon"
ATTR_RISKS = "risks"
ATTR_VALID_UNTIL = "valid_until"

ALERT_LEVEL_STATES: Final = [
    str(level) for level in AlertLevel if level is not AlertLevel.UNKNOWN
]
"""States of the alert sensor of a day: green, yellow, orange, red."""

PRECIPITATION_STATES: Final = [
    str(amount) for amount in Precipitation if amount is not Precipitation.UNKNOWN
]
"""States of the precipitation sensor of a day: none, light, ... very_heavy."""

DASHBOARD_MODULE_URL: Final = f"/{DOMAIN}/frontend/dpc-dashboard.js"
"""URL of the DPC Alert dashboard strategy, loaded by the frontend of every user."""
