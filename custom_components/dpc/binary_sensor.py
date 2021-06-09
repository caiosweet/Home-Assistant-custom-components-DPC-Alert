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
    # Prior to HA 0.110
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
    IMAGE_URL,
    ISSUES_RESOURCE_URL,
    WARNING_ALERT,
    WARNING_TYPES,
)

DEFAULT_SCAN_INTERVAL = datetime.timedelta(minutes=30)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_LATITUDE): cv.string,
        vol.Optional(CONF_LONGITUDE): cv.string,
        vol.Optional(CONF_ISTAT): cv.string,
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
    alert = config.get(CONF_ALERT)
    scan_interval = config.get(CONF_SCAN_INTERVAL)
    sensors = []
    updater = dpcUpdater(hass, longitude, latitude, scan_interval, warnings)
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
        self._alert = WARNING_ALERT.get(alert.upper())

    @property
    def is_on(self):
        if self._updater.dpc_output:
            data = self._updater.dpc_output[self._warning_type]
            if "alert" in data:
                return WARNING_ALERT.get(data["alert"]) >= self._alert

    @property
    def device_state_attributes(self):
        """Return attrubutes."""
        output = dict()
        if self._updater.dpc_id:
            output["id"] = self._updater.dpc_id
        output["link"] = BULLETTIN_URL
        output[ATTR_ATTRIBUTION] = ATTRIBUTION
        if self.is_on:
            data = self._updater.dpc_output[self._warning_type]
            output["data"] = data["date"]
            output["rischio"] = data["risk"].capitalize()
            output["info"] = data["info"]
            output["allerta"] = data["alert"]
            output["zona_info"] = data["civil_protection_zone_info"]
            output["level"] = WARNING_ALERT.get(data["alert"])
            output["image_url"] = data["image_url"]
            output["id"] = data["dpc_id"]
        return output

    @property
    def device_class(self):
        """Return device_class."""
        return DEFAULT_DEVICE_CLASS

    @property
    def icon(self):
        """Return icon."""
        return WARNING_TYPES[self._warning_type][1]

    @property
    def name(self):
        """Return name."""
        return WARNING_TYPES[self._warning_type][0]

    async def async_update(self):
        """Update data."""
        await self._updater.async_update()


class dpcUpdater:
    """fetch all data."""

    def __init__(self, hass, longitude, latitude, scan_interval, warnings):
        self._hass = hass
        self._longitude = longitude
        self._latitude = latitude
        self._warnings = warnings
        self.dpc_output = None
        self.dpc_id = None
        self.pub_date = None
        self.async_update = Throttle(scan_interval)(self._async_update)

    async def _async_update(self):
        new_dpc_id = await self._hass.async_add_executor_job(self.update_dpc_id)
        _LOGGER.debug(
            "[%s] Date published: %s - %s", DEFAULT_NAME, new_dpc_id, self.pub_date
        )
        self.dpc_output = await self._hass.async_add_executor_job(self.fetch_all)
        _LOGGER.debug("[%s] ASYNC UPDATE: %s", DEFAULT_NAME, self.dpc_output)

    def update_dpc_id(self):
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
                    self.pub_date = date_time_obj
                _LOGGER.debug(
                    "[%s] Shape Link: %s - ID: %s", DEFAULT_NAME, link, self.dpc_id
                )
            return id_pub
        except:
            _LOGGER.debug("[%s] Failed DPC ID: %s ", DEFAULT_NAME, self.dpc_id)

    def fetch_all(self):
        """Launch requests for all url."""

        url_today = BASE_URL.format(self.dpc_id, "today")
        url_tomorrow = BASE_URL.format(self.dpc_id, "tomorrow")

        r_today = requests.get(url_today)
        r_tomorrow = requests.get(url_tomorrow)

        js_today = r_today.json()
        js_tomorrow = r_tomorrow.json()

        point = {"type": "Point", "coordinates": [self._longitude, self._latitude]}
        today = datetime.date.today()

        data = {}
        default_data = {"dpc_id": self.dpc_id, "link": BULLETTIN_URL}

        # check each polygon to see if it contains the point
        for feature in js_today["features"]:
            polygon = feature["geometry"]
            properties = feature["properties"]
            image = IMAGE_URL.format(self.dpc_id, "oggi")
            if point_in_polygon(point, polygon):
                for risk in ["idraulico", "temporali", "idrogeologico"]:
                    if today == self.pub_date.date():
                        data[risk + "_oggi"] = {
                            "date": self.pub_date,
                            "risk": risk,
                            "info": properties["Per rischio " + risk]
                            .split("/")[0]
                            .rstrip()
                            .lstrip(),
                            "alert": properties["Per rischio " + risk]
                            .split("/")[1]
                            .replace("ALLERTA", "")
                            .replace("NESSUNA", "VERDE")
                            .rstrip()
                            .lstrip(),
                            "link": BULLETTIN_URL,
                            "image_url": image,
                            "dpc_id": self.dpc_id,
                            "civil_protection_zone_info": properties["Nome zona"],
                        }
                    else:
                        data[risk + "_domani"] = default_data
        for feature in js_tomorrow["features"]:
            polygon = feature["geometry"]
            properties = feature["properties"]
            image = IMAGE_URL.format(self.dpc_id, "domani")
            if point_in_polygon(point, polygon):
                if today >= (self.pub_date.date() + datetime.timedelta(days=2)):
                    data["idraulico_oggi"] = default_data
                    data["temporali_oggi"] = default_data
                    data["idrogeologico_oggi"] = default_data
                else:
                    day = "_domani"
                    if today == (self.pub_date.date() + datetime.timedelta(days=1)):
                        day = "_oggi"
                    for risk in ["idraulico", "temporali", "idrogeologico"]:
                        data[risk + day] = {
                            "date": self.pub_date,
                            "risk": risk,
                            "info": properties["Per rischio " + risk]
                            .split("/")[0]
                            .rstrip()
                            .lstrip(),
                            "alert": properties["Per rischio " + risk]
                            .split("/")[1]
                            .replace("ALLERTA", "")
                            .replace("NESSUNA", "VERDE")
                            .rstrip()
                            .lstrip(),
                            "link": BULLETTIN_URL,
                            "image_url": image,
                            "dpc_id": self.dpc_id,
                            "civil_protection_zone_info": properties["Nome zona"],
                        }
        return data
