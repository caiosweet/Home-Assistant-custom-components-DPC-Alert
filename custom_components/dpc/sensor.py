"""Sensor platform for Dpc: the place and each of its days.

The place has its highest alert and precipitation, and, for its diagnostics,
its zones and bulletins. Each day has its alert, its criticality, the level of
each risk, its precipitation and the number of phenomena near the place. The
states are the keys of aiodpc, which Home Assistant translates.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, time
from typing import Any

from aiodpc import (
    CRITICALITY_PAGE_URL,
    ROME_TZ,
    VIGILANCE_PAGE_URL,
    AlertLevel,
    Criticality,
    CriticalityDay,
    Precipitation,
    Risk,
    RiskType,
    VigilanceDay,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    EntityCategory,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ALERT_LEVEL_STATES,
    ATTR_ID,
    ATTR_LAST_CHECK,
    ATTR_LINK,
    ATTR_RISKS,
    ATTR_TOTAL_ALERTS,
    CRITICALITY_STATES,
    HIGHEST_ALERT_STATES,
    HIGHEST_PRECIPITATION_STATES,
    PRECIPITATION_STATES,
    RISK_TRANSLATION_KEYS,
    PlaceDay,
)
from .coordinator import (
    DpcConfigEntry,
    DpcData,
    DpcDataUpdateCoordinator,
    LatestBulletin,
)
from .entity import DpcEntity

# The coordinator updates the entities: nothing to limit
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: DpcConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensors of the place and of its days."""
    coordinator = entry.runtime_data
    # Only the vigilance bulletin covers the day after tomorrow
    criticality_days = [
        day for day in coordinator.days if day is not PlaceDay.AFTER_TOMORROW
    ]
    async_add_entities(
        [
            DpcHighestAlertSensor(coordinator, entry),
            DpcHighestPrecipitationSensor(coordinator, entry),
            *(
                DpcBulletinSensor(coordinator, entry, description)
                for description in BULLETIN_SENSORS
            ),
            *(DpcAlertDaySensor(coordinator, entry, day) for day in criticality_days),
            *(
                DpcCriticalityDaySensor(coordinator, entry, day)
                for day in criticality_days
            ),
            *(
                DpcRiskLevelSensor(coordinator, entry, day, risk)
                for day in criticality_days
                for risk in RiskType
            ),
            *(
                DpcPrecipitationDaySensor(coordinator, entry, day)
                for day in coordinator.days
            ),
            *(
                DpcNearbyPhenomenaSensor(coordinator, entry, day)
                for day in coordinator.days
            ),
        ]
    )


def _last_day[DayT](days: Mapping[PlaceDay, DayT]) -> DayT | None:
    """Return the last day the bulletin covers, if any."""
    return [*days.values()][-1] if days else None


@dataclass(frozen=True, kw_only=True)
class DpcBulletinSensorEntityDescription(SensorEntityDescription):
    """Description of a sensor of the bulletins of a place, for its diagnostics."""

    translation_key: str
    latest_fn: Callable[[DpcData], LatestBulletin[Any] | None]
    """Return the bulletin the sensor reads; None until one is fetched."""
    value_fn: Callable[[DpcData], str | datetime | None]
    link: str | None = None
    """The page of the bulletin, for a sensor of the bulletin itself."""


