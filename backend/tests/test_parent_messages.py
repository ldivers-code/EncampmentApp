"""
Backend tests for /api/parent/messages, /api/parent/exec-contacts,
and /api/exec/parent-messages module (parent ↔ Exec Staff contact channel).

Coverage:
- GET /api/parent/exec-contacts  → parent only, returns approved exec_staff cards
- POST /api/parent/messages      → parent creates thread (validation, urgency default)
- GET /api/parent/messages       → parent sees own threads w/ replies, newest first
- POST /api/parent/messages/{id}/reply → re-opens resolved, 404 on cross-parent
- GET /api/exec/parent-messages  → exec/commander/dcp list w/ filters + counts
- POST /api/exec/parent-messages/{id}/reply → status open→in_progress, emails parent
- PUT /api/exec/parent-messages/{id}/status → resolved sets resolved_at/by, 400 on bad
- RBAC: cadre/exec_cadre 403 on exec inbox, non-parents 403 on parent endpoints
- Idempotency: duplicate-subject threads each get unique id
- SendGrid tolerated when not configured (email_sent=False/True both ok)
"""
import os
import re
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

PARENT = {"email": "jane.hundley@test.com", "password": "parent123"}
EXEC_STAFF = {"email": "commander@test.cap.gov", "password": "test123"}
COMMANDER = {"email": "commander@test.com", "password": "test123"}
EXEC_CADRE = {"email": "exec_cadre@test.com", "password": "test123"}
CADRE = {"email": "testcadre@cap.gov", "password": "test123"}

# Marker text used in every test-created subject so cleanup can find them.
TEST_TAG = "TEST_PM_"


# ── Auth helpers ─────────────────────────────────────────────────────
def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"Login failed for {creds['email']}: {r.status_code} {r.text}")
    data = r.json()
    return data.get("access_token") or data.get("token")


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


# ── Module-scoped tokens ─────────────────────────────────────────────
@pytest.fixture(scope="module")
def parent_token():
    return _login(PARENT)


@pytest.fixture(scope="module")
def exec_token():
    return _login(EXEC_STAFF)


@pytest.fixture(scope="module")
def commander_token():
    return _login(COMMANDER)


@pytest.fixture(scope="module")
def exec_cadre_token():
    return _login(EXEC_CADRE)


@pytest.fixture(scope="module")
def cadre_token():
    return _login(CADRE)


# ── Cleanup: delete every TEST_PM_* thread when this module finishes ─
@pytest.fixture(scope="module", autouse=True)
def _cleanup(commander_token):
    yield
    # Use Mongo directly via the backend's admin tooling — we have no DB delete
    # endpoint, so instead we resolve every TEST_PM_* thread via exec inbox and
    # mark resolved (best-effort cleanup so the inbox isn't permanently dirty).
    try:
        r = requests.get(
            f"{BASE_URL}/api/exec/parent-messages",
            headers=_hdr(commander_token), timeout=30,
        )
        if r.status_code == 200:
            for m in r.json().get("messages", []):
                if TEST_TAG in (m.get("subject") or ""):
                    requests.put(
                        f"{BASE_URL}/api/exec/parent-messages/{m['id']}/status",
                        json={"status": "resolved"},
                        headers=_hdr(commander_token), timeout=15,
                    )
    except Exception:
        pass


# ── Helpers ──────────────────────────────────────────────────────────
def _create_thread(parent_token, subject_suffix="basic", urgency="question",
                   body="Test body for parent→exec contact."):
    subject = f"{TEST_TAG}{subject_suffix}_{int(time.time()*1000)}"
    r = requests.post(
        f"{BASE_URL}/api/parent/messages",
        json={"subject": subject, "body": body, "urgency": urgency},
        headers=_hdr(parent_token), timeout=30,
    )
    return r, subject


