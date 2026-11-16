"""Tests for the DPC binary sensors."""

from __future__ import annotations

from aiodpc import ATTRIBUTION
from homeassistant.const import STATE_OFF, STATE_ON, Platform
from homeassistant.core import HomeAssistant
import pytest

from custom_components.dpc.const import CONF_WARNING_LEVEL

from . import RISK_KINDS, binary_sensor_unique_id, get_entity_id


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
async def test_binary_sensor_attributes(hass: HomeAssistant) -> None:
    """Test that a binary sensor has no attribute of the bulletin.

    Its level, criticality, zone and bulletin are entities of their own.
    """
    state = hass.states.get(
        get_entity_id(
            hass, Platform.BINARY_SENSOR, binary_sensor_unique_id("temporali_oggi")
        )
    )

    assert state.entity_id == "binary_sensor.dpc_today_thunderstorm_risk"
    assert dict(state.attributes) == {
        "device_class": "safety",
        "attribution": ATTRIBUTION,
        "friendly_name": "DPC · Today Thunderstorm risk",
    }


@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize("entry_options", [{CONF_WARNING_LEVEL: 3}])
async def test_binary_sensors_with_higher_warning_level(hass: HomeAssistant) -> None:
    """Test that the configured warning level is the threshold."""
    states = risk_states(hass)
    assert [kind for kind, state in states.items() if state == STATE_ON] == [
        "idrogeologico_domani"
    ]
