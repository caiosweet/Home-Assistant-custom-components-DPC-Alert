"""
Custom integration to integrate DPC-Alert with Home Assistant.

For more details about this integration, please refer to
https://github.com/caiosweet/Home-Assistant-custom-components-DPC-Alert
"""
from __future__ import annotations

import asyncio
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    CONF_RADIUS,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import event
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DpcApiClient, DpcApiException
from .const import (
    CONF_MUNICIPALITY,
    DEFAULT_RADIUS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    PLATFORMS,
    STARTUP_MESSAGE,
)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        LOGGER.info(STARTUP_MESSAGE)

    location_name = entry.data.get(CONF_NAME)
    latitude = entry.data.get(CONF_LATITUDE)
    longitude = entry.data.get(CONF_LONGITUDE)
    municipality = entry.options.get(CONF_MUNICIPALITY)
    update_interval = timedelta(
        minutes=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    radius = entry.options.get(CONF_RADIUS, DEFAULT_RADIUS)
    session = async_get_clientsession(hass)
    client = DpcApiClient(
        location_name, latitude, longitude, municipality, radius, session, update_interval
    )

    coordinator = DpcDataUpdateCoordinator(hass, client=client, update_interval=update_interval)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    for platform in PLATFORMS:
        if entry.options.get(platform, True):
            coordinator.platforms.append(platform)
            await hass.config_entries.async_forward_entry_setups(entry, [platform])

    if not entry.update_listeners:
        entry.add_update_listener(async_reload_entry)

    return True


class DpcDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, client: DpcApiClient, update_interval) -> None:
        """Initialize."""
        self.api = client
        self.platforms = []
        super().__init__(hass, LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.api.async_get_data()
        except (DpcApiException, Exception) as exception:
            raise UpdateFailed(exception) from exception
        finally:
            LOGGER.debug("[%s] COORDINATOR DATA: %s", self.api._name, self.api._data)

            if self.api._pending_full_update:
                LOGGER.warning("Pending full update, i will retry in 10 min")
                event.async_call_later(
                    self.hass,
                    600,
                    self._async_request_refresh_later,
                )

    async def _async_request_refresh_later(self, _now):
        """Request async_request_refresh."""
        await self.async_request_refresh()


async def async_update_options(hass, config_entry):
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


async def async_migrate_entry(hass, entry):
    LOGGER.info("Migrating DPC entry from Version %s", entry.version)
    if entry.version == 1:
        entry.options = dict(entry.options)
        entry.options[CONF_MUNICIPALITY] = ""
        entry.version = 2

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
