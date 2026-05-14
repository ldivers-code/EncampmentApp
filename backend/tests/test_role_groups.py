"""Phase 3 — Unit tests for the seven-concerns role separation.

These tests do NOT hit the live backend; they verify the policy module and
the DEFAULT_PERMISSIONS map directly so the rules are pinned independently
of route wiring.

Rules under test:
  • Cadre receives NO Senior Staff permissions by default.
  • Exec Cadre is treated as a cadre-lead (cadre-elevated), NOT senior staff.
  • Students receive student permissions only.
  • Full admin retains full access.
"""
from models import UserRole, DEFAULT_PERMISSIONS
from role_groups import (
    FULL_ADMIN_ROLES,
    SENIOR_STAFF_ROLES,
    CADRE_LEAD_ROLES,
    CADRE_ROLES,
    STUDENT_ROLES,
    PARENT_ROLES,
    is_full_admin,
    is_senior_staff,
    is_cadre_lead,
    is_cadre,
    is_student,
    is_parent,
    cadre_lead_can_target,
)


# ── Group disjointness ────────────────────────────────────────────────────

def test_admin_and_senior_staff_disjoint():
    assert FULL_ADMIN_ROLES.isdisjoint(SENIOR_STAFF_ROLES)


def test_senior_staff_and_cadre_lead_disjoint():
    """The whole point of Phase 3 — Cadre Lead is NOT Senior Staff."""
    assert SENIOR_STAFF_ROLES.isdisjoint(CADRE_LEAD_ROLES)


def test_senior_staff_and_cadre_disjoint():
    assert SENIOR_STAFF_ROLES.isdisjoint(CADRE_ROLES)


def test_cadre_lead_is_subset_of_cadre():
    """Exec Cadre is cadre with elevation, not its own concern."""
    assert CADRE_LEAD_ROLES.issubset(CADRE_ROLES)


def test_student_is_isolated_from_cadre_and_staff():
    assert STUDENT_ROLES.isdisjoint(CADRE_ROLES)
    assert STUDENT_ROLES.isdisjoint(SENIOR_STAFF_ROLES)
    assert STUDENT_ROLES.isdisjoint(FULL_ADMIN_ROLES)


def test_parent_is_isolated():
    assert PARENT_ROLES.isdisjoint(CADRE_ROLES | SENIOR_STAFF_ROLES | FULL_ADMIN_ROLES | STUDENT_ROLES)


# ── Predicates ─────────────────────────────────────────────────────────────

def test_predicates_for_admin():
    u = {"role": UserRole.COMMANDER}
    assert is_full_admin(u)
    assert not is_senior_staff(u)
    assert not is_cadre_lead(u)
    assert not is_cadre(u)
    assert not is_student(u)


def test_predicates_for_senior_staff():
    u = {"role": UserRole.STAFF}
    assert not is_full_admin(u)
    assert is_senior_staff(u)
    assert not is_cadre_lead(u)
    assert not is_cadre(u)


def test_predicates_for_cadre_lead():
    u = {"role": UserRole.EXEC_CADRE}
    assert not is_full_admin(u)
    assert not is_senior_staff(u), "Cadre Lead must NOT be classified as Senior Staff"
    assert is_cadre_lead(u)
    assert is_cadre(u), "Cadre Lead IS a cadre (elevated subset)"


def test_predicates_for_base_cadre():
    u = {"role": UserRole.CADRE}
    assert is_cadre(u)
    assert not is_cadre_lead(u)
    assert not is_senior_staff(u)


def test_predicates_for_student():
    u = {"role": UserRole.STUDENT}
    assert is_student(u)
    assert not is_cadre(u)
    assert not is_senior_staff(u)


def test_predicates_for_parent():
    u = {"role": UserRole.PARENT}
    assert is_parent(u)
    assert not is_cadre(u)


# ── Default permissions (concern #6 → concern #7 mapping) ──────────────────

ADMIN_ONLY_FLAGS = ("admin_panel",)
SENIOR_STAFF_FLAGS = ("analytics",)  # senior-staff cross-cutting capability
FINANCE_FLAGS = ("budget_view", "budget_edit")
MEDICAL_FLAGS = ("health_view", "health_full")
ROSTER_EDIT_FLAGS = ("roster_edit",)


