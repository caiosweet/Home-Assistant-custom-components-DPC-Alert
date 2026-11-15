"""DpcEntity class"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_NAME,
    ATTR_SW_VERSION,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
)
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import (
    ATTRIBUTION,
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
    def device_info(self):
        return {
            ATTR_IDENTIFIERS: {
                (
                    DOMAIN,
                    self.config_entry.data.get(CONF_LATITUDE),
                    self.config_entry.data.get(CONF_LONGITUDE),
                )
            },
            # The name of the place: renaming the entry renames the device
            ATTR_NAME: self.config_entry.title
            or self.config_entry.data.get(CONF_NAME)
            or DEFAULT_NAME,
            ATTR_MODEL: f"Criticality and Vigilance Bulletin {DOMAIN}",
            ATTR_MANUFACTURER: MANUFACTURER,
            ATTR_SW_VERSION: VERSION,
            "entry_type": DeviceEntryType.SERVICE,
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {ATTR_ATTRIBUTION: ATTRIBUTION, "integration": DOMAIN}
