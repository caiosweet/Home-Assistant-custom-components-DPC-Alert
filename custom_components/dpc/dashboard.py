"""The DPC Alert dashboard, offered in the Add dashboard dialog of Home Assistant.

The dashboard is a strategy (frontend/dpc-dashboard.js): a script the frontend
runs to build the dashboard from the DPC entities, with native cards only. The
integration serves it and has the frontend load it, so it is listed under
Community dashboards as soon as the integration is installed.
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

from .const import DASHBOARD_MODULE_URL, VERSION

DASHBOARD_MODULE: Final = Path(__file__).parent / "frontend" / "dpc-dashboard.js"
"""The dashboard strategy, a JavaScript module without dependencies."""


async def async_offer_the_dashboard(hass: HomeAssistant) -> None:
    """Serve the dashboard strategy and have the frontend load it.

    Only when the frontend runs: without it there is no dashboard to offer.
    """
    if "frontend" not in hass.config.components:
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig(DASHBOARD_MODULE_URL, str(DASHBOARD_MODULE))]
    )
    # The browsers keep the module in their cache: the version in the URL makes
    # them load it again when the integration is updated
    frontend.add_extra_js_url(hass, f"{DASHBOARD_MODULE_URL}?v={VERSION}")
