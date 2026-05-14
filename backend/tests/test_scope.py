"""Phase 5 — Unit tests for the shared sensitive-data / export helpers.

Pins the contract for `safe_roster_entry`, `redact_participant`,
`redact_payment_only`, `visible_flights_for`, and `export_columns_for`.
"""
import pytest
from fastapi import HTTPException

from models import UserRole
from scope import (
    safe_roster_entry,
    redact_participant,
    redact_payment_only,
    visible_flights_for,
    export_columns_for,
    can_view_full_participant,
    can_view_finance,
    can_view_payment,
    can_view_health,
    can_view_medical,
    can_view_contact_pii,
    can_view_notes,
    PRIVILEGED_VIEWING_ROLES,
    FINANCE_ROLES,
    HEALTH_ROLES,
    SAFE_EXPORT_COLUMNS,
    PAYMENT_FIELDS,
)


SAMPLE_PARTICIPANT = {
    "id": "p1", "first_name": "Jane", "last_name": "Doe",
    "rank": "C/SrA", "capid": "12345",
    "flight": "alpha", "squadron": "6th_cts",
    "participant_type": "cadre", "is_exec_cadre": False,
    "member_type": "CADET", "position": "Flight Commander",
    "gender": "F", "age": 17, "wing": "TN", "unit": "TN-001",
    "photo_path": "/p/jane.jpg",
    # Sensitive — must be redacted for non-privileged callers
    "email": "jane@example.com",
    "phone": "(555) 123-4567",
    "cell_phone": "(555) 222-3333",
    "cadet_parent_email": "parent@example.com",
    "cadet_parent_phone": "(555) 444-5555",
    "cadet_parent_name": "Mary Doe",
    "address": "123 Main St", "city": "Knoxville", "state": "TN", "zip_code": "37901",
    "emergency_contact": "Mary Doe", "emergency_phone": "(555) 444-5555",
    "shirt_size": "M",
    "religious_preference": "Catholic",
    "paid": True, "paid_in_full": True, "amount_paid": 100.0,
    "registration_status": "approved",
    "unit_approved": True, "wing_approved": True, "slotted": True,
    "notes": "Strong leader", "comments": "Recommended for staff",
    "unit_cc_name": "Capt Smith", "unit_cc_email": "smith@cap.gov",
}


def _admin():     return {"role": UserRole.COMMANDER}
def _senior():    return {"role": UserRole.STAFF}            # senior staff (no finance)
def _finance():   return {"role": UserRole.FINANCE}
def _health():    return {"role": UserRole.HEALTH_SERVICES}
def _cadre():     return {"role": UserRole.CADRE, "flight": "alpha"}
def _exec_cadre():return {"role": UserRole.EXEC_CADRE, "flight": "alpha"}
def _student():   return {"role": UserRole.STUDENT}
def _parent():    return {"role": UserRole.PARENT}
def _sqcc():      return {"role": UserRole.SQUADRON_COMMANDER, "squadron": "6th_cts"}


# ── Permission predicates ──────────────────────────────────────────────────

def test_can_view_full_participant_admin_and_senior_staff_only():
    assert can_view_full_participant(_admin())
    assert can_view_full_participant(_senior())
    assert can_view_full_participant(_finance())
    assert not can_view_full_participant(_cadre())
    assert not can_view_full_participant(_exec_cadre())
    assert not can_view_full_participant(_student())
    assert not can_view_full_participant(_parent())


def test_can_view_finance_locked_to_finance_roles():
    assert can_view_finance(_admin())
    assert can_view_finance(_finance())
    # senior staff DOES NOT see finance by default
    assert not can_view_finance(_senior())
    assert not can_view_finance(_cadre())
    assert not can_view_finance(_exec_cadre())
    assert not can_view_finance(_health())


def test_can_view_payment_alias_matches_finance():
    """Phase 5: semantic alias for finance — exact same set."""
    for role in (_admin(), _finance(), _senior(), _cadre(), _exec_cadre(), _parent()):
        assert can_view_payment(role) == can_view_finance(role)


