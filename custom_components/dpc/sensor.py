"""Sensor platform for Dpc."""
from homeassistant.const import ATTR_ICON, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME

from . import DpcDataUpdateCoordinator
from .const import (
    ATTR_AFTERTOMORROW,
    ATTR_ALERT,
    ATTR_EVENTS_TODAY,
    ATTR_EVENTS_TOMORROW,
    ATTR_ID,
    ATTR_INFO,
    ATTR_LAST_UPDATE,
    ATTR_LEVEL,
    ATTR_LINK,
    ATTR_MAX_LEVEL,
    ATTR_PHENOMENA,
    ATTR_PUBLICATION_DATE,
    ATTR_RISK,
    ATTR_TODAY,
    ATTR_TOMORROW,
    ATTR_TOTAL_ALERTS,
    ATTR_TOTAL_PHENOMENA,
    ATTR_ZONE_NAME,
    CONF_WARNING_LEVEL,
    DEFAULT_NAME,
    DEFAULT_WARNING_LEVEL,
    DOMAIN,
    LOGGER,
    WARNING_TYPES,
)
from .entity import DpcEntity

ICON = {"safety": "mdi:shield-check", "danger": "mdi:hazard-lights"}  # shield-account


async def async_setup_entry(hass, entry, async_add_entities):  # async_add_devices
    """Setup sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            DpcSensorCriticality(coordinator, entry),
            DpcSensorVigilance(coordinator, entry),
        ]
    )


class DpcSensorCriticality(DpcEntity):
    """Dpc Criticality Sensor class."""

    def __init__(
        self,
        coordinator: DpcDataUpdateCoordinator,
        entry: str,
    ):
        """Initialize Entities."""
        super().__init__(coordinator, entry)
        self.coordinator = coordinator
        self.entry = entry
        self._state = None
        self._max_level = None
        self._total_alerts = None
        self._events_today = None
        self._events_tomorrow = None
        self._name = entry.data.get(CONF_NAME)
        self._latitude = entry.data.get(CONF_LATITUDE)
        self._longitude = entry.data.get(CONF_LONGITUDE)
        self._level = entry.options.get(CONF_WARNING_LEVEL, DEFAULT_WARNING_LEVEL)

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"{self._name}_criticality_{self._latitude}_{self._longitude}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self.entry.data.get(CONF_NAME, DEFAULT_NAME)} Alert"

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return ICON["danger"] if self._total_alerts != 0 else ICON["safety"]

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data
        )

    @property
    def state(self):
        """Return the state of the sensor."""
        try:
            self._state = 0
            self._total_alerts = 0

            self._events_today = []
            self._events_tomorrow = []
            data = self.coordinator.data.get("criticality")
            if data:
                for warning in WARNING_TYPES:
                    if warning in data and ATTR_LEVEL in data[warning]:

                        level = data[warning][ATTR_LEVEL]
                        if level > self._state:
                            self._state = level

                        if data[warning][ATTR_LEVEL] >= self._level:
                            self._total_alerts += 1

                            event_day = {
                                ATTR_RISK: data[warning][ATTR_RISK],
                                ATTR_INFO: data[warning][ATTR_INFO],
                                ATTR_ALERT: data[warning][ATTR_ALERT],
                                ATTR_LEVEL: data[warning][ATTR_LEVEL],
                                ATTR_ICON: data[warning][ATTR_ICON],
                            }
                            if "oggi" in warning:
                                self._events_today.append(event_day)
                            if "domani" in warning:
                                self._events_tomorrow.append(event_day)

            return self._state if self._state != 0 else None

        except Exception as exception:
            LOGGER.error("[Criticality Sensor] Error! - %s", exception)

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = super().extra_state_attributes
        data = self.coordinator.data.get("criticality")
        if data:
            attrs[ATTR_ID] = data[ATTR_ID]
            attrs[ATTR_PUBLICATION_DATE] = data[ATTR_PUBLICATION_DATE]
            attrs[ATTR_LAST_UPDATE] = data[ATTR_LAST_UPDATE]
            attrs[ATTR_MAX_LEVEL] = self._state
            attrs[ATTR_TOTAL_ALERTS] = self._total_alerts
            if ATTR_TODAY in data:
                attrs[ATTR_TODAY] = data[ATTR_TODAY]
                if self._events_today:
                    attrs[ATTR_EVENTS_TODAY] = self._events_today
            if ATTR_TOMORROW in data:
                attrs[ATTR_TOMORROW] = data[ATTR_TOMORROW]
                if self._events_tomorrow:
                    attrs[ATTR_EVENTS_TOMORROW] = self._events_tomorrow
            attrs[ATTR_ZONE_NAME] = data[ATTR_ZONE_NAME]
            attrs[ATTR_LINK] = data[ATTR_LINK]
        return attrs

    # async def async_update(self):
    #     """Update Dpc Sensor Entity."""
    #     await self.coordinator.async_request_refresh()

    # async def async_added_to_hass(self):
    #     """Subscribe to updates."""
    #     self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))


class DpcSensorVigilance(DpcEntity):
    """Dpc Vigilance Sensor class."""

    def __init__(
        self,
        coordinator: DpcDataUpdateCoordinator,
        entry: str,
    ):
        """Initialize Entities."""
        super().__init__(coordinator, entry)
        self.coordinator = coordinator
        self.entry = entry
        self._state = None
        self._max_level = None
        self._total_alerts = None
        self._total_phenomena = None
        self._name = entry.data.get(CONF_NAME)
        self._latitude = entry.data.get(CONF_LATITUDE)
        self._longitude = entry.data.get(CONF_LONGITUDE)
        self._level = entry.options.get(CONF_WARNING_LEVEL, DEFAULT_WARNING_LEVEL)

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"{self._name}_vigilance_{self._latitude}_{self._longitude}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self.entry.data.get(CONF_NAME, DEFAULT_NAME)} Vigilance"

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return ICON["danger"] if self._total_alerts != 0 else ICON["safety"]

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data
        )

    @property
    def state(self):
        """Return the state of the sensor."""
        try:
            self._total_alerts = 0
            self._state = 0
            self._total_phenomena = 0
            data = self.coordinator.data.get("vigilance")
            if data:
                for warning in [ATTR_TODAY, ATTR_TOMORROW, ATTR_AFTERTOMORROW]:
                    if warning in data and ATTR_LEVEL in data[warning]:
                        level = data[warning][ATTR_LEVEL]

                        if level > self._state:
                            self._state = level

                        if data[warning][ATTR_LEVEL] >= self._level:
                            self._total_alerts += 1

                        if ATTR_PHENOMENA in data[warning]:
                            self._total_phenomena += len(data[warning][ATTR_PHENOMENA])

                        # if (
                        #     not data[warning][ATTR_PHENOMENA]
                        #     and data[warning][ATTR_LEVEL] < self._level
                        # ):
                        #     data.pop(warning)
            return self._state if self._state != 0 else None

        except Exception as exception:
            LOGGER.error("[Vigilance Sensor] Error! - %s", exception)

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = super().extra_state_attributes
        data = self.coordinator.data.get("vigilance")
        if data:
            attrs.update(data)
            attrs[ATTR_MAX_LEVEL] = self._state
            attrs[ATTR_TOTAL_PHENOMENA] = self._total_phenomena
            attrs[ATTR_TOTAL_ALERTS] = self._total_alerts
        return attrs

    # async def async_update(self):
    #     """Update Dpc Sensor Entity."""
    #     await self.coordinator.async_request_refresh()

    # async def async_added_to_hass(self):
    #     """Subscribe to updates."""
    #     self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
