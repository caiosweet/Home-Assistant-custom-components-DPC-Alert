"""Tests for the coordinator of the DPC bulletins."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import patch

from aiodpc import CRITICALITY_PAGE_URL, VIGILANCE_PAGE_URL, CriticalityMap
from aiodpc.urls import criticality_geojson_url
import aiohttp
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    STATE_ON,
    STATE_UNKNOWN,
    Platform,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.dpc.const import (
    CONF_MUNICIPALITY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LATEST_ID_CHECK_INTERVAL,
    RETRY_INTERVAL,
)

from . import (
    CRIT_ID,
    LATITUDE,
    LONGITUDE,
    binary_sensor_unique_id,
    geojson_requests,
    get_entity_id,
    mock_dpc_responses,
    rome,
    sensor_unique_id,
    setup_integration,
)


# Past the minute during which the places share the latest bulletin IDs
LATER = timedelta(seconds=LATEST_ID_CHECK_INTERVAL + 1)
MILAN = (45.46, 9.19)


def place_entry(latitude: float, longitude: float) -> MockConfigEntry:
    """Return the config entry of another place."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"{latitude} {longitude}",
        version=2,
        unique_id=f"{latitude:.6f}_{longitude:.6f}",
        data={
            CONF_NAME: f"{latitude} {longitude}",
            CONF_LATITUDE: latitude,
            CONF_LONGITUDE: longitude,
        },
        options={CONF_MUNICIPALITY: ""},
    )


