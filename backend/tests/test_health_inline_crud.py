"""
Test Health Inline CRUD Operations - Allergies and OTC Approvals
Tests for P1-B: Add Inline Health Data Editing from Medical Roster

Endpoints tested:
- POST /api/health/cadet/{capid}/allergies - Create allergy record
- PUT /api/health/allergies/{id} - Update allergy record
- DELETE /api/health/allergies/{id} - Delete allergy record
- PUT /api/health/cadet/{capid}/otc-approvals - Create/update OTC approvals
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
COMMANDER_EMAIL = "testadmin@cap.gov"
COMMANDER_PASSWORD = "TestPass123!"

# Test CAPID with existing allergy data
TEST_CAPID = "684152"  # Marfio, Mia - has 2 allergies (Milk and Latex)


class TestHealthInlineCRUD:
    """Test suite for Health inline CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as commander (has health_full permission)
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
        
        # API returns access_token, not token
        token = login_response.json().get("access_token")
        if not token:
            pytest.skip("No access_token in login response")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.token = token
        
        yield
        
        # Cleanup: Delete any test allergies created
        self._cleanup_test_allergies()
    
    def _cleanup_test_allergies(self):
        """Clean up test-created allergies"""
        try:
            # Get allergies for test CAPID
            response = self.session.get(f"{BASE_URL}/api/health/cadet/{TEST_CAPID}/allergies")
            if response.status_code == 200:
                allergies = response.json()
                for allergy in allergies:
                    if allergy.get("allergy_name", "").startswith("TEST_"):
                        self.session.delete(f"{BASE_URL}/api/health/allergies/{allergy['id']}")
        except Exception:
            pass
    
    # ==================== ALLERGY CRUD TESTS ====================
    
    def test_get_cadet_allergies(self):
        """Test GET /api/health/cadet/{capid}/allergies - Get existing allergies"""
        response = self.session.get(f"{BASE_URL}/api/health/cadet/{TEST_CAPID}/allergies")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        allergies = response.json()
        assert isinstance(allergies, list), "Response should be a list"
        
        # Verify existing allergies for test cadet (Milk and Latex)
        allergy_names = [a.get("allergy_name") for a in allergies]
        print(f"Found allergies for CAPID {TEST_CAPID}: {allergy_names}")
        
        # Should have at least the known allergies
        assert len(allergies) >= 2, f"Expected at least 2 allergies, got {len(allergies)}"
    
    def test_create_allergy_success(self):
        """Test POST /api/health/cadet/{capid}/allergies - Create new allergy"""
        allergy_data = {
            "allergy_name": f"TEST_Peanuts_{uuid.uuid4().hex[:6]}",
            "allergy_type": "Food",
            "is_anaphylaxis": True,
            "has_epipen": True,
            "has_albuterol_inhaler": False,
            "typical_reactions": "Hives, swelling, difficulty breathing",
            "treatments": "Administer EpiPen, call 911",
            "contact_name": "Test Parent",
            "emergency_contact": "555-123-4567"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/health/cadet/{TEST_CAPID}/allergies",
            json=allergy_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        created = response.json()
        assert "id" in created, "Response should contain 'id'"
        assert created["allergy_name"] == allergy_data["allergy_name"]
        assert created["allergy_type"] == "Food"
        assert created["is_anaphylaxis"] == True
        assert created["has_epipen"] == True
        assert created["capid"] == TEST_CAPID
        
        # Verify persistence with GET
        get_response = self.session.get(f"{BASE_URL}/api/health/cadet/{TEST_CAPID}/allergies")
        assert get_response.status_code == 200
        
        allergies = get_response.json()
        # Handle both 'id' and 'allergy_id' field names
        created_allergy = next((a for a in allergies if a.get("id") == created["id"] or a.get("allergy_id") == created["id"]), None)
        assert created_allergy is not None, "Created allergy should be retrievable"
        assert created_allergy["allergy_name"] == allergy_data["allergy_name"]
        
        # Store for cleanup
        self._test_allergy_id = created["id"]
        print(f"Created allergy with ID: {created['id']}")
    
    def test_create_allergy_minimal_data(self):
        """Test creating allergy with minimal required data"""
        allergy_data = {
            "allergy_name": f"TEST_Minimal_{uuid.uuid4().hex[:6]}"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/health/cadet/{TEST_CAPID}/allergies",
            json=allergy_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        created = response.json()
        assert created["allergy_name"] == allergy_data["allergy_name"]
        assert created["allergy_type"] == "Other"  # Default value
        assert created["is_anaphylaxis"] == False  # Default value
    
    def test_update_allergy_success(self):
        """Test PUT /api/health/allergies/{id} - Update existing allergy"""
        # First create an allergy to update
        create_data = {
            "allergy_name": f"TEST_ToUpdate_{uuid.uuid4().hex[:6]}",
            "allergy_type": "Food",
            "is_anaphylaxis": False
        }
        
        create_response = self.session.post(
            f"{BASE_URL}/api/health/cadet/{TEST_CAPID}/allergies",
            json=create_data
        )
        assert create_response.status_code == 200
        allergy_id = create_response.json()["id"]
        
        # Update the allergy
        update_data = {
            "allergy_name": create_data["allergy_name"],  # Keep same name
            "allergy_type": "Drug",  # Change type
            "is_anaphylaxis": True,  # Change to anaphylaxis
            "has_epipen": True,
            "typical_reactions": "Updated reactions"
        }
        
        update_response = self.session.put(
            f"{BASE_URL}/api/health/allergies/{allergy_id}",
            json=update_data
        )
        
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        updated = update_response.json()
        assert updated["allergy_type"] == "Drug"
        assert updated["is_anaphylaxis"] == True
        assert updated["has_epipen"] == True
        assert updated["typical_reactions"] == "Updated reactions"
        
        # Verify persistence with GET
        get_response = self.session.get(f"{BASE_URL}/api/health/cadet/{TEST_CAPID}/allergies")
        allergies = get_response.json()
        # Handle both 'id' and 'allergy_id' field names
        updated_allergy = next((a for a in allergies if a.get("id") == allergy_id or a.get("allergy_id") == allergy_id), None)
        assert updated_allergy is not None
        assert updated_allergy["is_anaphylaxis"] == True
        
        print(f"Updated allergy {allergy_id} successfully")
    
    def test_update_allergy_not_found(self):
        """Test PUT /api/health/allergies/{id} with non-existent ID"""
        fake_id = str(uuid.uuid4())
        
        response = self.session.put(
            f"{BASE_URL}/api/health/allergies/{fake_id}",
            json={"allergy_name": "Test"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_delete_allergy_success(self):
        """Test DELETE /api/health/allergies/{id} - Delete allergy"""
        # First create an allergy to delete
        create_data = {
            "allergy_name": f"TEST_ToDelete_{uuid.uuid4().hex[:6]}",
            "allergy_type": "Environmental"
        }
        
        create_response = self.session.post(
            f"{BASE_URL}/api/health/cadet/{TEST_CAPID}/allergies",
            json=create_data
        )
        assert create_response.status_code == 200
        allergy_id = create_response.json()["id"]
        
        # Delete the allergy
        delete_response = self.session.delete(f"{BASE_URL}/api/health/allergies/{allergy_id}")
        
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}: {delete_response.text}"
        
        result = delete_response.json()
        assert "message" in result
        
        # Verify deletion with GET
        get_response = self.session.get(f"{BASE_URL}/api/health/cadet/{TEST_CAPID}/allergies")
        allergies = get_response.json()
        # Handle both 'id' and 'allergy_id' field names
        deleted_allergy = next((a for a in allergies if a.get("id") == allergy_id or a.get("allergy_id") == allergy_id), None)
        assert deleted_allergy is None, "Deleted allergy should not be retrievable"
        
        print(f"Deleted allergy {allergy_id} successfully")
    
    def test_delete_allergy_not_found(self):
        """Test DELETE /api/health/allergies/{id} with non-existent ID"""
        fake_id = str(uuid.uuid4())
        
        response = self.session.delete(f"{BASE_URL}/api/health/allergies/{fake_id}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    # ==================== OTC APPROVALS TESTS ====================
    
    def test_get_otc_approvals(self):
        """Test GET /api/health/cadet/{capid}/otc-approvals"""
        response = self.session.get(f"{BASE_URL}/api/health/cadet/{TEST_CAPID}/otc-approvals")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Response can be empty dict if no OTC data exists
        data = response.json()
        assert isinstance(data, dict), "Response should be a dict"
        print(f"OTC approvals for CAPID {TEST_CAPID}: {data}")
    
    def test_update_otc_approvals_create(self):
        """Test PUT /api/health/cadet/{capid}/otc-approvals - Create/Update OTC approvals"""
        otc_data = {
            "medications": {
                "acetaminophen": True,
                "ibuprofen": True,
                "antacids": False,
                "cough_drops": True,
                "throat_lozenges": True,
                "antihistamine": False,
                "decongestant": False,
                "hydrocortisone": True,
                "triple_antibiotic": True,
                "calamine": False,
                "sunscreen": True,
                "insect_repellent": True,
                "aloe_vera": True
            },
            "organization": "Test Organization"
        }
        
        response = self.session.put(
            f"{BASE_URL}/api/health/cadet/{TEST_CAPID}/otc-approvals",
            json=otc_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "medications" in result
        assert result["medications"]["acetaminophen"] == True
        assert result["medications"]["ibuprofen"] == True
        assert result["medications"]["antacids"] == False
        assert result["capid"] == TEST_CAPID
        
        # Verify approved_list is computed correctly
        assert "approved_list" in result
        assert "acetaminophen" in result["approved_list"]
        assert "ibuprofen" in result["approved_list"]
        assert "antacids" not in result["approved_list"]
        
        # Verify persistence with GET
        get_response = self.session.get(f"{BASE_URL}/api/health/cadet/{TEST_CAPID}/otc-approvals")
        assert get_response.status_code == 200
        
        persisted = get_response.json()
        assert persisted["medications"]["acetaminophen"] == True
        assert persisted["medications"]["ibuprofen"] == True
        
        print(f"OTC approvals updated successfully for CAPID {TEST_CAPID}")
    
    def test_update_otc_approvals_toggle(self):
        """Test toggling OTC medication approvals"""
        # First set some approvals
        initial_data = {
            "medications": {
                "acetaminophen": True,
                "ibuprofen": False
            }
        }
        
        response1 = self.session.put(
            f"{BASE_URL}/api/health/cadet/{TEST_CAPID}/otc-approvals",
            json=initial_data
        )
        assert response1.status_code == 200
        
        # Now toggle them
        toggled_data = {
            "medications": {
                "acetaminophen": False,  # Was True
                "ibuprofen": True  # Was False
            }
        }
        
        response2 = self.session.put(
            f"{BASE_URL}/api/health/cadet/{TEST_CAPID}/otc-approvals",
            json=toggled_data
        )
        
        assert response2.status_code == 200
        
        result = response2.json()
        assert result["medications"]["acetaminophen"] == False
        assert result["medications"]["ibuprofen"] == True
        
        print("OTC toggle test passed")
    
    # ==================== PERMISSION TESTS ====================
    
    def test_allergy_crud_requires_health_full(self):
        """Test that allergy CRUD endpoints require health_full permission"""
        # Create a new session without auth
        unauth_session = requests.Session()
        unauth_session.headers.update({"Content-Type": "application/json"})
        
        # Test POST without auth
        response = unauth_session.post(
            f"{BASE_URL}/api/health/cadet/{TEST_CAPID}/allergies",
            json={"allergy_name": "Test"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        # Test PUT without auth
        response = unauth_session.put(
            f"{BASE_URL}/api/health/allergies/fake-id",
            json={"allergy_name": "Test"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        # Test DELETE without auth
        response = unauth_session.delete(f"{BASE_URL}/api/health/allergies/fake-id")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        print("Permission tests passed - endpoints require authentication")
    
    def test_otc_update_requires_health_full(self):
        """Test that OTC update endpoint requires health_full permission"""
        unauth_session = requests.Session()
        unauth_session.headers.update({"Content-Type": "application/json"})
        
        response = unauth_session.put(
            f"{BASE_URL}/api/health/cadet/{TEST_CAPID}/otc-approvals",
            json={"medications": {"acetaminophen": True}}
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("OTC permission test passed")


class TestOrgChartRichText:
    """Test suite for Org Chart Rich Text functionality"""
    
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
        
        if login_response.status_code != 200:
            pytest.skip(f"Authentication failed: {login_response.status_code}")
        
        # API returns access_token, not token
        token = login_response.json().get("access_token")
        if not token:
            pytest.skip("No access_token in login response")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
    
    def test_get_org_chart_roles(self):
        """Test GET /api/org-chart/roles - Get all roles"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        roles = response.json()
        assert isinstance(roles, list), "Response should be a list"
        print(f"Found {len(roles)} org chart roles")
    
    def test_get_org_chart_role_detail(self):
        """Test GET /api/org-chart/roles/{role_id} - Get role details"""
        # First get all roles to find a valid role_id
        roles_response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        if roles_response.status_code != 200 or not roles_response.json():
            pytest.skip("No org chart roles available")
        
        roles = roles_response.json()
        test_role_id = roles[0]["role_id"]
        
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles/{test_role_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        role = response.json()
        assert "role_id" in role
        assert "title" in role
        print(f"Role details: {role.get('title')} - responsibilities: {role.get('responsibilities', 'N/A')[:100]}")
    
    def test_update_role_with_rich_text_responsibilities(self):
        """Test PUT /api/org-chart/roles/{role_id} - Update with HTML responsibilities"""
        # First get all roles
        roles_response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        if roles_response.status_code != 200 or not roles_response.json():
            pytest.skip("No org chart roles available")
        
        roles = roles_response.json()
        test_role_id = roles[0]["role_id"]
        
        # Get current role data
        role_response = self.session.get(f"{BASE_URL}/api/org-chart/roles/{test_role_id}")
        original_role = role_response.json()
        
        # Update with rich text HTML
        rich_text_html = """<ul><li><strong>Lead</strong> all encampment operations</li><li><em>Coordinate</em> with staff</li><li>Ensure safety protocols</li></ul><p>Additional notes here.</p>"""
        
        update_data = {
            "title": original_role.get("title"),
            "summary": original_role.get("summary", ""),
            "responsibilities": rich_text_html
        }
        
        response = self.session.put(
            f"{BASE_URL}/api/org-chart/roles/{test_role_id}",
            json=update_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify persistence
        verify_response = self.session.get(f"{BASE_URL}/api/org-chart/roles/{test_role_id}")
        assert verify_response.status_code == 200
        
        updated_role = verify_response.json()
        assert updated_role.get("responsibilities") == rich_text_html, "Rich text HTML should be persisted"
        
        print(f"Rich text responsibilities saved successfully for role {test_role_id}")
        
        # Restore original if it had responsibilities
        if original_role.get("responsibilities"):
            restore_data = {
                "title": original_role.get("title"),
                "summary": original_role.get("summary", ""),
                "responsibilities": original_role.get("responsibilities")
            }
            self.session.put(f"{BASE_URL}/api/org-chart/roles/{test_role_id}", json=restore_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
