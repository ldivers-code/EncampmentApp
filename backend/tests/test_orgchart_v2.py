"""
Org Chart API Tests - Iteration 60
Tests the SECOND complete rebuild of org chart with 85 positions.
New hierarchy: Encampment Commander → Commandant → CTG/CC → [CTG/CD, CTG/DF, CTG/CCEA, CSS/CC, CTO, Squadrons]
New categories: command, cadet_training, support, cadet_support
Dual reporting: CSS/CC has secondary_reports_to = ctg-df
"""
import pytest
import requests
import os

from tests.conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, PARENT_EMAIL, PARENT_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestOrgChartV2API:
    """Org Chart v2 endpoint tests - 85 positions with restructured hierarchy"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as commander before each test"""
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        
    def test_get_all_roles_returns_85_positions(self):
        """GET /api/org-chart/roles should return exactly 85 positions"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 85, f"Expected 85 positions, got {len(data)}"
        
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
        assert root['role_category'] == 'command'
        
    def test_encampment_commander_has_5_direct_reports(self):
        """Encampment Commander should have 5 direct reports"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/enc-commander")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data['children']) == 5, f"Expected 5 children, got {len(data['children'])}: {data['children']}"
        expected_children = ['commandant', 'dcs', 'sm-superintendent', 'chaplains', 'safety']
        for child_id in expected_children:
            assert child_id in data['children'], f"Missing child: {child_id}"
            
    def test_commandant_has_ctg_cc_underneath(self):
        """Commandant of Cadets should have CTG/CC as child"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/commandant")
        assert response.status_code == 200
        data = response.json()
        
        assert data['position_title'] == 'Commandant of Cadets'
        assert 'ctg-cc' in data['children'], f"CTG/CC not found in children: {data['children']}"
        
    def test_ctg_cc_has_8_children(self):
        """CTG/CC should have 8 children: CTG/CD, CTG/DF, CTG/CCEA, CSS/CC, CTO, 6th/21st/22nd CTS"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/ctg-cc")
        assert response.status_code == 200
        data = response.json()
        
        assert data['position_title'] == 'Cadet Training Group Commander'
        assert data['display_label'] == 'CTG/CC'
        assert data['assigned_name'] == 'C/Lt Col Yoder, L'
        
        expected_children = [
            'ctg-cd', 'ctg-df', 'ctg-ccea', 'css-cc', 
            'chief-training-officer', '6th-sq-cmdr', '21st-sq-cmdr', '22nd-sq-cmdr'
        ]
        assert len(data['children']) == 8, f"Expected 8 children, got {len(data['children'])}: {data['children']}"
        for child_id in expected_children:
            assert child_id in data['children'], f"Missing child: {child_id}"
            
    def test_dcs_has_5_children(self):
        """DCS should have 5 children: XP, LG, Comm, Finance, Health Services/WORD"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/dcs")
        assert response.status_code == 200
        data = response.json()
        
        assert data['position_title'] == 'Deputy Commander for Support'
        assert data['display_label'] == 'DCS'
        
        expected_children = ['xp-plans', 'lg-logistics', 'comm', 'finance', 'health-word']
        assert len(data['children']) == 5, f"Expected 5 children, got {len(data['children'])}: {data['children']}"
        for child_id in expected_children:
            assert child_id in data['children'], f"Missing child: {child_id}"
            
    def test_css_cc_has_secondary_reports_to(self):
        """CSS/CC should have secondary_reports_to = ctg-df (dual reporting)"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/css-cc")
        assert response.status_code == 200
        data = response.json()
        
        assert data['position_title'] == 'Cadet Support Squadron Commander'
        assert data['display_label'] == 'CSS/CC'
        assert data['reports_to'] == 'ctg-cc', f"Primary reports_to should be ctg-cc, got {data['reports_to']}"
        assert data['secondary_reports_to'] == 'ctg-df', f"Secondary reports_to should be ctg-df, got {data.get('secondary_reports_to')}"
        
    def test_schema_includes_secondary_reports_to(self):
        """Verify response schema has secondary_reports_to field"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/enc-commander")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            'id', 'role_id', 'position_title', 'assigned_name', 
            'reports_to', 'secondary_reports_to', 'role_category', 'children', 
            'job_description', 'display_label', 'responsible_for', 'supervises', 
            'created_at', 'updated_at'
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
            
    def test_4_role_categories_present(self):
        """Verify all 4 new role categories are represented"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        data = response.json()
        
        categories = set(r['role_category'] for r in data if r.get('role_category'))
        expected_categories = {'command', 'cadet_training', 'support', 'cadet_support'}
        
        for cat in expected_categories:
            assert cat in categories, f"Missing category: {cat}"
            
    def test_no_ctg_cce_position_exists(self):
        """Verify CTG/CCE position does NOT exist (was removed)"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        data = response.json()
        
        role_ids = [r['role_id'] for r in data]
        assert 'ctg-cce' not in role_ids, "CTG/CCE should not exist in new hierarchy"
        
        # Also check by position title
        titles = [r['position_title'].lower() for r in data]
        assert not any('ctg/cce' in t for t in titles), "No position should have CTG/CCE in title"


class TestOrgChartV2Hierarchy:
    """Tests for specific hierarchy relationships in v2"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as commander before each test"""
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert login_resp.status_code == 200
        
    def test_6th_cts_structure(self):
        """6th CTS Commander should have TO, 1stSgt, Flight A, Flight B"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/6th-sq-cmdr")
        assert response.status_code == 200
        data = response.json()
        
        assert data['position_title'] == '6th CTS Commander'
        assert data['display_label'] == '6th CTS'
        assert data['assigned_name'] == 'C/Capt Nhan, V'
        
        expected = ['6th-sq-to', '6th-sq-1sgt', '6th-flt-a-cmdr', '6th-flt-b-cmdr']
        for child_id in expected:
            assert child_id in data['children'], f"Missing child: {child_id}"
            
    def test_21st_cts_structure(self):
        """21st CTS Commander should have TO, 1stSgt, Flight C, Flight D"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/21st-sq-cmdr")
        assert response.status_code == 200
        data = response.json()
        
        assert data['position_title'] == '21st CTS Commander'
        assert data['assigned_name'] == "C/2nd Lt Nair, P"
        expected = ['21st-sq-to', '21st-sq-1sgt', '21st-flt-c-cmdr', '21st-flt-d-cmdr']
        for child_id in expected:
            assert child_id in data['children']
            
    def test_22nd_cts_structure(self):
        """22nd CTS Commander should have TO, 1stSgt, Flight E, Flight F"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/22nd-sq-cmdr")
        assert response.status_code == 200
        data = response.json()
        
        assert data['position_title'] == '22nd CTS Commander'
        assert data['assigned_name'] == "C/1st Lt Breslin, D"
        expected = ['22nd-sq-to', '22nd-sq-1sgt', '22nd-flt-e-cmdr', '22nd-flt-f-cmdr']
        for child_id in expected:
            assert child_id in data['children']
            
    def test_ctg_ccea_has_public_affairs_and_dining(self):
        """CTG/CCEA should have Public Affairs and Dining Facility departments"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/ctg-ccea")
        assert response.status_code == 200
        data = response.json()
        
        assert data['position_title'] == 'Chief Cadet Enlisted Advisor'
        assert data['display_label'] == 'CTG/CCEA'
        assert 'public-affairs-dept' in data['children']
        assert 'dining-facility-dept' in data['children']
        
    def test_css_cc_has_7_children(self):
        """CSS/CC should have 7 children: TO, 1stSgt, Logistics, PA, Comms, Dining, WORD"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/css-cc")
        assert response.status_code == 200
        data = response.json()
        
        expected = ['css-to', 'css-1sgt', 'css-logistics', 'css-pa', 'css-comms', 'css-dining', 'css-word']
        assert len(data['children']) == 7, f"Expected 7 children, got {len(data['children'])}: {data['children']}"
        for child_id in expected:
            assert child_id in data['children'], f"Missing child: {child_id}"
            
    def test_cto_has_7_children(self):
        """CTO should have Plans & Programs, Media & Publishing, SM, and 4 Cadets"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/chief-training-officer")
        assert response.status_code == 200
        data = response.json()
        
        assert data['position_title'] == 'Chief Training Officer'
        assert data['display_label'] == 'CTO'
        assert len(data['children']) == 7, f"Expected 7 children, got {len(data['children'])}: {data['children']}"
        
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


