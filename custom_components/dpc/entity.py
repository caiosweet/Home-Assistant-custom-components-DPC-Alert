"""The devices of a place and of its days, their entities and the entity IDs.

A place is a device. Each day it shows (today, tomorrow, the day after) is a
device of its own, linked to it, with the entities of that day; the place keeps
the entities of the whole bulletin.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from aiodpc import ATTRIBUTION, CRITICALITY_PAGE_URL, VIGILANCE_PAGE_URL
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    MAJOR_VERSION,
    MINOR_VERSION,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import (
    CONF_MUNICIPALITY,
    CONF_WARNING_LEVEL,
    DEFAULT_NAME,
    DEFAULT_WARNING_LEVEL,
    DOMAIN,
    MANUFACTURER,
    VERSION,
    VIA_DEVICE_ID_VERSION,
    PlaceDay,
)
from .coordinator import DpcDataUpdateCoordinator, PlaceDevice

MODEL = f"Criticality and Vigilance Bulletin {DOMAIN}"

DAY_PAGES = {
    PlaceDay.TODAY: CRITICALITY_PAGE_URL,
    PlaceDay.TOMORROW: CRITICALITY_PAGE_URL,
    # Only the vigilance bulletin covers the day after tomorrow
    PlaceDay.AFTER_TOMORROW: VIGILANCE_PAGE_URL,
}
"""The DPC page of the bulletin of each day, linked from its device."""


def place_name(entry: ConfigEntry) -> str:
    """Return the name of a place.

    Its municipality when one is set, otherwise the name of its entry, so that
    renaming the entry renames it.
    """
    name: str = (
        entry.options.get(CONF_MUNICIPALITY)
        or entry.title
        or entry.data.get(CONF_NAME)
        or DEFAULT_NAME
    )
    return name


def place_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return the device of a place: a service."""
    return DeviceInfo(
        # The identifier the device has always had: changing it would create a
        # new device, so it keeps its three parts
        identifiers={
            (  # type: ignore[arg-type]
                DOMAIN,
                entry.data[CONF_LATITUDE],
                entry.data[CONF_LONGITUDE],
            )
        },
        name=place_name(entry),
        model=MODEL,
        manufacturer=MANUFACTURER,
        sw_version=VERSION,
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=CRITICALITY_PAGE_URL,
    )


def day_device_identifier(entry: ConfigEntry, day: PlaceDay) -> tuple[str, str]:
    """Return the identifier of the device of a day of a place."""
    return DOMAIN, f"{entry.unique_id}-{day}"


def day_device_info(
    entry: ConfigEntry, day: PlaceDay, place: PlaceDevice
) -> DeviceInfo:
    """Return the device of a day of a place, e.g. "Portula Today"."""
    return DeviceInfo(
        identifiers={day_device_identifier(entry, day)},
        translation_key=day,
        translation_placeholders={"place": place.name},
        model=MODEL,
        manufacturer=MANUFACTURER,
        sw_version=VERSION,
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=DAY_PAGES[day],
        **_part_of_the_place(entry, place),
    )


def _part_of_the_place(entry: ConfigEntry, place: PlaceDevice) -> DeviceInfo:
    """Return the link from the device of a day to the device of its place."""
    if (MAJOR_VERSION, MINOR_VERSION) >= VIA_DEVICE_ID_VERSION:
        return DeviceInfo(via_device_id=place.id)
    else:  # pragma: no cover - Home Assistant before 2026.8, not tested
        (identifier,) = place_device_info(entry)["identifiers"]
        # The device info of 2026.10 no longer declares the deprecated via_device
        return DeviceInfo(via_device=identifier)  # type: ignore[typeddict-unknown-key]


def async_set_up_the_devices(
    hass: HomeAssistant, entry: ConfigEntry, days: Iterable[PlaceDay]
) -> PlaceDevice:
    """Register the device of a place, and remove the days it no longer shows.

    The device of the place comes first: the devices of its days link to it.
    They are created with their entities; removing one removes its entities.
    """
    registry = dr.async_get(hass)
    device = registry.async_get_or_create(
        config_entry_id=entry.entry_id, **place_device_info(entry)
    )
    gone = {day_device_identifier(entry, day) for day in set(PlaceDay) - set(days)}
    # Identifiers are unique only within a config entry
    for day_device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        if day_device.identifiers & gone:
            registry.async_remove_device(day_device.id)
    return PlaceDevice(
        id=device.id, name=device.name_by_user or device.name or place_name(entry)
    )


def place_entity_id(
    platform: str, place: str, key: str, day: PlaceDay | None = None
) -> str:
    """Return the entity ID a new entity of a place gets: dpc_<place>[_<day>]_<key>.

    E.g. binary_sensor.dpc_portula_today_hydraulic_risk. Every ID of the
    integration starts with dpc, once, even for a place named DPC.
    """
    parts = [slugify(place)]
    if parts[0] != DOMAIN and not parts[0].startswith(f"{DOMAIN}_"):
        parts.insert(0, DOMAIN)
    if day is not None:
        parts.append(day.object_id)
    return f"{platform}.{'_'.join([*parts, key])}"


class DpcEntity(CoordinatorEntity[DpcDataUpdateCoordinator]):
    """An entity of a place, or of one of its days.

    Home Assistant names it in its language, after its device and its
    translation key. It suggests the ID of a new entity (see
    :func:`place_entity_id`); entities registered before keep theirs until the
    user recreates them.
    """

    # The attribution the CC BY 4.0 license of the DPC data requires
    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DpcDataUpdateCoordinator,
        config_entry: ConfigEntry,
        day: PlaceDay | None = None,
    ) -> None:
        """Initialize an entity of the place, or of a day when one is given."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.day = day
        """The day of the entity; None for an entity of the whole place."""
        self.warning_level: int = config_entry.options.get(
            CONF_WARNING_LEVEL, DEFAULT_WARNING_LEVEL
        )
        """Lowest level reported as a warning: 1 green, 2 yellow, 3 orange, 4 red."""

    def suggest_entity_id(self, platform: str, key: str) -> None:
        """Suggest the ID of the entity, made of its place, day and key."""
        self.entity_id = place_entity_id(
            platform, self.coordinator.place_device.name, key, self.day
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device of the day of the entity, or of the place."""
        if self.day is None:
            return place_device_info(self.config_entry)
        return day_device_info(
            self.config_entry, self.day, self.coordinator.place_device
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {"integration": DOMAIN}
