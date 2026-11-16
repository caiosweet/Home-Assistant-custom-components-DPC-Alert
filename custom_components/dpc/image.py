"""Image platform for Dpc: the national maps of the bulletins, day by day."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from aiodpc import DpcError
from homeassistant.components.image import Image, ImageEntity, ImageEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .bulletins import async_get_bulletins
from .const import ATTR_IMAGE_URL, LOGGER, PlaceDay
from .coordinator import DpcConfigEntry, DpcData, DpcDataUpdateCoordinator
from .entity import DpcEntity

# The coordinator updates the entities: nothing to limit
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class DpcMapEntityDescription(ImageEntityDescription):
    """Description of the map of a bulletin on a day."""

    translation_key: str
    day: PlaceDay
    url_fn: Callable[[DpcData], str | None]
    """Return the URL of the preview of the map, None when there is none."""


def _criticality_map(day: PlaceDay) -> Callable[[DpcData], str | None]:
    """Return how to find the criticality map of a day."""

    def url(data: DpcData) -> str | None:
        covered = data.criticality_days.get(day)
        return covered.image_url if covered else None

    return url


def _vigilance_map(day: PlaceDay) -> Callable[[DpcData], str | None]:
    """Return how to find the vigilance map of a day."""

    def url(data: DpcData) -> str | None:
        covered = data.vigilance_days.get(day)
        return covered.image_url if covered else None

    return url


# DPC publishes no vigilance map for the day after tomorrow
MAP_DESCRIPTIONS = (
    *(
        DpcMapEntityDescription(
            key=f"criticality_map_{day}",
            translation_key="criticality_map",
            day=day,
            url_fn=_criticality_map(day),
        )
        for day in (PlaceDay.TODAY, PlaceDay.TOMORROW)
    ),
    *(
        DpcMapEntityDescription(
            key=f"vigilance_map_{day}",
            translation_key="vigilance_map",
            day=day,
            url_fn=_vigilance_map(day),
        )
        for day in (PlaceDay.TODAY, PlaceDay.TOMORROW)
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: DpcConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup image platform."""
    coordinator = entry.runtime_data
    async_add_entities(
        DpcMapImage(hass, coordinator, entry, description)
        for description in MAP_DESCRIPTIONS
        if description.day in coordinator.days
    )


class DpcMapImage(DpcEntity, ImageEntity):
    """The national map of a bulletin on a day, as DPC previews it.

    The map is downloaded as soon as the day has one, once for every place,
    and kept until the map of the day changes: a new bulletin, or the next
    day. DPC often publishes it blank, and sometimes replaces it later at the
    same address: until a map is downloaded that is not blank, the entity is
    unavailable, so that dashboards leave it out, and every update of the place
    tries again.
    """

    entity_description: DpcMapEntityDescription
    # The previews DPC publishes
    _attr_content_type = "image/png"

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DpcDataUpdateCoordinator,
        entry: ConfigEntry,
        description: DpcMapEntityDescription,
    ) -> None:
        """Initialize the map of a bulletin on a day."""
        DpcEntity.__init__(self, coordinator, entry, description.day)
        ImageEntity.__init__(self, hass)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}-{description.key}"
        self.suggest_entity_id(Platform.IMAGE, description.translation_key)
        self._download: asyncio.Task[None] | None = None
        self._show_the_map_of_the_day()

    async def async_added_to_hass(self) -> None:
        """Download the map of the day."""
        await super().async_added_to_hass()
        self._download_the_map()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Show the map of the latest bulletin, or try again to download it."""
        self._show_the_map_of_the_day()
        self._download_the_map()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Return whether the map of the day is downloaded, and not blank.

        After midnight, until DPC publishes the next bulletin, tomorrow has
        none; and DPC often publishes a map blank. Unavailable, the map is not
        shown at all, instead of blank or broken.
        """
        return super().available and self._cached_image is not None

    async def async_image(self) -> bytes | None:
        """Return the map of the day, as downloaded; None without one."""
        return self._cached_image.content if self._cached_image else None

    def _show_the_map_of_the_day(self) -> None:
        """Point to the map of the day, and forget the previous one if it changed."""
        url = self.entity_description.url_fn(self.coordinator.data)
        if url == self._attr_image_url:
            return
        self._attr_image_url = url
        # The address of the map at DPC, for cards that link to it
        self._attr_extra_state_attributes = {ATTR_IMAGE_URL: url} if url else {}
        self._attr_image_last_updated = None
        self._cached_image = None
        if self._download is not None:
            self._download.cancel()
            self._download = None

    @callback
    def _download_the_map(self) -> None:
        """Download the map of the day, unless it is shown or being downloaded."""
        url = self._attr_image_url
        if (
            not isinstance(url, str)
            or self._cached_image is not None
            or (self._download is not None and not self._download.done())
        ):
            return
        self._download = self.coordinator.config_entry.async_create_task(
            self.hass, self._async_download(url), f"{self.entity_id} map"
        )

    async def _async_download(self, url: str) -> None:
        """Show the map at an address, unless DPC publishes it blank."""
        try:
            image = await async_get_bulletins(self.hass).preview(url)
        except DpcError as err:
            # Tried again at the next update of the place
            LOGGER.debug("The map %s cannot be downloaded: %s", url, err)
            return
        if image is None:
            LOGGER.debug("The map %s is blank, until DPC replaces it", url)
            return
        self._cached_image = Image(self.content_type, image)
        self._attr_image_last_updated = dt_util.utcnow()
        self.async_write_ha_state()
