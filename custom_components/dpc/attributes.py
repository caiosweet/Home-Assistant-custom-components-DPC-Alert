"""Entity attributes built from the aiodpc models.

They keep the names and values the integration has always had, mostly in Italian
as DPC writes them, so existing automations and templates keep working.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from aiodpc import (
    CRITICALITY_PAGE_URL,
    ROME_TZ,
    VIGILANCE_PAGE_URL,
    CriticalityBulletin,
    CriticalityDay,
    Phenomenon,
    RiskAssessment,
    VigilanceBulletin,
    VigilanceDay,
)
from homeassistant.const import ATTR_ICON

from .const import (
    ALERT_TEXTS,
    ATTR_ALERT,
    ATTR_EXPIRES,
    ATTR_ID,
    ATTR_IMAGE_URL,
    ATTR_INFO,
    ATTR_LAST_UPDATE,
    ATTR_LEVEL,
    ATTR_LINK,
    ATTR_PHENOMENA,
    ATTR_PRECIPITATION,
    ATTR_PUBLICATION_DATE,
    ATTR_RISK,
    ATTR_ZONE_NAME,
    DEFAULT_PHENOMENON_ICON,
    PHENOMENON_CATEGORY_NAMES,
    PHENOMENON_ICONS,
    PRECIPITATION_ICONS,
    PRECIPITATION_TEXTS,
    RISK_ICONS,
    RISK_NAMES,
)
from .coordinator import LatestBulletin


def criticality_attributes(
    latest: LatestBulletin[CriticalityBulletin],
) -> dict[str, Any]:
    """Return the attributes of a criticality bulletin."""
    return {
        ATTR_ID: latest.bulletin.id,
        ATTR_PUBLICATION_DATE: latest.bulletin.published,
        ATTR_LAST_UPDATE: latest.checked_at.isoformat(),
        ATTR_LINK: CRITICALITY_PAGE_URL,
    }


def criticality_day_attributes(day: CriticalityDay) -> dict[str, Any]:
    """Return the attributes of the overall assessment of a day."""
    return {
        ATTR_INFO: day.description,
        ATTR_ALERT: ALERT_TEXTS[day.level],
        ATTR_LEVEL: day.level.value,
        ATTR_IMAGE_URL: day.image_url,
        ATTR_EXPIRES: day.valid_until,
        ATTR_ZONE_NAME: day.zone,
    }


def risk_attributes(risk: RiskAssessment) -> dict[str, Any]:
    """Return the attributes of the assessment of a risk type."""
    return {
        ATTR_RISK: RISK_NAMES[risk.type],
        ATTR_INFO: risk.description,
        ATTR_ALERT: ALERT_TEXTS[risk.level],
        ATTR_LEVEL: risk.level.value,
    }


def risk_event_attributes(risk: RiskAssessment) -> dict[str, Any]:
    """Return the attributes of a risk listed among the events of a day."""
    return risk_attributes(risk) | {ATTR_ICON: RISK_ICONS[risk.type]}


def risk_day_attributes(day: CriticalityDay, risk: RiskAssessment) -> dict[str, Any]:
    """Return the attributes of the assessment of a risk type on a day."""
    return risk_attributes(risk) | {
        ATTR_IMAGE_URL: day.image_url,
        ATTR_EXPIRES: day.valid_until,
        ATTR_ZONE_NAME: day.zone,
    }


def vigilance_attributes(latest: LatestBulletin[VigilanceBulletin]) -> dict[str, Any]:
    """Return the attributes of a vigilance bulletin."""
    return {
        ATTR_ID: latest.bulletin.id,
        ATTR_PUBLICATION_DATE: datetime.combine(
            latest.bulletin.date, time(), tzinfo=ROME_TZ
        ),
        ATTR_LAST_UPDATE: latest.checked_at.isoformat(),
        ATTR_LINK: VIGILANCE_PAGE_URL,
    }


def vigilance_day_attributes(day: VigilanceDay) -> dict[str, Any]:
    """Return the attributes of the expected weather on a day."""
    return {
        ATTR_ICON: PRECIPITATION_ICONS[day.precipitation],
        ATTR_IMAGE_URL: day.image_url,
        ATTR_LEVEL: day.precipitation.value,
        ATTR_PRECIPITATION: PRECIPITATION_TEXTS[day.precipitation],
        ATTR_ZONE_NAME: day.zone,
        ATTR_PHENOMENA: [
            phenomenon_attributes(phenomenon)
            for phenomenon in day.phenomena
            # Codes unknown to aiodpc have no category: they were never listed
            if phenomenon.category is not None
        ],
    }


def phenomenon_attributes(phenomenon: Phenomenon) -> dict[str, Any]:
    """Return the attributes of a weather phenomenon of a known category."""
    assert phenomenon.category is not None
    return {
        "id": phenomenon.bulletin_id,
        "date": phenomenon.bulletin_date,
        "id_event": phenomenon.code,
        "event": PHENOMENON_CATEGORY_NAMES[phenomenon.category],
        "value": phenomenon.description,
        "latitude": phenomenon.latitude,
        "longitude": phenomenon.longitude,
        "distance": phenomenon.distance_km,
        "direction": phenomenon.direction,
        "degrees": phenomenon.degrees,
        ATTR_ICON: PHENOMENON_ICONS.get(phenomenon.code, DEFAULT_PHENOMENON_ICON),
    }
