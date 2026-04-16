"""
Test Parent Portal Admin Feature
- GET /api/parent/portal-config returns default widget configuration
- PUT /api/parent/portal-config saves widget config (admin only)
- GET /api/parent/admin-preview/participants returns list of participants
- GET /api/parent/admin-preview/{participant_id} returns cadet data
- GET /api/parent/admin-preview/{participant_id}/schedule returns schedule events
"""
import pytest
import requests
import os

from tests.conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, PARENT_EMAIL, PARENT_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials


class TestParentPortalAdmin:
    """Test Parent Portal Admin endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login_as_commander(self):
        """Login as commander and return session with cookies"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": COMMANDER_EMAIL, "password": COMMANDER_PASSWORD}
        )
        assert response.status_code == 200, f"Commander login failed: {response.text}"
        return self.session
    
    def login_as_parent(self):
        """Login as parent and return session with cookies"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PARENT_EMAIL, "password": PARENT_PASSWORD}
        )
        assert response.status_code == 200, f"Parent login failed: {response.text}"
        return self.session
    
    # ============ GET /api/parent/portal-config ============
    
    def test_portal_config_requires_auth(self):
        """Portal config endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/parent/portal-config")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_portal_config_returns_default_widgets(self):
        """GET /api/parent/portal-config returns default widget configuration"""
        self.login_as_commander()
        response = self.session.get(f"{BASE_URL}/api/parent/portal-config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "widgets" in data or "type" in data, f"Response missing widgets: {data}"
        
        # Check default widgets exist
        widgets = data.get("widgets", data)
        expected_widgets = ["overview", "schedule", "health", "points", "meals", "otc_form"]
        for widget in expected_widgets:
            if widget in widgets:
                assert "visible" in widgets[widget], f"Widget {widget} missing 'visible' field"
                assert "size" in widgets[widget], f"Widget {widget} missing 'size' field"
                assert "order" in widgets[widget], f"Widget {widget} missing 'order' field"
    
    def test_portal_config_accessible_by_parent(self):
        """Parents can also access portal config (to see layout)"""
        self.login_as_parent()
        response = self.session.get(f"{BASE_URL}/api/parent/portal-config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    # ============ PUT /api/parent/portal-config ============
    
    def test_update_portal_config_admin_only(self):
        """PUT /api/parent/portal-config requires admin role"""
        self.login_as_parent()
        response = self.session.put(
            f"{BASE_URL}/api/parent/portal-config",
            json={"widgets": {"overview": {"visible": True, "size": "full", "order": 0}}}
        )
        assert response.status_code == 403, f"Expected 403 for parent, got {response.status_code}: {response.text}"
    
    def test_update_portal_config_as_commander(self):
        """Commander can update portal config"""
        self.login_as_commander()
        
        # Update config
        new_config = {
            "widgets": {
                "overview": {"visible": True, "size": "full", "order": 0},
                "schedule": {"visible": True, "size": "half", "order": 1},
                "health": {"visible": False, "size": "third", "order": 2},
                "points": {"visible": True, "size": "half", "order": 3},
                "meals": {"visible": True, "size": "full", "order": 4},
                "otc_form": {"visible": True, "size": "full", "order": 5}
            }
        }
        response = self.session.put(
            f"{BASE_URL}/api/parent/portal-config",
            json=new_config
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify config was saved
        get_response = self.session.get(f"{BASE_URL}/api/parent/portal-config")
        assert get_response.status_code == 200
        saved_data = get_response.json()
        widgets = saved_data.get("widgets", {})
        
        # Check schedule size was changed to half
        if "schedule" in widgets:
            assert widgets["schedule"]["size"] == "half", f"Schedule size not updated: {widgets['schedule']}"
        
        # Check health visibility was changed to False
        if "health" in widgets:
            assert widgets["health"]["visible"] == False, f"Health visibility not updated: {widgets['health']}"
    
    # ============ GET /api/parent/admin-preview/participants ============
    
    def test_admin_preview_participants_requires_auth(self):
        """Admin preview participants requires authentication"""
        response = requests.get(f"{BASE_URL}/api/parent/admin-preview/participants")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_admin_preview_participants_admin_only(self):
        """Admin preview participants requires admin role"""
        self.login_as_parent()
        response = self.session.get(f"{BASE_URL}/api/parent/admin-preview/participants")
        assert response.status_code == 403, f"Expected 403 for parent, got {response.status_code}: {response.text}"
    
    def test_admin_preview_participants_returns_list(self):
        """GET /api/parent/admin-preview/participants returns list of participants"""
        self.login_as_commander()
        response = self.session.get(f"{BASE_URL}/api/parent/admin-preview/participants")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        
        # Check participant structure if any exist
        if len(data) > 0:
            participant = data[0]
            assert "id" in participant, f"Participant missing 'id': {participant}"
            assert "first_name" in participant, f"Participant missing 'first_name': {participant}"
            assert "last_name" in participant, f"Participant missing 'last_name': {participant}"
    
    # ============ GET /api/parent/admin-preview/{participant_id} ============
    
    def test_admin_preview_cadet_requires_auth(self):
        """Admin preview cadet requires authentication"""
        response = requests.get(f"{BASE_URL}/api/parent/admin-preview/test-id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_admin_preview_cadet_admin_only(self):
        """Admin preview cadet requires admin role"""
        self.login_as_parent()
        response = self.session.get(f"{BASE_URL}/api/parent/admin-preview/test-id")
        assert response.status_code == 403, f"Expected 403 for parent, got {response.status_code}: {response.text}"
    
    def test_admin_preview_cadet_returns_data(self):
        """GET /api/parent/admin-preview/{participant_id} returns cadet data"""
        self.login_as_commander()
        
        # First get a participant ID
        participants_response = self.session.get(f"{BASE_URL}/api/parent/admin-preview/participants")
        assert participants_response.status_code == 200
        participants = participants_response.json()
        
        if len(participants) == 0:
            pytest.skip("No participants available for testing")
        
        participant_id = participants[0]["id"]
        
        # Get cadet preview data
        response = self.session.get(f"{BASE_URL}/api/parent/admin-preview/{participant_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "first_name" in data, f"Cadet data missing 'first_name': {data}"
        assert "last_name" in data, f"Cadet data missing 'last_name': {data}"
    
    def test_admin_preview_cadet_not_found(self):
        """Admin preview returns 404 for non-existent participant"""
        self.login_as_commander()
        response = self.session.get(f"{BASE_URL}/api/parent/admin-preview/non-existent-id-12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
    
    # ============ GET /api/parent/admin-preview/{participant_id}/schedule ============
    
    def test_admin_preview_schedule_requires_auth(self):
        """Admin preview schedule requires authentication"""
        response = requests.get(f"{BASE_URL}/api/parent/admin-preview/test-id/schedule")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_admin_preview_schedule_admin_only(self):
        """Admin preview schedule requires admin role"""
        self.login_as_parent()
        response = self.session.get(f"{BASE_URL}/api/parent/admin-preview/test-id/schedule")
        assert response.status_code == 403, f"Expected 403 for parent, got {response.status_code}: {response.text}"
    
    def test_admin_preview_schedule_returns_events(self):
        """GET /api/parent/admin-preview/{participant_id}/schedule returns schedule events"""
        self.login_as_commander()
        
        # First get a participant ID
        participants_response = self.session.get(f"{BASE_URL}/api/parent/admin-preview/participants")
        assert participants_response.status_code == 200
        participants = participants_response.json()
        
        if len(participants) == 0:
            pytest.skip("No participants available for testing")
        
        participant_id = participants[0]["id"]
        
        # Get schedule preview
        response = self.session.get(f"{BASE_URL}/api/parent/admin-preview/{participant_id}/schedule")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
    
    # ============ Additional admin preview endpoints ============
    
    def test_admin_preview_health_returns_data(self):
        """GET /api/parent/admin-preview/{participant_id}/health returns health incidents"""
        self.login_as_commander()
        
        participants_response = self.session.get(f"{BASE_URL}/api/parent/admin-preview/participants")
        participants = participants_response.json()
        
        if len(participants) == 0:
            pytest.skip("No participants available for testing")
        
        participant_id = participants[0]["id"]
        
        response = self.session.get(f"{BASE_URL}/api/parent/admin-preview/{participant_id}/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
    
    def test_admin_preview_points_returns_data(self):
        """GET /api/parent/admin-preview/{participant_id}/points returns points data"""
        self.login_as_commander()
        
        participants_response = self.session.get(f"{BASE_URL}/api/parent/admin-preview/participants")
        participants = participants_response.json()
        
        if len(participants) == 0:
            pytest.skip("No participants available for testing")
        
        participant_id = participants[0]["id"]
        
        response = self.session.get(f"{BASE_URL}/api/parent/admin-preview/{participant_id}/points")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
    
    def test_admin_preview_meals_returns_data(self):
        """GET /api/parent/admin-preview/{participant_id}/meals returns meal plans"""
        self.login_as_commander()
        
        participants_response = self.session.get(f"{BASE_URL}/api/parent/admin-preview/participants")
        participants = participants_response.json()
        
        if len(participants) == 0:
            pytest.skip("No participants available for testing")
        
        participant_id = participants[0]["id"]
        
        response = self.session.get(f"{BASE_URL}/api/parent/admin-preview/{participant_id}/meals")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"


class TestParentPortalConfigSizes:
    """Test widget size configurations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login as commander
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": COMMANDER_EMAIL, "password": COMMANDER_PASSWORD}
        )
        assert response.status_code == 200, f"Commander login failed: {response.text}"
    
    def test_widget_size_third(self):
        """Widget can be set to 1/3 width (third)"""
        config = {
            "widgets": {
                "overview": {"visible": True, "size": "third", "order": 0},
                "schedule": {"visible": True, "size": "full", "order": 1},
                "health": {"visible": True, "size": "half", "order": 2},
                "points": {"visible": True, "size": "half", "order": 3},
                "meals": {"visible": True, "size": "full", "order": 4},
                "otc_form": {"visible": True, "size": "full", "order": 5}
            }
        }
        response = self.session.put(f"{BASE_URL}/api/parent/portal-config", json=config)
        assert response.status_code == 200, f"Failed to save config: {response.text}"
        
        # Verify
        get_response = self.session.get(f"{BASE_URL}/api/parent/portal-config")
        saved = get_response.json()
        assert saved["widgets"]["overview"]["size"] == "third"
    
    def test_widget_size_half(self):
        """Widget can be set to 1/2 width (half)"""
        config = {
            "widgets": {
                "overview": {"visible": True, "size": "half", "order": 0},
                "schedule": {"visible": True, "size": "full", "order": 1},
                "health": {"visible": True, "size": "half", "order": 2},
                "points": {"visible": True, "size": "half", "order": 3},
                "meals": {"visible": True, "size": "full", "order": 4},
                "otc_form": {"visible": True, "size": "full", "order": 5}
            }
        }
        response = self.session.put(f"{BASE_URL}/api/parent/portal-config", json=config)
        assert response.status_code == 200, f"Failed to save config: {response.text}"
        
        # Verify
        get_response = self.session.get(f"{BASE_URL}/api/parent/portal-config")
        saved = get_response.json()
        assert saved["widgets"]["overview"]["size"] == "half"
    
    def test_widget_size_full(self):
        """Widget can be set to full width"""
        config = {
            "widgets": {
                "overview": {"visible": True, "size": "full", "order": 0},
                "schedule": {"visible": True, "size": "full", "order": 1},
                "health": {"visible": True, "size": "half", "order": 2},
                "points": {"visible": True, "size": "half", "order": 3},
                "meals": {"visible": True, "size": "full", "order": 4},
                "otc_form": {"visible": True, "size": "full", "order": 5}
            }
        }
        response = self.session.put(f"{BASE_URL}/api/parent/portal-config", json=config)
        assert response.status_code == 200, f"Failed to save config: {response.text}"
        
        # Verify
        get_response = self.session.get(f"{BASE_URL}/api/parent/portal-config")
        saved = get_response.json()
        assert saved["widgets"]["overview"]["size"] == "full"
    
    def test_widget_visibility_toggle(self):
        """Widget visibility can be toggled"""
        # Set health to hidden
        config = {
            "widgets": {
                "overview": {"visible": True, "size": "full", "order": 0},
                "schedule": {"visible": True, "size": "full", "order": 1},
                "health": {"visible": False, "size": "half", "order": 2},
                "points": {"visible": True, "size": "half", "order": 3},
                "meals": {"visible": True, "size": "full", "order": 4},
                "otc_form": {"visible": True, "size": "full", "order": 5}
            }
        }
        response = self.session.put(f"{BASE_URL}/api/parent/portal-config", json=config)
        assert response.status_code == 200
        
        # Verify health is hidden
        get_response = self.session.get(f"{BASE_URL}/api/parent/portal-config")
        saved = get_response.json()
        assert saved["widgets"]["health"]["visible"] == False
    
    def test_widget_reorder(self):
        """Widget order can be changed"""
        # Move schedule to position 0, overview to position 1
        config = {
            "widgets": {
                "overview": {"visible": True, "size": "full", "order": 1},
                "schedule": {"visible": True, "size": "full", "order": 0},
                "health": {"visible": True, "size": "half", "order": 2},
                "points": {"visible": True, "size": "half", "order": 3},
                "meals": {"visible": True, "size": "full", "order": 4},
                "otc_form": {"visible": True, "size": "full", "order": 5}
            }
        }
        response = self.session.put(f"{BASE_URL}/api/parent/portal-config", json=config)
        assert response.status_code == 200
        
        # Verify order
        get_response = self.session.get(f"{BASE_URL}/api/parent/portal-config")
        saved = get_response.json()
        assert saved["widgets"]["schedule"]["order"] == 0
        assert saved["widgets"]["overview"]["order"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
