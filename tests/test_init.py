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

from custom_components.dpc.const import (
    CONF_DAYS,
    CONF_MUNICIPALITY,
    CONF_WARNING_LEVEL,
    DOMAIN,
)

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

    With the three days: 6 binary sensors, 2 phenomena near Rome in the
    bulletin, 4 maps, and 24 sensors: 8 of the place and 16 of the days.
    """
    entry = init_integration
    assert entry.state is ConfigEntryState.LOADED

    entities = er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    platforms = sorted(entity.domain for entity in entities)
    assert platforms == (
        [Platform.BINARY_SENSOR] * 6
        + [Platform.GEO_LOCATION] * 2
        + [Platform.IMAGE] * 4
        + [Platform.SENSOR] * 24
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
    """Test that a version 1 entry goes through every migration, to 2.2."""
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
    assert (entry.version, entry.minor_version) == (2, 2)
    assert entry.options == {CONF_MUNICIPALITY: "", CONF_DAYS: ["today", "tomorrow"]}


@pytest.mark.usefixtures("mock_dpc")
async def test_migrate_entry_to_the_days(hass: HomeAssistant) -> None:
    """Test that a place of 2026.11.0 keeps its options and gets today and tomorrow.

    Those are the days of its binary sensors.
    """
    options = {CONF_MUNICIPALITY: "Roma", CONF_WARNING_LEVEL: 3, "image": False}
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id=UNIQUE_ID,
        data={CONF_NAME: NAME, CONF_LATITUDE: LATITUDE, CONF_LONGITUDE: LONGITUDE},
        options=options,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert (entry.version, entry.minor_version) == (2, 2)
    assert entry.options == {**options, CONF_DAYS: ["today", "tomorrow"]}


@pytest.mark.usefixtures("mock_dpc")
async def test_migrate_entry_of_a_beta_with_the_day_after_tomorrow(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Test that a place of the betas of 2026.11.1 keeps the day after tomorrow.

    The betas had the precipitation of the day after tomorrow.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id=UNIQUE_ID,
        data={CONF_NAME: NAME, CONF_LATITUDE: LATITUDE, CONF_LONGITUDE: LONGITUDE},
        options={CONF_MUNICIPALITY: ""},
    )
    entry.add_to_hass(hass)
    entity_registry.async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        f"{UNIQUE_ID}-precipitation_aftertomorrow",
        config_entry=entry,
    )

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.options[CONF_DAYS] == ["today", "tomorrow", "aftertomorrow"]


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
        # Every ID starts with dpc, once
        ("DPC", "", "DPC", "dpc"),
        ("DPC Casa", "", "DPC Casa", "dpc_casa"),
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
    """Test that a place names its devices after its municipality, or itself.

    The entity IDs are made of the place, the day and the key of the entity,
    in English whatever the language: dpc_<place>[_<day>]_<key>.
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

    devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    assert sorted(device.name for device in devices) == [
        device_name,
        f"{device_name} · Today",
        f"{device_name} · Tomorrow",
    ]
    entity_ids = {
        item.entity_id
        for item in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
    }
    assert {
        f"sensor.{place}_highest_alert",
        f"sensor.{place}_highest_precipitation",
        f"sensor.{place}_today_alert",
        f"sensor.{place}_tomorrow_alert",
        f"binary_sensor.{place}_today_hydraulic_risk",
        f"image.{place}_today_criticality_map",
        f"geo_location.{place}_today_isolated_thunderstorms_sse",
    } <= entity_ids


