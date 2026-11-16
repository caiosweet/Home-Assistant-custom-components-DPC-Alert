"""
Custom integration to integrate DPC-Alert with Home Assistant.

For more details about this integration, please refer to
https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert
"""

from __future__ import annotations

from functools import partial

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType

from .bulletins import Place, async_get_bulletins
from .const import (
    CONF_DAYS,
    CONF_MUNICIPALITY,
    DAYS_BEFORE_THE_OPTION,
    DOMAIN,
    LOGGER,
    PLATFORMS,
    STARTUP_MESSAGE,
    PlaceDay,
    platform_shown,
)
from .coordinator import DpcConfigEntry, DpcDataUpdateCoordinator
from .dashboard import async_offer_the_frontend
from .entity import async_set_up_the_devices

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Offer the DPC Alert dashboard and card; the places are set up from the UI only."""
    del config
    LOGGER.info(STARTUP_MESSAGE)
    await async_offer_the_frontend(hass)
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
    coordinator.place_device = async_set_up_the_devices(hass, entry, coordinator.days)

    coordinator.platforms = [
        platform for platform in PLATFORMS if platform_shown(entry.options, platform)
    ]
    async_remove_hidden_entities(hass, entry, coordinator.platforms)
    await hass.config_entries.async_forward_entry_setups(entry, coordinator.platforms)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


@callback
def async_remove_hidden_entities(
    hass: HomeAssistant, entry: ConfigEntry, platforms: list[str]
) -> None:
    """Remove the entities of the kinds the options no longer show.

    As the devices of the days no longer shown, they go rather than stay
    unavailable; showing their kind again creates them anew.
    """
    registry = er.async_get(hass)
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if registry_entry.domain not in platforms:
            registry.async_remove(registry_entry.entity_id)


async def async_update_options(hass: HomeAssistant, entry: DpcConfigEntry) -> None:
    """Reload a place when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: DpcConfigEntry) -> bool:
    """Unload a place, with the platforms it was set up with."""
    return await hass.config_entries.async_unload_platforms(
        entry, entry.runtime_data.platforms
    )


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an old config entry, one version after the other.

    Each step updates the entry in place, so an entry of version 1 goes
    through all of them.
    """
    LOGGER.info(
        "Migrating DPC entry from version %s.%s", entry.version, entry.minor_version
    )
    if entry.version == 1:
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, CONF_MUNICIPALITY: ""}, version=2
        )
    if entry.version == 2 and entry.minor_version < 2:
        registry = er.async_get(hass)
        days = list(DAYS_BEFORE_THE_OPTION)
        # The betas of 2026.11.1 had the precipitation of the day after tomorrow
        if registry.async_get_entity_id(
            Platform.SENSOR,
            DOMAIN,
            f"{entry.unique_id}-precipitation_{PlaceDay.AFTER_TOMORROW}",
        ):
            days.append(PlaceDay.AFTER_TOMORROW)
        options = {**entry.options, CONF_DAYS: days}
        # The phenomena are off by default: the betas had them on
        options.setdefault(
            Platform.GEO_LOCATION,
            any(
                registry_entry.domain == Platform.GEO_LOCATION
                for registry_entry in er.async_entries_for_config_entry(
                    registry, entry.entry_id
                )
            ),
        )
        hass.config_entries.async_update_entry(entry, options=options, minor_version=2)
    return True
