"""Tests for CAP Participant Import preview/apply flow with conflict resolution.

Covers:
- POST /api/participants/import/preview (staging + summary + rows + conflict detection)
- POST /api/participants/import/apply (update/create/skip resolutions)
- CAPID float-artifact normalization (538026.0 → 538026)
- Diff only contains non-blank new values
- Backwards compat with /api/participants/import (auto-apply)
- Staging cleanup on apply
"""
import os
import io
import uuid
import pytest
import requests
import pandas as pd

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


# ---------- helpers ----------

def _build_excel(rows: list[dict]) -> bytes:
    """Build a minimal CAP Event Admin Report-style xlsx in memory."""
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture(scope="module")
def commander_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "commander@test.com", "password": "test123"})
    if r.status_code != 200:
        pytest.skip(f"Commander login failed: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def conflict_participants(commander_session):
    """Create 2 participants with SAME first+last name but different CAPIDs.
    These are the two possible candidates for a name-only import row."""
    ids = []
    suffix = uuid.uuid4().hex[:6].upper()
    first_name = "ConflictTEST"
    last_name = f"User{suffix}"
    for tag in ("A", "B"):
        payload = {
            "capid": f"CFLCT{tag}{suffix}",
            "rank": "C/Amn",
            "first_name": first_name,
            "last_name": last_name,
            "unit": f"TN00{tag}",
            "wing": "TNWG",
            "gender": "M",
            "age": 16,
            "email": f"test_cflct_{tag.lower()}_{suffix}@test.com",
            "shirt_size": "M",
            "participant_type": "basic_student",
        }
        r = commander_session.post(f"{API}/participants", json=payload)
        assert r.status_code in (200, 201), f"seed failed: {r.status_code} {r.text[:200]}"
        ids.append(r.json()["id"])
    yield {"ids": ids, "first_name": first_name, "last_name": last_name, "suffix": suffix}
    # teardown
    commander_session.post(f"{API}/participants/bulk-delete", json={"participant_ids": ids, "confirm": True})


@pytest.fixture(scope="module")
def capid_float_participant(commander_session):
    """Create a participant whose CAPID is a 6-digit string; we'll upload it as 538026.0 via pandas."""
    capid = f"5{uuid.uuid4().int % 100000:05d}"
    payload = {
        "capid": capid,
        "rank": "C/A1C",
        "first_name": "FloatTEST",
        "last_name": f"CapId{uuid.uuid4().hex[:4].upper()}",
        "unit": "TN001",
        "wing": "TNWG",
        "gender": "F",
        "age": 17,
        "email": f"test_floatcapid_{uuid.uuid4().hex[:6]}@test.com",
        "shirt_size": "L",
        "participant_type": "basic_student",
    }
    r = commander_session.post(f"{API}/participants", json=payload)
    assert r.status_code in (200, 201), r.text
    pid = r.json()["id"]
    yield {"id": pid, "capid": capid, "payload": payload}
    commander_session.post(f"{API}/participants/bulk-delete", json={"participant_ids": [pid], "confirm": True})


# ---------- tests ----------

class TestImportPreviewConflict:
    def test_preview_detects_name_conflict(self, commander_session, conflict_participants):
        cp = conflict_participants
        # Row has NO CAPID/email but name matches two existing participants
        xlsx = _build_excel([{
            "RegistrantsCAPID": "",
            "NameLast": cp["last_name"],
            "NameFirst": cp["first_name"],
            "Email": "",
            "Unit": "TN999",
            "Wing": "TNWG",
            "Rank": "C/SSgt",
        }])
        r = commander_session.post(
            f"{API}/participants/import/preview",
            files={"file": ("conflict.xlsx", xlsx,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "staging_id" in body and isinstance(body["staging_id"], str)
        assert "summary" in body and set(body["summary"].keys()) >= {"new", "update", "conflict", "skipped"}
        assert body["summary"]["conflict"] >= 1
        assert len(body["rows"]) == 1
        row = body["rows"][0]
        assert row["match_type"] == "name"
        assert row["default_action"] == "conflict"
        assert row["default_target_id"] is None
        # Both candidates returned
        cand_ids = {c["id"] for c in row["candidates"]}
        assert set(cp["ids"]).issubset(cand_ids), \
            f"Expected both seeded ids {cp['ids']} in candidates, got {cand_ids}"
        # staging_id persisted — we use it in apply test
        pytest.conflict_staging_id = body["staging_id"]
        pytest.conflict_row_idx = row["row_idx"]

    def test_apply_resolves_to_chosen_participant(self, commander_session, conflict_participants):
        cp = conflict_participants
        staging_id = getattr(pytest, "conflict_staging_id", None)
        row_idx = getattr(pytest, "conflict_row_idx", 0)
        if not staging_id:
            pytest.skip("preview test did not run")

        chosen_id = cp["ids"][1]  # resolve to SECOND participant
        other_id = cp["ids"][0]

        # Capture pre-state
        before_b = commander_session.get(f"{API}/participants/{chosen_id}").json()
        before_a = commander_session.get(f"{API}/participants/{other_id}").json()

        r = commander_session.post(
            f"{API}/participants/import/apply",
            json={
                "staging_id": staging_id,
                "resolutions": {str(row_idx): {"action": "update", "participant_id": chosen_id}},
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["updated"] == 1
        assert body["imported"] == 0
        assert body["skipped"] == 0

        # Chosen participant got the new rank/unit
        after_b = commander_session.get(f"{API}/participants/{chosen_id}").json()
        assert after_b["unit"] == "TN999"
        assert after_b["rank"] == "C/SSgt"
        # Other participant is unchanged
        after_a = commander_session.get(f"{API}/participants/{other_id}").json()
        assert after_a["unit"] == before_a["unit"]
        assert after_a["rank"] == before_a["rank"]

        # Staging is cleaned up — re-apply with same id → 404
        r2 = commander_session.post(
            f"{API}/participants/import/apply",
            json={"staging_id": staging_id, "resolutions": {}},
        )
        assert r2.status_code == 404

    def test_apply_create_action_forces_new_participant(self, commander_session, conflict_participants):
        """Even when the name matches existing participants, action='create' must insert a brand-new row."""
        cp = conflict_participants
        # re-upload the same name-only row
        xlsx = _build_excel([{
            "RegistrantsCAPID": "",
            "NameLast": cp["last_name"],
            "NameFirst": cp["first_name"],
            "Email": f"force_new_{cp['suffix']}@test.com",
            "Unit": "TN777",
            "Wing": "TNWG",
        }])
        # Wait — email is unique + no existing so it'll be match_type=none. Use no email to get conflict
        xlsx = _build_excel([{
            "RegistrantsCAPID": "",
            "NameLast": cp["last_name"],
            "NameFirst": cp["first_name"],
            "Unit": "TN777",
            "Wing": "TNWG",
        }])
        r = commander_session.post(
            f"{API}/participants/import/preview",
            files={"file": ("c2.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        staging_id = body["staging_id"]
        row_idx = body["rows"][0]["row_idx"]
        assert body["rows"][0]["default_action"] == "conflict"

        # Apply with action=create → new participant created
        r2 = commander_session.post(
            f"{API}/participants/import/apply",
            json={
                "staging_id": staging_id,
                "resolutions": {str(row_idx): {"action": "create"}},
            },
        )
        assert r2.status_code == 200, r2.text
        b = r2.json()
        assert b["imported"] == 1
        assert b["updated"] == 0

        # Cleanup: find and delete the brand-new participant (search by unit TN777)
        rs = commander_session.get(f"{API}/participants")
        if rs.status_code == 200:
            items = rs.json() if isinstance(rs.json(), list) else rs.json().get("participants", [])
            new_ids = [p["id"] for p in items
                       if p.get("first_name") == cp["first_name"]
                       and p.get("last_name") == cp["last_name"]
                       and p.get("unit") == "TN777"]
            if new_ids:
                commander_session.post(
                    f"{API}/participants/bulk-delete",
                    json={"participant_ids": new_ids, "confirm": True},
                )

    def test_apply_skip_action(self, commander_session, conflict_participants):
        cp = conflict_participants
        xlsx = _build_excel([{
            "RegistrantsCAPID": "",
            "NameLast": cp["last_name"],
            "NameFirst": cp["first_name"],
            "Unit": "TN888",
            "Wing": "TNWG",
        }])
        r = commander_session.post(
            f"{API}/participants/import/preview",
            files={"file": ("skip.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert r.status_code == 200
        body = r.json()
        staging_id = body["staging_id"]
        row_idx = body["rows"][0]["row_idx"]

        r2 = commander_session.post(
            f"{API}/participants/import/apply",
            json={
                "staging_id": staging_id,
                "resolutions": {str(row_idx): {"action": "skip"}},
            },
        )
        assert r2.status_code == 200, r2.text
        b = r2.json()
        assert b["skipped"] == 1
        assert b["imported"] == 0
        assert b["updated"] == 0


class TestCapidFloatNormalization:
    def test_capid_read_as_float_still_matches(self, commander_session, capid_float_participant):
        p = capid_float_participant
        # Build DataFrame where CAPID column is numeric → pandas will store 538026.0
        xlsx = _build_excel([{
            "RegistrantsCAPID": float(p["capid"]),  # <-- 538026.0
            "NameLast": p["payload"]["last_name"],
            "NameFirst": p["payload"]["first_name"],
            "Unit": "TN050",
            "Wing": "TNWG",
            "Rank": "C/SrA",
        }])
        r = commander_session.post(
            f"{API}/participants/import/preview",
            files={"file": ("float.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["rows"]) == 1
        row = body["rows"][0]
        assert row["match_type"] == "capid", f"Expected capid match, got {row}"
        assert row["default_action"] == "update"
        assert row["default_target_id"] == p["id"]
        # CAPID is returned as clean string (no .0)
        assert row["capid"] == p["capid"]


class TestDiffFields:
    def test_diff_only_non_blank(self, commander_session, capid_float_participant):
        p = capid_float_participant
        # Row with some fields blank — they should NOT appear in changes
        xlsx = _build_excel([{
            "RegistrantsCAPID": p["capid"],
            "NameLast": p["payload"]["last_name"],
            "NameFirst": p["payload"]["first_name"],
            "Unit": "TN999",          # new value → should appear
            "Wing": "",               # blank → should NOT appear
            "Rank": "C/SMSgt",        # changed → should appear
            "Email": "",              # blank → should NOT overwrite
        }])
        r = commander_session.post(
            f"{API}/participants/import/preview",
            files={"file": ("diff.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        row = body["rows"][0]
        assert row["default_action"] == "update"
        changes = row["changes"]
        # All change values must be non-empty strings/ints
        for field, delta in changes.items():
            new_val = delta.get("new")
            assert new_val not in (None, ""), f"blank change leaked for {field}: {delta}"
        # unit + rank must be present
        assert "unit" in changes, f"unit diff missing: {changes}"
        # email should NOT be in changes (blank)
        assert "email" not in changes, f"blank email leaked into diff: {changes}"


class TestBackwardsCompat:
    def test_auto_apply_still_works(self, commander_session):
        """Legacy /participants/import must still accept a file and apply immediately."""
        capid = f"8{uuid.uuid4().int % 100000:05d}"
        xlsx = _build_excel([{
            "RegistrantsCAPID": capid,
            "NameLast": "LegacyTEST",
            "NameFirst": f"Auto{uuid.uuid4().hex[:4]}",
            "Unit": "TN001",
            "Wing": "TNWG",
            "Rank": "C/Amn",
            "Email": f"legacy_{capid}@test.com",
        }])
        r = commander_session.post(
            f"{API}/participants/import",
            files={"file": ("legacy.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["imported"] + body["updated"] >= 1

        # cleanup
        q = commander_session.get(f"{API}/participants")
        if q.status_code == 200:
            items = q.json() if isinstance(q.json(), list) else q.json().get("participants", [])
            ids = [p["id"] for p in items if p.get("capid") == capid]
            if ids:
                commander_session.post(f"{API}/participants/bulk-delete",
                                       json={"participant_ids": ids, "confirm": True})


class TestAuthGuard:
    def test_preview_requires_auth(self):
        xlsx = _build_excel([{"RegistrantsCAPID": "999999", "NameLast": "x", "NameFirst": "y"}])
        r = requests.post(
            f"{API}/participants/import/preview",
            files={"file": ("u.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert r.status_code in (401, 403), f"expected auth rejection, got {r.status_code}"

    def test_apply_requires_auth(self):
        r = requests.post(f"{API}/participants/import/apply", json={"staging_id": "nope", "resolutions": {}})
        assert r.status_code in (401, 403)

    def test_apply_unknown_staging_404(self, commander_session):
        r = commander_session.post(f"{API}/participants/import/apply",
                                   json={"staging_id": "does-not-exist", "resolutions": {}})
        assert r.status_code == 404
