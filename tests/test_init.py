"""Tests for the setup of the DPC integration."""

from __future__ import annotations

from aiodpc import CRITICALITY_PAGE_URL, VIGILANCE_PAGE_URL
import aiohttp
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    STATE_UNAVAILABLE,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.dpc.const import CONF_MUNICIPALITY, CONF_WARNING_LEVEL, DOMAIN

from . import (
    LATITUDE,
    LONGITUDE,
    NAME,
    PUBLICATION_DAY,
    UNIQUE_ID,
    get_entity_id,
    mock_dpc_responses,
    sensor_unique_id,
    setup_integration,
)


async def test_setup_and_unload(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test that the entry sets up its entities, then unloads.

    6 binary sensors, the alert and vigilance sensors with the 5 sensors of
    their days, 4 maps, and the 2 phenomena near Rome in the bulletin.
    """
    entry = init_integration
    assert entry.state is ConfigEntryState.LOADED

    entities = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    platforms = sorted(entity.domain for entity in entities)
    assert platforms == (
        [Platform.BINARY_SENSOR] * 6
        + [Platform.GEO_LOCATION] * 2
        + [Platform.IMAGE] * 4
        + [Platform.SENSOR] * 7
    )

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED


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
    assert {entity.domain for entity in entities} == {
        Platform.SENSOR,
        Platform.IMAGE,
        Platform.GEO_LOCATION,
    }


async def test_setup_when_dpc_is_unreachable(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that the setup is retried soon while DPC is unreachable."""
    aioclient_mock.get(CRITICALITY_PAGE_URL, exc=aiohttp.ClientError)
    aioclient_mock.get(VIGILANCE_PAGE_URL, exc=aiohttp.ClientError)
    mock_config_entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.parametrize(
    ("unreachable_page", "unavailable", "available"),
    [
        (CRITICALITY_PAGE_URL, "criticality", "vigilance"),
        (VIGILANCE_PAGE_URL, "vigilance", "criticality"),
    ],
)
async def test_setup_with_one_bulletin(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
    unreachable_page: str,
    unavailable: str,
    available: str,
) -> None:
    """Test a place set up with one bulletin while the other is unreachable."""
    freezer.move_to(PUBLICATION_DAY)
    # The first route registered for a URL answers it
    aioclient_mock.get(unreachable_page, exc=aiohttp.ClientError)
    mock_dpc_responses(aioclient_mock)

    await setup_integration(hass, mock_config_entry)

    def sensor_state(bulletin: str) -> str:
        entity_id = get_entity_id(hass, Platform.SENSOR, sensor_unique_id(bulletin))
        return hass.states.get(entity_id).state

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert sensor_state(unavailable) == STATE_UNAVAILABLE
    assert sensor_state(available) == "3"
    # Home Assistant reads an entity only while it is available, but the
    # unavailable one would still answer without a bulletin
    entity = hass.data[Platform.SENSOR].get_entity(
        get_entity_id(hass, Platform.SENSOR, sensor_unique_id(unavailable))
    )
    assert entity.native_value is None
    assert "id" not in entity.extra_state_attributes


@pytest.mark.usefixtures("mock_dpc")
async def test_setup_of_a_place_outside_the_alert_zones(hass: HomeAssistant) -> None:
    """Test that a place DPC does not cover fails to set up, without retrying."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="48.856600_2.352200",
        data={CONF_NAME: NAME, CONF_LATITUDE: 48.8566, CONF_LONGITUDE: 2.3522},
        options={CONF_MUNICIPALITY: ""},
    )
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert "not inside any DPC alert zone" in entry.reason


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
    coordinator = entry.runtime_data

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {**entry.options, CONF_MUNICIPALITY: "Roma", CONF_WARNING_LEVEL: 3},
    )
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not coordinator
    state = hass.states.get(
        get_entity_id(hass, Platform.SENSOR, sensor_unique_id("criticality"))
    )
    assert state.attributes["total_alerts"] == 1


@pytest.mark.parametrize(
    ("name", "municipality", "device_name", "place"),
    [
        # Since 2026.11, a place is named after its alert zone
        ("Bacini di Roma", "Roma", "Roma", "dpc_roma"),
        # Before, it had any name and no municipality, or the name DPC
        ("Casa", "", "Casa", "dpc_casa"),
        ("DPC", "Portula", "Portula", "dpc_portula"),
        ("DPC", "", "DPC", "dpc"),
    ],
)
async def test_device_and_entity_ids_of_a_place(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_dpc: AiohttpClientMocker,
    name: str,
    municipality: str,
    device_name: str,
    place: str,
) -> None:
    """Test that a place names its device after its municipality, or itself.

    Its entity IDs are dpc_<municipality>_<kind>, or dpc_<name>_<kind> without one.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        title=name,
        unique_id=UNIQUE_ID,
        data={CONF_NAME: name, CONF_LATITUDE: LATITUDE, CONF_LONGITUDE: LONGITUDE},
        options={CONF_MUNICIPALITY: municipality},
    )

    await setup_integration(hass, entry)

    (device,) = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    assert device.name == device_name
    entity_ids = {
        item.entity_id
        for item in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    }
    assert {
        f"sensor.{place}_alert",
        f"sensor.{place}_vigilance",
        f"binary_sensor.{place}_idraulico_oggi",
    } <= entity_ids


async def test_places_with_the_same_name(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_dpc: AiohttpClientMocker,
) -> None:
    """Test two places of the same name, possible since 2026.2.0: no conflict."""
    entries = [
        MockConfigEntry(
            domain=DOMAIN,
            version=2,
            title=NAME,
            unique_id=f"{latitude:.6f}_{longitude:.6f}",
            data={CONF_NAME: NAME, CONF_LATITUDE: latitude, CONF_LONGITUDE: longitude},
            options={CONF_MUNICIPALITY: ""},
        )
        for latitude, longitude in ((LATITUDE, LONGITUDE), (45.46, 9.19))
    ]
    for entry in entries:
        await setup_integration(hass, entry)

    entity_ids = [
        {
            item.entity_id
            for item in er.async_entries_for_config_entry(
                entity_registry, entry.entry_id
            )
        }
        for entry in entries
    ]
    # Milan has no phenomenon within 50 km in the bulletin, Rome has 2
    assert [len(ids) for ids in entity_ids] == [19, 17]
    assert not entity_ids[0] & entity_ids[1]
    assert "sensor.dpc_alert_2" in entity_ids[1]
