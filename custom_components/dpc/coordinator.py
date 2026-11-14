"""Coordinator of the DPC bulletins of a place."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial

from aiodpc import BulletinKind, CriticalityBulletin, DpcError, VigilanceBulletin
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .bulletins import DpcBulletins
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER, RETRY_INTERVAL


@dataclass(frozen=True)
class LatestBulletin[BulletinT: (CriticalityBulletin, VigilanceBulletin)]:
    """A bulletin and when DPC last confirmed that it is the latest one."""

    bulletin: BulletinT
    checked_at: datetime


@dataclass(frozen=True, slots=True)
class DpcData:
    """The latest DPC bulletins of the place; None until one is fetched."""

    criticality: LatestBulletin[CriticalityBulletin] | None = None
    vigilance: LatestBulletin[VigilanceBulletin] | None = None


class DpcDataUpdateCoordinator(DataUpdateCoordinator[DpcData]):
    """Keep the latest DPC bulletins of the place of a config entry.

    The bulletins come from :class:`DpcBulletins`, shared by every place, which
    downloads a bulletin only when DPC publishes a new one. When a bulletin
    cannot be updated, the previous one is kept, since its days stay valid
    until they are over, and the next update comes sooner.
    """

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, bulletins: DpcBulletins
    ) -> None:
        """Initialize the coordinator of a config entry."""
        self.scan_interval = timedelta(
            minutes=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        self.platforms: list[str] = []
        self._criticality = _BulletinTracker(
            entry.title,
            BulletinKind.CRITICALITY,
            partial(bulletins.criticality, entry.entry_id),
        )
        self._vigilance = _BulletinTracker(
            entry.title,
            BulletinKind.VIGILANCE,
            partial(bulletins.vigilance, entry.entry_id),
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
        """Return the latest bulletins of the place."""
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


class _BulletinTracker[BulletinT: (CriticalityBulletin, VigilanceBulletin)]:
    """Keep the latest bulletin of a kind, and the previous one on failure."""

    def __init__(
        self,
        name: str,
        kind: BulletinKind,
        get_bulletin: Callable[[], Awaitable[BulletinT]],
    ) -> None:
        self._name = name
        self._kind = kind
        self._get_bulletin = get_bulletin
        self.latest: LatestBulletin[BulletinT] | None = None
        self.error: DpcError | None = None
        """Why the last refresh failed; None when it succeeded."""

    async def refresh(self) -> None:
        """Get the latest bulletin; on failure keep the previous one."""
        try:
            bulletin = await self._get_bulletin()
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
        if self.latest is None or self.latest.bulletin.id != bulletin.id:
            LOGGER.debug("[%s] New %s bulletin %s", self._name, self._kind, bulletin.id)
        self.error = None
        self.latest = LatestBulletin(bulletin, checked_at=dt_util.now())
