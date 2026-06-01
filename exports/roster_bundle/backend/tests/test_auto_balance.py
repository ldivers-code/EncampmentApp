"""Unit tests for the auto-balance bug fix + waitlist by application order.

These tests exercise the pure helpers (sort key) and the live endpoint
(`POST /api/students/auto-assign`) using the real preview DB.
"""
import os
import sys
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

from routes.students import _app_edit_sort_key, MAX_STUDENTS_PER_FLIGHT, ALL_FLIGHTS


# ── Pure helpers ────────────────────────────────────────────────────

def test_app_edit_sort_key_iso_passthrough():
    assert _app_edit_sort_key("2026-05-30") == "2026-05-30"


def test_app_edit_sort_key_human_date():
    # "30 May 2026" should sort earlier than "31 May 2026"
    a = _app_edit_sort_key("30 May 2026")
    b = _app_edit_sort_key("31 May 2026")
    assert a < b


def test_app_edit_sort_key_blank_sorts_last():
    blank = _app_edit_sort_key("")
    real = _app_edit_sort_key("30 May 2026")
    assert real < blank
    assert _app_edit_sort_key(None) == "9999-12-31"
    assert _app_edit_sort_key("nan") == "9999-12-31"


def test_capacity_constants():
    # User spec: 3 elements × 5 = 15 per flight; 6 flights = 90 total
    assert MAX_STUDENTS_PER_FLIGHT == 15
    assert len(ALL_FLIGHTS) == 6


# ── Live endpoint ───────────────────────────────────────────────────

def _login(email, password):
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token") or r.json().get("token")
    return {"Authorization": f"Bearer {tok}"}


def test_auto_assign_endpoint_uses_canonical_type():
    """Regression: before the fix the endpoint was filtering by legacy
    `basic_student`/`advanced_student` which returned 0 rows in the canonical
    DB. The fix queries `participant_type == "student"`. The endpoint must
    return a `total_unassigned` count > 0 OR `0 with 'all assigned' message`
    — never silently no-op when unassigned students exist."""
    headers = _login("commander@test.com", "test123")

    # Sanity: count unassigned students in DB
    r = requests.get(f"{BASE_URL}/api/participants", headers=headers, timeout=15)
    assert r.status_code == 200
    parts = r.json()
    students_unassigned = [
        p for p in parts
        if p.get("participant_type") == "student"
        and not p.get("flight")
    ]

    r2 = requests.post(f"{BASE_URL}/api/students/auto-assign",
                       headers=headers, timeout=30)
    assert r2.status_code == 200, r2.text
    body = r2.json()
    if students_unassigned:
        # Must report the count it saw, not 0
        assert body.get("total_unassigned", 0) >= len(students_unassigned) // 2, (
            f"Endpoint reported {body.get('total_unassigned')} unassigned but DB "
            f"has {len(students_unassigned)} — legacy filter bug regressed?"
        )
        # Result must include either assigned or waitlisted
        assert (body.get("assigned", 0) + body.get("waitlisted", 0)) > 0


def test_auto_assign_respects_15_per_flight_cap():
    """After auto-assign, no flight may have more than 15 students."""
    headers = _login("commander@test.com", "test123")
    requests.post(f"{BASE_URL}/api/students/auto-assign",
                  headers=headers, timeout=30)

    r = requests.get(f"{BASE_URL}/api/participants", headers=headers, timeout=15)
    assert r.status_code == 200
    parts = r.json()
    counts = {f: 0 for f in ALL_FLIGHTS}
    for p in parts:
        if p.get("participant_type") != "student":
            continue
        f = (p.get("flight") or "").lower()
        if f in counts:
            counts[f] += 1
    for f, c in counts.items():
        assert c <= MAX_STUDENTS_PER_FLIGHT, (
            f"Flight {f} has {c} students (cap is {MAX_STUDENTS_PER_FLIGHT})"
        )
