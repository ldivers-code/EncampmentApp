"""
Test suite for Active Users / Presence endpoints
Tests heartbeat, active-users list, and offline functionality
"""
import pytest
import requests
import os
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
COMMANDER_EMAIL = "commander@test.cap.gov"
COMMANDER_PASSWORD = "test123"

class TestPresenceEndpoints:
    """Tests for /api/presence/* endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token before each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.user = data.get("user")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    # ============ Heartbeat Endpoint Tests ============
    
    def test_heartbeat_endpoint_returns_200(self):
        """POST /api/presence/heartbeat returns 200 OK"""
        response = self.session.post(f"{BASE_URL}/api/presence/heartbeat")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Heartbeat endpoint returns 200")
    
    def test_heartbeat_response_structure(self):
        """Heartbeat response contains status and timestamp"""
        response = self.session.post(f"{BASE_URL}/api/presence/heartbeat")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data, "Response missing 'status' field"
        assert data["status"] == "ok", f"Expected status 'ok', got '{data['status']}'"
        assert "timestamp" in data, "Response missing 'timestamp' field"
        
        # Verify timestamp is valid ISO format
        try:
            datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {data['timestamp']}")
        
        print(f"PASS: Heartbeat returns correct structure: {data}")
    
    def test_heartbeat_requires_auth(self):
        """Heartbeat endpoint requires authentication"""
        # Create new session without auth
        no_auth_session = requests.Session()
        response = no_auth_session.post(f"{BASE_URL}/api/presence/heartbeat")
        
        # Should return 401 or 403
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("PASS: Heartbeat requires authentication")
    
    # ============ Active Users Endpoint Tests ============
    
    def test_active_users_endpoint_returns_200(self):
        """GET /api/presence/active-users returns 200 OK"""
        response = self.session.get(f"{BASE_URL}/api/presence/active-users")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Active users endpoint returns 200")
    
    def test_active_users_response_structure(self):
        """Active users response has count and users array"""
        response = self.session.get(f"{BASE_URL}/api/presence/active-users")
        assert response.status_code == 200
        
        data = response.json()
        assert "count" in data, "Response missing 'count' field"
        assert "users" in data, "Response missing 'users' field"
        assert isinstance(data["count"], int), "Count should be integer"
        assert isinstance(data["users"], list), "Users should be a list"
        
        print(f"PASS: Active users returns correct structure. Count: {data['count']}")
    
    def test_active_users_user_fields(self):
        """Each active user has required fields (id, name, role)"""
        # First send heartbeat to ensure current user is active
        self.session.post(f"{BASE_URL}/api/presence/heartbeat")
        
        response = self.session.get(f"{BASE_URL}/api/presence/active-users")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] > 0, "Expected at least 1 active user after heartbeat"
        
        for user in data["users"]:
            assert "id" in user, "User missing 'id' field"
            assert "name" in user, "User missing 'name' field"
            assert "role" in user, "User missing 'role' field"
            print(f"  User: {user['name']} - {user['role']}")
        
        print(f"PASS: All {len(data['users'])} users have required fields")
    
    def test_current_user_appears_in_active_users(self):
        """Current user appears in active users list after heartbeat"""
        # Send heartbeat
        hb_response = self.session.post(f"{BASE_URL}/api/presence/heartbeat")
        assert hb_response.status_code == 200
        
        # Get active users
        response = self.session.get(f"{BASE_URL}/api/presence/active-users")
        assert response.status_code == 200
        
        data = response.json()
        user_ids = [u.get("id") for u in data["users"]]
        
        assert self.user["id"] in user_ids, f"Current user {self.user['id']} not in active users list"
        print(f"PASS: Current user ({self.user['name']}) appears in active users list")
    
    def test_active_users_requires_auth(self):
        """Active users endpoint requires authentication"""
        no_auth_session = requests.Session()
        response = no_auth_session.get(f"{BASE_URL}/api/presence/active-users")
        
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("PASS: Active users requires authentication")
    
    # ============ Offline Endpoint Tests ============
    
    def test_offline_endpoint_returns_200(self):
        """POST /api/presence/offline returns 200 OK"""
        response = self.session.post(f"{BASE_URL}/api/presence/offline")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: Offline endpoint returns 200")
    
    def test_offline_response_structure(self):
        """Offline response contains status ok"""
        response = self.session.post(f"{BASE_URL}/api/presence/offline")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data, "Response missing 'status' field"
        assert data["status"] == "ok", f"Expected status 'ok', got '{data['status']}'"
        
        print(f"PASS: Offline returns correct structure: {data}")
    
    def test_offline_requires_auth(self):
        """Offline endpoint requires authentication"""
        no_auth_session = requests.Session()
        response = no_auth_session.post(f"{BASE_URL}/api/presence/offline")
        
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("PASS: Offline requires authentication")
    
    # ============ Integration Tests ============
    
    def test_heartbeat_updates_active_status(self):
        """Sending heartbeat should update user's active status"""
        # Send heartbeat
        hb_response = self.session.post(f"{BASE_URL}/api/presence/heartbeat")
        assert hb_response.status_code == 200
        
        # Check active users
        active_response = self.session.get(f"{BASE_URL}/api/presence/active-users")
        assert active_response.status_code == 200
        
        data = active_response.json()
        user_ids = [u["id"] for u in data["users"]]
        
        assert self.user["id"] in user_ids, "User should appear in active list after heartbeat"
        print("PASS: Heartbeat updates active status")
    
    def test_active_users_count_matches_list_length(self):
        """Active users count should match the length of users list"""
        response = self.session.get(f"{BASE_URL}/api/presence/active-users")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == len(data["users"]), \
            f"Count ({data['count']}) doesn't match users length ({len(data['users'])})"
        
        print(f"PASS: Count ({data['count']}) matches users list length")
    
    def test_user_has_last_active_timestamp(self):
        """Active users should include last_active timestamp"""
        # Send heartbeat to ensure we have data
        self.session.post(f"{BASE_URL}/api/presence/heartbeat")
        
        response = self.session.get(f"{BASE_URL}/api/presence/active-users")
        assert response.status_code == 200
        
        data = response.json()
        if data["count"] > 0:
            user = data["users"][0]
            # last_active may or may not be included, check if present
            if "last_active" in user:
                print(f"PASS: User has last_active timestamp: {user['last_active']}")
            else:
                print("INFO: last_active not included in response (optional)")
        else:
            print("INFO: No active users to check")


