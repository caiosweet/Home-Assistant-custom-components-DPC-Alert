"""Image platform for Dpc: the national maps of the bulletins, day by day."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.image import ImageEntity, ImageEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import ATTR_IMAGE_URL, PlaceDay
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
        DpcEntity.__init__(self, coordinator, entry, description.day)
        ImageEntity.__init__(self, hass)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}-{description.key}"
        self.suggest_entity_id(Platform.IMAGE, description.translation_key)
        self._show_the_map_of_the_day()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Show the map of the latest bulletin."""
        self._show_the_map_of_the_day()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Return whether the day has a map.

        After midnight, until DPC publishes the next bulletin, tomorrow has
        none: unavailable, the map is not shown at all instead of broken.
        """
        return super().available and self._attr_image_url is not None

    def _show_the_map_of_the_day(self) -> None:
        """Point to the map of the day, and forget the previous one if it changed."""
        url = self.entity_description.url_fn(self.coordinator.data)
        if url == self._attr_image_url:
            return
        self._attr_image_url = url
        # The address of the map at DPC, for cards that link to it
        self._attr_extra_state_attributes = {ATTR_IMAGE_URL: url} if url else {}
        self._attr_image_last_updated = dt_util.utcnow() if url else None
        self._cached_image = None
