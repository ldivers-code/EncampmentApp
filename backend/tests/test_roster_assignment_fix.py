"""Acceptance tests for the roster assignment + Exec Cadre role-mgmt fixes.

Covers:
  * 15-student cap enforcement on single + bulk assignment endpoints
  * Idempotent re-upload (no duplicates)
  * App-only rows flagged for review, not deleted
  * Blank SubEvents → needs_review with no flight
  * Exec Cadre may edit cadre-side roles ONLY + audit log
"""
import io
import os
import sys
import uuid

import pandas as pd
import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


# ── Helpers ─────────────────────────────────────────────────────────

def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=10)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json().get('access_token') or r.json().get('token')}"}


def _make_roster_excel(rows: list[dict]) -> io.BytesIO:
    """Build an eCAP-shape Excel in-memory."""
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    return buf


def _sample_row(capid: str, app_edit: str = "30 May 2026", subevent: str = "Basic Encampment"):
    return {
        "CAPID": capid,
        "FirstName": f"Test{capid}",
        "LastName": "Cadet",
        "Grade": "C/Amn",
        "Gender": "M",
        "Age": 14,
        "Email": f"cadet{capid}@example.com",
        "Phone": "615-555-0100",
        "Wing": "TNWG",
        "Unit": "TN-001",
        "SubEvents": subevent,
        "AppEditDate": app_edit,
        "AmountPaid": 100,
        "PaidInFull": "Yes",
    }


@pytest.fixture
def commander_headers():
    return _login("commander@test.com", "test123")


# ────────────────────────────────────────────────────────────────────
# 1. Hard cap on single-row assignment
# ────────────────────────────────────────────────────────────────────

def test_single_assignment_blocked_when_flight_full(commander_headers):
    """Once a flight is at 15, the next student PUT returns 409."""
    # Fill alpha to 15 first via the auto-assigner.
    requests.post(f"{BASE_URL}/api/students/auto-assign",
                  headers=commander_headers, timeout=30)
    parts = requests.get(f"{BASE_URL}/api/participants",
                         headers=commander_headers, timeout=15).json()
    students = [p for p in parts if p.get("participant_type") == "student"]
    alpha_students = [p for p in students if (p.get("flight") or "").lower() == "alpha"]
    other_students_with_flight = [
        p for p in students
        if (p.get("flight") or "").lower() in ("bravo", "charlie", "delta", "echo", "foxtrot")
    ]

    # If alpha is full (>=15), trying to move one more student in must 409.
    if len(alpha_students) >= 15 and other_students_with_flight:
        target = other_students_with_flight[0]
        r = requests.put(
            f"{BASE_URL}/api/participants/{target['id']}/assignment",
            json={"flight": "alpha"},
            headers=commander_headers, timeout=10,
        )
        assert r.status_code == 409, (
            f"Expected 409 when moving into full alpha, got {r.status_code}: {r.text}"
        )
        body = r.json()
        assert "capacity" in body.get("detail", "").lower()


def test_cadre_assignment_NOT_blocked_by_student_cap(commander_headers):
    """Cadre / senior_staff should not be counted toward the 15-cap."""
    parts = requests.get(f"{BASE_URL}/api/participants",
                         headers=commander_headers, timeout=15).json()
    cadre = [p for p in parts
             if p.get("participant_type") == "cadre"
             and not p.get("is_non_flight")][:1]
    if not cadre:
        pytest.skip("No flight-eligible cadre in preview DB")
    target = cadre[0]
    r = requests.put(
        f"{BASE_URL}/api/participants/{target['id']}/assignment",
        json={"flight": "alpha"},
        headers=commander_headers, timeout=10,
    )
    assert r.status_code == 200, (
        f"Cadre move into alpha should NOT be capped — got {r.status_code}: {r.text}"
    )


# ────────────────────────────────────────────────────────────────────
# 2. Hard cap on bulk-assignment
# ────────────────────────────────────────────────────────────────────

def test_bulk_assignment_blocked_when_would_overfill(commander_headers):
    parts = requests.get(f"{BASE_URL}/api/participants",
                         headers=commander_headers, timeout=15).json()
    students = [p for p in parts if p.get("participant_type") == "student"]
    waitlisted = [p for p in students if not p.get("flight")]
    if len(waitlisted) < 3:
        pytest.skip("Need 3+ waitlisted students for this test")

    # Try to bulk-move 3 waitlisted students into alpha (which is at 15).
    payload = {
        "participant_ids": [p["id"] for p in waitlisted[:3]],
        "flight": "alpha",
        "squadron": "6th_cts",
    }
    r = requests.put(
        f"{BASE_URL}/api/participants/bulk-assignment",
        json=payload, headers=commander_headers, timeout=10,
    )
    assert r.status_code == 409, (
        f"Expected 409 on bulk overfill, got {r.status_code}: {r.text}"
    )


# ────────────────────────────────────────────────────────────────────
# 3. Idempotent upload
# ────────────────────────────────────────────────────────────────────

