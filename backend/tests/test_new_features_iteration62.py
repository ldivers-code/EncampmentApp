"""
Test Suite for Iteration 62 - 3 New Features:
1. Daily Med Diary (Health Services)
2. Supplement List (Health Services)
3. Contraband Logging (Check-In / Logistics)
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
COMMANDER_EMAIL = "commander@test.com"
COMMANDER_PASSWORD = "test123"
PARENT_EMAIL = "jane.hundley@test.com"
PARENT_PASSWORD = "parent123"


@pytest.fixture(scope="module")
def commander_session():
    """Authenticated session for commander user"""
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": COMMANDER_EMAIL,
        "password": COMMANDER_PASSWORD
    })
    assert resp.status_code == 200, f"Commander login failed: {resp.text}"
    return session


@pytest.fixture(scope="module")
def parent_session():
    """Authenticated session for parent user"""
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": PARENT_EMAIL,
        "password": PARENT_PASSWORD
    })
    assert resp.status_code == 200, f"Parent login failed: {resp.text}"
    return session


@pytest.fixture(scope="module")
def test_participant_id(commander_session):
    """Get a participant ID for testing"""
    resp = commander_session.get(f"{BASE_URL}/api/participants")
    assert resp.status_code == 200
    participants = resp.json()
    # Find a basic_student or cadre participant
    for p in participants:
        if p.get("participant_type") in ["basic_student", "cadre"]:
            return p["id"]
    # Fallback to first participant
    if participants:
        return participants[0]["id"]
    pytest.skip("No participants found for testing")


# ==================== MED DIARY TESTS ====================

class TestMedDiary:
    """Tests for Daily Medication Diary feature"""
    
    def test_get_all_med_diary_empty_or_existing(self, commander_session):
        """GET /api/health/med-diary returns diary entries"""
        resp = commander_session.get(f"{BASE_URL}/api/health/med-diary")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print(f"Med diary entries count: {len(data)}")
    
    def test_get_med_diary_with_date_filter(self, commander_session):
        """GET /api/health/med-diary with date filter"""
        today = datetime.now().strftime("%Y-%m-%d")
        resp = commander_session.get(f"{BASE_URL}/api/health/med-diary?date={today}")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print(f"Med diary entries for {today}: {len(data)}")
    
    def test_create_med_diary_entry(self, commander_session, test_participant_id):
        """POST /api/health/cadet/{id}/med-diary creates entry"""
        entry_data = {
            "medication_name": "TEST_Ibuprofen",
            "dosage": "200mg",
            "notes": "Test entry from pytest"
        }
        resp = commander_session.post(
            f"{BASE_URL}/api/health/cadet/{test_participant_id}/med-diary",
            json=entry_data
        )
        assert resp.status_code == 200, f"Failed to create med diary entry: {resp.text}"
        data = resp.json()
        assert "id" in data
        assert data["medication_name"] == "TEST_Ibuprofen"
        assert data["dosage"] == "200mg"
        assert data["participant_id"] == test_participant_id
        assert "administered_by" in data
        assert "administered_at" in data
        print(f"Created med diary entry: {data['id']}")
        return data["id"]
    
    def test_get_cadet_med_diary(self, commander_session, test_participant_id):
        """GET /api/health/cadet/{id}/med-diary returns entries for specific cadet"""
        resp = commander_session.get(f"{BASE_URL}/api/health/cadet/{test_participant_id}/med-diary")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print(f"Cadet med diary entries: {len(data)}")
    
    def test_delete_med_diary_entry(self, commander_session, test_participant_id):
        """DELETE /api/health/med-diary/{id} removes entry"""
        # First create an entry to delete
        entry_data = {
            "medication_name": "TEST_ToDelete",
            "dosage": "100mg"
        }
        create_resp = commander_session.post(
            f"{BASE_URL}/api/health/cadet/{test_participant_id}/med-diary",
            json=entry_data
        )
        assert create_resp.status_code == 200
        entry_id = create_resp.json()["id"]
        
        # Now delete it
        delete_resp = commander_session.delete(f"{BASE_URL}/api/health/med-diary/{entry_id}")
        assert delete_resp.status_code == 200
        
        # Verify it's gone
        get_resp = commander_session.get(f"{BASE_URL}/api/health/cadet/{test_participant_id}/med-diary")
        entries = get_resp.json()
        assert not any(e["id"] == entry_id for e in entries), "Entry should be deleted"
        print(f"Successfully deleted med diary entry: {entry_id}")
    
    def test_parent_can_view_med_diary(self, parent_session):
        """GET /api/parent/my-cadet/med-diary returns med diary for parent's cadet"""
        resp = parent_session.get(f"{BASE_URL}/api/parent/my-cadet/med-diary")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print(f"Parent can see {len(data)} med diary entries for their cadet")


