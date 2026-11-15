"""Tests for the maps of the DPC bulletins."""

from __future__ import annotations

from http import HTTPStatus

from aiodpc.urls import criticality_preview_url, vigilance_preview_url
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.image import ImageEntity
from homeassistant.const import STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant
import httpx
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator
import respx

from custom_components.dpc.image import PLACEHOLDER_IMAGE

from . import CRIT_ID, UNIQUE_ID, VIGI_ID, get_entity_id

PNG = b"\x89PNG\r\n\x1a\n map"


def map_entity(hass: HomeAssistant, key: str) -> ImageEntity:
    """Return the image entity of a map, e.g. criticality_map_today."""
    entity_id = get_entity_id(hass, Platform.IMAGE, f"{UNIQUE_ID}-{key}")
    entity = hass.data[Platform.IMAGE].get_entity(entity_id)
    assert isinstance(entity, ImageEntity)
    return entity


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
    today = hass.states.get("image.dpc_criticality_map_today")
    assert today is not None
    # The state is when the map shown last changed: at the setup
    assert today.state == "2026-11-14T14:00:00+00:00"


@respx.mock
async def test_missing_map_uses_placeholder_image(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that an absent map is served by a generic placeholder image."""
    map_entity_ = map_entity(hass, "criticality_map_tomorrow")
    assert map_entity_.image_url is None
    assert await map_entity_.async_image() == PLACEHOLDER_IMAGE


@respx.mock
async def test_map_is_downloaded_when_shown(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    # Requested after init_integration, so its access token is issued after the
    # clock is moved to the frozen time and does not expire
    hass_client: ClientSessionGenerator,
) -> None:
    """Test that Home Assistant serves the map downloaded from DPC."""
    preview = respx.get(criticality_preview_url(CRIT_ID, 0)).respond(
        content=PNG, headers={"content-type": "image/png"}
    )
    client = await hass_client()

    for _ in range(2):
        response = await client.get("/api/image_proxy/image.dpc_criticality_map_today")
        assert response.status == HTTPStatus.OK
        assert await response.read() == PNG

    # The map is kept until it changes
    assert preview.call_count == 1


@respx.mock
async def test_map_changes_at_midnight(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that after midnight the map of today is the second day of the bulletin."""
    respx.get(criticality_preview_url(CRIT_ID, 0)).mock(
        return_value=httpx.Response(200, content=PNG)
    )
    today = map_entity(hass, "criticality_map_today")
    assert await today.async_image() == PNG

    freezer.move_to("2026-11-15 00:10:00+01:00")
    await init_integration.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert today.image_url == criticality_preview_url(CRIT_ID, 1)
    # The map of the previous day is forgotten
    assert today._cached_image is None
    state = hass.states.get("image.dpc_criticality_map_today")
    assert state is not None
    assert state.state == "2026-11-14T23:10:00+00:00"
    # Until the next bulletin there is no map of tomorrow
    assert map_entity(hass, "criticality_map_tomorrow").image_url is None
    tomorrow = hass.states.get("image.dpc_criticality_map_tomorrow")
    assert tomorrow is not None
    assert tomorrow.state == STATE_UNKNOWN


@respx.mock
async def test_map_is_kept_while_the_day_does_not_change(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that an update with the same bulletin keeps the downloaded map."""
    respx.get(criticality_preview_url(CRIT_ID, 0)).mock(
        return_value=httpx.Response(200, content=PNG)
    )
    today = map_entity(hass, "criticality_map_today")
    await today.async_image()

    freezer.move_to("2026-11-14 16:00:00+01:00")
    await init_integration.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert today._cached_image is not None
    state = hass.states.get("image.dpc_criticality_map_today")
    assert state is not None
    assert state.state == "2026-11-14T14:00:00+00:00"
