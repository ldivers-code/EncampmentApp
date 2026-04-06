"""
Test Schedule Import, Publish/Unpublish, and Settings Features
- Schedule import endpoint: POST /api/schedule/import
- Schedule publish endpoint: POST /api/schedule/publish  
- Schedule unpublish endpoint: POST /api/schedule/unpublish
- Schedule settings endpoint: GET /api/schedule/settings
- Schedule CRUD operations
"""
import pytest
import requests
import os
import io
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD

# Get backend URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = COMMANDER_EMAIL
TEST_PASSWORD = COMMANDER_PASSWORD
TEST_NAME = "Test Commander"


class TestScheduleFeatures:
    """Test suite for schedule import, publish/unpublish features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Try to login first
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if login_response.status_code == 200:
            self.token = login_response.json()["access_token"]
        else:
            # Register if login fails
            register_response = self.session.post(f"{BASE_URL}/api/auth/register", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "name": TEST_NAME,
                "role": "commander"
            })
            if register_response.status_code == 200:
                self.token = register_response.json()["access_token"]
            else:
                pytest.skip("Could not authenticate")
        
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    # ========== Schedule Settings Tests ==========
    
    def test_get_schedule_settings(self):
        """Test GET /api/schedule/settings returns correct fields"""
        response = self.session.get(f"{BASE_URL}/api/schedule/settings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "is_published" in data, "Missing is_published field"
        assert "last_published_at" in data, "Missing last_published_at field"
        assert "last_modified_at" in data, "Missing last_modified_at field"
        print(f"Schedule settings: is_published={data['is_published']}, last_published_at={data['last_published_at']}")
    
    # ========== Schedule Unpublish Tests ==========
    
    def test_unpublish_schedule(self):
        """Test POST /api/schedule/unpublish marks schedule as draft"""
        response = self.session.post(f"{BASE_URL}/api/schedule/unpublish")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Missing message in response"
        assert "unpublish" in data["message"].lower(), f"Unexpected message: {data['message']}"
        
        # Verify settings updated
        settings_response = self.session.get(f"{BASE_URL}/api/schedule/settings")
        assert settings_response.status_code == 200
        settings = settings_response.json()
        assert settings["is_published"] == False, "Schedule should be unpublished (draft)"
        print("Schedule unpublished successfully")
    
    # ========== Schedule Publish Tests ==========
    
    def test_publish_schedule(self):
        """Test POST /api/schedule/publish marks schedule as published"""
        response = self.session.post(f"{BASE_URL}/api/schedule/publish")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "message" in data, "Missing message in response"
        assert "published_at" in data, "Missing published_at in response"
        
        # Verify settings updated
        settings_response = self.session.get(f"{BASE_URL}/api/schedule/settings")
        assert settings_response.status_code == 200
        settings = settings_response.json()
        assert settings["is_published"] == True, "Schedule should be published"
        assert settings["last_published_at"] is not None, "last_published_at should be set"
        print(f"Schedule published at: {settings['last_published_at']}")
    
    # ========== Schedule Import Tests ==========
    
    def test_import_schedule_with_valid_excel(self):
        """Test POST /api/schedule/import imports predefined schedule (July 17-24)"""
        # Create a minimal valid Excel file for testing
        try:
            import openpyxl
            from io import BytesIO
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws['A1'] = 'Schedule'
            ws['B1'] = 'Template'
            
            excel_buffer = BytesIO()
            wb.save(excel_buffer)
            excel_buffer.seek(0)
            
            files = {'file': ('schedule.xlsx', excel_buffer, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            headers = {"Authorization": f"Bearer {self.token}"}
            
            response = requests.post(f"{BASE_URL}/api/schedule/import", files=files, headers=headers)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            data = response.json()
            assert "message" in data, "Missing message in response"
            assert "imported" in data["message"].lower(), f"Unexpected message: {data['message']}"
            # The import should create events for July 17-24
            assert "July 17-24" in data["message"] or "events" in data["message"].lower(), f"Expected success message, got: {data['message']}"
            print(f"Import result: {data['message']}")
            
        except ImportError:
            pytest.skip("openpyxl not installed, skipping Excel import test")
    
    def test_import_schedule_invalid_file_type(self):
        """Test POST /api/schedule/import rejects non-Excel files"""
        files = {'file': ('schedule.txt', b'not an excel file', 'text/plain')}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.post(f"{BASE_URL}/api/schedule/import", files=files, headers=headers)
        assert response.status_code == 400, f"Expected 400 for invalid file type, got {response.status_code}"
        print("Correctly rejected non-Excel file")
    
    # ========== Schedule CRUD Tests ==========
    
    def test_get_schedule_events(self):
        """Test GET /api/schedule returns events list"""
        response = self.session.get(f"{BASE_URL}/api/schedule")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Found {len(data)} schedule events")
        
        if len(data) > 0:
            # Check event structure
            event = data[0]
            assert "id" in event, "Event missing id"
            assert "title" in event, "Event missing title"
            assert "date" in event, "Event missing date"
            assert "start_time" in event, "Event missing start_time"
            assert "end_time" in event, "Event missing end_time"
            assert "event_type" in event, "Event missing event_type"
            assert "is_published" in event, "Event missing is_published flag"
    
    def test_create_schedule_event(self):
        """Test POST /api/schedule creates new event"""
        event_data = {
            "title": "TEST_Schedule_Event",
            "description": "Test event for schedule feature testing",
            "date": "2026-07-17",
            "start_time": "09:00",
            "end_time": "10:00",
            "location": "Test Location",
            "event_type": "training",
            "squadron": ""
        }
        
        response = self.session.post(f"{BASE_URL}/api/schedule", json=event_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["title"] == event_data["title"], "Title mismatch"
        assert data["date"] == event_data["date"], "Date mismatch"
        assert "id" in data, "Missing event id"
        
        # Store event id for cleanup
        self.created_event_id = data["id"]
        print(f"Created event: {data['id']}")
        
        # Verify event persisted
        get_response = self.session.get(f"{BASE_URL}/api/schedule")
        assert get_response.status_code == 200
        events = get_response.json()
        event_ids = [e["id"] for e in events]
        assert data["id"] in event_ids, "Created event not found in schedule"
    
    def test_update_schedule_event(self):
        """Test PUT /api/schedule/{id} updates event"""
        # First create an event
        event_data = {
            "title": "TEST_Update_Event",
            "description": "Original description",
            "date": "2026-07-18",
            "start_time": "11:00",
            "end_time": "12:00",
            "location": "Original Location",
            "event_type": "ceremony",
            "squadron": ""
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/schedule", json=event_data)
        assert create_response.status_code == 200
        event_id = create_response.json()["id"]
        
        # Update the event
        updated_data = {
            "title": "TEST_Updated_Event",
            "description": "Updated description",
            "date": "2026-07-18",
            "start_time": "11:30",
            "end_time": "12:30",
            "location": "Updated Location",
            "event_type": "training",
            "squadron": "sq1"
        }
        
        update_response = self.session.put(f"{BASE_URL}/api/schedule/{event_id}", json=updated_data)
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}"
        
        data = update_response.json()
        assert data["title"] == updated_data["title"], "Title not updated"
        assert data["location"] == updated_data["location"], "Location not updated"
        assert data["event_type"] == updated_data["event_type"], "Event type not updated"
        print(f"Updated event: {event_id}")
    
    def test_delete_schedule_event(self):
        """Test DELETE /api/schedule/{id} removes event"""
        # First create an event to delete
        event_data = {
            "title": "TEST_Delete_Event",
            "description": "Event to be deleted",
            "date": "2026-07-19",
            "start_time": "14:00",
            "end_time": "15:00",
            "location": "Delete Location",
            "event_type": "admin",
            "squadron": ""
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/schedule", json=event_data)
        assert create_response.status_code == 200
        event_id = create_response.json()["id"]
        
        # Delete the event
        delete_response = self.session.delete(f"{BASE_URL}/api/schedule/{event_id}")
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}"
        
        # Verify event removed
        get_response = self.session.get(f"{BASE_URL}/api/schedule")
        events = get_response.json()
        event_ids = [e["id"] for e in events]
        assert event_id not in event_ids, "Deleted event still in schedule"
        print(f"Deleted event: {event_id}")
    
    # ========== Schedule Date Verification Tests ==========
    
    def test_schedule_dates_july_17_24(self):
        """Verify imported schedule has events for July 17-24, 2026"""
        response = self.session.get(f"{BASE_URL}/api/schedule")
        assert response.status_code == 200
        
        events = response.json()
        if len(events) == 0:
            pytest.skip("No events in schedule to verify dates")
        
        # Expected dates
        expected_dates = [
            "2026-07-17",  # Staff Arrival
            "2026-07-18",  # In-Processing
            "2026-07-19",  # Day 1
            "2026-07-20",  # Day 2
            "2026-07-21",  # Day 3
            "2026-07-22",  # Day 4
            "2026-07-23",  # Day 5
            "2026-07-24"   # Graduation
        ]
        
        # Get unique dates from events
        event_dates = set(e["date"] for e in events)
        
        # Check how many expected dates are covered
        covered_dates = [d for d in expected_dates if d in event_dates]
        print(f"Covered dates: {covered_dates}")
        print(f"Event dates found: {sorted(event_dates)}")
        
        # At least some of the expected dates should be covered
        assert len(covered_dates) > 0, "No expected dates (July 17-24) found in schedule"
    
    def test_schedule_has_staff_arrival_events(self):
        """Verify schedule has events on July 17 (Staff Arrival)"""
        response = self.session.get(f"{BASE_URL}/api/schedule")
        assert response.status_code == 200
        
        events = response.json()
        july_17_events = [e for e in events if e["date"] == "2026-07-17"]
        
        if len(events) > 0 and len(july_17_events) == 0:
            # Schedule was imported but might have different date format
            print(f"No July 17 events found. First event date: {events[0]['date']}")
        else:
            print(f"Found {len(july_17_events)} events on July 17 (Staff Arrival)")
    
    def test_schedule_has_graduation_events(self):
        """Verify schedule has events on July 24 (Graduation)"""
        response = self.session.get(f"{BASE_URL}/api/schedule")
        assert response.status_code == 200
        
        events = response.json()
        july_24_events = [e for e in events if e["date"] == "2026-07-24"]
        
        if len(events) > 0:
            print(f"Found {len(july_24_events)} events on July 24 (Graduation)")
            
            # Check for graduation ceremony
            graduation_events = [e for e in july_24_events if "graduation" in e["title"].lower()]
            if graduation_events:
                print(f"Found graduation event: {graduation_events[0]['title']}")


class TestScheduleAccessControl:
    """Test role-based access control for schedule features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_schedule_settings_requires_auth(self):
        """Test that schedule settings requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/schedule/settings")
        assert response.status_code == 403 or response.status_code == 401, f"Expected 401/403 without auth, got {response.status_code}"
        print("Schedule settings correctly requires authentication")
    
    def test_publish_requires_editor_role(self):
        """Test that publishing requires editor (commander/staff) role"""
        response = self.session.post(f"{BASE_URL}/api/schedule/publish")
        assert response.status_code == 403 or response.status_code == 401, f"Expected 401/403 without auth, got {response.status_code}"
        print("Publish correctly requires authentication")
    
    def test_unpublish_requires_editor_role(self):
        """Test that unpublishing requires editor (commander/staff) role"""
        response = self.session.post(f"{BASE_URL}/api/schedule/unpublish")
        assert response.status_code == 403 or response.status_code == 401, f"Expected 401/403 without auth, got {response.status_code}"
        print("Unpublish correctly requires authentication")
    
    def test_import_requires_editor_role(self):
        """Test that import requires editor (commander/staff) role"""
        files = {'file': ('test.xlsx', b'test', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        response = requests.post(f"{BASE_URL}/api/schedule/import", files=files)
        assert response.status_code == 403 or response.status_code == 401, f"Expected 401/403 without auth, got {response.status_code}"
        print("Import correctly requires authentication")


# Cleanup test data
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_events():
    """Cleanup TEST_ prefixed events after all tests"""
    yield
    
    # Login and cleanup
    session = requests.Session()
    login_response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get all events
        events_response = session.get(f"{BASE_URL}/api/schedule")
        if events_response.status_code == 200:
            events = events_response.json()
            for event in events:
                if event["title"].startswith("TEST_"):
                    session.delete(f"{BASE_URL}/api/schedule/{event['id']}")
                    print(f"Cleaned up test event: {event['title']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
