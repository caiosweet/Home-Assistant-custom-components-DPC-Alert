"""Binary sensor platform for Dpc: each risk type, today and tomorrow."""

from __future__ import annotations

from dataclasses import dataclass

from aiodpc import CriticalityDay, RiskType
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

# Re-exported without being declared: binary_sensor.const only exists since 2026.9
from homeassistant.components.binary_sensor import (  # type: ignore[attr-defined]
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import RISK_TRANSLATION_KEYS, PlaceDay
from .coordinator import DpcConfigEntry, DpcDataUpdateCoordinator
from .entity import DpcEntity

# The coordinator updates the entities: nothing to limit
PARALLEL_UPDATES = 0

# The unique IDs keep the Italian names the sensors have always had
RISK_KEYS = {
    RiskType.HYDRAULIC: "idraulico",
    RiskType.THUNDERSTORMS: "temporali",
    RiskType.HYDROGEOLOGICAL: "idrogeologico",
}
# The days of the criticality bulletin: only the vigilance bulletin covers the
# day after tomorrow
DAY_KEYS = {PlaceDay.TODAY: "oggi", PlaceDay.TOMORROW: "domani"}


@dataclass(frozen=True, kw_only=True)
class DpcRiskEntityDescription(BinarySensorEntityDescription):
    """Description of the binary sensor of a risk type on a day."""

    translation_key: str
    risk: RiskType
    day: PlaceDay


RISK_DESCRIPTIONS = tuple(
    DpcRiskEntityDescription(
        key=f"{RISK_KEYS[risk]}_{DAY_KEYS[day]}",
        translation_key=RISK_TRANSLATION_KEYS[risk],
        device_class=BinarySensorDeviceClass.SAFETY,
        risk=risk,
        day=day,
    )
    for day in DAY_KEYS
    for risk in RiskType
)


async def async_setup_entry(
    hass: HomeAssistant, entry: DpcConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup binary_sensor platform."""
    coordinator = entry.runtime_data
    async_add_entities(
        DpcRiskBinarySensor(coordinator, entry, description)
        for description in RISK_DESCRIPTIONS
        if description.day in coordinator.days
    )


class DpcRiskBinarySensor(DpcEntity, BinarySensorEntity):
    """On when the risk on the day is at or above the warning level."""

    entity_description: DpcRiskEntityDescription

    def __init__(
        self,
        coordinator: DpcDataUpdateCoordinator,
        entry: ConfigEntry,
        description: DpcRiskEntityDescription,
    ) -> None:
        """Initialize the binary sensor of a risk on a day."""
        super().__init__(coordinator, entry, description.day)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}-{description.key}"
        self.suggest_entity_id(Platform.BINARY_SENSOR, description.translation_key)

    @property
    def available(self) -> bool:
        """Return whether a criticality bulletin is available."""
        return super().available and self.coordinator.data.criticality is not None

    @property
    def _day(self) -> CriticalityDay | None:
        """Return the assessment of the day, if the bulletin covers it."""
        latest = self.coordinator.data.criticality
        return latest.bulletin.on(self.entity_description.day.day) if latest else None

    @property
    def is_on(self) -> bool | None:
        """Return whether the risk is at or above the warning level."""
        if (day := self._day) is None:
            return None
        return day.assessment(self.entity_description.risk).level >= self.warning_level
