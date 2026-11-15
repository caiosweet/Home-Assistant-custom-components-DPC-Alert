"""Geolocation platform for Dpc: the weather phenomena near a place.

Each phenomenon of the vigilance bulletin within the radius of the place is an
entity of the source ``dpc``, so the map card shows them with
``geo_location_sources: [dpc]``. The entities come and go with the bulletins.

An entity is named after the category of its phenomenon ("Nearby wind"), and
its type ("Gale") is translated by Home Assistant; the DPC legend stays, in
Italian, in its description.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from aiodpc import Phenomenon, PhenomenonCategory, PhenomenonType
from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_DAY,
    ATTR_DESCRIPTION,
    ATTR_DIRECTION,
    ATTR_PHENOMENON,
    ATTR_VALID_UNTIL,
    DOMAIN,
)
from .coordinator import DpcConfigEntry, DpcData, DpcDataUpdateCoordinator
from .entity import DpcEntity

# The coordinator updates the entities: nothing to limit
PARALLEL_UPDATES = 0


@dataclass(frozen=True, slots=True)
class NearbyPhenomenon:
    """A weather phenomenon of a known category near the place, on a day."""

    day: str
    """The day, as named in the attributes: today, tomorrow or aftertomorrow."""
    valid_until: datetime
    """End of the day: the midnight (Europe/Rome) that ends it."""
    category: PhenomenonCategory
    type: PhenomenonType
    phenomenon: Phenomenon


def nearby_phenomena(entry: ConfigEntry, data: DpcData) -> dict[str, NearbyPhenomenon]:
    """Return the phenomena near the place, by the unique ID of their entity.

    The ID is made of the place, the date and the key of the phenomenon (its code
    and position), so it stays the same when, after midnight, tomorrow becomes
    today, and when the next bulletin has the same phenomenon.
    """
    phenomena: dict[str, NearbyPhenomenon] = {}
    for name, day in data.vigilance_days.items():
        for phenomenon in day.phenomena:
            # Codes unknown to aiodpc have no category nor type, nothing to show
            if phenomenon.category is None or phenomenon.type is None:
                continue
            unique_id = f"{entry.unique_id}-{day.date.isoformat()}-{phenomenon.key}"
            phenomena[unique_id] = NearbyPhenomenon(
                day=name,
                valid_until=day.valid_until,
                category=phenomenon.category,
                type=phenomenon.type,
                phenomenon=phenomenon,
            )
    return phenomena


async def async_setup_entry(
    hass: HomeAssistant, entry: DpcConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup geolocation platform."""
    coordinator = entry.runtime_data
    added: set[str] = set()

    @callback
    def show_the_phenomena_near_the_place() -> None:
        """Add the new phenomena of the bulletin, and remove those it no longer has.

        The entity registry, not only the entities of this run, tells which are
        gone: the phenomena of a previous run stay registered until the next one.
        """
        nearby = nearby_phenomena(entry, coordinator.data)
        registry = er.async_get(hass)
        for registry_entry in er.async_entries_for_config_entry(
            registry, entry.entry_id
        ):
            if (
                registry_entry.domain == Platform.GEO_LOCATION
                and registry_entry.unique_id not in nearby
            ):
                # Removing it from the registry removes the entity too
                registry.async_remove(registry_entry.entity_id)
                added.discard(registry_entry.unique_id)
        new = sorted(nearby.keys() - added)
        added.update(new)
        async_add_entities(
            DpcPhenomenonEvent(coordinator, entry, unique_id, nearby[unique_id])
            for unique_id in new
        )

    show_the_phenomena_near_the_place()
    entry.async_on_unload(
        coordinator.async_add_listener(show_the_phenomena_near_the_place)
    )


class DpcPhenomenonEvent(DpcEntity, GeolocationEvent):
    """A weather phenomenon near the place: where it is, how far, and which day."""

    _attr_source = DOMAIN
    # DPC gives the distances in km, like the radius of the options
    _attr_unit_of_measurement = UnitOfLength.KILOMETERS

    def __init__(
        self,
        coordinator: DpcDataUpdateCoordinator,
        entry: ConfigEntry,
        unique_id: str,
        nearby: NearbyPhenomenon,
    ) -> None:
        """Initialize the entity of a phenomenon near the place."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = unique_id
        self._attr_translation_key = str(nearby.category)
        self._nearby: NearbyPhenomenon | None = None
        self._show(nearby)

    @property
    def available(self) -> bool:
        """Return whether the bulletin still has the phenomenon."""
        return super().available and self._nearby is not None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Follow the phenomenon in the latest bulletin."""
        nearby = nearby_phenomena(self.config_entry, self.coordinator.data)
        self._show(nearby.get(self.unique_id or ""))
        super()._handle_coordinator_update()

    def _show(self, nearby: NearbyPhenomenon | None) -> None:
        """Show where the phenomenon is; None while it is being removed."""
        self._nearby = nearby
        if nearby is None:
            return
        self._attr_distance = nearby.phenomenon.distance_km
        self._attr_latitude = nearby.phenomenon.latitude
        self._attr_longitude = nearby.phenomenon.longitude

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the phenomenon, its day and direction, and the DPC legend."""
        attributes = super().extra_state_attributes
        if (nearby := self._nearby) is not None:
            attributes |= {
                ATTR_PHENOMENON: str(nearby.type),
                ATTR_DAY: nearby.day,
                ATTR_VALID_UNTIL: nearby.valid_until,
                ATTR_DIRECTION: nearby.phenomenon.direction,
                ATTR_DESCRIPTION: nearby.phenomenon.description,
            }
        return attributes
