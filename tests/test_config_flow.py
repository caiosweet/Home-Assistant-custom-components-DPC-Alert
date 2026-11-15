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

from . import LATITUDE, LONGITUDE, PUBLICATION_DAY, UNIQUE_ID, mock_dpc_responses

MAP_INPUT = {CONF_LOCATION: {CONF_LATITUDE: LATITUDE, CONF_LONGITUDE: LONGITUDE}}
BOLZANO = (46.49, 11.33)
ROME_ZONE = AlertZone("Bacini di Roma", ("Roma", "Fiumicino", "Tivoli"))
BOLZANO_ZONE = AlertZone(
    "Provincia Autonoma di Bolzano", ("Bolzano/Bozen", "Merano/Meran")
)
# A place is named after its alert zone
PLACE = {
    CONF_NAME: "Bacini di Roma",
    CONF_LATITUDE: LATITUDE,
    CONF_LONGITUDE: LONGITUDE,
}
GET_ALERT_ZONE = "custom_components.dpc.config_flow.DpcClient.get_alert_zone"

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


def schema_key(result: FlowResult, field: str) -> Any:
    """Return the key of a field of a form, e.g. to know if it is required."""
    return next(key for key in result["data_schema"].schema if key == field)


def selector_config(result: FlowResult, field: str) -> dict[str, Any]:
    """Return the selector configuration of a field of a form."""
    return result["data_schema"].schema[schema_key(result, field)].config


def is_required(result: FlowResult, field: str) -> bool:
    """Return whether a field of a form is required."""
    return type(schema_key(result, field)).__name__ == "Required"


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


def map_input(latitude: float, longitude: float) -> dict[str, Any]:
    """Return the input of the map step for a place."""
    return {CONF_LOCATION: {CONF_LATITUDE: latitude, CONF_LONGITUDE: longitude}}


def place_entry(
    zone: str, latitude: float, longitude: float, municipality: str
) -> MockConfigEntry:
    """Return the config entry of a place, named after its alert zone."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=2,
        title=zone,
        data={CONF_NAME: zone, CONF_LATITUDE: latitude, CONF_LONGITUDE: longitude},
        options={CONF_MUNICIPALITY: municipality},
    )


async def to_municipality(
    hass: HomeAssistant,
    alert_zone: AlertZone = ROME_ZONE,
    at: tuple[float, float] = (LATITUDE, LONGITUDE),
) -> FlowResult:
    """Pick the place on the map, up to the choice of its municipality."""
    result = await start(hass, "map")
    with patch(GET_ALERT_ZONE, return_value=alert_zone):
        return await hass.config_entries.flow.async_configure(
            result["flow_id"], map_input(*at)
        )


async def test_map_flow(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test a place picked on the map, named after its alert zone."""
    result = await start(hass, "map")
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "map"
    assert [str(key) for key in result["data_schema"].schema] == [CONF_LOCATION]

    with patch(GET_ALERT_ZONE, return_value=ROME_ZONE):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MAP_INPUT
        )

    assert result["step_id"] == "municipality"
    assert result["description_placeholders"] == {"zone": "Bacini di Roma"}
    assert is_required(result, CONF_MUNICIPALITY)
    assert selector_config(result, CONF_MUNICIPALITY)["options"] == [
        "Fiumicino",
        "Roma",
        "Tivoli",
    ]

    # Typed in the search: saved as DPC lists it
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MUNICIPALITY: " roma "}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Bacini di Roma"
    assert result["data"] == PLACE
    assert result["options"] == {CONF_MUNICIPALITY: "Roma"}
    assert result["result"].unique_id == UNIQUE_ID
    assert len(mock_setup_entry.mock_calls) == 1


async def test_map_flow_starts_at_home(hass: HomeAssistant) -> None:
    """Test that the map starts at the home of Home Assistant."""
    result = await start(hass, "map")

    assert schema_key(result, CONF_LOCATION).description["suggested_value"] == {
        CONF_LATITUDE: hass.config.latitude,
        CONF_LONGITUDE: hass.config.longitude,
    }


async def test_zone_flow(hass: HomeAssistant) -> None:
    """Test a place taken from a zone."""
    hass.states.async_set(
        "zone.home",
        "0",
        {"latitude": LATITUDE, "longitude": LONGITUDE, "friendly_name": "Casa"},
    )
    result = await start(hass, "zone")
    assert result["step_id"] == "zone"
    assert [str(key) for key in result["data_schema"].schema] == [CONF_ZONE]

    with patch(GET_ALERT_ZONE, return_value=ROME_ZONE):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ZONE: "zone.home"}
        )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MUNICIPALITY: "Roma"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Bacini di Roma"
    assert result["data"] == PLACE


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
            result["flow_id"], MAP_INPUT
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
        {CONF_LOCATION: {CONF_LATITUDE: latitude, CONF_LONGITUDE: longitude}},
    )

    assert result["step_id"] == step_id
    assert (result.get("errors") or None) == errors


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