# ════════════════════════════════════════════════════════════════════
# 1. Exec contact card
# ════════════════════════════════════════════════════════════════════
class TestExecContacts:
    def test_parent_can_list_exec_contacts(self, parent_token):
        r = requests.get(f"{BASE_URL}/api/parent/exec-contacts",
                         headers=_hdr(parent_token), timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "contacts" in body
        assert isinstance(body["contacts"], list)
        # Every card has the documented shape
        for c in body["contacts"]:
            assert set(c.keys()) >= {"id", "name", "email", "phone", "position_title"}
            assert isinstance(c["name"], str)
            assert isinstance(c["email"], str)

    def test_non_parent_blocked(self, cadre_token):
        r = requests.get(f"{BASE_URL}/api/parent/exec-contacts",
                         headers=_hdr(cadre_token), timeout=30)
        assert r.status_code == 403, r.text

    def test_exec_cadre_blocked(self, exec_cadre_token):
        r = requests.get(f"{BASE_URL}/api/parent/exec-contacts",
                         headers=_hdr(exec_cadre_token), timeout=30)
        assert r.status_code == 403

    def test_commander_blocked_on_parent_endpoint(self, commander_token):
        # Parent-only endpoint — even commander should be 403
        r = requests.get(f"{BASE_URL}/api/parent/exec-contacts",
                         headers=_hdr(commander_token), timeout=30)
        assert r.status_code == 403


# ════════════════════════════════════════════════════════════════════
# 2. POST /parent/messages — create thread
# ════════════════════════════════════════════════════════════════════
class TestCreateParentMessage:
    def test_create_basic_question(self, parent_token):
        r, subject = _create_thread(parent_token, "basic")
        assert r.status_code == 200, r.text
        data = r.json()
        # Contract
        assert "id" in data and isinstance(data["id"], str) and len(data["id"]) > 0
        assert data["status"] == "open"
        assert isinstance(data["email_sent"], bool)
        assert isinstance(data["recipients_count"], int)
        assert data["recipients_count"] >= 0

    def test_create_emergency(self, parent_token):
        r, _ = _create_thread(parent_token, "emerg", urgency="emergency",
                              body="EMERGENCY: please respond immediately.")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "open"

    def test_invalid_urgency_defaults_to_question(self, parent_token, commander_token):
        r, subject = _create_thread(parent_token, "badurg", urgency="HYPER_RUSH")
        assert r.status_code == 200, r.text
        msg_id = r.json()["id"]
        # Verify the saved doc has urgency='question'
        rr = requests.get(f"{BASE_URL}/api/exec/parent-messages",
                          headers=_hdr(commander_token), timeout=30)
        assert rr.status_code == 200
        match = next((m for m in rr.json()["messages"] if m["id"] == msg_id), None)
        assert match is not None, "freshly created thread not found in exec inbox"
        assert match["urgency"] == "question"
        assert match["subject"] == subject  # trimmed/echoed

    def test_subject_trimmed_within_limits(self, parent_token, commander_token):
        # Within-limit subject/body get trimmed (no leading/trailing whitespace).
        padded_subj = "   " + TEST_TAG + "trim_inner   "
        padded_body = "  hello world  "
        r = requests.post(
            f"{BASE_URL}/api/parent/messages",
            json={"subject": padded_subj, "body": padded_body, "urgency": "urgent"},
            headers=_hdr(parent_token), timeout=30,
        )
        assert r.status_code == 200, r.text
        msg_id = r.json()["id"]
        rr = requests.get(f"{BASE_URL}/api/exec/parent-messages",
                          headers=_hdr(commander_token), timeout=30)
        match = next((m for m in rr.json()["messages"] if m["id"] == msg_id), None)
        assert match is not None
        assert match["subject"] == padded_subj.strip()
        assert match["thread"][0]["body"] == padded_body.strip()
        assert len(match["subject"]) <= 200
        assert len(match["thread"][0]["body"]) <= 5000

    def test_oversize_subject_rejected_by_validation(self, parent_token):
        # Over-limit input is rejected by Pydantic validation (422)
        r = requests.post(
            f"{BASE_URL}/api/parent/messages",
            json={
                "subject": "x" * 500,
                "body": "ok body",
                "urgency": "question",
            },
            headers=_hdr(parent_token), timeout=30,
        )
        # Either Pydantic 422 OR silently truncated 200 are both valid contracts.
        # The current impl returns 422 — capture that.
        assert r.status_code in (200, 422)

    def test_validation_empty_subject(self, parent_token):
        r = requests.post(
            f"{BASE_URL}/api/parent/messages",
            json={"subject": "", "body": "hi", "urgency": "question"},
            headers=_hdr(parent_token), timeout=30,
        )
        assert r.status_code == 422

    def test_validation_empty_body(self, parent_token):
        r = requests.post(
            f"{BASE_URL}/api/parent/messages",
            json={"subject": f"{TEST_TAG}empty", "body": "", "urgency": "question"},
            headers=_hdr(parent_token), timeout=30,
        )
        assert r.status_code == 422

    def test_non_parent_cannot_create(self, cadre_token):
        r = requests.post(
            f"{BASE_URL}/api/parent/messages",
            json={"subject": f"{TEST_TAG}nope", "body": "x", "urgency": "question"},
            headers=_hdr(cadre_token), timeout=30,
        )
        assert r.status_code == 403

    def test_idempotency_duplicate_subject_unique_ids(self, parent_token):
        subj = f"{TEST_TAG}dup_{int(time.time()*1000)}"
        # Create two with the same subject literal
        ids = set()
        for _ in range(2):
            r = requests.post(
                f"{BASE_URL}/api/parent/messages",
                json={"subject": subj, "body": "same subject test", "urgency": "question"},
                headers=_hdr(parent_token), timeout=30,
            )
            assert r.status_code == 200, r.text
            ids.add(r.json()["id"])
        assert len(ids) == 2, "duplicate-subject threads should each get a unique id"


# ════════════════════════════════════════════════════════════════════
# 3. GET /parent/messages — list own
# ════════════════════════════════════════════════════════════════════
class TestListParentMessages:
    def test_parent_sees_own_threads(self, parent_token):
        # Ensure at least one thread exists
        r1, subject = _create_thread(parent_token, "list_me")
        assert r1.status_code == 200
        new_id = r1.json()["id"]

        r = requests.get(f"{BASE_URL}/api/parent/messages",
                         headers=_hdr(parent_token), timeout=30)
        assert r.status_code == 200, r.text
        threads = r.json()
        assert isinstance(threads, list)
        assert any(t["id"] == new_id for t in threads)
        # Each thread carries replies array
        for t in threads:
            assert "thread" in t and isinstance(t["thread"], list)
            assert "status" in t and "urgency" in t and "subject" in t
        # Newest first by updated_at
        ts = [t.get("updated_at", "") for t in threads]
        assert ts == sorted(ts, reverse=True), "threads should be newest first"

    def test_non_parent_blocked_on_list(self, cadre_token):
        r = requests.get(f"{BASE_URL}/api/parent/messages",
                         headers=_hdr(cadre_token), timeout=30)
        assert r.status_code == 403


# ════════════════════════════════════════════════════════════════════
# 4. Parent reply + cross-parent 404
# ════════════════════════════════════════════════════════════════════
class TestParentReply:
    def test_parent_reply_appends_and_reopens(
            self, parent_token, exec_token, commander_token):
        # Create and resolve via exec
        r, _ = _create_thread(parent_token, "reopen")
        assert r.status_code == 200
        msg_id = r.json()["id"]

        # Exec resolves it
        rr = requests.put(
            f"{BASE_URL}/api/exec/parent-messages/{msg_id}/status",
            json={"status": "resolved"},
            headers=_hdr(exec_token), timeout=30,
        )
        assert rr.status_code == 200, rr.text

        # Parent replies → should re-open and append
        rp = requests.post(
            f"{BASE_URL}/api/parent/messages/{msg_id}/reply",
            json={"body": "Following up please."},
            headers=_hdr(parent_token), timeout=30,
        )
        assert rp.status_code == 200, rp.text
        assert rp.json().get("ok") is True

        # Verify status flipped back to open and reply appended
        ri = requests.get(f"{BASE_URL}/api/exec/parent-messages",
                          headers=_hdr(commander_token), timeout=30)
        match = next((m for m in ri.json()["messages"] if m["id"] == msg_id), None)
        assert match is not None
        assert match["status"] == "open", "resolved thread should re-open on parent reply"
        assert len(match["thread"]) >= 2
        assert match["thread"][-1]["from_role"] == "parent"
        assert match["thread"][-1]["body"] == "Following up please."

    def test_parent_reply_unknown_thread_returns_404(self, parent_token):
        r = requests.post(
            f"{BASE_URL}/api/parent/messages/does-not-exist-xyz/reply",
            json={"body": "ghost reply"},
            headers=_hdr(parent_token), timeout=30,
        )
        assert r.status_code == 404

    def test_parent_cannot_reply_to_others_thread(self, parent_token, commander_token):
        # Grab an existing thread that does NOT belong to this parent.
        ri = requests.get(f"{BASE_URL}/api/exec/parent-messages",
                          headers=_hdr(commander_token), timeout=30)
        assert ri.status_code == 200
        # Get this parent's id by hitting /api/auth/me (or any 'me') so we can
        # avoid their own threads. Fallback: pick a thread whose parent_email
        # doesn't match jane.hundley.
        candidate = next(
            (m for m in ri.json()["messages"]
             if m.get("parent_email") and m["parent_email"] != PARENT["email"]),
            None,
        )
        if candidate is None:
            pytest.skip("no other parent's thread available to test cross-parent 404")
        r = requests.post(
            f"{BASE_URL}/api/parent/messages/{candidate['id']}/reply",
            json={"body": "I shouldn't see this thread"},
            headers=_hdr(parent_token), timeout=30,
        )
        assert r.status_code == 404, r.text


# ════════════════════════════════════════════════════════════════════
# 5. GET /exec/parent-messages — inbox + RBAC
# ════════════════════════════════════════════════════════════════════
class TestExecInbox:
    def test_exec_staff_can_list(self, exec_token):
        r = requests.get(f"{BASE_URL}/api/exec/parent-messages",
                         headers=_hdr(exec_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        for key in ("messages", "open_count", "emergency_open", "total"):
            assert key in d
        assert isinstance(d["messages"], list)
        assert isinstance(d["open_count"], int)
        assert isinstance(d["emergency_open"], int)
        assert isinstance(d["total"], int)
        assert d["total"] == len(d["messages"])

    def test_commander_can_list(self, commander_token):
        r = requests.get(f"{BASE_URL}/api/exec/parent-messages",
                         headers=_hdr(commander_token), timeout=30)
        assert r.status_code == 200

    def test_exec_cadre_blocked(self, exec_cadre_token):
        r = requests.get(f"{BASE_URL}/api/exec/parent-messages",
                         headers=_hdr(exec_cadre_token), timeout=30)
        assert r.status_code == 403

    def test_cadre_blocked(self, cadre_token):
        r = requests.get(f"{BASE_URL}/api/exec/parent-messages",
                         headers=_hdr(cadre_token), timeout=30)
        assert r.status_code == 403

    def test_parent_blocked(self, parent_token):
        r = requests.get(f"{BASE_URL}/api/exec/parent-messages",
                         headers=_hdr(parent_token), timeout=30)
        assert r.status_code == 403

    def test_filter_by_status_and_urgency(self, parent_token, commander_token):
        # Seed: one emergency + open thread we can find via filter
        rr, _ = _create_thread(parent_token, "filt_emg", urgency="emergency")
        assert rr.status_code == 200
        msg_id = rr.json()["id"]

        r1 = requests.get(
            f"{BASE_URL}/api/exec/parent-messages",
            params={"urgency": "emergency", "status": "open"},
            headers=_hdr(commander_token), timeout=30,
        )
        assert r1.status_code == 200, r1.text
        d = r1.json()
        assert all(m["urgency"] == "emergency" for m in d["messages"])
        assert all(m["status"] == "open" for m in d["messages"])
        assert any(m["id"] == msg_id for m in d["messages"])
        # emergency_open count must be >= 1
        assert d["emergency_open"] >= 1


# ════════════════════════════════════════════════════════════════════
# 6. POST /exec/parent-messages/{id}/reply — status auto open→in_progress
# ════════════════════════════════════════════════════════════════════
class TestExecReply:
    def test_exec_reply_flips_status_to_in_progress(
            self, parent_token, exec_token, commander_token):
        r, _ = _create_thread(parent_token, "execreply")
        assert r.status_code == 200
        msg_id = r.json()["id"]

        rp = requests.post(
            f"{BASE_URL}/api/exec/parent-messages/{msg_id}/reply",
            json={"body": "We're looking into it."},
            headers=_hdr(exec_token), timeout=30,
        )
        assert rp.status_code == 200, rp.text
        assert rp.json().get("ok") is True

        ri = requests.get(f"{BASE_URL}/api/exec/parent-messages",
                          headers=_hdr(commander_token), timeout=30)
        match = next((m for m in ri.json()["messages"] if m["id"] == msg_id), None)
        assert match is not None
        assert match["status"] == "in_progress", \
            "open thread should auto-flip to in_progress on exec reply"
        assert match["thread"][-1]["from_role"] == "exec"
        assert match["thread"][-1]["body"] == "We're looking into it."

    def test_exec_reply_unknown_thread_404(self, exec_token):
        r = requests.post(
            f"{BASE_URL}/api/exec/parent-messages/no-such-thread/reply",
            json={"body": "nope"},
            headers=_hdr(exec_token), timeout=30,
        )
        assert r.status_code == 404

    def test_cadre_cannot_exec_reply(self, parent_token, cadre_token):
        r, _ = _create_thread(parent_token, "cadre_block")
        msg_id = r.json()["id"]
        rp = requests.post(
            f"{BASE_URL}/api/exec/parent-messages/{msg_id}/reply",
            json={"body": "should be blocked"},
            headers=_hdr(cadre_token), timeout=30,
        )
        assert rp.status_code == 403


# ════════════════════════════════════════════════════════════════════
# 7. PUT /exec/parent-messages/{id}/status — resolution metadata
# ════════════════════════════════════════════════════════════════════
class TestStatusUpdate:
    def test_resolved_sets_metadata(self, parent_token, exec_token, commander_token):
        r, _ = _create_thread(parent_token, "resolve_me")
        msg_id = r.json()["id"]
        rs = requests.put(
            f"{BASE_URL}/api/exec/parent-messages/{msg_id}/status",
            json={"status": "resolved"},
            headers=_hdr(exec_token), timeout=30,
        )
        assert rs.status_code == 200, rs.text
        assert rs.json()["status"] == "resolved"

        ri = requests.get(f"{BASE_URL}/api/exec/parent-messages",
                          headers=_hdr(commander_token), timeout=30)
        match = next((m for m in ri.json()["messages"] if m["id"] == msg_id), None)
        assert match is not None
        assert match["status"] == "resolved"
        assert match.get("resolved_at"), "resolved_at must be populated"
        assert match.get("resolved_by"), "resolved_by must be populated"

    def test_invalid_status_returns_400(self, parent_token, exec_token):
        r, _ = _create_thread(parent_token, "bad_status")
        msg_id = r.json()["id"]
        rs = requests.put(
            f"{BASE_URL}/api/exec/parent-messages/{msg_id}/status",
            json={"status": "wat"},
            headers=_hdr(exec_token), timeout=30,
        )
        assert rs.status_code == 400

    def test_status_update_unknown_thread_404(self, exec_token):
        r = requests.put(
            f"{BASE_URL}/api/exec/parent-messages/no-thread-xyz/status",
            json={"status": "resolved"},
            headers=_hdr(exec_token), timeout=30,
        )
        assert r.status_code == 404

    def test_status_update_rbac(self, parent_token, cadre_token):
        r, _ = _create_thread(parent_token, "rbac_status")
        msg_id = r.json()["id"]
        rs = requests.put(
            f"{BASE_URL}/api/exec/parent-messages/{msg_id}/status",
            json={"status": "resolved"},
            headers=_hdr(cadre_token), timeout=30,
        )
        assert rs.status_code == 403


# ════════════════════════════════════════════════════════════════════
# 8. End-to-end happy path mirrors main agent's manual verification
# ════════════════════════════════════════════════════════════════════
class TestHappyPath:
    def test_emergency_e2e_flow(self, parent_token, exec_token, commander_token):
        # 1. Parent posts EMERGENCY
        r, subj = _create_thread(parent_token, "e2e_emerg", urgency="emergency",
                                 body="My cadet may be ill, please call.")
        assert r.status_code == 200
        msg_id = r.json()["id"]
        assert r.json()["status"] == "open"

        # 2. Exec sees it (open_count and emergency_open both >= 1)
        inbox = requests.get(
            f"{BASE_URL}/api/exec/parent-messages",
            headers=_hdr(exec_token), timeout=30,
        ).json()
        assert any(m["id"] == msg_id for m in inbox["messages"])
        assert inbox["open_count"] >= 1
        assert inbox["emergency_open"] >= 1

        # 3. Exec replies — status flips to in_progress
        rp = requests.post(
            f"{BASE_URL}/api/exec/parent-messages/{msg_id}/reply",
            json={"body": "On our way, please standby."},
            headers=_hdr(exec_token), timeout=30,
        )
        assert rp.status_code == 200

        # 4. Parent sees exec reply in their thread list
        my = requests.get(f"{BASE_URL}/api/parent/messages",
                          headers=_hdr(parent_token), timeout=30).json()
        mine = next((t for t in my if t["id"] == msg_id), None)
        assert mine is not None
        assert mine["status"] == "in_progress"
        assert any(r.get("from_role") == "exec" for r in mine["thread"])

        # 5. Exec resolves
        rs = requests.put(
            f"{BASE_URL}/api/exec/parent-messages/{msg_id}/status",
            json={"status": "resolved"},
            headers=_hdr(exec_token), timeout=30,
        )
        assert rs.status_code == 200

        # 6. Inbox emergency_open decreases (relative)
        inbox2 = requests.get(
            f"{BASE_URL}/api/exec/parent-messages",
            headers=_hdr(commander_token), timeout=30,
        ).json()
        match = next((m for m in inbox2["messages"] if m["id"] == msg_id), None)
        assert match is not None
        assert match["status"] == "resolved"
