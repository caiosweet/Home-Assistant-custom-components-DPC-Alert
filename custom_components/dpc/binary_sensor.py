"""Binary sensor platform for Dpc."""
from typing import Any, Dict

from homeassistant.components.binary_sensor import (
    ENTITY_ID_FORMAT,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import ATTR_ICON, ATTR_NAME
from homeassistant.helpers.entity import async_generate_entity_id

from . import DpcDataUpdateCoordinator
from .const import (
    ATTR_ALERT,
    ATTR_EXPIRES,
    ATTR_ID,
    ATTR_IMAGE_URL,
    ATTR_INFO,
    ATTR_LAST_UPDATE,
    ATTR_LEVEL,
    ATTR_LINK,
    ATTR_PUBLICATION_DATE,
    ATTR_RISK,
    ATTR_ZONE_NAME,
    CONF_WARNING_LEVEL,
    DEFAULT_WARNING_LEVEL,
    DOMAIN,
)
from .entity import DpcEntity

BINARY_SENSOR_TYPES = [
    {
        ATTR_NAME: "Rischio Idraulico Oggi",
        ATTR_RISK: "idraulico_oggi",
        ATTR_ICON: "mdi:home-flood",
    },
    {
        ATTR_NAME: "Rischio Temporali Oggi",
        ATTR_RISK: "temporali_oggi",
        ATTR_ICON: "mdi:weather-lightning",
    },
    {
        ATTR_NAME: "Rischio Idrogeologico Oggi",
        ATTR_RISK: "idrogeologico_oggi",
        ATTR_ICON: "mdi:waves",
    },
    {
        ATTR_NAME: "Rischio Idraulico Domani",
        ATTR_RISK: "idraulico_domani",
        ATTR_ICON: "mdi:home-flood",
    },
    {
        ATTR_NAME: "Rischio Temporali Domani",
        ATTR_RISK: "temporali_domani",
        ATTR_ICON: "mdi:weather-lightning",
    },
    {
        ATTR_NAME: "Rischio Idrogeologico Domani",
        ATTR_RISK: "idrogeologico_domani",
        ATTR_ICON: "mdi:waves",
    },
]


async def async_setup_entry(hass, entry, async_add_entities):
    """Setup binary_sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors: list = []
    for sensor_type in BINARY_SENSOR_TYPES:
        uid = f"{entry.unique_id}_{sensor_type[ATTR_RISK]})"
        entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, uid, hass=hass)
        sensors.append(DpcBinarySensor(coordinator, entry, sensor_type, entity_id))
    async_add_entities(sensors)


class DpcBinarySensor(DpcEntity, BinarySensorEntity):
    """Dpc binary_sensor class."""

    def __init__(
        self,
        coordinator: DpcDataUpdateCoordinator,
        entry: str,
        sensor_type: Dict[str, Any],
        entity_id: str,
    ):
        """Initialize Entities."""
        super().__init__(coordinator, entry)
        self.coordinator = coordinator
        self.entity_id = entity_id
        # self.entry = entry
        self._enabled = True
        self._level = entry.options.get(CONF_WARNING_LEVEL, DEFAULT_WARNING_LEVEL)
        self._icon = sensor_type[ATTR_ICON]
        self._name = sensor_type[ATTR_NAME]
        self._kind = sensor_type[ATTR_RISK]
        self._unique_id = f"{entry.unique_id}-{self._kind}"

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.get("criticality") is not None
        )

    @property
    def name(self):
        """Return the name of the binary_sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return self._unique_id

    @property
    def icon(self):
        """Return the icon for this entity."""
        return self._icon

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return the class of this binary_sensor."""
        return BinarySensorDeviceClass.SAFETY

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return self._enabled

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        data = self.coordinator.data.get("criticality")
        if data and self._kind in data and ATTR_LEVEL in data[self._kind]:
            return data[self._kind][ATTR_LEVEL] >= self._level

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = super().extra_state_attributes
        data = self.coordinator.data.get("criticality")
        # if self.is_on:
        if data and self._kind in data and ATTR_ALERT in data[self._kind]:
            attrs[ATTR_ID] = data.get(ATTR_ID)
            attrs[ATTR_PUBLICATION_DATE] = data.get(ATTR_PUBLICATION_DATE)
            attrs[ATTR_EXPIRES] = data[self._kind][ATTR_EXPIRES]
            attrs[ATTR_LAST_UPDATE] = data.get(ATTR_LAST_UPDATE)
            attrs[ATTR_RISK] = data[self._kind][ATTR_RISK]
            attrs[ATTR_INFO] = data[self._kind][ATTR_INFO]
            attrs[ATTR_ALERT] = data[self._kind][ATTR_ALERT]
            attrs[ATTR_LEVEL] = data[self._kind][ATTR_LEVEL]
            attrs[ATTR_ZONE_NAME] = data.get(ATTR_ZONE_NAME)
            attrs[ATTR_IMAGE_URL] = data[self._kind][ATTR_IMAGE_URL]
            attrs[ATTR_LINK] = data.get(ATTR_LINK)
        return attrs

    async def async_update(self):
        """Update Dpc Binary Sensor Entity."""
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """Subscribe to updates."""
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
