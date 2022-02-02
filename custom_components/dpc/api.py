"""Dpc API Client."""
import asyncio
import json
import re
import socket
from datetime import date, datetime, time, timedelta
from math import *

import aiohttp
import async_timeout
from geojson_utils import geometry_within_radius, point_distance, point_in_polygon

from .const import (
    ATTR_AFTERTOMORROW,
    ATTR_ALERT,
    ATTR_EXPIRES,
    ATTR_ID,
    ATTR_IMAGE_URL,
    ATTR_INFO,
    ATTR_LAST_UPDATE,
    ATTR_LEVEL,
    ATTR_LINK,
    ATTR_PHENOMENA,
    ATTR_PRECIPITATION,
    ATTR_PUBLICATION_DATE,
    ATTR_RISK,
    ATTR_TODAY,
    ATTR_TOMORROW,
    ATTR_ZONE_NAME,
    LOGGER,
    WARNING_ALERT,
)

CRIT_API_URL = "https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/contents/files/all"
CRIT_BULLETIN_URL = (
    "https://mappe.protezionecivile.gov.it/it/mappe-rischi/bollettino-di-criticita/"
)
CRIT_IMAGE_URL = (
    "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-"
    "Idrogeologica-Idraulica/master/files/preview/{}_{}.png"
)
CRIT_PATTERN_URL = (
    "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-"
    "Idrogeologica-Idraulica/master/files/geojson/{}_{}.json"
)
VIGI_API_URL = "https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Vigilanza-Meteorologica/contents/files/all"
VIGI_BULLETIN_URL = (
    "https://mappe.protezionecivile.it/it/mappe-rischi/bollettino-di-vigilanza/"
)
VIGI_IMAGE_URL = (
    "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Vigilanza-"
    "Meteorologica/master/files/preview/{}_{}.png"
)
VIGI_PATTERN_URL = (
    "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Vigilanza-"
    "Meteorologica/master/files/geojson/{}_{}.json"
)

OGGI = "oggi"
DOMANI = "domani"
DOPODOMANI = "dopodomani"
RISKS = ["idraulico", "temporali", "idrogeologico"]

CRITICALITY = "criticality"
VIGILANCE = "vigilance"

DEFAULT_ICON = "mdi:hazard-lights"
CRIT_ICON = {
    "idraulico": "mdi:home-flood",
    "temporali": "mdi:weather-lightning",
    "idrogeologico": "mdi:waves",
}
VIGI_ICON = {
    1: "mdi:numeric-1-circle",
    2: "mdi:numeric-2-circle",
    3: "mdi:numeric-3-circle",
    4: "mdi:numeric-4-circle",
    5: "mdi:numeric-5-circle",
}
PHENOMENA_ICON = {
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
    40: "mdi:wave" "mdi:sail-boat",
    41: "mdi:waves",
    42: "mdi:hydro-power",
    50: "mdi:arrow-up-thick",
    51: "mdi:arrow-down-thick",
    60: "mdi:thermometer-chevron-up",
    61: "mdi:thermometer-plus",
    62: "mdi:thermometer-chevron-down",
    63: "mdi:thermometer-minus",
}
PHENOMENA_TYPE = {
    "PRECIPITAZIONI": {
        1: "piogge sparse o intermittenti",
        2: "piogge diffuse e continue",
        3: "nevicate deboli o moderate",
        4: "nevicate abbondanti",
        5: "rovesci o temporali a carattere isolato",
        6: "rovesci o temporali a carattere sparso",
        7: "rovesci o temporali a carattere diffuso",
    },
    "VENTI": {
        10: "forti",
        11: "burrasca",
        12: "tempesta",
        13: "frequenti raffiche",
    },
    "GELATE": {
        20: "diffusa formazione di ghiaggio al suolo a quote collinari",
        21: "diffusa formazione di ghiaggio al suolo a quote di pianura",
    },
    "NEBBIE": {
        30: "diffuse nelle ore notturne e del primo mattino",
        31: "diffuse e persistenti anche nelle ore diurne",
    },
    "MARI": {
        40: "molto mosso",
        41: "agitato o molto agitato",
        42: "grosso o molto grosso",
    },
    "MOTO_ONDOSO": {
        50: "in aumento",
        51: "in diminuzione",
    },
    "TEMPERATURE": {
        60: "elevate o in sensibile aumento",
        61: "molto elevate o in marcato aumento",
        62: "basse o in sensibile calo",
        63: "molto basse o in marcato calo",
    },
}

REGEX_DPC_ID = re.compile(r'href=[\'"]?([^\'" >]+\/)([0-9]+.[0-9]+).zip', re.IGNORECASE)
TIMEOUT = 20


