"""Tests for the DPC API client."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import aiohttp
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.dpc.api import (
    CRIT_BULLETIN_URL,
    CRIT_PATTERN_URL,
    VIGI_BULLETIN_URL,
    DpcApiClient,
)
from custom_components.dpc.const import DEFAULT_RADIUS, DEFAULT_SCAN_INTERVAL

from . import (
    CRIT_ID,
    LATITUDE,
    LONGITUDE,
    NAME,
    PUBLICATION_DAY,
    RISK_KINDS,
    mock_dpc_responses,
)


def make_client(
    hass: HomeAssistant, latitude: float = LATITUDE, longitude: float = LONGITUDE
) -> DpcApiClient:
    """Return an API client using the mocked Home Assistant HTTP session."""
    return DpcApiClient(
        NAME,
        latitude,
        longitude,
        "",
        DEFAULT_RADIUS,
        async_get_clientsession(hass),
        timedelta(minutes=DEFAULT_SCAN_INTERVAL),
    )


@pytest.fixture
def client(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> DpcApiClient:
    """Return an API client for the default location."""
    return make_client(hass)


def criticality_expires(data: dict) -> dict[str, datetime]:
    """Return the expiration of each day and risk kind in the criticality data."""
    criticality = data["criticality"]
    return {
        key: criticality[key]["expires"]
        for key in ("today", "tomorrow", *RISK_KINDS)
        if criticality.get(key)
    }


def expected_expires(
    today: datetime, tomorrow: datetime | None = None
) -> dict[str, datetime]:
    """Return the expected expiration of each day and risk kind."""
    expected = {"today": today}
    expected |= {kind: today for kind in RISK_KINDS if kind.endswith("_oggi")}
    if tomorrow is not None:
        expected["tomorrow"] = tomorrow
        expected |= {kind: tomorrow for kind in RISK_KINDS if kind.endswith("_domani")}
    return expected


# The criticality bulletin covers "fino alle 24.00 del giorno di emissione (oggi) e
# nelle 24 ore del giorno seguente (domani)" (pcm-dpc/DPC-Bollettini-Criticita-
# Idrogeologica-Idraulica), so each day expires at the midnight that ends it.


@pytest.mark.usefixtures("mock_dpc")
async def test_expires_on_publication_day(client: DpcApiClient) -> None:
    """Test the expiration of the bulletin issued on 2026-11-14 on that day."""
    data = await client.async_get_data()

    assert criticality_expires(data) == expected_expires(
        today=datetime(2026, 11, 15), tomorrow=datetime(2026, 11, 16)
    )


@pytest.mark.usefixtures("mock_dpc")
async def test_expires_after_midnight(
    client: DpcApiClient, freezer: FrozenDateTimeFactory
) -> None:
    """Test that tomorrow moves to today at midnight and keeps its expiration."""
    await client.async_get_data()

    freezer.move_to("2026-11-15 00:10:00")
    data = await client.async_get_data()

    assert criticality_expires(data) == expected_expires(today=datetime(2026, 11, 16))


async def test_expires_when_started_before_the_new_bulletin(
    client: DpcApiClient,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a start in the morning, when the latest bulletin is from yesterday."""
    freezer.move_to("2026-11-15 08:00:00")
    mock_dpc_responses(aioclient_mock)

    data = await client.async_get_data()

    requested = {str(call[1]) for call in aioclient_mock.mock_calls}
    assert CRIT_PATTERN_URL.format(CRIT_ID, "today") not in requested
    assert criticality_expires(data) == expected_expires(today=datetime(2026, 11, 16))


@pytest.mark.usefixtures("mock_dpc")
async def test_expires_with_the_next_bulletin(
    client: DpcApiClient,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that the next day's bulletin replaces the previous one."""
    await client.async_get_data()

    aioclient_mock.clear_requests()
    mock_dpc_responses(aioclient_mock, crit_id="20261115_1500", vigi_id="20261115")
    freezer.move_to("2026-11-15 15:30:00")
    data = await client.async_get_data()

    assert data["criticality"]["id"] == "20261115_1500"
    assert criticality_expires(data) == expected_expires(
        today=datetime(2026, 11, 16), tomorrow=datetime(2026, 11, 17)
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "Assenza di fenomeni significativi prevedibili / NESSUNA ALLERTA",
            {
                "info": "Assenza di fenomeni significativi prevedibili",
                "alert": "NESSUNA ALLERTA",
                "level": 1,
            },
        ),
        (
            "Ordinaria / ALLERTA GIALLA",
            {"info": "Ordinaria", "alert": "ALLERTA GIALLA", "level": 2},
        ),
        (
            "Moderata per rischio idrogeologico / ALLERTA ARANCIONE",
            {
                "info": "Moderata per rischio idrogeologico",
                "alert": "ALLERTA ARANCIONE",
                "level": 3,
            },
        ),
        (
            "Elevata / ALLERTA ROSSA",
            {"info": "Elevata", "alert": "ALLERTA ROSSA", "level": 4},
        ),
        ("Senza allerta", {"info": "Senza allerta", "alert": "", "level": 0}),
        (None, {"info": "", "alert": "", "level": 0}),
    ],
)
def test_get_info_level(value: str | None, expected: dict) -> None:
    """Test the parsing of a DPC criticality value."""
    assert DpcApiClient.get_info_level(value) == expected


@pytest.mark.parametrize(
    ("latitude", "longitude", "expected"),
    [(LATITUDE, LONGITUDE, True), (48.8566, 2.3522, False)],
)
async def test_validate_coordinates(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    latitude: float,
    longitude: float,
    expected: bool,
) -> None:
    """Test the validation of coordinates against the DPC alert zones."""
    freezer.move_to(PUBLICATION_DAY)
    mock_dpc_responses(aioclient_mock)

    assert (
        await make_client(hass, latitude, longitude).async_validate_coordinates()
        is expected
    )


async def test_validate_coordinates_when_dpc_is_unreachable(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test that the validation is inconclusive when DPC is unreachable."""
    aioclient_mock.get(CRIT_BULLETIN_URL, exc=aiohttp.ClientError)
    aioclient_mock.get(VIGI_BULLETIN_URL, exc=aiohttp.ClientError)

    assert await make_client(hass).async_validate_coordinates() is None


@pytest.mark.parametrize("exception", [TimeoutError, aiohttp.ClientError])
async def test_api_fetch_error(
    client: DpcApiClient, aioclient_mock: AiohttpClientMocker, exception: type
) -> None:
    """Test that a failed request returns no data."""
    aioclient_mock.get(CRIT_BULLETIN_URL, exc=exception)

    assert await client.api_fetch(CRIT_BULLETIN_URL) == {}


async def test_api_fetch_cancelled(
    client: DpcApiClient, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test that a cancelled request is not swallowed."""
    aioclient_mock.get(CRIT_BULLETIN_URL, exc=asyncio.CancelledError)

    with pytest.raises(asyncio.CancelledError):
        await client.api_fetch(CRIT_BULLETIN_URL)
