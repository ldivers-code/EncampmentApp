"""
Tests for the new /api/inspections/* module (replaces old /api/points/*).

Coverage:
- /inspections/types metadata
- /inspections/settings (GET auto-create, PUT updates + validation)
- /inspections/scores per-cadet (knowledge w/ absent) and flight-level (drill 51/54)
- /inspections/scores GET filters + DELETE
- /inspections/merit-points PUT + GET
- /inspections/dashboard aggregation (CTF/CTS/Weekly Totals/Weekly Change)
- /inspections/student/{id}
- RBAC: regular cadre 403, exec_cadre/commander 200
- Old /api/points/* returns 404
- /api/parent/my-cadet/points still works (no 500)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

COMMANDER = {"email": "commander@test.com", "password": "test123"}
EXEC_CADRE = {"email": "exec_cadre@test.com", "password": "test123"}
CADRE = {"email": "testcadre@cap.gov", "password": "test123"}
PARENT = {"email": "jane.hundley@test.com", "password": "parent123"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"Login failed for {creds['email']}: {r.status_code} {r.text}")
    return r.json().get("access_token")


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


# ── Fixtures ─────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def commander_token():
    return _login(COMMANDER)


@pytest.fixture(scope="module")
def exec_cadre_token():
    return _login(EXEC_CADRE)


@pytest.fixture(scope="module")
def cadre_token():
    return _login(CADRE)


@pytest.fixture(scope="module")
def parent_token():
    return _login(PARENT)


# ── /inspections/types ───────────────────────────────────────────────
class TestInspectionTypes:
    def test_types_metadata(self, exec_cadre_token):
        r = requests.get(f"{BASE_URL}/api/inspections/types",
                         headers=_hdr(exec_cadre_token), timeout=30)
        assert r.status_code == 200
        data = r.json()
        # 5 inspection types
        assert set(data["types"]) == {
            "dorm_uniform", "dorm_uniform_repeat", "drill",
            "daily_sports", "knowledge"
        }
        assert set(data["per_cadet_types"]) == {
            "dorm_uniform", "dorm_uniform_repeat", "knowledge"}
        assert set(data["flight_level_types"]) == {"drill", "daily_sports"}
        # Field counts
        assert len(data["fields"]["dorm_uniform"]) == 8
        assert len(data["fields"]["dorm_uniform_repeat"]) == 8
        assert len(data["fields"]["drill"]) == 18
        assert len(data["fields"]["knowledge"]) == 9
        assert len(data["fields"]["daily_sports"]) == 1
        # Max totals
        assert data["max_total"]["dorm_uniform"] == 20
        assert data["max_total"]["dorm_uniform_repeat"] == 20
        assert data["max_total"]["drill"] == 54
        assert data["max_total"]["knowledge"] == 9
        assert data["max_total"]["daily_sports"] == 20
        # Days / flights
        assert data["days"] == [1, 2, 3, 4, 5, 6]
        assert set(data["flights"]) == {
            "alpha", "bravo", "charlie", "delta", "echo", "foxtrot"}
        # Squadron map
        assert data["flight_to_squadron"]["alpha"] == "6th_cts"
        assert data["flight_to_squadron"]["charlie"] == "21st_cts"
        assert data["flight_to_squadron"]["echo"] == "22nd_cts"
        sq = data["squadron_flights"]
        assert set(sq["6th_cts"]) == {"alpha", "bravo"}
        assert set(sq["21st_cts"]) == {"charlie", "delta"}
        assert set(sq["22nd_cts"]) == {"echo", "foxtrot"}
        # Default weights TOTALS U22:W26
        w = data["default_weights"]
        assert w["dorm_uniform"] == 20
        assert w["dorm_uniform_repeat"] == 100
        assert w["drill"] == 100
        assert w["daily_sports"] == 20
        assert w["knowledge"] == 100
        assert w["app"] == 10


# ── /inspections/settings ────────────────────────────────────────────
class TestSettings:
    def test_get_settings_auto_create(self, commander_token):
        r = requests.get(f"{BASE_URL}/api/inspections/settings",
                         headers=_hdr(commander_token), timeout=30)
        assert r.status_code == 200
        s = r.json()
        assert "day_inspections" in s
        assert "weights" in s
        assert isinstance(s.get("include_merit_points"), bool)
        # All 6 days present in defaults
        for d in ["1", "2", "3", "4", "5", "6"]:
            assert d in s["day_inspections"]

    def test_put_settings_validation(self, commander_token):
        # Include invalid days (7, abc) and invalid types — they must be ignored
        body = {
            "day_inspections": {
                "2": ["drill", "bogus_type", "knowledge"],
                "7": ["drill"],
                "abc": ["drill"],
            },
            "weights": {
                "drill": 75.0,
                "unknown_key": 999.0,  # must be ignored
            },
            "include_merit_points": False,
        }
        r = requests.put(f"{BASE_URL}/api/inspections/settings",
                         headers=_hdr(commander_token), json=body, timeout=30)
        assert r.status_code == 200, r.text
        s = r.json()
        # Day 2 cleaned (bogus removed)
        assert "drill" in s["day_inspections"]["2"]
        assert "knowledge" in s["day_inspections"]["2"]
        assert "bogus_type" not in s["day_inspections"]["2"]
        # Day 7 must NOT exist
        assert "7" not in s["day_inspections"]
        assert "abc" not in s["day_inspections"]
        # Weights
        assert s["weights"]["drill"] == 75.0
        assert "unknown_key" not in s["weights"]
        assert s["include_merit_points"] is False

        # Restore good defaults so the rest of the suite is deterministic.
        restore = {
            "day_inspections": {
                "1": [],
                "2": ["dorm_uniform", "dorm_uniform_repeat", "drill",
                      "daily_sports", "knowledge"],
                "3": ["drill", "daily_sports", "knowledge"],
                "4": ["dorm_uniform_repeat", "daily_sports"],
                "5": ["drill", "daily_sports", "knowledge"],
                "6": ["dorm_uniform_repeat", "knowledge"],
            },
            "weights": {
                "dorm_uniform": 20.0, "dorm_uniform_repeat": 100.0,
                "drill": 100.0, "daily_sports": 20.0,
                "knowledge": 100.0, "app": 10.0,
            },
            "include_merit_points": True,
        }
        r2 = requests.put(f"{BASE_URL}/api/inspections/settings",
                          headers=_hdr(commander_token), json=restore, timeout=30)
        assert r2.status_code == 200


# ── Score CRUD ───────────────────────────────────────────────────────
class TestScoresPerCadet:
    """Knowledge Day 2 Alpha — 3 cadets, one absent."""

    def test_put_knowledge_with_absent(self, commander_token):
        body = {
            "day": 2, "flight": "alpha", "inspection_type": "knowledge",
            "cadet_scores": [
                {"cadet_participant_id": "TEST_p1", "cadet_name": "Cadet One",
                 "field_scores": {f"q{i}": 1 for i in range(1, 9)}, "absent": False},  # 8/9
                {"cadet_participant_id": "TEST_p2", "cadet_name": "Cadet Two",
                 "field_scores": {f"q{i}": 1 for i in range(1, 10)}, "absent": False},  # 9/9
                {"cadet_participant_id": "TEST_p3", "cadet_name": "Cadet Three",
                 "field_scores": {}, "absent": True},
            ],
        }
        r = requests.put(f"{BASE_URL}/api/inspections/scores",
                         headers=_hdr(commander_token), json=body, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["inserted"] == 3

        # GET filter & check absent row has percent None
        r2 = requests.get(
            f"{BASE_URL}/api/inspections/scores",
            params={"day": 2, "flight": "alpha", "inspection_type": "knowledge"},
            headers=_hdr(commander_token), timeout=30)
        assert r2.status_code == 200
        rows = r2.json()
        assert len(rows) == 3
        by_id = {r["cadet_participant_id"]: r for r in rows}
        assert by_id["TEST_p1"]["total"] == 8
        assert abs(by_id["TEST_p1"]["percent"] - 8/9) < 1e-6
        assert by_id["TEST_p2"]["total"] == 9
        assert by_id["TEST_p2"]["percent"] == 1.0
        assert by_id["TEST_p3"]["absent"] is True
        assert by_id["TEST_p3"]["percent"] is None

    def test_idempotent_replace(self, commander_token):
        # Re-upserting overwrites; only 1 cadet row now
        body = {
            "day": 2, "flight": "alpha", "inspection_type": "knowledge",
            "cadet_scores": [
                {"cadet_participant_id": "TEST_p1", "cadet_name": "Cadet One",
                 "field_scores": {f"q{i}": 1 for i in range(1, 9)}, "absent": False},
                {"cadet_participant_id": "TEST_p2", "cadet_name": "Cadet Two",
                 "field_scores": {f"q{i}": 1 for i in range(1, 10)}, "absent": False},
                {"cadet_participant_id": "TEST_p3", "cadet_name": "Cadet Three",
                 "field_scores": {}, "absent": True},
            ],
        }
        # First write
        requests.put(f"{BASE_URL}/api/inspections/scores",
                     headers=_hdr(commander_token), json=body, timeout=30)
        # Write again
        r = requests.put(f"{BASE_URL}/api/inspections/scores",
                         headers=_hdr(commander_token), json=body, timeout=30)
        assert r.status_code == 200
        # Total should still be 3, not 6
        r2 = requests.get(
            f"{BASE_URL}/api/inspections/scores",
            params={"day": 2, "flight": "alpha", "inspection_type": "knowledge"},
            headers=_hdr(commander_token), timeout=30)
        assert len(r2.json()) == 3


class TestScoresFlightLevel:
    """Drill 51/54 → 0.9444…"""

    def test_drill_flight_level(self, commander_token):
        # 18 movements; produce total of 51 by giving 15x3 + 3x2 = 45+6 = 51
        movements = [
            "fall_in", "dress_right_dress", "ready_front", "at_ease",
            "flight_attention", "present_arms", "order_arms", "left_face",
            "right_face", "about_face", "parade_rest", "hand_salute",
            "forward_march", "incline_to_the_left", "incline_to_the_right",
            "flight_halt", "column_of_files", "fall_out",
        ]
        scores = {m: 3 for m in movements}
        # Drop 3 points from first three movements
        for m in movements[:3]:
            scores[m] = 2
        # Sanity: total = 15*3 + 3*2 = 51
        assert sum(scores.values()) == 51

        body = {
            "day": 2, "flight": "alpha", "inspection_type": "drill",
            "field_scores": scores,
        }
        r = requests.put(f"{BASE_URL}/api/inspections/scores",
                         headers=_hdr(commander_token), json=body, timeout=30)
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["inserted"] == 1
        assert out["total"] == 51
        assert abs(out["percent"] - 51 / 54) < 1e-6  # 0.9444...

        # GET single row
        r2 = requests.get(
            f"{BASE_URL}/api/inspections/scores",
            params={"day": 2, "flight": "alpha", "inspection_type": "drill"},
            headers=_hdr(commander_token), timeout=30)
        rows = r2.json()
        assert len(rows) == 1
        assert rows[0]["cadet_participant_id"] is None
        assert rows[0]["total"] == 51

    def test_delete_scores(self, commander_token):
        # Write daily_sports then delete
        requests.put(
            f"{BASE_URL}/api/inspections/scores",
            headers=_hdr(commander_token),
            json={"day": 3, "flight": "bravo",
                  "inspection_type": "daily_sports",
                  "field_scores": {"sports_score": 18}}, timeout=30)
        r = requests.delete(
            f"{BASE_URL}/api/inspections/scores",
            params={"day": 3, "flight": "bravo", "inspection_type": "daily_sports"},
            headers=_hdr(commander_token), timeout=30)
        assert r.status_code == 200
        assert r.json()["deleted"] >= 1
        r2 = requests.get(
            f"{BASE_URL}/api/inspections/scores",
            params={"day": 3, "flight": "bravo", "inspection_type": "daily_sports"},
            headers=_hdr(commander_token), timeout=30)
        assert r2.json() == []


# ── Merit points ─────────────────────────────────────────────────────
class TestMeritPoints:
    def test_put_and_list(self, commander_token):
        r = requests.put(f"{BASE_URL}/api/inspections/merit-points",
                         headers=_hdr(commander_token),
                         json={"day": 2, "flight": "alpha", "points": 5.5},
                         timeout=30)
        assert r.status_code == 200
        assert r.json()["points"] == 5.5

        r2 = requests.get(f"{BASE_URL}/api/inspections/merit-points",
                          headers=_hdr(commander_token), timeout=30)
        assert r2.status_code == 200
        items = r2.json()
        match = [x for x in items if x["day"] == 2 and x["flight"] == "alpha"]
        assert match and match[0]["points"] == 5.5


# ── Dashboard aggregation ────────────────────────────────────────────
class TestDashboard:
    """End-to-end: write knowledge (88.89%) + drill (94.44%) on Day 2 Alpha,
    expect CTF avg ≈ 91.7%, CTF pts ≈ 183.33 (100*0.944 + 100*0.889)."""

    def test_dashboard_aggregation(self, commander_token):
        # Seed Day 2 Alpha (knowledge present already; drill present already)
        # Recompute by writing fresh
        # Knowledge: 2 present (8/9 and 9/9) → avg = (0.8889+1.0)/2 = 0.9444
        # but spec says "88.89% (2 present, 1 absent)" — that's two cadets
        # both at 8/9 → 0.8889. Adjust seed to match spec.
        requests.put(
            f"{BASE_URL}/api/inspections/scores",
            headers=_hdr(commander_token),
            json={"day": 2, "flight": "alpha", "inspection_type": "knowledge",
                  "cadet_scores": [
                      {"cadet_participant_id": "TEST_p1", "cadet_name": "One",
                       "field_scores": {f"q{i}": 1 for i in range(1, 9)},
                       "absent": False},  # 8/9
                      {"cadet_participant_id": "TEST_p2", "cadet_name": "Two",
                       "field_scores": {f"q{i}": 1 for i in range(1, 9)},
                       "absent": False},  # 8/9
                      {"cadet_participant_id": "TEST_p3", "cadet_name": "Three",
                       "field_scores": {}, "absent": True},
                  ]}, timeout=30)
        # Drill already 51/54 from previous test.

        # Clear other Day-2 Alpha inspections for clean math
        for t in ("dorm_uniform", "dorm_uniform_repeat", "daily_sports"):
            requests.delete(
                f"{BASE_URL}/api/inspections/scores",
                params={"day": 2, "flight": "alpha", "inspection_type": t},
                headers=_hdr(commander_token), timeout=30)
        # Clear Bravo entirely
        for t in ("dorm_uniform", "dorm_uniform_repeat", "drill",
                  "daily_sports", "knowledge"):
            requests.delete(
                f"{BASE_URL}/api/inspections/scores",
                params={"day": 2, "flight": "bravo", "inspection_type": t},
                headers=_hdr(commander_token), timeout=30)
        # Clear merit on Day 2 Alpha so it doesn't pollute math
        requests.put(f"{BASE_URL}/api/inspections/merit-points",
                     headers=_hdr(commander_token),
                     json={"day": 2, "flight": "alpha", "points": 0},
                     timeout=30)

        # Pull dashboard with merit OFF for deterministic math
        r = requests.get(
            f"{BASE_URL}/api/inspections/dashboard",
            params={"include_merit_points": "false"},
            headers=_hdr(commander_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        day2 = d["by_day"]["2"] if "2" in d["by_day"] else d["by_day"][2]
        alpha = next(f for f in day2["flights"] if f["flight"] == "alpha")
        # CTF avg ≈ (8/9 + 51/54)/2 = (0.8889 + 0.9444)/2 ≈ 0.9167
        assert abs(alpha["ctf_average"] - ((8/9) + (51/54)) / 2) < 1e-3
        # CTF pts ≈ 100*0.9444 + 100*0.8889 ≈ 183.33
        expected_pts = 100 * (51/54) + 100 * (8/9)
        assert abs(alpha["ctf_points"] - expected_pts) < 1e-2

        # Bravo all zero
        bravo = next(f for f in day2["flights"] if f["flight"] == "bravo")
        assert bravo["ctf_average"] == 0.0
        assert bravo["ctf_points"] == 0.0

        # CTS for 6th_cts = avg of Alpha (~0.9167) and Bravo (0) ≈ 0.458
        sq6 = next(s for s in day2["squadrons"] if s["squadron"] == "6th_cts")
        assert abs(sq6["cts_average"] - alpha["ctf_average"] / 2) < 1e-3
        assert abs(sq6["cts_points"] - alpha["ctf_points"]) < 1e-2

        # Weekly totals contain Alpha total
        wt = d["weekly_totals"]
        assert abs(wt["alpha"] - expected_pts) < 1e-1  # Other days may add

        # Day 1 baseline = 0 for all flights
        wc = d["weekly_change"]
        day1 = wc["1"] if "1" in wc else wc[1]
        for f in ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]:
            assert day1[f] == 0.0

    def test_dashboard_merit_on_adds_to_ctf_points(self, commander_token):
        requests.put(f"{BASE_URL}/api/inspections/merit-points",
                     headers=_hdr(commander_token),
                     json={"day": 2, "flight": "alpha", "points": 10},
                     timeout=30)
        r = requests.get(
            f"{BASE_URL}/api/inspections/dashboard",
            params={"include_merit_points": "true"},
            headers=_hdr(commander_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        day2 = d["by_day"]["2"] if "2" in d["by_day"] else d["by_day"][2]
        alpha = next(f for f in day2["flights"] if f["flight"] == "alpha")
        assert alpha["merit_points"] == 10
        # Cleanup
        requests.put(f"{BASE_URL}/api/inspections/merit-points",
                     headers=_hdr(commander_token),
                     json={"day": 2, "flight": "alpha", "points": 0},
                     timeout=30)


# ── Student endpoint ─────────────────────────────────────────────────
class TestStudent:
    def test_student_summary(self, commander_token):
        # TEST_p1 had 8/9 on Day 2 Alpha
        r = requests.get(f"{BASE_URL}/api/inspections/student/TEST_p1",
                         headers=_hdr(commander_token), timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["participant_id"] == "TEST_p1"
        assert data["summary"]["inspections_taken"] >= 1
        assert data["summary"]["avg_percent"] is not None

    def test_student_empty(self, commander_token):
        r = requests.get(f"{BASE_URL}/api/inspections/student/NONEXISTENT_xyz",
                         headers=_hdr(commander_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["scores"] == []
        assert d["summary"]["inspections_taken"] == 0


# ── RBAC ─────────────────────────────────────────────────────────────
class TestRBAC:
    def test_regular_cadre_denied(self, cadre_token):
        # /settings
        for path in ("/api/inspections/settings", "/api/inspections/dashboard"):
            r = requests.get(f"{BASE_URL}{path}",
                             headers=_hdr(cadre_token), timeout=30)
            assert r.status_code == 403, f"Expected 403 on {path}, got {r.status_code}"
            assert "restricted" in r.text.lower() or "inspection" in r.text.lower()
        # /scores (PUT denied)
        r = requests.put(
            f"{BASE_URL}/api/inspections/scores",
            headers=_hdr(cadre_token),
            json={"day": 2, "flight": "alpha", "inspection_type": "knowledge",
                  "cadet_scores": []}, timeout=30)
        assert r.status_code == 403
        # GET /scores also denied
        r2 = requests.get(f"{BASE_URL}/api/inspections/scores",
                          headers=_hdr(cadre_token), timeout=30)
        assert r2.status_code == 403

    def test_exec_cadre_authorized(self, exec_cadre_token):
        for path in ("/api/inspections/settings",
                     "/api/inspections/dashboard",
                     "/api/inspections/types"):
            r = requests.get(f"{BASE_URL}{path}",
                             headers=_hdr(exec_cadre_token), timeout=30)
            assert r.status_code == 200, f"{path} → {r.status_code}"

    def test_commander_authorized(self, commander_token):
        r = requests.get(f"{BASE_URL}/api/inspections/dashboard",
                         headers=_hdr(commander_token), timeout=30)
        assert r.status_code == 200

    def test_role_list_contains_required_roles(self):
        """Code-level guarantee: exec_staff and plans_programs are in
        INSPECTION_ROLES (no test accounts to login with)."""
        import sys
        sys.path.insert(0, "/app/backend")
        from routes.inspections import INSPECTION_ROLES
        from models import UserRole
        assert UserRole.EXEC_CADRE in INSPECTION_ROLES
        assert UserRole.EXECUTIVE_STAFF in INSPECTION_ROLES
        assert UserRole.PLANS_PROGRAMS in INSPECTION_ROLES
        assert UserRole.COMMANDER in INSPECTION_ROLES
        assert UserRole.DCP in INSPECTION_ROLES


# ── Old /api/points/* removed ────────────────────────────────────────
class TestLegacyPointsRemoved:
    def test_points_endpoints_404(self, commander_token):
        for path in (
            "/api/points",
            "/api/points/leaderboard",
            "/api/points/cadet/123",
        ):
            r = requests.get(f"{BASE_URL}{path}",
                             headers=_hdr(commander_token), timeout=30)
            assert r.status_code == 404, f"{path} expected 404 got {r.status_code}"


# ── Parent endpoint still works ──────────────────────────────────────
class TestParentMyCadetPoints:
    def test_parent_my_cadet_points_no_500(self, parent_token):
        r = requests.get(f"{BASE_URL}/api/parent/my-cadet/points",
                         headers=_hdr(parent_token), timeout=30)
        # Must not 500 even when zero data
        assert r.status_code != 500, f"500 with body: {r.text}"
        # Acceptable: 200 (success) or 404/403 (no linked cadet)
        assert r.status_code in (200, 403, 404)


# ── Cleanup ──────────────────────────────────────────────────────────
@pytest.fixture(scope="module", autouse=True)
def _cleanup_after(commander_token):
    yield
    try:
        for d in (2, 3):
            for f in ("alpha", "bravo"):
                for t in ("dorm_uniform", "dorm_uniform_repeat", "drill",
                          "daily_sports", "knowledge"):
                    requests.delete(
                        f"{BASE_URL}/api/inspections/scores",
                        params={"day": d, "flight": f, "inspection_type": t},
                        headers=_hdr(commander_token), timeout=30)
        requests.put(f"{BASE_URL}/api/inspections/merit-points",
                     headers=_hdr(commander_token),
                     json={"day": 2, "flight": "alpha", "points": 0},
                     timeout=30)
    except Exception as e:
        print("cleanup error:", e)
