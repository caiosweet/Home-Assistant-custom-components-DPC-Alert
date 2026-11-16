"""Tests for the maps of the DPC bulletins."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from http import HTTPStatus
from unittest.mock import patch

from aiodpc import DpcConnectionError
from aiodpc.urls import criticality_preview_url, vigilance_preview_url
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.image import ImageEntity
from homeassistant.const import STATE_UNAVAILABLE, Platform
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.dpc.bulletins import async_get_bulletins
from custom_components.dpc.const import (
    CONF_DAYS,
    LATEST_ID_CHECK_INTERVAL,
    PREVIEWS_KEPT,
)

from . import (
    BLANK_MAP,
    CRIT_ID,
    MAP,
    UNIQUE_ID,
    VIGI_ID,
    get_entity_id,
    mock_dpc_responses,
    setup_integration,
)

TODAY_MAP = criticality_preview_url(CRIT_ID, 0)
# Past the minute during which the places share a check of a blank map
LATER = timedelta(seconds=LATEST_ID_CHECK_INTERVAL + 1)


def map_entity(hass: HomeAssistant, key: str) -> ImageEntity:
    """Return the image entity of a map, e.g. criticality_map_today."""
    entity_id = get_entity_id(hass, Platform.IMAGE, f"{UNIQUE_ID}-{key}")
    entity = hass.data[Platform.IMAGE].get_entity(entity_id)
    assert isinstance(entity, ImageEntity)
    return entity


def map_state(
    hass: HomeAssistant, entity_id: str = "image.dpc_today_criticality_map"
) -> str:
    """Return the state of a map: when it was downloaded, or unavailable."""
    state = hass.states.get(entity_id)
    assert state is not None
    return state.state


def map_requests(aioclient_mock: AiohttpClientMocker, url: str = TODAY_MAP) -> int:
    """Return how many times a map was downloaded."""
    return sum(
        str(requested) == url for _, requested, _, _ in aioclient_mock.mock_calls
    )


def serve_map(aioclient_mock: AiohttpClientMocker, image: bytes | None) -> None:
    """Serve the bulletins with the map of today, or without it (not found)."""
    aioclient_mock.clear_requests()
    if image is None:
        aioclient_mock.get(TODAY_MAP, status=HTTPStatus.NOT_FOUND)
    else:
        aioclient_mock.get(TODAY_MAP, content=image)
    mock_dpc_responses(aioclient_mock)


async def update(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Update the place, as at its next scan."""
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


@pytest.mark.usefixtures("init_integration")
async def test_maps_of_the_days(hass: HomeAssistant) -> None:
    """Test that each map points to the preview of its bulletin and day."""
    assert {
        key: map_entity(hass, key).image_url
        for key in (
            "criticality_map_today",
            "criticality_map_tomorrow",
            "vigilance_map_today",
            "vigilance_map_tomorrow",
        )
    } == {
        "criticality_map_today": criticality_preview_url(CRIT_ID, 0),
        "criticality_map_tomorrow": criticality_preview_url(CRIT_ID, 1),
        "vigilance_map_today": vigilance_preview_url(VIGI_ID, 0),
        "vigilance_map_tomorrow": vigilance_preview_url(VIGI_ID, 1),
    }
    today = hass.states.get("image.dpc_today_criticality_map")
    assert today is not None
    # The state is when the map shown was downloaded: at the setup
    assert today.state == "2026-11-14T14:00:00+00:00"
    # The map at DPC, for cards that link to it
    assert today.attributes["image_url"] == criticality_preview_url(CRIT_ID, 0)


async def test_map_is_downloaded_once(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_dpc: AiohttpClientMocker,
    # Requested after init_integration, so its access token is issued after the
    # clock is moved to the frozen time and does not expire
    hass_client: ClientSessionGenerator,
) -> None:
    """Test that Home Assistant serves the map downloaded from DPC, kept."""
    client = await hass_client()

    for _ in range(2):
        response = await client.get("/api/image_proxy/image.dpc_today_criticality_map")
        assert response.status == HTTPStatus.OK
        assert response.content_type == "image/png"
        assert await response.read() == MAP
    await update(hass, init_integration)

    # Downloaded at the setup, and kept until it changes
    assert map_requests(mock_dpc) == 1


