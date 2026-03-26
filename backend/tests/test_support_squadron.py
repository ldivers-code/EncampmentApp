"""
Test Support Squadron Hierarchical Structure
Tests the 21 support squadron roles (1 commander + 5 sections × 4 roles each)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
COMMANDER_EMAIL = "commander@test.com"
COMMANDER_PASSWORD = "Test1234!"

# Support Squadron role definitions
SUPPORT_SQ_COMMANDER = "support-sq-cc"
SUPPORT_SECTIONS = ["logistics", "comms", "pa", "dining", "health"]
SUPPORT_ROLE_TYPES = ["oic", "aoic", "ncoic", "cadre"]

# Expected 21 support roles: 1 commander + 5 sections × 4 roles = 21
EXPECTED_SUPPORT_ROLE_COUNT = 21


class TestSupportSquadronBackend:
    """Backend API tests for Support Squadron hierarchical structure"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as commander
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.auth_token = token
        else:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
    
    def test_org_chart_roles_endpoint_returns_200(self):
        """Test that org chart roles endpoint is accessible"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ Org chart roles endpoint returns 200")
    
    def test_total_support_squadron_roles_count(self):
        """Test that API returns all 21 support squadron roles"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        
        roles = response.json()
        support_roles = [r for r in roles if r['role_id'].startswith('support-')]
        
        assert len(support_roles) == EXPECTED_SUPPORT_ROLE_COUNT, \
            f"Expected {EXPECTED_SUPPORT_ROLE_COUNT} support roles, got {len(support_roles)}"
        print(f"✓ Found {len(support_roles)} support squadron roles (expected {EXPECTED_SUPPORT_ROLE_COUNT})")
    
    def test_support_squadron_commander_exists(self):
        """Test that Support Squadron Commander role exists"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        
        roles = response.json()
        support_cc = next((r for r in roles if r['role_id'] == SUPPORT_SQ_COMMANDER), None)
        
        assert support_cc is not None, "Support Squadron Commander role not found"
        assert support_cc['title'] == "Support Squadron Commander"
        assert support_cc['reports_to'] == "deputy-support"
        print(f"✓ Support Squadron Commander exists and reports to deputy-support")
    
    def test_all_five_sections_have_oic(self):
        """Test that all 5 functional sections have OIC roles"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        
        roles = response.json()
        
        for section in SUPPORT_SECTIONS:
            oic_role_id = f"support-{section}-oic"
            oic_role = next((r for r in roles if r['role_id'] == oic_role_id), None)
            
            assert oic_role is not None, f"OIC role for {section} not found"
            assert oic_role['reports_to'] == SUPPORT_SQ_COMMANDER, \
                f"{section} OIC should report to support-sq-cc, got {oic_role['reports_to']}"
            print(f"✓ {section.capitalize()} OIC exists and reports to Support Sq CC")
    
    def test_all_sections_have_four_roles(self):
        """Test that each section has OIC, AOIC, NCOIC, and Cadre roles"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        
        roles = response.json()
        
        for section in SUPPORT_SECTIONS:
            section_roles = []
            for role_type in SUPPORT_ROLE_TYPES:
                role_id = f"support-{section}-{role_type}"
                role = next((r for r in roles if r['role_id'] == role_id), None)
                assert role is not None, f"Role {role_id} not found"
                section_roles.append(role)
            
            assert len(section_roles) == 4, f"Section {section} should have 4 roles"
            print(f"✓ {section.capitalize()} section has all 4 roles (OIC, AOIC, NCOIC, Cadre)")
    
    def test_aoic_ncoic_cadre_report_to_oic(self):
        """Test that AOIC, NCOIC, and Cadre report to their section OIC"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        
        roles = response.json()
        
        for section in SUPPORT_SECTIONS:
            oic_role_id = f"support-{section}-oic"
            
            for role_type in ["aoic", "ncoic", "cadre"]:
                role_id = f"support-{section}-{role_type}"
                role = next((r for r in roles if r['role_id'] == role_id), None)
                
                assert role is not None, f"Role {role_id} not found"
                assert role['reports_to'] == oic_role_id, \
                    f"{role_id} should report to {oic_role_id}, got {role['reports_to']}"
            
            print(f"✓ {section.capitalize()} AOIC/NCOIC/Cadre all report to {section} OIC")
    
    def test_individual_role_details_endpoint(self):
        """Test that individual role details can be fetched"""
        # Test Support Squadron Commander
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/{SUPPORT_SQ_COMMANDER}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        role = response.json()
        assert role['role_id'] == SUPPORT_SQ_COMMANDER
        assert 'title' in role
        assert 'reports_to' in role
        print(f"✓ Individual role details endpoint works for {SUPPORT_SQ_COMMANDER}")
    
    def test_support_role_details_have_correct_hierarchy(self):
        """Test that role details show correct hierarchy info"""
        # Test a specific section role
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/support-logistics-aoic")
        assert response.status_code == 200
        
        role = response.json()
        assert role['reports_to'] == "support-logistics-oic", \
            f"Logistics AOIC should report to support-logistics-oic"
        print(f"✓ Role details show correct hierarchy (Logistics AOIC reports to Logistics OIC)")
    
    def test_support_roles_have_summaries(self):
        """Test that support roles have summary descriptions"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        
        roles = response.json()
        support_roles = [r for r in roles if r['role_id'].startswith('support-')]
        
        roles_with_summary = [r for r in support_roles if r.get('summary')]
        assert len(roles_with_summary) > 0, "Support roles should have summaries"
        print(f"✓ {len(roles_with_summary)}/{len(support_roles)} support roles have summaries")
    
    def test_support_roles_have_responsibilities(self):
        """Test that support roles have responsibilities defined"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        
        roles = response.json()
        support_roles = [r for r in roles if r['role_id'].startswith('support-')]
        
        roles_with_responsibilities = [r for r in support_roles if r.get('responsibilities')]
        assert len(roles_with_responsibilities) > 0, "Support roles should have responsibilities"
        print(f"✓ {len(roles_with_responsibilities)}/{len(support_roles)} support roles have responsibilities")
    
    def test_vacant_roles_have_no_assigned_member(self):
        """Test that vacant roles show no assigned member"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        
        roles = response.json()
        support_roles = [r for r in roles if r['role_id'].startswith('support-')]
        
        # Check that roles without assignments have None/null for assigned_member_name
        for role in support_roles:
            if not role.get('assigned_participant_id'):
                # Vacant role should have no assigned_member_name or it should be None
                assert role.get('assigned_member_name') is None or role.get('assigned_member_name') == '', \
                    f"Vacant role {role['role_id']} should not have assigned_member_name"
        
        print(f"✓ Vacant roles correctly show no assigned member")
    
    def test_total_org_chart_roles_count(self):
        """Test total org chart roles count (should be ~79 based on context)"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        
        roles = response.json()
        print(f"✓ Total org chart roles: {len(roles)}")
        
        # Verify we have a reasonable number of roles
        assert len(roles) >= 50, f"Expected at least 50 total roles, got {len(roles)}"


