"""Binary Sensor for Protezione Civile"""
from datetime import date, timedelta
from dateutil.parser import parse
import json
import logging
import requests

import voluptuous as vol
from homeassistant.components.binary_sensor import PLATFORM_SCHEMA, ENTITY_ID_FORMAT
from homeassistant.const import CONF_NAME, ATTR_ATTRIBUTION, CONF_SCAN_INTERVAL, CONF_LATITUDE, CONF_LONGITUDE
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
    vol.Optional(CONF_LATITUDE): cv.string,
    vol.Optional(CONF_LONGITUDE): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_WARNINGS, default=[]):
        vol.All(cv.ensure_list, [vol.In(WARNING_TYPES)]),
    vol.Required(CONF_ISTAT): cv.string,
    vol.Optional(CONF_ALERT, default='GIALLA'): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    name = config.get(CONF_NAME)
    latitude = float(config.get(CONF_LATITUDE, hass.config.latitude))
    longitude = float(config.get(CONF_LONGITUDE, hass.config.longitude))
    warnings = config.get(CONF_WARNINGS)
    istat = str(config.get(CONF_ISTAT)).zfill(6)
    alert = config.get(CONF_ALERT)
    scan_interval = config.get(CONF_SCAN_INTERVAL)
    sensors = []
    sensor_name = '{} - '.format(name)
    updater = dpcUpdater(istat, scan_interval)
    await updater.async_update()
    for warning_type in warnings:
        uid = '{}_{}'.format(name, warning_type)
        entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, uid, hass=hass)
        sensors.append(dpcWarningsSensor(entity_id, sensor_name, updater, warning_type, alert))
    async_add_entities(sensors, True)

class dpcSensor(BinarySensorDevice):
    def __init__(self, entity_id, name, updater):
        self.entity_id = entity_id
        self._name = name
        self._updater = updater
        self._data = None

    @property
    def device_state_attributes(self):
        output = dict()
        if self._updater.dpc_output is not None:
            data = self._updater.dpc_output[self._warning_key]
            if 'update' in data:
                output['Prossimo Aggiornamento'] = data['update']
        if self._updater.dpc_output is None:
                output['Error setting up dpc'] = 'Check the istat number or data not found'
        output[ATTR_ATTRIBUTION] = ATTRIBUTION
        return output

    async def async_update(self):
        await self._updater.async_update()

class dpcWarningsSensor(dpcSensor):
    def __init__(self, entity_id, name, updater, warning_type, alert):
        super().__init__(entity_id, name, updater)
        self._warning_type = warning_type
        self._warning_key = WARNING_TYPES[self._warning_type][0]
        self._alert = WARNING_ALERT.get(alert.upper())
    
    @property
    def is_on(self):
        value = False
        if self._updater.dpc_output is not None:
            data = self._updater.dpc_output[self._warning_key]
            k_date = parse(data['date']).date()
            if WARNING_ALERT.get(data['alert']) >= self._alert and k_date >= date.today():
                value = data
        return value 

    @property
    def device_state_attributes(self):
        output = super().device_state_attributes
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

class dpcUpdater:
    def __init__(self, istat, scan_interval):
        self._istat = istat
        self.dpc_output = None
        self.async_update = Throttle(scan_interval)(self._async_update)

    async def _async_update(self):
        jsondata = {}
        url_base = 'http://www.protezionecivilepop.tk/allerte?citta='
        URLs = [
                url_base + self._istat + '&rischio=' + 'temporali' + '&allerta=' + 'verde' + '&giorno=' + 'domani' + '&formato=json',
                url_base + self._istat + '&rischio=' + 'idraulico' + '&allerta=' + 'verde' + '&giorno=' + 'domani' + '&formato=json',
                url_base + self._istat + '&rischio=' + 'idrogeologico' + '&allerta=' + 'verde' + '&giorno=' + 'domani' + '&formato=json',
                url_base + self._istat + '&rischio=' + 'temporali' + '&allerta=' + 'verde' + '&giorno=' + 'oggi' + '&formato=json',
                url_base + self._istat + '&rischio=' + 'idraulico' + '&allerta=' + 'verde' + '&giorno=' + 'oggi' + '&formato=json',
                url_base + self._istat + '&rischio=' + 'idrogeologico' + '&allerta=' + 'verde' + '&giorno=' + 'oggi' + '&formato=json'
               ]

        # Doing a request
        try:
            for url in URLs:
                try:
                    data = await hass.async_add_executor_job(requests.get(url, timeout=10))
                except requests.exceptions.Timeout:
                    _LOGGER.error('Connection to the site timed out at URL %s', url)
                    return False
                if data.status_code != 200:
                    _LOGGER.error('Connection failed with http code %s', data.status_code)
                    return False
                try:
                    k = data.json()['previsione']
                except ValueError:
                    # If json decoder could not parse the response
                    _LOGGER.error('Failed to parse response from site. Check the istat number %s', self._istat)
                    return False
                
                # Parsing response
                k_date = parse(k['date']).date()
                if k_date == date.today() and ('oggi' in url or 'domani' in url):
                    jsondata[k['risk'] + '_oggi'] = k
                if k_date > date.today() and 'domani' in url:
                    jsondata[k['risk'] + '_domani'] = k
                if k_date < date.today() and'oggi' in url:
                    jsondata[k['risk'] + '_domani'] = {'alert': 'BIANCA', 'date': k['date'], 'update': 'ore 17:00'}

                ris = json.loads(json.dumps(jsondata))

            self.dpc_output = ris
        except:
            _LOGGER.error('Error setting up dpc - Check the istat number %s', self._istat)
