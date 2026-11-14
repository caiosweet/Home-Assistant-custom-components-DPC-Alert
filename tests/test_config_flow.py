"""Tests for the DPC config flow and options flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from aiodpc import CRITICALITY_PAGE_URL, VIGILANCE_PAGE_URL, DpcConnectionError
import aiohttp
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    CONF_RADIUS,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.dpc.const import CONF_MUNICIPALITY, CONF_WARNING_LEVEL, DOMAIN

from . import LATITUDE, LONGITUDE, NAME, PUBLICATION_DAY, UNIQUE_ID, mock_dpc_responses

USER_INPUT = {CONF_NAME: NAME, CONF_LATITUDE: LATITUDE, CONF_LONGITUDE: LONGITUDE}
VALIDATE = "custom_components.dpc.config_flow.DpcClient.is_location_covered"

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_user_flow(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test a successful user flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch(VALIDATE, return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == NAME
    assert result["data"] == USER_INPUT
    assert result["result"].unique_id == UNIQUE_ID
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("validation", "error"),
    [
        ({"return_value": False}, "coordinates_outside"),
        ({"side_effect": DpcConnectionError}, "cannot_connect"),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant, validation: dict, error: str
) -> None:
    """Test the errors of the user step and that the flow recovers from them."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(VALIDATE, **validation):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    with patch(VALIDATE, return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    ("latitude", "longitude", "error"),
    [(LATITUDE, LONGITUDE, None), (48.8566, 2.3522, "coordinates_outside")],
)
async def test_user_flow_validates_the_location_with_dpc(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    latitude: float,
    longitude: float,
    error: str | None,
) -> None:
    """Test that the location must be inside a DPC alert zone."""
    freezer.move_to(PUBLICATION_DAY)
    mock_dpc_responses(aioclient_mock)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {**USER_INPUT, CONF_LATITUDE: latitude, CONF_LONGITUDE: longitude},
    )

    if error is None:
        assert result["type"] is FlowResultType.CREATE_ENTRY
    else:
        assert result["errors"] == {"base": error}


async def test_user_flow_when_dpc_is_unreachable(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test that the location cannot be validated when DPC is unreachable."""
    aioclient_mock.get(CRITICALITY_PAGE_URL, exc=aiohttp.ClientError)
    aioclient_mock.get(VIGILANCE_PAGE_URL, exc=aiohttp.ClientError)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_location_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that the same location cannot be added twice."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(VALIDATE, return_value=True) as mock_validate:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {**USER_INPUT, CONF_NAME: "Casa"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    mock_validate.assert_not_called()


async def test_options_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test the options flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    options = {
        "binary_sensor": False,
        "sensor": True,
        CONF_MUNICIPALITY: "Roma",
        CONF_SCAN_INTERVAL: 15,
        CONF_WARNING_LEVEL: 3,
        CONF_RADIUS: 30,
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], options
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options == {**options, CONF_RADIUS: 30.0}
