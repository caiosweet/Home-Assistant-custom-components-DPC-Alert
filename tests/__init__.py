"""Tests for the DPC integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.dpc.api import (
    CRIT_BULLETIN_URL,
    CRIT_PATTERN_URL,
    VIGI_BULLETIN_URL,
    VIGI_PATTERN_URL,
)
from custom_components.dpc.const import DOMAIN

FIXTURES = Path(__file__).parent / "fixtures"

NAME = "DPC"
LATITUDE = 41.9
LONGITUDE = 12.5
UNIQUE_ID = f"{LATITUDE:.6f}_{LONGITUDE:.6f}"

# Bulletins served by default: criticality published on 2026-11-14 at 14:30
CRIT_ID = "20261114_1430"
VIGI_ID = "20261114"
# Default frozen time: publication day, after the criticality bulletin is out
PUBLICATION_DAY = "2026-11-14 15:00:00"

RISK_KINDS = (
    "idraulico_oggi",
    "temporali_oggi",
    "idrogeologico_oggi",
    "idraulico_domani",
    "temporali_domani",
    "idrogeologico_domani",
)


def load_fixture(filename: str) -> str:
    """Load a fixture file from tests/fixtures."""
    return (FIXTURES / filename).read_text(encoding="utf-8")


def bulletin_page(bulletin_id: str) -> str:
    """Return a minimal DPC map page that links the given bulletin."""
    return (
        '<html><body><a href="https://mappe.protezionecivile.gov.it/?id='
        f'{bulletin_id}.json&amp;hidden=info,minimap,">Bollettino</a></body></html>'
    )


def mock_dpc_responses(
    aioclient_mock: AiohttpClientMocker,
    crit_id: str = CRIT_ID,
    vigi_id: str = VIGI_ID,
) -> None:
    """Serve the DPC pages and GeoJSON files of the given bulletins."""
    aioclient_mock.get(CRIT_BULLETIN_URL, text=bulletin_page(crit_id))
    aioclient_mock.get(VIGI_BULLETIN_URL, text=bulletin_page(vigi_id))
    for day in ("today", "tomorrow"):
        aioclient_mock.get(
            CRIT_PATTERN_URL.format(crit_id, day),
            text=load_fixture(f"criticality_{day}.json"),
        )
    for day in ("oggi", "domani", "dopodomani"):
        aioclient_mock.get(
            VIGI_PATTERN_URL.format(vigi_id, day),
            text=load_fixture(f"vigilance_{day}.json"),
        )
        aioclient_mock.get(
            VIGI_PATTERN_URL.format(vigi_id, f"fenomeni_{day}"),
            text=load_fixture(f"phenomena_{day}.json"),
        )


async def setup_integration(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set up the integration for the given config entry."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def get_entity_id(hass: HomeAssistant, platform: str, unique_id: str) -> str:
    """Return the entity ID registered for a unique ID.

    Looking entities up by unique ID keeps the tests independent of entity names,
    which are translated and change the generated entity IDs.
    """
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, unique_id)
    assert entity_id, f"no {platform} entity with unique_id {unique_id}"
    return entity_id


def binary_sensor_unique_id(kind: str) -> str:
    """Return the unique ID of the binary sensor of a risk kind."""
    return f"{UNIQUE_ID}-{kind}"


def sensor_unique_id(bulletin: str) -> str:
    """Return the unique ID of the criticality or vigilance sensor."""
    return f"{NAME}_{bulletin}_{LATITUDE}_{LONGITUDE}"
