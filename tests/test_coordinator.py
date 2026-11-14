"""Tests for the coordinator of the DPC bulletins."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from aiodpc import CRITICALITY_PAGE_URL, VIGILANCE_PAGE_URL
from aiodpc.urls import criticality_geojson_url
import aiohttp
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    Platform,
)
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.dpc.const import (
    CONF_MUNICIPALITY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    RETRY_INTERVAL,
)

from . import (
    CRIT_ID,
    NAME,
    binary_sensor_unique_id,
    geojson_requests,
    get_entity_id,
    mock_dpc_responses,
    rome,
    sensor_unique_id,
    setup_integration,
)


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
    await hass.data[DOMAIN][entry.entry_id].async_refresh()
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
) -> None:
    """Test that the bulletins stay while DPC is unreachable, retrying sooner."""
    coordinator = hass.data[DOMAIN][init_integration.entry_id]
    aioclient_mock.clear_requests()
    aioclient_mock.get(CRITICALITY_PAGE_URL, exc=aiohttp.ClientError)
    aioclient_mock.get(VIGILANCE_PAGE_URL, exc=aiohttp.ClientError)

    await update(hass, init_integration)

    assert coordinator.last_update_success
    assert coordinator.update_interval == RETRY_INTERVAL
    assert criticality_attributes(hass)["id"] == CRIT_ID
    assert risk_state(hass, "idrogeologico_domani") == STATE_ON

    aioclient_mock.clear_requests()
    mock_dpc_responses(aioclient_mock)
    await update(hass, init_integration)

    assert coordinator.update_interval == timedelta(minutes=DEFAULT_SCAN_INTERVAL)


@pytest.mark.usefixtures("mock_dpc")
async def test_location_outside_the_alert_zones(hass: HomeAssistant) -> None:
    """Test that the entities are unavailable for a location DPC does not cover."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="48.856600_2.352200",
        data={CONF_NAME: NAME, CONF_LATITUDE: 48.8566, CONF_LONGITUDE: 2.3522},
        options={CONF_MUNICIPALITY: ""},
    )

    await setup_integration(hass, entry)

    unique_id = f"{NAME}_criticality_48.8566_2.3522"
    entity_id = get_entity_id(hass, Platform.SENSOR, unique_id)
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE
