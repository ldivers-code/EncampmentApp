"""
Test suite for Unit Assignment and Flight-Specific Scheduling features
- Admin page: Squadron/Flight dropdown assignment 
- PUT /api/users/{user_id}/unit endpoint
- Schedule settings endpoint with version number
- Event creation with target_groups
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestConfig:
    """Test configuration and auth helpers"""
    
    @staticmethod
    def get_commander_token():
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "commander@test.com", "password": "test123"}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Commander authentication failed")
        
    @staticmethod
    def get_auth_headers(token):
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


class TestUserUnitAssignment:
    """Tests for PUT /api/users/{user_id}/unit endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestConfig.get_commander_token()
        self.headers = TestConfig.get_auth_headers(self.token)
        
    def test_get_users_returns_squadron_and_flight(self):
        """Users list includes squadron and flight fields"""
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        assert response.status_code == 200
        users = response.json()
        assert len(users) > 0
        # Check that squadron/flight fields exist
        for user in users:
            assert "squadron" in user
            assert "flight" in user
    
    def test_assign_squadron_and_flight_to_user(self):
        """Successfully assign squadron and flight to a user"""
        # First get a user ID
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        users = response.json()
        cadet_user = next((u for u in users if u["role"] == "cadet"), None)
        if not cadet_user:
            pytest.skip("No cadet user available for testing")
        
        user_id = cadet_user["id"]
        
        # Assign to sq1/alpha
        response = requests.put(
            f"{BASE_URL}/api/users/{user_id}/unit",
            json={"squadron": "sq1", "flight": "alpha"},
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["squadron"] == "sq1"
        assert data["flight"] == "alpha"
        
    def test_assign_staff_squadron_no_flight(self):
        """Staff squadron assignment should work without flight"""
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        users = response.json()
        cadet_user = next((u for u in users if u["role"] == "cadet"), None)
        if not cadet_user:
            pytest.skip("No cadet user available for testing")
        
        user_id = cadet_user["id"]
        
        # Assign to staff (no flight)
        response = requests.put(
            f"{BASE_URL}/api/users/{user_id}/unit",
            json={"squadron": "staff", "flight": None},
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["squadron"] == "staff"
        
    def test_invalid_flight_squadron_combination_rejected(self):
        """Flight must belong to correct squadron"""
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        users = response.json()
        cadet_user = next((u for u in users if u["role"] == "cadet"), None)
        if not cadet_user:
            pytest.skip("No cadet user available for testing")
        
        user_id = cadet_user["id"]
        
        # Try invalid combination: alpha flight with sq2 (alpha belongs to sq1)
        response = requests.put(
            f"{BASE_URL}/api/users/{user_id}/unit",
            json={"squadron": "sq2", "flight": "alpha"},
            headers=self.headers
        )
        assert response.status_code == 400
        assert "belongs to" in response.json()["detail"]
        
    def test_clear_unit_assignment(self):
        """Clear unit assignment by setting to null/none"""
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        users = response.json()
        cadet_user = next((u for u in users if u["role"] == "cadet"), None)
        if not cadet_user:
            pytest.skip("No cadet user available for testing")
        
        user_id = cadet_user["id"]
        
        # Clear assignment
        response = requests.put(
            f"{BASE_URL}/api/users/{user_id}/unit",
            json={"squadron": None, "flight": None},
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Restore for other tests
        requests.put(
            f"{BASE_URL}/api/users/{user_id}/unit",
            json={"squadron": "sq1", "flight": "alpha"},
            headers=self.headers
        )


class TestScheduleSettings:
    """Tests for schedule settings endpoint with version number"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestConfig.get_commander_token()
        self.headers = TestConfig.get_auth_headers(self.token)
        
    def test_get_schedule_settings_returns_version(self):
        """Schedule settings include version number for real-time sync"""
        response = requests.get(f"{BASE_URL}/api/schedule/settings", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "is_published" in data
        assert "last_modified_at" in data
        
    def test_version_is_integer(self):
        """Version number is an integer"""
        response = requests.get(f"{BASE_URL}/api/schedule/settings", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["version"], int)


class TestEventTargetGroups:
    """Tests for event creation with target_groups"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestConfig.get_commander_token()
        self.headers = TestConfig.get_auth_headers(self.token)
        
    def test_create_event_with_target_groups(self):
        """Create event with specific target groups"""
        event_data = {
            "title": "TEST_SQ1_Training",
            "description": "Training for Squadron 1 only",
            "date": "2026-07-19",
            "start_time": "10:00",
            "end_time": "11:00",
            "location": "TR-2",
            "event_type": "training",
            "target_groups": ["sq1"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/schedule",
            json=event_data,
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["target_groups"] == ["sq1"]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/schedule/{data['id']}", headers=self.headers)
        
    def test_create_event_with_multiple_target_groups(self):
        """Create event targeting multiple groups"""
        event_data = {
            "title": "TEST_Multi_Target",
            "description": "Training for multiple groups",
            "date": "2026-07-20",
            "start_time": "14:00",
            "end_time": "15:00",
            "location": "TR-3",
            "event_type": "training",
            "target_groups": ["sq1", "alpha", "bravo"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/schedule",
            json=event_data,
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert set(data["target_groups"]) == {"sq1", "alpha", "bravo"}
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/schedule/{data['id']}", headers=self.headers)
        
    def test_create_event_with_all_target(self):
        """Create event targeting all participants"""
        event_data = {
            "title": "TEST_All_Participants",
            "description": "Event for everyone",
            "date": "2026-07-21",
            "start_time": "09:00",
            "end_time": "10:00",
            "location": "Parade Field",
            "event_type": "ceremony",
            "target_groups": ["all"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/schedule",
            json=event_data,
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "all" in data["target_groups"]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/schedule/{data['id']}", headers=self.headers)
        
    def test_create_event_with_staff_only(self):
        """Create staff-only event"""
        event_data = {
            "title": "TEST_Staff_Briefing",
            "description": "Staff briefing",
            "date": "2026-07-22",
            "start_time": "07:00",
            "end_time": "07:30",
            "location": "Staff Room",
            "event_type": "admin",
            "target_groups": ["staff"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/schedule",
            json=event_data,
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["target_groups"] == ["staff"]
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/schedule/{data['id']}", headers=self.headers)


class TestScheduleFiltering:
    """Tests for schedule filtering by user unit"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestConfig.get_commander_token()
        self.headers = TestConfig.get_auth_headers(self.token)
        
    def test_schedule_returns_events_with_target_groups(self):
        """Schedule endpoint returns target_groups field for each event"""
        response = requests.get(f"{BASE_URL}/api/schedule", headers=self.headers)
        assert response.status_code == 200
        events = response.json()
        if len(events) > 0:
            # Check that events have target_groups
            for event in events[:5]:  # Check first 5 events
                assert "target_groups" in event
                assert isinstance(event["target_groups"], list)


class TestValidSquadronFlightCombinations:
    """Tests for valid squadron/flight combinations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestConfig.get_commander_token()
        self.headers = TestConfig.get_auth_headers(self.token)
        
    def test_sq1_alpha_valid(self):
        """Squadron 1 with Alpha flight is valid"""
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        users = response.json()
        cadet_user = next((u for u in users if u["role"] == "cadet"), None)
        if not cadet_user:
            pytest.skip("No cadet user available")
        
        response = requests.put(
            f"{BASE_URL}/api/users/{cadet_user['id']}/unit",
            json={"squadron": "sq1", "flight": "alpha"},
            headers=self.headers
        )
        assert response.status_code == 200
        
    def test_sq2_charlie_valid(self):
        """Squadron 2 with Charlie flight is valid"""
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        users = response.json()
        cadet_user = next((u for u in users if u["role"] == "cadet"), None)
        if not cadet_user:
            pytest.skip("No cadet user available")
        
        response = requests.put(
            f"{BASE_URL}/api/users/{cadet_user['id']}/unit",
            json={"squadron": "sq2", "flight": "charlie"},
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Restore
        requests.put(
            f"{BASE_URL}/api/users/{cadet_user['id']}/unit",
            json={"squadron": "sq1", "flight": "alpha"},
            headers=self.headers
        )
        
    def test_sq3_echo_valid(self):
        """Squadron 3 with Echo flight is valid"""
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        users = response.json()
        cadet_user = next((u for u in users if u["role"] == "cadet"), None)
        if not cadet_user:
            pytest.skip("No cadet user available")
        
        response = requests.put(
            f"{BASE_URL}/api/users/{cadet_user['id']}/unit",
            json={"squadron": "sq3", "flight": "echo"},
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Restore
        requests.put(
            f"{BASE_URL}/api/users/{cadet_user['id']}/unit",
            json={"squadron": "sq1", "flight": "alpha"},
            headers=self.headers
        )
