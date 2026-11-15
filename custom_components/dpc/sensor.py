"""Sensor platform for Dpc."""

from __future__ import annotations

from typing import Any

from aiodpc import AlertLevel, CriticalityDay, Precipitation, Risk, VigilanceDay
from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .attributes import (
    criticality_attributes,
    criticality_day_attributes,
    risk_event_attributes,
    vigilance_attributes,
    vigilance_day_attributes,
)
from .const import (
    ALERT_LEVEL_STATES,
    ATTR_AFTERTOMORROW,
    ATTR_EVENTS_TODAY,
    ATTR_EVENTS_TOMORROW,
    ATTR_MAX_LEVEL,
    ATTR_PHENOMENA,
    ATTR_RISKS,
    ATTR_TODAY,
    ATTR_TOMORROW,
    ATTR_TOTAL_ALERTS,
    ATTR_TOTAL_PHENOMENA,
    ATTR_VALID_UNTIL,
    ATTR_ZONE_NAME,
    PRECIPITATION_STATES,
)
from .coordinator import DpcConfigEntry, DpcDataUpdateCoordinator
from .entity import DpcEntity, place_entity_id

# The coordinator updates the entities: nothing to limit
PARALLEL_UPDATES = 0

EVENTS = {ATTR_TODAY: ATTR_EVENTS_TODAY, ATTR_TOMORROW: ATTR_EVENTS_TOMORROW}


async def async_setup_entry(
    hass: HomeAssistant, entry: DpcConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup sensor platform."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            DpcSensorCriticality(coordinator, entry),
            DpcSensorVigilance(coordinator, entry),
            *(
                DpcAlertDaySensor(coordinator, entry, day)
                for day in (ATTR_TODAY, ATTR_TOMORROW)
            ),
            *(
                DpcPrecipitationDaySensor(coordinator, entry, day)
                for day in (ATTR_TODAY, ATTR_TOMORROW, ATTR_AFTERTOMORROW)
            ),
        ]
    )


class DpcSensorCriticality(DpcEntity, SensorEntity):
    """Highest alert level of today and tomorrow (1 green to 4 red)."""

    _attr_translation_key = "criticality"

    def __init__(
        self, coordinator: DpcDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize Entities."""
        super().__init__(coordinator, entry)
        self.entity_id = place_entity_id(ENTITY_ID_FORMAT, entry, "alert")
        self._attr_unique_id = (
            f"{entry.data.get(CONF_NAME)}_criticality_"
            f"{entry.data.get(CONF_LATITUDE)}_{entry.data.get(CONF_LONGITUDE)}"
        )

    @property
    def available(self) -> bool:
        """Return whether a criticality bulletin is available."""
        return super().available and self.coordinator.data.criticality is not None

    @property
    def _days(self) -> dict[str, CriticalityDay]:
        """Return today and tomorrow, when the bulletin covers them."""
        return self.coordinator.data.criticality_days

    @property
    def _max_level(self) -> int:
        """Return the highest alert level of the days; 0 when unknown."""
        return max((day.level.value for day in self._days.values()), default=0)

    def _events(self, day: CriticalityDay) -> list[dict[str, Any]]:
        """Return the risks of a day at or above the warning level."""
        return [
            risk_event_attributes(risk)
            for risk in day.risks
            if risk.level >= self.warning_level
        ]

    @property
    def native_value(self) -> int | None:
        """Return the highest alert level of today and tomorrow."""
        return self._max_level or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attributes = super().extra_state_attributes
        if (latest := self.coordinator.data.criticality) is None:
            return attributes
        attributes |= criticality_attributes(latest)
        attributes[ATTR_MAX_LEVEL] = self._max_level
        attributes[ATTR_TOTAL_ALERTS] = 0
        for name, day in self._days.items():
            attributes[name] = criticality_day_attributes(day)
            attributes[ATTR_ZONE_NAME] = day.zone
            if events := self._events(day):
                attributes[EVENTS[name]] = events
                attributes[ATTR_TOTAL_ALERTS] += len(events)
        return attributes


class DpcSensorVigilance(DpcEntity, SensorEntity):
    """Highest expected precipitation of the next days (1 none to 5 very heavy)."""

    _attr_translation_key = "vigilance"

    def __init__(
        self, coordinator: DpcDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize Entities."""
        super().__init__(coordinator, entry)
        self.entity_id = place_entity_id(ENTITY_ID_FORMAT, entry, "vigilance")
        self._attr_unique_id = (
            f"{entry.data.get(CONF_NAME)}_vigilance_"
            f"{entry.data.get(CONF_LATITUDE)}_{entry.data.get(CONF_LONGITUDE)}"
        )

    @property
    def available(self) -> bool:
        """Return whether a vigilance bulletin is available."""
        return super().available and self.coordinator.data.vigilance is not None

    @property
    def _days(self) -> dict[str, VigilanceDay]:
        """Return today, tomorrow and the day after, when the bulletin covers them."""
        return self.coordinator.data.vigilance_days

    @property
    def _max_level(self) -> int:
        """Return the highest precipitation level of the days; 0 when unknown."""
        return max((day.precipitation.value for day in self._days.values()), default=0)

    @property
    def _total_alerts(self) -> int:
        """Return the number of days at or above the warning level."""
        return sum(
            day.precipitation >= self.warning_level for day in self._days.values()
        )

    @property
    def native_value(self) -> int | None:
        """Return the highest expected precipitation of the next days."""
        return self._max_level or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attributes = super().extra_state_attributes
        if (latest := self.coordinator.data.vigilance) is None:
            return attributes
        attributes |= vigilance_attributes(latest)
        attributes[ATTR_TOTAL_PHENOMENA] = 0
        for name, day in self._days.items():
            attributes[name] = vigilance_day_attributes(day)
            attributes[ATTR_ZONE_NAME] = day.zone
            attributes[ATTR_TOTAL_PHENOMENA] += len(attributes[name][ATTR_PHENOMENA])
        attributes[ATTR_MAX_LEVEL] = self._max_level
        attributes[ATTR_TOTAL_ALERTS] = self._total_alerts
        return attributes


class DpcDaySensor(DpcEntity, SensorEntity):
    """The level of one day of a bulletin, as a state Home Assistant translates.

    Dashboards show these states without templates, in the language of the user,
    e.g. "Orange alert" for the alert of tomorrow.
    """

    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(
        self,
        coordinator: DpcDataUpdateCoordinator,
        entry: ConfigEntry,
        level: str,
        day: str,
    ) -> None:
        """Initialize the sensor of a level ("alert") on a day ("today")."""
        super().__init__(coordinator, entry)
        key = f"{level}_{day}"
        self._day = day
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.unique_id}-{key}"
        self.entity_id = place_entity_id(ENTITY_ID_FORMAT, entry, key)


