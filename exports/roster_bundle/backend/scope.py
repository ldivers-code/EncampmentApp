"""Shared visibility / redaction / capability helpers.

This module is the single source of truth for:
  • Which roster rows a user is allowed to read.
  • Which fields on each row must be zeroed-out (redacted) before returning.
  • Capability checks for finance, medical, and full-contact data classes.

All endpoints that return participant data MUST go through these helpers so
the rules are consistent across roster, by-flight, stats, exports, parent
portal, and any future endpoints.

Policy summary (matches the product RBAC spec):
  - Full admin (DCP, Commander, Executive Staff) see everything.
  - Senior staff (STAFF, PLANS_PROGRAMS, HEALTH_SERVICES, FINANCE, EXEC_CADRE) see
    full participant fields appropriate to their directorate (medical/finance
    additionally gated on capability).
  - Cadre cadets see only their assigned flight; sensitive PII redacted.
  - Exec Cadre cadets see roster but NO senior-staff/admin endpoints (handled at
    require_role). No additional contact/payment exposure beyond cadre.
  - Students see roster only as redacted (no contact, no payment, no PII).
  - Parents see ONLY their linked cadet.
  - Medical (`hs_*`) is gated on `health_view`/`health_full` permissions.
  - Finance is gated on FINANCE/COMMANDER/EXECUTIVE_STAFF roles.
"""
from __future__ import annotations

from typing import Iterable, Optional
from fastapi import HTTPException

from models import UserRole

# ─────────────────────────────────────────────────────────────────────────────
# Role groups
# ─────────────────────────────────────────────────────────────────────────────

FULL_ADMIN_ROLES = {
    UserRole.DCP,
    UserRole.COMMANDER,
    UserRole.EXECUTIVE_STAFF,
}

# Senior staff & specialised directorates that should see full participant
# fields. Cadre / Exec Cadre / Student / Parent are deliberately NOT in this
# list — they get the redacted view.
PRIVILEGED_VIEWING_ROLES = FULL_ADMIN_ROLES | {
    UserRole.STAFF,
    UserRole.PLANS_PROGRAMS,
    UserRole.FINANCE,
    UserRole.HEALTH_SERVICES,
    UserRole.LOGISTICS,
    UserRole.SUPPORT_LOGISTICS,
    UserRole.SUPPORT_HEALTH,
    UserRole.TRAINING_OFFICER,
    UserRole.SQUADRON_COMMANDER,
}

FINANCE_ROLES = {
    UserRole.COMMANDER,
    UserRole.EXECUTIVE_STAFF,
    UserRole.FINANCE,
    UserRole.DCP,
}

HEALTH_ROLES = {
    UserRole.DCP,
    UserRole.COMMANDER,
    UserRole.EXECUTIVE_STAFF,
    UserRole.HEALTH_SERVICES,
    UserRole.SUPPORT_HEALTH,
}

# Role <-> participant flight scope mapping
SQUADRON_FLIGHTS_MAP = {
    "6th_cts":  ["alpha", "bravo"],
    "21st_cts": ["charlie", "delta"],
    "22nd_cts": ["echo", "foxtrot"],
}

FLIGHT_TO_SQUADRON_MAP = {
    "alpha": "6th_cts", "bravo": "6th_cts",
    "charlie": "21st_cts", "delta": "21st_cts",
    "echo": "22nd_cts", "foxtrot": "22nd_cts",
}


# ─────────────────────────────────────────────────────────────────────────────
# Capability checks
# ─────────────────────────────────────────────────────────────────────────────

def is_full_admin(user: dict) -> bool:
    return user.get("role") in FULL_ADMIN_ROLES


def can_view_full_participant(user: dict) -> bool:
    """Is this user allowed to see every roster field (incl. address, parent
    contact, shirt size, etc.)?"""
    return user.get("role") in PRIVILEGED_VIEWING_ROLES


