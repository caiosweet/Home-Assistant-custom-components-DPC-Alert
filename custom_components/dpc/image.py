"""Image platform for Dpc: the national maps of the bulletins, day by day."""

from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.image import (
    ENTITY_ID_FORMAT,
    ImageEntity,
    ImageEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import ATTR_TODAY, ATTR_TOMORROW
from .coordinator import DpcConfigEntry, DpcData, DpcDataUpdateCoordinator
from .entity import DpcEntity, place_entity_id

# The coordinator updates the entities: nothing to limit
PARALLEL_UPDATES = 0

# A generic placeholder used when DPC has no map for a day yet, such as when the
# bulletin covers only today and tomorrow and the next day is still unavailable.
PLACEHOLDER_IMAGE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAF" \
    "tig3AAAAAXNSR0IAr+s3AAAAA1JREFUGFdjYAAAAAIAAeIhvAAAAABJRU5ErkJggg=="
)


@dataclass(frozen=True, kw_only=True)
class DpcMapEntityDescription(ImageEntityDescription):
    """Description of the map of a bulletin on a day."""

    url_fn: Callable[[DpcData], str | None]
    """Return the URL of the preview of the map, None when there is none."""


def _criticality_map(day: str) -> Callable[[DpcData], str | None]:
    """Return how to find the criticality map of a day."""

    def url(data: DpcData) -> str | None:
        covered = data.criticality_days.get(day)
        return covered.image_url if covered else None

    return url


def _vigilance_map(day: str) -> Callable[[DpcData], str | None]:
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
            translation_key=f"criticality_map_{day}",
            url_fn=_criticality_map(day),
        )
        for day in (ATTR_TODAY, ATTR_TOMORROW)
    ),
    *(
        DpcMapEntityDescription(
            key=f"vigilance_map_{day}",
            translation_key=f"vigilance_map_{day}",
            url_fn=_vigilance_map(day),
        )
        for day in (ATTR_TODAY, ATTR_TOMORROW)
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
    )


class DpcMapImage(DpcEntity, ImageEntity):
    """The national map of a bulletin on a day, as DPC previews it.

    Home Assistant downloads the map when a dashboard shows it, and keeps it
    until the map of the day changes: a new bulletin, or the next day.
    """

    entity_description: DpcMapEntityDescription

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DpcDataUpdateCoordinator,
        entry: ConfigEntry,
        description: DpcMapEntityDescription,
    ) -> None:
        """Initialize the map of a bulletin on a day."""
        DpcEntity.__init__(self, coordinator, entry)
        ImageEntity.__init__(self, hass)
        self.entity_description = description
        self.entity_id = place_entity_id(ENTITY_ID_FORMAT, entry, description.key)
        self._attr_unique_id = f"{entry.unique_id}-{description.key}"
        self._show_the_map_of_the_day()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Show the map of the latest bulletin."""
        self._show_the_map_of_the_day()
        super()._handle_coordinator_update()

    async def async_image(self) -> bytes | None:
        """Return the map preview or a generic placeholder when no map exists."""
        if self.image_url is not None:
            return await super().async_image()
        return PLACEHOLDER_IMAGE

    def _show_the_map_of_the_day(self) -> None:
        """Point to the map of the day, and forget the previous one if it changed."""
        url = self.entity_description.url_fn(self.coordinator.data)
        if url == self._attr_image_url:
            return
        self._attr_image_url = url
        self._attr_image_last_updated = dt_util.utcnow() if url else None
        self._cached_image = None
