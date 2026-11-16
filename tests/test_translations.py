"""Tests for the translations: the texts of aiodpc, in the six languages."""

from __future__ import annotations

from typing import Any

from aiodpc.i18n import Language
import pytest

from scripts.translations import FILES, STRINGS, dpc_texts, merged, read


def paths(texts: dict[str, Any], prefix: str = "") -> set[str]:
    """Return the path of every text of a translation file."""
    return {
        path
        for key, value in texts.items()
        for path in (
            paths(value, f"{prefix}{key}.")
            if isinstance(value, dict)
            else {f"{prefix}{key}"}
        )
    }


@pytest.mark.parametrize("language", list(Language))
def test_texts_of_aiodpc(language: Language) -> None:
    """Test that the translations have the texts of aiodpc, and only them.

    After a change of the aiodpc requirement, run python -m scripts.translations.
    """
    texts = read(FILES[language])

    assert merged(texts, dpc_texts(language)) == texts


def test_strings_are_the_english_texts() -> None:
    """Test that strings.json, the source of the texts, is the English file."""
    assert read(STRINGS) == read(FILES[Language.ENGLISH])


@pytest.mark.parametrize("language", list(Language))
def test_every_text_in_every_language(language: Language) -> None:
    """Test that each language has the texts of English, and no other."""
    assert paths(read(FILES[language])) == paths(read(STRINGS))


def test_texts_of_the_states() -> None:
    """Test some texts, as aiodpc writes them: DPC's own in Italian."""
    italian = dpc_texts(Language.ITALIAN)["entity"]
    portuguese = dpc_texts(Language.BRAZILIAN_PORTUGUESE)["entity"]

    assert (
        italian["sensor"]["criticality"]["state"]["moderate_hydrogeological"]
        == "Moderata per rischio idrogeologico"
    )
    assert portuguese["sensor"]["highest_alert"]["state"]["1"] == "Sem alerta"
    directions = portuguese["geo_location"]["wind"]["state_attributes"]["direction"]
    assert directions["state"]["wnw"] == "ONO"
