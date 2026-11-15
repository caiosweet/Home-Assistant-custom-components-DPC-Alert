"""Tests for the DPC sensors."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from aiodpc import (
    CRITICALITY_PAGE_URL,
    VIGILANCE_PAGE_URL,
    AlertLevel,
    Precipitation,
)
from aiodpc.urls import criticality_preview_url, vigilance_preview_url
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant, State
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dpc.const import CONF_WARNING_LEVEL
from custom_components.dpc.coordinator import DpcData

from . import CRIT_ID, UNIQUE_ID, VIGI_ID, get_entity_id, rome, sensor_unique_id


def criticality_state(hass: HomeAssistant):
    """Return the state of the criticality sensor."""
    return hass.states.get(
        get_entity_id(hass, Platform.SENSOR, sensor_unique_id("criticality"))
    )


def vigilance_state(hass: HomeAssistant):
    """Return the state of the vigilance sensor."""
    return hass.states.get(
        get_entity_id(hass, Platform.SENSOR, sensor_unique_id("vigilance"))
    )


def day_state(hass: HomeAssistant, key: str) -> State:
    """Return the state of the sensor of a day, e.g. alert_today."""
    state = hass.states.get(get_entity_id(hass, Platform.SENSOR, f"{UNIQUE_ID}-{key}"))
    assert state is not None
    return state


@pytest.mark.usefixtures("init_integration")
async def test_criticality_sensor(hass: HomeAssistant) -> None:
    """Test the criticality sensor of the bulletin issued on 2026-11-14."""
    state = criticality_state(hass)

    # Highest level of the zone: moderate (orange) hydrogeological risk tomorrow
    assert state.state == "3"
    attrs = state.attributes
    assert attrs["integration"] == "dpc"
    assert attrs["id"] == CRIT_ID
    assert attrs["publication_date"] == rome(2026, 11, 14, 14, 30)
    assert datetime.fromisoformat(attrs["last_update"]) == rome(2026, 11, 14, 15)
    assert attrs["link"] == CRITICALITY_PAGE_URL
    assert attrs["zone_name"] == "Bacini di Roma"
    assert attrs["max_level"] == 3
    # Warnings at or above the default level (2, yellow): 2 today, 1 tomorrow
    assert attrs["total_alerts"] == 3

    assert attrs["today"] == {
        "info": "Ordinaria per rischio temporali",
        "alert": "ALLERTA GIALLA",
        "level": 2,
        "image_url": criticality_preview_url(CRIT_ID, 0),
        "expires": rome(2026, 11, 15),
        "zone_name": "Bacini di Roma",
    }
    assert attrs["tomorrow"] == {
        "info": "Moderata per rischio idrogeologico",
        "alert": "ALLERTA ARANCIONE",
        "level": 3,
        "image_url": criticality_preview_url(CRIT_ID, 1),
        "expires": rome(2026, 11, 16),
        "zone_name": "Bacini di Roma",
    }
    assert attrs["events_today"] == [
        {
            "risk": "Temporali",
            "info": "Ordinaria",
            "alert": "ALLERTA GIALLA",
            "level": 2,
            "icon": "mdi:weather-lightning",
        },
        {
            "risk": "Idrogeologico",
            "info": "Ordinaria",
            "alert": "ALLERTA GIALLA",
            "level": 2,
            "icon": "mdi:waves",
        },
    ]
    assert attrs["events_tomorrow"] == [
        {
            "risk": "Idrogeologico",
            "info": "Moderata",
            "alert": "ALLERTA ARANCIONE",
            "level": 3,
            "icon": "mdi:waves",
        },
    ]
    # The icon comes from icons.json, not from the state
    assert "icon" not in attrs


@pytest.mark.usefixtures("init_integration")
async def test_vigilance_sensor(hass: HomeAssistant) -> None:
    """Test the vigilance sensor of the bulletin issued on 2026-11-14."""
    state = vigilance_state(hass)

    assert state.state == "3"
    attrs = state.attributes
    assert attrs["id"] == VIGI_ID
    assert attrs["publication_date"] == rome(2026, 11, 14)
    assert datetime.fromisoformat(attrs["last_update"]) == rome(2026, 11, 14, 15)
    assert attrs["link"] == VIGILANCE_PAGE_URL
    assert attrs["zone_name"] == "Lazio centrale"
    assert attrs["max_level"] == 3
    # Days at or above the default level (2): today and tomorrow
    assert attrs["total_alerts"] == 2
    # Phenomena within the default 50 km radius: one today, one tomorrow
    assert attrs["total_phenomena"] == 2

    today = attrs["today"]
    assert today["level"] == 2
    assert today["precipitation"] == "Deboli"
    assert today["icon"] == "mdi:numeric-2-circle"
    assert today["image_url"] == vigilance_preview_url(VIGI_ID, 0)
    assert len(today["phenomena"]) == 1
    phenomenon = today["phenomena"][0]
    assert phenomenon["id_event"] == 5
    assert phenomenon["event"] == "Precipitazioni"
    assert phenomenon["value"] == "rovesci o temporali a carattere isolato"
    assert phenomenon["icon"] == "mdi:lightning-bolt"
    assert phenomenon["distance"] < 50
    assert phenomenon["direction"] == "SSE"

    assert attrs["tomorrow"]["level"] == 3
    assert attrs["tomorrow"]["precipitation"] == "Moderati"
    assert [p["event"] for p in attrs["tomorrow"]["phenomena"]] == ["Mari"]

    aftertomorrow = attrs["aftertomorrow"]
    assert aftertomorrow["level"] == 1
    assert aftertomorrow["image_url"] is None
    assert aftertomorrow["phenomena"] == []


@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize("entry_options", [{CONF_WARNING_LEVEL: 3}])
async def test_sensors_with_higher_warning_level(hass: HomeAssistant) -> None:
    """Test that only warnings at or above the configured level are counted."""
    criticality = criticality_state(hass)
    assert criticality.state == "3"
    assert criticality.attributes["total_alerts"] == 1
    assert "events_today" not in criticality.attributes
    assert len(criticality.attributes["events_tomorrow"]) == 1

    assert vigilance_state(hass).attributes["total_alerts"] == 1


@pytest.mark.usefixtures("init_integration")
async def test_alert_of_each_day(hass: HomeAssistant) -> None:
    """Test the alert level of today and tomorrow, and the risks at that level."""
    today = day_state(hass, "alert_today")
    assert today.entity_id == "sensor.dpc_alert_today"
    assert today.state == "yellow"
    assert today.attributes["options"] == ["green", "yellow", "orange", "red"]
    assert today.attributes["risks"] == ["thunderstorms", "hydrogeological"]
    assert today.attributes["valid_until"] == rome(2026, 11, 15)

    tomorrow = day_state(hass, "alert_tomorrow")
    assert tomorrow.state == "orange"
    # The yellow thunderstorm risk is below the alert level of the day
    assert tomorrow.attributes["risks"] == ["hydrogeological"]
    assert tomorrow.attributes["valid_until"] == rome(2026, 11, 16)


@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize("entry_options", [{CONF_WARNING_LEVEL: 4}])
async def test_alert_of_a_day_ignores_the_warning_level(hass: HomeAssistant) -> None:
    """Test that the alert of a day is the level of the bulletin, whatever the options."""
    assert day_state(hass, "alert_tomorrow").state == "orange"


@pytest.mark.usefixtures("init_integration")
async def test_precipitation_of_each_day(hass: HomeAssistant) -> None:
    """Test the expected precipitation of the three days of the vigilance bulletin."""
    states = {
        day: day_state(hass, f"precipitation_{day}")
        for day in ("today", "tomorrow", "aftertomorrow")
    }

    assert {day: state.state for day, state in states.items()} == {
        "today": "light",
        "tomorrow": "moderate",
        "aftertomorrow": "none",
    }
    assert states["today"].entity_id == "sensor.dpc_precipitation_today"
    assert states["today"].attributes["options"] == [
        "none",
        "light",
        "moderate",
        "heavy",
        "very_heavy",
    ]
    assert states["aftertomorrow"].attributes["valid_until"] == rome(2026, 11, 17)
    assert "risks" not in states["today"].attributes


async def test_days_shift_at_midnight(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that after midnight tomorrow is today, until the next bulletin."""
    freezer.move_to("2026-11-15 00:10:00+01:00")
    await init_integration.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert day_state(hass, "alert_today").state == "orange"
    assert day_state(hass, "alert_tomorrow").state == STATE_UNKNOWN
    assert "risks" not in day_state(hass, "alert_tomorrow").attributes
    assert day_state(hass, "precipitation_today").state == "moderate"
    assert day_state(hass, "precipitation_aftertomorrow").state == STATE_UNKNOWN
    assert (
        "valid_until" not in day_state(hass, "precipitation_aftertomorrow").attributes
    )


async def test_levels_unknown_to_aiodpc(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that a level aiodpc does not recognise is an unknown state."""
    coordinator = init_integration.runtime_data
    criticality = coordinator.data.criticality
    vigilance = coordinator.data.vigilance
    assert criticality is not None
    assert vigilance is not None

    coordinator.async_set_updated_data(
        DpcData(
            criticality=replace(
                criticality,
                bulletin=replace(
                    criticality.bulletin,
                    days=tuple(
                        replace(day, level=AlertLevel.UNKNOWN)
                        for day in criticality.bulletin.days
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

    assert day_state(hass, "alert_today").state == STATE_UNKNOWN
    assert day_state(hass, "precipitation_today").state == STATE_UNKNOWN
