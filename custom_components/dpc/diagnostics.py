"""Provides diagnostics for dpc."""

from __future__ import annotations

import dataclasses
from typing import Any

from attr import asdict
from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from .const import CONF_MUNICIPALITY

TO_REDACT = {
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MUNICIPALITY,
    "identifiers",
    "unique_id",
}


def _without_coordinates(data: Any, coordinates: str) -> Any:
    """Return data with lists for tuples, and the coordinates text redacted.

    The binary sensors of the places added with 2026.2.0 have entity IDs made
    of the coordinates, e.g. binary_sensor.41_900000_12_500000_idraulico_oggi.
    """
    if isinstance(data, str):
        return data.replace(coordinates, "**REDACTED**")
    if isinstance(data, dict):
        return {
            key: _without_coordinates(value, coordinates) for key, value in data.items()
        }
    if isinstance(data, list | tuple):
        return [_without_coordinates(value, coordinates) for value in data]
    return data


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = config_entry.runtime_data
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

    diagnostics = {
        "entry": config_entry.as_dict(),
        "coordinator_data": {
            "coordinator last update success": coordinator.last_update_success,
            # Redacted below: the positions of the phenomena, with their distance
            # and direction from the place, would reveal where the place is
            "data": dataclasses.asdict(coordinator.data),
        },
        "devices": devices,
    }
    coordinates = slugify(
        f"{config_entry.data[CONF_LATITUDE]:.6f}_{config_entry.data[CONF_LONGITUDE]:.6f}"
    )
    # async_redact_data only goes through dicts and lists
    return async_redact_data(_without_coordinates(diagnostics, coordinates), TO_REDACT)
