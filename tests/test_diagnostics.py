"""Tests for the DPC diagnostics."""

from __future__ import annotations

import json

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.dpc.const import DOMAIN

from . import CRIT_ID, VIGI_ID, binary_sensor_unique_id, setup_integration

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
    assert len(device["entities"]) == 19


async def test_diagnostics_hide_where_the_place_is(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    mock_dpc: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
) -> None:
    """Test that nothing in the diagnostics reveals the place.

    Neither the positions of the phenomena near it, nor an entity ID made of
    its coordinates, as 2026.2.0 named the binary sensors.
    """
    mock_config_entry.add_to_hass(hass)
    entity_registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        binary_sensor_unique_id("idraulico_oggi"),
        suggested_object_id="41_900000_12_500000_idraulico_oggi",
        config_entry=mock_config_entry,
    )
    await setup_integration(hass, mock_config_entry)

    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, mock_config_entry
    )

    text = json.dumps(diagnostics)
    assert "41_900000" not in text
    assert "41.9" not in text
    # The first phenomenon of the fixtures is at 41.57, 12.67
    assert "41.57" not in text
    (phenomenon, *_) = diagnostics["coordinator_data"]["data"]["vigilance"]["bulletin"][
        "days"
    ][0]["phenomena"]
    assert phenomenon["latitude"] == phenomenon["longitude"] == REDACTED
    assert phenomenon["distance_km"] == phenomenon["direction"] == REDACTED
    for entity in diagnostics["devices"][0]["entities"]:
        if entity["entry"]["domain"] == "geo_location":
            assert entity["state"]["state"] == REDACTED
            assert entity["state"]["attributes"]["direction"] == REDACTED
