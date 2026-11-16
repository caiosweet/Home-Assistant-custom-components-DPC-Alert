"""Tests for the weather phenomena near a DPC place."""

from __future__ import annotations

from dataclasses import replace

from aiodpc import ATTRIBUTION, CompassPoint, Phenomenon
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNAVAILABLE, Platform, UnitOfLength
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.dpc.const import CONF_DAYS, DOMAIN

from . import UNIQUE_ID, mock_dpc_responses, setup_integration

# The phenomena of the bulletin of 2026-11-14 within 50 km of Rome: the place,
# the day, and the key of the phenomenon (its code and position)
SHOWERS = "5@41.573134169859415,12.674774846264892"
ROUGH_SEA = "40@41.75,12.3"
SHOWERS_TODAY = f"{UNIQUE_ID}-today-{SHOWERS}"
ROUGH_SEA_TOMORROW = f"{UNIQUE_ID}-tomorrow-{ROUGH_SEA}"


def phenomena(hass: HomeAssistant, entry: MockConfigEntry) -> dict[str, State | None]:
    """Return the state of each registered phenomenon, by unique ID."""
    return {
        registry_entry.unique_id: hass.states.get(registry_entry.entity_id)
        for registry_entry in er.async_entries_for_config_entry(
            er.async_get(hass), entry.entry_id
        )
        if registry_entry.domain == Platform.GEO_LOCATION
    }