class TestOrgChartV2Categories:
    """Tests for the 4 new category colors"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as commander before each test"""
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert login_resp.status_code == 200
        
    def test_command_category_positions(self):
        """Verify command category positions (dark blue)"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        data = response.json()
        
        command_positions = [r for r in data if r['role_category'] == 'command']
        command_ids = [r['role_id'] for r in command_positions]
        
        # Encampment Commander, Commandant, SM Superintendent, Chaplains, Safety should be command
        expected_command = ['enc-commander', 'commandant', 'sm-superintendent', 'chaplains', 'safety']
        for role_id in expected_command:
            assert role_id in command_ids, f"{role_id} should be in command category"
            
    def test_cadet_training_category_positions(self):
        """Verify cadet_training category positions (green)"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        data = response.json()
        
        training_positions = [r for r in data if r['role_category'] == 'cadet_training']
        training_ids = [r['role_id'] for r in training_positions]
        
        # CTG/CC, CTG/CD, CTG/DF, CTG/CCEA, CTO, Squadron Commanders should be cadet_training
        expected_training = ['ctg-cc', 'ctg-cd', 'ctg-df', 'ctg-ccea', 'chief-training-officer', '6th-sq-cmdr']
        for role_id in expected_training:
            assert role_id in training_ids, f"{role_id} should be in cadet_training category"
            
    def test_support_category_positions(self):
        """Verify support category positions (amber)"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        data = response.json()
        
        support_positions = [r for r in data if r['role_category'] == 'support']
        support_ids = [r['role_id'] for r in support_positions]
        
        # DCS, XP, LG, Comm, Finance, Health Services should be support
        expected_support = ['dcs', 'xp-plans', 'lg-logistics', 'comm', 'finance', 'health-word']
        for role_id in expected_support:
            assert role_id in support_ids, f"{role_id} should be in support category"
            
    def test_cadet_support_category_positions(self):
        """Verify cadet_support category positions (purple)"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        data = response.json()
        
        cadet_support_positions = [r for r in data if r['role_category'] == 'cadet_support']
        cadet_support_ids = [r['role_id'] for r in cadet_support_positions]
        
        # CSS/CC and its children should be cadet_support
        expected_cadet_support = ['css-cc', 'css-to', 'css-1sgt', 'css-logistics', 'css-pa', 'css-comms', 'css-dining', 'css-word']
        for role_id in expected_cadet_support:
            assert role_id in cadet_support_ids, f"{role_id} should be in cadet_support category"


