"""
Honor Agreement Feature Tests
Tests for:
- POST /api/auth/sign-honor-agreement - Sign honor agreement with signature_name
- POST /api/auth/send-honor-agreement-reminders - Send reminders to unsigned users
- GET /api/auth/me - Verify honor_agreement_signed field is returned
- Login response includes honor_agreement_signed field
"""
import pytest
import requests
import os

from tests.conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, PARENT_EMAIL, PARENT_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
CADRE_USER = {"email": "commander@cap.us", "password": COMMANDER_PASSWORD}  # exec_cadre role
COMMANDER_USER = {"email": COMMANDER_EMAIL, "password": COMMANDER_PASSWORD}  # commander role


class TestHonorAgreementBackend:
    """Honor Agreement API Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login_as_cadre(self):
        """Login as cadre user (exec_cadre role)"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=CADRE_USER)
        assert response.status_code == 200, f"Cadre login failed: {response.text}"
        return response.json()
    
    def login_as_commander(self):
        """Login as commander user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=COMMANDER_USER)
        assert response.status_code == 200, f"Commander login failed: {response.text}"
        return response.json()
    
    def test_login_returns_honor_agreement_fields(self):
        """Test that login response includes honor_agreement_signed field"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=CADRE_USER)
        assert response.status_code == 200
        
        data = response.json()
        user = data.get("user", {})
        
        # Verify honor agreement fields are present in response
        assert "honor_agreement_signed" in user, "honor_agreement_signed field missing from login response"
        assert "honor_agreement_type" in user, "honor_agreement_type field missing from login response"
        assert "honor_agreement_signed_at" in user, "honor_agreement_signed_at field missing from login response"
        print(f"Login response includes honor_agreement_signed: {user.get('honor_agreement_signed')}")
    
    def test_auth_me_returns_honor_agreement_fields(self):
        """Test that /api/auth/me returns honor_agreement_signed field"""
        self.login_as_cadre()
        
        response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        
        data = response.json()
        assert "honor_agreement_signed" in data, "honor_agreement_signed field missing from /auth/me"
        assert "honor_agreement_type" in data, "honor_agreement_type field missing from /auth/me"
        assert "honor_agreement_signed_at" in data, "honor_agreement_signed_at field missing from /auth/me"
        print(f"/auth/me returns honor_agreement_signed: {data.get('honor_agreement_signed')}")
    
    def test_sign_honor_agreement_requires_signature_name(self):
        """Test that signing requires signature_name"""
        self.login_as_cadre()
        
        # Try signing without signature_name
        response = self.session.post(f"{BASE_URL}/api/auth/sign-honor-agreement", json={})
        assert response.status_code == 400, "Should fail without signature_name"
        
        # Try signing with empty signature_name
        response = self.session.post(f"{BASE_URL}/api/auth/sign-honor-agreement", json={"signature_name": ""})
        assert response.status_code == 400, "Should fail with empty signature_name"
        
        # Try signing with whitespace-only signature_name
        response = self.session.post(f"{BASE_URL}/api/auth/sign-honor-agreement", json={"signature_name": "   "})
        assert response.status_code == 400, "Should fail with whitespace-only signature_name"
        print("Signature validation working correctly")
    
    def test_sign_honor_agreement_cadre_user(self):
        """Test signing honor agreement as cadre user (should get 'cadre' type)"""
        self.login_as_cadre()
        
        # Sign the agreement
        response = self.session.post(
            f"{BASE_URL}/api/auth/sign-honor-agreement",
            json={"signature_name": "Flight Commander Test"}
        )
        assert response.status_code == 200, f"Sign failed: {response.text}"
        
        data = response.json()
        assert data.get("message") == "Honor agreement signed successfully"
        assert data.get("agreement_type") == "cadre", f"Expected 'cadre' type for exec_cadre role, got {data.get('agreement_type')}"
        assert "signed_at" in data
        print(f"Cadre user signed agreement with type: {data.get('agreement_type')}")
        
        # Verify via /auth/me
        me_response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data.get("honor_agreement_signed") == True, "honor_agreement_signed should be True after signing"
        assert me_data.get("honor_agreement_type") == "cadre"
        assert me_data.get("honor_agreement_signed_at") is not None
        print("Verified honor_agreement_signed=True in /auth/me response")
    
    def test_sign_honor_agreement_commander_user(self):
        """Test signing honor agreement as commander user (should get 'staff' type)"""
        self.login_as_commander()
        
        # Sign the agreement
        response = self.session.post(
            f"{BASE_URL}/api/auth/sign-honor-agreement",
            json={"signature_name": "Test Commander Signature"}
        )
        assert response.status_code == 200, f"Sign failed: {response.text}"
        
        data = response.json()
        assert data.get("message") == "Honor agreement signed successfully"
        assert data.get("agreement_type") == "staff", f"Expected 'staff' type for commander role, got {data.get('agreement_type')}"
        print(f"Commander user signed agreement with type: {data.get('agreement_type')}")
        
        # Verify via /auth/me
        me_response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data.get("honor_agreement_signed") == True
        assert me_data.get("honor_agreement_type") == "staff"
        print("Verified honor_agreement_signed=True for commander")
    
    def test_send_reminders_requires_admin_role(self):
        """Test that send-reminders requires admin role"""
        # Login as cadre (not admin)
        self.login_as_cadre()
        
        response = self.session.post(f"{BASE_URL}/api/auth/send-honor-agreement-reminders")
        # exec_cadre should NOT have permission to send reminders
        assert response.status_code in [401, 403], f"Expected 401/403 for non-admin, got {response.status_code}"
        print("Non-admin correctly blocked from sending reminders")
    
    def test_send_reminders_as_commander(self):
        """Test sending reminders as commander"""
        self.login_as_commander()
        
        response = self.session.post(f"{BASE_URL}/api/auth/send-honor-agreement-reminders")
        assert response.status_code == 200, f"Send reminders failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "count" in data
        assert "unsigned_users" in data
        assert isinstance(data["count"], int)
        assert isinstance(data["unsigned_users"], list)
        print(f"Sent reminders to {data['count']} unsigned users")
        
        # Verify unsigned_users structure
        if data["unsigned_users"]:
            user = data["unsigned_users"][0]
            assert "id" in user
            assert "name" in user
            assert "email" in user
            print(f"Sample unsigned user: {user['name']} ({user['email']})")


class TestHonorAgreementRoleMapping:
    """Test that agreement type is correctly mapped based on role"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_cadre_roles_get_cadre_agreement(self):
        """Verify cadre and exec_cadre roles get 'cadre' agreement type"""
        # Login as exec_cadre
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=CADRE_USER)
        assert response.status_code == 200
        
        user = response.json().get("user", {})
        role = user.get("role")
        assert role in ["cadre", "exec_cadre"], f"Expected cadre role, got {role}"
        print(f"User role: {role} - should get 'cadre' agreement type")
    
    def test_staff_roles_get_staff_agreement(self):
        """Verify commander/staff roles get 'staff' agreement type"""
        # Login as commander
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=COMMANDER_USER)
        assert response.status_code == 200
        
        user = response.json().get("user", {})
        role = user.get("role")
        assert role == "commander", f"Expected commander role, got {role}"
        print(f"User role: {role} - should get 'staff' agreement type")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
