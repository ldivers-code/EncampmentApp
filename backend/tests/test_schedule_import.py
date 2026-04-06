"""
Test Schedule Import Feature - Excel multi-sheet parsing
Tests:
- POST /api/schedule/import with Excel file
- New categories 'aerospace' and 'character' in imported events
- GET /api/schedule returns events with correct dates (Jul 17-24)
- Re-import replaces existing schedule (idempotent)
- Non-Excel file upload returns 400
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
COMMANDER_EMAIL = "commander@test.com"
COMMANDER_PASSWORD = "test123"
EXCEL_FILE_PATH = "/tmp/schedule.xlsx"


class TestScheduleImport:
    """Schedule import endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as commander before each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token") or data.get("token")
        assert self.token, "No token in login response"
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        yield
        self.session.close()
    
    def test_import_excel_file_success(self):
        """Test importing the multi-sheet Excel file"""
        assert os.path.exists(EXCEL_FILE_PATH), f"Excel file not found at {EXCEL_FILE_PATH}"
        
        with open(EXCEL_FILE_PATH, 'rb') as f:
            files = {'file': ('schedule.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            # Remove Content-Type header for multipart
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(f"{BASE_URL}/api/schedule/import", files=files, headers=headers)
        
        assert response.status_code == 200, f"Import failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "imported_count" in data, "Missing imported_count in response"
        assert "type_breakdown" in data, "Missing type_breakdown in response"
        assert "message" in data, "Missing message in response"
        
        # Verify reasonable number of events imported (around 207 expected)
        imported_count = data["imported_count"]
        assert imported_count > 100, f"Too few events imported: {imported_count}"
        assert imported_count < 300, f"Too many events imported: {imported_count}"
        
        print(f"✓ Imported {imported_count} events")
        print(f"✓ Type breakdown: {data['type_breakdown']}")
    
    def test_imported_events_have_correct_dates(self):
        """Verify imported events have dates in Jul 17-24, 2026 range"""
        response = self.session.get(f"{BASE_URL}/api/schedule")
        assert response.status_code == 200, f"GET schedule failed: {response.text}"
        
        events = response.json()
        assert len(events) > 0, "No events returned"
        
        # Check date range
        expected_dates = [
            "2026-07-17", "2026-07-18", "2026-07-19", "2026-07-20",
            "2026-07-21", "2026-07-22", "2026-07-23", "2026-07-24"
        ]
        
        event_dates = set(e["date"] for e in events)
        
        # All event dates should be in expected range
        for date in event_dates:
            assert date in expected_dates, f"Unexpected date: {date}"
        
        # Should have events on multiple days
        assert len(event_dates) >= 6, f"Events only on {len(event_dates)} days, expected at least 6"
        
        print(f"✓ Events span {len(event_dates)} days: {sorted(event_dates)}")
    
    def test_aerospace_category_exists(self):
        """Verify 'aerospace' category events exist after import"""
        response = self.session.get(f"{BASE_URL}/api/schedule")
        assert response.status_code == 200
        
        events = response.json()
        aerospace_events = [e for e in events if e.get("event_type") == "aerospace"]
        
        assert len(aerospace_events) > 0, "No aerospace events found"
        
        # Print some aerospace event titles for verification
        print(f"✓ Found {len(aerospace_events)} aerospace events")
        for e in aerospace_events[:5]:
            print(f"  - {e['title']} on {e['date']}")
    
    def test_character_category_exists(self):
        """Verify 'character' category events exist after import"""
        response = self.session.get(f"{BASE_URL}/api/schedule")
        assert response.status_code == 200
        
        events = response.json()
        character_events = [e for e in events if e.get("event_type") == "character"]
        
        assert len(character_events) > 0, "No character events found"
        
        # Print some character event titles for verification
        print(f"✓ Found {len(character_events)} character events")
        for e in character_events[:5]:
            print(f"  - {e['title']} on {e['date']}")
    
    def test_all_event_types_present(self):
        """Verify all expected event types are present"""
        response = self.session.get(f"{BASE_URL}/api/schedule")
        assert response.status_code == 200
        
        events = response.json()
        event_types = set(e.get("event_type") for e in events)
        
        # Expected types based on the classifier
        expected_types = {"pt", "character", "aerospace", "leadership", "training", 
                         "ceremony", "meal", "admin", "recreation", "academics"}
        
        # At least these core types should be present
        core_types = {"meal", "pt", "training", "ceremony", "admin"}
        for t in core_types:
            assert t in event_types, f"Missing core event type: {t}"
        
        # New types should be present
        assert "aerospace" in event_types, "Missing aerospace event type"
        assert "character" in event_types, "Missing character event type"
        
        print(f"✓ Event types found: {sorted(event_types)}")
    
    def test_reimport_replaces_schedule(self):
        """Test that re-importing replaces existing schedule (idempotent)"""
        # First import
        with open(EXCEL_FILE_PATH, 'rb') as f:
            files = {'file': ('schedule.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            headers = {"Authorization": f"Bearer {self.token}"}
            response1 = requests.post(f"{BASE_URL}/api/schedule/import", files=files, headers=headers)
        
        assert response1.status_code == 200
        count1 = response1.json()["imported_count"]
        
        # Get events after first import
        response = self.session.get(f"{BASE_URL}/api/schedule")
        events_after_first = len(response.json())
        
        # Second import (should replace, not add)
        with open(EXCEL_FILE_PATH, 'rb') as f:
            files = {'file': ('schedule.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            headers = {"Authorization": f"Bearer {self.token}"}
            response2 = requests.post(f"{BASE_URL}/api/schedule/import", files=files, headers=headers)
        
        assert response2.status_code == 200
        count2 = response2.json()["imported_count"]
        
        # Get events after second import
        response = self.session.get(f"{BASE_URL}/api/schedule")
        events_after_second = len(response.json())
        
        # Counts should be similar (idempotent)
        assert count1 == count2, f"Import counts differ: {count1} vs {count2}"
        assert events_after_first == events_after_second, f"Event counts differ after reimport: {events_after_first} vs {events_after_second}"
        
        print(f"✓ Re-import is idempotent: {count1} events both times")
    
    def test_non_excel_file_returns_400(self):
        """Test that non-Excel file upload returns 400 error"""
        # Create a fake text file
        fake_content = b"This is not an Excel file"
        files = {'file': ('schedule.txt', fake_content, 'text/plain')}
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.post(f"{BASE_URL}/api/schedule/import", files=files, headers=headers)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "Excel" in response.json().get("detail", ""), "Error message should mention Excel"
        
        print("✓ Non-Excel file correctly rejected with 400")
    
    def test_schedule_in_draft_mode_after_import(self):
        """Verify schedule is in draft mode after import"""
        # Import first
        with open(EXCEL_FILE_PATH, 'rb') as f:
            files = {'file': ('schedule.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(f"{BASE_URL}/api/schedule/import", files=files, headers=headers)
        
        assert response.status_code == 200
        
        # Check settings
        response = self.session.get(f"{BASE_URL}/api/schedule/settings")
        assert response.status_code == 200
        
        settings = response.json()
        assert settings.get("is_published") == False, "Schedule should be in draft mode after import"
        
        print("✓ Schedule is in draft mode after import")
    
    def test_events_have_required_fields(self):
        """Verify imported events have all required fields"""
        response = self.session.get(f"{BASE_URL}/api/schedule")
        assert response.status_code == 200
        
        events = response.json()
        assert len(events) > 0
        
        required_fields = ["id", "title", "date", "start_time", "end_time", "event_type"]
        
        for event in events[:10]:  # Check first 10 events
            for field in required_fields:
                assert field in event, f"Missing field '{field}' in event: {event.get('title', 'unknown')}"
            
            # Validate time format (HH:MM)
            assert len(event["start_time"]) >= 5, f"Invalid start_time format: {event['start_time']}"
            assert len(event["end_time"]) >= 5, f"Invalid end_time format: {event['end_time']}"
        
        print("✓ All events have required fields with valid formats")
    
    def test_unauthorized_import_rejected(self):
        """Test that import without auth is rejected"""
        with open(EXCEL_FILE_PATH, 'rb') as f:
            files = {'file': ('schedule.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            # No auth header
            response = requests.post(f"{BASE_URL}/api/schedule/import", files=files)
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Unauthorized import correctly rejected")


class TestScheduleEventTypes:
    """Test event type dropdown includes new categories"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as commander"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        self.token = data.get("access_token") or data.get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        yield
        self.session.close()
    
    def test_create_aerospace_event(self):
        """Test creating an event with aerospace type"""
        event_data = {
            "title": "TEST_Aerospace_Event",
            "description": "Test aerospace event",
            "date": "2026-07-18",
            "start_time": "10:00",
            "end_time": "11:00",
            "location": "Hangar",
            "event_type": "aerospace",
            "target_groups": ["all"]
        }
        
        response = self.session.post(f"{BASE_URL}/api/schedule", json=event_data)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        created = response.json()
        assert created["event_type"] == "aerospace"
        assert created["title"] == "TEST_Aerospace_Event"
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/schedule/{created['id']}")
        print("✓ Created aerospace event successfully")
    
    def test_create_character_event(self):
        """Test creating an event with character type"""
        event_data = {
            "title": "TEST_Character_Event",
            "description": "Test character event",
            "date": "2026-07-19",
            "start_time": "14:00",
            "end_time": "15:00",
            "location": "Chapel",
            "event_type": "character",
            "target_groups": ["all"]
        }
        
        response = self.session.post(f"{BASE_URL}/api/schedule", json=event_data)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        created = response.json()
        assert created["event_type"] == "character"
        assert created["title"] == "TEST_Character_Event"
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/schedule/{created['id']}")
        print("✓ Created character event successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
