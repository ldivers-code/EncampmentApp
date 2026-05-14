"""Phase 4 — Unit tests for account_status helper.

These tests don't hit the live backend; they exercise the policy module
directly with mocked DB access so the rules are pinned independently.

We use asyncio.run() instead of pytest-asyncio so the suite stays
dependency-free.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

from account_status import compute_account_status


def _mock_db(participant_doc=None):
    """Build a tiny mock that responds to db.participants.find_one() once."""
    db = MagicMock()
    db.participants.find_one = AsyncMock(return_value=participant_doc)
    return db


def _run(coro):
    return asyncio.run(coro)


# ── account_status derivation ─────────────────────────────────────────────

def test_pending_user_status_is_pending_approval():
    db = _mock_db()
    user = {"id": "u1", "role": "cadre", "is_approved": False}
    s = _run(compute_account_status(db, user))
    assert s["account_status"] == "pending_approval"
    assert s["is_approved"] is False
    assert s["participant_link_status"] == "unlinked"
    assert s["encampment_participant_type"] is None
    assert s["permission_role"] == "cadre"


def test_approved_but_unlinked_status():
    db = _mock_db()
    user = {"id": "u2", "role": "student", "is_approved": True,
            "linked_participant_id": None}
    s = _run(compute_account_status(db, user))
    assert s["account_status"] == "approved_unlinked"
    assert s["is_approved"] is True
    assert s["participant_link_status"] == "unlinked"
    assert s["linked_participant_id"] is None


def test_approved_and_linked_status():
    db = _mock_db({
        "id": "p1", "participant_type": "cadre", "flight": "alpha",
        "squadron": "6th_cts", "position": "flight_sergeant",
    })
    user = {"id": "u3", "role": "cadre", "is_approved": True,
            "linked_participant_id": "p1", "flight": "alpha",
            "cadre_position": "flight_sergeant"}
    s = _run(compute_account_status(db, user))
    assert s["account_status"] == "approved_linked"
    assert s["participant_link_status"] == "linked"
    assert s["encampment_participant_type"] == "cadre"
    assert s["duty_assignment"] is not None
    assert "Flight alpha" in s["duty_assignment"]


def test_stale_linked_id_against_removed_participant_falls_back_to_unlinked():
    """If linked_participant_id points to a removed participant, treat as unlinked."""
    db = _mock_db(None)
    user = {"id": "u4", "role": "student", "is_approved": True,
            "linked_participant_id": "removed-p"}
    s = _run(compute_account_status(db, user))
    assert s["account_status"] == "approved_unlinked"
    assert s["participant_link_status"] == "unlinked"
    assert s["linked_participant_id"] == "removed-p", \
        "We expose the stored ID even when it resolves to nothing, so the admin can investigate"


def test_pending_user_with_linked_id_is_still_pending():
    """Parents register WITH a linked participant before approval — they
    must still be reported as pending_approval (not approved_linked)."""
    db = _mock_db({"id": "p1", "participant_type": "student", "flight": "alpha"})
    user = {"id": "u5", "role": "parent", "is_approved": False,
            "linked_participant_id": "p1"}
    s = _run(compute_account_status(db, user))
    assert s["account_status"] == "pending_approval"
    # Linkage data is still surfaced — only the rollup is gated.
    assert s["participant_link_status"] == "linked"
    assert s["encampment_participant_type"] == "student"


def test_six_canonical_fields_always_present():
    """Phase 4 contract: every status payload returns the SAME six fields
    plus the account_status rollup so the client can route deterministically."""
    db = _mock_db()
    user = {"id": "u6", "role": "cadre", "is_approved": False}
    s = _run(compute_account_status(db, user))
    expected = {
        "is_approved", "linked_participant_id", "participant_link_status",
        "encampment_participant_type", "permission_role", "duty_assignment",
        "account_status",
    }
    assert expected.issubset(set(s.keys())), \
        f"Missing canonical fields: {expected - set(s.keys())}"


def test_duty_assignment_is_none_when_no_duty_data():
    db = _mock_db()
    user = {"id": "u7", "role": "student", "is_approved": True,
            "linked_participant_id": None}
    s = _run(compute_account_status(db, user))
    assert s["duty_assignment"] is None


def test_duty_assignment_includes_cadre_position():
    db = _mock_db({"id": "p1", "participant_type": "cadre"})
    user = {"id": "u8", "role": "cadre", "is_approved": True,
            "linked_participant_id": "p1",
            "cadre_position": "flight_commander", "cadre_unit": "ops"}
    s = _run(compute_account_status(db, user))
    assert "flight_commander" in s["duty_assignment"]
    assert "ops" in s["duty_assignment"]