async def update(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Update the bulletins of an entry, as its update interval does."""
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


async def test_phenomena_near_the_place(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test one entity per phenomenon within the radius, of the source dpc."""
    nearby = phenomena(hass, init_integration)
    assert nearby.keys() == {SHOWERS_TODAY, ROUGH_SEA_TOMORROW}

    showers = nearby[SHOWERS_TODAY]
    assert showers is not None
    # The type and the direction of the phenomenon, on the device of its day
    assert showers.entity_id == "geo_location.dpc_today_isolated_thunderstorms_sse"
    assert dict(showers.attributes) == {
        "source": DOMAIN,
        "latitude": 41.57313,
        "longitude": 12.67477,
        "unit_of_measurement": UnitOfLength.KILOMETERS,
        "attribution": ATTRIBUTION,
        # Both translated by Home Assistant
        "phenomenon": "isolated_thunderstorms",
        "direction": "sse",
        # The texts of aiodpc, in the language of Home Assistant
        "friendly_name": "DPC · Today Isolated showers or thunderstorms, 39.1 km SSE",
    }
    assert showers.state == "39.1"

    rough_sea = nearby[ROUGH_SEA_TOMORROW]
    assert rough_sea is not None
    assert rough_sea.entity_id == "geo_location.dpc_tomorrow_moderate_sea_sw"
    assert rough_sea.attributes["phenomenon"] == "moderate_sea"
    assert rough_sea.attributes["direction"] == "sw"


async def test_phenomena_follow_the_days(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that after midnight the phenomena of yesterday are removed.

    Those of tomorrow move to the device of today, with the IDs of today.
    """
    freezer.move_to("2026-11-15 00:10:00+01:00")
    await update(hass, init_integration)

    rough_sea_today = f"{UNIQUE_ID}-today-{ROUGH_SEA}"
    nearby = phenomena(hass, init_integration)
    assert nearby.keys() == {rough_sea_today}
    still_rough = nearby[rough_sea_today]
    assert still_rough is not None
    assert still_rough.entity_id == "geo_location.dpc_today_moderate_sea_sw"
    registry_entry = er.async_get(hass).async_get(still_rough.entity_id)
    assert registry_entry is not None
    device = device_registry.async_get(registry_entry.device_id or "")
    assert device is not None
    assert device.identifiers == {(DOMAIN, f"{UNIQUE_ID}-today")}


async def test_phenomena_of_the_next_bulletin(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that a phenomenon of the next bulletin, on the same day, is the same."""
    entity_ids = {
        unique_id: state.entity_id
        for unique_id, state in phenomena(hass, init_integration).items()
        if state is not None
    }
    aioclient_mock.clear_requests()
    mock_dpc_responses(aioclient_mock, crit_id="20261115_1500", vigi_id="20261115")
    freezer.move_to("2026-11-15 15:30:00+01:00")

    await update(hass, init_integration)

    # The same fixtures, one day later: the same phenomena on the same days
    nearby = phenomena(hass, init_integration)
    assert {
        unique_id: state.entity_id
        for unique_id, state in nearby.items()
        if state is not None
    } == entity_ids
    assert nearby[SHOWERS_TODAY] is not None
    assert len(hass.states.async_all(Platform.GEO_LOCATION)) == 2


async def test_phenomena_of_a_previous_run_are_removed(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    mock_dpc: AiohttpClientMocker,
) -> None:
    """Test that a phenomenon registered before the restart, now gone, is removed.

    The betas of 2026.11.1 had the date in the unique IDs of the phenomena.
    """
    mock_config_entry.add_to_hass(hass)
    gone = entity_registry.async_get_or_create(
        Platform.GEO_LOCATION,
        DOMAIN,
        f"{UNIQUE_ID}-2026-11-14-{SHOWERS}",
        config_entry=mock_config_entry,
    )
    # Phenomena are not the only registered entities: the others stay
    other = entity_registry.async_get_or_create(
        Platform.SENSOR,
        DOMAIN,
        f"{UNIQUE_ID}-alert_today",
        config_entry=mock_config_entry,
    )

    await setup_integration(hass, mock_config_entry)

    assert entity_registry.async_get(gone.entity_id) is None
    assert entity_registry.async_get(other.entity_id) is not None
    assert phenomena(hass, mock_config_entry).keys() == {
        SHOWERS_TODAY,
        ROUGH_SEA_TOMORROW,
    }


async def test_phenomena_unavailable_without_dpc(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that the phenomena follow the availability of the coordinator."""
    coordinator = init_integration.runtime_data
    coordinator.last_update_success = False
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    for state in phenomena(hass, init_integration).values():
        assert state is not None
        assert state.state == STATE_UNAVAILABLE


async def test_phenomena_of_unknown_codes_are_left_out(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that a phenomenon whose code aiodpc does not know has no entity."""
    coordinator = init_integration.runtime_data
    vigilance = coordinator.data.vigilance
    assert vigilance is not None
    today, *later = vigilance.bulletin.days
    unknown = Phenomenon(
        code=99,
        category=None,
        description=None,
        latitude=41.8,
        longitude=12.4,
        distance_km=12.3,
        direction=CompassPoint.SW,
        degrees=225,
        bulletin_id=None,
        bulletin_date=None,
    )
    days = (replace(today, phenomena=(*today.phenomena, unknown)), *later)

    coordinator.async_set_updated_data(
        replace(
            coordinator.data,
            vigilance=replace(
                vigilance, bulletin=replace(vigilance.bulletin, days=days)
            ),
        )
    )
    await hass.async_block_till_done()

    assert phenomena(hass, init_integration).keys() == {
        SHOWERS_TODAY,
        ROUGH_SEA_TOMORROW,
    }


@pytest.mark.parametrize("entry_options", [{CONF_DAYS: ["tomorrow"]}])
async def test_phenomena_of_the_days_of_the_place(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that only the phenomena of the days the place shows have entities."""
    assert phenomena(hass, init_integration).keys() == {ROUGH_SEA_TOMORROW}


@pytest.mark.parametrize(
    ("language", "name"),
    [
        (
            "pt-BR",
            "DPC · Hoje Pancadas de chuva ou tempestades isoladas, 39,1 km SSE",
        ),
        # A language aiodpc does not speak: the English texts
        ("nl", "DPC · Today Isolated showers or thunderstorms, 39.1 km SSE"),
    ],
)
async def test_phenomena_in_the_language_of_home_assistant(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_dpc: AiohttpClientMocker,
    language: str,
    name: str,
) -> None:
    """Test that a phenomenon is named in the language of Home Assistant."""
    hass.config.language = language
    await setup_integration(hass, mock_config_entry)

    showers = phenomena(hass, mock_config_entry)[SHOWERS_TODAY]
    assert showers is not None
    assert showers.attributes["friendly_name"] == name
    # The entity ID is in English, whatever the language
    assert showers.entity_id == "geo_location.dpc_today_isolated_thunderstorms_sse"
