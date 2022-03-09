"""Dpc API Client."""
from __future__ import annotations

import asyncio
import json
import re
import socket
from datetime import date, datetime, time, timedelta

import aiohttp
import async_timeout

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
from .geojson_utils import (
    calculate_initial_compass_bearing,
    geometry_within_radius,
    point_distance,
    point_in_polygon,
)

CRIT_API_URL = "https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica/contents/files"
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

VIGI_API_URL = (
    "https://api.github.com/repos/pcm-dpc/DPC-Bollettini-Vigilanza-Meteorologica/contents/files"
)
VIGI_BULLETIN_URL = "https://mappe.protezionecivile.it/it/mappe-rischi/bollettino-di-vigilanza/"
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
TIMEOUT = 10


class DpcApiClient:
    def __init__(
        self,
        location_name: str,
        latitude: float,
        longitude: float,
        municipality: str,
        radius: int,
        session: aiohttp.ClientSession,
        update_interval: timedelta,
    ) -> None:
        """Dpc API Client."""
        self._name = location_name
        self._latitude = latitude
        self._longitude = longitude
        self._municipality = municipality
        self._radius = radius
        self._session = session
        self._interval = update_interval

        self._data = {}
        self._pub_date_crit = None
        self._pub_date_vigi = None
        self._id_crit = None
        self._id_vigi = None
        self._point = {"type": "Point", "coordinates": [longitude, latitude]}
        self._str_today = None
        self._str_yesterday = None
        self._urls = []

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
        new_id_crit = None
        new_id_vigi = None
        is_swap_criticality = False
        is_swap_vigilance = False

        tasks = []
        for url in [CRIT_API_URL, VIGI_API_URL]:
            tasks.append(self.get_id_from_api_(url))
        result = await asyncio.gather(*tasks)
        new_id_crit, new_id_vigi = result

        if not new_id_crit:
            new_id_crit = await self.get_id_from_site_(CRIT_BULLETIN_URL)

        if not new_id_vigi:
            new_id_vigi = await self.get_id_from_site_(VIGI_BULLETIN_URL)

        LOGGER.debug("IDS: %s - %s", new_id_crit, new_id_vigi)
        if not (new_id_crit or new_id_vigi):
            LOGGER.error("Sorry, no IDs fetched!!")
            return self._data or {}

        if new_id_crit:
            if self._id_crit != new_id_crit:
                criticality_days = ["today", "tomorrow"]
                self._id_crit = new_id_crit
                self._pub_date_crit = datetime.strptime(self._id_crit, "%Y%m%d_%H%M")

                if date_today != self._pub_date_crit.date():
                    is_swap_criticality = True
                    criticality_days.remove("today")
                for day in criticality_days:
                    self._urls.extend([CRIT_PATTERN_URL.format(self._id_crit, day)])
            elif between_midnight_first_update:
                self.swapping_data_criticality()
            else:
                LOGGER.debug("[%s] Criticality No changes. %s", self._name, self._id_crit)

        if new_id_vigi:
            if self._id_vigi != new_id_vigi:
                vigilance_days = [OGGI, DOMANI, DOPODOMANI]
                self._id_vigi = new_id_vigi
                self._pub_date_vigi = datetime.strptime(self._id_vigi, "%Y%m%d")

                if date_today != self._pub_date_vigi.date():
                    is_swap_vigilance = True
                    vigilance_days.remove(OGGI)
                for day in vigilance_days:
                    self._urls.extend(
                        [
                            VIGI_PATTERN_URL.format(self._id_vigi, day),
                            VIGI_PATTERN_URL.format(self._id_vigi, f"fenomeni_{day}"),
                        ]
                    )
            elif between_midnight_first_update:
                self.swapping_data_vigilance()
            else:
                LOGGER.debug("[%s] Vigilance No changes. %s", self._name, self._id_vigi)

        if self._urls:
            await self.multi_fetch(self._urls)

            if is_swap_criticality:
                self.swapping_data_criticality()
            if is_swap_vigilance:
                self.swapping_data_vigilance()

        if CRITICALITY in self._data:
            self._data[CRITICALITY][ATTR_LAST_UPDATE] = now.isoformat()
        if VIGILANCE in self._data:
            self._data[VIGILANCE][ATTR_LAST_UPDATE] = now.isoformat()

        return self._data

    async def get_id_from_api_(self, url) -> str:
        try:
            resp = await self.api_fetch(url)
            data = resp.get(url, "")  # [{"name": "20200101_1530.json"}]
            if not (resp and data):
                return
            jdata = json.loads(data)
            str_days = (self._str_today, self._str_yesterday)

            for item in reversed(jdata):
                if not item["name"].startswith(str_days):
                    continue
                id = re.split(".json", item["name"])[0]
                LOGGER.debug("[%s] From the Github API I got the ID: %s", self._name, id)
                # return re.split("_all.zip|.zip", item["name"])[0]
                return id
        except ValueError as e:  # includes simplejson.decoder.JSONDecodeError
            LOGGER.debug("Decoding JSON has failed: %s", e)

    async def get_id_from_site_(self, url) -> str:
        resp = await self.api_fetch(url)
        html = resp.get(url, "")
        id_pub = [match[1] for match in REGEX_DPC_ID.findall(html)]
        if id_pub:
            id = id_pub[0]
            LOGGER.debug("[%s] From the SITE I got the ID: %s", self._name, id)
            return id  # id_pub[0]

    async def api_fetch(self, url: str) -> dict:
        """Get information from the API."""
        fetched = {}
        try:
            async with async_timeout.timeout(TIMEOUT):
                r = await self._session.get(url, raise_for_status=True)
                fetched = {url: await r.text()}

        except asyncio.CancelledError as e:
            LOGGER.error("Cancelled error fetching information from %s - %s", url, e)

        except asyncio.TimeoutError as e:
            LOGGER.error("Timeout error fetching information from %s [%s] - %s", url, TIMEOUT, e)

        except (KeyError, TypeError) as e:
            LOGGER.error("Error parsing information from %s - %s", url, e)

        except (aiohttp.ClientError, socket.gaierror) as e:
            LOGGER.error("Error fetching information from %s - %s", url, e)

        except Exception as unexpected_error:  # pylint: disable=broad-except
            LOGGER.exception(
                "Unexpected error exception occured for %s:  %s",
                url,
                getattr(unexpected_error, "__dict__", {}),
            )

        finally:
            return fetched

    async def multi_fetch(self, urls: list) -> list:
        """Fetching responses for multiple urls."""
        return await asyncio.gather(*[self.fetch_and_parse(url) for url in urls])

    async def fetch_and_parse(self, url: str) -> dict:
        try:
            result = await self.api_fetch(url)
            if result:
                response = json.loads(result.get(url))  #  result.get(url)
                if "Vigilanza-Meteorologica" in url:
                    await self.get_vigilance(response, url)
                else:  # "Criticita-Idrogeologica" in url:
                    await self.get_criticality(response, url)

        except json.decoder.JSONDecodeError as e:  # ValueError
            LOGGER.warning("[%s] Error decoding DPC Data [%s]", self._name, e)

        except Exception as e:
            LOGGER.warning("[%s] JsonData Fetched all: [%s]", self._name, e)

    async def get_criticality(self, response: dict, url: str) -> dict:
        short_url = url.split("geojson/")[1]
        LOGGER.debug("[%s] Criticality Update %s", self._name, short_url)
        expiration_date = datetime.combine(self._pub_date_crit, datetime.min.time())
        try:
            if "today" in url:
                day_en = ATTR_TODAY
                day_it = OGGI
            else:
                day_en = ATTR_TOMORROW
                day_it = DOMANI
                expiration_date += timedelta(days=1)

            criticallity = self._data.get(CRITICALITY, {})

            prop = self.get_properties(self._municipality, self._point, response)
            criticallity[ATTR_ZONE_NAME] = prop.get(ATTR_ZONE_NAME, prop["Nome zona"])
            image = CRIT_IMAGE_URL.format(self._id_crit, day_it)

            criticallity[day_en] = self.get_info_level(prop["Rappresentata nella mappa"])
            criticallity[day_en].update(
                {
                    ATTR_IMAGE_URL: image,
                    ATTR_EXPIRES: expiration_date,
                    ATTR_ZONE_NAME: prop["Nome zona"],
                }
            )

            for risk in RISKS:
                criticallity[f"{risk}_{day_it}"] = {
                    ATTR_RISK: risk.capitalize(),
                    ATTR_IMAGE_URL: image,
                    ATTR_EXPIRES: expiration_date,
                    "icon": CRIT_ICON.get(risk),
                }
                criticallity[f"{risk}_{day_it}"].update(
                    self.get_info_level(prop["Per rischio " + risk])
                )

            criticallity.update(
                {
                    ATTR_ID: self._id_crit,
                    ATTR_LINK: CRIT_BULLETIN_URL,
                    ATTR_PUBLICATION_DATE: self._pub_date_crit,
                }
            )

            self._data[CRITICALITY] = criticallity
            self._urls.remove(url)

        except Exception as exception:
            LOGGER.error("Criticality Exception! - %s", exception)
            pass

    async def get_vigilance(self, response: dict, url: str) -> dict:
        short_url = url.split("geojson/")[1]
        LOGGER.debug("[%s] Vigilance Update %s", self._name, short_url)
        try:
            day_en = ""
            image_vigi = ""
            if "_oggi" in url:
                day_en = ATTR_TODAY
                image_vigi = VIGI_IMAGE_URL.format(self._id_vigi, OGGI)
            elif "_domani" in url:
                day_en = ATTR_TOMORROW
                image_vigi = VIGI_IMAGE_URL.format(self._id_vigi, DOMANI)
            elif "_dopodomani" in url:
                day_en = ATTR_AFTERTOMORROW
                image_vigi = None

            vigilance = self._data.get(VIGILANCE, {})
            vigilance[day_en] = vigilance.get(day_en, {})

            if "_fenomeni" in url:
                phenomena = self.get_phenomena(self._point, response)
                vigilance[day_en].update({ATTR_PHENOMENA: phenomena})

            else:  # "Vigilanza-Meteorologica" in url:
                prop = self.get_properties(self._municipality, self._point, response)

                vigilance[day_en].update(
                    {
                        "icon": VIGI_ICON.get(prop["id_classificazione"]),
                        ATTR_IMAGE_URL: image_vigi,
                        ATTR_LEVEL: prop["id_classificazione"],
                        ATTR_PRECIPITATION: prop["Quantitativi_previsti"],
                        ATTR_ZONE_NAME: prop["Nome_Zona"],
                    }
                )

                vigilance.update(
                    {
                        ATTR_ID: self._id_vigi,
                        ATTR_PUBLICATION_DATE: self._pub_date_vigi,
                        ATTR_ZONE_NAME: prop.get(ATTR_ZONE_NAME, prop["Nome_Zona"]),
                    }
                )
            self._data[VIGILANCE] = vigilance
            self._urls.remove(url)

        except Exception as exception:
            LOGGER.error("Vigilance Exception! - %s", exception)
            pass

    @staticmethod
    def get_info_level(value: str) -> dict:
        d = {}
        d[ATTR_INFO] = value.split("/")[0].rstrip().lstrip()
        d[ATTR_ALERT] = value.split("/")[1].lstrip()
        d[ATTR_LEVEL] = WARNING_ALERT.get(d[ATTR_ALERT], 0)
        return d

    def get_properties(self, comune_conf, point, geojs) -> dict:
        def _from_city():
            LOGGER.debug("[%s] Getting property from the city [%s]", self._name, comune_conf)
            zones = []
            point_in_zone = ""
            for feature in geojs["features"]:
                prop = feature["properties"]
                # Different key (Comuni, comuni) for Criticality end Vigilance
                comuni = prop.get("Comuni", prop.get("comuni"))
                comune = [city.lower() for city in comuni if comune_conf.lower() == city.lower()]

                if not comune:
                    continue

                # Getting zone from coordinates
                if point_in_polygon(point, feature["geometry"]):
                    # Different key (Nome zona, Nome_Zona) for Criticality end Vigilance
                    point_in_zone = prop.get("Nome zona", prop.get("Nome_Zona"))
                    LOGGER.debug("Point In Polygon. Zone: [%s]", point_in_zone)

                critical = prop.get("Rappresentata nella mappa")
                if critical:
                    id_class = self.get_info_level(critical).get(ATTR_LEVEL)
                    # add id_classificaione for the criticality sorted
                    prop.update({"id_classificazione": id_class})
                zones.append(prop)

                LOGGER.debug(
                    "City: %s - Zona: %s - ID: %s - Info: %s",
                    comune,
                    prop.get("Nome zona", prop.get("Nome_Zona")),
                    prop.get("id_classificazione"),
                    critical,
                )

            if not zones:
                LOGGER.error("[%s] City not found [%s]", self._name, comune_conf)
                return _from_point()

            zone = sorted(zones, key=lambda i: i["id_classificazione"], reverse=True)[0]
            zone.update({ATTR_ZONE_NAME: point_in_zone})
            return zone

        def _from_point():
            LOGGER.debug("[%s] Getting properties from coordinates %s", self._name, point)
            for feature in geojs["features"]:
                if not point_in_polygon(point, feature["geometry"]):
                    continue
                return feature["properties"]
            LOGGER.error("[%s] Not point in polygons [%s]", self._name, point)

        return _from_city() if comune_conf else _from_point()

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
                distance = round(point_distance(point, pointB) / 1000, 1)
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

    def swapping_data_criticality(self):
        swap_data = self._data.get(CRITICALITY, {})
        if swap_data:
            for risk in RISKS:
                day_0 = f"{risk}_{OGGI}"
                day_1 = f"{risk}_{DOMANI}"
                swap_data[day_0] = swap_data.get(day_1, {})
                swap_data[day_1] = {}
            swap_data[ATTR_TODAY] = swap_data.get(ATTR_TOMORROW, {})
            swap_data.pop(ATTR_TOMORROW, None)
            self._data[CRITICALITY] = swap_data
            LOGGER.debug("[%s] Swapped data for Criticality", self._name)

    def swapping_data_vigilance(self):
        swap_data = self._data.get(VIGILANCE, {})
        if swap_data:
            swap_data[ATTR_TODAY] = swap_data.get(ATTR_TOMORROW, {})
            swap_data[ATTR_TOMORROW] = swap_data.get(ATTR_AFTERTOMORROW, {})
            swap_data.pop(ATTR_AFTERTOMORROW, None)
            self._data[VIGILANCE] = swap_data
            LOGGER.debug("[%s] Swapped data for Vigilance", self._name)


class DpcApiException(Exception):
    """Base Exception for Dpc error."""

    pass
