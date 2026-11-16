"""Geolocation platform for Dpc: the weather phenomena near a place.

Each phenomenon of the vigilance bulletin within the radius of the place is an
entity of the source ``dpc``, so the map card shows them with
``geo_location_sources: [dpc]``. The entities come and go with the bulletins.

An entity belongs to the device of its day, and is named after its phenomenon,
distance and direction, in the language of Home Assistant, with the texts of
aiodpc: "Chuvas esparsas ou intermitentes, 42,0 km NE".
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from aiodpc import Phenomenon, PhenomenonCategory, PhenomenonType
from aiodpc.i18n import TRANSLATIONS, Language, Translation
from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_DIRECTION, ATTR_PHENOMENON, DOMAIN, PlaceDay
from .coordinator import DpcConfigEntry, DpcData, DpcDataUpdateCoordinator
from .entity import DpcEntity

# The coordinator updates the entities: nothing to limit
PARALLEL_UPDATES = 0


@dataclass(frozen=True, slots=True)
class NearbyPhenomenon:
    """A weather phenomenon of a known category near the place, on a day."""

    day: PlaceDay
    category: PhenomenonCategory
    type: PhenomenonType
    phenomenon: Phenomenon


def nearby_phenomena(
    entry: ConfigEntry, data: DpcData, days: Iterable[PlaceDay]
) -> dict[str, NearbyPhenomenon]:
    """Return the phenomena of the days near the place, by the unique ID of their entity.

    The ID is made of the place, the day and the key of the phenomenon (its code
    and position), so it stays the same when the next bulletin has the same
    phenomenon. After midnight, a phenomenon of tomorrow is another entity, on
    the device of today.
    """
    phenomena: dict[str, NearbyPhenomenon] = {}
    shown = set(days)
    for name, day in data.vigilance_days.items():
        if name not in shown:
            continue
        for phenomenon in day.phenomena:
            # Codes unknown to aiodpc have no category nor type, nothing to show
            if phenomenon.category is None or phenomenon.type is None:
                continue
            unique_id = f"{entry.unique_id}-{name}-{phenomenon.key}"
            phenomena[unique_id] = NearbyPhenomenon(
                day=name,
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
    # Entity names are in the language of Home Assistant, as when it translates them
    texts = TRANSLATIONS[Language.of(hass.config.language) or Language.ENGLISH]

    @callback
    def show_the_phenomena_near_the_place() -> None:
        """Add the new phenomena of the bulletin, and remove those it no longer has.

        The entity registry, not only the entities of this run, tells which are
        gone: the phenomena of a previous run stay registered until the next one.
        """
        nearby = nearby_phenomena(entry, coordinator.data, coordinator.days)
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
            DpcPhenomenonEvent(coordinator, entry, unique_id, nearby[unique_id], texts)
            for unique_id in new
        )

    show_the_phenomena_near_the_place()
    entry.async_on_unload(
        coordinator.async_add_listener(show_the_phenomena_near_the_place)
    )


def name_placeholders(nearby: NearbyPhenomenon, texts: Translation) -> dict[str, str]:
    """Return the parts of the name of a phenomenon in a language.

    The name is the template of aiodpc, "{phenomenon}, {distance} km
    {direction}", which Home Assistant fills with them.
    """
    phenomenon = nearby.phenomenon
    return {
        "phenomenon": texts.phenomenon_types[nearby.type],
        "distance": f"{phenomenon.distance_km:.1f}".replace(
            ".", texts.decimal_separator
        ),
        "direction": texts.compass_points[phenomenon.direction],
    }


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
        texts: Translation,
    ) -> None:
        """Initialize the entity of a phenomenon, named with the texts of a language."""
        super().__init__(coordinator, entry, nearby.day)
        self._attr_unique_id = unique_id
        # The category gives the icon
        self._attr_translation_key = str(nearby.category)
        self._attr_translation_placeholders = name_placeholders(nearby, texts)
        # e.g. geo_location.dpc_milano_today_scattered_rain_wnw
        direction = nearby.phenomenon.direction.lower()
        self.suggest_entity_id(Platform.GEO_LOCATION, f"{nearby.type}_{direction}")
        self._nearby: NearbyPhenomenon | None = None
        self._show(nearby)

    @property
    def available(self) -> bool:
        """Return whether the bulletin still has the phenomenon."""
        return super().available and self._nearby is not None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Follow the phenomenon in the latest bulletin."""
        nearby = nearby_phenomena(
            self.config_entry, self.coordinator.data, self.coordinator.days
        )
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
        # The type of the phenomenon and its direction, which Home Assistant translates
        self._attr_extra_state_attributes = {
            ATTR_PHENOMENON: str(nearby.type),
            ATTR_DIRECTION: nearby.phenomenon.direction.lower(),
        }