async def test_municipality_not_listed(hass: HomeAssistant) -> None:
    """Test that the municipality must be one of the alert zone."""
    result = await to_municipality(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MUNICIPALITY: "Milano"}
    )

    assert result["step_id"] == "municipality"
    assert result["errors"] == {CONF_MUNICIPALITY: "municipality_not_listed"}


@pytest.mark.parametrize("municipality", ["Bolzano/Bozen", "Bozen", "bolzano"])
async def test_municipality_of_another_place(
    hass: HomeAssistant, municipality: str
) -> None:
    """Test that a municipality can be added once, whatever its name."""
    place_entry(
        "Provincia Autonoma di Bolzano", 46.5, 11.35, "Bolzano/Bozen"
    ).add_to_hass(hass)
    result = await to_municipality(hass, BOLZANO_ZONE, at=BOLZANO)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MUNICIPALITY: municipality}
    )

    assert result["errors"] == {CONF_MUNICIPALITY: "municipality_in_use"}
    assert result["description_placeholders"] == {
        "zone": "Provincia Autonoma di Bolzano",
        "municipality": "Bolzano/Bozen",
    }


async def test_homonym_of_another_place(hass: HomeAssistant) -> None:
    """Test that a municipality far away with the same name is another one.

    Peglio is in Lombardy and in the Marche.
    """
    place_entry("Lario e Prealpi occidentali", 46.16, 9.295, "Peglio").add_to_hass(hass)
    result = await to_municipality(
        hass, AlertZone("Marc-1", ("Peglio", "Urbino")), at=(43.696, 12.497)
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MUNICIPALITY: "Peglio"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert (result["title"], result["options"]) == (
        "Marc-1",
        {CONF_MUNICIPALITY: "Peglio"},
    )


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
    # Required, also for the places added before it was
    assert is_required(result, CONF_MUNICIPALITY)

    options = {
        "binary_sensor": False,
        "sensor": True,
        CONF_MUNICIPALITY: "roma",
        CONF_SCAN_INTERVAL: 15,
        CONF_WARNING_LEVEL: 3,
        CONF_RADIUS: 30,
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], options
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options == {
        **options,
        # The platforms left unchanged are enabled
        "image": True,
        "geo_location": True,
        CONF_MUNICIPALITY: "Roma",
        CONF_RADIUS: 30.0,
    }


@pytest.mark.parametrize(
    ("municipality", "saved"), [("Tivoli", "Tivoli"), ("  ", None)]
)
@pytest.mark.parametrize("entry_options", [{CONF_MUNICIPALITY: "Roma"}])
async def test_options_flow_without_alert_zone(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    municipality: str,
    saved: str | None,
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
        result["flow_id"], {CONF_MUNICIPALITY: municipality, CONF_RADIUS: 50}
    )

    if saved:
        assert mock_config_entry.options[CONF_MUNICIPALITY] == saved
    else:
        assert result["errors"] == {CONF_MUNICIPALITY: "municipality_not_listed"}


@pytest.mark.parametrize(
    ("municipality", "errors"),
    [
        # Not in the alert zone of the place
        ("Milano", {CONF_MUNICIPALITY: "municipality_not_listed"}),
        # The municipality of another place
        ("Tivoli", {CONF_MUNICIPALITY: "municipality_in_use"}),
        # Its own municipality
        ("Roma", None),
    ],
)
@pytest.mark.parametrize("entry_options", [{CONF_MUNICIPALITY: "Roma"}])
async def test_options_flow_checks_the_municipality(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    municipality: str,
    errors: dict[str, str] | None,
) -> None:
    """Test that the options check the municipality, keeping what was entered."""
    mock_config_entry.add_to_hass(hass)
    place_entry("Bacini di Roma", 41.96, 12.8, "Tivoli").add_to_hass(hass)
    with patch(GET_ALERT_ZONE, return_value=ROME_ZONE):
        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_MUNICIPALITY: municipality, CONF_RADIUS: 40}
    )

    assert (result.get("errors") or None) == errors
    if not errors:
        assert mock_config_entry.options[CONF_MUNICIPALITY] == municipality
        return
    assert result["type"] is FlowResultType.FORM
    key = schema_key(result, CONF_MUNICIPALITY)
    assert key.description["suggested_value"] == municipality
    if errors == {CONF_MUNICIPALITY: "municipality_in_use"}:
        assert result["description_placeholders"] == {"municipality": "Tivoli"}
