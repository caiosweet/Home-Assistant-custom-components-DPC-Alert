"""Binary Sensor for Dipartimento della Protezione Civile Meteo-Hydro Alert"""
import aiohttp
import asyncio

# import async_timeout # TODO#
from datetime import date, timedelta
from dateutil.parser import parse
import feedparser
import json
import logging

import voluptuous as vol
from homeassistant.components.binary_sensor import PLATFORM_SCHEMA, ENTITY_ID_FORMAT

try:
    from homeassistant.components.binary_sensor import BinarySensorEntity
except ImportError:
    from homeassistant.components.binary_sensor import (
        BinarySensorDevice as BinarySensorEntity,
    )
from homeassistant.const import CONF_NAME, ATTR_ATTRIBUTION, CONF_SCAN_INTERVAL

# from homeassistant.helpers.aiohttp_client import async_get_clientsession # TODO#
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.util import Throttle

from .const import (
    ATTRIBUTION,
    BASE_URL,
    BULLETTIN_URL,
    FEED_URL,
    CONF_ALERT,
    CONF_ISTAT,
    CONF_WARNINGS,
    DEFAULT_DEVICE_CLASS,
    DEFAULT_NAME,
    ISSUES_RESOURCE_URL,
    WARNING_TYPES,
    WARNING_ALERT,
)

DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
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


@asyncio.coroutine
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup."""
    _LOGGER.debug("[%s] start async setup platform", DEFAULT_NAME)
    name = config.get(CONF_NAME)
    warnings = config.get(CONF_WARNINGS)
    istat = str(config.get(CONF_ISTAT)).zfill(6)
    alert = config.get(CONF_ALERT)
    scan_interval = config.get(CONF_SCAN_INTERVAL)
    sensors = []
    updater = dpcUpdater(hass, istat, scan_interval, warnings)
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
        self._warning_type = warning_type
        self._warning_key = WARNING_TYPES[self._warning_type][0]
        self._alert = WARNING_ALERT.get(alert.upper())

    @property
    def is_on(self):
        try:
            data = self._updater.dpc_output[self._warning_key]
            prevision_date = parse(data["date"]).date()
        except KeyError:
            return False
        return (
            data is not None
            and WARNING_ALERT.get(data["alert"]) >= self._alert
            and prevision_date >= date.today()
        )

    @property
    def device_state_attributes(self):
        """Return attrubutes."""
        output = dict()
        output[ATTR_ATTRIBUTION] = ATTRIBUTION
        if self._updater.newlink:
            output["link"] = self._updater.newlink
        if self.is_on:
            data = self._updater.dpc_output[self._warning_key]
            output["data"] = parse(data["date"]).date().strftime("%d-%m-%Y")
            output["rischio"] = data["risk"].capitalize()
            output["info"] = data["info"]
            output["allerta"] = data["alert"]
            output["istat"] = data["istat_code"]
            output["città"] = data["city_name"]
            output["provincia"] = data["province_name"]
            output["prov"] = data["province_code"]
            output["regione"] = data["region"]
            output["zona_id"] = data["civil_protection_zone_id"]
            output["zona_info"] = data["civil_protection_zone_info"]
            output["longitudine"] = data["longitude"]
            output["latitudine"] = data["latitude"]
            output["level"] = WARNING_ALERT.get(data["alert"])
            output["link"] = data["link"]
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

    @asyncio.coroutine
    async def async_update(self):
        """Update data."""
        await self._updater.async_update()


class dpcUpdater:
    """fetch all data."""

    def __init__(self, hass, istat, scan_interval, warnings):
        self._hass = hass
        self._istat = istat
        self._warnings = warnings
        self.dpc_output = None
        self.newlink = BULLETTIN_URL
        self.async_update = Throttle(scan_interval)(self.async_update)

    async def async_update(self):
        await self._hass.async_add_executor_job(self.new_feed)
        self.dpc_output = await self.fetch_all()
        _LOGGER.debug("[%s] ASYNC UPDATE: %s\n", DEFAULT_NAME, self.dpc_output)

    def new_feed(self):
        try:
            NewsFeed = feedparser.parse(FEED_URL)
            entry = NewsFeed.entries[0]
            self.newlink = entry.link
        except:
            newlink = self.newlink
            _LOGGER.debug("[%s] Failed feedparser: %s \n", DEFAULT_NAME, newlink)

    async def fetch_all(self):
        """Launch requests for all url."""
        tasks = []
        async with aiohttp.ClientSession() as session:
            for warning_type in self._warnings:
                warning_type = warning_type.split("_")
                url = BASE_URL.format(self._istat, warning_type[0], warning_type[1])
                task = asyncio.ensure_future(self.fetch(url, session))
                tasks.append(task)
            dataList = await asyncio.gather(*tasks)
            responses = {k: v for element in dataList for k, v in element.items()}
            return responses

    async def fetch(self, url, session):
        """Fetch a url, using specified ClientSession."""
        try:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    _LOGGER.warning(
                        "[%s] Connection failed with http code: %s with url: %s",
                        DEFAULT_NAME,
                        response.status,
                        url,
                    )
                    return {}
                try:
                    data = await response.json()
                except aiohttp.ContentTypeError:
                    # If json decoder could not parse the response
                    _LOGGER.warning(
                        "[%s] Failed to parse response from site. Check the istat number: %s - URL: %s",
                        DEFAULT_NAME,
                        self._istat,
                        url,
                    )
                    return {}
                jsondata = {}
                # Parsing response
                prevision = data.get("previsione", {})  # data["previsione"]
                try:
                    prevision_date = parse(prevision["date"]).date()
                except KeyError:
                    _LOGGER.warning(
                        "[%s] Missing data for %s - URL: %s \n Please, open issue here --> %s",
                        DEFAULT_NAME,
                        self._istat,
                        url,
                        ISSUES_RESOURCE_URL,
                    )
                    return {}

                if self.newlink:
                    prevision["link"] = self.newlink
                if prevision_date == date.today():
                    jsondata[prevision["risk"] + "_oggi"] = prevision
                elif prevision_date > date.today():
                    jsondata[prevision["risk"] + "_domani"] = prevision
                else:  # prevision_date < date.today():
                    day = (
                        "_domani"
                        if "oggi" in url
                        and prevision_date < date.today() + timedelta(days=1)
                        else "_oggi"
                    )
                    jsondata[prevision["risk"] + day] = {"link": prevision["link"]}
                # _LOGGER.debug("JSON DATA: %s\n", jsondata)
                return json.loads(json.dumps(jsondata))
        except aiohttp.client_exceptions.ClientConnectorError:
            _LOGGER.error("[%s] Cannot connect to: %s", DEFAULT_NAME, url)
            return {}