class DpcAlertDaySensor(DpcDaySensor):
    """Alert level of a day, green to red, and the risks at that level."""

    _attr_options = ALERT_LEVEL_STATES

    def __init__(
        self, coordinator: DpcDataUpdateCoordinator, entry: ConfigEntry, day: str
    ) -> None:
        """Initialize the alert sensor of today or tomorrow."""
        super().__init__(coordinator, entry, "alert", day)

    @property
    def available(self) -> bool:
        """Return whether a criticality bulletin is available."""
        return super().available and self.coordinator.data.criticality is not None

    @property
    def _risk(self) -> Risk | None:
        """Return the risk of the day, if the bulletin covers it."""
        day = self.coordinator.data.criticality_days.get(self._day)
        return Risk.of(day) if day else None

    @property
    def native_value(self) -> str | None:
        """Return the alert level of the day: green, yellow, orange or red."""
        risk = self._risk
        if risk is None or risk.level is AlertLevel.UNKNOWN:
            return None
        return str(risk.level)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the risks at the alert level, and when the day ends."""
        attributes = super().extra_state_attributes
        if (risk := self._risk) is not None:
            attributes[ATTR_RISKS] = [str(risk_type) for risk_type in risk.types]
            attributes[ATTR_VALID_UNTIL] = risk.valid_until
        return attributes


class DpcPrecipitationDaySensor(DpcDaySensor):
    """Expected precipitation of a day, from none to very heavy."""

    _attr_options = PRECIPITATION_STATES

    def __init__(
        self, coordinator: DpcDataUpdateCoordinator, entry: ConfigEntry, day: str
    ) -> None:
        """Initialize the precipitation sensor of today, tomorrow or the day after."""
        super().__init__(coordinator, entry, "precipitation", day)

    @property
    def available(self) -> bool:
        """Return whether a vigilance bulletin is available."""
        return super().available and self.coordinator.data.vigilance is not None

    @property
    def _forecast(self) -> VigilanceDay | None:
        """Return the forecast of the day, if the bulletin covers it."""
        return self.coordinator.data.vigilance_days.get(self._day)

    @property
    def native_value(self) -> str | None:
        """Return the expected precipitation of the day: none to very_heavy."""
        forecast = self._forecast
        if forecast is None or forecast.precipitation is Precipitation.UNKNOWN:
            return None
        return str(forecast.precipitation)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return when the day ends."""
        attributes = super().extra_state_attributes
        if (forecast := self._forecast) is not None:
            attributes[ATTR_VALID_UNTIL] = forecast.valid_until
        return attributes
