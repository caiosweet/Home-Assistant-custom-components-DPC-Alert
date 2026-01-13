"""Provides diagnostics for dpc."""

from __future__ import annotations

from typing import Any

from attr import asdict
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_MUNICIPALITY, DOMAIN

TO_REDACT = {
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MUNICIPALITY,
    "identifiers",
    "unique_id",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    devices = []

    registry_devices = dr.async_entries_for_config_entry(
        device_registry, config_entry.entry_id
    )

    for device in registry_devices:
        entities = []

        registry_entities = er.async_entries_for_device(
            entity_registry,
            device_id=device.id,
            include_disabled_entities=True,
        )

        for entity in registry_entities:
            state_dict = None
            if state := hass.states.get(entity.entity_id):
                state_dict = dict(state.as_dict())
                state_dict.pop("context", None)

            entities.append({"entry": asdict(entity), "state": state_dict})

        devices.append({"device": asdict(device), "entities": entities})

    return {
        "entry": async_redact_data(config_entry.as_dict(), TO_REDACT),
        "coordinator_data": {
            "coordinator last update success": coordinator.last_update_success,
            "data": coordinator.data,
        },
        "devices": async_redact_data(devices, TO_REDACT),
    }
