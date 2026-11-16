"""Tests for the icons of the DPC entities, in icons.json."""

from __future__ import annotations

import json
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers.icon import async_get_icons

from custom_components.dpc.const import DOMAIN

STRINGS = Path(__file__).parents[1] / "custom_components" / DOMAIN / "strings.json"
RISKS = ("hydraulic", "thunderstorms", "hydrogeological")


async def test_every_entity_has_an_icon(hass: HomeAssistant) -> None:
    """Test that Home Assistant loads an icon for every translated entity."""
    icons = (await async_get_icons(hass, "entity", integrations={DOMAIN}))[DOMAIN]
    entities = json.loads(STRINGS.read_text(encoding="utf-8"))["entity"]

    for platform, translation_keys in entities.items():
        assert set(icons[platform]) == set(translation_keys), platform


async def test_sensor_icons_follow_the_alert_level(hass: HomeAssistant) -> None:
    """Test that the alerts show a warning from yellow up, whatever their states."""
    icons = (await async_get_icons(hass, "entity", integrations={DOMAIN}))[DOMAIN]
    sensor = icons["sensor"]
    by_level = list(sensor["alert"]["state"].values())

    assert list(sensor["alert"]["state"]) == ["green", "yellow", "orange", "red"]
    assert list(sensor["highest_alert"]["state"].values()) == by_level
    criticality = sensor["criticality"]["state"]
    assert criticality["absent"] == by_level[0]
    assert {criticality[f"ordinary_{risk}"] for risk in RISKS} == {by_level[1]}
    assert {criticality[f"moderate_{risk}"] for risk in RISKS} == {by_level[2]}
    assert {criticality[f"high_{risk}"] for risk in RISKS} == {by_level[3]}
    assert list(sensor["highest_precipitation"]["state"].values()) == list(
        sensor["precipitation"]["state"].values()
    )
