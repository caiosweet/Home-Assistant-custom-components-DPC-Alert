"""Write the texts of the DPC values into the translations of the integration.

The states, the values of the attributes and the names of what DPC defines
(the risks, the days, the bulletins, the precipitation, the phenomena) come
from the data dictionary of aiodpc, ``aiodpc.i18n``, so that the library and
the integration say the same. The other texts, the names only Home Assistant
has, stay as they are in the translation files.

Run it after each change of the aiodpc requirement, in the environment of the
tests; tests/test_translations.py fails until then::

    python -m scripts.translations
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from aiodpc import (
    AlertLevel,
    BulletinKind,
    CompassPoint,
    Criticality,
    PhenomenonCategory,
    PhenomenonType,
    Precipitation,
    RiskType,
)
from aiodpc.i18n import TRANSLATIONS, Language, Translator
from aiodpc.parsers import PHENOMENON_TYPES

from custom_components.dpc.const import RISK_TRANSLATION_KEYS, PlaceDay

COMPONENT: Final = Path(__file__).parents[1] / "custom_components" / "dpc"

STRINGS: Final = COMPONENT / "strings.json"
"""The texts of the integration, in English: the source of the translations."""

FILES: Final = {
    language: COMPONENT / "translations" / f"{language}.json" for language in Language
}
"""The translation file of each language: the languages of aiodpc and of the
integration are the same, with the same tags."""

DEVICE_NAME: Final = "{place} · {day}"
"""The name of the device of a day, e.g. "Milano · Today": the place, then the
day as aiodpc writes it."""

RISK_LEVEL_NAMES: Final = {
    Language.ENGLISH: "{risk} level",
    Language.ITALIAN: "Livello di {risk}",
    Language.BRAZILIAN_PORTUGUESE: "Nível de {risk}",
    Language.FRENCH: "Niveau de {risk}",
    Language.GERMAN: "Warnstufe {risk}",
    Language.SPANISH: "Nivel de {risk}",
}
"""The name of the level of a risk, around the risk as aiodpc writes it within a
sentence ("hydraulic risk")."""


def _capitalized(text: str) -> str:
    """Return a text starting with a capital letter, like the labels of aiodpc."""
    return text[:1].upper() + text[1:]


def _states[ValueT](
    values: dict[str, ValueT], texts: dict[ValueT, str]
) -> dict[str, str]:
    """Return the text of each state, from the state and its value."""
    return {state: texts[value] for state, value in values.items()}


def dpc_texts(language: Language) -> dict[str, Any]:
    """Return the texts of the DPC values in a language, as in a translation file."""
    texts = TRANSLATIONS[language]
    tell = Translator(language)
    alert_levels = _states(
        {str(level): level for level in AlertLevel if level is not AlertLevel.UNKNOWN},
        texts.alert_levels,
    )
    precipitation = _states(
        {
            str(amount): amount
            for amount in Precipitation
            if amount is not Precipitation.UNKNOWN
        },
        texts.precipitation,
    )
    criticalities = {
        str(Criticality.ABSENT): texts.criticalities[Criticality.ABSENT],
        **{
            f"{criticality}_{risk}": texts.criticality_for_risk.format(
                criticality=texts.criticalities[criticality],
                risk=texts.risk_types[risk],
            )
            for criticality in (
                Criticality.ORDINARY,
                Criticality.MODERATE,
                Criticality.HIGH,
            )
            for risk in RiskType
        },
    }
    directions = {
        str(point).lower(): texts.compass_points[point] for point in CompassPoint
    }
    # The levels by their number, as the highest alert and the warning level
    level_numbers = _states(
        {
            str(level.code): level
            for level in AlertLevel
            if level is not AlertLevel.UNKNOWN
        },
        texts.alert_levels,
    )
    return {
        "selector": {
            "days": {"options": {str(day): texts.days[day.day] for day in PlaceDay}},
            # Green, no alert, is no warning level
            "warning_level": {
                "options": {
                    str(level.code): texts.alert_levels[level]
                    for level in AlertLevel
                    if level.is_alert
                }
            },
        },
        "device": {
            str(day): {
                "name": DEVICE_NAME.format(place="{place}", day=texts.days[day.day])
            }
            for day in PlaceDay
        },
        "entity": {
            "binary_sensor": {
                key: {"name": tell(risk)} for risk, key in RISK_TRANSLATION_KEYS.items()
            },
            "sensor": {
                "highest_alert": {"state": level_numbers},
                "highest_precipitation": {
                    "state": _states(
                        {
                            str(amount.code): amount
                            for amount in Precipitation
                            if amount is not Precipitation.UNKNOWN
                        },
                        texts.precipitation,
                    )
                },
                "criticality_bulletin": {"name": tell(BulletinKind.CRITICALITY)},
                "vigilance_bulletin": {"name": tell(BulletinKind.VIGILANCE)},
                "alert": {
                    "state": alert_levels,
                    "state_attributes": {
                        "risks": {"state": {str(risk): tell(risk) for risk in RiskType}}
                    },
                },
                "criticality": {"state": criticalities},
                **{
                    f"{key}_level": {
                        "name": _capitalized(
                            RISK_LEVEL_NAMES[language].format(
                                risk=texts.risk_types[risk]
                            )
                        ),
                        "state": alert_levels,
                    }
                    for risk, key in RISK_TRANSLATION_KEYS.items()
                },
                "precipitation": {
                    "name": tell(PhenomenonCategory.PRECIPITATION),
                    "state": precipitation,
                },
            },
            "geo_location": {
                str(category): {
                    "name": texts.phenomenon,
                    "state_attributes": {
                        "phenomenon": {
                            "state": {
                                str(phenomenon_type): texts.phenomenon_types[
                                    phenomenon_type
                                ]
                                for phenomenon_type in PhenomenonType
                                if PHENOMENON_TYPES[phenomenon_type.code][0] is category
                            }
                        },
                        "direction": {"state": directions},
                    },
                }
                for category in PhenomenonCategory
            },
        },
    }


def merged(texts: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Return translations with new texts, keeping the order and the other keys.

    The texts of the states and of the choices of a list are replaced whole: a
    value aiodpc or the integration no longer has goes.
    """
    result = dict(texts)
    for key, value in new.items():
        if (
            key not in {"state", "options"}
            and isinstance(value, dict)
            and isinstance(result.get(key), dict)
        ):
            result[key] = merged(result[key], value)
        else:
            result[key] = value
    return result


def read(path: Path) -> dict[str, Any]:
    """Return the texts of a translation file."""
    texts: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return texts


def write(path: Path, texts: dict[str, Any]) -> None:
    """Write a translation file, as Home Assistant formats them."""
    path.write_text(
        json.dumps(texts, indent=4, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> None:
    """Write the texts of aiodpc into every translation file."""
    for language, path in FILES.items():
        write(path, merged(read(path), dpc_texts(language)))
    # The source of the texts is the English file
    write(STRINGS, read(FILES[Language.ENGLISH]))


if __name__ == "__main__":
    main()