def criticality_state(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    """Return the state of the criticality sensor of an entry."""
    unique_id = (
        f"{entry.data[CONF_NAME]}_criticality_"
        f"{entry.data[CONF_LATITUDE]}_{entry.data[CONF_LONGITUDE]}"
    )
    return hass.states.get(get_entity_id(hass, Platform.SENSOR, unique_id)).state


def criticality_attributes(hass: HomeAssistant) -> dict[str, Any]:
    """Return the attributes of the criticality sensor."""
    entity_id = get_entity_id(hass, Platform.SENSOR, sensor_unique_id("criticality"))
    return hass.states.get(entity_id).attributes


def risk_state(hass: HomeAssistant, kind: str) -> str:
    """Return the state of the binary sensor of a risk kind."""
    entity_id = get_entity_id(
        hass, Platform.BINARY_SENSOR, binary_sensor_unique_id(kind)
    )
    return hass.states.get(entity_id).state


async def update(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Update the bulletins of an entry, as its update interval does."""
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


# The criticality bulletin covers "fino alle 24.00 del giorno di emissione (oggi) e
# nelle 24 ore del giorno seguente (domani)" (pcm-dpc/DPC-Bollettini-Criticita-
# Idrogeologica-Idraulica), so each day expires at the midnight that ends it.


@pytest.mark.usefixtures("init_integration")
async def test_expires_on_publication_day(hass: HomeAssistant) -> None:
    """Test the expiration of the bulletin issued on 2026-11-14 on that day."""
    attributes = criticality_attributes(hass)

    assert attributes["today"]["expires"] == rome(2026, 11, 15)
    assert attributes["tomorrow"]["expires"] == rome(2026, 11, 16)


async def test_tomorrow_becomes_today_at_midnight(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that tomorrow moves to today at midnight and keeps its expiration."""
    tomorrow = criticality_attributes(hass)["tomorrow"]
    downloaded = geojson_requests(aioclient_mock)

    freezer.move_to("2026-11-15 00:10:00+01:00")
    await update(hass, init_integration)

    attributes = criticality_attributes(hass)
    assert attributes["today"] == tomorrow
    assert attributes["today"]["expires"] == rome(2026, 11, 16)
    assert "tomorrow" not in attributes
    assert risk_state(hass, "idrogeologico_oggi") == STATE_ON
    assert risk_state(hass, "idrogeologico_domani") == STATE_UNKNOWN
    # The bulletin did not change, so it is not downloaded again
    assert geojson_requests(aioclient_mock) == downloaded


async def test_start_before_the_new_bulletin(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a start in the morning, when the latest bulletin is from yesterday."""
    freezer.move_to("2026-11-15 08:00:00+01:00")
    mock_dpc_responses(aioclient_mock)

    await setup_integration(hass, mock_config_entry)

    # Yesterday's assessment is over, so it is not downloaded
    assert criticality_geojson_url(CRIT_ID, 0) not in geojson_requests(aioclient_mock)
    attributes = criticality_attributes(hass)
    assert attributes["today"]["expires"] == rome(2026, 11, 16)
    assert "tomorrow" not in attributes


async def test_next_bulletin_replaces_the_previous_one(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that the next day's bulletin replaces the previous one."""
    aioclient_mock.clear_requests()
    mock_dpc_responses(aioclient_mock, crit_id="20261115_1500", vigi_id="20261115")
    freezer.move_to("2026-11-15 15:30:00+01:00")

    await update(hass, init_integration)

    attributes = criticality_attributes(hass)
    assert attributes["id"] == "20261115_1500"
    assert attributes["today"]["expires"] == rome(2026, 11, 16)
    assert attributes["tomorrow"]["expires"] == rome(2026, 11, 17)


async def test_bulletins_are_kept_when_dpc_is_unreachable(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that the bulletins stay while DPC is unreachable, retrying sooner."""
    coordinator = init_integration.runtime_data
    aioclient_mock.clear_requests()
    aioclient_mock.get(CRITICALITY_PAGE_URL, exc=aiohttp.ClientError)
    aioclient_mock.get(VIGILANCE_PAGE_URL, exc=aiohttp.ClientError)
    freezer.tick(LATER)

    await update(hass, init_integration)

    assert coordinator.last_update_success
    assert coordinator.update_interval == RETRY_INTERVAL
    assert criticality_attributes(hass)["id"] == CRIT_ID
    assert risk_state(hass, "idrogeologico_domani") == STATE_ON

    aioclient_mock.clear_requests()
    mock_dpc_responses(aioclient_mock)
    freezer.tick(LATER)
    await update(hass, init_integration)

    assert coordinator.update_interval == timedelta(minutes=DEFAULT_SCAN_INTERVAL)


async def test_places_share_the_downloads(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_dpc: AiohttpClientMocker,
) -> None:
    """Test that the bulletins are downloaded once for every place."""
    milan = place_entry(*MILAN)
    mock_config_entry.add_to_hass(hass)
    milan.add_to_hass(hass)

    # As at startup, every place is set up at the same time
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    downloads = geojson_requests(mock_dpc)
    assert len(downloads) == len(set(downloads)) == 8  # 2 criticality, 6 vigilance
    pages = [url for _, url, _, _ in mock_dpc.mock_calls if "mappe" in str(url)]
    assert len(pages) == 2  # one check of each bulletin, shared by the places
    assert criticality_state(hass, mock_config_entry) == "3"
    assert criticality_state(hass, milan) == "4"


async def test_place_added_later(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_dpc: AiohttpClientMocker,
) -> None:
    """Test that a new place is read with one more download, alone."""
    downloads = len(geojson_requests(mock_dpc))
    milan = place_entry(*MILAN)

    await setup_integration(hass, milan)
    await update(hass, init_integration)

    assert len(geojson_requests(mock_dpc)) == 2 * downloads
    assert criticality_state(hass, milan) == "4"
    assert criticality_state(hass, init_integration) == "3"


async def test_place_outside_alone(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_dpc: AiohttpClientMocker,
) -> None:
    """Test that a place outside every zone does not affect the others."""
    paris = place_entry(48.8566, 2.3522)
    paris.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(paris.entry_id)
    await update(hass, init_integration)

    assert paris.state is ConfigEntryState.SETUP_ERROR
    assert criticality_state(hass, init_integration) == "3"


async def test_place_removed(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_dpc: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that a removed place is no longer read."""
    milan = place_entry(*MILAN)
    await setup_integration(hass, milan)
    assert await hass.config_entries.async_unload(milan.entry_id)
    await hass.async_block_till_done()

    mock_dpc.clear_requests()
    mock_dpc_responses(mock_dpc, crit_id="20261115_1500", vigi_id="20261115")
    freezer.move_to("2026-11-15 15:30:00+01:00")
    with patch.object(
        CriticalityMap, "at", autospec=True, wraps=CriticalityMap.at
    ) as at:
        await update(hass, init_integration)

    assert criticality_attributes(hass)["id"] == "20261115_1500"
    assert [call.args[1].coordinates for call in at.call_args_list] == [
        (LATITUDE, LONGITUDE)
    ]