def can_view_finance(user: dict) -> bool:
    """Allowed to see payment / amount_paid / approval status."""
    return user.get("role") in FINANCE_ROLES


# Phase 5: semantic alias — used at call sites that talk about "payment"
# specifically (vs the more general "finance / budget" concept).
def can_view_payment(user: dict) -> bool:
    return can_view_finance(user)


def can_view_health(user: dict) -> bool:
    """Allowed to read medical roster / allergies / diary etc."""
    if user.get("role") in HEALTH_ROLES:
        return True
    perms = user.get("permissions") or {}
    return bool(perms.get("health_view") or perms.get("health_full") or perms.get("page_health"))


def can_view_full_health(user: dict) -> bool:
    """Allowed to read full medical detail (vs. summary)."""
    if user.get("role") in (UserRole.HEALTH_SERVICES, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.DCP):
        return True
    perms = user.get("permissions") or {}
    return bool(perms.get("health_full"))


# Phase 5: semantic alias — used at call sites that talk about "medical" specifically.
def can_view_medical(user: dict) -> bool:
    return can_view_health(user)


def can_view_full_medical(user: dict) -> bool:
    return can_view_full_health(user)


def can_view_contact_pii(user: dict) -> bool:
    """Allowed to see address, parent contact, emergency contact, etc.
    Same set as can_view_full_participant — kept as a separate name so the
    intent is documented at every call site."""
    return can_view_full_participant(user)


def can_view_notes(user: dict) -> bool:
    """Allowed to see free-text notes / comments. Same set as full participant."""
    return can_view_full_participant(user)


# ─────────────────────────────────────────────────────────────────────────────
# Visibility filter — which rows
# ─────────────────────────────────────────────────────────────────────────────

def apply_participant_visibility(query: dict, user: dict) -> None:
    """Mutates `query` in place so the caller's roster scan only returns rows
    the user is allowed to see.

    - Parents are rejected outright (use parent endpoints).
    - Squadron Commander / Training Officer scope to their squadron's two flights.
    - Cadre / Exec Cadre scope to their assigned flight.
    - Everyone else (incl. full admins) is unscoped.

    Raises 403 for parents.
    """
    role = user.get("role")
    user_flight = (user.get("flight") or "").lower()
    user_squadron = (user.get("squadron") or "").lower()

    if role == UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Parents do not have roster access")

    if role in (UserRole.SQUADRON_COMMANDER, UserRole.TRAINING_OFFICER):
        sq = user_squadron or FLIGHT_TO_SQUADRON_MAP.get(user_flight, "")
        if sq and sq in SQUADRON_FLIGHTS_MAP:
            query["flight"] = {"$in": SQUADRON_FLIGHTS_MAP[sq]}
        return

    if role in (UserRole.CADRE, UserRole.EXEC_CADRE) and user_flight:
        query["flight"] = user_flight