BULLETIN_SENSORS = (
    DpcBulletinSensorEntityDescription(
        key="alert_zone",
        translation_key="alert_zone",
        latest_fn=lambda data: data.criticality,
        value_fn=lambda data: (
            day.zone if (day := _last_day(data.criticality_days)) else None
        ),
    ),
    DpcBulletinSensorEntityDescription(
        key="vigilance_zone",
        translation_key="vigilance_zone",
        latest_fn=lambda data: data.vigilance,
        value_fn=lambda data: (
            day.zone if (day := _last_day(data.vigilance_days)) else None
        ),
    ),
    DpcBulletinSensorEntityDescription(
        key="criticality_bulletin",
        translation_key="criticality_bulletin",
        device_class=SensorDeviceClass.TIMESTAMP,
        latest_fn=lambda data: data.criticality,
        value_fn=lambda data: (
            data.criticality.bulletin.published if data.criticality else None
        ),
        link=CRITICALITY_PAGE_URL,
    ),
    DpcBulletinSensorEntityDescription(
        key="vigilance_bulletin",
        translation_key="vigilance_bulletin",
        device_class=SensorDeviceClass.TIMESTAMP,
        latest_fn=lambda data: data.vigilance,
        # The day of publication, at midnight in Italy
        value_fn=lambda data: (
            datetime.combine(data.vigilance.bulletin.date, time(), tzinfo=ROME_TZ)
            if data.vigilance
            else None
        ),
        link=VIGILANCE_PAGE_URL,
    ),
    DpcBulletinSensorEntityDescription(
        key="criticality_valid_until",
        translation_key="criticality_valid_until",
        device_class=SensorDeviceClass.TIMESTAMP,
        latest_fn=lambda data: data.criticality,
        value_fn=lambda data: (
            day.valid_until if (day := _last_day(data.criticality_days)) else None
        ),
    ),
    DpcBulletinSensorEntityDescription(
        key="vigilance_valid_until",
        translation_key="vigilance_valid_until",
        device_class=SensorDeviceClass.TIMESTAMP,
        latest_fn=lambda data: data.vigilance,
        value_fn=lambda data: (
            day.valid_until if (day := _last_day(data.vigilance_days)) else None
        ),
    ),
)
"""The diagnostic sensors of the place: its zones, bulletins and their end."""


class DpcBulletinSensor(DpcEntity, SensorEntity):
    """A sensor of the bulletins of a place: a zone, a bulletin or its end."""

    entity_description: DpcBulletinSensorEntityDescription
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    # They change with every bulletin, and the state has its time
    _unrecorded_attributes = frozenset({ATTR_ID, ATTR_LINK, ATTR_LAST_CHECK})

    def __init__(
        self,
        coordinator: DpcDataUpdateCoordinator,
        entry: ConfigEntry,
        description: DpcBulletinSensorEntityDescription,
    ) -> None:
        """Initialize a sensor of the bulletins of the place."""
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}-{description.key}"
        self.suggest_entity_id(Platform.SENSOR, description.translation_key)

    @property
    def available(self) -> bool:
        """Return whether the bulletin has been fetched."""
        data = self.coordinator.data
        return super().available and self.entity_description.latest_fn(data) is not None

    @property
    def native_value(self) -> str | datetime | None:
        """Return the zone, the publication or the end of the bulletin."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the ID of a bulletin, its page and when it was last checked."""
        latest = self.entity_description.latest_fn(self.coordinator.data)
        if (link := self.entity_description.link) is None or latest is None:
            return None
        return {
            ATTR_ID: latest.bulletin.id,
            ATTR_LINK: link,
            ATTR_LAST_CHECK: latest.checked_at,
        }


