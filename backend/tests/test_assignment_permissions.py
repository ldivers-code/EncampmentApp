"""
Test suite for participant assignment permissions
Tests the role-based access control for /api/participants/{id}/assignment endpoint

Permissions:
- Full access roles (DCP, Commander, Executive Staff, Plans & Programs, Staff): Can edit BOTH students and cadre
- Cadre-only roles (Exec Cadre): Can ONLY edit cadre, NOT students (should get 403)
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD
EXEC_CADRE_EMAIL = "execcadre@cap.test.com"
EXEC_CADRE_PASSWORD = COMMANDER_PASSWORD


class TestAssignmentPermissions:
    """Test role-based permissions for participant assignment endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_auth_token(self, email, password):
        """Helper to get auth token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def get_participants_by_type(self, token, participant_type):
        """Helper to get participants filtered by type"""
        headers = {"Authorization": f"Bearer {token}"}
        response = self.session.get(f"{BASE_URL}/api/participants", headers=headers)
        if response.status_code == 200:
            participants = response.json()
            return [p for p in participants if p.get("participant_type") == participant_type]
        return []
    
    # ============ Commander Tests (Full Access) ============
    
    def test_commander_can_login(self):
        """Test commander can login"""
        token = self.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert token is not None, "Commander should be able to login"
        print(f"✓ Commander login successful")
    
    def test_commander_can_edit_student_assignment(self):
        """Commander should be able to edit student flight/squadron assignments"""
        token = self.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert token is not None, "Commander login failed"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get a student participant
        students = self.get_participants_by_type(token, "basic_student")
        if not students:
            students = self.get_participants_by_type(token, "advanced_student")
        
        assert len(students) > 0, "No students found in database"
        student = students[0]
        student_id = student["id"]
        
        # Try to update student assignment
        response = self.session.put(
            f"{BASE_URL}/api/participants/{student_id}/assignment",
            json={"flight": "Alpha", "squadron": "6th_cts"},
            headers=headers
        )
        
        assert response.status_code == 200, f"Commander should be able to edit student assignment. Got: {response.status_code} - {response.text}"
        print(f"✓ Commander can edit student assignment (status: {response.status_code})")
    
    def test_commander_can_edit_cadre_assignment(self):
        """Commander should be able to edit cadre flight/squadron assignments"""
        token = self.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert token is not None, "Commander login failed"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get a cadre participant
        cadre = self.get_participants_by_type(token, "cadre")
        assert len(cadre) > 0, "No cadre found in database"
        cadre_member = cadre[0]
        cadre_id = cadre_member["id"]
        
        # Try to update cadre assignment
        response = self.session.put(
            f"{BASE_URL}/api/participants/{cadre_id}/assignment",
            json={"flight": "Bravo", "squadron": "6th_cts"},
            headers=headers
        )
        
        assert response.status_code == 200, f"Commander should be able to edit cadre assignment. Got: {response.status_code} - {response.text}"
        print(f"✓ Commander can edit cadre assignment (status: {response.status_code})")
    
    # ============ Exec Cadre Tests (Cadre Only) ============
    
    def test_exec_cadre_can_login(self):
        """Test exec_cadre can login"""
        token = self.get_auth_token(EXEC_CADRE_EMAIL, EXEC_CADRE_PASSWORD)
        assert token is not None, "Exec Cadre should be able to login"
        print(f"✓ Exec Cadre login successful")
    
    def test_exec_cadre_can_edit_cadre_assignment(self):
        """Exec Cadre should be able to edit cadre flight/squadron assignments"""
        token = self.get_auth_token(EXEC_CADRE_EMAIL, EXEC_CADRE_PASSWORD)
        assert token is not None, "Exec Cadre login failed"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get a cadre participant
        cadre = self.get_participants_by_type(token, "cadre")
        assert len(cadre) > 0, "No cadre found in database"
        cadre_member = cadre[0]
        cadre_id = cadre_member["id"]
        
        # Try to update cadre assignment
        response = self.session.put(
            f"{BASE_URL}/api/participants/{cadre_id}/assignment",
            json={"flight": "Charlie", "squadron": "21st_cts"},
            headers=headers
        )
        
        assert response.status_code == 200, f"Exec Cadre should be able to edit cadre assignment. Got: {response.status_code} - {response.text}"
        print(f"✓ Exec Cadre can edit cadre assignment (status: {response.status_code})")
    
    def test_exec_cadre_cannot_edit_student_assignment(self):
        """Exec Cadre should NOT be able to edit student assignments - should get 403"""
        token = self.get_auth_token(EXEC_CADRE_EMAIL, EXEC_CADRE_PASSWORD)
        assert token is not None, "Exec Cadre login failed"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get a student participant
        students = self.get_participants_by_type(token, "basic_student")
        if not students:
            students = self.get_participants_by_type(token, "advanced_student")
        
        assert len(students) > 0, "No students found in database"
        student = students[0]
        student_id = student["id"]
        
        # Try to update student assignment - should fail with 403
        response = self.session.put(
            f"{BASE_URL}/api/participants/{student_id}/assignment",
            json={"flight": "Delta", "squadron": "21st_cts"},
            headers=headers
        )
        
        assert response.status_code == 403, f"Exec Cadre should NOT be able to edit student assignment. Expected 403, got: {response.status_code}"
        
        # Verify error message mentions the restriction
        error_detail = response.json().get("detail", "")
        assert "Exec Cadre" in error_detail or "student" in error_detail.lower(), f"Error message should mention restriction: {error_detail}"
        
        print(f"✓ Exec Cadre correctly blocked from editing student assignment (status: {response.status_code})")
        print(f"  Error message: {error_detail}")
    
    # ============ Unauthenticated Tests ============
    
    def test_unauthenticated_cannot_edit_assignment(self):
        """Unauthenticated users should not be able to edit assignments"""
        # Get any participant ID first (using commander)
        token = self.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        students = self.get_participants_by_type(token, "basic_student")
        if students:
            student_id = students[0]["id"]
            
            # Try without auth
            response = self.session.put(
                f"{BASE_URL}/api/participants/{student_id}/assignment",
                json={"flight": "Echo"}
            )
            
            assert response.status_code in [401, 403], f"Unauthenticated should be blocked. Got: {response.status_code}"
            print(f"✓ Unauthenticated users blocked (status: {response.status_code})")
        else:
            pytest.skip("No students found to test")
    
    # ============ Invalid Data Tests ============
    
    def test_invalid_participant_id_returns_404(self):
        """Invalid participant ID should return 404"""
        token = self.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert token is not None
        
        headers = {"Authorization": f"Bearer {token}"}
        fake_id = str(uuid.uuid4())
        
        response = self.session.put(
            f"{BASE_URL}/api/participants/{fake_id}/assignment",
            json={"flight": "Alpha"},
            headers=headers
        )
        
        assert response.status_code == 404, f"Invalid participant ID should return 404. Got: {response.status_code}"
        print(f"✓ Invalid participant ID returns 404")
    
    def test_invalid_flight_returns_400(self):
        """Invalid flight name should return 400"""
        token = self.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert token is not None
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get any participant
        students = self.get_participants_by_type(token, "basic_student")
        if students:
            student_id = students[0]["id"]
            
            response = self.session.put(
                f"{BASE_URL}/api/participants/{student_id}/assignment",
                json={"flight": "InvalidFlight123"},
                headers=headers
            )
            
            assert response.status_code == 400, f"Invalid flight should return 400. Got: {response.status_code}"
            print(f"✓ Invalid flight returns 400")
        else:
            pytest.skip("No students found to test")


class TestFrontendButtonVisibility:
    """
    Test that the frontend correctly shows/hides edit assignment buttons
    based on user role and participant type.
    
    Note: These are API-level tests that verify the data needed for frontend logic.
    The actual button visibility is tested via Playwright.
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_auth_token(self, email, password):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_exec_cadre_user_has_correct_role(self):
        """Verify exec_cadre user has the exec_cadre role"""
        token = self.get_auth_token(EXEC_CADRE_EMAIL, EXEC_CADRE_PASSWORD)
        assert token is not None, "Exec Cadre login failed"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = self.session.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        assert response.status_code == 200
        user_data = response.json()
        assert user_data.get("role") == "exec_cadre", f"Expected role 'exec_cadre', got: {user_data.get('role')}"
        print(f"✓ Exec Cadre user has correct role: {user_data.get('role')}")
    
    def test_commander_user_has_correct_role(self):
        """Verify commander user has the commander role"""
        token = self.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert token is not None, "Commander login failed"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = self.session.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        assert response.status_code == 200
        user_data = response.json()
        assert user_data.get("role") == "commander", f"Expected role 'commander', got: {user_data.get('role')}"
        print(f"✓ Commander user has correct role: {user_data.get('role')}")
    
    def test_participants_have_correct_types(self):
        """Verify participants have correct participant_type values"""
        token = self.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert token is not None
        
        headers = {"Authorization": f"Bearer {token}"}
        response = self.session.get(f"{BASE_URL}/api/participants", headers=headers)
        
        assert response.status_code == 200
        participants = response.json()
        
        # Count by type
        types = {}
        for p in participants:
            ptype = p.get("participant_type", "unknown")
            types[ptype] = types.get(ptype, 0) + 1
        
        print(f"✓ Participant types found: {types}")
        
        # Verify we have both students and cadre
        has_students = types.get("basic_student", 0) > 0 or types.get("advanced_student", 0) > 0
        has_cadre = types.get("cadre", 0) > 0
        
        assert has_students, "No students found in database"
        assert has_cadre, "No cadre found in database"
        print(f"✓ Database has both students and cadre for testing")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