@pytest.mark.usefixtures("init_integration")
async def test_devices_of_the_days(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test a device for each day the place shows, part of the device of the place."""
    devices = dr.async_entries_for_config_entry(
        device_registry, mock_config_entry.entry_id
    )
    (place,) = (device for device in devices if device.via_device_id is None)
    days = {
        device.name: device for device in devices if device.via_device_id == place.id
    }
    assert place.name == "DPC"
    assert days.keys() == {
        "DPC · Today",
        "DPC · Tomorrow",
        "DPC · Day after tomorrow",
    }

    today = days["DPC · Today"]
    assert today.identifiers == {(DOMAIN, f"{UNIQUE_ID}-today")}
    assert today.entry_type is dr.DeviceEntryType.SERVICE
    assert today.configuration_url == CRITICALITY_PAGE_URL
    # Only the vigilance bulletin covers the day after tomorrow
    after_tomorrow = days["DPC · Day after tomorrow"]
    assert after_tomorrow.configuration_url == VIGILANCE_PAGE_URL

    def entity_ids(device: dr.DeviceEntry) -> set[str]:
        return {
            item.entity_id
            for item in er.async_entries_for_device(entity_registry, device.id)
        }

    assert entity_ids(place) == {
        "sensor.dpc_highest_alert",
        "sensor.dpc_highest_precipitation",
        "sensor.dpc_alert_zone",
        "sensor.dpc_vigilance_zone",
        "sensor.dpc_criticality_bulletin",
        "sensor.dpc_vigilance_bulletin",
        "sensor.dpc_criticality_valid_until",
        "sensor.dpc_vigilance_valid_until",
    }
    assert entity_ids(today) == {
        "binary_sensor.dpc_today_hydraulic_risk",
        "binary_sensor.dpc_today_thunderstorm_risk",
        "binary_sensor.dpc_today_hydrogeological_risk",
        "sensor.dpc_today_alert",
        "sensor.dpc_today_criticality",
        "sensor.dpc_today_hydraulic_risk_level",
        "sensor.dpc_today_thunderstorm_risk_level",
        "sensor.dpc_today_hydrogeological_risk_level",
        "sensor.dpc_today_precipitation",
        "sensor.dpc_today_nearby_phenomena",
        "image.dpc_today_criticality_map",
        "image.dpc_today_vigilance_map",
        "geo_location.dpc_today_isolated_thunderstorms_sse",
    }
    # Only the vigilance bulletin covers the day after tomorrow
    assert entity_ids(after_tomorrow) == {
        "sensor.dpc_after_tomorrow_precipitation",
        "sensor.dpc_after_tomorrow_nearby_phenomena",
    }


async def test_days_no_longer_shown_are_removed(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test that a day taken out of the options goes, with its entities."""
    entry = init_integration
    tomorrow = entity_registry.async_get("sensor.dpc_tomorrow_alert")
    assert tomorrow is not None

    hass.config_entries.async_update_entry(
        entry, options={**entry.options, CONF_DAYS: ["today"]}
    )
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert sorted(
        device.name
        for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    ) == ["DPC", "DPC · Today"]
    assert entity_registry.async_get(tomorrow.entity_id) is None
    assert hass.states.get(tomorrow.entity_id) is None
    assert hass.states.get("sensor.dpc_today_alert") is not None


async def test_days_follow_the_name_of_the_place(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test that renaming the place renames its days, and the IDs to recreate."""
    entry = init_integration
    devices = {
        device.name: device
        for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    }

    device_registry.async_update_device(devices["DPC"].id, name_by_user="Casa")
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    today = device_registry.async_get(devices["DPC · Today"].id)
    assert today is not None
    assert today.name == "Casa · Today"
    # The entities keep their IDs; Recreate entity IDs proposes the new ones
    registered = entity_registry.async_get("binary_sensor.dpc_today_hydraulic_risk")
    assert registered is not None
    assert (
        entity_registry.async_regenerate_entity_id(registered)
        == "binary_sensor.dpc_casa_today_hydraulic_risk"
    )


async def test_entity_ids_registered_before_are_kept(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    mock_dpc: AiohttpClientMocker,
) -> None:
    """Test that an entity keeps its ID, and that recreating it gives the new one."""
    mock_config_entry.add_to_hass(hass)
    old = entity_registry.async_get_or_create(
        Platform.BINARY_SENSOR,
        DOMAIN,
        f"{UNIQUE_ID}-idraulico_oggi",
        suggested_object_id="dpc_idraulico_oggi",
        config_entry=mock_config_entry,
    )

    await setup_integration(hass, mock_config_entry)

    entry = entity_registry.async_get(old.entity_id)
    assert entry is not None
    assert entry.entity_id == "binary_sensor.dpc_idraulico_oggi"
    # What Settings → Entities → Recreate entity IDs proposes
    assert (
        entity_registry.async_regenerate_entity_id(entry)
        == "binary_sensor.dpc_today_hydraulic_risk"
    )


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
    # Today and tomorrow, the days of the places of 2026.11.0. Milan has no
    # phenomenon within 50 km in the bulletin, Rome has 2
    assert [len(ids) for ids in entity_ids] == [34, 32]
    assert not entity_ids[0] & entity_ids[1]
    assert "sensor.dpc_today_alert_2" in entity_ids[1]
