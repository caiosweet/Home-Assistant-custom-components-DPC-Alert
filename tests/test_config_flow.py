"""Tests for the DPC config flow and options flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

from aiodpc import (
    CRITICALITY_PAGE_URL,
    AlertZone,
    DpcConnectionError,
    DpcLocationError,
)
import aiohttp
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LOCATION,
    CONF_LONGITUDE,
    CONF_NAME,
    CONF_RADIUS,
    CONF_SCAN_INTERVAL,
    CONF_ZONE,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult, FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.dpc.const import CONF_MUNICIPALITY, CONF_WARNING_LEVEL, DOMAIN

from . import LATITUDE, LONGITUDE, NAME, PUBLICATION_DAY, UNIQUE_ID, mock_dpc_responses

PLACE = {CONF_NAME: NAME, CONF_LATITUDE: LATITUDE, CONF_LONGITUDE: LONGITUDE}
MAP_INPUT = {
    CONF_NAME: NAME,
    CONF_LOCATION: {CONF_LATITUDE: LATITUDE, CONF_LONGITUDE: LONGITUDE},
}
ROME_ZONE = AlertZone("Bacini di Roma", ("Roma", "Fiumicino", "Tivoli"))
GET_ALERT_ZONE = "custom_components.dpc.config_flow.DpcClient.get_alert_zone"

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


def selector_config(result: FlowResult, field: str) -> dict[str, Any]:
    """Return the selector configuration of a field of a form."""
    for key, validator in result["data_schema"].schema.items():
        if key == field:
            return validator.config
    raise AssertionError(f"no field {field}")


async def start(hass: HomeAssistant, menu_option: str) -> FlowResult:
    """Start a user flow and choose an option of its menu."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["map", "zone"]
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": menu_option}
    )


async def test_map_flow(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test a place picked on the map, with its municipality."""
    result = await start(hass, "map")
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "map"

    with patch(GET_ALERT_ZONE, return_value=ROME_ZONE):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MAP_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "municipality"
    assert result["description_placeholders"] == {"zone": "Bacini di Roma"}
    assert selector_config(result, CONF_MUNICIPALITY)["options"] == [
        "Fiumicino",
        "Roma",
        "Tivoli",
    ]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MUNICIPALITY: "Roma"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == NAME
    assert result["data"] == PLACE
    assert result["options"] == {CONF_MUNICIPALITY: "Roma"}
    assert result["result"].unique_id == UNIQUE_ID
    assert len(mock_setup_entry.mock_calls) == 1


async def test_map_flow_starts_at_home(hass: HomeAssistant) -> None:
    """Test that the map starts at the home of Home Assistant, named after it."""
    result = await start(hass, "map")

    suggested = {
        str(key): key.description["suggested_value"]
        for key in result["data_schema"].schema
    }
    assert suggested[CONF_LOCATION] == {
        CONF_LATITUDE: hass.config.latitude,
        CONF_LONGITUDE: hass.config.longitude,
    }
    # The place is named after the home
    assert suggested[CONF_NAME] == hass.config.location_name


async def test_municipality_left_empty(hass: HomeAssistant) -> None:
    """Test a place without municipality: its alert zone only is used."""
    result = await start(hass, "map")
    with patch(GET_ALERT_ZONE, return_value=ROME_ZONE):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MAP_INPUT
        )

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {CONF_MUNICIPALITY: ""}


@pytest.mark.parametrize(("name", "title"), [(None, "Casa"), ("Ufficio", "Ufficio")])
async def test_zone_flow(hass: HomeAssistant, name: str | None, title: str) -> None:
    """Test a place taken from a zone, named after it unless named."""
    hass.states.async_set(
        "zone.home",
        "0",
        {"latitude": LATITUDE, "longitude": LONGITUDE, "friendly_name": "Casa"},
    )
    result = await start(hass, "zone")
    assert result["step_id"] == "zone"

    user_input = {CONF_ZONE: "zone.home"} | ({CONF_NAME: name} if name else {})
    with patch(GET_ALERT_ZONE, return_value=ROME_ZONE):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input
        )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MUNICIPALITY: "Roma"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == title
    assert result["data"] == PLACE | {CONF_NAME: title}


async def test_zone_not_found(hass: HomeAssistant) -> None:
    """Test a zone that does not exist anymore."""
    result = await start(hass, "zone")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ZONE: "zone.removed"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_ZONE: "zone_not_found"}


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (DpcLocationError, "coordinates_outside"),
        (DpcConnectionError, "cannot_connect"),
    ],
)
async def test_place_errors(
    hass: HomeAssistant, side_effect: type[Exception], error: str
) -> None:
    """Test the errors of a place and that the flow recovers from them."""
    result = await start(hass, "map")

    with patch(GET_ALERT_ZONE, side_effect=side_effect):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MAP_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    with patch(GET_ALERT_ZONE, return_value=ROME_ZONE):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MAP_INPUT
        )

    assert result["step_id"] == "municipality"


async def test_place_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that the same place cannot be added twice, without asking DPC."""
    mock_config_entry.add_to_hass(hass)
    result = await start(hass, "map")

    with patch(GET_ALERT_ZONE) as get_alert_zone:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MAP_INPUT | {CONF_NAME: "Casa"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    get_alert_zone.assert_not_called()


@pytest.mark.parametrize(
    ("latitude", "longitude", "step_id", "errors"),
    [
        (LATITUDE, LONGITUDE, "municipality", None),
        (48.8566, 2.3522, "map", {"base": "coordinates_outside"}),
    ],
)
async def test_place_checked_with_dpc(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    latitude: float,
    longitude: float,
    step_id: str,
    errors: dict[str, str] | None,
) -> None:
    """Test that the place must be inside a DPC alert zone."""
    freezer.move_to(PUBLICATION_DAY)
    mock_dpc_responses(aioclient_mock)
    result = await start(hass, "map")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: NAME,
            CONF_LOCATION: {CONF_LATITUDE: latitude, CONF_LONGITUDE: longitude},
        },
    )

    assert result["step_id"] == step_id
    assert result.get("errors") == errors


