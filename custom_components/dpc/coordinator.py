"""Coordinator of the DPC bulletins of a location."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from aiodpc import (
    BulletinKind,
    CriticalityBulletin,
    DpcClient,
    DpcError,
    Location,
    VigilanceBulletin,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_RADIUS,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_MUNICIPALITY,
    DEFAULT_RADIUS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    RETRY_INTERVAL,
)


@dataclass(frozen=True)
class LatestBulletin[BulletinT: (CriticalityBulletin, VigilanceBulletin)]:
    """A bulletin and when DPC last confirmed that it is the latest one."""

    bulletin: BulletinT
    checked_at: datetime


@dataclass(frozen=True, slots=True)
class DpcData:
    """The latest DPC bulletins of the location; None until one is fetched."""

    criticality: LatestBulletin[CriticalityBulletin] | None = None
    vigilance: LatestBulletin[VigilanceBulletin] | None = None


class DpcDataUpdateCoordinator(DataUpdateCoordinator[DpcData]):
    """Keep the latest DPC bulletins of the location of a config entry.

    Each update only checks the IDs of the latest bulletins, and downloads a
    bulletin again only when DPC has published a new one. When a bulletin cannot
    be updated, the previous one is kept, since its days stay valid until they
    are over, and the next update comes sooner.
    """

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: DpcClient
    ) -> None:
        """Initialize the coordinator of a config entry."""
        self.location = Location(
            entry.data[CONF_LATITUDE],
            entry.data[CONF_LONGITUDE],
            municipality=entry.options.get(CONF_MUNICIPALITY) or None,
        )
        self.phenomena_within_km = max(
            float(entry.options.get(CONF_RADIUS, DEFAULT_RADIUS)), 0.0
        )
        self.scan_interval = timedelta(
            minutes=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        self.platforms: list[str] = []
        self._client = client
        self._criticality = _BulletinTracker(
            entry.title, BulletinKind.CRITICALITY, client, self._get_criticality
        )
        self._vigilance = _BulletinTracker(
            entry.title, BulletinKind.VIGILANCE, client, self._get_vigilance
        )
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=self.scan_interval,
        )
        self.data = DpcData()

    async def _async_update_data(self) -> DpcData:
        """Return the latest bulletins, downloading those published since."""
        trackers = (self._criticality, self._vigilance)
        await asyncio.gather(*(tracker.refresh() for tracker in trackers))

        errors = [tracker.error for tracker in trackers if tracker.error]
        self.update_interval = (
            min(RETRY_INTERVAL, self.scan_interval) if errors else self.scan_interval
        )
        data = DpcData(self._criticality.latest, self._vigilance.latest)
        if data.criticality is None and data.vigilance is None:
            raise UpdateFailed(f"No DPC bulletin could be fetched: {errors[0]}")
        return data

    async def _get_criticality(self, bulletin_id: str) -> CriticalityBulletin:
        return await self._client.get_criticality(
            self.location, bulletin_id=bulletin_id
        )

    async def _get_vigilance(self, bulletin_id: str) -> VigilanceBulletin:
        return await self._client.get_vigilance(
            self.location,
            bulletin_id=bulletin_id,
            phenomena_within_km=self.phenomena_within_km,
        )


class _BulletinTracker[BulletinT: (CriticalityBulletin, VigilanceBulletin)]:
    """Keep the latest bulletin of a kind, downloading it only when it changes."""

    def __init__(
        self,
        name: str,
        kind: BulletinKind,
        client: DpcClient,
        get_bulletin: Callable[[str], Awaitable[BulletinT]],
    ) -> None:
        self._name = name
        self._kind = kind
        self._client = client
        self._get_bulletin = get_bulletin
        self.latest: LatestBulletin[BulletinT] | None = None
        self.error: DpcError | None = None
        """Why the last refresh failed; None when it succeeded."""

    async def refresh(self) -> None:
        """Fetch the latest bulletin if DPC has published a new one.

        On failure the previous bulletin is kept and the error is stored.
        """
        try:
            bulletin_id = await self._client.latest_bulletin_id(self._kind)
            if self.latest is not None and self.latest.bulletin.id == bulletin_id:
                bulletin = self.latest.bulletin
            else:
                LOGGER.debug(
                    "[%s] New %s bulletin %s", self._name, self._kind, bulletin_id
                )
                bulletin = await self._get_bulletin(bulletin_id)
        except DpcError as err:
            if self.error is None:
                LOGGER.warning(
                    "[%s] The %s bulletin could not be updated: %s",
                    self._name,
                    self._kind,
                    err,
                )
            self.error = err
            return

        if self.error is not None:
            LOGGER.info("[%s] The %s bulletin is updated again", self._name, self._kind)
        self.error = None
        self.latest = LatestBulletin(bulletin, checked_at=dt_util.now())
