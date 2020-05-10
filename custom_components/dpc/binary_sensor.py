"""Binary Sensor for Protezione Civile"""
import aiohttp
from datetime import date, timedelta
from dateutil.parser import parse
import asyncio
# import async_timeout #TODO#
import json
import logging

import voluptuous as vol
from homeassistant.components.binary_sensor import PLATFORM_SCHEMA, ENTITY_ID_FORMAT
from homeassistant.const import CONF_NAME, ATTR_ATTRIBUTION, CONF_SCAN_INTERVAL
# from homeassistant.helpers.aiohttp_client import async_get_clientsession #TODO#
import homeassistant.helpers.config_validation as cv
from homeassistant.components.binary_sensor import BinarySensorDevice
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = 'Information provided by protezionecivilepop.tk'

CONF_ALERT = 'alert'
CONF_ISTAT = 'istat'
CONF_WARNINGS = 'warnings'

DEFAULT_DEVICE_CLASS = 'safety'
DEFAULT_NAME = 'dpc'
DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)

WARNING_TYPES = {
    'temporali_oggi': ['temporali_oggi', 'Rischio Temporali Oggi', 'mdi:weather-lightning'],
    'idraulico_oggi': ['idraulico_oggi', 'Rischio Idraulico Oggi', 'mdi:home-flood'],
    'idrogeologico_oggi': ['idrogeologico_oggi', 'Rischio Idrogeologico Oggi', 'mdi:waves'],
    'temporali_domani': ['temporali_domani', 'Rischio Temporali Domani', 'mdi:weather-lightning'],
    'idraulico_domani': ['idraulico_domani', 'Rischio Idraulico Domani', 'mdi:home-flood'],
    'idrogeologico_domani': ['idrogeologico_domani', 'Rischio Idrogeologico Domani', 'mdi:waves'],
}

WARNING_ALERT = {
    'BIANCA' : 0,
    'VERDE': 1,
    'GIALLA': 2,
    'ARANCIONE': 3,
    'ROSSA': 4,
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_ISTAT): cv.string,
    vol.Optional(CONF_ALERT, default='GIALLA'): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_WARNINGS, default=[]):
        vol.All(cv.ensure_list, [vol.In(WARNING_TYPES)]),
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    name = config.get(CONF_NAME)
    warnings = config.get(CONF_WARNINGS)
    istat = str(config.get(CONF_ISTAT)).zfill(6)
    alert = config.get(CONF_ALERT)
    scan_interval = config.get(CONF_SCAN_INTERVAL)
    sensors = []
    sensor_name = '{} - '.format(name)
    updater = dpcUpdater(hass, istat, scan_interval)
    await updater.async_update()
    for warning_type in warnings:
        uid = '{}_{}'.format(name, warning_type)
        entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, uid, hass=hass)
        sensors.append(dpcSensor(entity_id, sensor_name, updater, warning_type, alert))
    _LOGGER.debug('UPDATER: %s', updater.dpc_output)
    async_add_entities(sensors, True)

class dpcSensor(BinarySensorDevice):
    def __init__(self, entity_id, name, updater, warning_type, alert):
        self.entity_id = entity_id
        self._name = name
        self._updater = updater
        self._data = None
        self._warning_type = warning_type
        self._warning_key = WARNING_TYPES[self._warning_type][0]
        self._alert = WARNING_ALERT.get(alert.upper())

    @property
    def is_on(self):
        data = self._updater.dpc_output[self._warning_key]
        k_date = parse(data['date']).date()
        return data is not None and WARNING_ALERT.get(data['alert']) >= self._alert and k_date >= date.today()

    @property
    def device_state_attributes(self):
        output = dict()
        output[ATTR_ATTRIBUTION] = ATTRIBUTION
        if self.is_on:
            data = self._updater.dpc_output[self._warning_key]
            output['data'] = parse(data['date']).date().strftime('%d-%m-%Y')
            output['rischio'] = data['risk'].capitalize()
            output['info'] = data['info']
            output['allerta'] = data['alert']
            output['istat'] = data['istat_code']
            output['città'] = data['city_name']
            output['provincia'] = data['province_name']
            output['prov'] = data['province_code']
            output['regione'] = data['region']
            output['zona_id'] = data['civil_protection_zone_id']
            output['zona_info'] = data['civil_protection_zone_info']
            output['longitudine'] = data['longitude']
            output['latitudine'] = data['latitude']
            output['level'] = WARNING_ALERT.get(data['alert'])
        return output

    @property
    def device_class(self):
        return DEFAULT_DEVICE_CLASS

    @property
    def icon(self):
        return WARNING_TYPES[self._warning_type][2]

    @property
    def name(self):
        return WARNING_TYPES[self._warning_type][1]

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        try:
            info = self._updater.dpc_output[self._warning_key]['info']
        except KeyError:
            return False
        return True

    async def async_update(self):
        await self._updater.async_update()

class dpcUpdater:
    def __init__(self, hass, istat, scan_interval):
        # self._hass = hass #TODO#
        self._istat = istat
        self.dpc_output = {}
        self.async_update = Throttle(scan_interval)(self._async_update)

    async def _async_update(self):
        url_base = f"http://www.protezionecivilepop.tk/allerte?citta={self._istat}&rischio="
        URL_LIST = [
            url_base + 'temporali' + '&allerta=' + 'verde' + '&giorno=' + 'domani' + '&formato=json',
            url_base + 'idraulico' + '&allerta=' + 'verde' + '&giorno=' + 'domani' + '&formato=json',
            url_base + 'idrogeologico' + '&allerta=' + 'verde' + '&giorno=' + 'domani' + '&formato=json',
            url_base + 'temporali' + '&allerta=' + 'verde' + '&giorno=' + 'oggi' + '&formato=json',
            url_base + 'idraulico' + '&allerta=' + 'verde' + '&giorno=' + 'oggi' + '&formato=json',
            url_base + 'idrogeologico' + '&allerta=' + 'verde' + '&giorno=' + 'oggi' + '&formato=json'
        ]
        await self.fetch_all(URL_LIST)
        # await self._hass.async_add_executor_job(self.fetch_all) #TODO?#

    async def fetch_all(self, urls):
        """Launch requests for all url."""
        tasks = []
        async with aiohttp.ClientSession() as session:
            for url in urls:
                task = asyncio.ensure_future(self.fetch(url, session))
                tasks.append(task)
            responses = await asyncio.gather(*tasks)
            _LOGGER.debug('RESPONSE: %s', responses)
            return responses

    async def fetch(self, url, session):
        """Fetch a url, using specified ClientSession."""
        try:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    _LOGGER.error('Connection failed with http code: %s with url: %s', response.status, url)
                    return {}
                try:
                    data = await response.json()
                except aiohttp.ContentTypeError:
                    # If json decoder could not parse the response
                    _LOGGER.error('Failed to parse response from site. Check the istat number: %s - URL: %s', self._istat, url)
                    return {}

                # Parsing response
                k = data['previsione']
                k_date = parse(k['date']).date()
                if k_date == date.today():
                    self.dpc_output[k['risk'] + '_oggi'] = k
                elif k_date > date.today():
                    self.dpc_output[k['risk'] + '_domani'] = k
                else:
                    return {}
                _LOGGER.debug('DATA response: %s\n', k)
                json.loads(json.dumps(self.dpc_output))
                return url, data
        except aiohttp.client_exceptions.ClientConnectorError:
            _LOGGER.error('Cannot connect to: %s', url)
            return {}
