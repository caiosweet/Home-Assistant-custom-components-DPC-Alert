"""Tests for the DPC sensors: the place and each of its days."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from aiodpc import (
    ATTRIBUTION,
    CRITICALITY_PAGE_URL,
    VIGILANCE_PAGE_URL,
    AlertLevel,
    Precipitation,
)
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dpc.const import CONF_DAYS, CONF_WARNING_LEVEL
from custom_components.dpc.coordinator import DpcData

from . import CRIT_ID, UNIQUE_ID, VIGI_ID, get_entity_id, rome, sensor_unique_id


def summary_state(hass: HomeAssistant, bulletin: str) -> State:
    """Return the highest alert ("criticality") or precipitation ("vigilance")."""
    state = hass.states.get(
        get_entity_id(hass, Platform.SENSOR, sensor_unique_id(bulletin))
    )
    assert state is not None
    return state


def sensor_state(hass: HomeAssistant, key: str) -> State:
    """Return the state of a sensor by the end of its unique ID, e.g. alert_today."""
    state = hass.states.get(get_entity_id(hass, Platform.SENSOR, f"{UNIQUE_ID}-{key}"))
    assert state is not None
    return state


async def refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Update the bulletins of an entry, as its update interval does."""
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


@pytest.mark.usefixtures("init_integration")
async def test_highest_alert(hass: HomeAssistant) -> None:
    """Test the highest alert of the place in the bulletin issued on 2026-11-14."""
    state = summary_state(hass, "criticality")

    # Moderate (orange) hydrogeological risk tomorrow
    assert state.entity_id == "sensor.dpc_highest_alert"
    assert state.state == "3"
    assert dict(state.attributes) == {
        # The numbers it has always had, which Home Assistant shows as levels
        "options": ["1", "2", "3", "4"],
        "device_class": "enum",
        "attribution": ATTRIBUTION,
        # Risks at or above the default warning level (2, yellow): 2 today, 1 tomorrow
        "total_alerts": 3,
        "friendly_name": "DPC Highest alert",
    }


@pytest.mark.usefixtures("init_integration")
async def test_highest_precipitation(hass: HomeAssistant) -> None:
    """Test the highest precipitation of the place in the next three days."""
    state = summary_state(hass, "vigilance")

    assert state.entity_id == "sensor.dpc_highest_precipitation"
    assert state.state == "3"
    assert state.attributes["options"] == ["1", "2", "3", "4", "5"]
    # Days at or above the default warning level (2): today and tomorrow
    assert state.attributes["total_alerts"] == 2
    assert state.attributes["friendly_name"] == "DPC Highest precipitation"


@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize("entry_options", [{CONF_WARNING_LEVEL: 3}])
async def test_summaries_with_higher_warning_level(hass: HomeAssistant) -> None:
    """Test that only warnings at or above the configured level are counted."""
    alert = summary_state(hass, "criticality")
    assert alert.state == "3"
    assert alert.attributes["total_alerts"] == 1

    assert summary_state(hass, "vigilance").attributes["total_alerts"] == 1


@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize("entry_options", [{CONF_DAYS: []}])
async def test_place_without_days(hass: HomeAssistant) -> None:
    """Test that a place with no day keeps its summaries and bulletins.

    The highest alert is of the whole bulletin, today and tomorrow.
    """
    assert {state.entity_id for state in hass.states.async_all(Platform.SENSOR)} == {
        "sensor.dpc_highest_alert",
        "sensor.dpc_highest_precipitation",
        "sensor.dpc_alert_zone",
        "sensor.dpc_vigilance_zone",
        "sensor.dpc_criticality_bulletin",
        "sensor.dpc_vigilance_bulletin",
        "sensor.dpc_criticality_valid_until",
        "sensor.dpc_vigilance_valid_until",
    }
    assert summary_state(hass, "criticality").state == "3"


