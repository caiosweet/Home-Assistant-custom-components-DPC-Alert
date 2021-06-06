"""Binary Sensor for Dipartimento della Protezione Civile Meteo-Hydro Alert"""

import datetime
import logging
import re

import requests
import voluptuous as vol
from bs4 import BeautifulSoup
from geojson_utils import point_in_polygon
from homeassistant.components.binary_sensor import (
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA,
)

try:
    from homeassistant.components.binary_sensor import BinarySensorEntity
except ImportError:
    from homeassistant.components.binary_sensor import (
        BinarySensorDevice as BinarySensorEntity,
    )
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
)
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.util import Throttle

from .const import (
    ATTRIBUTION,
    BASE_URL,
    BULLETTIN_URL,
    CONF_ALERT,
    CONF_ISTAT,
    CONF_WARNINGS,
    DEFAULT_DEVICE_CLASS,
    DEFAULT_NAME,
    ISSUES_RESOURCE_URL,
    WARNING_ALERT,
    WARNING_TYPES,
)

DEFAULT_SCAN_INTERVAL = datetime.timedelta(minutes=30)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_LATITUDE): cv.string,
        vol.Optional(CONF_LONGITUDE): cv.string,
        vol.Required(CONF_ISTAT): cv.string,
        vol.Optional(CONF_ALERT, default="GIALLA"): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_WARNINGS, default=[]): vol.All(
            cv.ensure_list, [vol.In(WARNING_TYPES)]
        ),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
    }
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup."""
    _LOGGER.debug("[%s] start async setup platform", DEFAULT_NAME)
    name = config.get(CONF_NAME)
    latitude = round(float(config.get(CONF_LATITUDE, hass.config.latitude)), 2)
    longitude = round(float(config.get(CONF_LONGITUDE, hass.config.longitude)), 2)
    warnings = config.get(CONF_WARNINGS)
    istat = str(config.get(CONF_ISTAT)).zfill(6)
    alert = config.get(CONF_ALERT)
    scan_interval = config.get(CONF_SCAN_INTERVAL)
    sensors = []
    updater = dpcUpdater(hass, longitude, latitude, istat, scan_interval, warnings)
    await updater.async_update()
    for warning_type in warnings:
        uid = f"{name}_{warning_type}"
        entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, uid, hass=hass)
        sensors.append(dpcSensor(entity_id, name, updater, warning_type, alert))
    async_add_entities(sensors, True)

class dpcSensor(BinarySensorEntity):
    """Binary sensor representing Meteo-Hydro Alert data."""

    def __init__(self, entity_id, name, updater, warning_type, alert):
        """Initialize dpc binary sensor."""
        self.entity_id = entity_id
        self._name = name
        self._updater = updater
        self._data = None
        self._warning_type = warning_type
        self._warning_key = WARNING_TYPES[self._warning_type][0]
        self._alert = WARNING_ALERT.get(alert.upper())
    @property
    def is_on(self):
        try:
            data = self._updater.dpc_output[self._warning_key]
            prevision_date = data["date"]
            _LOGGER.debug("bulletin date (publication date): %s %s %s", prevision_date, self._name, self.entity_id)
        except KeyError:
            _LOGGER.error("Entity: %s %s", self._name, self.entity_id)
            return False
        return (
            data is not None
            and WARNING_ALERT.get(data["alert"]) >= self._alert
            # and prevision_date.date() >= datetime.date.today()
        )
    @property
    def device_state_attributes(self):
        """Return attrubutes."""
        output = dict()
        if self._updater.dpc_id:
            output["id"] = self._updater.dpc_id
        output["link"] = BULLETTIN_URL
        output[ATTR_ATTRIBUTION] = ATTRIBUTION
        if self.is_on:
            data = self._updater.dpc_output[self._warning_key]
            output["data"] = data["date"]
            output["rischio"] = data["risk"].capitalize()
            output["info"] = data["info"]
            output["allerta"] = data["alert"]
            output["zona_info"] = data["civil_protection_zone_info"]
            output["level"] = WARNING_ALERT.get(data["alert"])
            # output["id"] = data["dpc_id"]
        return output
    @property
    def device_class(self):
        """Return device_class."""
        return DEFAULT_DEVICE_CLASS
    @property
    def icon(self):
        """Return icon."""
        return WARNING_TYPES[self._warning_type][2]
    @property
    def name(self):
        """Return name."""
        return WARNING_TYPES[self._warning_type][1]
    async def async_update(self):
        """Update data."""
        await self._updater.async_update()

class dpcUpdater:
    """fetch all data."""

    def __init__(self, hass, longitude, latitude, istat, scan_interval, warnings):
        self._hass = hass
        self._longitude = longitude
        self._latitude = latitude
        self._istat = istat
        self._warnings = warnings
        self.dpc_output = None
        self.dpc_id = None
        self.prevision_data = None
        self.async_update = Throttle(scan_interval)(self.async_update)
    async def async_update(self):
        dpc_data_pub = await self._hass.async_add_executor_job(self.dpc_id_pub)
        _LOGGER.debug("[%s] Data published: %s", DEFAULT_NAME, dpc_data_pub)
        self.dpc_output = await self._hass.async_add_executor_job(self.fetch_all)
        _LOGGER.debug("[%s] ASYNC UPDATE: %s", DEFAULT_NAME, self.dpc_output)
    def dpc_id_pub(self):
        try:
            req = requests.get(BULLETTIN_URL)
            soup = BeautifulSoup(req.text, "html.parser")
            for link in soup.find_all(href=re.compile("shp\.zip$")):
                id_pub = re.findall("[0-9]+_[0-9]+", link.get("href"))
                if id_pub:
                    self.dpc_id = id_pub[0]  # string
                    date_time_str = self.dpc_id
                    date_time_obj = datetime.datetime.strptime(
                        date_time_str, "%Y%m%d_%H%M"
                    )
                    self.prevision_data = date_time_obj
                _LOGGER.debug(
                    "[%s] Shape Link: %s - ID: %s", DEFAULT_NAME, link, self.dpc_id
                )
            return id_pub
        except:
            _LOGGER.debug("[%s] Failed DPC ID: %s ", DEFAULT_NAME, self.dpc_id)
    def fetch_all(self):
        """Launch requests for all url."""
        dpc_id = self.dpc_id
        prevision_data = self.prevision_data

        url_today = BASE_URL.format(dpc_id, "today")
        url_tomorrow = BASE_URL.format(dpc_id, "tomorrow")

        r_today = requests.get(url_today)
        r_tomorrow = requests.get(url_tomorrow)

        js_today = r_today.json()
        js_tomorrow = r_tomorrow.json()

        point = {"type": "Point", "coordinates": [self._longitude, self._latitude]}

        default_data = {"dpc_id": dpc_id, "link": BULLETTIN_URL}
        data = {}
        formatted_datetime = prevision_data

        # check each polygon to see if it contains the point
        for feature in js_today["features"]:
            polygon = feature["geometry"]
            properties = feature["properties"]
            if point_in_polygon(point, polygon):
                if datetime.date.today() == prevision_data.date():
                    data["idraulico_oggi"] = {
                        "date": formatted_datetime,
                        "risk": "idraulico",
                        "info": properties["Per rischio idraulico"]
                        .split("/")[0]
                        .rstrip()
                        .lstrip(),
                        "alert": properties["Per rischio idraulico"]
                        .split("/")[1]
                        .replace("ALLERTA", "")
                        .replace("NESSUNA", "VERDE")
                        .rstrip()
                        .lstrip(),
                        "link": BULLETTIN_URL,
                        "dpc_id": dpc_id,
                        "civil_protection_zone_info": properties["Nome zona"],
                    }
                    data["temporali_oggi"] = {
                        "date": formatted_datetime,
                        "risk": "temporali",
                        "info": properties["Per rischio temporali"]
                        .split("/")[0]
                        .rstrip()
                        .lstrip(),
                        "alert": properties["Per rischio temporali"]
                        .split("/")[1]
                        .replace("ALLERTA", "")
                        .replace("NESSUNA", "VERDE")
                        .rstrip()
                        .lstrip(),
                        "link": BULLETTIN_URL,
                        "dpc_id": dpc_id,
                        "civil_protection_zone_info": properties["Nome zona"],
                    }
                    data["idrogeologico_oggi"] = {
                        "date": formatted_datetime,
                        "risk": "idrogeologico",
                        "info": properties["Per rischio idrogeologico"]
                        .split("/")[0]
                        .rstrip()
                        .lstrip(),
                        "alert": properties["Per rischio idrogeologico"]
                        .split("/")[1]
                        .replace("ALLERTA", "")
                        .replace("NESSUNA", "VERDE")
                        .rstrip()
                        .lstrip(),
                        "link": BULLETTIN_URL,
                        "dpc_id": dpc_id,
                        "civil_protection_zone_info": properties["Nome zona"],
                    }
                else:
                    data["idraulico_domani"] = default_data
                    data["temporali_domani"] = default_data
                    data["idrogeologico_domani"] = default_data
        for feature in js_tomorrow["features"]:
            polygon = feature["geometry"]
            properties = feature["properties"]
            if point_in_polygon(point, polygon):
                day = ""
                if datetime.date.today() < (
                    prevision_data.date() + datetime.timedelta(days=1)
                ):
                    day = "_domani"
                elif datetime.date.today() >= (
                    prevision_data.date() + datetime.timedelta(days=2)
                ):
                    data["idraulico_oggi"] = default_data
                    data["temporali_oggi"] = default_data
                    data["idrogeologico_oggi"] = default_data
                else:
                    day = "_oggi"
                data["idraulico" + day] = {
                    "date": formatted_datetime,
                    "risk": "idraulico",
                    "info": properties["Per rischio idraulico"]
                    .split("/")[0]
                    .rstrip()
                    .lstrip(),
                    "alert": properties["Per rischio idraulico"]
                    .split("/")[1]
                    .replace("ALLERTA", "")
                    .replace("NESSUNA", "VERDE")
                    .rstrip()
                    .lstrip(),
                    "link": BULLETTIN_URL,
                    "dpc_id": dpc_id,
                    "civil_protection_zone_info": properties["Nome zona"],
                }
                data["temporali" + day] = {
                    "date": formatted_datetime,
                    "risk": "temporali",
                    "info": properties["Per rischio temporali"]
                    .split("/")[0]
                    .rstrip()
                    .lstrip(),
                    "alert": properties["Per rischio temporali"]
                    .split("/")[1]
                    .replace("ALLERTA", "")
                    .replace("NESSUNA", "VERDE")
                    .rstrip()
                    .lstrip(),
                    "link": BULLETTIN_URL,
                    "dpc_id": dpc_id,
                    "civil_protection_zone_info": properties["Nome zona"],
                }
                data["idrogeologico" + day] = {
                    "date": formatted_datetime,
                    "risk": "idrogeologico",
                    "info": properties["Per rischio idrogeologico"]
                    .split("/")[0]
                    .rstrip()
                    .lstrip(),
                    "alert": properties["Per rischio idrogeologico"]
                    .split("/")[1]
                    .replace("ALLERTA", "")
                    .replace("NESSUNA", "VERDE")
                    .rstrip()
                    .lstrip(),
                    "link": BULLETTIN_URL,
                    "dpc_id": dpc_id,
                    "civil_protection_zone_info": properties["Nome zona"],
                }
        _LOGGER.debug("DATA: %s", data)
        return data
