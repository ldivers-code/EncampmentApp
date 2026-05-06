"""Tests for bulk participant type-change and bulk-delete endpoints + Excel export with shirt_size."""
import os
import io
import uuid
import pytest
import requests
import openpyxl

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def commander_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "commander@test.com", "password": "test123"})
    if r.status_code != 200:
        pytest.skip(f"Commander login failed: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def created_participants(commander_session):
    """Create 3 disposable test participants (TEST_ prefix). Cleaned up at end."""
    ids = []
    for i in range(3):
        payload = {
            "capid": f"9{uuid.uuid4().int % 10000000:07d}",
            "rank": "C/Amn",
            "first_name": "TESTBulk",
            "last_name": f"User{i}_{uuid.uuid4().hex[:6]}",
            "unit": "TN001",
            "wing": "TNWG",
            "gender": "M",
            "age": 16,
            "email": f"test_bulk_{i}_{uuid.uuid4().hex[:6]}@test.com",
            "shirt_size": "M",
            "participant_type": "basic_student",
        }
        r = commander_session.post(f"{API}/participants", json=payload)
        assert r.status_code in (200, 201), f"create failed: {r.status_code} {r.text[:200]}"
        ids.append(r.json()["id"])
    yield ids
    # Cleanup any survivors
    commander_session.post(f"{API}/participants/bulk-delete", json={"participant_ids": ids, "confirm": True})


class TestBulkChangeType:
    def test_bulk_change_to_cadre(self, commander_session, created_participants):
        ids = created_participants
        r = commander_session.put(f"{API}/participants/bulk-type",
                                  json={"participant_ids": ids, "new_type": "cadre"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["modified"] >= len(ids)
        assert body["new_type"] == "cadre"
        # Verify persistence via GET
        for pid in ids:
            g = commander_session.get(f"{API}/participants/{pid}")
            assert g.status_code == 200
            assert g.json()["participant_type"] == "cadre"

    def test_bulk_change_to_staff(self, commander_session, created_participants):
        ids = created_participants
        r = commander_session.put(f"{API}/participants/bulk-type",
                                  json={"participant_ids": ids, "new_type": "staff"})
        assert r.status_code == 200
        for pid in ids:
            g = commander_session.get(f"{API}/participants/{pid}")
            assert g.json()["participant_type"] == "staff"

    def test_bulk_change_back_to_student(self, commander_session, created_participants):
        ids = created_participants
        r = commander_session.put(f"{API}/participants/bulk-type",
                                  json={"participant_ids": ids, "new_type": "basic_student"})
        assert r.status_code == 200

    def test_bulk_invalid_type(self, commander_session, created_participants):
        r = commander_session.put(f"{API}/participants/bulk-type",
                                  json={"participant_ids": created_participants, "new_type": "garbage"})
        assert r.status_code == 400

    def test_bulk_empty_ids(self, commander_session):
        r = commander_session.put(f"{API}/participants/bulk-type",
                                  json={"participant_ids": [], "new_type": "cadre"})
        assert r.status_code == 400


class TestBulkDelete:
    def test_bulk_delete_requires_confirm(self, commander_session, created_participants):
        r = commander_session.post(f"{API}/participants/bulk-delete",
                                   json={"participant_ids": created_participants, "confirm": False})
        assert r.status_code == 400

    def test_bulk_delete_success(self, commander_session, created_participants):
        # Delete one of the test participants and verify removal
        target = [created_participants[-1]]
        r = commander_session.post(f"{API}/participants/bulk-delete",
                                   json={"participant_ids": target, "confirm": True})
        assert r.status_code == 200, r.text
        assert r.json()["deleted"] >= 1
        # Verify it returns 404 now
        g = commander_session.get(f"{API}/participants/{target[0]}")
        assert g.status_code == 404


class TestExcelExportShirtSize:
    def test_excel_export_includes_shirt_size(self, commander_session):
        r = commander_session.get(f"{API}/participants/analytics/export?format=excel")
        assert r.status_code == 200, r.text[:200]
        ct = r.headers.get("content-type", "")
        assert "spreadsheet" in ct or "excel" in ct or "octet-stream" in ct, ct
        wb = openpyxl.load_workbook(io.BytesIO(r.content), data_only=True)
        ws = wb.active
        headers = [str(c.value or "").strip().lower() for c in next(ws.iter_rows(min_row=1, max_row=1))]
        assert any("shirt" in h for h in headers), f"shirt_size column missing in headers: {headers}"


class TestBulkRBAC:
    def test_unauthenticated_bulk_type_blocked(self):
        r = requests.put(f"{API}/participants/bulk-type",
                         json={"participant_ids": ["x"], "new_type": "cadre"})
        assert r.status_code in (401, 403)

    def test_unauthenticated_bulk_delete_blocked(self):
        r = requests.post(f"{API}/participants/bulk-delete",
                          json={"participant_ids": ["x"], "confirm": True})
        assert r.status_code in (401, 403)
