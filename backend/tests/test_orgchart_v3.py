"""
Org Chart V3 Tests - Iteration 61 (DEPRECATED)

This file targeted the 85-position template with squadron-category color
scheme. The canonical template is now 79 positions with 6 categories
(staff/support/cadet_support/6th_cts/21st_cts/22nd_cts) — Feb 2026 Phase 1+2
overhaul. See `tests/test_orgchart_phase1_2.py` for the current suite.
"""
import pytest

pytest.skip(
    "Legacy 85-position v3 org-chart suite — superseded by test_orgchart_phase1_2.py "
    "(canonical 79-position template; 6 categories).",
    allow_module_level=True,
)

import requests
import os

from tests.conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, PARENT_EMAIL, PARENT_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_session():
    """Get authenticated session with commander credentials"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login as commander
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": COMMANDER_EMAIL,
        "password": COMMANDER_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return session


class TestOrgChartBasics:
    """Basic org chart API tests"""
    
    def test_get_all_roles_returns_85_positions(self, auth_session):
        """Verify total position count is 85"""
        response = auth_session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        roles = response.json()
        assert len(roles) == 85, f"Expected 85 positions, got {len(roles)}"
    
    def test_all_roles_have_required_fields(self, auth_session):
        """Verify all roles have required schema fields"""
        response = auth_session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        roles = response.json()
        
        required_fields = ['role_id', 'position_title', 'reports_to', 'role_category', 'order']
        for role in roles:
            for field in required_fields:
                assert field in role, f"Role {role.get('role_id', 'unknown')} missing field: {field}"


class TestSquadronTrainingOfficersUnderCTO:
    """Test that Squadron Training Officers are now under Chief Training Officer"""
    
    def test_6th_cts_to_reports_to_cto(self, auth_session):
        """6th CTS Squadron Training Officer reports to Chief Training Officer"""
        response = auth_session.get(f"{BASE_URL}/api/org-chart/roles/6th-sq-to")
        assert response.status_code == 200
        role = response.json()
        assert role['reports_to'] == 'chief-training-officer', f"6th-sq-to reports to {role['reports_to']}, expected chief-training-officer"
        assert role['assigned_name'] == 'Capt Brad Dozier'
    
    def test_21st_cts_to_reports_to_cto(self, auth_session):
        """21st CTS Squadron Training Officer reports to Chief Training Officer"""
        response = auth_session.get(f"{BASE_URL}/api/org-chart/roles/21st-sq-to")
        assert response.status_code == 200
        role = response.json()
        assert role['reports_to'] == 'chief-training-officer', f"21st-sq-to reports to {role['reports_to']}, expected chief-training-officer"
        assert role['assigned_name'] == 'Capt Renee Cyr'
    
    def test_22nd_cts_to_reports_to_cto(self, auth_session):
        """22nd CTS Squadron Training Officer reports to Chief Training Officer"""
        response = auth_session.get(f"{BASE_URL}/api/org-chart/roles/22nd-sq-to")
        assert response.status_code == 200
        role = response.json()
        assert role['reports_to'] == 'chief-training-officer', f"22nd-sq-to reports to {role['reports_to']}, expected chief-training-officer"
        assert role['assigned_name'] == '1st Lt Max Hammond'
    
    def test_cto_has_10_children_including_3_tos(self, auth_session):
        """Chief Training Officer has 10 children including the 3 Squadron TOs"""
        response = auth_session.get(f"{BASE_URL}/api/org-chart/roles/chief-training-officer")
        assert response.status_code == 200
        role = response.json()
        children = role.get('children', [])
        assert len(children) == 10, f"CTO has {len(children)} children, expected 10"
        
        # Verify the 3 TOs are in children
        assert '6th-sq-to' in children, "6th-sq-to not in CTO children"
        assert '21st-sq-to' in children, "21st-sq-to not in CTO children"
        assert '22nd-sq-to' in children, "22nd-sq-to not in CTO children"
    
    def test_6th_sq_cmdr_does_not_have_to_as_child(self, auth_session):
        """6th CTS Commander no longer has Squadron Training Officer as a child"""
        response = auth_session.get(f"{BASE_URL}/api/org-chart/roles/6th-sq-cmdr")
        assert response.status_code == 200
        role = response.json()
        children = role.get('children', [])
        assert '6th-sq-to' not in children, "6th-sq-to should NOT be a child of 6th-sq-cmdr"


class TestSecondaryReportingToCTGDF:
    """Test secondary_reports_to = ctg-df for squadron positions"""
    
    def test_all_3_squadron_commanders_have_secondary_to_ctgdf(self, auth_session):
        """All 3 Squadron Commanders have secondary_reports_to = ctg-df"""
        sq_cmdrs = ['6th-sq-cmdr', '21st-sq-cmdr', '22nd-sq-cmdr']
        for role_id in sq_cmdrs:
            response = auth_session.get(f"{BASE_URL}/api/org-chart/roles/{role_id}")
            assert response.status_code == 200
            role = response.json()
            assert role.get('secondary_reports_to') == 'ctg-df', f"{role_id} secondary_reports_to = {role.get('secondary_reports_to')}, expected ctg-df"
    
    def test_all_6_flight_commanders_have_secondary_to_ctgdf(self, auth_session):
        """All 6 Flight Commanders have secondary_reports_to = ctg-df"""
        flt_cmdrs = [
            '6th-flt-a-cmdr', '6th-flt-b-cmdr',
            '21st-flt-c-cmdr', '21st-flt-d-cmdr',
            '22nd-flt-e-cmdr', '22nd-flt-f-cmdr'
        ]
        for role_id in flt_cmdrs:
            response = auth_session.get(f"{BASE_URL}/api/org-chart/roles/{role_id}")
            assert response.status_code == 200
            role = response.json()
            assert role.get('secondary_reports_to') == 'ctg-df', f"{role_id} secondary_reports_to = {role.get('secondary_reports_to')}, expected ctg-df"
    
    def test_all_6_flight_sergeants_have_secondary_to_ctgdf(self, auth_session):
        """All 6 Flight Sergeants have secondary_reports_to = ctg-df"""
        flt_sgts = [
            '6th-flt-a-sgt', '6th-flt-b-sgt',
            '21st-flt-c-sgt', '21st-flt-d-sgt',
            '22nd-flt-e-sgt', '22nd-flt-f-sgt'
        ]
        for role_id in flt_sgts:
            response = auth_session.get(f"{BASE_URL}/api/org-chart/roles/{role_id}")
            assert response.status_code == 200
            role = response.json()
            assert role.get('secondary_reports_to') == 'ctg-df', f"{role_id} secondary_reports_to = {role.get('secondary_reports_to')}, expected ctg-df"
    
    def test_all_3_first_sergeants_have_secondary_to_ctgdf(self, auth_session):
        """All 3 First Sergeants have secondary_reports_to = ctg-df"""
        first_sgts = ['6th-sq-1sgt', '21st-sq-1sgt', '22nd-sq-1sgt']
        for role_id in first_sgts:
            response = auth_session.get(f"{BASE_URL}/api/org-chart/roles/{role_id}")
            assert response.status_code == 200
            role = response.json()
            assert role.get('secondary_reports_to') == 'ctg-df', f"{role_id} secondary_reports_to = {role.get('secondary_reports_to')}, expected ctg-df"
    
    def test_css_cc_still_has_secondary_to_ctgdf(self, auth_session):
        """CSS/CC still has secondary_reports_to = ctg-df"""
        response = auth_session.get(f"{BASE_URL}/api/org-chart/roles/css-cc")
        assert response.status_code == 200
        role = response.json()
        assert role.get('secondary_reports_to') == 'ctg-df', f"css-cc secondary_reports_to = {role.get('secondary_reports_to')}, expected ctg-df"


class TestFiveCategoryColorScheme:
    """Test 5 role categories are present"""
    
    def test_all_5_categories_present(self, auth_session):
        """Verify all 5 categories exist in the data"""
        response = auth_session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        roles = response.json()
        
        categories = set(role['role_category'] for role in roles)
        expected = {'command', 'cadet_training', 'squadron', 'support', 'cadet_support'}
        assert categories == expected, f"Categories found: {categories}, expected: {expected}"
    
    def test_command_category_positions(self, auth_session):
        """Verify command category has correct positions"""
        response = auth_session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        roles = response.json()
        
        command_roles = [r for r in roles if r['role_category'] == 'command']
        command_ids = [r['role_id'] for r in command_roles]
        
        # Should include enc-commander, commandant, sm-superintendent, chaplains, safety
        assert 'enc-commander' in command_ids
        assert 'commandant' in command_ids
        assert 'sm-superintendent' in command_ids
    
    def test_squadron_category_positions(self, auth_session):
        """Verify squadron category has correct positions (yellow)"""
        response = auth_session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        roles = response.json()
        
        squadron_roles = [r for r in roles if r['role_category'] == 'squadron']
        squadron_ids = [r['role_id'] for r in squadron_roles]
        
        # Squadron commanders, flight commanders, flight sergeants, first sergeants, TOs
        assert '6th-sq-cmdr' in squadron_ids
        assert '21st-sq-cmdr' in squadron_ids
        assert '22nd-sq-cmdr' in squadron_ids
        assert '6th-sq-to' in squadron_ids
        assert '6th-flt-a-cmdr' in squadron_ids
        assert '6th-flt-a-sgt' in squadron_ids
    
    def test_cadet_support_category_positions(self, auth_session):
        """Verify cadet_support category has CSS positions (silver)"""
        response = auth_session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        roles = response.json()
        
        css_roles = [r for r in roles if r['role_category'] == 'cadet_support']
        css_ids = [r['role_id'] for r in css_roles]
        
        # CSS/CC and its children
        assert 'css-cc' in css_ids
        assert 'css-to' in css_ids
        assert 'css-logistics' in css_ids
    
    def test_support_category_positions(self, auth_session):
        """Verify support category has DCS positions (emerald green)"""
        response = auth_session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        roles = response.json()
        
        support_roles = [r for r in roles if r['role_category'] == 'support']
        support_ids = [r['role_id'] for r in support_roles]
        
        # DCS and its children
        assert 'dcs' in support_ids
        assert 'xp-plans' in support_ids
        assert 'lg-logistics' in support_ids
        assert 'comm' in support_ids
        assert 'finance' in support_ids


class TestCountSecondaryReporting:
    """Count positions with secondary reporting"""
    
    def test_count_positions_with_secondary_reporting(self, auth_session):
        """Count total positions with secondary_reports_to = ctg-df"""
        response = auth_session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        roles = response.json()
        
        secondary_roles = [r for r in roles if r.get('secondary_reports_to') == 'ctg-df']
        # Expected: 3 sq cmdrs + 6 flt cmdrs + 6 flt sgts + 3 first sgts + 1 css-cc = 19
        assert len(secondary_roles) >= 19, f"Found {len(secondary_roles)} positions with secondary reporting, expected at least 19"
        
        # Print for debugging
        print(f"\nPositions with secondary_reports_to = ctg-df ({len(secondary_roles)}):")
        for r in secondary_roles:
            print(f"  - {r['role_id']}: {r['position_title']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