# Phase 5 helper: are the requested flight(s) visible to this user?
# Returns the (possibly narrowed) list of flights the caller is allowed to
# see, or raises 403 when the request is completely out of scope.
def visible_flights_for(user: dict, requested_flights: Iterable[str]) -> list[str]:
    """Restrict a requested flight set to the caller's visibility scope.

    * Full admin / senior staff: returns the requested list unchanged.
    * Squadron Commander / Training Officer: intersect with their squadron's flights.
    * Cadre / Exec Cadre: intersect with their assigned flight.
    * Parent: 403 (matches apply_participant_visibility).

    Raises 403 if the intersection is empty — i.e. the caller asked for a
    flight they have no business seeing.
    """
    role = user.get("role")
    if role == UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Parents do not have roster access")

    requested = [f.lower() for f in requested_flights if f]
    if not requested:
        return []

    user_flight = (user.get("flight") or "").lower()
    user_squadron = (user.get("squadron") or "").lower()

    # Phase 5: Squadron Commander / Training Officer are PRIVILEGED viewers
    # (full PII within their squadron) BUT still flight-scoped at the row
    # level. Check their squadron scope BEFORE the broad full-participant
    # short-circuit so they can't reach cross-squadron flights.
    if role in (UserRole.SQUADRON_COMMANDER, UserRole.TRAINING_OFFICER):
        sq = user_squadron or FLIGHT_TO_SQUADRON_MAP.get(user_flight, "")
        allowed = set(SQUADRON_FLIGHTS_MAP.get(sq, []))
        narrowed = [f for f in requested if f in allowed]
        if not narrowed:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view this flight's roster.",
            )
        return narrowed

    # Full admin / senior staff (non-squadron-scoped): see the requested list.
    if can_view_full_participant(user):
        return requested

    if role in (UserRole.CADRE, UserRole.EXEC_CADRE) and user_flight:
        allowed = {user_flight}
    else:
        # Student / unscoped cadre / anything else without scope: no flight-roster access.
        allowed = set()

    narrowed = [f for f in requested if f in allowed]
    if not narrowed:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view this flight's roster.",
        )
    return narrowed


# ─────────────────────────────────────────────────────────────────────────────
# Field redaction
# ─────────────────────────────────────────────────────────────────────────────

# Sensitive field groups, by data class.
CONTACT_FIELDS = (
    "address", "city", "state", "zip_code",
    "phone", "cell_phone", "email",
    "cadet_parent_phone", "cadet_parent_email", "cadet_parent_name",
    "emergency_contact", "emergency_phone",
    "unit_cc_name", "unit_cc_email",
)

PAYMENT_FIELDS = (
    "amount_paid", "paid", "paid_in_full",
    "registration_status",
    "unit_approved", "wing_approved", "slotted",
)

PII_FIELDS = (
    "shirt_size", "religious_preference",
)

NOTES_FIELDS = (
    "notes", "comments",
)


# Fields that should be replaced with None (vs False) when redacted, because
# their type is string/number rather than bool.
_NULL_REDACT_FIELDS = {"amount_paid", "registration_status"}


def _redact_payment_value(field: str, current):
    """Return the appropriate redacted value for a payment field, preserving
    the field's type (None for strings/numbers, False for booleans)."""
    if field in _NULL_REDACT_FIELDS:
        return None
    return False


def redact_participant(p: dict, user: dict) -> dict:
    """Return a new dict with sensitive fields zeroed-out based on the
    requesting user's permissions. Full admins / privileged viewing roles get
    everything. Everyone else (cadre, exec_cadre, student, parent, etc.) loses:
      - contact PII
      - payment
      - notes / comments
      - other PII (shirt size etc)
    Parent endpoints intentionally bypass this helper because they pass the
    full doc through a parent-specific projection.
    """
    if can_view_full_participant(user):
        # Full visibility — but still gate finance fields by capability, since
        # logistics/training officer/etc. should not see amount_paid.
        if not can_view_finance(user):
            redacted = dict(p)
            for f in PAYMENT_FIELDS:
                if f in redacted:
                    redacted[f] = _redact_payment_value(f, redacted[f])
            return redacted
        return dict(p)

    # Non-privileged caller: redact everything sensitive.
    redacted = dict(p)
    for f in CONTACT_FIELDS:
        if f in redacted:
            redacted[f] = None
    for f in PAYMENT_FIELDS:
        if f in redacted:
            redacted[f] = _redact_payment_value(f, redacted[f])
    for f in PII_FIELDS:
        if f in redacted:
            redacted[f] = None
    for f in NOTES_FIELDS:
        if f in redacted:
            redacted[f] = None
    return redacted


def redact_participants(items: Iterable[dict], user: dict) -> list[dict]:
    """Convenience: apply `redact_participant` to a list."""
    return [redact_participant(p, user) for p in items]


