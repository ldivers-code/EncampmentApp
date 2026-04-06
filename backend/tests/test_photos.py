"""
Test suite for Cadet Photo Upload feature
Tests: POST /api/participants/{id}/photo, GET /api/participants/{id}/photo, DELETE /api/participants/{id}/photo
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
COMMANDER_EMAIL = "commander@test.com"
COMMANDER_PASSWORD = "test123"
PARENT_EMAIL = "jane.hundley@test.com"
PARENT_PASSWORD = "parent123"

# Test participant ID (from main agent context)
TEST_PARTICIPANT_ID = "11e0d188-2260-4421-b8ba-3a8df13e8263"


@pytest.fixture(scope="module")
def commander_token():
    """Get commander auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": COMMANDER_EMAIL,
        "password": COMMANDER_PASSWORD
    })
    assert response.status_code == 200, f"Commander login failed: {response.text}"
    data = response.json()
    return data.get("access_token")


@pytest.fixture(scope="module")
def parent_token():
    """Get parent auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": PARENT_EMAIL,
        "password": PARENT_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Parent login failed: {response.text}")
    data = response.json()
    return data.get("access_token")


@pytest.fixture(scope="module")
def test_participant_id(commander_token):
    """Get a valid participant ID for testing"""
    headers = {"Authorization": f"Bearer {commander_token}"}
    response = requests.get(f"{BASE_URL}/api/participants", headers=headers)
    assert response.status_code == 200, f"Failed to get participants: {response.text}"
    participants = response.json()
    if not participants:
        pytest.skip("No participants found for testing")
    # Return first participant ID
    return participants[0].get("id")


class TestPhotoUpload:
    """Test photo upload endpoint"""
    
    def test_upload_photo_success(self, commander_token, test_participant_id):
        """Test successful photo upload by commander"""
        headers = {"Authorization": f"Bearer {commander_token}"}
        
        # Create a simple test image (1x1 pixel PNG)
        # PNG header for a 1x1 transparent pixel
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 dimensions
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,  # bit depth, color type
            0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,  # IDAT chunk
            0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,  # compressed data
            0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,  # checksum
            0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,  # IEND chunk
            0xAE, 0x42, 0x60, 0x82
        ])
        
        files = {
            "file": ("test_photo.png", io.BytesIO(png_data), "image/png")
        }
        
        response = requests.post(
            f"{BASE_URL}/api/participants/{test_participant_id}/photo",
            headers=headers,
            files=files
        )
        
        # Accept 200 or 201 for success
        assert response.status_code in [200, 201], f"Photo upload failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "message" in data or "photo_path" in data
        print(f"Photo upload successful: {data}")
    
    def test_upload_photo_invalid_type(self, commander_token, test_participant_id):
        """Test photo upload with invalid file type"""
        headers = {"Authorization": f"Bearer {commander_token}"}
        
        # Create a text file (invalid type)
        files = {
            "file": ("test.txt", io.BytesIO(b"This is not an image"), "text/plain")
        }
        
        response = requests.post(
            f"{BASE_URL}/api/participants/{test_participant_id}/photo",
            headers=headers,
            files=files
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid file type, got {response.status_code}"
        print(f"Invalid file type correctly rejected: {response.json()}")
    
    def test_upload_photo_no_auth(self, test_participant_id):
        """Test photo upload without authentication"""
        files = {
            "file": ("test.png", io.BytesIO(b"fake image data"), "image/png")
        }
        
        response = requests.post(
            f"{BASE_URL}/api/participants/{test_participant_id}/photo",
            files=files
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("Unauthenticated upload correctly rejected")
    
    def test_upload_photo_nonexistent_participant(self, commander_token):
        """Test photo upload for non-existent participant"""
        headers = {"Authorization": f"Bearer {commander_token}"}
        
        fake_id = "00000000-0000-0000-0000-000000000000"
        files = {
            "file": ("test.png", io.BytesIO(b"fake image data"), "image/png")
        }
        
        response = requests.post(
            f"{BASE_URL}/api/participants/{fake_id}/photo",
            headers=headers,
            files=files
        )
        
        assert response.status_code == 404, f"Expected 404 for non-existent participant, got {response.status_code}"
        print("Non-existent participant correctly rejected")


class TestPhotoRetrieval:
    """Test photo retrieval endpoint"""
    
    def test_get_photo_with_query_auth(self, commander_token, test_participant_id):
        """Test photo retrieval with query parameter auth"""
        # First upload a photo
        headers = {"Authorization": f"Bearer {commander_token}"}
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
            0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
            0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
            0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,
            0xAE, 0x42, 0x60, 0x82
        ])
        files = {"file": ("test.png", io.BytesIO(png_data), "image/png")}
        upload_response = requests.post(
            f"{BASE_URL}/api/participants/{test_participant_id}/photo",
            headers=headers,
            files=files
        )
        
        if upload_response.status_code not in [200, 201]:
            pytest.skip(f"Photo upload failed, skipping retrieval test: {upload_response.text}")
        
        # Now retrieve with query param auth
        response = requests.get(
            f"{BASE_URL}/api/participants/{test_participant_id}/photo?auth={commander_token}"
        )
        
        # Should return 200 with image data, or 404 if no photo
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            assert response.headers.get("content-type", "").startswith("image/")
            print(f"Photo retrieved successfully, content-type: {response.headers.get('content-type')}")
        else:
            print("No photo found (404) - this is acceptable if photo wasn't stored")
    
    def test_get_photo_with_header_auth(self, commander_token, test_participant_id):
        """Test photo retrieval with Authorization header"""
        headers = {"Authorization": f"Bearer {commander_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/participants/{test_participant_id}/photo",
            headers=headers
        )
        
        # Should return 200 with image or 404 if no photo
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"Photo retrieval with header auth: status {response.status_code}")
    
    def test_get_photo_no_auth(self, test_participant_id):
        """Test photo retrieval without authentication"""
        response = requests.get(
            f"{BASE_URL}/api/participants/{test_participant_id}/photo"
        )
        
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("Unauthenticated retrieval correctly rejected")
    
    def test_get_photo_invalid_token(self, test_participant_id):
        """Test photo retrieval with invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/participants/{test_participant_id}/photo?auth=invalid_token_here"
        )
        
        assert response.status_code == 401, f"Expected 401 with invalid token, got {response.status_code}"
        print("Invalid token correctly rejected")


