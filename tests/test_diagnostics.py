"""Tests for the DPC diagnostics."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from . import CRIT_ID, VIGI_ID

REDACTED = "**REDACTED**"


async def test_diagnostics(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    # Requested after init_integration, so its access token is issued after the
    # clock is moved to the frozen time and does not expire
    hass_client: ClientSessionGenerator,
) -> None:
    """Test that diagnostics include the bulletins and redact the location."""
    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, init_integration
    )

    entry = diagnostics["entry"]
    assert entry["data"]["latitude"] == REDACTED
    assert entry["data"]["longitude"] == REDACTED
    assert entry["unique_id"] == REDACTED

    coordinator = diagnostics["coordinator_data"]
    assert coordinator["coordinator last update success"] is True
    assert coordinator["data"]["criticality"]["bulletin"]["id"] == CRIT_ID
    assert coordinator["data"]["vigilance"]["bulletin"]["id"] == VIGI_ID

    (device,) = diagnostics["devices"]
    assert device["device"]["identifiers"] == REDACTED
    assert len(device["entities"]) == 8