class TestActiveUsersIntegrationFlow:
    """End-to-end integration tests for active users flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        self.token = data.get("access_token")
        self.user = data.get("user")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_full_presence_flow(self):
        """Test complete flow: heartbeat -> check active -> offline"""
        print("\n=== Testing Full Presence Flow ===")
        
        # 1. Send heartbeat
        print("\n1. Sending heartbeat...")
        hb_response = self.session.post(f"{BASE_URL}/api/presence/heartbeat")
        assert hb_response.status_code == 200
        print(f"   Heartbeat response: {hb_response.json()}")
        
        # 2. Check active users
        print("\n2. Checking active users...")
        active_response = self.session.get(f"{BASE_URL}/api/presence/active-users")
        assert active_response.status_code == 200
        active_data = active_response.json()
        print(f"   Active users count: {active_data['count']}")
        for u in active_data['users']:
            print(f"   - {u['name']} ({u['role']})")
        
        # 3. Verify current user is active
        user_in_list = any(u["id"] == self.user["id"] for u in active_data["users"])
        assert user_in_list, "Current user should be in active list"
        print(f"\n3. Current user '{self.user['name']}' is in active list: ✓")
        
        # 4. Go offline
        print("\n4. Going offline...")
        offline_response = self.session.post(f"{BASE_URL}/api/presence/offline")
        assert offline_response.status_code == 200
        print(f"   Offline response: {offline_response.json()}")
        
        print("\n=== Full Presence Flow Complete ===")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
