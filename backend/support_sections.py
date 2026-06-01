"""Support / Senior Member taxonomy — the *non-flight* duty assignments.

Some encampment participants don't belong to a cadet flight (alpha–foxtrot)
— they staff a support section (Logistics, Comms, Public Affairs, …) or sit
in senior leadership (Commander, DCP, Superintendent, …).

Previously the roster rendered them as "Unassigned / Waitlist" because their
`flight` field was empty. That was a UX bug — these people are intentionally
non-flight. This module is the single source of truth for:

  * Which UserRoles count as "support cadre" vs "support senior staff" vs
    "senior member".
  * What value goes in `participant.squadron` and `participant.flight` for
    each group, so the Roster page can render dedicated dropdowns instead
    of the cadet-flight dropdown.
  * The bidirectional mapping between UserRole and the canonical
    `support_section` slug — so changing the roster cell can sync back into
    `user.role` + `user.support_section` (and vice-versa).

See also:
  * `role_groups.py` — concern #6 (permission roles).
  * `models.UserRole` — the enum values referenced here.
"""
from __future__ import annotations

from typing import Optional

from models import UserRole


# ─────────────────────────────────────────────────────────────────────────
# Squadron buckets for the Roster page UI
# ─────────────────────────────────────────────────────────────────────────

SQUADRON_SUPPORT_CADRE = "support_cadre"
SQUADRON_SUPPORT_SENIOR_STAFF = "support_senior_staff"
SQUADRON_SENIOR_MEMBER = "senior_member"

# Cadet-flight squadrons (CTS = Cadet Training Squadron) — already exist.
SQUADRON_CTS_SLUGS = ("6th_cts", "16th_cts", "21st_cts", "22nd_cts")


# ─────────────────────────────────────────────────────────────────────────
# Support sections — what goes in the "Flight" dropdown for support staff
# ─────────────────────────────────────────────────────────────────────────

SUPPORT_SECTIONS: tuple[tuple[str, str], ...] = (
    ("logistics",       "Logistics"),
    ("communications",  "Communications"),
    ("public_affairs",  "Public Affairs"),
    ("dining",          "Dining"),
    ("health",          "Health"),
    ("plans_programs",  "Plans / Programs"),
    ("training",        "Training"),
    ("finance",         "Finance"),
)
"""Canonical (slug, label) list. The slug is stored on the participant /
user; the label is shown in dropdowns and badges."""

SUPPORT_SECTION_SLUGS: frozenset[str] = frozenset(s for s, _ in SUPPORT_SECTIONS)


def section_label(slug: Optional[str]) -> str:
    """Human label for a section slug. Returns '' if unknown."""
    if not slug:
        return ""
    for s, label in SUPPORT_SECTIONS:
        if s == slug:
            return label
    return slug.replace("_", " ").title()


# ─────────────────────────────────────────────────────────────────────────
# Role → (squadron-bucket, default-section) mapping
# ─────────────────────────────────────────────────────────────────────────

# Senior Member roles — sit outside the flight roster entirely (org-chart
# only). They get squadron=senior_member and no section.
SENIOR_MEMBER_ROLES: frozenset[str] = frozenset({
    UserRole.COMMANDER,
    UserRole.DCP,
    UserRole.EXECUTIVE_STAFF,
    UserRole.TRAINING_OFFICER,
    UserRole.SUPERINTENDENT,
    UserRole.CHIEF_TRAINING_OFFICER,
})

# Support cadre — cadet support staff. squadron=support_cadre + section.
SUPPORT_CADRE_ROLES: frozenset[str] = frozenset({
    UserRole.SUPPORT_LOGISTICS,
    UserRole.SUPPORT_COMMS,
    UserRole.SUPPORT_PA,
    UserRole.SUPPORT_DINING,
    UserRole.SUPPORT_HEALTH,
})

# Support senior staff — senior-member support staff (directorate leads).
# squadron=support_senior_staff + section.
SUPPORT_SENIOR_STAFF_ROLES: frozenset[str] = frozenset({
    UserRole.LOGISTICS,
    UserRole.FINANCE,
    UserRole.PLANS_PROGRAMS,
    UserRole.HEALTH_SERVICES,
    UserRole.DINING_FACILITY,
    UserRole.PUBLIC_AFFAIRS,
    UserRole.STAFF,
})

