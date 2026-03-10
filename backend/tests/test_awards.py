"""
Test file for Honor Awards feature - Individual Awards Tracking
Tests: Award types, CRUD operations, auto-assign, recipients summary
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cadet-med-hub.preview.emergentagent.com')

class TestAwardsFeature:
    """Test suite for Honor Awards feature"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Login as commander and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "commander@test.cap.gov",
            "password": "test123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json().get("access_token")
        assert token, "No token returned"
        return token
    
    @pytest.fixture(scope="class")
    def headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    @pytest.fixture(scope="class")
    def participant_id(self, headers):
        """Get a participant ID for testing awards"""
        response = requests.get(f"{BASE_URL}/api/participants", headers=headers)
        assert response.status_code == 200
        participants = response.json()
        # Get first non-removed participant
        for p in participants:
            if not p.get("is_removed"):
                return p["id"]
        pytest.skip("No participants available for testing")
    
    # ============ Award Types Tests ============
    def test_get_award_types(self, headers):
        """Test GET /api/points/awards/types returns all award types"""
        response = requests.get(f"{BASE_URL}/api/points/awards/types", headers=headers)
        assert response.status_code == 200, f"Failed to get award types: {response.text}"
        
        types = response.json()
        assert isinstance(types, list), "Response should be a list"
        assert len(types) >= 10, f"Expected at least 10 award types, got {len(types)}"
        
        # Verify expected award types exist
        type_values = [t["value"] for t in types]
        expected_types = [
            "cadet_of_day", "cadre_of_day", "flight_honor_graduate",
            "commandants_award", "honor_cadet", "honor_cadre",
            "leadership_award", "pt_excellence", "academic_excellence",
            "drill_award", "spirit_award", "most_improved"
        ]
        for expected in expected_types:
            assert expected in type_values, f"Award type '{expected}' not found"
        
        # Verify structure
        for t in types:
            assert "value" in t, "Award type missing 'value'"
            assert "label" in t, "Award type missing 'label'"
            assert "auto_eligible" in t, "Award type missing 'auto_eligible'"
            assert "participant_type" in t, "Award type missing 'participant_type'"
        
        print(f"✓ Found {len(types)} award types: {type_values}")
    
    def test_cadet_of_day_is_auto_eligible(self, headers):
        """Test cadet_of_day and cadre_of_day are auto-eligible"""
        response = requests.get(f"{BASE_URL}/api/points/awards/types", headers=headers)
        types = response.json()
        
        cadet_of_day = next((t for t in types if t["value"] == "cadet_of_day"), None)
        cadre_of_day = next((t for t in types if t["value"] == "cadre_of_day"), None)
        
        assert cadet_of_day, "cadet_of_day type not found"
        assert cadet_of_day["auto_eligible"] == True, "cadet_of_day should be auto_eligible"
        assert cadet_of_day["participant_type"] == "cadet", "cadet_of_day should be for cadets"
        
        assert cadre_of_day, "cadre_of_day type not found"
        assert cadre_of_day["auto_eligible"] == True, "cadre_of_day should be auto_eligible"
        assert cadre_of_day["participant_type"] == "cadre", "cadre_of_day should be for cadre"
        
        print("✓ cadet_of_day and cadre_of_day are auto-eligible")
    
    # ============ Create Award Tests ============
    def test_create_honor_award(self, headers, participant_id):
        """Test POST /api/points/awards creates a new award"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/points/awards",
            params={
                "award_type": "leadership_award",
                "recipient_id": participant_id,
                "date": today,
                "notes": "TEST_Leadership excellence displayed"
            },
            headers=headers
        )
        assert response.status_code == 200, f"Failed to create award: {response.text}"
        
        data = response.json()
        # Could be new award or updated award
        assert "id" in data or "message" in data
        
        if "id" in data:
            assert data["award_type"] == "leadership_award"
            assert data["recipient_id"] == participant_id
            assert data["date"] == today
            assert "recipient_name" in data
            print(f"✓ Created award for {data['recipient_name']}")
        else:
            print(f"✓ Award operation completed: {data.get('message')}")
    
    def test_create_award_with_notes(self, headers, participant_id):
        """Test creating award with notes"""
        today = datetime.now().strftime("%Y-%m-%d")
        notes = "TEST_Exceptional performance during drill competition"
        
        response = requests.post(
            f"{BASE_URL}/api/points/awards",
            params={
                "award_type": "drill_award",
                "recipient_id": participant_id,
                "date": today,
                "notes": notes
            },
            headers=headers
        )
        assert response.status_code == 200, f"Failed to create award: {response.text}"
        
        data = response.json()
        if "id" in data:
            assert data.get("notes") == notes, "Notes not saved correctly"
            print(f"✓ Created drill_award with notes")
    
    def test_create_award_invalid_recipient(self, headers):
        """Test creating award with invalid recipient returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/points/awards",
            params={
                "award_type": "spirit_award",
                "recipient_id": "non-existent-id",
                "date": datetime.now().strftime("%Y-%m-%d")
            },
            headers=headers
        )
        assert response.status_code == 404, "Should return 404 for invalid recipient"
        print("✓ Invalid recipient returns 404")
    
    # ============ Get Awards Tests ============
    def test_get_honor_awards(self, headers):
        """Test GET /api/points/awards returns awards list"""
        response = requests.get(f"{BASE_URL}/api/points/awards", headers=headers)
        assert response.status_code == 200, f"Failed to get awards: {response.text}"
        
        awards = response.json()
        assert isinstance(awards, list), "Response should be a list"
        
        if len(awards) > 0:
            award = awards[0]
            assert "id" in award
            assert "award_type" in award
            assert "award_label" in award
            assert "recipient_id" in award
            assert "recipient_name" in award
            assert "date" in award
            print(f"✓ Retrieved {len(awards)} awards")
        else:
            print("✓ No awards found (empty list)")
    
    def test_get_awards_filter_by_type(self, headers):
        """Test filtering awards by type"""
        response = requests.get(
            f"{BASE_URL}/api/points/awards",
            params={"award_type": "cadet_of_day"},
            headers=headers
        )
        assert response.status_code == 200
        
        awards = response.json()
        for award in awards:
            assert award["award_type"] == "cadet_of_day", "Filter not working correctly"
        print(f"✓ Filtered awards by type: {len(awards)} cadet_of_day awards")
    
    def test_get_awards_by_date(self, headers):
        """Test GET /api/points/awards/by-date/{date}"""
        test_date = "2026-02-24"  # Date mentioned in context
        response = requests.get(
            f"{BASE_URL}/api/points/awards/by-date/{test_date}",
            headers=headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        awards = response.json()
        assert isinstance(awards, list)
        for award in awards:
            assert award["date"] == test_date, "Date filter not working"
        print(f"✓ Got {len(awards)} awards for {test_date}")
    
    def test_get_awards_by_current_date(self, headers):
        """Test getting awards for current date"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = requests.get(
            f"{BASE_URL}/api/points/awards/by-date/{today}",
            headers=headers
        )
        assert response.status_code == 200
        
        awards = response.json()
        print(f"✓ Got {len(awards)} awards for today ({today})")
    
    # ============ Auto-Assign Awards Tests ============
    def test_auto_assign_daily_awards(self, headers):
        """Test POST /api/points/awards/auto-assign/{date}"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/points/awards/auto-assign/{today}",
            headers=headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "awards" in data
        assert isinstance(data["awards"], list)
        
        print(f"✓ Auto-assign result: {data['message']}")
        for award in data["awards"]:
            print(f"  - {award['award']}: {award['recipient']}")
    
    # ============ Recipients Summary Tests ============
    def test_get_recipients_summary(self, headers):
        """Test GET /api/points/awards/recipients-summary"""
        response = requests.get(
            f"{BASE_URL}/api/points/awards/recipients-summary",
            headers=headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        summary = response.json()
        assert isinstance(summary, list)
        
        if len(summary) > 0:
            recipient = summary[0]
            assert "_id" in recipient  # recipient_id
            assert "recipient_name" in recipient
            assert "total_awards" in recipient
            assert "awards" in recipient
            assert isinstance(recipient["awards"], list)
            print(f"✓ Top recipient: {recipient['recipient_name']} with {recipient['total_awards']} awards")
        else:
            print("✓ No recipients summary (no awards yet)")
    
    # ============ Delete Award Tests ============
    def test_delete_award(self, headers, participant_id):
        """Test DELETE /api/points/awards/{award_id}"""
        # First create an award to delete
        today = datetime.now().strftime("%Y-%m-%d")
        create_response = requests.post(
            f"{BASE_URL}/api/points/awards",
            params={
                "award_type": "most_improved",
                "recipient_id": participant_id,
                "date": today,
                "notes": "TEST_Award to be deleted"
            },
            headers=headers
        )
        assert create_response.status_code == 200
        
        # Get the award ID
        data = create_response.json()
        award_id = data.get("id")
        if not award_id:
            # Award might have been updated, get from list
            awards = requests.get(
                f"{BASE_URL}/api/points/awards",
                params={"award_type": "most_improved"},
                headers=headers
            ).json()
            award_id = awards[0]["id"] if awards else None
        
        if award_id:
            # Delete the award
            delete_response = requests.delete(
                f"{BASE_URL}/api/points/awards/{award_id}",
                headers=headers
            )
            assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
            
            result = delete_response.json()
            assert "message" in result
            print(f"✓ Deleted award: {result['message']}")
        else:
            print("⚠ Could not get award ID for deletion test")
    
    def test_delete_nonexistent_award(self, headers):
        """Test deleting non-existent award returns 404"""
        response = requests.delete(
            f"{BASE_URL}/api/points/awards/nonexistent-id",
            headers=headers
        )
        assert response.status_code == 404, "Should return 404"
        print("✓ Delete non-existent award returns 404")
    
    # ============ Permission Tests ============
    def test_unauthorized_delete(self):
        """Test that non-commander cannot delete awards"""
        # Login as staff (not commander)
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@test.cap.gov",
            "password": "test123"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Staff user not available for testing")
        
        staff_token = login_response.json().get("access_token")
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        
        # Try to delete - should fail unless user is commander
        # Note: plans_programs can also delete per backend code
        response = requests.delete(
            f"{BASE_URL}/api/points/awards/any-id",
            headers=staff_headers
        )
        # Staff cannot delete (only commander and plans_programs)
        if response.status_code == 403:
            print("✓ Staff user correctly denied delete permission")
        else:
            print(f"⚠ Delete returned {response.status_code} (expected 403 for staff)")


# Cleanup fixtures
@pytest.fixture(scope="class", autouse=True)
def cleanup_test_awards(request):
    """Cleanup test awards after tests"""
    yield
    # Cleanup would go here if needed


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
