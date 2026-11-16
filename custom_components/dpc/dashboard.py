"""The DPC Alert dashboard and card, offered by the frontend of Home Assistant.

The dashboard is a strategy (frontend/dpc-dashboard.js): a script the frontend
runs to build the dashboard from the DPC entities, with native cards only. The
card (frontend/dpc-card.js) shows the alert and the precipitation of the days
of a place, with the helpers of the strategy. The integration serves both and
has the frontend load them, so the dashboard is listed under Community
dashboards, and the card in the card picker, as soon as the integration is
installed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from homeassistant.components import frontend

# Recent versions define it in another module of http and re-export it without
# declaring it; importing it from http works in every supported version
from homeassistant.components.http import (  # type: ignore[attr-defined]
    StaticPathConfig,
)
from homeassistant.core import HomeAssistant

from .const import FRONTEND_MODULES, FRONTEND_URL

FRONTEND_DIRECTORY: Final = Path(__file__).parent / "frontend"
"""The modules of the frontend: JavaScript without dependencies or build."""


async def async_offer_the_frontend(hass: HomeAssistant) -> None:
    """Serve the dashboard strategy and the card, and have the frontend load them.

    Only when the frontend runs: without it there is nothing to offer.
    """
    if "frontend" not in hass.config.components:
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig(FRONTEND_URL, str(FRONTEND_DIRECTORY))]
    )
    for module in FRONTEND_MODULES:
        frontend.add_extra_js_url(hass, f"{FRONTEND_URL}/{module}")
