"""Tests for the DPC Alert dashboard, served to the frontend."""

from __future__ import annotations

from http import HTTPStatus
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.dpc.const import DASHBOARD_MODULE_URL, VERSION

from . import setup_integration

ADD_EXTRA_JS_URL = "custom_components.dpc.dashboard.frontend.add_extra_js_url"


async def test_dashboard_is_offered_with_the_frontend(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_dpc: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
) -> None:
    """Test that the strategy is served, and loaded by the frontend."""
    assert await async_setup_component(hass, "http", {})
    # The frontend itself needs its package, absent from the tests
    hass.config.components.add("frontend")

    with patch(ADD_EXTRA_JS_URL) as add_extra_js_url:
        await setup_integration(hass, mock_config_entry)

    add_extra_js_url.assert_called_once_with(
        hass, f"{DASHBOARD_MODULE_URL}?v={VERSION}"
    )
    client = await hass_client()
    response = await client.get(DASHBOARD_MODULE_URL)
    assert response.status == HTTPStatus.OK
    # Listed in the Add dashboard dialog
    assert "window).customStrategies" in await response.text()


async def test_no_dashboard_without_the_frontend(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_dpc: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
) -> None:
    """Test that nothing is served when the frontend does not run."""
    assert await async_setup_component(hass, "http", {})

    with patch(ADD_EXTRA_JS_URL) as add_extra_js_url:
        await setup_integration(hass, mock_config_entry)

    add_extra_js_url.assert_not_called()
    client = await hass_client()
    response = await client.get(DASHBOARD_MODULE_URL)
    assert response.status == HTTPStatus.NOT_FOUND