# Field lists used by Excel/CSV/PDF exports — the safe (non-redacted-allowed)
# minimum that a non-privileged caller is allowed to export.
SAFE_EXPORT_COLUMNS = (
    "capid", "rank", "last_name", "first_name",
    "unit", "wing", "region",
    "gender", "age", "age_at_event",
    "member_type", "participant_type",
    "squadron", "flight", "position",
)


def export_columns_for(user: dict, requested: Optional[Iterable[str]] = None) -> list[str]:
    """Return the list of columns this user is allowed to export. If `requested`
    is given, the result is the intersection of the user's allowed set and
    `requested`."""
    if can_view_full_participant(user):
        if can_view_finance(user):
            allowed = None  # all
        else:
            allowed = set(requested or [])
            for f in PAYMENT_FIELDS:
                allowed.discard(f)
        if requested is None:
            return list(requested or [])  # caller provides full list elsewhere
        return [c for c in requested if (allowed is None or c in allowed)]
    # Non-privileged: only safe columns
    safe = set(SAFE_EXPORT_COLUMNS)
    if requested is None:
        return list(SAFE_EXPORT_COLUMNS)
    return [c for c in requested if c in safe]


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: shared roster-entry shaper
# ─────────────────────────────────────────────────────────────────────────────

def safe_roster_entry(p: dict, user: dict) -> dict:
    """Build the canonical 'roster row' dict — used by /flights/*/roster,
    /squadrons/*/roster, and by-flight callers — with sensitive fields
    automatically nulled-out for non-privileged viewers.

    Always includes identity fields (rank/name/capid/flight/squadron/ptype).
    Contact PII (email/phone/parent_*), payment, notes and pii fields are
    populated only when the caller is allowed to see them, otherwise empty
    strings / None.

    Returns a flat dict; the caller is responsible for sorting / grouping.
    """
    show_contact = can_view_contact_pii(user)
    show_payment = can_view_finance(user)
    show_notes = can_view_notes(user)

    def _maybe(field, allowed, default=""):
        return p.get(field, default) if allowed else default

    return {
        "id": p.get("id"),
        "first_name": p.get("first_name", ""),
        "last_name": p.get("last_name", ""),
        "rank": p.get("rank", ""),
        "capid": p.get("capid", ""),
        "name": f"{p.get('rank', '')} {p.get('last_name', '')}, {p.get('first_name', '')}".strip(", "),
        "flight": (p.get("flight") or "").lower(),
        "squadron": p.get("squadron", ""),
        "participant_type": p.get("participant_type", ""),
        "is_exec_cadre": bool(p.get("is_exec_cadre")),
        "member_type": p.get("member_type", ""),
        "position": p.get("position", ""),
        "gender": p.get("gender", ""),
        "age": p.get("age"),
        "wing": p.get("wing", ""),
        "unit": p.get("unit", ""),
        "photo_path": p.get("photo_path", ""),
        # Contact (PII) — gated.
        "email":         _maybe("email", show_contact),
        "phone":         _maybe("phone", show_contact) or _maybe("cell_phone", show_contact),
        "parent_email":  _maybe("cadet_parent_email", show_contact),
        "parent_phone":  _maybe("cadet_parent_phone", show_contact),
        "parent_name":   _maybe("cadet_parent_name", show_contact),
        # Payment — gated.
        "paid":          bool(p.get("paid")) if show_payment else False,
        "amount_paid":   p.get("amount_paid") if show_payment else None,
        # Notes — gated.
        "notes":         _maybe("notes", show_notes, None),
    }


def redact_payment_only(p: dict, user: dict) -> dict:
    """Strip payment fields only, leaving contact/PII/notes intact. Used by
    senior-staff (non-finance) callers who legitimately see full PII but
    must not see money."""
    if can_view_finance(user):
        return dict(p)
    redacted = dict(p)
    for f in PAYMENT_FIELDS:
        if f in redacted:
            redacted[f] = _redact_payment_value(f, redacted[f])
    return redacted
