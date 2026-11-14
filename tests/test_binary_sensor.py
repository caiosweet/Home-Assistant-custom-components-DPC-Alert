"""Tests for the DPC binary sensors."""

from __future__ import annotations

from datetime import datetime

from homeassistant.const import STATE_OFF, STATE_ON, Platform
from homeassistant.core import HomeAssistant
import pytest

from custom_components.dpc.api import CRIT_BULLETIN_URL, CRIT_IMAGE_URL
from custom_components.dpc.const import CONF_WARNING_LEVEL

from . import CRIT_ID, RISK_KINDS, binary_sensor_unique_id, get_entity_id


def risk_states(hass: HomeAssistant) -> dict[str, str]:
    """Return the state of the binary sensor of each risk kind."""
    return {
        kind: hass.states.get(
            get_entity_id(hass, Platform.BINARY_SENSOR, binary_sensor_unique_id(kind))
        ).state
        for kind in RISK_KINDS
    }


@pytest.mark.usefixtures("init_integration")
async def test_binary_sensor_states(hass: HomeAssistant) -> None:
    """Test that the risks at or above the default level (2, yellow) are on."""
    assert risk_states(hass) == {
        "idraulico_oggi": STATE_OFF,
        "temporali_oggi": STATE_ON,
        "idrogeologico_oggi": STATE_ON,
        "idraulico_domani": STATE_OFF,
        "temporali_domani": STATE_OFF,
        "idrogeologico_domani": STATE_ON,
    }


@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        (
            "temporali_oggi",
            {
                "risk": "Temporali",
                "info": "Ordinaria",
                "alert": "ALLERTA GIALLA",
                "level": 2,
                "image_url": CRIT_IMAGE_URL.format(CRIT_ID, "oggi"),
                # Today's assessment is valid until 24:00 of the issue day
                "expires": datetime(2026, 11, 15),
            },
        ),
        (
            "idrogeologico_domani",
            {
                "risk": "Idrogeologico",
                "info": "Moderata",
                "alert": "ALLERTA ARANCIONE",
                "level": 3,
                "image_url": CRIT_IMAGE_URL.format(CRIT_ID, "domani"),
                # Tomorrow's assessment covers the 24 hours of the following day
                "expires": datetime(2026, 11, 16),
            },
        ),
    ],
)
async def test_binary_sensor_attributes(
    hass: HomeAssistant, kind: str, expected: dict
) -> None:
    """Test the attributes of a binary sensor."""
    state = hass.states.get(
        get_entity_id(hass, Platform.BINARY_SENSOR, binary_sensor_unique_id(kind))
    )

    attrs = state.attributes
    assert {key: attrs[key] for key in expected} == expected
    assert attrs["id"] == CRIT_ID
    assert attrs["publication_date"] == datetime(2026, 11, 14, 14, 30)
    assert attrs["zone_name"] == "Bacini di Roma"
    assert attrs["link"] == CRIT_BULLETIN_URL
    assert attrs["device_class"] == "safety"


@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize("entry_options", [{CONF_WARNING_LEVEL: 3}])
async def test_binary_sensors_with_higher_warning_level(hass: HomeAssistant) -> None:
    """Test that the configured warning level is the threshold."""
    states = risk_states(hass)
    assert [kind for kind, state in states.items() if state == STATE_ON] == [
        "idrogeologico_domani"
    ]
