"""Tests for the DPC integration."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import struct
import zlib

from aiodpc import CRITICALITY_PAGE_URL, ROME_TZ, VIGILANCE_PAGE_URL
from aiodpc.urls import (
    criticality_geojson_url,
    criticality_preview_url,
    phenomena_geojson_url,
    vigilance_geojson_url,
    vigilance_preview_url,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
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
PUBLICATION_DAY = "2026-11-14 15:00:00+01:00"


def png(*pixels: bytes) -> bytes:
    """Return a PNG of a row of RGB pixels, as small as a test needs."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data))
        )

    # Width, height, 8 bits per sample, RGB, then the default methods
    header = struct.pack(">IIBBBBB", len(pixels), 1, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"\x00" + b"".join(pixels)))
        + chunk(b"IEND", b"")
    )


WHITE = b"\xff\xff\xff"
# A map of the bulletin, and one as DPC often publishes it: all white
MAP = png(WHITE, b"\x90\xc9\x85")
BLANK_MAP = png(WHITE, WHITE)


def rome(*args: int) -> datetime:
    """Return a datetime in Italy, where the days of the bulletins are."""
    return datetime(*args, tzinfo=ROME_TZ)


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
    """Serve the DPC pages, GeoJSON files and maps of the given bulletins."""
    aioclient_mock.get(CRITICALITY_PAGE_URL, text=bulletin_page(crit_id))
    aioclient_mock.get(VIGILANCE_PAGE_URL, text=bulletin_page(vigi_id))
    for offset, day in enumerate(("today", "tomorrow")):
        aioclient_mock.get(
            criticality_geojson_url(crit_id, offset),
            text=load_fixture(f"criticality_{day}.json"),
        )
    for offset, day in enumerate(("oggi", "domani", "dopodomani")):
        aioclient_mock.get(
            vigilance_geojson_url(vigi_id, offset),
            text=load_fixture(f"vigilance_{day}.json"),
        )
        aioclient_mock.get(
            phenomena_geojson_url(vigi_id, offset),
            text=load_fixture(f"phenomena_{day}.json"),
        )
    # DPC publishes no vigilance map for the day after tomorrow
    for offset in (0, 1):
        aioclient_mock.get(criticality_preview_url(crit_id, offset), content=MAP)
        aioclient_mock.get(vigilance_preview_url(vigi_id, offset), content=MAP)


def geojson_requests(aioclient_mock: AiohttpClientMocker) -> list[str]:
    """Return the URLs of the bulletin files requested so far."""
    return [
        str(url)
        for _, url, _, _ in aioclient_mock.mock_calls
        if "/geojson/" in str(url)
    ]


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
