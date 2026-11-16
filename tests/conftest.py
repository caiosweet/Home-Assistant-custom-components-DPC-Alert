"""Fixtures for the DPC tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.dpc.const import CONF_DAYS, CONF_MUNICIPALITY, DOMAIN, PlaceDay

from . import (
    LATITUDE,
    LONGITUDE,
    NAME,
    PUBLICATION_DAY,
    UNIQUE_ID,
    mock_dpc_responses,
    setup_integration,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in all tests."""


@pytest.fixture
def entry_options() -> dict[str, Any]:
    """Return the options of the config entry; parametrize it to change them."""
    return {}


@pytest.fixture
def mock_config_entry(entry_options: dict[str, Any]) -> MockConfigEntry:
    """Return the default config entry, with every day."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        version=2,
        minor_version=2,
        unique_id=UNIQUE_ID,
        data={CONF_NAME: NAME, CONF_LATITUDE: LATITUDE, CONF_LONGITUDE: LONGITUDE},
        options={CONF_MUNICIPALITY: "", CONF_DAYS: list(PlaceDay), **entry_options},
    )


@pytest.fixture
def mock_dpc(
    aioclient_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> AiohttpClientMocker:
    """Serve the default DPC bulletins at the default frozen time."""
    freezer.move_to(PUBLICATION_DAY)
    mock_dpc_responses(aioclient_mock)
    return aioclient_mock


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_dpc: AiohttpClientMocker,
) -> MockConfigEntry:
    """Set up the integration with the default bulletins."""
    await setup_integration(hass, mock_config_entry)
    return mock_config_entry


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Do not set up the integration when a config flow creates an entry."""
    with patch(
        "custom_components.dpc.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup
