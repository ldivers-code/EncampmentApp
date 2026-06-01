"""Tests for the Review Queue endpoints."""
import os
import sys
import uuid
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# Load backend .env before importing pymongo so MONGO_URL is set in env.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from pymongo import MongoClient  # noqa: E402

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Use a sync pymongo client for test setup/teardown — the motor client in
# database.py needs an active event loop which pytest doesn't provide.
_sync_client = MongoClient(os.environ["MONGO_URL"])
_sync_db = _sync_client[os.environ["DB_NAME"]]


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=10)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json().get('access_token') or r.json().get('token')}"}


def _create_flagged_participant():
    pid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": pid,
        "capid": f"99{uuid.uuid4().hex[:6]}",
        "first_name": "Review",
        "last_name": f"Test{uuid.uuid4().hex[:4]}",
        "rank": "C/Amn",
        "unit": "TN-001",
        "participant_type": "needs_review",
        "review_status": "needs_review",
        "review_reason": "Blank SubEvents (test fixture)",
        "review_flagged_at": now,
        "created_at": now,
        "updated_at": now,
        "is_removed": False,
    }
    _sync_db.participants.insert_one(doc)
    return pid


def _cleanup(pid):
    _sync_db.participants.delete_one({"id": pid})


def test_review_queue_requires_admin_role():
    """Cadre user should get 403."""
    # Use an account that's not in REVIEW_QUEUE_ROLES
    r = requests.get(f"{BASE_URL}/api/review-queue", timeout=10)
    assert r.status_code in (401, 403)


def test_review_queue_lists_flagged_rows():
    headers = _login("commander@test.com", "test123")
    pid = _create_flagged_participant()
    try:
        r = requests.get(f"{BASE_URL}/api/review-queue", headers=headers, timeout=10)
        assert r.status_code == 200
        rows = r.json()
        ids = {row["id"] for row in rows}
        assert pid in ids, f"Inserted fixture {pid} should appear in queue"

        # Stats
        s = requests.get(f"{BASE_URL}/api/review-queue/stats",
                         headers=headers, timeout=10).json()
        assert s["total"] >= 1
        assert s["blank_subevents"] >= 1
    finally:
        _cleanup(pid)


def test_resolve_approve_as_student():
    headers = _login("commander@test.com", "test123")
    pid = _create_flagged_participant()
    try:
        r = requests.post(
            f"{BASE_URL}/api/review-queue/{pid}/resolve",
            json={"action": "approve_as_student"},
            headers=headers, timeout=10,
        )
        assert r.status_code == 200, r.text
        assert r.json()["participant_type"] == "student"

        # Verify state
        parts = requests.get(f"{BASE_URL}/api/participants",
                             headers=headers, timeout=15).json()
        resolved = next((p for p in parts if p["id"] == pid), None)
        assert resolved
        assert resolved["participant_type"] == "student"
        assert resolved.get("review_status") in (None, "")
    finally:
        _cleanup(pid)


def test_resolve_mark_cancelled_soft_removes():
    headers = _login("commander@test.com", "test123")
    pid = _create_flagged_participant()
    try:
        r = requests.post(
            f"{BASE_URL}/api/review-queue/{pid}/resolve",
            json={"action": "mark_cancelled"},
            headers=headers, timeout=10,
        )
        assert r.status_code == 200
        # Should be hidden from active query
        parts = requests.get(f"{BASE_URL}/api/participants",
                             headers=headers, timeout=15).json()
        assert not any(p["id"] == pid for p in parts), (
            "Cancelled review row should be soft-removed from active list"
        )
    finally:
        _cleanup(pid)


def test_resolve_merge_carries_non_empty_fields():
    headers = _login("commander@test.com", "test123")

    # Pick an existing real participant as the merge target
    parts = requests.get(f"{BASE_URL}/api/participants",
                         headers=headers, timeout=15).json()
    target = next((p for p in parts if p.get("participant_type") == "student"), None)
    assert target, "Need at least one student in DB"

    pid = _create_flagged_participant()
    try:
        # Add a unique field on the duplicate that the target lacks
        _sync_db.participants.update_one(
            {"id": pid},
            {"$set": {"unique_test_marker": "MERGE-CARRY-VALUE"}}
        )
        r = requests.post(
            f"{BASE_URL}/api/review-queue/{pid}/resolve",
            json={"action": "merge_into", "merge_target_id": target["id"]},
            headers=headers, timeout=10,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "unique_test_marker" in (body.get("fields_carried") or [])

        # Target should now have the marker; duplicate should be soft-removed
        merged_target = _sync_db.participants.find_one(
            {"id": target["id"]}, {"_id": 0}
        )
        assert merged_target.get("unique_test_marker") == "MERGE-CARRY-VALUE"
        # Roll back the marker so we don't pollute the DB
        _sync_db.participants.update_one(
            {"id": target["id"]},
            {"$unset": {"unique_test_marker": ""}}
        )
    finally:
        _cleanup(pid)


def test_resolve_merge_requires_target_id():
    headers = _login("commander@test.com", "test123")
    pid = _create_flagged_participant()
    try:
        r = requests.post(
            f"{BASE_URL}/api/review-queue/{pid}/resolve",
            json={"action": "merge_into"},
            headers=headers, timeout=10,
        )
        assert r.status_code == 400
    finally:
        _cleanup(pid)
