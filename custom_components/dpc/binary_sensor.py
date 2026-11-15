"""Binary sensor platform for Dpc: each risk type, today and tomorrow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiodpc import CriticalityDay, Day, RiskType
from homeassistant.components.binary_sensor import (
    ENTITY_ID_FORMAT,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

# Re-exported without being declared: binary_sensor.const only exists since 2026.9
from homeassistant.components.binary_sensor import (  # type: ignore[attr-defined]
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .attributes import criticality_attributes, risk_day_attributes
from .coordinator import DpcConfigEntry, DpcDataUpdateCoordinator
from .entity import DpcEntity, language_independent_entity_id

# The coordinator updates the entities: nothing to limit
PARALLEL_UPDATES = 0

# The keys are the Italian names the sensors have always had: their unique IDs,
# entity IDs and translations are built from them.
RISK_KEYS = {
    RiskType.HYDRAULIC: "idraulico",
    RiskType.THUNDERSTORMS: "temporali",
    RiskType.HYDROGEOLOGICAL: "idrogeologico",
}
DAY_KEYS = {Day.TODAY: "oggi", Day.TOMORROW: "domani"}


@dataclass(frozen=True, kw_only=True)
class DpcRiskEntityDescription(BinarySensorEntityDescription):
    """Description of the binary sensor of a risk type on a day."""

    risk: RiskType
    day: Day


RISK_DESCRIPTIONS = tuple(
    DpcRiskEntityDescription(
        key=f"{RISK_KEYS[risk]}_{DAY_KEYS[day]}",
        translation_key=f"{RISK_KEYS[risk]}_{DAY_KEYS[day]}",
        device_class=BinarySensorDeviceClass.SAFETY,
        risk=risk,
        day=day,
    )
    for day in Day
    for risk in RiskType
)


async def async_setup_entry(
    hass: HomeAssistant, entry: DpcConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup binary_sensor platform."""
    coordinator = entry.runtime_data
    async_add_entities(
        DpcRiskBinarySensor(
            coordinator,
            entry,
            description,
            language_independent_entity_id(ENTITY_ID_FORMAT, entry, description.key),
        )
        for description in RISK_DESCRIPTIONS
    )


class DpcRiskBinarySensor(DpcEntity, BinarySensorEntity):
    """On when the risk on the day is at or above the warning level."""

    entity_description: DpcRiskEntityDescription

    def __init__(
        self,
        coordinator: DpcDataUpdateCoordinator,
        entry: ConfigEntry,
        description: DpcRiskEntityDescription,
        entity_id: str,
    ) -> None:
        """Initialize Entities."""
        super().__init__(coordinator, entry)
        self.entity_description = description
        self.entity_id = entity_id
        self._attr_unique_id = f"{entry.unique_id}-{description.key}"

    @property
    def available(self) -> bool:
        """Return whether a criticality bulletin is available."""
        return super().available and self.coordinator.data.criticality is not None

    @property
    def _day(self) -> CriticalityDay | None:
        """Return the assessment of the day, if the bulletin covers it."""
        latest = self.coordinator.data.criticality
        return latest.bulletin.on(self.entity_description.day) if latest else None

    @property
    def is_on(self) -> bool | None:
        """Return whether the risk is at or above the warning level."""
        if (day := self._day) is None:
            return None
        return day.assessment(self.entity_description.risk).level >= self.warning_level

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attributes = super().extra_state_attributes
        latest = self.coordinator.data.criticality
        if latest and (day := self._day):
            risk = day.assessment(self.entity_description.risk)
            attributes |= criticality_attributes(latest)
            attributes |= risk_day_attributes(day, risk)
        return attributes
