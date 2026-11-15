"""
Custom integration to integrate DPC-Alert with Home Assistant.

For more details about this integration, please refer to
https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert
"""

from __future__ import annotations

from functools import partial

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .bulletins import Place, async_get_bulletins
from .const import CONF_MUNICIPALITY, DOMAIN, LOGGER, PLATFORMS, STARTUP_MESSAGE
from .coordinator import DpcConfigEntry, DpcDataUpdateCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up this integration using YAML is not supported."""
    del config
    LOGGER.info(STARTUP_MESSAGE)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: DpcConfigEntry) -> bool:
    """Set up a place.

    Raises ConfigEntryNotReady while DPC cannot be reached, so that Home
    Assistant retries soon, and ConfigEntryError when DPC does not cover the
    place.
    """
    # The places share the downloads: a bulletin is the same file for all of them
    bulletins = async_get_bulletins(hass)
    bulletins.add_place(entry.entry_id, Place.of(entry))
    entry.async_on_unload(partial(bulletins.remove_place, entry.entry_id))

    coordinator = DpcDataUpdateCoordinator(hass, entry, bulletins)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    coordinator.platforms = [
        platform for platform in PLATFORMS if entry.options.get(platform, True)
    ]
    await hass.config_entries.async_forward_entry_setups(entry, coordinator.platforms)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass: HomeAssistant, entry: DpcConfigEntry) -> None:
    """Reload a place when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: DpcConfigEntry) -> bool:
    """Unload a place, with the platforms it was set up with."""
    return await hass.config_entries.async_unload_platforms(
        entry, entry.runtime_data.platforms
    )


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an old config entry."""
    LOGGER.info("Migrating DPC entry from Version %s", entry.version)
    if entry.version == 1:
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, CONF_MUNICIPALITY: ""}, version=2
        )

    return True