async def test_place_when_dpc_is_unreachable(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test that the place cannot be checked when DPC is unreachable."""
    aioclient_mock.get(CRITICALITY_PAGE_URL, exc=aiohttp.ClientError)
    result = await start(hass, "map")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MAP_INPUT
    )

    assert result["errors"] == {"base": "cannot_connect"}


async def test_options_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test the options flow, offering the municipalities of the zone."""
    mock_config_entry.add_to_hass(hass)

    with patch(GET_ALERT_ZONE, return_value=ROME_ZONE):
        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert selector_config(result, CONF_MUNICIPALITY)["options"] == [
        "Fiumicino",
        "Roma",
        "Tivoli",
    ]

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


@pytest.mark.parametrize("entry_options", [{CONF_MUNICIPALITY: "Roma"}])
async def test_options_flow_without_alert_zone(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that any municipality can be typed when DPC is unreachable."""
    mock_config_entry.add_to_hass(hass)

    with patch(GET_ALERT_ZONE, side_effect=DpcConnectionError):
        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )
    config = selector_config(result, CONF_MUNICIPALITY)
    assert config["options"] == ["Roma"]
    assert config["custom_value"] is True

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_MUNICIPALITY: "Tivoli", CONF_RADIUS: 50}
    )

    assert mock_config_entry.options[CONF_MUNICIPALITY] == "Tivoli"


@pytest.mark.parametrize("entry_options", [{CONF_MUNICIPALITY: "Roma"}])
async def test_options_flow_clears_the_municipality(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that a cleared municipality is saved as empty."""
    mock_config_entry.add_to_hass(hass)
    with patch(GET_ALERT_ZONE, return_value=ROME_ZONE):
        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_RADIUS: 50}
    )

    assert mock_config_entry.options[CONF_MUNICIPALITY] == ""


async def test_place_of_an_entry_without_unique_id(hass: HomeAssistant) -> None:
    """Test a place added when entries had no unique ID, and one without data."""
    MockConfigEntry(domain=DOMAIN, version=2, data={}).add_to_hass(hass)
    MockConfigEntry(
        domain=DOMAIN, version=2, title="Casa", unique_id="Casa", data=PLACE
    ).add_to_hass(hass)
    result = await start(hass, "map")

    with patch(GET_ALERT_ZONE) as get_alert_zone:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MAP_INPUT
        )

    assert result["errors"] == {"base": "place_nearby"}
    assert result["description_placeholders"] == {"place": "Casa"}
    get_alert_zone.assert_not_called()


@pytest.mark.parametrize(
    ("latitude", "errors"),
    [
        # About 555 m north: the bulletins would be the same
        (LATITUDE + 0.005, {"base": "place_nearby"}),
        # About 2.2 km north
        (LATITUDE + 0.02, None),
    ],
)
async def test_place_near_another_one(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    latitude: float,
    errors: dict[str, str] | None,
) -> None:
    """Test that a place less than 1 km from another one is refused."""
    mock_config_entry.add_to_hass(hass)
    result = await start(hass, "map")

    with patch(GET_ALERT_ZONE, return_value=ROME_ZONE):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Ufficio",
                CONF_LOCATION: {CONF_LATITUDE: latitude, CONF_LONGITUDE: LONGITUDE},
            },
        )

    assert result.get("errors") == errors
    if errors:
        assert result["description_placeholders"] == {"place": NAME}


async def test_name_of_another_place(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that the name of another place is refused, whatever its case."""
    mock_config_entry.add_to_hass(hass)
    result = await start(hass, "map")

    with patch(GET_ALERT_ZONE, return_value=ROME_ZONE):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: NAME.lower(),
                CONF_LOCATION: {CONF_LATITUDE: 45.46, CONF_LONGITUDE: 9.19},
            },
        )

    assert result["errors"] == {CONF_NAME: "name_exists"}
