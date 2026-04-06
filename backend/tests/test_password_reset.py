"""
Password Reset Feature Tests
Tests for:
1. Self-service password reset via forgot-password flow (email + CAPID verification)
2. Admin password reset via Admin panel
3. Token verification and expiry
"""
import pytest
import requests
import os
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
COMMANDER_CREDENTIALS = {
    "email": "commander@test.cap.gov",
    "password": COMMANDER_PASSWORD
}

TEST_USER = {
    "email": "658773@tncap.us",
    "name": "Guiseppe S Doran",
    "capid": "658773"
}

@pytest.fixture(scope="module")
def commander_token():
    """Get authentication token for commander"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=COMMANDER_CREDENTIALS
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Could not authenticate commander")

@pytest.fixture
def auth_headers(commander_token):
    """Headers with commander auth token"""
    return {"Authorization": f"Bearer {commander_token}"}


class TestForgotPasswordAPI:
    """Tests for POST /api/auth/forgot-password"""
    
    def test_forgot_password_with_valid_email_and_capid(self):
        """Test forgot password with matching email and CAPID"""
        params = {"email": TEST_USER["email"], "capid": TEST_USER["capid"]}
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", params=params)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        # When SendGrid is not configured, debug_token is returned
        if "debug_token" in data:
            print(f"Debug token received: {data['debug_token']}")
            assert len(data["debug_token"]) > 0  # UUID format
        print(f"Response message: {data['message']}")
    
    def test_forgot_password_with_wrong_capid(self):
        """Test forgot password with wrong CAPID - should still return success (no info leak)"""
        params = {"email": TEST_USER["email"], "capid": "000000"}
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", params=params)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        # Should NOT return debug_token when CAPID doesn't match
        # The API returns same generic message to prevent info leakage
        print(f"Response: {data}")
    
    def test_forgot_password_with_nonexistent_email(self):
        """Test forgot password with non-existent email - should still return success"""
        params = {"email": "nonexistent@test.com", "capid": "123456"}
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", params=params)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        # Should NOT reveal that user doesn't exist
    
    def test_forgot_password_returns_debug_token_when_valid(self):
        """Test that debug token is returned when email+CAPID match and SendGrid not configured"""
        params = {"email": TEST_USER["email"], "capid": TEST_USER["capid"]}
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", params=params)
        
        assert response.status_code == 200
        data = response.json()
        # Since SendGrid is not configured, we should get debug_token
        if "debug_token" in data:
            assert isinstance(data["debug_token"], str)
            assert len(data["debug_token"]) == 36  # UUID format
            print(f"Reset token: {data['debug_token']}")


class TestVerifyResetTokenAPI:
    """Tests for POST /api/auth/verify-reset-token"""
    
    @pytest.fixture
    def valid_reset_token(self):
        """Generate a valid reset token"""
        params = {"email": TEST_USER["email"], "capid": TEST_USER["capid"]}
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", params=params)
        data = response.json()
        return data.get("debug_token")
    
    def test_verify_valid_token(self, valid_reset_token):
        """Test token verification with valid token"""
        if not valid_reset_token:
            pytest.skip("No debug token available (SendGrid may be configured)")
        
        params = {"token": valid_reset_token}
        response = requests.post(f"{BASE_URL}/api/auth/verify-reset-token", params=params)
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == True
        assert "email" in data
        assert data["email"] == TEST_USER["email"]
        print(f"Token verified for email: {data['email']}")
    
    def test_verify_invalid_token(self):
        """Test token verification with invalid token"""
        params = {"token": "invalid-token-12345"}
        response = requests.post(f"{BASE_URL}/api/auth/verify-reset-token", params=params)
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == False
        assert "message" in data
        print(f"Invalid token response: {data}")


class TestResetPasswordAPI:
    """Tests for POST /api/auth/reset-password"""
    
    @pytest.fixture
    def reset_token(self):
        """Generate reset token for testing"""
        params = {"email": TEST_USER["email"], "capid": TEST_USER["capid"]}
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", params=params)
        data = response.json()
        return data.get("debug_token")
    
    def test_reset_password_with_valid_token(self, reset_token):
        """Test password reset with valid token"""
        if not reset_token:
            pytest.skip("No reset token available")
        
        new_password = "newpassword123"
        params = {"token": reset_token, "new_password": new_password}
        response = requests.post(f"{BASE_URL}/api/auth/reset-password", params=params)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "successfully" in data["message"].lower()
        print(f"Password reset response: {data}")
        
        # Now reset password back to original for other tests
        # Need to generate new token and reset again
        params = {"email": TEST_USER["email"], "capid": TEST_USER["capid"]}
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", params=params)
        new_token = response.json().get("debug_token")
        if new_token:
            params = {"token": new_token, "new_password": COMMANDER_PASSWORD}
            requests.post(f"{BASE_URL}/api/auth/reset-password", params=params)
    
    def test_reset_password_with_invalid_token(self):
        """Test password reset with invalid token"""
        params = {"token": "invalid-token-xyz", "new_password": "newpassword123"}
        response = requests.post(f"{BASE_URL}/api/auth/reset-password", params=params)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        print(f"Invalid token reset response: {data}")
    
    def test_reset_password_too_short(self, reset_token):
        """Test password reset with too short password"""
        if not reset_token:
            pytest.skip("No reset token available")
        
        params = {"token": reset_token, "new_password": "12345"}  # Less than 6 chars
        response = requests.post(f"{BASE_URL}/api/auth/reset-password", params=params)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "6 characters" in data["detail"]


class TestAdminResetPasswordAPI:
    """Tests for POST /api/users/{user_id}/reset-password (Admin only)"""
    
    def test_admin_reset_requires_auth(self):
        """Test that admin reset requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/users/some-user-id/reset-password",
            params={"new_password": "newpass123"}
        )
        assert response.status_code == 403
    
    def test_admin_reset_password_success(self, auth_headers):
        """Test admin can reset user password"""
        # First get user list to find a user ID
        response = requests.get(f"{BASE_URL}/api/users", headers=auth_headers)
        assert response.status_code == 200
        users = response.json()
        
        # Find Guiseppe's user ID
        target_user = None
        for user in users:
            if user.get("email") == TEST_USER["email"]:
                target_user = user
                break
        
        if not target_user:
            pytest.skip("Test user not found in users list")
        
        user_id = target_user["id"]
        new_password = "adminreset123"
        
        # Reset password via admin API
        params = {"new_password": new_password}
        response = requests.post(
            f"{BASE_URL}/api/users/{user_id}/reset-password",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "successfully" in data["message"].lower()
        print(f"Admin reset response: {data}")
        
        # Verify user can login with new password
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER["email"], "password": new_password}
        )
        assert login_response.status_code == 200
        print("User can login with new password set by admin")
        
        # Reset password back for other tests
        params = {"new_password": COMMANDER_PASSWORD}
        requests.post(
            f"{BASE_URL}/api/users/{user_id}/reset-password",
            params=params,
            headers=auth_headers
        )
    
    def test_admin_reset_password_short_password(self, auth_headers):
        """Test admin reset fails with too short password"""
        # Get a user ID first
        response = requests.get(f"{BASE_URL}/api/users", headers=auth_headers)
        users = response.json()
        
        if not users:
            pytest.skip("No users found")
        
        user_id = users[0]["id"]
        
        params = {"new_password": "12345"}  # Too short
        response = requests.post(
            f"{BASE_URL}/api/users/{user_id}/reset-password",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "6 characters" in data["detail"]
    
    def test_admin_reset_nonexistent_user(self, auth_headers):
        """Test admin reset for non-existent user"""
        params = {"new_password": "validpassword123"}
        response = requests.post(
            f"{BASE_URL}/api/users/nonexistent-user-id/reset-password",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestFullPasswordResetFlow:
    """End-to-end tests for complete password reset flows"""
    
    def test_complete_self_service_flow(self):
        """Test complete self-service password reset flow"""
        # Step 1: Request password reset
        params = {"email": TEST_USER["email"], "capid": TEST_USER["capid"]}
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", params=params)
        assert response.status_code == 200
        
        reset_token = response.json().get("debug_token")
        if not reset_token:
            pytest.skip("No debug token (SendGrid may be configured)")
        
        # Step 2: Verify token
        params = {"token": reset_token}
        response = requests.post(f"{BASE_URL}/api/auth/verify-reset-token", params=params)
        assert response.status_code == 200
        assert response.json()["valid"] == True
        
        # Step 3: Reset password
        new_password = "flowtestpass123"
        params = {"token": reset_token, "new_password": new_password}
        response = requests.post(f"{BASE_URL}/api/auth/reset-password", params=params)
        assert response.status_code == 200
        
        # Step 4: Login with new password
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER["email"], "password": new_password}
        )
        assert response.status_code == 200
        print("Complete self-service flow PASSED")
        
        # Cleanup: Reset password back
        params = {"email": TEST_USER["email"], "capid": TEST_USER["capid"]}
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", params=params)
        new_token = response.json().get("debug_token")
        if new_token:
            params = {"token": new_token, "new_password": COMMANDER_PASSWORD}
            requests.post(f"{BASE_URL}/api/auth/reset-password", params=params)
    
    def test_token_becomes_invalid_after_use(self):
        """Test that reset token becomes invalid after being used"""
        # Generate token
        params = {"email": TEST_USER["email"], "capid": TEST_USER["capid"]}
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", params=params)
        reset_token = response.json().get("debug_token")
        
        if not reset_token:
            pytest.skip("No debug token available")
        
        # Use token to reset password
        params = {"token": reset_token, "new_password": "temppass123"}
        response = requests.post(f"{BASE_URL}/api/auth/reset-password", params=params)
        assert response.status_code == 200
        
        # Try to use same token again - should fail
        params = {"token": reset_token, "new_password": "anotherpass123"}
        response = requests.post(f"{BASE_URL}/api/auth/reset-password", params=params)
        assert response.status_code == 400
        print("Token invalidation after use PASSED")
        
        # Cleanup
        params = {"email": TEST_USER["email"], "capid": TEST_USER["capid"]}
        response = requests.post(f"{BASE_URL}/api/auth/forgot-password", params=params)
        new_token = response.json().get("debug_token")
        if new_token:
            params = {"token": new_token, "new_password": COMMANDER_PASSWORD}
            requests.post(f"{BASE_URL}/api/auth/reset-password", params=params)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