def _perms(role):
    return DEFAULT_PERMISSIONS[role].model_dump()


def test_cadre_default_has_no_senior_staff_permissions():
    """Cadre MUST NOT receive Senior Staff capabilities by default."""
    p = _perms(UserRole.CADRE)
    for f in ADMIN_ONLY_FLAGS + SENIOR_STAFF_FLAGS + FINANCE_FLAGS + MEDICAL_FLAGS:
        assert p[f] is False, f"CADRE leak: {f} = True by default"
    # Cadre can read roster/schedule but cannot edit them.
    assert p["roster_view"] is True
    assert p["roster_edit"] is False
    assert p["schedule_edit"] is False


def test_exec_cadre_default_has_no_senior_staff_permissions():
    """Exec Cadre is cadre-LEAD, not senior staff — no cross-cutting analytics,
    finance, medical, or admin by default."""
    p = _perms(UserRole.EXEC_CADRE)
    for f in ADMIN_ONLY_FLAGS + SENIOR_STAFF_FLAGS + FINANCE_FLAGS + MEDICAL_FLAGS:
        assert p[f] is False, f"EXEC_CADRE leak: {f} = True by default"
    # Cadre-lead may read but not edit by default (elevation happens at route).
    assert p["roster_view"] is True
    assert p["roster_edit"] is False


def test_student_default_has_student_permissions_only():
    """Students receive student permissions only — no roster, no edits, no admin."""
    p = _perms(UserRole.STUDENT)
    assert p["roster_view"] is False
    assert p["roster_edit"] is False
    for f in ADMIN_ONLY_FLAGS + SENIOR_STAFF_FLAGS + FINANCE_FLAGS + MEDICAL_FLAGS + ROSTER_EDIT_FLAGS:
        assert p[f] is False, f"STUDENT leak: {f} = True by default"


def test_full_admin_default_retains_full_access():
    for admin_role in (UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF):
        p = _perms(admin_role)
        assert p["admin_panel"] is True, f"{admin_role} missing admin_panel"
        assert p["roster_edit"] is True
        assert p["schedule_edit"] is True
        assert p["budget_edit"] is True
        assert p["analytics"] is True
        assert p["health_full"] is True


def test_senior_staff_default_has_director_capabilities_but_not_admin():
    p = _perms(UserRole.STAFF)
    # Senior Staff sees roster, edits roster/schedule within their directorate
    assert p["roster_view"] is True
    assert p["roster_edit"] is True
    assert p["schedule_edit"] is True
    # ...but is NOT a full admin
    assert p["admin_panel"] is False
    assert p["budget_edit"] is False


def test_parent_default_is_locked_down():
    p = _perms(UserRole.PARENT)
    for f in ("dashboard", "roster_view", "schedule_view", "meal_plan_view",
              "budget_view", "analytics", "org_chart", "handbooks",
              "documents", "admin_panel", "health_view"):
        assert p[f] is False, f"PARENT leak: {f} = True by default"


# ── Cadre-lead scope guard ─────────────────────────────────────────────────

def test_cadre_lead_can_target_admin_passes_through():
    actor = {"role": UserRole.COMMANDER}
    target = {"role": UserRole.STAFF}
    assert cadre_lead_can_target(actor, target) is True


def test_cadre_lead_can_target_cadre_ok():
    actor = {"role": UserRole.EXEC_CADRE}
    for trole in (UserRole.CADRE, UserRole.EXEC_CADRE, UserRole.STUDENT):
        assert cadre_lead_can_target(actor, {"role": trole}) is True


def test_cadre_lead_cannot_target_senior_staff():
    actor = {"role": UserRole.EXEC_CADRE}
    for trole in (UserRole.STAFF, UserRole.FINANCE, UserRole.PLANS_PROGRAMS,
                  UserRole.HEALTH_SERVICES, UserRole.COMMANDER):
        assert cadre_lead_can_target(actor, {"role": trole}) is False, \
            f"Cadre Lead must NOT manage {trole}"


def test_non_admin_non_cadre_lead_cannot_target_anyone():
    actor = {"role": UserRole.CADRE}
    target = {"role": UserRole.STUDENT}
    assert cadre_lead_can_target(actor, target) is False
