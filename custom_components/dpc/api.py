"""Dpc API Client."""
import asyncio
import datetime
import re
import socket

import aiohttp
import async_timeout
from bs4 import BeautifulSoup
from geojson_utils import point_in_polygon

from .const import LOGGER, WARNING_ALERT, WARNING_TYPES

BASE_URL = (
    "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-"
    "Idrogeologica-Idraulica/master/files/geojson/{}_{}.json"
)
BULLETTIN_URL = (
    "https://mappe.protezionecivile.gov.it/it/mappe-rischi/bollettino-di-criticita"
)

IMAGE_URL = (
    "https://raw.githubusercontent.com/pcm-dpc/DPC-Bollettini-Criticita-"
    "Idrogeologica-Idraulica/master/files/preview/{}_{}.png"
)

# HEADERS = {"Content-type": "application/json; charset=UTF-8"}

OGGI = "oggi"
DOMANI = "domani"
RISKS = ["idraulico", "temporali", "idrogeologico"]
TIMEOUT = 20
TODAY = "today"
TOMORROW = "tomorrow"


class DpcApiClient:
    def __init__(
        self,
        location_name: str,
        latitude: float,
        longitude: float,
        session: aiohttp.ClientSession,
        update_interval: datetime.timedelta,
    ) -> None:
        """Dpc API Client."""
        self._location = location_name
        self._latitude = latitude
        self._longitude = longitude
        self._session = session
        self._interval = update_interval
        self._dpc_id = None
        self._pub_date = None
        self._data = {}

    async def async_get_data(self):
        """Get data from the API."""
        now = datetime.datetime.now()
        midnight = datetime.datetime.combine(now.date(), datetime.time())
        midnight_first_update = midnight + self._interval
        between_midnight_first_update = bool(midnight <= now <= midnight_first_update)

        self._data["last_update"] = now.isoformat()  ### TODO

        text = await self.api_fetch("soup", BULLETTIN_URL)
        soup = BeautifulSoup(text, "html.parser")

        for link in soup.find_all(href=re.compile("shp\.zip$")):
            id_pub_date = re.findall("[0-9]+_[0-9]+", link.get("href"))

            if id_pub_date:
                if self._dpc_id == id_pub_date[0] and not between_midnight_first_update:
                    LOGGER.debug(
                        "[%s] No update needed. %s", self._location, self._dpc_id
                    )
                    return self._data

                self._dpc_id = id_pub_date[0]  # string
                self._pub_date = datetime.datetime.strptime(self._dpc_id, "%Y%m%d_%H%M")
                LOGGER.debug("[%s] Shape Link: %s", self._location, link)
                break

        # if not self._dpc_id:
        #     return {}

        self._data = {}  # Delete cache
        self._data["id"] = self._dpc_id
        self._data["last_update"] = now.isoformat()
        self._data["link"] = BULLETTIN_URL
        self._data["publication_date"] = self._pub_date

        for warning in WARNING_TYPES:
            self._data[warning] = {}  # default_data

        point = {"type": "Point", "coordinates": [self._longitude, self._latitude]}
        one_day = datetime.timedelta(days=1)
        today = datetime.date.today()
        tomorrow = today + one_day
        expiration_date = datetime.datetime.combine(
            self._pub_date, datetime.datetime.min.time()
        )

        js_today = await self.api_fetch("get", BASE_URL.format(self._dpc_id, TODAY))
        js_tomorrow = await self.api_fetch(
            "get", BASE_URL.format(self._dpc_id, TOMORROW)
        )
        # for feat_today, feat_toorrow in zip(js_today["features"], js_tomorrow["features"]):
        for idx, feature in enumerate(js_today["features"]):
            polygon = feature["geometry"]
            if point_in_polygon(point, polygon):

                # TODAY
                prop_today = feature["properties"]

                self._data["zone_name"] = prop_today["Nome zona"]
                image = IMAGE_URL.format(self._dpc_id, OGGI)

                if today == self._pub_date.date():
                    self._data[TODAY] = self.fix_info_string(
                        prop_today["Rappresentata nella mappa"]
                    )
                    for risk in RISKS:
                        self._data[f"{risk}_{OGGI}"] = {
                            "risk": risk.capitalize(),
                            "image_url": image,
                            "expires": expiration_date,
                        }
                        self._data[f"{risk}_{OGGI}"].update(
                            self.fix_info_string(prop_today["Per rischio " + risk])
                        )

                # TOMORROW
                prop_tomorrow = js_tomorrow["features"][idx]["properties"]

                image = IMAGE_URL.format(self._dpc_id, DOMANI)
                expiration_date += one_day
                if tomorrow == self._pub_date.date() + one_day:
                    day = DOMANI
                    day_en = TOMORROW

                elif today == self._pub_date.date() + one_day:
                    day = OGGI
                    day_en = TODAY
                else:
                    break
                self._data[day_en] = self.fix_info_string(
                    prop_tomorrow["Rappresentata nella mappa"]
                )
                for risk in RISKS:
                    self._data[f"{risk}_{day}"] = {
                        "risk": risk.capitalize(),
                        "image_url": image,
                        "expires": expiration_date,
                    }
                    self._data[f"{risk}_{day}"].update(
                        self.fix_info_string(prop_tomorrow["Per rischio " + risk])
                    )
                break

        LOGGER.debug("[%s] FINAL DATA: %s", self._location, self._data)
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
    def fix_info_string(value):
        d = dict()
        d["info"] = value.split("/")[0].rstrip().lstrip()
        d["alert"] = (
            value.split("/")[1]
            .replace("ALLERTA", "")
            .replace("NESSUNA", "VERDE")
            .rstrip()
            .lstrip()
        )
        d["level"] = WARNING_ALERT.get(d["alert"])
        return d