# ==================== SUPPLEMENTS TESTS ====================

class TestSupplements:
    """Tests for Supplement List feature"""
    
    def test_get_cadet_supplements_empty_or_existing(self, commander_session, test_participant_id):
        """GET /api/health/cadet/{id}/supplements returns supplement list"""
        resp = commander_session.get(f"{BASE_URL}/api/health/cadet/{test_participant_id}/supplements")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print(f"Cadet supplements count: {len(data)}")
    
    def test_create_supplement(self, commander_session, test_participant_id):
        """POST /api/health/cadet/{id}/supplements creates a supplement"""
        supplement_data = {
            "name": "TEST_Vitamin D",
            "dosage": "1000 IU",
            "frequency": "daily",
            "notes": "Test supplement from pytest"
        }
        resp = commander_session.post(
            f"{BASE_URL}/api/health/cadet/{test_participant_id}/supplements",
            json=supplement_data
        )
        assert resp.status_code == 200, f"Failed to create supplement: {resp.text}"
        data = resp.json()
        assert "id" in data
        assert data["name"] == "TEST_Vitamin D"
        assert data["dosage"] == "1000 IU"
        assert data["frequency"] == "daily"
        assert data["participant_id"] == test_participant_id
        print(f"Created supplement: {data['id']}")
        return data["id"]
    
    def test_delete_supplement(self, commander_session, test_participant_id):
        """DELETE /api/health/supplements/{id} removes supplement"""
        # First create a supplement to delete
        supplement_data = {
            "name": "TEST_ToDelete_Supplement",
            "dosage": "500mg"
        }
        create_resp = commander_session.post(
            f"{BASE_URL}/api/health/cadet/{test_participant_id}/supplements",
            json=supplement_data
        )
        assert create_resp.status_code == 200
        supplement_id = create_resp.json()["id"]
        
        # Now delete it
        delete_resp = commander_session.delete(f"{BASE_URL}/api/health/supplements/{supplement_id}")
        assert delete_resp.status_code == 200
        
        # Verify it's gone
        get_resp = commander_session.get(f"{BASE_URL}/api/health/cadet/{test_participant_id}/supplements")
        supplements = get_resp.json()
        assert not any(s["id"] == supplement_id for s in supplements), "Supplement should be deleted"
        print(f"Successfully deleted supplement: {supplement_id}")


# ==================== CONTRABAND TESTS ====================