async def test_blank_map_is_unavailable_until_dpc_replaces_it(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that a map DPC published blank is not shown, and checked again."""
    freezer.move_to("2026-11-14 15:00:00+01:00")
    serve_map(aioclient_mock, BLANK_MAP)
    await setup_integration(hass, mock_config_entry)

    assert map_state(hass) == STATE_UNAVAILABLE
    assert await map_entity(hass, "criticality_map_today").async_image() is None
    # The other maps are shown
    assert map_state(hass, "image.dpc_tomorrow_criticality_map") != STATE_UNAVAILABLE

    # Within the minute, the places share the check: not downloaded again
    await update(hass, mock_config_entry)
    assert map_requests(aioclient_mock) == 1

    # DPC replaces it at the same address
    serve_map(aioclient_mock, MAP)
    freezer.tick(LATER)
    await update(hass, mock_config_entry)

    assert map_state(hass) == "2026-11-14T14:01:01+00:00"
    assert await map_entity(hass, "criticality_map_today").async_image() == MAP


async def test_map_that_cannot_be_downloaded(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that a map that cannot be downloaded is not shown, and tried again."""
    freezer.move_to("2026-11-14 15:00:00+01:00")
    serve_map(aioclient_mock, None)
    await setup_integration(hass, mock_config_entry)

    assert map_state(hass) == STATE_UNAVAILABLE

    serve_map(aioclient_mock, MAP)
    await update(hass, mock_config_entry)

    assert map_state(hass) != STATE_UNAVAILABLE


async def test_map_changes_at_midnight(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_dpc: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that after midnight the map of today is the second day of the bulletin."""
    today = map_entity(hass, "criticality_map_today")

    freezer.move_to("2026-11-15 00:10:00+01:00")
    await update(hass, init_integration)

    assert today.image_url == criticality_preview_url(CRIT_ID, 1)
    assert await today.async_image() == MAP
    assert map_state(hass) == "2026-11-14T23:10:00+00:00"
    # Until the next bulletin there is no map of tomorrow: unavailable, without
    # the access token the frontend would request a broken image with
    assert map_entity(hass, "criticality_map_tomorrow").image_url is None
    tomorrow = hass.states.get("image.dpc_tomorrow_criticality_map")
    assert tomorrow is not None
    assert tomorrow.state == STATE_UNAVAILABLE
    assert "access_token" not in tomorrow.attributes
    assert "image_url" not in tomorrow.attributes


async def test_download_of_a_previous_map_is_cancelled(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that a map still being downloaded when the day changes is not shown."""
    today = map_entity(hass, "criticality_map_today")
    started, release = asyncio.Event(), asyncio.Event()
    downloads: list[str] = []

    async def slow_preview(url: str) -> bytes:
        downloads.append(url)
        started.set()
        await release.wait()
        return MAP

    # As a blank map: downloaded again at the next update
    today._cached_image = None
    with patch.object(async_get_bulletins(hass), "preview", slow_preview):
        await init_integration.runtime_data.async_refresh()
        await started.wait()
        previous = today._download
        # An update while it is downloaded does not download it again
        await init_integration.runtime_data.async_refresh()
        assert downloads == [TODAY_MAP]

        freezer.move_to("2026-11-15 00:10:00+01:00")
        await init_integration.runtime_data.async_refresh()
        release.set()
        await hass.async_block_till_done()

    assert previous is not None
    assert previous.cancelled()
    # The map of the new day was downloaded instead
    criticality = [url for url in downloads if url.startswith(TODAY_MAP[:-8])]
    assert criticality == [
        criticality_preview_url(CRIT_ID, 0),
        criticality_preview_url(CRIT_ID, 1),
    ]
    assert await today.async_image() == MAP
    assert map_state(hass) == "2026-11-14T23:10:00+00:00"


@pytest.mark.usefixtures("init_integration")
async def test_maps_kept(
    hass: HomeAssistant,
    mock_dpc: AiohttpClientMocker,
) -> None:
    """Test that only the latest maps are kept, the oldest forgotten first."""
    bulletins = async_get_bulletins(hass)
    # Other addresses, rather than a query the mock would not tell apart
    others = [
        TODAY_MAP.replace("oggi", f"other{number}") for number in range(PREVIEWS_KEPT)
    ]
    for url in others:
        mock_dpc.get(url, content=MAP)
    for url in others:
        assert await bulletins.preview(url) == MAP

    # The map of today was the oldest: downloaded again
    assert await bulletins.preview(TODAY_MAP) == MAP
    assert map_requests(mock_dpc) == 2
    # The others are kept
    assert await bulletins.preview(others[-1]) == MAP
    assert map_requests(mock_dpc, others[-1]) == 1


@pytest.mark.usefixtures("init_integration")
async def test_preview_raises_when_dpc_is_unreachable(
    hass: HomeAssistant, mock_dpc: AiohttpClientMocker
) -> None:
    """Test that a map that cannot be downloaded raises DpcConnectionError."""
    url = TODAY_MAP.replace("oggi", "gone")
    mock_dpc.get(url, status=HTTPStatus.NOT_FOUND)

    with pytest.raises(DpcConnectionError):
        await async_get_bulletins(hass).preview(url)


@pytest.mark.parametrize("entry_options", [{CONF_DAYS: ["tomorrow"]}])
@pytest.mark.usefixtures("init_integration")
async def test_maps_of_the_days_of_the_place(hass: HomeAssistant) -> None:
    """Test that only the days the place shows have maps."""
    assert {state.entity_id for state in hass.states.async_all(Platform.IMAGE)} == {
        "image.dpc_tomorrow_criticality_map",
        "image.dpc_tomorrow_vigilance_map",
    }
