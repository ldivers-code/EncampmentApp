"""Phase 3 — Single source of truth for the seven separated concerns.

The application now distinguishes seven independent dimensions:

  1. ACCOUNT STATUS         — is_approved flag on the user document
                              ("pending_approval" | "approved_unlinked" | "approved_linked").
                              Surfaced by GET /api/auth/status.

  2. CAP MEMBER TYPE        — participant.member_type
                              ("SENIOR" | "CADET" | "CADET SPONSOR" | ...).
                              Set from the Registration Zone master report.

  3. ENCAMPMENT             — participant.participant_type
     PARTICIPANT TYPE         ("student" | "cadre" | "senior_staff" | "needs_review").
                              The canonical encampment classification (Phase 2 work).

  4. CADRE ROLE TYPE        — participant.is_exec_cadre boolean +
                              user.cadre_position ("flight_commander" | "flight_sergeant" |
                              "cadet_squadron_commander" | "group_commander" | ...).
                              Exec Cadre is a DUTY SUBSET of cadre, not a senior-staff
                              promotion path.

  5. DUTY ASSIGNMENT        — user.flight / user.squadron / user.cadre_unit /
                              user.cadre_position / user.support_section.
                              Where the person is posted at encampment.

  6. PERMISSION ROLE        — user.role (UserRole enum). What capabilities the
                              account holder gets in the system. INDEPENDENT of
                              concerns 1–5 except where DEFAULT_PERMISSIONS map.

  7. ACCESS SCOPE           — apply_participant_visibility / redact_participant
                              from scope.py + the AccessPermissions flag set.
                              Which rows/fields the caller may read.

Rules (enforced by this module + DEFAULT_PERMISSIONS + per-route checks):

  * Cadre receives CADRE permissions only by default.
    NEVER receives Senior Staff permissions by default.
  * Executive Cadre (UserRole.EXEC_CADRE) is treated as a CADRE-LEAD: it may
    receive elevated *cadre-level* permissions (e.g. seeing all flights for
    cadre supervision, escalating flight reports, signing cadre-team docs).
    It does NOT receive Senior Staff capabilities (analytics, listing senior-
    staff users, full PII roster viewing, finance, medical-full).
  * Students receive STUDENT permissions only.
  * Full Admin (DCP / Commander / Executive Staff) retains full access.

Every route that checks user.role should reference the group constants below
instead of hard-coded lists so the policy stays consistent.
"""
from __future__ import annotations

from models import UserRole


# ─────────────────────────────────────────────────────────────────────────────
# Permission-role groups (concern #6)
# ─────────────────────────────────────────────────────────────────────────────

FULL_ADMIN_ROLES: frozenset[str] = frozenset({
    UserRole.DCP,
    UserRole.COMMANDER,
    UserRole.EXECUTIVE_STAFF,
})
"""Concern #6 — Full admin permission role. Sees everything, can do everything."""


SENIOR_STAFF_ROLES: frozenset[str] = frozenset({
    UserRole.STAFF,
    UserRole.PLANS_PROGRAMS,
    UserRole.FINANCE,
    UserRole.HEALTH_SERVICES,
    UserRole.TRAINING_OFFICER,
    UserRole.LOGISTICS,
    UserRole.DINING_FACILITY,
    UserRole.SUPPORT_LOGISTICS,
    UserRole.SUPPORT_COMMS,
    UserRole.SUPPORT_PA,
    UserRole.SUPPORT_DINING,
    UserRole.SUPPORT_HEALTH,
    UserRole.SQUADRON_COMMANDER,
})
"""Concern #6 — Senior Staff permission roles (senior-member directorate leads).
These accounts back senior-staff participants; they see the full roster with
the appropriate redactions and may edit within their directorate."""


CADRE_LEAD_ROLES: frozenset[str] = frozenset({
    UserRole.EXEC_CADRE,
})
"""Concern #6 — Cadre lead permission role (Executive Cadre).
Treated as a CADRE-LEAD with elevated cadre-level permissions. NOT a senior-
staff promotion path."""


CADRE_ROLES: frozenset[str] = frozenset({
    UserRole.CADRE,
    UserRole.EXEC_CADRE,
})
"""Concern #6 — All cadre permission roles (base + lead).
Includes EXEC_CADRE because Exec Cadre IS cadre (just elevated)."""


STUDENT_ROLES: frozenset[str] = frozenset({
    UserRole.STUDENT,
})
"""Concern #6 — Student permission roles. Receives STUDENT permissions only."""


PARENT_ROLES: frozenset[str] = frozenset({
    UserRole.PARENT,
})
"""Concern #6 — Parent permission role. Only sees the linked cadet."""


# Convenience aggregate sets used by per-route gating.
ADMIN_OR_SENIOR_STAFF: frozenset[str] = FULL_ADMIN_ROLES | SENIOR_STAFF_ROLES
ADMIN_OR_CADRE_LEAD: frozenset[str] = FULL_ADMIN_ROLES | CADRE_LEAD_ROLES
ADMIN_SENIOR_OR_CADRE_LEAD: frozenset[str] = FULL_ADMIN_ROLES | SENIOR_STAFF_ROLES | CADRE_LEAD_ROLES


# ─────────────────────────────────────────────────────────────────────────────
# Helper predicates
# ─────────────────────────────────────────────────────────────────────────────

def is_full_admin(user: dict) -> bool:
    return (user or {}).get("role") in FULL_ADMIN_ROLES


def is_senior_staff(user: dict) -> bool:
    return (user or {}).get("role") in SENIOR_STAFF_ROLES


def is_cadre_lead(user: dict) -> bool:
    return (user or {}).get("role") in CADRE_LEAD_ROLES


def is_cadre(user: dict) -> bool:
    return (user or {}).get("role") in CADRE_ROLES


def is_student(user: dict) -> bool:
    return (user or {}).get("role") in STUDENT_ROLES


def is_parent(user: dict) -> bool:
    return (user or {}).get("role") in PARENT_ROLES


def is_admin_or_senior_staff(user: dict) -> bool:
    return (user or {}).get("role") in ADMIN_OR_SENIOR_STAFF


# ─────────────────────────────────────────────────────────────────────────────
# Cadre-lead scope guard
# ─────────────────────────────────────────────────────────────────────────────

def cadre_lead_can_target(actor: dict, target_user: dict) -> bool:
    """Phase 3 guard — when a Cadre Lead (Exec Cadre) tries to act on another
    user, the target MUST be a cadre, exec-cadre, or student account. Cadre
    Leads MUST NOT manage senior-staff or admin accounts.

    Returns True if the actor's role is admin (no restriction), or if the
    target's role is within the cadre-or-student scope.
    """
    if is_full_admin(actor):
        return True
    if not is_cadre_lead(actor):
        return False
    target_role = (target_user or {}).get("role")
    return target_role in (CADRE_ROLES | STUDENT_ROLES)