class TestSupportSquadronRoleIds:
    """Test specific role IDs exist in the system"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip(f"Authentication failed")
    
    @pytest.mark.parametrize("role_id,expected_title", [
        ("support-sq-cc", "Support Squadron Commander"),
        ("support-logistics-oic", "Logistics OIC"),
        ("support-logistics-aoic", "Logistics AOIC"),
        ("support-logistics-ncoic", "Logistics NCOIC"),
        ("support-logistics-cadre", "Logistics Cadre"),
        ("support-comms-oic", "Communications OIC"),
        ("support-comms-aoic", "Communications AOIC"),
        ("support-comms-ncoic", "Communications NCOIC"),
        ("support-comms-cadre", "Communications Cadre"),
        ("support-pa-oic", "Public Affairs OIC"),
        ("support-pa-aoic", "Public Affairs AOIC"),
        ("support-pa-ncoic", "Public Affairs NCOIC"),
        ("support-pa-cadre", "Public Affairs Cadre"),
        ("support-dining-oic", "Dining Services OIC"),
        ("support-dining-aoic", "Dining Services AOIC"),
        ("support-dining-ncoic", "Dining Services NCOIC"),
        ("support-dining-cadre", "Dining Services Cadre"),
        ("support-health-oic", "Health Services OIC"),
        ("support-health-aoic", "Health Services AOIC"),
        ("support-health-ncoic", "Health Services NCOIC"),
        ("support-health-cadre", "Health Services Cadre"),
    ])
    def test_support_role_exists(self, role_id, expected_title):
        """Test that each support role exists with correct title"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/{role_id}")
        assert response.status_code == 200, f"Role {role_id} not found (status {response.status_code})"
        
        role = response.json()
        assert role['title'] == expected_title, \
            f"Role {role_id} has title '{role['title']}', expected '{expected_title}'"
        print(f"✓ {role_id}: {expected_title}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
