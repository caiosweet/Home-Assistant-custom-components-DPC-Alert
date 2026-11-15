"""The latest DPC bulletins of every place, downloaded once for all of them."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import math
import time

from aiodpc import (
    BulletinKind,
    CriticalityBulletin,
    CriticalityMap,
    DpcClient,
    DpcLocationError,
    Location,
    VigilanceBulletin,
    VigilanceMap,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_RADIUS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.hass_dict import HassKey

from .const import (
    CONF_MUNICIPALITY,
    DEFAULT_RADIUS,
    DOMAIN,
    LATEST_ID_CHECK_INTERVAL,
    LOGGER,
)


@dataclass(frozen=True, slots=True)
class Place:
    """A place to read the bulletins at, as configured in a config entry."""

    location: Location
    phenomena_within_km: float

    @classmethod
    def of(cls, entry: ConfigEntry) -> Place:
        """Return the place of a config entry."""
        return cls(
            location=Location(
                entry.data[CONF_LATITUDE],
                entry.data[CONF_LONGITUDE],
                municipality=entry.options.get(CONF_MUNICIPALITY) or None,
            ),
            phenomena_within_km=max(
                float(entry.options.get(CONF_RADIUS, DEFAULT_RADIUS)), 0.0
            ),
        )


class DpcBulletins:
    """The latest DPC bulletins of every configured place.

    The config entries share it. A bulletin is the same file for the whole of
    Italy, so when DPC publishes a new one it is downloaded once and read at
    every place, in an executor because reading it takes some CPU time.
    """

    def __init__(self, hass: HomeAssistant, client: DpcClient) -> None:
        """Initialize the bulletins, downloaded with the client."""
        self._places: dict[str, Place] = {}
        self._criticality = _SharedBulletin[CriticalityMap, CriticalityBulletin](
            hass,
            client,
            BulletinKind.CRITICALITY,
            self._places,
            get_map=lambda bulletin_id: client.get_criticality_map(
                bulletin_id=bulletin_id
            ),
            read=lambda criticality, place: criticality.at(place.location),
        )
        self._vigilance = _SharedBulletin[VigilanceMap, VigilanceBulletin](
            hass,
            client,
            BulletinKind.VIGILANCE,
            self._places,
            get_map=lambda bulletin_id: client.get_vigilance_map(
                bulletin_id=bulletin_id
            ),
            read=lambda vigilance, place: vigilance.at(
                place.location, phenomena_within_km=place.phenomena_within_km
            ),
        )

    def add_place(self, entry_id: str, place: Place) -> None:
        """Add the place of a config entry."""
        self._places[entry_id] = place

    def remove_place(self, entry_id: str) -> None:
        """Remove the place of a config entry, with its readings."""
        self._places.pop(entry_id, None)
        self._criticality.forget(entry_id)
        self._vigilance.forget(entry_id)

    async def criticality(self, entry_id: str) -> CriticalityBulletin:
        """Return the latest criticality bulletin of the place of an entry.

        Raises :class:`aiodpc.DpcError`, e.g. :class:`aiodpc.DpcLocationError`
        when the place is in no alert zone.
        """
        return await self._criticality.reading(entry_id)

    async def vigilance(self, entry_id: str) -> VigilanceBulletin:
        """Return the latest vigilance bulletin of the place of an entry.

        Raises :class:`aiodpc.DpcError`, as :meth:`criticality`.
        """
        return await self._vigilance.reading(entry_id)


DATA_BULLETINS: HassKey[DpcBulletins] = HassKey(f"{DOMAIN}_bulletins")


@callback
def async_get_bulletins(hass: HomeAssistant) -> DpcBulletins:
    """Return the bulletins shared by the config entries."""
    if (bulletins := hass.data.get(DATA_BULLETINS)) is None:
        client = DpcClient(async_get_clientsession(hass))
        bulletins = hass.data[DATA_BULLETINS] = DpcBulletins(hass, client)
    return bulletins


class _SharedBulletin[MapT, BulletinT]:
    """The latest bulletin of a kind, read at every place."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: DpcClient,
        kind: BulletinKind,
        places: dict[str, Place],
        *,
        get_map: Callable[[str], Awaitable[MapT]],
        read: Callable[[MapT, Place], BulletinT],
    ) -> None:
        self._hass = hass
        self._client = client
        self._kind = kind
        self._places = places
        self._get_map = get_map
        self._read = read
        self._lock = asyncio.Lock()
        self._latest_id: str | None = None
        self._checked_at = -math.inf
        self._bulletin_id: str | None = None
        """ID of the bulletin of the readings."""
        self._readings: dict[str, BulletinT | DpcLocationError] = {}

    def forget(self, entry_id: str) -> None:
        """Forget the reading of a place."""
        self._readings.pop(entry_id, None)

    async def reading(self, entry_id: str) -> BulletinT:
        """Return the latest bulletin at the place of an entry.

        The bulletin is downloaded only when DPC publishes a new one, or when
        a place has not been read yet; it is then read at every place.
        """
        async with self._lock:
            latest_id = await self._latest_id_of_dpc()
            if latest_id != self._bulletin_id or entry_id not in self._readings:
                await self._read_everywhere(latest_id)
        reading = self._readings[entry_id]
        if isinstance(reading, DpcLocationError):
            raise DpcLocationError(*reading.args)
        return reading

    async def _latest_id_of_dpc(self) -> str:
        """Return the ID of the latest bulletin, checked once a minute at most.

        The places update one after the other, so they share the check.
        """
        if self._latest_id is None or (
            time.monotonic() - self._checked_at >= LATEST_ID_CHECK_INTERVAL
        ):
            self._latest_id = await self._client.latest_bulletin_id(self._kind)
            self._checked_at = time.monotonic()
        return self._latest_id

    async def _read_everywhere(self, bulletin_id: str) -> None:
        """Download a bulletin and read it at the places that need it.

        A new bulletin is read at every place; otherwise only the places not
        read yet are. The places are taken once the bulletin is downloaded,
        so that the places added meanwhile, e.g. at startup, are read too.
        """
        LOGGER.debug("Downloading the %s bulletin %s", self._kind, bulletin_id)
        bulletin_map = await self._get_map(bulletin_id)
        is_new = bulletin_id != self._bulletin_id
        places = {
            entry_id: place
            for entry_id, place in self._places.items()
            if is_new or entry_id not in self._readings
        }
        readings = await self._hass.async_add_executor_job(
            self._read_places, bulletin_map, places
        )
        if is_new:
            self._readings = readings
            self._bulletin_id = bulletin_id
        else:
            self._readings |= readings

    def _read_places(
        self, bulletin_map: MapT, places: dict[str, Place]
    ) -> dict[str, BulletinT | DpcLocationError]:
        """Read a bulletin at each place; run in an executor."""
        readings: dict[str, BulletinT | DpcLocationError] = {}
        for entry_id, place in places.items():
            try:
                readings[entry_id] = self._read(bulletin_map, place)
            except DpcLocationError as err:
                readings[entry_id] = err
        return readings