class DpcHighestAlertSensor(DpcEntity, SensorEntity):
    """Highest alert level of the place, today and tomorrow: 1 green to 4 red.

    Of both days, whatever the days the place shows: the alert of the bulletin.
    """

    _attr_translation_key = "highest_alert"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = HIGHEST_ALERT_STATES

    def __init__(
        self, coordinator: DpcDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the highest alert of the place."""
        super().__init__(coordinator, entry)
        # The unique ID it has always had, from when it was the criticality sensor
        self._attr_unique_id = (
            f"{entry.data.get(CONF_NAME)}_criticality_"
            f"{entry.data.get(CONF_LATITUDE)}_{entry.data.get(CONF_LONGITUDE)}"
        )
        self.suggest_entity_id(Platform.SENSOR, "highest_alert")

    @property
    def available(self) -> bool:
        """Return whether a criticality bulletin is available."""
        return super().available and self.coordinator.data.criticality is not None

    @property
    def _days(self) -> Mapping[PlaceDay, CriticalityDay]:
        """Return today and tomorrow, when the bulletin covers them."""
        return self.coordinator.data.criticality_days

    def _warnings(self, day: CriticalityDay) -> int:
        """Return the number of risks of a day at or above the warning level."""
        return sum(risk.level >= self.warning_level for risk in day.risks)

    @property
    def native_value(self) -> str | None:
        """Return the highest alert level of today and tomorrow, e.g. "3"."""
        level = max((day.level for day in self._days.values()), default=None)
        if level is None or level is AlertLevel.UNKNOWN:
            return None
        return str(level.code)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the number of risks at or above the warning level."""
        return {ATTR_TOTAL_ALERTS: sum(map(self._warnings, self._days.values()))}


class DpcHighestPrecipitationSensor(DpcEntity, SensorEntity):
    """Highest expected precipitation of the place, in 3 days: 1 none to 5 very heavy."""

    _attr_translation_key = "highest_precipitation"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = HIGHEST_PRECIPITATION_STATES

    def __init__(
        self, coordinator: DpcDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the highest precipitation of the place."""
        super().__init__(coordinator, entry)
        # The unique ID it has always had, from when it was the vigilance sensor
        self._attr_unique_id = (
            f"{entry.data.get(CONF_NAME)}_vigilance_"
            f"{entry.data.get(CONF_LATITUDE)}_{entry.data.get(CONF_LONGITUDE)}"
        )
        self.suggest_entity_id(Platform.SENSOR, "highest_precipitation")

    @property
    def available(self) -> bool:
        """Return whether a vigilance bulletin is available."""
        return super().available and self.coordinator.data.vigilance is not None

    @property
    def _days(self) -> Mapping[PlaceDay, VigilanceDay]:
        """Return today, tomorrow and the day after, when the bulletin covers them."""
        return self.coordinator.data.vigilance_days

    @property
    def native_value(self) -> str | None:
        """Return the highest expected precipitation of the days, e.g. "3"."""
        amount = max((day.precipitation for day in self._days.values()), default=None)
        if amount is None or amount is Precipitation.UNKNOWN:
            return None
        return str(amount.code)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the number of days at or above the warning level."""
        return {
            ATTR_TOTAL_ALERTS: sum(
                day.precipitation >= self.warning_level for day in self._days.values()
            )
        }


class DpcDaySensor(DpcEntity, SensorEntity):
    """A sensor of one day of the place, on the device of the day.

    Dashboards show its state without templates, in the language of the user,
    e.g. "Orange alert" for the alert of tomorrow.
    """

    def __init__(
        self,
        coordinator: DpcDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        day: PlaceDay,
    ) -> None:
        """Initialize the sensor of a day, e.g. the "alert" of "today"."""
        super().__init__(coordinator, entry, day)
        self._day = day
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.unique_id}-{key}_{day}"
        self.suggest_entity_id(Platform.SENSOR, key)


class DpcCriticalitySensor(DpcDaySensor):
    """A sensor of a day of the criticality bulletin."""

    @property
    def available(self) -> bool:
        """Return whether a criticality bulletin is available."""
        return super().available and self.coordinator.data.criticality is not None

    @property
    def _assessment(self) -> CriticalityDay | None:
        """Return the assessment of the day, if the bulletin covers it."""
        return self.coordinator.data.criticality_days.get(self._day)


class DpcAlertDaySensor(DpcCriticalitySensor):
    """Alert level of a day, green to red, and the risks at that level."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ALERT_LEVEL_STATES

    def __init__(
        self, coordinator: DpcDataUpdateCoordinator, entry: ConfigEntry, day: PlaceDay
    ) -> None:
        """Initialize the alert of today or tomorrow."""
        super().__init__(coordinator, entry, "alert", day)

    @property
    def _risk(self) -> Risk | None:
        """Return the risk of the day, if the bulletin covers it."""
        day = self._assessment
        return Risk.of(day) if day else None

    @property
    def native_value(self) -> str | None:
        """Return the alert level of the day: green, yellow, orange or red."""
        risk = self._risk
        if risk is None or risk.level is AlertLevel.UNKNOWN:
            return None
        return str(risk.level)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the risks at the alert level of the day."""
        if (risk := self._risk) is None:
            return None
        return {ATTR_RISKS: [str(risk_type) for risk_type in risk.types]}


def criticality_state(day: CriticalityDay) -> str | None:
    """Return the criticality of a day and the risk its map shows.

    E.g. "moderate_hydrogeological" for "Moderata per rischio idrogeologico",
    "absent" for a green zone; None for a text aiodpc does not recognise.
    """
    criticality = day.criticality
    if criticality is Criticality.ABSENT:
        return str(criticality)
    if criticality is Criticality.UNKNOWN or (risk := day.mapped_risk) is None:
        return None
    return f"{criticality}_{risk}"


class DpcCriticalityDaySensor(DpcCriticalitySensor):
    """Criticality of a day, as the DPC summary and map give it."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = CRITICALITY_STATES

    def __init__(
        self, coordinator: DpcDataUpdateCoordinator, entry: ConfigEntry, day: PlaceDay
    ) -> None:
        """Initialize the criticality of today or tomorrow."""
        super().__init__(coordinator, entry, "criticality", day)

    @property
    def native_value(self) -> str | None:
        """Return the criticality of the day, e.g. moderate_hydrogeological."""
        day = self._assessment
        return criticality_state(day) if day else None


class DpcRiskLevelSensor(DpcCriticalitySensor):
    """Alert level of one risk on a day, green to red."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ALERT_LEVEL_STATES

    def __init__(
        self,
        coordinator: DpcDataUpdateCoordinator,
        entry: ConfigEntry,
        day: PlaceDay,
        risk: RiskType,
    ) -> None:
        """Initialize the level of a risk, e.g. hydraulic_risk_level, on a day."""
        super().__init__(
            coordinator, entry, f"{RISK_TRANSLATION_KEYS[risk]}_level", day
        )
        self._risk_type = risk

    @property
    def native_value(self) -> str | None:
        """Return the alert level of the risk: green, yellow, orange or red."""
        if (day := self._assessment) is None:
            return None
        level = day.assessment(self._risk_type).level
        return None if level is AlertLevel.UNKNOWN else str(level)


class DpcVigilanceSensor(DpcDaySensor):
    """A sensor of a day of the vigilance bulletin."""

    @property
    def available(self) -> bool:
        """Return whether a vigilance bulletin is available."""
        return super().available and self.coordinator.data.vigilance is not None

    @property
    def _forecast(self) -> VigilanceDay | None:
        """Return the forecast of the day, if the bulletin covers it."""
        return self.coordinator.data.vigilance_days.get(self._day)


class DpcPrecipitationDaySensor(DpcVigilanceSensor):
    """Expected precipitation of a day, from none to very heavy."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = PRECIPITATION_STATES

    def __init__(
        self, coordinator: DpcDataUpdateCoordinator, entry: ConfigEntry, day: PlaceDay
    ) -> None:
        """Initialize the precipitation of today, tomorrow or the day after."""
        super().__init__(coordinator, entry, "precipitation", day)

    @property
    def native_value(self) -> str | None:
        """Return the expected precipitation of the day: none to very_heavy."""
        forecast = self._forecast
        if forecast is None or forecast.precipitation is Precipitation.UNKNOWN:
            return None
        return str(forecast.precipitation)


class DpcNearbyPhenomenaSensor(DpcVigilanceSensor):
    """Number of weather phenomena of a day within the radius of the place.

    The phenomena themselves are geolocation entities of the same day.
    """

    def __init__(
        self, coordinator: DpcDataUpdateCoordinator, entry: ConfigEntry, day: PlaceDay
    ) -> None:
        """Initialize the number of phenomena of today, tomorrow or the day after."""
        super().__init__(coordinator, entry, "nearby_phenomena", day)

    @property
    def native_value(self) -> int | None:
        """Return the number of phenomena near the place on the day."""
        if (forecast := self._forecast) is None:
            return None
        # Codes unknown to aiodpc have no category: they have no entity either
        return sum(phenomenon.category is not None for phenomenon in forecast.phenomena)
