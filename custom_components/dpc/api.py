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
    WARNING_TYPES,
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

# HEADERS = {"Content-type": "application/json; charset=UTF-8"}

OGGI = "oggi"
DOMANI = "domani"
DOPODOMANI = "dopodomani"
RISKS = ["idraulico", "temporali", "idrogeologico"]
TIMEOUT = 20

VIGI_ICON = {
    1: "mdi:numeric-1-circle",
    2: "mdi:numeric-2-circle",
    3: "mdi:numeric-3-circle",
    4: "mdi:numeric-4-circle",
    5: "mdi:numeric-5-circle",
}
DEFAULT_ICON = "mdi:hazard-lights"
PHENOMENA_ICON = {
    1: "mdi:water",
    2: "mdi:water-plus",
    3: "mdi:snowflake",
    4: "mdi:snowflake-alert",
    5: "mdi:flash",
    6: "mdi:lightning-bolt-outline",
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
        self._data_vigi = {}
        self._data_crit = {}  # criticality
        self._data = {}
        self._update_vigi = False
        self._update_crit = False

    async def async_get_data(self):
        """Get data from the API."""
        now = dt.datetime.now()
        midnight = dt.datetime.combine(now.date(), dt.time())
        midnight_first_update = midnight + self._interval

        between_midnight_next_update = bool(midnight <= now <= midnight_first_update)
        one_day = dt.timedelta(days=1)
        date_today = dt.date.today()
        # tomorrow = date_today + one_day
        point = {"type": "Point", "coordinates": [self._longitude, self._latitude]}

        self._data[ATTR_LAST_UPDATE] = now.isoformat()  ### TODO

        ## VIGILANCE
        parse_vigilance = await self.api_fetch("soup", VIGI_BULLETIN_URL)
        soup_vigilance = BeautifulSoup(parse_vigilance, "html.parser")

        for link in soup_vigilance.find_all(href=re.compile("\.zip$")):
            id_pub_vigi = re.findall("[0-9]+", link.get("href"))

            if not id_pub_vigi:
                continue
            if self._id_vigi == id_pub_vigi[0] and not between_midnight_next_update:
                LOGGER.debug(
                    "[%s] Vigilance Sensor - No update needed. %s",
                    self._location,
                    self._id_vigi,
                )
                self._data["vigilance"][ATTR_LAST_UPDATE] = now.isoformat()  # TODO
                self._update_vigi = False
            else:
                self._update_vigi = True
                self._id_vigi = id_pub_vigi[0]
            break

        if self._update_vigi:
            try:
                self._data_vigi = {}

                image_vigi_today = VIGI_IMAGE_URL.format(self._id_vigi, OGGI)
                image_vigi_tomorrow = VIGI_IMAGE_URL.format(self._id_vigi, DOMANI)

                for day in [OGGI, DOMANI, DOPODOMANI]:
                    url = VIGI_PATTERN_URL.format(self._id_vigi, day)
                    url2 = VIGI_PATTERN_URL.format(self._id_vigi, f"fenomeni_{day}")
                    if day == OGGI:
                        js_vi_today = await self.api_fetch("get", url)
                        vigi_today = self.get_properties(point, js_vi_today)
                        js_ph_today = await self.api_fetch("get", url2)
                        pheno_today = self.get_phenomena(point, js_ph_today)

                    elif day == DOMANI:
                        js_vi_1day = await self.api_fetch("get", url)
                        vigi_1day = self.get_properties(point, js_vi_1day)
                        js_ph_1day = await self.api_fetch("get", url2)
                        pheno_1day = self.get_phenomena(point, js_ph_1day)

                    elif day == DOPODOMANI:
                        js_vi_2days = await self.api_fetch("get", url)
                        vigi_2days = self.get_properties(point, js_vi_2days)
                        ph_2days = await self.api_fetch("get", url2)
                        pheno_2days = self.get_phenomena(point, ph_2days)

                self._data_vigi.update(
                    {
                        ATTR_ID: self._id_vigi,
                        ATTR_ZONE_NAME: vigi_today["Nome_Zona"],
                        ATTR_LAST_UPDATE: now.isoformat(),
                        ATTR_TODAY: {
                            "icon": VIGI_ICON.get(vigi_today["id_classificazione"]),
                            ATTR_IMAGE_URL: image_vigi_today,
                            ATTR_LEVEL: vigi_today["id_classificazione"],
                            ATTR_PRECIPITATION: vigi_today["Quantitativi_previsti"],
                            ATTR_PHENOMENA: pheno_today,
                        },
                        ATTR_TOMORROW: {
                            "icon": VIGI_ICON.get(vigi_1day["id_classificazione"]),
                            ATTR_IMAGE_URL: image_vigi_tomorrow,
                            ATTR_LEVEL: vigi_1day["id_classificazione"],
                            ATTR_PRECIPITATION: vigi_1day["Quantitativi_previsti"],
                            ATTR_PHENOMENA: pheno_1day,
                        },
                        ATTR_AFTERTOMORROW: {
                            "icon": VIGI_ICON.get(vigi_2days["id_classificazione"]),
                            ATTR_LEVEL: vigi_2days["id_classificazione"],
                            ATTR_PRECIPITATION: vigi_2days["Quantitativi_previsti"],
                            ATTR_PHENOMENA: pheno_2days,
                        },
                    }
                )

                # swap data at modinight
                if (
                    between_midnight_next_update
                    or str(date_today).replace("-", "") != self._id_vigi
                ):
                    self._data_vigi[ATTR_TODAY] = self._data_vigi[ATTR_TOMORROW]
                    self._data_vigi[ATTR_TOMORROW] = self._data_vigi[ATTR_AFTERTOMORROW]
                    self._data_vigi.pop(ATTR_AFTERTOMORROW, None)

                self._data["vigilance"] = self._data_vigi

            except Exception as exception:
                LOGGER.error("Vigilance Exception! - %s", exception)
                pass
            LOGGER.debug("[%s] VIGILANCE: %s", self._location, self._data_vigi)

        ## CRITICAL
        parse_criticality = await self.api_fetch("soup", CRIT_BULLETIN_URL)
        soup_criticality = BeautifulSoup(parse_criticality, "html.parser")
        for link in soup_criticality.find_all(href=re.compile("shp\.zip$")):
            id_pub_date = re.findall("[0-9]+_[0-9]+", link.get("href"))

            if not id_pub_date:
                continue
            if self._id_crit == id_pub_date[0] and not between_midnight_next_update:
                LOGGER.debug(
                    "[%s] Criticality Sensor - No update needed. %s",
                    self._location,
                    self._id_crit,
                )
                self._data["criticality"][ATTR_LAST_UPDATE] = now.isoformat()
                self._update_crit = False
            else:
                self._update_crit = True
                self._id_crit = id_pub_date[0]  # string
            break

        if self._update_crit:
            try:
                self._pub_date = dt.datetime.strptime(self._id_crit, "%Y%m%d_%H%M")

                self._data_crit = {}  # Delete cache
                self._data_crit[ATTR_ID] = self._id_crit
                self._data_crit[ATTR_LAST_UPDATE] = now.isoformat()
                self._data_crit[ATTR_LINK] = CRIT_BULLETIN_URL
                self._data_crit[ATTR_PUBLICATION_DATE] = self._pub_date

                for warning in WARNING_TYPES:
                    self._data_crit[warning] = {}  # default_data

                expiration_date = dt.datetime.combine(
                    self._pub_date, dt.datetime.min.time()
                )

                url_today = CRIT_PATTERN_URL.format(self._id_crit, "today")
                url_tomorrow = CRIT_PATTERN_URL.format(self._id_crit, "tomorrow")
                js_today = await self.api_fetch("get", url_today)
                js_tomorrow = await self.api_fetch("get", url_tomorrow)

                # for feat_today, feat_toorrow in zip(js_today["features"], js_tomorrow["features"]):
                for idx, feature in enumerate(js_today["features"]):
                    polygon = feature["geometry"]
                    if not point_in_polygon(point, polygon):
                        continue
                    # TODAY
                    prop_today = feature["properties"]
                    self._data_crit[ATTR_ZONE_NAME] = prop_today["Nome zona"]
                    image = CRIT_IMAGE_URL.format(self._id_crit, OGGI)

                    self._data_crit[ATTR_TODAY] = self.get_info_level(
                        prop_today["Rappresentata nella mappa"]
                    )
                    for risk in RISKS:
                        self._data_crit[f"{risk}_{OGGI}"] = {
                            ATTR_RISK: risk.capitalize(),
                            ATTR_IMAGE_URL: image,
                            ATTR_EXPIRES: expiration_date,
                        }
                        self._data_crit[f"{risk}_{OGGI}"].update(
                            self.get_info_level(prop_today["Per rischio " + risk])
                        )

                    # TOMORROW
                    prop_tomorrow = js_tomorrow["features"][idx]["properties"]
                    image = CRIT_IMAGE_URL.format(self._id_crit, DOMANI)
                    expiration_date += one_day

                    self._data_crit[ATTR_TOMORROW] = self.get_info_level(
                        prop_tomorrow["Rappresentata nella mappa"]
                    )
                    for risk in RISKS:
                        self._data_crit[f"{risk}_{DOMANI}"] = {
                            ATTR_RISK: risk.capitalize(),
                            ATTR_IMAGE_URL: image,
                            ATTR_EXPIRES: expiration_date,
                        }
                        self._data_crit[f"{risk}_{DOMANI}"].update(
                            self.get_info_level(prop_tomorrow["Per rischio " + risk])
                        )
                    break

                # swap data at modinight...
                if between_midnight_next_update or date_today != self._pub_date.date():
                    for risk in RISKS:
                        day_0 = f"{risk}_{OGGI}"
                        day_1 = f"{risk}_{DOMANI}"
                        self._data_crit[day_0] = self._data_crit[day_1]
                        self._data_crit[day_1] = {}
                    self._data_crit[ATTR_TODAY] = self._data_crit[ATTR_TOMORROW]
                    self._data_crit.pop(ATTR_TOMORROW, None)

                self._data["criticality"] = self._data_crit

            except Exception as exception:
                LOGGER.error("Criticality Exception! - %s", exception)
                pass
            LOGGER.debug("[%s] CRITICALITY: %s", self._location, self._data_crit)

        LOGGER.debug("\n\n[%s] DATA: %s", self._location, self._data)
        return self._data

    async def api_fetch(self, method: str, url: str, headers: dict = {}) -> dict:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(TIMEOUT, loop=asyncio.get_event_loop()):
                if method == "soup":
                    resp = await self._session.get(url, headers=headers)
                    LOGGER.debug(
                        "[%s] Response Soup %s - %s", self._location, url, resp
                    )
                    return await resp.text()

                elif method == "get":
                    resp = await self._session.get(url, headers=headers)
                    LOGGER.debug(
                        "[%s] Response Json %s - %s", self._location, url, resp
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
        except (aiohttp.ClientError, socket.gaierror) as exception:
            LOGGER.error(
                "Error fetching information from %s - %s",
                url,
                exception,
            )
        except Exception as exception:  # pylint: disable=broad-except
            LOGGER.error("Something really wrong happened! - %s", exception)

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

    # @staticmethod
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
