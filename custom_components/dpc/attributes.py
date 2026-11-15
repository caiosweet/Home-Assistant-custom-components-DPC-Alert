"""Attributes of the alert, vigilance and binary sensors, built from aiodpc.

They keep the names and values these sensors have always had, mostly in
Italian as DPC writes them, so existing automations and templates keep
working. The sensors of each day, the maps and the phenomena have their own,
translated attributes.
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
    RiskAssessment,
    VigilanceBulletin,
)

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
    ATTR_PUBLICATION_DATE,
    ATTR_RISK,
    ATTR_ZONE_NAME,
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


def risk_day_attributes(day: CriticalityDay, risk: RiskAssessment) -> dict[str, Any]:
    """Return the attributes of the assessment of a risk type on a day."""
    return {
        ATTR_RISK: RISK_NAMES[risk.type],
        ATTR_INFO: risk.description,
        ATTR_ALERT: ALERT_TEXTS[risk.level],
        ATTR_LEVEL: risk.level.value,
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
