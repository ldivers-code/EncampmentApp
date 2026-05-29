"""Backend tests for Phase 8: Google Sheets tab auto-discovery + bulk-add."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cadre-hub.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

CAST_ID = "16rG0RaIzVKjWc0TJe8f4ET7Nxpro8SGJkjOrJbdeaGM"
CAST_URL = f"https://docs.google.com/spreadsheets/d/{CAST_ID}/edit"


def _login(email: str, password: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} -> {r.status_code}: {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def commander_token():
    return _login("commander@test.com", "test123")


@pytest.fixture(scope="module")
def to_token():
    return _login("to@test.com", "test123")


def _h(t):
    return {"Authorization": f"Bearer {t}"}


# ── Cleanup state before testing — start from a clean schedules list ────
@pytest.fixture(scope="module", autouse=True)
def reset_schedules(commander_token):
    # Reset settings.schedules to empty for deterministic dedup/bulk-add tests
    r = requests.post(
        f"{API}/google-sheets/settings",
        headers=_h(commander_token),
        json={"schedules": [], "sync_interval_hours": 1, "auto_sync_enabled": True},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    yield
    # Final cleanup
    requests.post(
        f"{API}/google-sheets/settings",
        headers=_h(commander_token),
        json={"schedules": [], "sync_interval_hours": 1, "auto_sync_enabled": True},
        timeout=30,
    )


# ── discover-tabs happy path ────────────────────────────────────────────
class TestDiscoverTabs:
    def test_discover_with_raw_id(self, commander_token):
        r = requests.post(
            f"{API}/google-sheets/discover-tabs",
            headers=_h(commander_token),
            json={"spreadsheet_id": CAST_ID},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["spreadsheet_id"] == CAST_ID
        assert isinstance(data["tabs"], list)
        assert len(data["tabs"]) == 4, f"Expected 4 tabs, got {len(data['tabs'])}: {[t['sheet_name'] for t in data['tabs']]}"
        # All four tabs should have parsed_date
        for tab in data["tabs"]:
            assert tab["parsed_date"] is not None, f"Tab {tab['sheet_name']} missing parsed_date (a1={tab['a1']})"
            assert tab["looks_like_schedule"] is True
            assert "sheet_name" in tab and tab["sheet_name"]
            assert "suggested_label" in tab
        assert data["schedule_tab_count"] == 4

    def test_discover_with_full_url(self, commander_token):
        r = requests.post(
            f"{API}/google-sheets/discover-tabs",
            headers=_h(commander_token),
            json={"spreadsheet_id": CAST_URL},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        assert r.json()["spreadsheet_id"] == CAST_ID

    def test_discover_forbidden_for_non_admin(self, to_token):
        r = requests.post(
            f"{API}/google-sheets/discover-tabs",
            headers=_h(to_token),
            json={"spreadsheet_id": CAST_ID},
            timeout=30,
        )
        assert r.status_code == 403, f"training_officer should be 403, got {r.status_code}: {r.text}"

    def test_discover_invalid_id(self, commander_token):
        r = requests.post(
            f"{API}/google-sheets/discover-tabs",
            headers=_h(commander_token),
            json={"spreadsheet_id": "NOT_A_REAL_SPREADSHEET_ID_XYZ_12345"},
            timeout=60,
        )
        assert r.status_code == 400, f"Expected 400 for bogus id, got {r.status_code}: {r.text}"
        body = r.json()
        assert "detail" in body and body["detail"]


# ── bulk-add ────────────────────────────────────────────────────────────
class TestBulkAdd:
    def test_bulk_add_basic_and_dedup_and_id_uniqueness(self, commander_token):
        # Discover real tabs first
        d = requests.post(
            f"{API}/google-sheets/discover-tabs",
            headers=_h(commander_token),
            json={"spreadsheet_id": CAST_ID},
            timeout=60,
        )
        assert d.status_code == 200, d.text
        tabs = d.json()["tabs"]
        assert len(tabs) == 4

        # 1) Bulk add all 4
        payload_tabs = [{"sheet_name": t["sheet_name"], "label": t["suggested_label"]} for t in tabs]
        r = requests.post(
            f"{API}/google-sheets/schedules/bulk-add",
            headers=_h(commander_token),
            json={"spreadsheet_id": CAST_ID, "tabs": payload_tabs},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["added"] == 4, f"Expected added=4, got {body}"
        assert body["skipped"] == 0
        assert body["total_schedules"] == 4

        # Verify saved schedules carry sheet_name (not gid)
        s = requests.get(f"{API}/google-sheets/settings", headers=_h(commander_token), timeout=30)
        assert s.status_code == 200
        schedules = s.json()["schedules"]
        assert len(schedules) == 4
        for sched in schedules:
            assert sched.get("sheet_name"), f"schedule missing sheet_name: {sched}"
            assert sched.get("gid") in (None, ""), f"schedule should not have gid: {sched}"
            assert sched["spreadsheet_id"] == CAST_ID

        # 2) Dedup: re-add same tabs should skip all 4
        r2 = requests.post(
            f"{API}/google-sheets/schedules/bulk-add",
            headers=_h(commander_token),
            json={"spreadsheet_id": CAST_ID, "tabs": payload_tabs},
            timeout=30,
        )
        assert r2.status_code == 200, r2.text
        b2 = r2.json()
        assert b2["added"] == 0, f"Expected added=0 on dedup, got {b2}"
        assert b2["skipped"] == 4
        assert b2["total_schedules"] == 4

        # 3) ID uniqueness: add tabs with colliding labels using a fake-but-different sheet_name set
        # to verify auto-suffix of slug. Use a different spreadsheet_id so dedup doesn't kick in.
        FAKE_SID = "FAKE_SPREADSHEET_FOR_ID_TEST_001"
        r3 = requests.post(
            f"{API}/google-sheets/schedules/bulk-add",
            headers=_h(commander_token),
            json={
                "spreadsheet_id": FAKE_SID,
                "tabs": [
                    {"sheet_name": "Tab A", "label": "Same Label"},
                    {"sheet_name": "Tab B", "label": "Same Label"},
                    {"sheet_name": "Tab C", "label": "Same Label"},
                ],
            },
            timeout=30,
        )
        assert r3.status_code == 200, r3.text
        b3 = r3.json()
        assert b3["added"] == 3

        s2 = requests.get(f"{API}/google-sheets/settings", headers=_h(commander_token), timeout=30)
        new_ones = [x for x in s2.json()["schedules"] if x["spreadsheet_id"] == FAKE_SID]
        ids = sorted(x["id"] for x in new_ones)
        # Expect base, base_2, base_3 pattern
        assert len(ids) == 3
        assert ids[0] == "same_label"
        assert ids[1] == "same_label_2"
        assert ids[2] == "same_label_3"

    def test_bulk_add_forbidden_non_admin(self, to_token):
        r = requests.post(
            f"{API}/google-sheets/schedules/bulk-add",
            headers=_h(to_token),
            json={"spreadsheet_id": CAST_ID, "tabs": [{"sheet_name": "x", "label": "x"}]},
            timeout=30,
        )
        assert r.status_code == 403


# ── End-to-end: sync via sheet_name ─────────────────────────────────────
class TestSyncViaSheetName:
    def test_sync_sat_may_30_tab(self, commander_token):
        # Settings should contain our schedules from the previous class.
        # Find the schedule whose sheet_name contains 'May 30' or 'Sat May 30'
        s = requests.get(f"{API}/google-sheets/settings", headers=_h(commander_token), timeout=30)
        assert s.status_code == 200
        schedules = s.json()["schedules"]
        target = None
        for sched in schedules:
            name = (sched.get("sheet_name") or "").lower()
            if "may 30" in name or "5/30" in name or "sat may 30" in name:
                target = sched
                break
        if not target:
            # Re-discover and bulk-add to repopulate
            d = requests.post(
                f"{API}/google-sheets/discover-tabs",
                headers=_h(commander_token),
                json={"spreadsheet_id": CAST_ID},
                timeout=60,
            )
            tabs = d.json()["tabs"]
            payload_tabs = [{"sheet_name": t["sheet_name"], "label": t["suggested_label"]} for t in tabs]
            requests.post(
                f"{API}/google-sheets/schedules/bulk-add",
                headers=_h(commander_token),
                json={"spreadsheet_id": CAST_ID, "tabs": payload_tabs},
                timeout=30,
            )
            s = requests.get(f"{API}/google-sheets/settings", headers=_h(commander_token), timeout=30)
            schedules = s.json()["schedules"]
            for sched in schedules:
                name = (sched.get("sheet_name") or "").lower()
                if "may 30" in name:
                    target = sched
                    break

        assert target is not None, f"Could not find 'Sat May 30th' schedule among: {[x.get('sheet_name') for x in schedules]}"

        # Trigger sync
        r = requests.post(
            f"{API}/google-sheets/schedules/{target['id']}/sync",
            headers=_h(commander_token),
            timeout=120,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("success") is True, f"Sync failed: {body}"
        assert body.get("format") == "grid"
        assert body.get("date") == "2026-05-30", f"Date mismatch: {body.get('date')}"
        # Expect ~54 events (allow ±10 wiggle room)
        ec = body.get("event_count", 0)
        assert 40 <= ec <= 70, f"Expected ~54 events, got {ec}"
