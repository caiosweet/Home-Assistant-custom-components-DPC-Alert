"""Dpc API Client."""
import asyncio
import datetime as dt
import math
import re
import socket

import aiohttp
import async_timeout
from bs4 import BeautifulSoup
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

CRIT_BULLETIN_URL = (
    "https://mappe.protezionecivile.gov.it/it/mappe-rischi/bollettino-di-criticita"
)
CRIT_IMAGE_URL = (
    "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-"
    "Idrogeologica-Idraulica/master/files/preview/{}_{}.png"
)
CRIT_PATTERN_URL = (
    "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-"
    "Idrogeologica-Idraulica/master/files/geojson/{}_{}.json"
)

VIGI_BULLETIN_URL = (
    "https://mappe.protezionecivile.it/it/mappe-rischi/bollettino-di-vigilanza"
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
TIMEOUT = 20
DEFAULT_ICON = "mdi:hazard-lights"
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


class DpcApiClient:
    def __init__(
        self,
        location_name: str,
        latitude: float,
        longitude: float,
        radius: int,
        session: aiohttp.ClientSession,
        update_interval: dt.timedelta,
    ) -> None:
        """Dpc API Client."""
        self._location = location_name
        self._latitude = latitude
        self._longitude = longitude
        self._radius = radius
        self._session = session
        self._interval = update_interval

        self._pub_date = None
        self._id_crit = None
        self._id_vigi = None
        self._cache_vigi = {}
        self._cache_crit = {}
        self._data = {}
        self._point = {"type": "Point", "coordinates": [longitude, latitude]}

    async def async_get_data(self):
        """Get data from the API."""
        now = dt.datetime.now()
        midnight = dt.datetime.combine(now.date(), dt.time())
        midnight_first_update = midnight + self._interval
        between_midnight_next_update = bool(midnight <= now <= midnight_first_update)
        date_today = dt.date.today()

        self._data[ATTR_LAST_UPDATE] = now.isoformat()

        urls = []
        id = await self.fetch_id([VIGI_BULLETIN_URL, CRIT_BULLETIN_URL])

        ## ID VIGILANCE
        parse_vigilance = id[0]
        soup_vigilance = BeautifulSoup(parse_vigilance, "html.parser")
        for link in soup_vigilance.find_all(href=re.compile("\.zip$")):
            id_pub_vigi = re.findall("[0-9]+", link.get("href"))

            if not id_pub_vigi:
                continue
            if self._id_vigi == id_pub_vigi[0] and not between_midnight_next_update:
                LOGGER.debug(
                    "[%s] Vigilance not update. %s", self._location, self._id_vigi
                )
                self._data["vigilance"][ATTR_LAST_UPDATE] = now.isoformat()  # TODO
            else:
                self._data["vigilance"] = {}
                self._cache_vigi = {}
                self._id_vigi = id_pub_vigi[0]
                for day in [OGGI, DOMANI, DOPODOMANI]:
                    url = VIGI_PATTERN_URL.format(self._id_vigi, day)
                    url2 = VIGI_PATTERN_URL.format(self._id_vigi, f"fenomeni_{day}")
                    urls.extend([url, url2])
            break

        ## ID CRITICALITY
        parse_criticality = id[1]
        soup_criticality = BeautifulSoup(parse_criticality, "html.parser")
        for link in soup_criticality.find_all(href=re.compile("shp\.zip$")):
            id_pub_date = re.findall("[0-9]+_[0-9]+", link.get("href"))

            if not id_pub_date:
                continue
            if self._id_crit == id_pub_date[0] and not between_midnight_next_update:
                LOGGER.debug(
                    "[%s] Criticality Not update. %s", self._location, self._id_crit
                )
                self._data["criticality"][ATTR_LAST_UPDATE] = now.isoformat()
            else:
                self._data["criticality"] = {}
                self._cache_crit = {}
                self._id_crit = id_pub_date[0]
                urls.extend(
                    [
                        CRIT_PATTERN_URL.format(self._id_crit, "today"),
                        CRIT_PATTERN_URL.format(self._id_crit, "tomorrow"),
                    ]
                )
            break

        if urls:
            await self.fetch_all(urls)

            # VIGILANCE swap data at modinight...
            if (
                between_midnight_next_update
                or str(date_today).replace("-", "") != self._id_vigi
            ):
                self._cache_vigi[ATTR_TODAY] = self._cache_vigi.get(ATTR_TOMORROW, {})
                self._cache_vigi[ATTR_TOMORROW] = self._cache_vigi.get(
                    ATTR_AFTERTOMORROW, {}
                )
                self._cache_vigi.pop(ATTR_AFTERTOMORROW, None)
                self._data["vigilance"] = self._cache_vigi
                LOGGER.debug("[%s] Vigilance swap data...", self._location)

            # CRITICALITY swap data at modinight...
            if between_midnight_next_update or date_today != self._pub_date.date():
                for risk in RISKS:
                    day_0 = f"{risk}_{OGGI}"
                    day_1 = f"{risk}_{DOMANI}"
                    self._cache_crit[day_0] = self._cache_crit.get(day_1, {})
                    self._cache_crit[day_1] = {}
                self._cache_crit[ATTR_TODAY] = self._cache_crit.get(ATTR_TOMORROW, {})
                self._cache_crit.pop(ATTR_TOMORROW, None)
                self._data["criticality"] = self._cache_crit
                LOGGER.debug("[%s] Criticality swap data...", self._location)

        LOGGER.debug("[%s] DATA: %s", self._location, self._data)
        return self._data

    async def fetch_id(self, urls):
        tasks = []
        for url in urls:
            task = asyncio.create_task(self.api_fetch("soup", url))
            tasks.append(task)
        results = await asyncio.gather(*tasks)
        return results

    async def fetch_all(self, urls):
        tasks = []
        for url in urls:
            task = asyncio.create_task(self.parse_response(url))
            tasks.append(task)
        results = await asyncio.gather(*tasks)
        return results

    async def parse_response(self, url):
        response = await self.api_fetch("get", url)
        if response:
            if "Vigilanza-Meteorologica" in url:
                await self.get_vigilance(response, url)
            elif "Criticita-Idrogeologica" in url:
                await self.get_criticality(response, url)
            return response

    async def api_fetch(self, method: str, url: str, headers: dict = {}) -> dict:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(TIMEOUT, loop=asyncio.get_event_loop()):
                if method == "soup":
                    resp = await self._session.get(url, headers=headers)
                    resp.raise_for_status()
                    LOGGER.debug(
                        "[%s] Response Soup %s - %s", self._location, url, resp.status
                    )
                    return await resp.text()

                elif method == "get":
                    resp = await self._session.get(url, headers=headers)
                    resp.raise_for_status()
                    LOGGER.debug(
                        "[%s] Got response [%s] for URL: %s",
                        self._location,
                        resp.status,
                        url,
                    )
                    return await resp.json(content_type=None)  # not import json

        except asyncio.TimeoutError as exception:
            LOGGER.error(
                "Timeout error fetching information from %s - %s",
                url,
                exception,
            )
        except (KeyError, TypeError) as exception:
            LOGGER.error(
                "Error parsing information from %s - %s",
                url,
                exception,
            )

        except (aiohttp.ClientError, aiohttp.http_exceptions.HttpProcessingError) as e:
            status = getattr(e, "status", None)
            message = getattr(e, "message", None)
            LOGGER.error("aiohttp exception for %s [%s]:%s", url, status, message)

        except (socket.gaierror) as exception:
            LOGGER.error(
                "Socket Error fetching information from %s - %s",
                url,
                exception,
            )

        except Exception as non_exp_err:
            LOGGER.exception(
                "Non-expected exception occured for %s:  %s",
                url,
                getattr(non_exp_err, "__dict__", {}),
            )

    async def get_vigilance(self, response, url):
        now = dt.datetime.now()
        try:
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

            else:
                vigi = self.get_properties(self._point, response)
                self._cache_vigi[day_en].update(
                    {
                        "icon": VIGI_ICON.get(vigi["id_classificazione"]),
                        ATTR_IMAGE_URL: image_vigi,
                        ATTR_LEVEL: vigi["id_classificazione"],
                        ATTR_PRECIPITATION: vigi["Quantitativi_previsti"],
                    }
                )
                self._cache_vigi.update(
                    {
                        ATTR_ID: self._id_vigi,
                        ATTR_ZONE_NAME: vigi["Nome_Zona"],
                        ATTR_LAST_UPDATE: now.isoformat(),
                    }
                )

            self._data["vigilance"] = self._cache_vigi

        except Exception as exception:
            LOGGER.error("Vigilance Exception! - %s", exception)
            pass

    async def get_criticality(self, response, url):

        now = dt.datetime.now()
        self._pub_date = dt.datetime.strptime(self._id_crit, "%Y%m%d_%H%M")
        expiration_date = dt.datetime.combine(self._pub_date, dt.datetime.min.time())
        try:
            if "today" in url:
                day_en = ATTR_TODAY
                day_it = OGGI
            else:
                day_en = ATTR_TOMORROW
                day_it = DOMANI
                expiration_date += dt.timedelta(days=1)

            self._cache_crit[ATTR_ID] = self._id_crit
            self._cache_crit[ATTR_LAST_UPDATE] = now.isoformat()
            self._cache_crit[ATTR_LINK] = CRIT_BULLETIN_URL
            self._cache_crit[ATTR_PUBLICATION_DATE] = self._pub_date

            prop = self.get_properties(self._point, response)
            self._cache_crit[ATTR_ZONE_NAME] = prop["Nome zona"]
            image = CRIT_IMAGE_URL.format(self._id_crit, day_it)

            self._cache_crit[day_en] = self.get_info_level(
                prop["Rappresentata nella mappa"]
            )
            for risk in RISKS:
                self._cache_crit[f"{risk}_{day_it}"] = {
                    ATTR_RISK: risk.capitalize(),
                    ATTR_IMAGE_URL: image,
                    ATTR_EXPIRES: expiration_date,
                }
                self._cache_crit[f"{risk}_{day_it}"].update(
                    self.get_info_level(prop["Per rischio " + risk])
                )

            self._data["criticality"] = self._cache_crit

        except Exception as exception:
            LOGGER.error("Criticality Exception! - %s", exception)
            pass

    @staticmethod
    def get_info_level(value):
        d = dict()
        d[ATTR_INFO] = value.split("/")[0].rstrip().lstrip()
        d[ATTR_ALERT] = (
            value.split("/")[1]
            .replace("ALLERTA", "")
            .replace("NESSUNA", "VERDE")
            .rstrip()
            .lstrip()
        )
        d[ATTR_LEVEL] = WARNING_ALERT.get(d[ATTR_ALERT])
        return d

    @staticmethod
    def get_properties(point, geojs):
        properties = {}
        for feature in geojs["features"]:
            if not point_in_polygon(point, feature["geometry"]):
                continue
            properties = feature["properties"]
            break
        return properties

    def get_phenomena(self, point, geojs):
        phenomena = []
        radius = self._radius * 1000  # Conv Km to Mt
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
                    # (point["coordinates"][1], point["coordinates"][0]),
                    (self._latitude, self._longitude),
                    (lat, long),
                )
                # Distance in Km
                pointB = {"type": "Point", "coordinates": [long, lat]}
                distance = math.floor(point_distance(point, pointB)) / 1000.00
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


def calculate_initial_compass_bearing(pointA, pointB):
    """
    https://gist.github.com/jeromer/2005586
    https://gist.github.com/RobertSudwarts/acf8df23a16afdb5837f
    """
    if (type(pointA) != tuple) or (type(pointB) != tuple):
        raise TypeError("Only tuples are supported as arguments")
    lat1 = math.radians(pointA[0])
    lat2 = math.radians(pointB[0])
    diffLong = math.radians(pointB[1] - pointA[1])
    x = math.sin(diffLong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (
        math.sin(lat1) * math.cos(lat2) * math.cos(diffLong)
    )
    initial_bearing = math.atan2(x, y)
    initial_bearing = math.degrees(initial_bearing)
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
    return dirs[ix % len(dirs)], math.floor(compass_bearing)
