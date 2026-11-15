"""Tests for the weather phenomena near a DPC place."""

from __future__ import annotations

from dataclasses import replace

from aiodpc import Phenomenon
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNAVAILABLE, Platform, UnitOfLength
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.dpc.const import DOMAIN

from . import UNIQUE_ID, mock_dpc_responses, rome, setup_integration

# The phenomena of the bulletin of 2026-11-14 within 50 km of Rome: the place,
# the day, and the key of the phenomenon (its code and position)
SHOWERS = "5@41.573134169859415,12.674774846264892"
ROUGH_SEA = "40@41.75,12.3"
SHOWERS_TODAY = f"{UNIQUE_ID}-2026-11-14-{SHOWERS}"
ROUGH_SEA_TOMORROW = f"{UNIQUE_ID}-2026-11-15-{ROUGH_SEA}"


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
    assert showers.entity_id == "geo_location.dpc_nearby_precipitation"
    assert showers.attributes["friendly_name"] == "DPC Nearby precipitation"
    assert float(showers.state) < 50
    assert showers.attributes["unit_of_measurement"] == UnitOfLength.KILOMETERS
    assert showers.attributes["source"] == DOMAIN
    assert showers.attributes["latitude"] == 41.57313
    assert showers.attributes["longitude"] == 12.67477
    # Translated by Home Assistant: "Isolated showers or thunderstorms"
    assert showers.attributes["phenomenon"] == "isolated_thunderstorms"
    assert showers.attributes["day"] == "today"
    assert showers.attributes["valid_until"] == rome(2026, 11, 15)
    assert (
        # The legend as DPC writes it
        showers.attributes["description"] == "rovesci o temporali a carattere isolato"
    )
    assert showers.attributes["direction"] == "SSE"

    rough_sea = nearby[ROUGH_SEA_TOMORROW]
    assert rough_sea is not None
    assert rough_sea.entity_id == "geo_location.dpc_nearby_sea_state"
    assert rough_sea.attributes["phenomenon"] == "moderate_sea"
    assert rough_sea.attributes["day"] == "tomorrow"


async def test_phenomena_follow_the_days(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that after midnight the phenomena of yesterday are removed.

    Those of tomorrow are the same entities, now today.
    """
    rough_sea = phenomena(hass, init_integration)[ROUGH_SEA_TOMORROW]
    assert rough_sea is not None

    freezer.move_to("2026-11-15 00:10:00+01:00")
    await update(hass, init_integration)

    nearby = phenomena(hass, init_integration)
    assert nearby.keys() == {ROUGH_SEA_TOMORROW}
    assert hass.states.get("geo_location.dpc_precipitation") is None
    still_rough = nearby[ROUGH_SEA_TOMORROW]
    assert still_rough is not None
    assert still_rough.entity_id == rough_sea.entity_id
    assert still_rough.attributes["day"] == "today"


async def test_phenomena_of_the_next_bulletin(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that the next bulletin replaces the phenomena of the previous one."""
    aioclient_mock.clear_requests()
    mock_dpc_responses(aioclient_mock, crit_id="20261115_1500", vigi_id="20261115")
    freezer.move_to("2026-11-15 15:30:00+01:00")

    await update(hass, init_integration)

    nearby = phenomena(hass, init_integration)
    # The same fixtures, one day later
    assert nearby.keys() == {
        f"{UNIQUE_ID}-2026-11-15-{SHOWERS}",
        f"{UNIQUE_ID}-2026-11-16-{ROUGH_SEA}",
    }
    assert all(state is not None for state in nearby.values())
    assert len(hass.states.async_all(Platform.GEO_LOCATION)) == 2


async def test_phenomena_of_a_previous_run_are_removed(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    mock_dpc: AiohttpClientMocker,
) -> None:
    """Test that a phenomenon registered before the restart, now gone, is removed."""
    mock_config_entry.add_to_hass(hass)
    gone = entity_registry.async_get_or_create(
        Platform.GEO_LOCATION,
        DOMAIN,
        f"{UNIQUE_ID}-2026-11-13-11@41.0,12.0",
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
        direction="SW",
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
