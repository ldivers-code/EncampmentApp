"""
Profile Change Password Feature Tests
Tests for POST /api/profile/change-password endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user credentials (as provided by main agent)
TEST_USER = {
    "email": "testuser@cap.us",
    "password": "resetpassword123",
    "capid": "123456"
}


class TestProfileChangePassword:
    """Tests for POST /api/profile/change-password endpoint"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER["email"], "password": TEST_USER["password"]}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Could not authenticate test user: {response.status_code}")
    
    @pytest.fixture
    def auth_headers(self, auth_token):
        """Headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_change_password_requires_auth(self):
        """Test that change password endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/profile/change-password",
            json={
                "current_password": "whatever",
                "new_password": "newpass123"
            }
        )
        assert response.status_code == 403
        print("Auth required: PASS")
    
    def test_change_password_wrong_current_password(self, auth_headers):
        """Test that wrong current password returns error"""
        response = requests.post(
            f"{BASE_URL}/api/profile/change-password",
            json={
                "current_password": "wrongpassword",
                "new_password": "newpass123"
            },
            headers=auth_headers
        )
        assert response.status_code == 400
        data = response.json()
        assert "incorrect" in data["detail"].lower()
        print(f"Wrong password response: {data}")
    
    def test_change_password_too_short_new_password(self, auth_headers):
        """Test that new password must be at least 6 characters"""
        response = requests.post(
            f"{BASE_URL}/api/profile/change-password",
            json={
                "current_password": TEST_USER["password"],
                "new_password": "12345"  # Only 5 chars
            },
            headers=auth_headers
        )
        assert response.status_code == 400
        data = response.json()
        assert "6 characters" in data["detail"]
        print(f"Short password response: {data}")
    
    def test_change_password_success(self, auth_headers):
        """Test successful password change"""
        new_password = "changedpass123"
        
        # Step 1: Change password
        response = requests.post(
            f"{BASE_URL}/api/profile/change-password",
            json={
                "current_password": TEST_USER["password"],
                "new_password": new_password
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "successfully" in data["message"].lower()
        print(f"Password change response: {data}")
        
        # Step 2: Verify can login with new password
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER["email"], "password": new_password}
        )
        assert login_response.status_code == 200
        print("Login with new password: SUCCESS")
        
        # Cleanup: Change password back
        new_token = login_response.json().get("access_token")
        cleanup_response = requests.post(
            f"{BASE_URL}/api/profile/change-password",
            json={
                "current_password": new_password,
                "new_password": TEST_USER["password"]
            },
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert cleanup_response.status_code == 200
        print("Cleanup (reset to original): SUCCESS")
    
    def test_change_password_old_password_invalidated(self, auth_headers):
        """Test that old password no longer works after change"""
        new_password = "tempchange123"
        
        # Change password
        response = requests.post(
            f"{BASE_URL}/api/profile/change-password",
            json={
                "current_password": TEST_USER["password"],
                "new_password": new_password
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Try to login with old password - should fail
        old_login = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER["email"], "password": TEST_USER["password"]}
        )
        assert old_login.status_code == 401
        print("Old password invalidated: SUCCESS")
        
        # Cleanup: Login with new password and reset
        new_login = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER["email"], "password": new_password}
        )
        new_token = new_login.json().get("access_token")
        requests.post(
            f"{BASE_URL}/api/profile/change-password",
            json={
                "current_password": new_password,
                "new_password": TEST_USER["password"]
            },
            headers={"Authorization": f"Bearer {new_token}"}
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
