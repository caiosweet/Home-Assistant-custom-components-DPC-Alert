"""Tests for the DPC sensors."""

from __future__ import annotations

from datetime import datetime

from aiodpc import CRITICALITY_PAGE_URL, VIGILANCE_PAGE_URL
from aiodpc.urls import criticality_preview_url, vigilance_preview_url
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import pytest

from custom_components.dpc.const import CONF_WARNING_LEVEL

from . import CRIT_ID, VIGI_ID, get_entity_id, rome, sensor_unique_id


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
    assert attrs["icon"] == "mdi:hazard-lights"


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
