"""
Test suite for Member Profiles and User Approval features.
Tests:
- Profile endpoints (GET/PUT /api/profile, POST /api/profile/photo)
- User approval workflow (GET /api/users/pending, POST /api/users/{id}/approve)
- Link participant to user (POST /api/users/{id}/link-participant)
- Find matching participants (GET /api/users/{id}/match-participants)
- Registration with role selection
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cadre-hub.preview.emergentagent.com')

# Test credentials
COMMANDER_EMAIL = "ldivers@cap.gov"
COMMANDER_PASSWORD = "Password123!"
TEST_EMAIL_PREFIX = f"testuser_{uuid.uuid4().hex[:8]}"


class TestAuthentication:
    """Basic authentication tests"""
    
    def test_login_commander(self):
        """Test commander login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "commander"
        print(f"✓ Commander login successful: {data['user']['name']}")


class TestProfileEndpoints:
    """Profile CRUD operations"""
    
    @pytest.fixture
    def auth_token(self):
        """Get commander auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Login failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_get_profile(self, auth_headers):
        """Test GET /api/profile returns user profile"""
        response = requests.get(f"{BASE_URL}/api/profile", headers=auth_headers)
        assert response.status_code == 200, f"Get profile failed: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "id" in data
        assert "email" in data
        assert "name" in data
        assert "role" in data
        assert data["email"] == COMMANDER_EMAIL
        print(f"✓ Profile retrieved: {data['name']} ({data['role']})")
    
    def test_update_profile_basic_info(self, auth_headers):
        """Test PUT /api/profile updates basic info"""
        # Get current profile
        orig = requests.get(f"{BASE_URL}/api/profile", headers=auth_headers).json()
        
        # Update profile
        update_data = {
            "phone": "(555) 123-4567",
            "cell_phone": "(555) 987-6543"
        }
        response = requests.put(f"{BASE_URL}/api/profile", json=update_data, headers=auth_headers)
        assert response.status_code == 200, f"Update profile failed: {response.text}"
        
        data = response.json()
        assert data["phone"] == "(555) 123-4567"
        assert data["cell_phone"] == "(555) 987-6543"
        print("✓ Profile basic info updated successfully")
    
    def test_update_profile_cap_info(self, auth_headers):
        """Test PUT /api/profile updates CAP info (CAPID, rank, unit, wing, region)"""
        update_data = {
            "rank": "Col",
            "unit": "TN-001",
            "wing": "TN",
            "region": "SER"
        }
        response = requests.put(f"{BASE_URL}/api/profile", json=update_data, headers=auth_headers)
        assert response.status_code == 200, f"Update CAP info failed: {response.text}"
        
        data = response.json()
        assert data["rank"] == "Col"
        assert data["unit"] == "TN-001"
        assert data["wing"] == "TN"
        assert data["region"] == "SER"
        print("✓ Profile CAP info updated successfully")
    
    def test_update_profile_address(self, auth_headers):
        """Test PUT /api/profile updates address"""
        update_data = {
            "address": "123 Main Street",
            "city": "Nashville",
            "state": "TN",
            "zip_code": "37201"
        }
        response = requests.put(f"{BASE_URL}/api/profile", json=update_data, headers=auth_headers)
        assert response.status_code == 200, f"Update address failed: {response.text}"
        
        data = response.json()
        assert data["address"] == "123 Main Street"
        assert data["city"] == "Nashville"
        assert data["state"] == "TN"
        assert data["zip_code"] == "37201"
        print("✓ Profile address updated successfully")
    
    def test_update_profile_emergency_contact(self, auth_headers):
        """Test PUT /api/profile updates emergency contact"""
        update_data = {
            "emergency_contact": "Jane Doe",
            "emergency_phone": "(555) 111-2222"
        }
        response = requests.put(f"{BASE_URL}/api/profile", json=update_data, headers=auth_headers)
        assert response.status_code == 200, f"Update emergency contact failed: {response.text}"
        
        data = response.json()
        assert data["emergency_contact"] == "Jane Doe"
        assert data["emergency_phone"] == "(555) 111-2222"
        print("✓ Profile emergency contact updated successfully")
    
    def test_profile_cannot_change_role(self, auth_headers):
        """Test that users cannot change their own role via profile update"""
        # Try to change role to something else
        update_data = {"role": "cadet"}
        response = requests.put(f"{BASE_URL}/api/profile", json=update_data, headers=auth_headers)
        
        # Get profile and verify role unchanged
        profile = requests.get(f"{BASE_URL}/api/profile", headers=auth_headers).json()
        assert profile["role"] == "commander", "Role should not change via profile update"
        print("✓ Profile correctly prevents role change")


class TestRegistrationWithRole:
    """Test new user registration with role selection"""
    
    def test_register_staff_role(self):
        """Test registration with staff role selection"""
        test_email = f"{TEST_EMAIL_PREFIX}_staff@test.cap.gov"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "Test123!",
            "name": "Test Staff User",
            "role": "staff",
            "capid": "999001"
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        
        data = response.json()
        assert data["user"]["role"] == "staff"
        assert data["user"]["is_approved"] == False, "New users should not be auto-approved"
        print(f"✓ Staff registration successful, user ID: {data['user']['id']}")
        return data["user"]["id"]
    
    def test_register_cadet_role(self):
        """Test registration with cadet role selection"""
        test_email = f"{TEST_EMAIL_PREFIX}_cadet@test.cap.gov"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "Test123!",
            "name": "Test Cadet User",
            "role": "cadet",
            "capid": "999002"
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        
        data = response.json()
        assert data["user"]["role"] == "cadet"
        assert data["user"]["is_approved"] == False, "New users should not be auto-approved"
        print(f"✓ Cadet registration successful, user ID: {data['user']['id']}")
        return data["user"]["id"]
    
    def test_register_invalid_role_defaults_to_staff(self):
        """Test registration with invalid role defaults to staff"""
        test_email = f"{TEST_EMAIL_PREFIX}_invalid@test.cap.gov"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "Test123!",
            "name": "Test Invalid Role",
            "role": "commander",  # Should not be allowed
            "capid": "999003"
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        
        data = response.json()
        # Should default to staff since commander role is not allowed during registration
        assert data["user"]["role"] == "staff", "Invalid role should default to staff"
        print("✓ Invalid role correctly defaulted to staff")


class TestUserApproval:
    """Test user approval workflow"""
    
    @pytest.fixture
    def commander_headers(self):
        """Get commander auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Commander login failed")
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    @pytest.fixture
    def pending_user_id(self, commander_headers):
        """Create a pending user for testing"""
        test_email = f"{TEST_EMAIL_PREFIX}_pending@test.cap.gov"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "Test123!",
            "name": "Test Pending User",
            "role": "staff",
            "capid": "999004"
        })
        if response.status_code != 200:
            # User might already exist, try to find them
            users = requests.get(f"{BASE_URL}/api/users/pending", headers=commander_headers)
            if users.status_code == 200:
                for u in users.json():
                    if "pending" in u.get("email", "").lower():
                        return u["id"]
            pytest.skip("Could not create test user")
        return response.json()["user"]["id"]
    
    def test_get_pending_users(self, commander_headers):
        """Test GET /api/users/pending returns pending users"""
        response = requests.get(f"{BASE_URL}/api/users/pending", headers=commander_headers)
        assert response.status_code == 200, f"Get pending users failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Found {len(data)} pending users")
    
    def test_approve_user(self, commander_headers, pending_user_id):
        """Test POST /api/users/{id}/approve approves user"""
        response = requests.post(f"{BASE_URL}/api/users/{pending_user_id}/approve", headers=commander_headers)
        assert response.status_code == 200, f"Approve user failed: {response.text}"
        
        data = response.json()
        assert data["user"]["is_approved"] == True
        assert data["user"]["approved_by"] is not None
        assert data["user"]["approved_at"] is not None
        print(f"✓ User approved successfully: {data['user']['name']}")
    
    def test_approve_nonexistent_user(self, commander_headers):
        """Test approving non-existent user returns 404"""
        response = requests.post(f"{BASE_URL}/api/users/nonexistent-id/approve", headers=commander_headers)
        assert response.status_code == 404
        print("✓ Non-existent user approval correctly returns 404")
    
    def test_pending_users_requires_commander(self):
        """Test GET /api/users/pending requires commander role"""
        # Create a regular staff user
        test_email = f"{TEST_EMAIL_PREFIX}_nonadmin@test.cap.gov"
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "Test123!",
            "name": "Non-Admin User",
            "role": "staff"
        })
        
        if reg_response.status_code == 200:
            token = reg_response.json()["access_token"]
            response = requests.get(f"{BASE_URL}/api/users/pending", 
                                  headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 403, "Non-commander should get 403"
            print("✓ Pending users endpoint correctly requires commander role")
        else:
            print("⚠ Could not test role restriction (user may already exist)")


class TestMatchParticipants:
    """Test finding and linking participants to users"""
    
    @pytest.fixture
    def commander_headers(self):
        """Get commander auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Commander login failed")
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    @pytest.fixture
    def test_user_id(self, commander_headers):
        """Create a test user for matching"""
        test_email = f"{TEST_EMAIL_PREFIX}_match@test.cap.gov"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "Test123!",
            "name": "Test Match User",
            "role": "staff",
            "capid": "434653"  # Use a real CAPID that exists in roster
        })
        if response.status_code == 200:
            return response.json()["user"]["id"]
        else:
            # Get all users and find one
            users = requests.get(f"{BASE_URL}/api/users", headers=commander_headers)
            if users.status_code == 200 and len(users.json()) > 0:
                return users.json()[0]["id"]
            pytest.skip("Could not get test user")
    
    def test_find_matching_participants(self, commander_headers, test_user_id):
        """Test GET /api/users/{id}/match-participants finds matches"""
        response = requests.get(f"{BASE_URL}/api/users/{test_user_id}/match-participants", 
                              headers=commander_headers)
        assert response.status_code == 200, f"Find matches failed: {response.text}"
        
        data = response.json()
        assert "user" in data
        assert "matches" in data
        assert isinstance(data["matches"], list)
        
        if len(data["matches"]) > 0:
            match = data["matches"][0]
            assert "match_type" in match
            assert "participant" in match
            assert "confidence" in match
            print(f"✓ Found {len(data['matches'])} potential matches")
        else:
            print("✓ Match search returned empty (no matching participants)")
    
    def test_link_user_to_participant(self, commander_headers):
        """Test POST /api/users/{id}/link-participant links and populates profile"""
        # Get commander's user ID
        me = requests.get(f"{BASE_URL}/api/auth/me", headers=commander_headers).json()
        
        # Get participants to find one to link
        participants = requests.get(f"{BASE_URL}/api/participants", headers=commander_headers)
        if participants.status_code != 200 or len(participants.json()) == 0:
            pytest.skip("No participants available")
        
        # Create a new test user to link
        test_email = f"{TEST_EMAIL_PREFIX}_tolink@test.cap.gov"
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "Test123!",
            "name": "User To Link",
            "role": "staff"
        })
        
        if reg_response.status_code != 200:
            pytest.skip("Could not create test user for linking")
        
        user_id = reg_response.json()["user"]["id"]
        participant_id = participants.json()[0]["id"]
        
        # Link participant to user
        response = requests.post(
            f"{BASE_URL}/api/users/{user_id}/link-participant?participant_id={participant_id}&auto_populate=true",
            headers=commander_headers
        )
        assert response.status_code == 200, f"Link participant failed: {response.text}"
        
        data = response.json()
        assert data["user"]["linked_participant_id"] == participant_id
        print(f"✓ User linked to participant successfully")
    
    def test_link_nonexistent_participant(self, commander_headers):
        """Test linking to non-existent participant returns 404"""
        # Get any user ID
        users = requests.get(f"{BASE_URL}/api/users", headers=commander_headers)
        if users.status_code != 200 or len(users.json()) == 0:
            pytest.skip("No users available")
        
        user_id = users.json()[0]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/users/{user_id}/link-participant?participant_id=nonexistent-id&auto_populate=true",
            headers=commander_headers
        )
        assert response.status_code == 404
        print("✓ Non-existent participant link correctly returns 404")


class TestProfilePhoto:
    """Test profile photo upload"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get commander auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Login failed")
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    def test_upload_profile_photo_invalid_type(self, auth_headers):
        """Test uploading non-image file fails"""
        files = {"file": ("test.txt", b"This is not an image", "text/plain")}
        response = requests.post(f"{BASE_URL}/api/profile/photo", headers=auth_headers, files=files)
        assert response.status_code == 400, "Should reject non-image files"
        print("✓ Non-image upload correctly rejected")
    
    def test_upload_profile_photo_valid(self, auth_headers):
        """Test uploading valid image succeeds"""
        # Create a minimal valid PNG image (1x1 pixel)
        png_data = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
            b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        files = {"file": ("test.png", png_data, "image/png")}
        response = requests.post(f"{BASE_URL}/api/profile/photo", headers=auth_headers, files=files)
        assert response.status_code == 200, f"Photo upload failed: {response.text}"
        
        data = response.json()
        assert "photo_url" in data
        assert data["photo_url"].startswith("data:image/png;base64,")
        print("✓ Profile photo uploaded successfully")
    
    def test_delete_profile_photo(self, auth_headers):
        """Test deleting profile photo"""
        response = requests.delete(f"{BASE_URL}/api/profile/photo", headers=auth_headers)
        assert response.status_code == 200
        
        # Verify photo is removed
        profile = requests.get(f"{BASE_URL}/api/profile", headers=auth_headers).json()
        assert profile.get("photo_url") is None
        print("✓ Profile photo deleted successfully")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture
    def commander_headers(self):
        """Get commander auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Commander login failed")
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    def test_cleanup_test_users(self, commander_headers):
        """Remove test users created during testing"""
        users = requests.get(f"{BASE_URL}/api/users", headers=commander_headers)
        if users.status_code != 200:
            return
        
        deleted = 0
        for user in users.json():
            if TEST_EMAIL_PREFIX in user.get("email", ""):
                response = requests.delete(f"{BASE_URL}/api/users/{user['id']}", 
                                         headers=commander_headers)
                if response.status_code == 200:
                    deleted += 1
        
        print(f"✓ Cleaned up {deleted} test users")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