def test_can_view_medical_alias_matches_health():
    for role in (_admin(), _health(), _senior(), _cadre(), _student()):
        assert can_view_medical(role) == can_view_health(role)


def test_can_view_contact_pii_matches_full_participant():
    """Contact PII parallels the full-participant view set."""
    for role in (_admin(), _senior(), _finance(), _cadre(), _exec_cadre(), _student(), _parent()):
        assert can_view_contact_pii(role) == can_view_full_participant(role)


def test_can_view_notes_matches_full_participant():
    for role in (_admin(), _senior(), _cadre(), _exec_cadre(), _student()):
        assert can_view_notes(role) == can_view_full_participant(role)


# ── safe_roster_entry — the shared roster shaper ───────────────────────────

def test_safe_roster_entry_admin_sees_everything():
    e = safe_roster_entry(SAMPLE_PARTICIPANT, _admin())
    assert e["email"] == "jane@example.com"
    assert e["phone"] == "(555) 123-4567"
    assert e["parent_email"] == "parent@example.com"
    assert e["parent_phone"] == "(555) 444-5555"
    assert e["paid"] is True
    assert e["amount_paid"] == 100.0
    assert e["notes"] == "Strong leader"


def test_safe_roster_entry_senior_staff_sees_pii_but_not_payment():
    e = safe_roster_entry(SAMPLE_PARTICIPANT, _senior())
    # Senior Staff (non-finance) sees contact / notes — they're directorate leads
    assert e["email"] == "jane@example.com"
    assert e["parent_email"] == "parent@example.com"
    assert e["notes"] == "Strong leader"
    # ...but NOT payment
    assert e["paid"] is False
    assert e["amount_paid"] is None


def test_safe_roster_entry_cadre_sees_no_pii_no_payment_no_notes():
    e = safe_roster_entry(SAMPLE_PARTICIPANT, _cadre())
    # Identity still visible — cadre can manage their flight
    assert e["first_name"] == "Jane"
    assert e["rank"] == "C/SrA"
    assert e["capid"] == "12345"
    assert e["flight"] == "alpha"
    # PII / payment / notes all redacted
    assert e["email"] == ""
    assert e["phone"] == ""
    assert e["parent_email"] == ""
    assert e["parent_phone"] == ""
    assert e["parent_name"] == ""
    assert e["paid"] is False
    assert e["amount_paid"] is None
    assert e["notes"] is None


def test_safe_roster_entry_exec_cadre_redacts_like_cadre():
    """Phase 3 + 5: Exec Cadre is a cadre-lead — same redaction as cadre."""
    e = safe_roster_entry(SAMPLE_PARTICIPANT, _exec_cadre())
    assert e["email"] == ""
    assert e["paid"] is False
    assert e["notes"] is None


def test_safe_roster_entry_student_redacts_everything_sensitive():
    e = safe_roster_entry(SAMPLE_PARTICIPANT, _student())
    assert e["email"] == ""
    assert e["paid"] is False
    assert e["notes"] is None


# ── redact_participant — full doc redaction ────────────────────────────────

def test_redact_participant_admin_no_change():
    r = redact_participant(SAMPLE_PARTICIPANT, _admin())
    assert r["email"] == "jane@example.com"
    assert r["amount_paid"] == 100.0
    assert r["notes"] == "Strong leader"


def test_redact_participant_senior_keeps_pii_strips_payment():
    r = redact_participant(SAMPLE_PARTICIPANT, _senior())
    assert r["email"] == "jane@example.com"
    assert r["address"] == "123 Main St"
    assert r["notes"] == "Strong leader"
    # Payment stripped
    assert r["amount_paid"] is None
    assert r["paid"] is False
    assert r["unit_approved"] is False


def test_redact_participant_cadre_strips_all_sensitive():
    r = redact_participant(SAMPLE_PARTICIPANT, _cadre())
    for f in ("email", "phone", "cadet_parent_email", "address", "city",
              "emergency_contact", "shirt_size", "religious_preference",
              "notes", "comments", "unit_cc_email"):
        assert r[f] is None, f"Cadre leak: {f} = {r[f]!r}"
    assert r["paid"] is False
    assert r["amount_paid"] is None


