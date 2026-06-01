"""Tests for the support / senior-member taxonomy + roster↔user sync."""
import os
import sys
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

from support_sections import (
    is_non_flight_role,
    is_support_role,
    squadron_bucket_for_role,
    section_for_role,
    role_for_section,
    SQUADRON_SUPPORT_CADRE,
    SQUADRON_SUPPORT_SENIOR_STAFF,
    SQUADRON_SENIOR_MEMBER,
    SUPPORT_SECTION_SLUGS,
)
from models import UserRole


# ── Pure helpers ────────────────────────────────────────────────────

def test_classify_commander_as_senior_member():
    assert is_non_flight_role(UserRole.COMMANDER)
    assert not is_support_role(UserRole.COMMANDER)
    assert squadron_bucket_for_role(UserRole.COMMANDER) == SQUADRON_SENIOR_MEMBER
    assert section_for_role(UserRole.COMMANDER) is None


def test_classify_new_superintendent_role():
    assert UserRole.SUPERINTENDENT == "superintendent"
    assert is_non_flight_role(UserRole.SUPERINTENDENT)
    assert squadron_bucket_for_role(UserRole.SUPERINTENDENT) == SQUADRON_SENIOR_MEMBER


def test_classify_new_chief_training_officer_role():
    assert UserRole.CHIEF_TRAINING_OFFICER == "chief_training_officer"
    assert is_non_flight_role(UserRole.CHIEF_TRAINING_OFFICER)


def test_classify_new_public_affairs_role():
    assert UserRole.PUBLIC_AFFAIRS == "public_affairs"
    assert is_support_role(UserRole.PUBLIC_AFFAIRS)
    assert squadron_bucket_for_role(UserRole.PUBLIC_AFFAIRS) == SQUADRON_SUPPORT_SENIOR_STAFF
    assert section_for_role(UserRole.PUBLIC_AFFAIRS) == "public_affairs"


def test_classify_support_cadre_roles():
    assert is_support_role(UserRole.SUPPORT_COMMS)
    assert squadron_bucket_for_role(UserRole.SUPPORT_COMMS) == SQUADRON_SUPPORT_CADRE
    assert section_for_role(UserRole.SUPPORT_COMMS) == "communications"


def test_cadre_role_keeps_flight():
    assert not is_non_flight_role(UserRole.CADRE)
    assert not is_non_flight_role(UserRole.EXEC_CADRE)
    assert squadron_bucket_for_role(UserRole.CADRE) is None


def test_role_for_section_resolves_in_correct_bucket():
    # Cadre side
    assert role_for_section("logistics", SQUADRON_SUPPORT_CADRE) == UserRole.SUPPORT_LOGISTICS
    assert role_for_section("communications", SQUADRON_SUPPORT_CADRE) == UserRole.SUPPORT_COMMS
    # Senior staff side
    assert role_for_section("logistics", SQUADRON_SUPPORT_SENIOR_STAFF) == UserRole.LOGISTICS
    assert role_for_section("public_affairs", SQUADRON_SUPPORT_SENIOR_STAFF) == UserRole.PUBLIC_AFFAIRS
    # Cadre Training doesn't have a role today
    assert role_for_section("training", SQUADRON_SUPPORT_CADRE) is None


def test_eight_support_sections_exist():
    expected = {"logistics", "communications", "public_affairs", "dining",
                "health", "plans_programs", "training", "finance"}
    assert SUPPORT_SECTION_SLUGS == expected


# ── Live endpoints ──────────────────────────────────────────────────

def _login(email, password):
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json().get('access_token') or r.json().get('token')}"}


def test_taxonomy_endpoint_returns_full_shape():
    headers = _login("commander@test.com", "test123")
    r = requests.get(f"{BASE_URL}/api/taxonomy/support", headers=headers, timeout=10)
    assert r.status_code == 200
    body = r.json()
    # Sections
    assert len(body["support_sections"]) == 8
    assert {s["slug"] for s in body["support_sections"]} == {
        "logistics", "communications", "public_affairs", "dining",
        "health", "plans_programs", "training", "finance",
    }
    # Squadrons
    assert body["squadrons"]["support_cadre"]["slug"] == "support_cadre"
    assert body["squadrons"]["support_senior_staff"]["slug"] == "support_senior_staff"
    assert body["squadrons"]["senior_member"]["slug"] == "senior_member"
    # Role groups
    assert "commander" in body["role_groups"]["senior_member"]
    assert "superintendent" in body["role_groups"]["senior_member"]
    assert "chief_training_officer" in body["role_groups"]["senior_member"]
    assert "training_officer" in body["role_groups"]["senior_member"]
    assert "public_affairs" in body["role_groups"]["support_senior_staff"]
    assert "support_comms" in body["role_groups"]["support_cadre"]


def test_participants_endpoint_enriches_support_users():
    headers = _login("commander@test.com", "test123")
    r = requests.get(f"{BASE_URL}/api/participants", headers=headers, timeout=15)
    assert r.status_code == 200
    parts = r.json()
    # Find at least one is_support participant (we seeded the preview DB
    # with a support_logistics test user).
    support = [p for p in parts if p.get("is_support")]
    assert len(support) >= 1, "Expected at least one is_support participant in the preview DB"
    for p in support:
        assert p.get("linked_user_role") is not None
        # Their participant_type is cadre (or senior_staff) — never `student`
        assert p.get("participant_type") in ("cadre", "senior_staff", "needs_review", None)