# Union — every role that should render with the Support / Senior dropdowns
# rather than the cadet-flight dropdown.
NON_FLIGHT_ROLES: frozenset[str] = (
    SENIOR_MEMBER_ROLES | SUPPORT_CADRE_ROLES | SUPPORT_SENIOR_STAFF_ROLES
)


# Forward map: UserRole → support section slug. Roles in SENIOR_MEMBER_ROLES
# return None (they have no section).
_ROLE_TO_SECTION: dict[str, Optional[str]] = {
    # Cadre support
    UserRole.SUPPORT_LOGISTICS: "logistics",
    UserRole.SUPPORT_COMMS:     "communications",
    UserRole.SUPPORT_PA:        "public_affairs",
    UserRole.SUPPORT_DINING:    "dining",
    UserRole.SUPPORT_HEALTH:    "health",
    # Senior staff support
    UserRole.LOGISTICS:         "logistics",
    UserRole.FINANCE:           "finance",
    UserRole.PLANS_PROGRAMS:    "plans_programs",
    UserRole.HEALTH_SERVICES:   "health",
    UserRole.DINING_FACILITY:   "dining",
    UserRole.PUBLIC_AFFAIRS:    "public_affairs",
    UserRole.STAFF:             None,    # catch-all senior staff w/o a specific section
}


# Reverse maps — section + bucket → UserRole. Used when the roster admin
# changes a participant's "Flight" cell and we need to sync the linked
# user's role.
_SECTION_TO_CADRE_ROLE: dict[str, str] = {
    "logistics":      UserRole.SUPPORT_LOGISTICS,
    "communications": UserRole.SUPPORT_COMMS,
    "public_affairs": UserRole.SUPPORT_PA,
    "dining":         UserRole.SUPPORT_DINING,
    "health":         UserRole.SUPPORT_HEALTH,
    # Cadre support has no Plans/Programs/Training/Finance variants today.
}

_SECTION_TO_SENIOR_ROLE: dict[str, str] = {
    "logistics":      UserRole.LOGISTICS,
    "finance":        UserRole.FINANCE,
    "plans_programs": UserRole.PLANS_PROGRAMS,
    "health":         UserRole.HEALTH_SERVICES,
    "dining":         UserRole.DINING_FACILITY,
    "public_affairs": UserRole.PUBLIC_AFFAIRS,
}


# ─────────────────────────────────────────────────────────────────────────
# Public helpers
# ─────────────────────────────────────────────────────────────────────────

def is_non_flight_role(role: Optional[str]) -> bool:
    """True if the participant's linked user role means they should be
    rendered with the Support / Senior Member dropdowns instead of the
    cadet flight dropdown."""
    return role in NON_FLIGHT_ROLES


def is_support_role(role: Optional[str]) -> bool:
    """True if the role belongs to either of the support buckets (cadre
    or senior staff). Excludes pure senior-member leadership."""
    return role in SUPPORT_CADRE_ROLES or role in SUPPORT_SENIOR_STAFF_ROLES


def squadron_bucket_for_role(role: Optional[str]) -> Optional[str]:
    """Return the canonical `participant.squadron` value for a given role,
    or None if the role gets a regular flight squadron (CTS)."""
    if role in SENIOR_MEMBER_ROLES:
        return SQUADRON_SENIOR_MEMBER
    if role in SUPPORT_CADRE_ROLES:
        return SQUADRON_SUPPORT_CADRE
    if role in SUPPORT_SENIOR_STAFF_ROLES:
        return SQUADRON_SUPPORT_SENIOR_STAFF
    return None


def section_for_role(role: Optional[str]) -> Optional[str]:
    """Default support-section slug for a role (used when first linking a
    participant). Senior Member roles return None."""
    return _ROLE_TO_SECTION.get(role)


def role_for_section(section: Optional[str], bucket: Optional[str]) -> Optional[str]:
    """Resolve the UserRole that should be set when the admin picks
    `section` in the Roster page, for a participant in `bucket`
    (`support_cadre` or `support_senior_staff`).

    Returns None when there is no matching role (e.g. picking Training in
    the cadre bucket — there's no `support_training` role today). In that
    case the caller should leave `user.role` alone and only update
    `user.support_section`.
    """
    if not section:
        return None
    if bucket == SQUADRON_SUPPORT_CADRE:
        return _SECTION_TO_CADRE_ROLE.get(section)
    if bucket == SQUADRON_SUPPORT_SENIOR_STAFF:
        return _SECTION_TO_SENIOR_ROLE.get(section)
    return None