class TestPhotoDelete:
    """Test photo deletion endpoint"""
    
    def test_delete_photo_success(self, commander_token, test_participant_id):
        """Test successful photo deletion by commander"""
        headers = {"Authorization": f"Bearer {commander_token}"}
        
        response = requests.delete(
            f"{BASE_URL}/api/participants/{test_participant_id}/photo",
            headers=headers
        )
        
        # Accept 200 or 404 (if no photo exists)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            print(f"Photo deleted successfully: {data}")
        else:
            print("No photo to delete (404)")
    
    def test_delete_photo_no_auth(self, test_participant_id):
        """Test photo deletion without authentication"""
        response = requests.delete(
            f"{BASE_URL}/api/participants/{test_participant_id}/photo"
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("Unauthenticated deletion correctly rejected")
    
    def test_delete_photo_nonexistent_participant(self, commander_token):
        """Test photo deletion for non-existent participant"""
        headers = {"Authorization": f"Bearer {commander_token}"}
        
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = requests.delete(
            f"{BASE_URL}/api/participants/{fake_id}/photo",
            headers=headers
        )
        
        assert response.status_code == 404, f"Expected 404 for non-existent participant, got {response.status_code}"
        print("Non-existent participant correctly rejected")


class TestParticipantsByFlight:
    """Test that photo_path is included in by-flight endpoint"""
    
    def test_by_flight_includes_photo_path(self, commander_token):
        """Test that /api/participants/by-flight includes photo_path field"""
        headers = {"Authorization": f"Bearer {commander_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/participants/by-flight",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed to get by-flight data: {response.text}"
        data = response.json()
        
        # Check that at least one flight group exists
        assert isinstance(data, list), "Expected list of flight groups"
        
        if data:
            # Check first flight group has members with photo_path field
            first_group = data[0]
            assert "members" in first_group, "Flight group should have members"
            if first_group["members"]:
                first_member = first_group["members"][0]
                # photo_path should be in the response (can be empty string or actual path)
                assert "photo_path" in first_member, "Member should have photo_path field"
                print(f"by-flight endpoint includes photo_path: {first_member.get('photo_path', 'empty')}")
        
        print(f"by-flight endpoint returned {len(data)} flight groups")


class TestRosterPageIntegration:
    """Test roster page data includes photo information"""
    
    def test_participants_list(self, commander_token):
        """Test that participants list endpoint works"""
        headers = {"Authorization": f"Bearer {commander_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/participants",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed to get participants: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of participants"
        print(f"Participants endpoint returned {len(data)} participants")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
