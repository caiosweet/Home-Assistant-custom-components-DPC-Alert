"""Constants for Dpc."""

from collections.abc import Mapping
from datetime import timedelta
import logging
from typing import Final

from aiodpc import AlertLevel, PhenomenonCategory, Precipitation, RiskType
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN

try:
    from .version import __version__ as VERSION
except ImportError:
    VERSION = "0.0.0"

LOGGER = logging.getLogger(__package__)
PLATFORMS = [BINARY_SENSOR_DOMAIN, SENSOR_DOMAIN]

# Base component constants
ATTRIBUTION = "Data provided by Civil Protection Department"
DOMAIN = "dpc"
ISSUE_URL = (
    "https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert/issues"
)
NAME = "Dipartimento Protezione Civile"
MANUFACTURER = "Italian Government"

# Config
CONF_MUNICIPALITY = "municipality"
CONF_WARNING_LEVEL = "warning_level"

# Defaults
DEFAULT_NAME = "DPC"
DEFAULT_WARNING_LEVEL = AlertLevel.YELLOW.value
DEFAULT_RADIUS = 50  # Km
DEFAULT_SCAN_INTERVAL = 30  # min

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

# The values below are the entity attributes as the integration has always shown
# them, mostly in Italian as DPC writes them, so automations and templates keep working.

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

RISK_ICONS: Final[Mapping[RiskType, str]] = {
    RiskType.HYDRAULIC: "mdi:home-flood",
    RiskType.THUNDERSTORMS: "mdi:weather-lightning",
    RiskType.HYDROGEOLOGICAL: "mdi:waves",
}

PRECIPITATION_TEXTS: Final[Mapping[Precipitation, str | None]] = {
    Precipitation.UNKNOWN: None,
    Precipitation.NONE: "Assenti o non rilevanti",
    Precipitation.LIGHT: "Deboli",
    Precipitation.MODERATE: "Moderati",
    Precipitation.HEAVY: "Elevati",
    Precipitation.VERY_HEAVY: "Molto elevati",
}

PRECIPITATION_ICONS: Final[Mapping[Precipitation, str | None]] = {
    Precipitation.UNKNOWN: None,
    Precipitation.NONE: "mdi:numeric-1-circle",
    Precipitation.LIGHT: "mdi:numeric-2-circle",
    Precipitation.MODERATE: "mdi:numeric-3-circle",
    Precipitation.HEAVY: "mdi:numeric-4-circle",
    Precipitation.VERY_HEAVY: "mdi:numeric-5-circle",
}

PHENOMENON_CATEGORY_NAMES: Final[Mapping[PhenomenonCategory, str]] = {
    PhenomenonCategory.PRECIPITATION: "Precipitazioni",
    PhenomenonCategory.WIND: "Venti",
    PhenomenonCategory.FROST: "Gelate",
    PhenomenonCategory.FOG: "Nebbie",
    PhenomenonCategory.SEA: "Mari",
    PhenomenonCategory.WAVE_MOTION: "Moto_ondoso",
    PhenomenonCategory.TEMPERATURE: "Temperature",
}

DEFAULT_PHENOMENON_ICON = "mdi:hazard-lights"
PHENOMENON_ICONS: Final[Mapping[int, str]] = {
    1: "mdi:water",
    2: "mdi:water-plus",
    3: "mdi:snowflake",
    4: "mdi:snowflake-alert",
    5: "mdi:lightning-bolt",
    6: "mdi:flash",
    7: "mdi:flash-alert",
    10: "mdi:weather-windy-variant",
    11: "mdi:weather-windy",
    12: "mdi:windsock",
    13: "mdi:wind-turbine",
    20: "mdi:image-filter-hdr",
    21: "mdi:snowflake-variant",
    30: "mdi:weather-fog",
    31: "mdi:weather-hazy",
    40: "mdi:waves",
    41: "mdi:waves",
    42: "mdi:hydro-power",
    50: "mdi:arrow-up-thick",
    51: "mdi:arrow-down-thick",
    60: "mdi:thermometer-chevron-up",
    61: "mdi:thermometer-plus",
    62: "mdi:thermometer-chevron-down",
    63: "mdi:thermometer-minus",
}
"""Icons of the DPC phenomenon codes (``id_fenomeno``)."""

ATTR_AFTERTOMORROW = "aftertomorrow"
ATTR_ALERT = "alert"
ATTR_ID = "id"
ATTR_EXPIRES = "expires"
ATTR_EVENTS_TODAY = "events_today"
ATTR_EVENTS_TOMORROW = "events_tomorrow"
ATTR_IMAGE_URL = "image_url"
ATTR_INFO = "info"
ATTR_LAST_UPDATE = "last_update"
ATTR_LEVEL = "level"
ATTR_LINK = "link"
ATTR_MAX_LEVEL = "max_level"
ATTR_PHENOMENA = "phenomena"
ATTR_PRECIPITATION = "precipitation"
ATTR_PUBLICATION_DATE = "publication_date"
ATTR_RISK = "risk"
ATTR_TODAY = "today"
ATTR_TOMORROW = "tomorrow"
ATTR_TOTAL_ALERTS = "total_alerts"
ATTR_TOTAL_PHENOMENA = "total_phenomena"
ATTR_ZONE_NAME = "zone_name"
