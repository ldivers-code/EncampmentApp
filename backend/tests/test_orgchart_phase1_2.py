"""Backend regression tests for Org Chart Phase 1+2 overhaul (Feb 2026).

Covers:
  - GET /api/org-chart/template       (canonical position template)
  - POST /api/org-chart/seed          (preserve + reset modes)
  - POST /api/org-chart/seed-defaults (destructive default)
  - POST /api/org-chart/resync-from-users
  - GET /api/org-chart/roles          (enrichment, children)
  - Live sync via PUT /api/users/{id}/unit + PUT /api/users/{id}/role
  - Exec Cadre permission scoping on role changes
  - role_audit_log persistence
"""
import os
import uuid
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
COMMANDER = {"email": "commander@test.com", "password": "test123"}
EXEC_CADRE = {"email": "exec_cadre@test.com", "password": "test123"}

EXPECTED_POSITIONS = 79
EXPECTED_CATEGORIES = {"staff", "support", "cadet_support",
                       "6th_cts", "21st_cts", "22nd_cts"}
SQUADRON_FLIGHT_IDS = [
    "6th-flt-a-cmdr", "6th-flt-a-sgt",
    "6th-flt-b-cmdr", "6th-flt-b-sgt",
    "21st-flt-c-cmdr", "21st-flt-c-sgt",
    "21st-flt-d-cmdr", "21st-flt-d-sgt",
    "22nd-flt-e-cmdr", "22nd-flt-e-sgt",
    "22nd-flt-f-cmdr", "22nd-flt-f-sgt",
]
FIRST_SERGEANTS = ["6th-sq-1sgt", "21st-sq-1sgt", "22nd-sq-1sgt"]


