"""Sensor platform for Dpc."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from aiodpc import AlertLevel, CriticalityDay, Precipitation, Risk, VigilanceDay
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .attributes import criticality_attributes, vigilance_attributes
from .const import (
    ALERT_LEVEL_STATES,
    ATTR_DESCRIPTION,
    ATTR_MAX_LEVEL,
    ATTR_RISKS,
    ATTR_TOTAL_ALERTS,
    ATTR_TOTAL_PHENOMENA,
    ATTR_VALID_UNTIL,
    ATTR_ZONE_NAME,
    PRECIPITATION_STATES,
    PlaceDay,
)
from .coordinator import DpcConfigEntry, DpcDataUpdateCoordinator
from .entity import DpcEntity

# The coordinator updates the entities: nothing to limit
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: DpcConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup sensor platform."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            DpcSensorCriticality(coordinator, entry),
            DpcSensorVigilance(coordinator, entry),
            # Only the vigilance bulletin covers the day after tomorrow
            *(
                DpcAlertDaySensor(coordinator, entry, day)
                for day in coordinator.days
                if day is not PlaceDay.AFTER_TOMORROW
            ),
            *(
                DpcPrecipitationDaySensor(coordinator, entry, day)
                for day in coordinator.days
            ),
        ]
    )


def _zone_of_the_last_day(
    days: Iterable[CriticalityDay | VigilanceDay],
) -> dict[str, str]:
    """Return the zone of the last day covered by the bulletin, if any."""
    covered = list(days)
    if not covered:
        return {}
    return {ATTR_ZONE_NAME: covered[-1].zone}


class DpcSensorCriticality(DpcEntity, SensorEntity):
    """Highest alert level of today and tomorrow (1 green to 4 red)."""

    _attr_translation_key = "criticality"

    def __init__(
        self, coordinator: DpcDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the highest alert of the place."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = (
            f"{entry.data.get(CONF_NAME)}_criticality_"
            f"{entry.data.get(CONF_LATITUDE)}_{entry.data.get(CONF_LONGITUDE)}"
        )
        self.suggest_entity_id(Platform.SENSOR, "criticality")

    @property
    def available(self) -> bool:
        """Return whether a criticality bulletin is available."""
        return super().available and self.coordinator.data.criticality is not None

    @property
    def _days(self) -> dict[PlaceDay, CriticalityDay]:
        """Return today and tomorrow, when the bulletin covers them."""
        return self.coordinator.data.criticality_days

    @property
    def _max_level(self) -> int:
        """Return the highest alert level of the days; 0 when unknown."""
        return max((day.level.value for day in self._days.values()), default=0)

    def _warnings(self, day: CriticalityDay) -> int:
        """Return the number of risks of a day at or above the warning level."""
        return sum(risk.level >= self.warning_level for risk in day.risks)

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
        attributes[ATTR_TOTAL_ALERTS] = sum(map(self._warnings, self._days.values()))
        attributes |= _zone_of_the_last_day(self._days.values())
        return attributes


class DpcSensorVigilance(DpcEntity, SensorEntity):
    """Highest expected precipitation of the next days (1 none to 5 very heavy)."""

    _attr_translation_key = "vigilance"

    def __init__(
        self, coordinator: DpcDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the highest precipitation of the place."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = (
            f"{entry.data.get(CONF_NAME)}_vigilance_"
            f"{entry.data.get(CONF_LATITUDE)}_{entry.data.get(CONF_LONGITUDE)}"
        )
        self.suggest_entity_id(Platform.SENSOR, "vigilance")

    @property
    def available(self) -> bool:
        """Return whether a vigilance bulletin is available."""
        return super().available and self.coordinator.data.vigilance is not None

    @property
    def _days(self) -> dict[PlaceDay, VigilanceDay]:
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
        attributes[ATTR_TOTAL_PHENOMENA] = sum(
            # Codes unknown to aiodpc have no category: they were never listed
            phenomenon.category is not None
            for day in self._days.values()
            for phenomenon in day.phenomena
        )
        attributes[ATTR_MAX_LEVEL] = self._max_level
        attributes[ATTR_TOTAL_ALERTS] = self._total_alerts
        attributes |= _zone_of_the_last_day(self._days.values())
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
        day: PlaceDay,
    ) -> None:
        """Initialize the sensor of a level ("alert") on a day ("today")."""
        super().__init__(coordinator, entry, day)
        self._day = day
        self._attr_translation_key = level
        self._attr_unique_id = f"{entry.unique_id}-{level}_{day}"
        self.suggest_entity_id(Platform.SENSOR, level)


class DpcAlertDaySensor(DpcDaySensor):
    """Alert level of a day, green to red, and the risks at that level."""

    _attr_options = ALERT_LEVEL_STATES

    def __init__(
        self, coordinator: DpcDataUpdateCoordinator, entry: ConfigEntry, day: PlaceDay
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
            # The summary as DPC writes it, in Italian, next to the translated state
            attributes[ATTR_DESCRIPTION] = risk.description
        return attributes


class DpcPrecipitationDaySensor(DpcDaySensor):
    """Expected precipitation of a day, from none to very heavy."""

    _attr_options = PRECIPITATION_STATES

    def __init__(
        self, coordinator: DpcDataUpdateCoordinator, entry: ConfigEntry, day: PlaceDay
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