class DpcApiClient:
    def __init__(
        self,
        location_name: str,
        latitude: float,
        longitude: float,
        radius: int,
        session: aiohttp.ClientSession,
        update_interval: timedelta,
    ) -> None:
        """Dpc API Client."""
        self._name = location_name
        self._latitude = latitude
        self._longitude = longitude
        self._radius = radius
        self._session = session
        self._interval = update_interval

        self._pub_date_crit = None
        self._pub_date_vigi = None
        self._id_crit = None
        self._id_vigi = None
        self._cache_vigi = {}
        self._cache_crit = {}
        self._data = {}
        self._point = {"type": "Point", "coordinates": [longitude, latitude]}
        self._str_today = None
        self._str_yesterday = None

    async def async_get_data(self):
        """Get data from the API."""
        now = datetime.now()
        midnight = datetime.combine(now.date(), time())
        midnight_first_update = midnight + self._interval
        between_midnight_first_update = bool(midnight <= now <= midnight_first_update)
        date_today = date.today()

        date_yesterday = date_today - timedelta(days=1)
        self._str_today = date_today.strftime("%Y%m%d")
        self._str_yesterday = date_yesterday.strftime("%Y%m%d")

        self._data[ATTR_LAST_UPDATE] = now.isoformat()

        urls = []

        try:
            ids_dpc = await self.scrape_urls([CRIT_API_URL, VIGI_API_URL])
            id_ct, id_vg = ids_dpc.get(CRIT_API_URL), ids_dpc.get(VIGI_API_URL)
            LOGGER.debug("[%s] Get IDs from Api. %s - %s", self._name, id_ct, id_vg)
        except:
            ids_dpc = await self.scrape_urls([CRIT_BULLETIN_URL, VIGI_BULLETIN_URL])
            id_ct, id_vg = ids_dpc.get(CRIT_BULLETIN_URL), ids_dpc.get(
                VIGI_BULLETIN_URL
            )
            LOGGER.debug("[%s] Get IDs from Site. %s - %s", self._name, id_ct, id_vg)

        if id_ct:
            if self._id_crit != id_ct:
                self._data[CRITICALITY] = {}
                self._cache_crit = {}
                self._id_crit = id_ct
                self._pub_date_crit = datetime.strptime(self._id_crit, "%Y%m%d_%H%M")
                urls.extend(
                    [
                        CRIT_PATTERN_URL.format(self._id_crit, "today"),
                        CRIT_PATTERN_URL.format(self._id_crit, "tomorrow"),
                    ]
                )
            elif between_midnight_first_update:
                self.swap_data_criticality()
            else:
                LOGGER.debug(
                    "[%s] Criticality No changes. %s", self._name, self._id_crit
                )
            self._data[CRITICALITY][ATTR_LAST_UPDATE] = now.isoformat()

        if id_vg:
            if self._id_vigi != id_vg:
                self._data[VIGILANCE] = {}
                self._cache_vigi = {}
                self._id_vigi = id_vg
                self._pub_date_vigi = datetime.strptime(self._id_vigi, "%Y%m%d")
                for day in [OGGI, DOMANI, DOPODOMANI]:
                    urls.extend(
                        [
                            VIGI_PATTERN_URL.format(self._id_vigi, day),
                            VIGI_PATTERN_URL.format(self._id_vigi, f"fenomeni_{day}"),
                        ]
                    )
            elif between_midnight_first_update:
                self.swap_data_vigilance()
            else:
                LOGGER.debug("[%s] Vigilance No changes. %s", self._name, self._id_vigi)
            self._data[VIGILANCE][ATTR_LAST_UPDATE] = now.isoformat()

        if urls:
            await self.fetch_all(urls)
            if id_ct and (date_today != self._pub_date_crit.date()):
                self.swap_data_criticality()
            if id_vg and (date_today != self._pub_date_vigi.date()):
                self.swap_data_vigilance()

        LOGGER.debug("[%s] DATA: %s", self._name, self._data)
        return self._data

    async def scrape_urls(self, urls: list) -> dict:
        results = await asyncio.gather(*[self.api_fetch(url) for url in urls])
        return {k: v for element in results for k, v in element.items()}

    async def fetch_all(self, urls: list):
        await asyncio.gather(*[self.fetch_and_parse(url) for url in urls])

    async def fetch_and_parse(self, url: str) -> dict:
        response = await self.api_fetch(url)
        if response:
            if "Vigilanza-Meteorologica" in url:
                self.get_vigilance(response, url)
            elif "Criticita-Idrogeologica" in url:
                self.get_criticality(response, url)

    async def api_fetch(self, url: str) -> dict:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(TIMEOUT):
                if "json" in url:
                    r = await self._session.get(url, raise_for_status=True)
                    fetched = await r.json(content_type=None)  # not import json
                elif "api." in url:
                    r = await self._session.get(url, raise_for_status=True)
                    jdata = json.loads(await r.text())
                    fetched = {url: self.get_id_from_api(jdata, self._str_today)}
                    LOGGER.debug("[%s] ClientResponse ->  %s", self._name, r)
                else:
                    r = await self._session.get(url, raise_for_status=True)
                    fetched = {url: self.parse(await r.text())}
                    LOGGER.debug("[%s] ClientResponse ->  %s", self._name, r)
                LOGGER.debug("[%s] -> Got [%s] for URL: %s", self._name, r.status, url)
                return fetched

        except asyncio.CancelledError as e:
            LOGGER.error("Cancelled error fetching information from %s - %s", url, e)

        except asyncio.TimeoutError as e:
            LOGGER.error("Timeout error fetching information from %s - %s", url, e)

        except (KeyError, TypeError) as e:
            LOGGER.error("Error parsing information from %s - %s", url, e)

        except (aiohttp.ClientError, aiohttp.http_exceptions.HttpProcessingError) as e:
            status = getattr(e, "status", None)
            message = getattr(e, "message", None)
            LOGGER.error("aiohttp exception for %s [%s]:%s", url, status, message)

        except (socket.gaierror) as e:
            LOGGER.error("Socket Error fetching information from %s - %s", url, e)

        except Exception as unexpected_error:
            LOGGER.exception(
                "Unexpected error exception occured for %s:  %s",
                url,
                getattr(unexpected_error, "__dict__", {}),
            )

    def get_id_from_api(self, data, day) -> str:
        for item in reversed(data):
            if not item["name"].startswith(day):
                continue
            return re.split("_all.zip|.zip", item["name"])[0]
        return self.get_id_from_api(data, self._str_yesterday)

    def parse(self, html) -> str:
        LOGGER.debug("[%s] Parse DPC Bulletin in progress...", self._name)
        id_pub = [match[1] for match in REGEX_DPC_ID.findall(html)]
        if id_pub:
            return id_pub[0]

    def swap_data_criticality(self):
        for risk in RISKS:
            day_0 = f"{risk}_{OGGI}"
            day_1 = f"{risk}_{DOMANI}"
            self._cache_crit[day_0] = self._cache_crit.get(day_1, {})
            self._cache_crit[day_1] = {}
        self._cache_crit[ATTR_TODAY] = self._cache_crit.get(ATTR_TOMORROW, {})
        self._cache_crit.pop(ATTR_TOMORROW, None)
        self._data[CRITICALITY] = self._cache_crit
        LOGGER.debug("[%s] Criticality swap data...", self._name)

    def swap_data_vigilance(self):
        self._cache_vigi[ATTR_TODAY] = self._cache_vigi.get(ATTR_TOMORROW, {})
        self._cache_vigi[ATTR_TOMORROW] = self._cache_vigi.get(ATTR_AFTERTOMORROW, {})
        self._cache_vigi.pop(ATTR_AFTERTOMORROW, None)
        self._data[VIGILANCE] = self._cache_vigi
        LOGGER.debug("[%s] Vigilance swap data...", self._name)

    def get_criticality(self, response: dict, url: str) -> dict:
        LOGGER.debug("[%s] Criticality Update in progress......", self._name)
        now = datetime.now()
        expiration_date = datetime.combine(self._pub_date_crit, datetime.min.time())
        try:
            if "today" in url:
                day_en = ATTR_TODAY
                day_it = OGGI
            else:
                day_en = ATTR_TOMORROW
                day_it = DOMANI
                expiration_date += timedelta(days=1)

            self._cache_crit[ATTR_ID] = self._id_crit
            self._cache_crit[ATTR_LAST_UPDATE] = now.isoformat()
            self._cache_crit[ATTR_LINK] = CRIT_BULLETIN_URL
            self._cache_crit[ATTR_PUBLICATION_DATE] = self._pub_date_crit

            prop = self.get_properties(self._point, response)
            self._cache_crit[ATTR_ZONE_NAME] = prop["Nome zona"]
            image = CRIT_IMAGE_URL.format(self._id_crit, day_it)

            self._cache_crit[day_en] = self.get_info_level(
                prop["Rappresentata nella mappa"]
            )
            self._cache_crit[day_en].update(
                {
                    ATTR_IMAGE_URL: image,
                    ATTR_EXPIRES: expiration_date,
                }
            )

            for risk in RISKS:
                self._cache_crit[f"{risk}_{day_it}"] = {
                    ATTR_RISK: risk.capitalize(),
                    ATTR_IMAGE_URL: image,
                    ATTR_EXPIRES: expiration_date,
                    "icon": CRIT_ICON.get(risk),
                }
                self._cache_crit[f"{risk}_{day_it}"].update(
                    self.get_info_level(prop["Per rischio " + risk])
                )

            self._data[CRITICALITY] = self._cache_crit

        except Exception as exception:
            LOGGER.error("Criticality Exception! - %s", exception)
            pass

    def get_vigilance(self, response: dict, url: str) -> dict:
        LOGGER.debug("[%s] Vigilance Update in progress......", self._name)
        now = datetime.now()
        try:
            day_en = str()
            image_vigi = str()
            if "_oggi" in url:
                day_en = ATTR_TODAY
                image_vigi = VIGI_IMAGE_URL.format(self._id_vigi, OGGI)
            elif "_domani" in url:
                day_en = ATTR_TOMORROW
                image_vigi = VIGI_IMAGE_URL.format(self._id_vigi, DOMANI)
            elif "_dopodomani" in url:
                day_en = ATTR_AFTERTOMORROW
                image_vigi = None

            if day_en not in self._cache_vigi:
                self._cache_vigi[day_en] = {}

            if "_fenomeni" in url:
                phenomena = self.get_phenomena(self._point, response)
                self._cache_vigi[day_en].update({ATTR_PHENOMENA: phenomena})

            elif "Vigilanza-Meteorologica" in url:
                prop = self.get_properties(self._point, response)
                self._cache_vigi[day_en].update(
                    {
                        "icon": VIGI_ICON.get(prop["id_classificazione"]),
                        ATTR_IMAGE_URL: image_vigi,
                        ATTR_LEVEL: prop["id_classificazione"],
                        ATTR_PRECIPITATION: prop["Quantitativi_previsti"],
                    }
                )
                self._cache_vigi.update(
                    {
                        ATTR_ID: self._id_vigi,
                        ATTR_PUBLICATION_DATE: self._pub_date_vigi,
                        ATTR_ZONE_NAME: prop["Nome_Zona"],
                        ATTR_LAST_UPDATE: now.isoformat(),
                    }
                )

            self._data[VIGILANCE] = self._cache_vigi

        except Exception as exception:
            LOGGER.error("Vigilance Exception! - %s", exception)
            pass

    @staticmethod
    def get_info_level(value) -> dict:
        d = dict()
        d[ATTR_INFO] = value.split("/")[0].rstrip().lstrip()
        d[ATTR_ALERT] = value.split("/")[1].lstrip()
        d[ATTR_LEVEL] = WARNING_ALERT.get(d[ATTR_ALERT], 0)
        return d

    @staticmethod
    def get_properties(point, geojs) -> dict:
        for feature in geojs["features"]:
            if not point_in_polygon(point, feature["geometry"]):
                continue
            return feature["properties"]

    def get_phenomena(self, point, geojs) -> list:
        phenomena = []
        radius = self._radius * 1000
        for feature in geojs["features"]:
            if not geometry_within_radius(feature["geometry"], point, radius):
                continue
            prop = feature["properties"]
            for p_event, p_id_phenom in PHENOMENA_TYPE.items():
                if not prop["id_fenomeno"] in p_id_phenom:
                    continue
                event = p_event.capitalize()
                id_event = prop["id_fenomeno"]
                value = p_id_phenom.get(id_event)
                lat, long = prop["lat"], prop["lon"]
                bearing = calculate_initial_compass_bearing(
                    (self._latitude, self._longitude),
                    (lat, long),
                )
                pointB = {"type": "Point", "coordinates": [long, lat]}
                distance = floor(point_distance(point, pointB) / 1000)
                new_prop = {
                    ATTR_ID: prop["id_bollettino"],
                    "date": prop["data_bollettino"],
                    "id_event": id_event,
                    "event": event,
                    "value": value,
                    "latitude": lat,
                    "longitude": long,
                    "distance": distance,
                    "direction": bearing[0],
                    "degrees": bearing[1],
                    "icon": PHENOMENA_ICON.get(id_event, DEFAULT_ICON),
                }
                phenomena.append(new_prop)
        return phenomena


def calculate_initial_compass_bearing(pointA, pointB) -> tuple:
    """credits
    https://gist.github.com/jeromer/2005586
    https://gist.github.com/RobertSudwarts/acf8df23a16afdb5837f
    """
    if (type(pointA) != tuple) or (type(pointB) != tuple):
        raise TypeError("Only tuples are supported as arguments")
    lat1 = radians(pointA[0])
    lat2 = radians(pointB[0])
    diffLong = radians(pointB[1] - pointA[1])
    x = sin(diffLong) * cos(lat2)
    y = cos(lat1) * sin(lat2) - (sin(lat1) * cos(lat2) * cos(diffLong))
    initial_bearing = atan2(x, y)
    initial_bearing = degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360
    dirs = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    ix = round(compass_bearing / (360.0 / len(dirs)))
    return dirs[ix % len(dirs)], floor(compass_bearing)