# ── Fixtures ────────────────────────────────────────────────────────────
def _login(creds):
    r = requests.post(f"{BASE}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login {creds['email']} failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers():
    return {"Authorization": f"Bearer {_login(COMMANDER)}",
            "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def exec_cadre_headers():
    return {"Authorization": f"Bearer {_login(EXEC_CADRE)}",
            "Content-Type": "application/json"}


# Module-scoped throwaway cadre user used for live-sync tests.
@pytest.fixture(scope="module")
def test_cadre_user(admin_headers):
    """Create + approve a brand-new cadre user for live-sync tests."""
    suffix = uuid.uuid4().hex[:6]
    email = f"TEST_cadre_{suffix}@example.com"
    payload = {
        "email": email, "password": "TestPass123!",
        "name": f"TEST Cadre {suffix}", "capid": f"99{suffix[:4]}",
        "role": "cadre",
    }
    r = requests.post(f"{BASE}/api/auth/register", json=payload, timeout=20)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    uid = r.json().get("user", {}).get("id") or r.json().get("id")
    if not uid:
        # Lookup via admin
        users = requests.get(f"{BASE}/api/users", headers=admin_headers, timeout=20).json()
        uid = next(u["id"] for u in users if u["email"] == email)
    # Approve
    ap = requests.post(f"{BASE}/api/users/{uid}/approve",
                       headers=admin_headers, timeout=20)
    assert ap.status_code in (200, 204), f"approve failed: {ap.status_code} {ap.text}"
    yield {"id": uid, "email": email, "name": f"TEST Cadre {suffix}"}
    # Teardown
    requests.delete(f"{BASE}/api/users/{uid}", headers=admin_headers, timeout=20)


# ── Helpers ─────────────────────────────────────────────────────────────
def _get_role(role_id, headers):
    r = requests.get(f"{BASE}/api/org-chart/roles/{role_id}",
                     headers=headers, timeout=20)
    return r


def _set_unit(uid, headers, **kwargs):
    body = {"squadron": None, "flight": None, "support_section": None,
            "cadre_unit": None, "cadre_position": None}
    body.update(kwargs)
    return requests.put(f"{BASE}/api/users/{uid}/unit",
                        headers=headers, json=body, timeout=20)


def _set_role(uid, role, headers):
    return requests.put(f"{BASE}/api/users/{uid}/role?role={role}",
                        headers=headers, timeout=20)


# ── Tests: Template ─────────────────────────────────────────────────────
class TestOrgChartTemplate:
    def test_template_returns_79_positions_with_6_categories(self, admin_headers):
        r = requests.get(f"{BASE}/api/org-chart/template",
                         headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["count"] == EXPECTED_POSITIONS, \
            f"expected {EXPECTED_POSITIONS} positions, got {body['count']}"
        assert len(body["positions"]) == EXPECTED_POSITIONS
        cats = set(body["categories"])
        assert cats == EXPECTED_CATEGORIES, f"categories mismatch: {cats}"
        # Field sanity check
        first = body["positions"][0]
        for k in ("role_id", "position_title", "reports_to",
                  "role_category", "order", "allowed_participant_types"):
            assert k in first, f"template missing field {k}"

    def test_pa_lives_under_dcs_not_ccea(self, admin_headers):
        r = requests.get(f"{BASE}/api/org-chart/template",
                         headers=admin_headers, timeout=20).json()
        by_id = {p["role_id"]: p for p in r["positions"]}
        assert "public-affairs-dept" in by_id
        assert by_id["public-affairs-dept"]["reports_to"] == "dcs", \
            "Public Affairs must report to DCS, not CTG/CCEA"
        # PA must NOT be a child of ctg-ccea
        ccea_children = [p for p in r["positions"]
                         if p["reports_to"] == "ctg-ccea"]
        assert "public-affairs-dept" not in [c["role_id"] for c in ccea_children]

    def test_first_sergeants_exist_not_superintendents(self, admin_headers):
        r = requests.get(f"{BASE}/api/org-chart/template",
                         headers=admin_headers, timeout=20).json()
        by_id = {p["role_id"]: p for p in r["positions"]}
        for fs in FIRST_SERGEANTS:
            assert fs in by_id, f"missing first-sergeant position {fs}"
            assert by_id[fs]["position_title"] == "First Sergeant"

    def test_all_flight_positions_canonical_ids(self, admin_headers):
        r = requests.get(f"{BASE}/api/org-chart/template",
                         headers=admin_headers, timeout=20).json()
        ids = {p["role_id"] for p in r["positions"]}
        missing = [pid for pid in SQUADRON_FLIGHT_IDS if pid not in ids]
        assert not missing, f"missing flight position ids: {missing}"


# ── Tests: Seed ─────────────────────────────────────────────────────────
class TestOrgChartSeed:
    def test_seed_preserve_mode_default(self, admin_headers):
        # Mark a known position with a custom assigned_name to verify preservation
        marker = "TEST_PRESERVE_MARKER"
        roles_before = requests.get(f"{BASE}/api/org-chart/roles?raw=true",
                                    headers=admin_headers, timeout=20).json()
        # Pick an arbitrary position, set its assigned_name via the PUT roles endpoint
        target_id = "media-publishing"
        put = requests.put(
            f"{BASE}/api/org-chart/roles/{target_id}",
            headers=admin_headers,
            json={"assigned_name": marker},
            timeout=20,
        )
        assert put.status_code == 200, put.text

        r = requests.post(f"{BASE}/api/org-chart/seed",
                          headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mode"] == "preserve"
        assert body["total"] == EXPECTED_POSITIONS
        for k in ("inserted", "updated", "deleted", "preserved_assignments"):
            assert k in body
        # Marker survived
        after = _get_role(target_id, admin_headers).json()
        assert after["assigned_name"] == marker, \
            "preserve-mode seed clobbered an existing assigned_name"

    def test_seed_reset_mode_destructive(self, admin_headers):
        r = requests.post(f"{BASE}/api/org-chart/seed?reset=true",
                          headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mode"] == "reset"
        assert body["inserted"] == EXPECTED_POSITIONS
        assert body["total"] == EXPECTED_POSITIONS
        # After reset, INITIAL_ASSIGNMENTS default should be applied
        enc = _get_role("enc-commander", admin_headers).json()
        assert enc["assigned_name"] == "Maj Divers, L"

    def test_seed_defaults_endpoint(self, admin_headers):
        r = requests.post(f"{BASE}/api/org-chart/seed-defaults",
                          headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == EXPECTED_POSITIONS
        assert body["mode"] == "reset"

    def test_roles_endpoint_returns_79_with_children(self, admin_headers):
        r = requests.get(f"{BASE}/api/org-chart/roles",
                         headers=admin_headers, timeout=20)
        assert r.status_code == 200, r.text
        roles = r.json()
        assert len(roles) == EXPECTED_POSITIONS
        sample = roles[0]
        for k in ("role_id", "position_title", "reports_to",
                  "role_category", "order", "assigned_name", "children"):
            assert k in sample, f"roles endpoint missing field {k}"
        # ctg-cc must have children
        ctg = next(r for r in roles if r["role_id"] == "ctg-cc")
        assert len(ctg["children"]) >= 5


# ── Tests: Live sync ────────────────────────────────────────────────────
class TestLiveSync:
    def test_unit_assignment_sets_flight_sergeant(self, admin_headers, test_cadre_user):
        # Reset chart first to clear seed-default assignments
        requests.post(f"{BASE}/api/org-chart/seed?reset=true",
                      headers=admin_headers, timeout=30)
        uid = test_cadre_user["id"]
        name = test_cadre_user["name"]
        r = _set_unit(uid, admin_headers,
                      squadron="6th_cts", flight="alpha",
                      cadre_position="flight_sergeant")
        assert r.status_code == 200, r.text
        node = _get_role("6th-flt-a-sgt", admin_headers).json()
        assert node["assigned_name"] == name, \
            f"expected {name} at 6th-flt-a-sgt, got {node['assigned_name']!r}"

    def test_unit_change_moves_assignment(self, admin_headers, test_cadre_user):
        uid = test_cadre_user["id"]
        name = test_cadre_user["name"]
        r = _set_unit(uid, admin_headers,
                      squadron="6th_cts", flight="alpha",
                      cadre_position="flight_commander")
        assert r.status_code == 200, r.text
        sgt = _get_role("6th-flt-a-sgt", admin_headers).json()
        cmdr = _get_role("6th-flt-a-cmdr", admin_headers).json()
        assert sgt["assigned_name"] != name, \
            f"old flight-sergeant slot still holds the moved user (got {sgt['assigned_name']!r})"
        assert cmdr["assigned_name"] == name

    def test_role_promotion_to_squadron_commander(self, admin_headers, test_cadre_user):
        uid = test_cadre_user["id"]
        name = test_cadre_user["name"]
        r = _set_role(uid, "squadron_commander", admin_headers)
        assert r.status_code == 200, r.text
        sq = _get_role("6th-sq-cmdr", admin_headers).json()
        assert sq["assigned_name"] == name, \
            f"6th-sq-cmdr expected {name}, got {sq['assigned_name']!r}"
        # Prior position should be cleared
        cmdr = _get_role("6th-flt-a-cmdr", admin_headers).json()
        assert cmdr["assigned_name"] != name

    def test_role_demotion_falls_back_to_cadre_position(self, admin_headers, test_cadre_user):
        uid = test_cadre_user["id"]
        name = test_cadre_user["name"]
        # cadre_position is still flight_commander on the user record
        r = _set_role(uid, "cadre", admin_headers)
        assert r.status_code == 200, r.text
        cmdr = _get_role("6th-flt-a-cmdr", admin_headers).json()
        assert cmdr["assigned_name"] == name, \
            f"demotion did not re-occupy 6th-flt-a-cmdr (got {cmdr['assigned_name']!r})"
        sq = _get_role("6th-sq-cmdr", admin_headers).json()
        assert sq["assigned_name"] != name


# ── Tests: Resync-from-users ────────────────────────────────────────────
class TestResync:
    def test_resync_from_users(self, admin_headers):
        r = requests.post(f"{BASE}/api/org-chart/resync-from-users",
                          headers=admin_headers, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("synced", "skipped", "total_users"):
            assert k in body
        assert body["total_users"] >= 1


# ── Tests: Exec Cadre permission scoping ────────────────────────────────
class TestExecCadrePermissions:
    def test_exec_cadre_can_promote_cadre_to_squadron_commander(
        self, exec_cadre_headers, admin_headers, test_cadre_user
    ):
        # Ensure target is currently a cadre-managed role
        _set_role(test_cadre_user["id"], "cadre", admin_headers)
        r = _set_role(test_cadre_user["id"], "squadron_commander",
                      exec_cadre_headers)
        assert r.status_code == 200, f"exec_cadre cadre-edit blocked: {r.status_code} {r.text}"

    def test_exec_cadre_cannot_grant_protected_role(
        self, exec_cadre_headers, test_cadre_user
    ):
        for protected in ("commander", "dcp", "executive_staff",
                           "superintendent", "chief_training_officer"):
            r = _set_role(test_cadre_user["id"], protected, exec_cadre_headers)
            assert r.status_code == 403, \
                f"exec_cadre was allowed to grant protected role {protected}: {r.status_code}"

    def test_exec_cadre_cannot_edit_senior_staff_user(
        self, exec_cadre_headers, admin_headers
    ):
        # commander@test.com is a senior-staff role — outside cadre bucket
        users = requests.get(f"{BASE}/api/users",
                             headers=admin_headers, timeout=20).json()
        cmdr_user = next(u for u in users if u["email"] == "commander@test.com")
        r = _set_role(cmdr_user["id"], "cadre", exec_cadre_headers)
        assert r.status_code == 403, \
            f"exec_cadre allowed to demote senior-staff user: {r.status_code} {r.text}"


# ── Tests: role_audit_log regression ────────────────────────────────────
class TestRoleAuditLog:
    def test_audit_log_endpoint_exists(self, admin_headers):
        r = requests.get(f"{BASE}/api/users/role-audit-log",
                         headers=admin_headers, timeout=20)
        assert r.status_code == 200, \
            f"role audit log endpoint missing: {r.status_code} {r.text[:200]}"
        body = r.json()
        assert isinstance(body, list)
