"""DpcEntity class"""

from __future__ import annotations

from typing import Any

from aiodpc import ATTRIBUTION, CRITICALITY_PAGE_URL
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_MUNICIPALITY,
    CONF_WARNING_LEVEL,
    DEFAULT_NAME,
    DEFAULT_WARNING_LEVEL,
    DOMAIN,
    MANUFACTURER,
    VERSION,
)
from .coordinator import DpcDataUpdateCoordinator


class DpcEntity(CoordinatorEntity[DpcDataUpdateCoordinator]):
    """An entity of a place, named after the place and its translation key.

    Home Assistant names it in its language and builds the entity ID of a new
    entity from the English name, e.g. binary_sensor.portula_hydraulic_risk_today,
    as it does for other integrations. The entities registered before keep
    their ID, like binary_sensor.dpc_portula_idraulico_oggi, until the user
    recreates it.
    """

    # The attribution the CC BY 4.0 license of the DPC data requires
    _attr_attribution = ATTRIBUTION
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
        return {"integration": DOMAIN}
