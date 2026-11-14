"""Tests for the setup of the DPC integration."""

from __future__ import annotations

import aiohttp
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    STATE_UNAVAILABLE,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.dpc.api import CRIT_BULLETIN_URL, VIGI_BULLETIN_URL
from custom_components.dpc.const import CONF_MUNICIPALITY, CONF_WARNING_LEVEL, DOMAIN

from . import (
    LATITUDE,
    LONGITUDE,
    NAME,
    UNIQUE_ID,
    get_entity_id,
    sensor_unique_id,
    setup_integration,
)


async def test_setup_and_unload(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test that the entry sets up 2 sensors and 6 binary sensors, then unloads."""
    entry = init_integration
    assert entry.state is ConfigEntryState.LOADED

    entities = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    platforms = sorted(entity.domain for entity in entities)
    assert platforms == [Platform.BINARY_SENSOR] * 6 + [Platform.SENSOR] * 2

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.parametrize("entry_options", [{"binary_sensor": False}])
async def test_setup_without_binary_sensors(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test that a platform disabled in the options is not set up."""
    entities = er.async_entries_for_config_entry(
        entity_registry, init_integration.entry_id
    )
    assert {entity.domain for entity in entities} == {Platform.SENSOR}


# When no bulletin can be fetched, the integration retries in 10 minutes
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_setup_when_dpc_is_unreachable(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that the entry loads with unavailable entities when DPC is unreachable."""
    aioclient_mock.get(CRIT_BULLETIN_URL, exc=aiohttp.ClientError)
    aioclient_mock.get(VIGI_BULLETIN_URL, exc=aiohttp.ClientError)

    await setup_integration(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED
    state = hass.states.get(
        get_entity_id(hass, Platform.SENSOR, sensor_unique_id("criticality"))
    )
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.usefixtures("mock_dpc")
async def test_migrate_entry_from_version_1(hass: HomeAssistant) -> None:
    """Test that a version 1 entry is migrated to version 2."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id=UNIQUE_ID,
        data={CONF_NAME: NAME, CONF_LATITUDE: LATITUDE, CONF_LONGITUDE: LONGITUDE},
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.version == 2
    assert entry.options[CONF_MUNICIPALITY] == ""


async def test_options_update_reloads_entry(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that changing the options reloads the entry with the new options."""
    entry = init_integration
    coordinator = hass.data[DOMAIN][entry.entry_id]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**entry.options, CONF_WARNING_LEVEL: 3}
    )
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert hass.data[DOMAIN][entry.entry_id] is not coordinator
    state = hass.states.get(
        get_entity_id(hass, Platform.SENSOR, sensor_unique_id("criticality"))
    )
    assert state.attributes["total_alerts"] == 1
