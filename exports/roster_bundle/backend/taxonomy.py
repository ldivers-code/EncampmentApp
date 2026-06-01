"""Public read-only taxonomy endpoints used by the frontend to render
support-section dropdowns and decide which squadron/flight options to show.
"""
from __future__ import annotations

from database import api_router
from permissions import get_current_user
from fastapi import Depends

from support_sections import (
    SUPPORT_SECTIONS,
    SQUADRON_SUPPORT_CADRE,
    SQUADRON_SUPPORT_SENIOR_STAFF,
    SQUADRON_SENIOR_MEMBER,
    SQUADRON_CTS_SLUGS,
    SENIOR_MEMBER_ROLES,
    SUPPORT_CADRE_ROLES,
    SUPPORT_SENIOR_STAFF_ROLES,
)


@api_router.get("/taxonomy/support")
def get_support_taxonomy(_user: dict = Depends(get_current_user)):
    """Return the canonical taxonomy used to render the Roster page
    dropdowns for non-flight participants. Auth required so anonymous
    clients don't enumerate roles, but no role gating beyond that."""
    return {
        "support_sections": [
            {"slug": slug, "label": label}
            for slug, label in SUPPORT_SECTIONS
        ],
        "squadrons": {
            "cadet_flight": [
                {"slug": s, "label": s.replace("_", " ").upper()}
                for s in SQUADRON_CTS_SLUGS
            ],
            "support_cadre":         {"slug": SQUADRON_SUPPORT_CADRE,         "label": "Support — Cadre"},
            "support_senior_staff":  {"slug": SQUADRON_SUPPORT_SENIOR_STAFF,  "label": "Support — Senior Staff"},
            "senior_member":         {"slug": SQUADRON_SENIOR_MEMBER,         "label": "Senior Member"},
        },
        "role_groups": {
            "senior_member":        sorted(SENIOR_MEMBER_ROLES),
            "support_cadre":        sorted(SUPPORT_CADRE_ROLES),
            "support_senior_staff": sorted(SUPPORT_SENIOR_STAFF_ROLES),
        },
    }
