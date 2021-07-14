"""Sensor platform for Dpc."""
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME

from . import DpcDataUpdateCoordinator
from .const import (
    CONF_WARNING_LEVEL,
    DEFAULT_NAME,
    DEFAULT_WARNING_LEVEL,
    DOMAIN,
    LOGGER,
    WARNING_TYPES,
)
from .entity import DpcEntity

ICON = {"safety": "mdi:shield-check", "danger": "mdi:hazard-lights"}


async def async_setup_entry(hass, entry, async_add_entities):  # async_add_devices
    """Setup sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DpcSensor(coordinator, entry)])


class DpcSensor(DpcEntity):
    """Dpc Sensor class."""

    def __init__(
        self,
        coordinator: DpcDataUpdateCoordinator,
        entry: str,
    ):
        """Initialize Entities."""
        super().__init__(coordinator, entry)
        self.coordinator = coordinator
        # self.entry = entry
        self._state = None
        self._max_level = None
        self._total_events = None
        self._events_today = None
        self._events_tomorrow = None
        self._level = entry.options.get(CONF_WARNING_LEVEL, DEFAULT_WARNING_LEVEL)

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        config = self.config_entry.data
        return f"{config.get(CONF_NAME)}_{config.get(CONF_LATITUDE)}_{config.get(CONF_LONGITUDE)}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self.config_entry.data.get(CONF_NAME, DEFAULT_NAME)}"

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return ICON["danger"] if self.state != 0 else ICON["safety"]

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.state is not None

    @property
    def state(self):
        """Return the state of the sensor."""
        try:
            self._max_level = 0
            self._state = 0
            self._events_today = []
            self._events_tomorrow = []
            data = self.coordinator.data
            for warning in WARNING_TYPES:
                if warning in data and "level" in data[warning]:

                    level = data[warning]["level"]
                    if level > self._max_level:
                        self._max_level = level

                    if data[warning]["level"] >= self._level:
                        self._state += 1

                        event_day = {
                            "risk": data[warning]["risk"],
                            "info": data[warning]["info"],
                            "alert": data[warning]["alert"],
                            "level": data[warning]["level"],
                        }
                        if "oggi" in warning:
                            self._events_today.append(event_day)
                        if "domani" in warning:
                            self._events_tomorrow.append(event_day)

            return self._state

        except Exception as exception:
            LOGGER.error("[SENSOR STATE] Error! - %s", exception)

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = super().extra_state_attributes
        data = self.coordinator.data
        if "id" in data:
            attrs["id"] = data["id"]
            attrs["publication_date"] = data["publication_date"]
            attrs["last_update"] = data["last_update"]
            attrs["max_level"] = self._max_level
            if "today" in data:
                data["today"].update(
                    {
                        "image_url": data[WARNING_TYPES[0]]["image_url"],
                        "expires": data[WARNING_TYPES[0]]["expires"],
                    }
                )
                attrs["today"] = data["today"]
                if self._events_today:
                    attrs["events_today"] = self._events_today
            if "tomorrow" in data:
                data["tomorrow"].update(
                    {
                        "image_url": data[WARNING_TYPES[3]]["image_url"],
                        "expires": data[WARNING_TYPES[3]]["expires"],
                    }
                )
                attrs["tomorrow"] = data["tomorrow"]
                if self._events_tomorrow:
                    attrs["events_tomorrow"] = self._events_tomorrow
            attrs["zone_name"] = data["zone_name"]
        return attrs

    async def async_update(self):
        """Update Dpc Sensor Entity."""
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """Subscribe to updates."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
