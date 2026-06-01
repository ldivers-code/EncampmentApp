"""
Org Chart API Tests - Iteration 59 (DEPRECATED)

This file targeted the old 86-position template. The canonical template is
now 79 positions with Public Affairs moved under DCS (Feb 2026 Phase 1+2
overhaul). See `tests/test_orgchart_phase1_2.py` for the current suite.
"""
import pytest

pytest.skip(
    "Legacy 86-position org-chart suite — superseded by test_orgchart_phase1_2.py "
    "(canonical 79-position template; PA under DCS).",
    allow_module_level=True,
)

import requests
import os

from tests.conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, PARENT_EMAIL, PARENT_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestOrgChartAPI:
    """Org Chart endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as commander before each test"""
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        
    def test_get_all_roles_returns_86_positions(self):
        """GET /api/org-chart/roles should return exactly 86 positions"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 86, f"Expected 86 positions, got {len(data)}"
        
    def test_root_node_is_encampment_commander(self):
        """Root node should be 'Encampment Commander' with no reports_to"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        data = response.json()
        
        root_nodes = [r for r in data if not r.get('reports_to')]
        assert len(root_nodes) == 1, f"Expected 1 root node, got {len(root_nodes)}"
        
        root = root_nodes[0]
        assert root['position_title'] == 'Encampment Commander'
        assert root['assigned_name'] == 'Maj Divers, L'
        assert root['role_category'] == 'senior_member'
        
    def test_root_has_12_direct_children(self):
        """Encampment Commander should have 12 direct reports"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/enc-commander")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data['children']) == 12, f"Expected 12 children, got {len(data['children'])}"
        expected_children = [
            'chaplains', 'safety', 'commandant', 'dep-cmdr-support', 
            'academics-supt', 'cadet-group-cmdr', 'superintendent',
            'plans-programs-sm', 'communications-sm', 'finance-sm',
            'chief-training-officer', 'health-services-word'
        ]
        for child_id in expected_children:
            assert child_id in data['children'], f"Missing child: {child_id}"
            
    def test_6th_squadron_commander_has_4_children(self):
        """6th Squadron Commander should have 4 children: TO, 1stSgt, Flight A, Flight B"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/6th-sq-cmdr")
        assert response.status_code == 200
        data = response.json()
        
        assert data['position_title'] == '6th Squadron Commander'
        assert data['assigned_name'] == 'C/Capt Nhan, V'
        assert len(data['children']) == 4, f"Expected 4 children, got {len(data['children'])}"
        
        expected = ['6th-sq-to', '6th-sq-1sgt', '6th-flt-a-cmdr', '6th-flt-b-cmdr']
        for child_id in expected:
            assert child_id in data['children'], f"Missing child: {child_id}"
            
    def test_cadet_group_commander_has_5_children(self):
        """Cadet Group Commander should have 5 children: C/Deputy + 4 Squadron Commanders"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/cadet-group-cmdr")
        assert response.status_code == 200
        data = response.json()
        
        assert data['position_title'] == 'Cadet Group Commander'
        assert data['assigned_name'] == 'C/Lt Col Yoder, L'
        assert len(data['children']) == 5, f"Expected 5 children, got {len(data['children'])}"
        
        expected = ['c-deputy-cmdr', '6th-sq-cmdr', '21st-sq-cmdr', '22nd-sq-cmdr', '16th-oss-cmdr']
        for child_id in expected:
            assert child_id in data['children'], f"Missing child: {child_id}"
            
    def test_schema_fields_correct(self):
        """Verify response schema has all required fields"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/enc-commander")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            'id', 'role_id', 'position_title', 'assigned_name', 
            'reports_to', 'role_category', 'children', 'job_description',
            'display_label', 'responsible_for', 'supervises', 
            'created_at', 'updated_at'
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
            
    def test_all_7_role_categories_present(self):
        """Verify all 7 role categories are represented in the data"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        data = response.json()
        
        categories = set(r['role_category'] for r in data if r.get('role_category'))
        expected_categories = {
            'senior_member', 'executive_cadre', 'training_cadre',
            'support_cadre', 'operations_cadre', 'female_cadre', 'out_of_tnwg'
        }
        
        for cat in expected_categories:
            assert cat in categories, f"Missing category: {cat}"
            
    def test_get_single_role_not_found(self):
        """GET /api/org-chart/roles/{invalid_id} should return 404"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/nonexistent-role")
        assert response.status_code == 404
        
    def test_update_role_position(self):
        """PUT /api/org-chart/roles/{role_id} should update position details"""
        # First get current state
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/chaplains")
        assert response.status_code == 200
        original = response.json()
        
        # Update job description
        update_data = {"job_description": "Test job description for chaplain"}
        response = self.session.put(
            f"{BASE_URL}/api/org-chart/roles/chaplains",
            json=update_data
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated['job_description'] == "Test job description for chaplain"
        
        # Restore original
        self.session.put(
            f"{BASE_URL}/api/org-chart/roles/chaplains",
            json={"job_description": original.get('job_description', '')}
        )
        
    def test_create_and_delete_role(self):
        """POST and DELETE /api/org-chart/roles should work"""
        # Create a test role
        new_role = {
            "role_id": "test-position-59",
            "position_title": "Test Position",
            "assigned_name": "Test Person",
            "reports_to": "enc-commander",
            "role_category": "training_cadre",
            "order": 99
        }
        
        response = self.session.post(f"{BASE_URL}/api/org-chart/roles", json=new_role)
        assert response.status_code == 200, f"Create failed: {response.text}"
        created = response.json()
        assert created['position_title'] == "Test Position"
        
        # Delete the test role
        response = self.session.delete(f"{BASE_URL}/api/org-chart/roles/test-position-59")
        assert response.status_code == 200
        
        # Verify deleted
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/test-position-59")
        assert response.status_code == 404
        
    def test_cannot_delete_role_with_subordinates(self):
        """DELETE should fail for roles with subordinates"""
        response = self.session.delete(f"{BASE_URL}/api/org-chart/roles/enc-commander")
        assert response.status_code == 400
        assert "subordinate" in response.json()['detail'].lower()
        
    def test_seed_endpoint_requires_auth(self):
        """POST /api/org-chart/seed should require commander/executive role"""
        # Test with unauthenticated session
        unauth_session = requests.Session()
        response = unauth_session.post(f"{BASE_URL}/api/org-chart/seed")
        assert response.status_code == 401
        
    def test_seed_defaults_endpoint_works(self):
        """POST /api/org-chart/seed-defaults should reseed the org chart"""
        # This is a destructive test - only run if needed
        # For now, just verify the endpoint exists and requires auth
        response = self.session.post(f"{BASE_URL}/api/org-chart/seed-defaults")
        assert response.status_code == 200
        data = response.json()
        assert "86" in data['message'] or "Seeded" in data['message']
        
        # Verify count is still 86
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert len(response.json()) == 86


class TestOrgChartHierarchy:
    """Tests for specific hierarchy relationships"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as commander before each test"""
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert login_resp.status_code == 200
        
    def test_21st_squadron_structure(self):
        """21st Squadron should have TO, 1stSgt, Flight C, Flight D"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/21st-sq-cmdr")
        assert response.status_code == 200
        data = response.json()
        
        assert data['assigned_name'] == "C/2nd Lt Nair, P"
        expected = ['21st-sq-to', '21st-sq-1sgt', '21st-flt-c-cmdr', '21st-flt-d-cmdr']
        for child_id in expected:
            assert child_id in data['children']
            
    def test_22nd_squadron_structure(self):
        """22nd Squadron should have TO, 1stSgt, Flight E, Flight F"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/22nd-sq-cmdr")
        assert response.status_code == 200
        data = response.json()
        
        assert data['assigned_name'] == "C/1st Lt Breslin, D"
        expected = ['22nd-sq-to', '22nd-sq-1sgt', '22nd-flt-e-cmdr', '22nd-flt-f-cmdr']
        for child_id in expected:
            assert child_id in data['children']
            
    def test_16th_oss_structure(self):
        """16th Ops Support Squadron should have 7 children"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/16th-oss-cmdr")
        assert response.status_code == 200
        data = response.json()
        
        assert data['position_title'] == "16th Ops Spt Sq Commander"
        assert len(data['children']) == 7
        
    def test_logistics_department_structure(self):
        """Logistics department should have OIC, AOIC, and 3 cadre members"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/logistics-dept")
        assert response.status_code == 200
        data = response.json()
        
        assert data['position_title'] == "Logistics"
        assert len(data['children']) == 5  # OIC, AOIC, 3 cadre
        
    def test_flight_sergeant_reports_to_flight_commander(self):
        """Flight Sergeants should report to their Flight Commanders"""
        # Check 6th Flight A
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/6th-flt-a-sgt")
        assert response.status_code == 200
        data = response.json()
        assert data['reports_to'] == '6th-flt-a-cmdr'
        
        # Check 21st Flight C
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/21st-flt-c-sgt")
        assert response.status_code == 200
        data = response.json()
        assert data['reports_to'] == '21st-flt-c-cmdr'
