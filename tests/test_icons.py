"""Tests for the icons of the DPC entities, in icons.json."""

from __future__ import annotations

import json
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers.icon import async_get_icons

from custom_components.dpc.const import DOMAIN

STRINGS = Path(__file__).parents[1] / "custom_components" / DOMAIN / "strings.json"


async def test_every_entity_has_an_icon(hass: HomeAssistant) -> None:
    """Test that Home Assistant loads an icon for every translated entity."""
    icons = (await async_get_icons(hass, "entity", integrations={DOMAIN}))[DOMAIN]
    entities = json.loads(STRINGS.read_text(encoding="utf-8"))["entity"]

    for platform, translation_keys in entities.items():
        assert set(icons[platform]) == set(translation_keys), platform


async def test_sensor_icons_follow_the_alert_level(hass: HomeAssistant) -> None:
    """Test that the sensors show a warning from yellow (2) up."""
    icons = (await async_get_icons(hass, "entity", integrations={DOMAIN}))[DOMAIN]

    for translation_key in ("criticality", "vigilance"):
        assert icons["sensor"][translation_key] == {
            "default": "mdi:shield-check",
            "range": {"1": "mdi:shield-check", "2": "mdi:hazard-lights"},
        }
