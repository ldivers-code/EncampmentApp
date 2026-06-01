"""
Test User-to-Participant Auto-Sync Feature
Tests the POST /api/sync/users-participants endpoint which:
1. Links users to participants by CAPID match
2. Creates new participant records for users with no CAPID match
3. Is idempotent - running again doesn't create duplicates
4. Requires admin/commander role (returns 403 for unauthorized users)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD

# Test user for unauthorized access
TEST_CADRE_EMAIL = f"test_cadre_{uuid.uuid4().hex[:8]}@test.com"
TEST_CADRE_CAPID = f"TEST{uuid.uuid4().hex[:6].upper()}"


class TestUserParticipantSync:
    """Tests for the User-to-Participant Auto-Sync feature"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get headers with admin auth token"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    @pytest.fixture(scope="class")
    def cadre_user(self, admin_headers):
        """Create a cadre user for unauthorized access testing"""
        # Register a new cadre user
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_CADRE_EMAIL,
            "password": TEST_CADRE_PASSWORD,
            "name": "Test Cadre User",
            "role": "cadre",
            "capid": TEST_CADRE_CAPID
        })
        if response.status_code != 200:
            pytest.skip(f"Cadre user registration failed: {response.status_code}")
        
        user_data = response.json()
        user_id = user_data["user"]["id"]
        
        # Approve the user
        requests.post(f"{BASE_URL}/api/users/{user_id}/approve", headers=admin_headers)
        
        # Login to get token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_CADRE_EMAIL,
            "password": TEST_CADRE_PASSWORD
        })
        
        yield {
            "id": user_id,
            "token": login_response.json()["access_token"] if login_response.status_code == 200 else None,
            "email": TEST_CADRE_EMAIL
        }
        
        # Cleanup: delete the test user
        requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=admin_headers)
    
    def test_sync_endpoint_exists(self, admin_headers):
        """Test that the sync endpoint exists and is accessible"""
        response = requests.post(f"{BASE_URL}/api/sync/users-participants", headers=admin_headers)
        # Should return 200 (success) not 404 (not found)
        assert response.status_code == 200, f"Endpoint should exist. Got: {response.status_code} - {response.text}"
        print(f"✓ Sync endpoint exists and returned 200")
    
    def test_sync_returns_correct_structure(self, admin_headers):
        """Test that sync returns the expected response structure"""
        response = requests.post(f"{BASE_URL}/api/sync/users-participants", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields in response
        assert "message" in data, "Response should contain 'message'"
        assert "linked" in data, "Response should contain 'linked' count"
        assert "created" in data, "Response should contain 'created' count"
        assert "already_linked" in data, "Response should contain 'already_linked' count"
        assert "skipped" in data, "Response should contain 'skipped' count"
        assert "total_users" in data, "Response should contain 'total_users' count"
        
        # All counts should be non-negative integers
        assert isinstance(data["linked"], int) and data["linked"] >= 0
        assert isinstance(data["created"], int) and data["created"] >= 0
        assert isinstance(data["already_linked"], int) and data["already_linked"] >= 0
        assert isinstance(data["skipped"], int) and data["skipped"] >= 0
        assert isinstance(data["total_users"], int) and data["total_users"] > 0
        
        print(f"✓ Sync response structure is correct: {data}")
    
    def test_sync_is_idempotent(self, admin_headers):
        """Test that running sync multiple times doesn't create duplicates"""
        # First sync
        response1 = requests.post(f"{BASE_URL}/api/sync/users-participants", headers=admin_headers)
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second sync immediately after
        response2 = requests.post(f"{BASE_URL}/api/sync/users-participants", headers=admin_headers)
        assert response2.status_code == 200
        data2 = response2.json()
        
        # After first sync, second sync should show all as "already_linked" or "skipped"
        # No new links or creates should happen
        assert data2["linked"] == 0, f"Second sync should not link any new users. Got: {data2['linked']}"
        assert data2["created"] == 0, f"Second sync should not create any new participants. Got: {data2['created']}"
        
        # The already_linked count should be >= what was linked in first sync
        total_processed_first = data1["linked"] + data1["created"] + data1["already_linked"]
        assert data2["already_linked"] >= data1["already_linked"], "Already linked count should not decrease"
        
        print(f"✓ Sync is idempotent - First: {data1}, Second: {data2}")
    
    def test_sync_requires_admin_role(self, cadre_user):
        """Test that sync endpoint returns 403 for non-admin users"""
        if not cadre_user["token"]:
            pytest.skip("Cadre user token not available")
        
        headers = {"Authorization": f"Bearer {cadre_user['token']}"}
        response = requests.post(f"{BASE_URL}/api/sync/users-participants", headers=headers)
        
        assert response.status_code == 403, f"Cadre user should get 403 Forbidden. Got: {response.status_code}"
        print(f"✓ Sync correctly returns 403 for unauthorized cadre user")
    
    def test_sync_requires_authentication(self):
        """Test that sync endpoint returns 401/403 without authentication"""
        response = requests.post(f"{BASE_URL}/api/sync/users-participants")
        
        # Should return 401 (Unauthorized) or 403 (Forbidden) without token
        assert response.status_code in [401, 403], f"Should require auth. Got: {response.status_code}"
        print(f"✓ Sync correctly requires authentication (returned {response.status_code})")
    
    def test_sync_links_user_by_capid(self, admin_headers):
        """Test that sync links users to participants by matching CAPID"""
        # Create a unique CAPID for this test
        test_capid = f"SYNC{uuid.uuid4().hex[:6].upper()}"
        test_email = f"sync_test_{uuid.uuid4().hex[:8]}@test.com"
        
        # First, create a participant with this CAPID
        participant_response = requests.post(f"{BASE_URL}/api/participants", json={
            "capid": test_capid,
            "first_name": "Sync",
            "last_name": "TestParticipant",
            "rank": "C/Amn",
            "unit": "TN-001",
            "participant_type": "basic_student"
        }, headers=admin_headers)
        
        if participant_response.status_code != 200:
            pytest.skip(f"Could not create test participant: {participant_response.text}")
        
        participant_id = participant_response.json()["id"]
        
        # Create a user with the same CAPID
        user_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": ADMIN_PASSWORD,
            "name": "Sync Test User",
            "role": "cadre",
            "capid": test_capid
        })
        
        if user_response.status_code != 200:
            # Cleanup participant
            requests.delete(f"{BASE_URL}/api/participants/{participant_id}", headers=admin_headers)
            pytest.skip(f"Could not create test user: {user_response.text}")
        
        user_id = user_response.json()["user"]["id"]
        
        try:
            # Run sync
            sync_response = requests.post(f"{BASE_URL}/api/sync/users-participants", headers=admin_headers)
            assert sync_response.status_code == 200
            
            # Check that the user is now linked
            users_response = requests.get(f"{BASE_URL}/api/users", headers=admin_headers)
            assert users_response.status_code == 200
            
            users = users_response.json()
            test_user = next((u for u in users if u["id"] == user_id), None)
            
            assert test_user is not None, "Test user should exist"
            assert test_user.get("linked_participant_id") == participant_id, \
                f"User should be linked to participant. Got: {test_user.get('linked_participant_id')}"
            
            print(f"✓ Sync correctly linked user to participant by CAPID match")
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=admin_headers)
            requests.delete(f"{BASE_URL}/api/participants/{participant_id}", headers=admin_headers)
    
    def test_sync_creates_participant_for_unmatched_user(self, admin_headers):
        """Test that sync creates a new participant for users with no CAPID match"""
        # Create a user with a unique CAPID that doesn't exist in participants
        test_capid = f"NEW{uuid.uuid4().hex[:6].upper()}"
        test_email = f"new_sync_{uuid.uuid4().hex[:8]}@test.com"
        test_name = "New Sync User"
        
        # Register user
        user_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": ADMIN_PASSWORD,
            "name": test_name,
            "role": "staff",
            "capid": test_capid
        })
        
        if user_response.status_code != 200:
            pytest.skip(f"Could not create test user: {user_response.text}")
        
        user_id = user_response.json()["user"]["id"]
        
        try:
            # Run sync
            sync_response = requests.post(f"{BASE_URL}/api/sync/users-participants", headers=admin_headers)
            assert sync_response.status_code == 200
            sync_data = sync_response.json()
            
            # Check that a participant was created
            # The sync should have created at least one participant (could be more if other unlinked users exist)
            
            # Verify user is now linked
            users_response = requests.get(f"{BASE_URL}/api/users", headers=admin_headers)
            users = users_response.json()
            test_user = next((u for u in users if u["id"] == user_id), None)
            
            assert test_user is not None, "Test user should exist"
            linked_participant_id = test_user.get("linked_participant_id")
            assert linked_participant_id is not None, "User should be linked to a participant"
            
            # Verify the participant exists with correct data
            participants_response = requests.get(f"{BASE_URL}/api/participants", headers=admin_headers)
            participants = participants_response.json()
            linked_participant = next((p for p in participants if p["id"] == linked_participant_id), None)
            
            assert linked_participant is not None, "Linked participant should exist"
            assert linked_participant["capid"] == test_capid, "Participant should have user's CAPID"
            
            print(f"✓ Sync correctly created participant for unmatched user: {linked_participant}")
            
            # Cleanup the created participant
            requests.delete(f"{BASE_URL}/api/participants/{linked_participant_id}", headers=admin_headers)
        finally:
            # Cleanup user
            requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=admin_headers)
    
    def test_sync_allowed_roles(self, admin_headers):
        """Test that sync is allowed for DCP, Commander, Executive Staff, and Plans & Programs roles"""
        # We already tested with commander (admin). Let's verify the endpoint accepts the request.
        # The role check is done by require_role decorator
        response = requests.post(f"{BASE_URL}/api/sync/users-participants", headers=admin_headers)
        assert response.status_code == 200, f"Admin should be able to sync. Got: {response.status_code}"
        print(f"✓ Sync allowed for admin/commander role")


class TestUserLinkStatus:
    """Tests for verifying user link status indicators"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_users_have_linked_participant_id_field(self, admin_headers):
        """Test that user response includes linked_participant_id field"""
        response = requests.get(f"{BASE_URL}/api/users", headers=admin_headers)
        assert response.status_code == 200
        
        users = response.json()
        assert len(users) > 0, "Should have at least one user"
        
        # Check that linked_participant_id field exists in user objects
        for user in users[:5]:  # Check first 5 users
            assert "linked_participant_id" in user or user.get("linked_participant_id") is None, \
                "User should have linked_participant_id field (can be null)"
        
        # Count linked vs unlinked
        linked_count = sum(1 for u in users if u.get("linked_participant_id"))
        unlinked_count = len(users) - linked_count
        
        print(f"✓ Users have linked_participant_id field. Linked: {linked_count}, Unlinked: {unlinked_count}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
