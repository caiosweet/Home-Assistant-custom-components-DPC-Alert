"""Sensor platform for Dpc."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from aiodpc import CriticalityDay, VigilanceDay, rome_date
from homeassistant.components.sensor import ENTITY_ID_FORMAT, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .attributes import (
    criticality_attributes,
    criticality_day_attributes,
    risk_event_attributes,
    vigilance_attributes,
    vigilance_day_attributes,
)
from .const import (
    ATTR_AFTERTOMORROW,
    ATTR_EVENTS_TODAY,
    ATTR_EVENTS_TOMORROW,
    ATTR_MAX_LEVEL,
    ATTR_PHENOMENA,
    ATTR_TODAY,
    ATTR_TOMORROW,
    ATTR_TOTAL_ALERTS,
    ATTR_TOTAL_PHENOMENA,
    ATTR_ZONE_NAME,
    DEFAULT_NAME,
    DOMAIN,
)
from .coordinator import DpcDataUpdateCoordinator
from .entity import DpcEntity

ICON = {"safety": "mdi:shield-check", "danger": "mdi:hazard-lights"}  # shield-account

EVENTS = {ATTR_TODAY: ATTR_EVENTS_TODAY, ATTR_TOMORROW: ATTR_EVENTS_TOMORROW}


def _language_independent_entity_id(entry: ConfigEntry, suffix: str) -> str:
    """Return sensor.<name>_<suffix>, the entity ID used before names were translated.

    For languages such as Italian and Portuguese, Home Assistant derives new entity
    IDs from the translated name (e.g. sensor.dpc_allerta). Suggesting the ID keeps
    it the same in every language. Existing entities keep their registered ID anyway.
    """
    return ENTITY_ID_FORMAT.format(
        slugify(f"{entry.data.get(CONF_NAME) or DEFAULT_NAME} {suffix}")
    )


def _covered[DayT](days: dict[str, DayT | None]) -> dict[str, DayT]:
    """Return the days covered by the bulletin, by attribute name."""
    return {name: day for name, day in days.items() if day is not None}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            DpcSensorCriticality(coordinator, entry),
            DpcSensorVigilance(coordinator, entry),
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
        self.entity_id = _language_independent_entity_id(entry, "alert")
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
        latest = self.coordinator.data.criticality
        if latest is None:
            return {}
        bulletin = latest.bulletin
        return _covered({ATTR_TODAY: bulletin.today, ATTR_TOMORROW: bulletin.tomorrow})

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
    def icon(self) -> str:
        """Return the icon of the sensor."""
        has_events = any(self._events(day) for day in self._days.values())
        return ICON["danger"] if has_events else ICON["safety"]

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
        self.entity_id = _language_independent_entity_id(entry, "vigilance")
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
        latest = self.coordinator.data.vigilance
        if latest is None:
            return {}
        bulletin = latest.bulletin
        today = rome_date()
        return _covered(
            {
                ATTR_TODAY: bulletin.on(today),
                ATTR_TOMORROW: bulletin.on(today + timedelta(days=1)),
                ATTR_AFTERTOMORROW: bulletin.on(today + timedelta(days=2)),
            }
        )

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
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return ICON["danger"] if self._total_alerts else ICON["safety"]

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
