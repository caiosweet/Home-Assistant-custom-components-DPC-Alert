"""
Custom integration to integrate DPC-Alert with Home Assistant.

For more details about this integration, please refer to
https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert
"""

from __future__ import annotations

import asyncio
from functools import partial

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .bulletins import Place, async_get_bulletins
from .const import CONF_MUNICIPALITY, DOMAIN, LOGGER, PLATFORMS, STARTUP_MESSAGE
from .coordinator import DpcDataUpdateCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up this integration using YAML is not supported."""
    del config
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        LOGGER.info(STARTUP_MESSAGE)

    # The places share the downloads: a bulletin is the same file for all of them
    bulletins = async_get_bulletins(hass)
    bulletins.add_place(entry.entry_id, Place.of(entry))
    entry.async_on_unload(partial(bulletins.remove_place, entry.entry_id))

    coordinator = DpcDataUpdateCoordinator(hass, entry, bulletins)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        LOGGER.warning(
            "Initial update failed for %s; entities will be unavailable until the next refresh",
            entry.title,
        )

    hass.data[DOMAIN][entry.entry_id] = coordinator

    for platform in PLATFORMS:
        if entry.options.get(platform, True):
            coordinator.platforms.append(platform)
            await hass.config_entries.async_forward_entry_setups(entry, [platform])

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
                if platform in coordinator.platforms
            ]
        )
    )
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an old config entry."""
    LOGGER.info("Migrating DPC entry from Version %s", entry.version)
    if entry.version == 1:
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, CONF_MUNICIPALITY: ""}, version=2
        )

    return True
