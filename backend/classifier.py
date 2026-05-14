"""Canonical participant classifier.

The Registration Zone SubEvents column is the single source of truth.

Rules:
  - Senior Staff sub-event + senior member → senior_staff
  - Cadre sub-event + cadet → cadre
  - Student sub-event + cadet → student
  - Anything else (blank, ambiguous, member_type/sub-event mismatch) → needs_review

The generic RegZone "staff" boolean and the generic "Staff Application"
sub-event keyword are NOT authoritative on their own — they are ignored by
this classifier. Mismatches (e.g., cadet listed under Senior Staff
Application; senior listed under Student Application) are explicitly flagged
as needs_review so an admin can resolve them.
"""
from __future__ import annotations
from typing import Optional

from models import ParticipantType

# Canonical sub-event tokens (case-insensitive contains-match after stripping).
# Each value lists the sub-strings that unambiguously identify that sub-event.
SUBEVENT_TOKENS = {
    ParticipantType.SENIOR_STAFF: ("senior staff",),
    ParticipantType.CADRE: ("cadre",),
    ParticipantType.STUDENT: ("student",),
}

# Member-type categories that are eligible for each ptype.
ELIGIBLE_MEMBER_TYPES = {
    ParticipantType.SENIOR_STAFF: {"SENIOR", "CADET SPONSOR"},
    ParticipantType.CADRE: {"CADET"},
    ParticipantType.STUDENT: {"CADET"},
}


def _normalize_subevent(sub_event: Optional[str]) -> str:
    if not sub_event:
        return ""
    return str(sub_event).strip().lower()


def _normalize_member_type(member_type: Optional[str]) -> str:
    if not member_type:
        return ""
    return str(member_type).strip().upper()


def classify_from_subevent(member_type: Optional[str], sub_event: Optional[str]) -> str:
    """Return the canonical ParticipantType for a roster row.

    Always returns one of:
      ParticipantType.SENIOR_STAFF | CADRE | STUDENT | NEEDS_REVIEW
    """
    se = _normalize_subevent(sub_event)
    mt = _normalize_member_type(member_type)

    if not se:
        # No sub-event signal at all → needs_review (do NOT guess from member_type alone)
        return ParticipantType.NEEDS_REVIEW

    # Identify which sub-event the row is in. "senior staff" must be checked
    # before "staff"-substring matches so a generic Staff Application doesn't
    # silently claim a senior-staff classification.
    detected: Optional[str] = None
    if "senior staff" in se:
        detected = ParticipantType.SENIOR_STAFF
    elif "cadre" in se:
        detected = ParticipantType.CADRE
    elif "student" in se:
        detected = ParticipantType.STUDENT
    else:
        # Sub-event present but not one of the three canonical applications.
        return ParticipantType.NEEDS_REVIEW

    # Validate member_type against the detected sub-event. Mismatches are
    # surfaced for admin review — not silently coerced.
    eligible = ELIGIBLE_MEMBER_TYPES[detected]
    if mt and mt not in eligible:
        return ParticipantType.NEEDS_REVIEW

    return detected


def is_legacy_value(value: Optional[str]) -> bool:
    """True if the given participant_type uses a pre-Phase-2 vocabulary."""
    if not value:
        return False
    return value in {"basic_student", "advanced_student", "exec_cadre", "senior_member"}


def canonicalize(value: Optional[str], member_type: Optional[str] = None) -> str:
    """Translate a legacy participant_type value to the canonical equivalent.

    Used only by the migration script and the read-side aliases — fresh
    classification should go through `classify_from_subevent`.
    """
    if not value:
        return ParticipantType.NEEDS_REVIEW
    v = value.lower().strip()
    if v in ("basic_student", "advanced_student", "student"):
        return ParticipantType.STUDENT
    if v in ("cadre", "exec_cadre"):
        return ParticipantType.CADRE
    if v in ("senior_staff", "senior_member"):
        return ParticipantType.SENIOR_STAFF
    if v == "staff":
        # "staff" was used for both senior members and cadets — disambiguate by member_type.
        mt = (member_type or "").upper().strip()
        if mt in ("SENIOR", "CADET SPONSOR"):
            return ParticipantType.SENIOR_STAFF
        if mt == "CADET":
            return ParticipantType.NEEDS_REVIEW  # cadet listed as "staff" with no sub-event signal
        return ParticipantType.NEEDS_REVIEW
    if v == "needs_review":
        return ParticipantType.NEEDS_REVIEW
    # Unknown / future value — preserve as-is rather than corrupting it.
    return v