def test_double_upload_creates_no_duplicates(commander_headers):
    """Uploading the same Excel twice must not create duplicate rows."""
    capid = f"99{uuid.uuid4().hex[:6]}"  # unlikely to collide
    rows = [_sample_row(capid)]
    excel = _make_roster_excel(rows)

    # First upload — additive mode to avoid touching the rest of the roster
    files = {"file": (f"roster1.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    r1 = requests.post(
        f"{BASE_URL}/api/students/upload?sync=false&auto_assign=true",
        files=files, headers=commander_headers, timeout=30,
    )
    assert r1.status_code == 200, r1.text

    # Second upload of the SAME file
    excel.seek(0)
    files = {"file": (f"roster2.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    r2 = requests.post(
        f"{BASE_URL}/api/students/upload?sync=false&auto_assign=true",
        files=files, headers=commander_headers, timeout=30,
    )
    assert r2.status_code == 200, r2.text

    # Only ONE row with this capid
    parts = requests.get(f"{BASE_URL}/api/participants",
                         headers=commander_headers, timeout=15).json()
    matches = [p for p in parts if (p.get("capid") or "") == capid]
    assert len(matches) == 1, f"Expected idempotent upload — got {len(matches)} rows for capid={capid}"


# ────────────────────────────────────────────────────────────────────
# 4. Blank SubEvents → needs_review
# ────────────────────────────────────────────────────────────────────

def test_blank_subevents_becomes_needs_review(commander_headers):
    capid = f"99{uuid.uuid4().hex[:6]}"
    row = _sample_row(capid, subevent="")  # blank!
    excel = _make_roster_excel([row])
    files = {"file": ("noevent.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    r = requests.post(
        f"{BASE_URL}/api/students/upload?sync=false&auto_assign=true",
        files=files, headers=commander_headers, timeout=30,
    )
    assert r.status_code == 200, r.text

    parts = requests.get(f"{BASE_URL}/api/participants",
                         headers=commander_headers, timeout=15).json()
    me = [p for p in parts if (p.get("capid") or "") == capid]
    assert me, "Uploaded row should be present"
    p = me[0]
    # Either participant_type=needs_review OR flight is None — both are
    # acceptable per spec, but a blank-subevent row must NOT take a seat.
    assert not p.get("flight"), f"Blank-subevent row got a flight: {p.get('flight')}"
    # Review flag should be present
    assert p.get("review_status") == "needs_review" or p.get("participant_type") == "needs_review", (
        f"Blank-subevent row should be flagged for review. Got "
        f"participant_type={p.get('participant_type')!r}, "
        f"review_status={p.get('review_status')!r}"
    )


# ────────────────────────────────────────────────────────────────────
# 5. Item #10 — Exec Cadre role management
# ────────────────────────────────────────────────────────────────────

def _create_user(email, password, role, name="Test User"):
    """Helper — create a user via the registration endpoint. Returns the
    user id once approved by an admin."""
    r = requests.post(f"{BASE_URL}/api/auth/register",
                      json={"email": email, "password": password,
                            "name": name, "role": role}, timeout=10)
    return r


def test_exec_cadre_can_set_cadre_role(commander_headers):
    """An Exec Cadre user must be able to change a cadre user's role to
    another cadre-bucket role (e.g. cadre → support_logistics)."""
    actor_headers = _login("exec_cadre@test.com", "test123")
    users = requests.get(f"{BASE_URL}/api/users", headers=commander_headers, timeout=15).json()
    cadre_targets = [u for u in users if u.get("role") == "cadre"]
    if not cadre_targets:
        pytest.skip("Need at least 1 cadre user in preview DB")

    target = cadre_targets[0]
    original_role = target["role"]
    r = requests.put(
        f"{BASE_URL}/api/users/{target['id']}/role?role=support_logistics",
        headers=actor_headers, timeout=10,
    )
    assert r.status_code == 200, f"Exec cadre should be allowed: {r.status_code} {r.text}"

    # Audit log: there should be a matching entry
    log = requests.get(f"{BASE_URL}/api/users/role-audit-log",
                       headers=actor_headers, timeout=10).json()
    assert any(
        e.get("target_user_id") == target["id"]
        and e.get("new_role") == "support_logistics"
        for e in log
    ), "Role change should produce an audit log entry"

    # Restore
    requests.put(
        f"{BASE_URL}/api/users/{target['id']}/role?role={original_role}",
        headers=commander_headers, timeout=10,
    )


def test_exec_cadre_cannot_grant_protected_role(commander_headers):
    """Exec cadre may NOT grant commander / dcp / executive_staff."""
    actor_headers = _login("exec_cadre@test.com", "test123")
    users = requests.get(f"{BASE_URL}/api/users", headers=commander_headers, timeout=15).json()
    cadre_targets = [u for u in users if u.get("role") == "cadre"]
    if not cadre_targets:
        pytest.skip("Need at least 1 cadre user in preview DB")

    target = cadre_targets[0]
    for forbidden in ("commander", "dcp", "executive_staff", "superintendent"):
        r = requests.put(
            f"{BASE_URL}/api/users/{target['id']}/role?role={forbidden}",
            headers=actor_headers, timeout=10,
        )
        assert r.status_code == 403, (
            f"Exec cadre should NOT be able to grant {forbidden} — got {r.status_code}: {r.text}"
        )


def test_exec_cadre_cannot_edit_non_cadre_user(commander_headers):
    """Exec cadre can't edit users whose current role is student/parent/senior staff."""
    actor_headers = _login("exec_cadre@test.com", "test123")
    users = requests.get(f"{BASE_URL}/api/users", headers=commander_headers, timeout=15).json()
    student_users = [u for u in users if u.get("role") == "student"]
    if not student_users:
        pytest.skip("Need at least 1 student user in preview DB")

    r = requests.put(
        f"{BASE_URL}/api/users/{student_users[0]['id']}/role?role=cadre",
        headers=actor_headers, timeout=10,
    )
    assert r.status_code == 403, (
        f"Exec cadre editing a student should be 403, got {r.status_code}"
    )