class TestOrgChartV2CRUD:
    """CRUD operation tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as commander before each test"""
        self.session = requests.Session()
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert login_resp.status_code == 200
        
    def test_update_role_position(self):
        """PUT /api/org-chart/roles/{role_id} should update position details"""
        # First get current state
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/chaplains")
        assert response.status_code == 200
        original = response.json()
        
        # Update job description
        update_data = {"job_description": "Test job description for chaplain v2"}
        response = self.session.put(
            f"{BASE_URL}/api/org-chart/roles/chaplains",
            json=update_data
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated['job_description'] == "Test job description for chaplain v2"
        
        # Restore original
        self.session.put(
            f"{BASE_URL}/api/org-chart/roles/chaplains",
            json={"job_description": original.get('job_description', '')}
        )
        
    def test_create_and_delete_role(self):
        """POST and DELETE /api/org-chart/roles should work"""
        # Create a test role
        new_role = {
            "role_id": "test-position-60",
            "position_title": "Test Position V2",
            "assigned_name": "Test Person V2",
            "reports_to": "enc-commander",
            "role_category": "cadet_training",
            "order": 99
        }
        
        response = self.session.post(f"{BASE_URL}/api/org-chart/roles", json=new_role)
        assert response.status_code == 200, f"Create failed: {response.text}"
        created = response.json()
        assert created['position_title'] == "Test Position V2"
        
        # Delete the test role
        response = self.session.delete(f"{BASE_URL}/api/org-chart/roles/test-position-60")
        assert response.status_code == 200
        
        # Verify deleted
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/test-position-60")
        assert response.status_code == 404
        
    def test_cannot_delete_role_with_subordinates(self):
        """DELETE should fail for roles with subordinates"""
        response = self.session.delete(f"{BASE_URL}/api/org-chart/roles/enc-commander")
        assert response.status_code == 400
        assert "subordinate" in response.json()['detail'].lower()
        
    def test_seed_endpoint_reseeds_85_positions(self):
        """POST /api/org-chart/seed should reseed with 85 positions"""
        response = self.session.post(f"{BASE_URL}/api/org-chart/seed")
        assert response.status_code == 200
        data = response.json()
        assert "85" in data['message'], f"Expected 85 in message, got: {data['message']}"
        
        # Verify count is 85
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert len(response.json()) == 85