class TestContraband:
    """Tests for Contraband Logging feature"""
    
    def test_get_participant_contraband_empty_or_existing(self, commander_session, test_participant_id):
        """GET /api/check-in/{id}/contraband returns contraband items for participant"""
        resp = commander_session.get(f"{BASE_URL}/api/check-in/{test_participant_id}/contraband")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print(f"Participant contraband items: {len(data)}")
    
    def test_create_contraband(self, commander_session, test_participant_id):
        """POST /api/check-in/{id}/contraband creates a contraband item"""
        contraband_data = {
            "item_name": "TEST_Cell Phone",
            "category": "electronics",
            "storage_location": "Logistics Office Locker 5",
            "description": "iPhone 15 Pro",
            "notes": "Test contraband from pytest"
        }
        resp = commander_session.post(
            f"{BASE_URL}/api/check-in/{test_participant_id}/contraband",
            json=contraband_data
        )
        assert resp.status_code == 200, f"Failed to create contraband: {resp.text}"
        data = resp.json()
        assert "id" in data
        assert data["item_name"] == "TEST_Cell Phone"
        assert data["category"] == "electronics"
        assert data["storage_location"] == "Logistics Office Locker 5"
        assert data["participant_id"] == test_participant_id
        assert data["returned"] == False
        assert "confiscated_by" in data
        assert "confiscated_at" in data
        print(f"Created contraband item: {data['id']}")
        return data["id"]
    
    def test_return_contraband(self, commander_session, test_participant_id):
        """PUT /api/check-in/contraband/{id}/return marks contraband as returned"""
        # First create a contraband item
        contraband_data = {
            "item_name": "TEST_ToReturn_Item",
            "category": "other",
            "storage_location": "Test Location"
        }
        create_resp = commander_session.post(
            f"{BASE_URL}/api/check-in/{test_participant_id}/contraband",
            json=contraband_data
        )
        assert create_resp.status_code == 200
        item_id = create_resp.json()["id"]
        
        # Now mark it as returned
        return_data = {
            "returned_to": "Cadet Smith",
            "notes": "Returned at end of encampment"
        }
        return_resp = commander_session.put(
            f"{BASE_URL}/api/check-in/contraband/{item_id}/return",
            json=return_data
        )
        assert return_resp.status_code == 200
        data = return_resp.json()
        assert data["returned"] == True
        assert data["returned_to"] == "Cadet Smith"
        assert "returned_at" in data
        print(f"Successfully marked contraband as returned: {item_id}")
    
    def test_get_all_contraband_logistics_view(self, commander_session):
        """GET /api/logistics/contraband returns all contraband with participant_name enrichment"""
        resp = commander_session.get(f"{BASE_URL}/api/logistics/contraband")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        print(f"Total contraband items in logistics view: {len(data)}")
        
        # Check that items have participant_name enrichment
        for item in data:
            if "participant_name" in item:
                print(f"  - {item['item_name']} belongs to {item['participant_name']}")
    
    def test_get_contraband_filtered_by_returned_status(self, commander_session):
        """GET /api/logistics/contraband?returned=false returns only unreturned items"""
        resp = commander_session.get(f"{BASE_URL}/api/logistics/contraband?returned=false")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # All items should have returned=False
        for item in data:
            assert item.get("returned") == False, f"Item {item['id']} should not be returned"
        print(f"Unreturned contraband items: {len(data)}")
    
    def test_delete_contraband(self, commander_session, test_participant_id):
        """DELETE /api/check-in/contraband/{id} removes contraband record"""
        # First create a contraband item to delete
        contraband_data = {
            "item_name": "TEST_ToDelete_Contraband",
            "category": "other"
        }
        create_resp = commander_session.post(
            f"{BASE_URL}/api/check-in/{test_participant_id}/contraband",
            json=contraband_data
        )
        assert create_resp.status_code == 200
        item_id = create_resp.json()["id"]
        
        # Now delete it
        delete_resp = commander_session.delete(f"{BASE_URL}/api/check-in/contraband/{item_id}")
        assert delete_resp.status_code == 200
        
        # Verify it's gone
        get_resp = commander_session.get(f"{BASE_URL}/api/check-in/{test_participant_id}/contraband")
        items = get_resp.json()
        assert not any(i["id"] == item_id for i in items), "Contraband should be deleted"
        print(f"Successfully deleted contraband: {item_id}")


# ==================== CLEANUP ====================

class TestCleanup:
    """Cleanup test data created during testing"""
    
    def test_cleanup_test_med_diary_entries(self, commander_session):
        """Remove TEST_ prefixed med diary entries"""
        resp = commander_session.get(f"{BASE_URL}/api/health/med-diary")
        if resp.status_code == 200:
            entries = resp.json()
            for entry in entries:
                if entry.get("medication_name", "").startswith("TEST_"):
                    commander_session.delete(f"{BASE_URL}/api/health/med-diary/{entry['id']}")
                    print(f"Cleaned up med diary entry: {entry['id']}")
    
    def test_cleanup_test_supplements(self, commander_session, test_participant_id):
        """Remove TEST_ prefixed supplements"""
        resp = commander_session.get(f"{BASE_URL}/api/health/cadet/{test_participant_id}/supplements")
        if resp.status_code == 200:
            supplements = resp.json()
            for sup in supplements:
                if sup.get("name", "").startswith("TEST_"):
                    commander_session.delete(f"{BASE_URL}/api/health/supplements/{sup['id']}")
                    print(f"Cleaned up supplement: {sup['id']}")
    
    def test_cleanup_test_contraband(self, commander_session, test_participant_id):
        """Remove TEST_ prefixed contraband items"""
        resp = commander_session.get(f"{BASE_URL}/api/check-in/{test_participant_id}/contraband")
        if resp.status_code == 200:
            items = resp.json()
            for item in items:
                if item.get("item_name", "").startswith("TEST_"):
                    commander_session.delete(f"{BASE_URL}/api/check-in/contraband/{item['id']}")
                    print(f"Cleaned up contraband: {item['id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