def test_redact_payment_only_strips_payment_keeps_pii():
    r = redact_payment_only(SAMPLE_PARTICIPANT, _senior())
    # Contact PII intact for senior staff
    assert r["email"] == "jane@example.com"
    assert r["cadet_parent_email"] == "parent@example.com"
    assert r["notes"] == "Strong leader"
    # Payment stripped
    assert r["paid"] is False
    assert r["amount_paid"] is None


def test_redact_payment_only_passthrough_for_finance():
    r = redact_payment_only(SAMPLE_PARTICIPANT, _finance())
    assert r["paid"] is True
    assert r["amount_paid"] == 100.0


# ── visible_flights_for — flight scope guard ───────────────────────────────

def test_visible_flights_admin_unscoped():
    assert visible_flights_for(_admin(), ["alpha", "echo"]) == ["alpha", "echo"]


def test_visible_flights_senior_staff_unscoped():
    assert visible_flights_for(_senior(), ["alpha", "echo"]) == ["alpha", "echo"]


def test_visible_flights_cadre_in_alpha_can_only_see_alpha():
    assert visible_flights_for(_cadre(), ["alpha"]) == ["alpha"]
    with pytest.raises(HTTPException) as e:
        visible_flights_for(_cadre(), ["echo"])
    assert e.value.status_code == 403


def test_visible_flights_cadre_intersection_when_mixed():
    assert visible_flights_for(_cadre(), ["alpha", "echo"]) == ["alpha"]


def test_visible_flights_squadron_cmdr_scoped_to_squadron_flights():
    sqcc = _sqcc()  # 6th_cts → alpha, bravo
    assert visible_flights_for(sqcc, ["alpha", "bravo"]) == ["alpha", "bravo"]
    with pytest.raises(HTTPException):
        visible_flights_for(sqcc, ["echo"])


def test_visible_flights_parent_403():
    with pytest.raises(HTTPException) as e:
        visible_flights_for(_parent(), ["alpha"])
    assert e.value.status_code == 403


def test_visible_flights_unscoped_cadre_with_no_flight_403():
    with pytest.raises(HTTPException):
        visible_flights_for({"role": UserRole.CADRE}, ["alpha"])


# ── export_columns_for — export column allowlist ──────────────────────────

def test_export_columns_admin_returns_everything_requested():
    cols = export_columns_for(_admin(), ["amount_paid", "email", "notes", "capid"])
    assert "amount_paid" in cols
    assert "email" in cols


def test_export_columns_senior_strips_payment():
    cols = export_columns_for(_senior(), ["amount_paid", "email", "paid", "capid"])
    assert "amount_paid" not in cols
    assert "paid" not in cols
    assert "email" in cols
    assert "capid" in cols


def test_export_columns_cadre_restricted_to_safe_set():
    cols = export_columns_for(_cadre(), ["amount_paid", "email", "address", "capid", "rank"])
    assert set(cols).issubset(set(SAFE_EXPORT_COLUMNS))
    # email/address/amount_paid all redacted away
    assert "amount_paid" not in cols
    assert "email" not in cols
    assert "address" not in cols
    # capid + rank are safe
    assert "capid" in cols
    assert "rank" in cols


def test_export_columns_parent_locked_down():
    cols = export_columns_for(_parent(), ["amount_paid", "email", "capid"])
    assert "amount_paid" not in cols
    assert "email" not in cols


# ── Role-set sanity ────────────────────────────────────────────────────────

def test_finance_roles_can_see_full_participant():
    """Sanity — every finance role must be allowed full PII to follow up on
    payments. (Finance roles are a subset of privileged viewers by design.)"""
    for r in FINANCE_ROLES:
        assert can_view_full_participant({"role": r}), f"{r} must be allowed full PII to follow up on payments"


def test_payment_fields_are_a_redacted_set():
    """Sanity — the constant exposed in scope.py covers the payment surface."""
    assert "amount_paid" in PAYMENT_FIELDS
    assert "paid" in PAYMENT_FIELDS
    assert "paid_in_full" in PAYMENT_FIELDS
    assert "registration_status" in PAYMENT_FIELDS
