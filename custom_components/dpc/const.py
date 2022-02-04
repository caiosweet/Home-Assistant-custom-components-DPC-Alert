"""Constants for Dpc."""
import logging

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN

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
VERSION = "2022.2.0"

# Config
CONF_WARNING_LEVEL = "warning_level"

# Defaults
DEFAULT_NAME = "DPC"
DEFAULT_WARNING_LEVEL = 2
DEFAULT_RADIUS = 50  # Km
DEFAULT_SCAN_INTERVAL = 30  # min

WARNING_ALERT = {
    "": 0,
    "NESSUNA ALLERTA": 1,
    "ALLERTA GIALLA": 2,
    "ALLERTA ARANCIONE": 3,
    "ALLERTA ROSSA": 4,
}


WARNING_TYPES = [
    "idraulico_oggi",
    "temporali_oggi",
    "idrogeologico_oggi",
    "idraulico_domani",
    "temporali_domani",
    "idrogeologico_domani",
]

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

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