@pytest.mark.usefixtures("init_integration")
async def test_bulletins_of_the_place(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Test the diagnostic sensors of the zones and bulletins of the place."""
    assert sensor_state(hass, "alert_zone").state == "Bacini di Roma"
    assert sensor_state(hass, "vigilance_zone").state == "Lazio centrale"

    criticality = sensor_state(hass, "criticality_bulletin")
    assert datetime.fromisoformat(criticality.state) == rome(2026, 11, 14, 14, 30)
    assert criticality.attributes["id"] == CRIT_ID
    assert criticality.attributes["link"] == CRITICALITY_PAGE_URL
    assert criticality.attributes["last_check"] == rome(2026, 11, 14, 15)
    assert criticality.attributes["device_class"] == "timestamp"
    assert (
        criticality.attributes["friendly_name"]
        == "DPC Hydrogeological and hydraulic criticality bulletin"
    )

    vigilance = sensor_state(hass, "vigilance_bulletin")
    assert datetime.fromisoformat(vigilance.state) == rome(2026, 11, 14)
    assert vigilance.attributes["id"] == VIGI_ID
    assert vigilance.attributes["link"] == VIGILANCE_PAGE_URL

    # The end of the last day of each bulletin
    assert datetime.fromisoformat(
        sensor_state(hass, "criticality_valid_until").state
    ) == rome(2026, 11, 16)
    assert datetime.fromisoformat(
        sensor_state(hass, "vigilance_valid_until").state
    ) == rome(2026, 11, 17)

    registered = entity_registry.async_get(criticality.entity_id)
    assert registered is not None
    assert registered.entity_category is er.EntityCategory.DIAGNOSTIC


@pytest.mark.usefixtures("init_integration")
async def test_alert_of_each_day(hass: HomeAssistant) -> None:
    """Test the alert level of today and tomorrow, and the risks at that level."""
    today = sensor_state(hass, "alert_today")
    assert today.entity_id == "sensor.dpc_today_alert"
    assert today.state == "yellow"
    assert today.attributes["options"] == ["green", "yellow", "orange", "red"]
    assert today.attributes["risks"] == ["thunderstorms", "hydrogeological"]
    assert today.attributes["friendly_name"] == "DPC · Today Alert"

    tomorrow = sensor_state(hass, "alert_tomorrow")
    assert tomorrow.state == "orange"
    assert tomorrow.attributes["risks"] == ["hydrogeological"]


@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize("entry_options", [{CONF_WARNING_LEVEL: 4}])
async def test_alert_of_a_day_ignores_the_warning_level(hass: HomeAssistant) -> None:
    """Test that the alert of a day is the level of the bulletin, whatever the options."""
    assert sensor_state(hass, "alert_tomorrow").state == "orange"


@pytest.mark.usefixtures("init_integration")
async def test_criticality_of_each_day(hass: HomeAssistant) -> None:
    """Test the criticality of a day and the risk its map shows, from DPC's summary.

    "Ordinaria per rischio temporali" today, "Moderata per rischio
    idrogeologico" tomorrow.
    """
    today = sensor_state(hass, "criticality_today")
    assert today.entity_id == "sensor.dpc_today_criticality"
    assert today.state == "ordinary_thunderstorms"
    assert len(today.attributes["options"]) == 10
    assert (
        sensor_state(hass, "criticality_tomorrow").state == "moderate_hydrogeological"
    )


async def test_criticality_of_a_day_without_alert(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test a green day: no significant phenomena expected, no risk on the map."""
    coordinator = init_integration.runtime_data
    criticality = coordinator.data.criticality
    assert criticality is not None
    today, *later = criticality.bulletin.days
    green = replace(
        today,
        level=AlertLevel.GREEN,
        description="Assenza di fenomeni significativi prevedibili",
    )

    coordinator.async_set_updated_data(
        replace(
            coordinator.data,
            criticality=replace(
                criticality,
                bulletin=replace(criticality.bulletin, days=(green, *later)),
            ),
        )
    )
    await hass.async_block_till_done()

    assert sensor_state(hass, "criticality_today").state == "absent"


@pytest.mark.usefixtures("init_integration")
async def test_level_of_each_risk(hass: HomeAssistant) -> None:
    """Test the alert level of each risk, today and tomorrow."""
    assert {
        key: sensor_state(hass, key).state
        for key in (
            "hydraulic_risk_level_today",
            "thunderstorm_risk_level_today",
            "hydrogeological_risk_level_today",
            "hydrogeological_risk_level_tomorrow",
        )
    } == {
        "hydraulic_risk_level_today": "green",
        "thunderstorm_risk_level_today": "yellow",
        "hydrogeological_risk_level_today": "yellow",
        "hydrogeological_risk_level_tomorrow": "orange",
    }
    today = sensor_state(hass, "hydraulic_risk_level_today")
    assert today.entity_id == "sensor.dpc_today_hydraulic_risk_level"
    assert today.attributes["friendly_name"] == "DPC · Today Hydraulic risk level"


@pytest.mark.usefixtures("init_integration")
async def test_precipitation_of_each_day(hass: HomeAssistant) -> None:
    """Test the expected precipitation of the three days of the vigilance bulletin."""
    states = {
        day: sensor_state(hass, f"precipitation_{day}")
        for day in ("today", "tomorrow", "aftertomorrow")
    }

    assert {day: state.state for day, state in states.items()} == {
        "today": "light",
        "tomorrow": "moderate",
        "aftertomorrow": "none",
    }
    assert states["today"].entity_id == "sensor.dpc_today_precipitation"
    assert (
        states["aftertomorrow"].entity_id == "sensor.dpc_after_tomorrow_precipitation"
    )
    assert states["today"].attributes["options"] == [
        "none",
        "light",
        "moderate",
        "heavy",
        "very_heavy",
    ]


@pytest.mark.usefixtures("init_integration")
async def test_phenomena_of_each_day(hass: HomeAssistant) -> None:
    """Test the number of phenomena near the place on each day, with its unit."""
    assert {
        day: sensor_state(hass, f"nearby_phenomena_{day}").state
        for day in ("today", "tomorrow", "aftertomorrow")
    } == {"today": "1", "tomorrow": "1", "aftertomorrow": "0"}
    today = sensor_state(hass, "nearby_phenomena_today")
    assert today.entity_id == "sensor.dpc_today_nearby_phenomena"
    assert today.attributes["unit_of_measurement"] == "phenomena"


@pytest.mark.usefixtures("init_integration")
async def test_attributes_of_the_days(hass: HomeAssistant) -> None:
    """Test that the sensors of a day have no attribute but their own."""
    for key in (
        "criticality_today",
        "hydraulic_risk_level_today",
        "precipitation_today",
    ):
        assert set(sensor_state(hass, key).attributes) == {
            "options",
            "device_class",
            "attribution",
            "friendly_name",
        }


async def test_days_shift_at_midnight(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that after midnight tomorrow is today, until the next bulletin."""
    freezer.move_to("2026-11-15 00:10:00+01:00")
    await refresh(hass, init_integration)

    assert sensor_state(hass, "alert_today").state == "orange"
    assert sensor_state(hass, "criticality_today").state == "moderate_hydrogeological"
    assert sensor_state(hass, "alert_tomorrow").state == STATE_UNKNOWN
    assert "risks" not in sensor_state(hass, "alert_tomorrow").attributes
    assert sensor_state(hass, "criticality_tomorrow").state == STATE_UNKNOWN
    assert sensor_state(hass, "hydraulic_risk_level_tomorrow").state == STATE_UNKNOWN
    assert sensor_state(hass, "precipitation_today").state == "moderate"
    assert sensor_state(hass, "precipitation_aftertomorrow").state == STATE_UNKNOWN
    assert sensor_state(hass, "nearby_phenomena_aftertomorrow").state == STATE_UNKNOWN


async def test_levels_unknown_to_aiodpc(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that a level or a text aiodpc does not recognise is an unknown state."""
    coordinator = init_integration.runtime_data
    criticality = coordinator.data.criticality
    vigilance = coordinator.data.vigilance
    assert criticality is not None
    assert vigilance is not None
    unknown_day, *other_days = criticality.bulletin.days
    unknown_risks = {
        risk.type.value: replace(risk, level=AlertLevel.UNKNOWN)
        for risk in unknown_day.risks
    }

    coordinator.async_set_updated_data(
        DpcData(
            criticality=replace(
                criticality,
                bulletin=replace(
                    criticality.bulletin,
                    days=(
                        replace(
                            unknown_day,
                            level=AlertLevel.UNKNOWN,
                            description="Un testo nuovo",
                            **unknown_risks,
                        ),
                        # A criticality whose risk DPC does not name
                        *(replace(day, description="Moderata") for day in other_days),
                    ),
                ),
            ),
            vigilance=replace(
                vigilance,
                bulletin=replace(
                    vigilance.bulletin,
                    days=tuple(
                        replace(day, precipitation=Precipitation.UNKNOWN)
                        for day in vigilance.bulletin.days
                    ),
                ),
            ),
        )
    )
    await hass.async_block_till_done()

    assert sensor_state(hass, "alert_today").state == STATE_UNKNOWN
    assert sensor_state(hass, "criticality_today").state == STATE_UNKNOWN
    assert sensor_state(hass, "criticality_tomorrow").state == STATE_UNKNOWN
    assert sensor_state(hass, "hydraulic_risk_level_today").state == STATE_UNKNOWN
    assert sensor_state(hass, "precipitation_today").state == STATE_UNKNOWN
    # The highest alert of tomorrow is still known
    assert summary_state(hass, "criticality").state == "3"
    assert summary_state(hass, "vigilance").state == STATE_UNKNOWN


async def test_sensors_when_the_days_of_the_bulletin_are_over(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the sensors when DPC has not replaced a bulletin whose days are over."""
    freezer.move_to("2026-11-16 08:00:00+01:00")
    await refresh(hass, init_integration)

    alert = summary_state(hass, "criticality")
    assert alert.state == STATE_UNKNOWN
    assert alert.attributes["total_alerts"] == 0
    assert sensor_state(hass, "alert_today").state == STATE_UNKNOWN
    assert sensor_state(hass, "alert_zone").state == STATE_UNKNOWN
    assert sensor_state(hass, "criticality_valid_until").state == STATE_UNKNOWN
    # The bulletin is still the latest DPC published
    assert sensor_state(hass, "criticality_bulletin").attributes["id"] == CRIT_ID


async def test_sensors_before_any_bulletin(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that the sensors of a bulletin never fetched are unavailable."""
    coordinator = init_integration.runtime_data
    coordinator.async_set_updated_data(
        DpcData(criticality=coordinator.data.criticality, vigilance=None)
    )
    await hass.async_block_till_done()

    for key in (
        "vigilance_zone",
        "vigilance_bulletin",
        "precipitation_today",
        "nearby_phenomena_today",
    ):
        assert sensor_state(hass, key).state == STATE_UNAVAILABLE
    assert summary_state(hass, "vigilance").state == STATE_UNAVAILABLE
    assert sensor_state(hass, "alert_zone").state == "Bacini di Roma"
