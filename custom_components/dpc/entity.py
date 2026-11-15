"""DpcEntity class"""

from __future__ import annotations

from typing import Any

from aiodpc import CRITICALITY_PAGE_URL
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
)
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import (
    ATTRIBUTION,
    CONF_MUNICIPALITY,
    CONF_WARNING_LEVEL,
    DEFAULT_NAME,
    DEFAULT_WARNING_LEVEL,
    DOMAIN,
    MANUFACTURER,
    VERSION,
)
from .coordinator import DpcDataUpdateCoordinator


def language_independent_entity_id(
    entity_id_format: str, entry: ConfigEntry, suffix: str
) -> str:
    """Return <platform>.<name of the place>_<suffix>, the same in every language.

    Home Assistant derives the entity IDs of new entities from their translated
    names (e.g. sensor.casa_allerta in Italian): suggesting the ID keeps it the
    same in every language. Existing entities keep their registered ID, and a
    taken ID gets a suffix (_2).
    """
    return entity_id_format.format(
        slugify(f"{entry.data.get(CONF_NAME) or DEFAULT_NAME} {suffix}")
    )


class DpcEntity(CoordinatorEntity[DpcDataUpdateCoordinator]):
    # Entity names come from translations (entity.<platform>.<translation_key>.name)
    # and are prefixed by the device name, i.e. the configured location name.
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: DpcDataUpdateCoordinator, config_entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.warning_level: int = config_entry.options.get(
            CONF_WARNING_LEVEL, DEFAULT_WARNING_LEVEL
        )
        """Lowest level reported as a warning: 1 green, 2 yellow, 3 orange, 4 red."""

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device of the place: a service."""
        return DeviceInfo(
            # The identifier the device has always had: changing it would
            # create a new device, so it keeps its three parts
            identifiers={
                (  # type: ignore[arg-type]
                    DOMAIN,
                    self.config_entry.data[CONF_LATITUDE],
                    self.config_entry.data[CONF_LONGITUDE],
                )
            },
            # The place: its municipality when one is set, otherwise the name
            # of its entry, so that renaming the entry renames the device
            name=self.config_entry.options.get(CONF_MUNICIPALITY)
            or self.config_entry.title
            or self.config_entry.data.get(CONF_NAME)
            or DEFAULT_NAME,
            model=f"Criticality and Vigilance Bulletin {DOMAIN}",
            manufacturer=MANUFACTURER,
            sw_version=VERSION,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=CRITICALITY_PAGE_URL,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {ATTR_ATTRIBUTION: ATTRIBUTION, "integration": DOMAIN}
