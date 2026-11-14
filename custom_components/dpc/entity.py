"""DpcEntity class"""

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

from .const import ATTRIBUTION, DEFAULT_NAME, DOMAIN, MANUFACTURER, VERSION


class DpcEntity(CoordinatorEntity):
    # Entity names come from translations (entity.<platform>.<translation_key>.name)
    # and are prefixed by the device name, i.e. the configured location name.
    _attr_has_entity_name = True

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator)
        self.config_entry = config_entry

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
            ATTR_NAME: self.config_entry.data.get(CONF_NAME) or DEFAULT_NAME,
            ATTR_MODEL: f"Criticality and Vigilance Bulletin {DOMAIN}",
            ATTR_MANUFACTURER: MANUFACTURER,
            ATTR_SW_VERSION: VERSION,
            "entry_type": DeviceEntryType.SERVICE,
        }

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {ATTR_ATTRIBUTION: ATTRIBUTION, "integration": DOMAIN}
