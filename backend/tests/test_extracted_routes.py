"""
Test suite for extracted route modules:
- notifications.py - In-app notification system
- training.py - Training officer routes (blister checks, counseling, cadre issues)
- checkin.py - Check-in system routes
- barracks.py - Barracks/bunk assignment routes
- schedule_changes.py - Schedule change request routes
- health_alerts.py - Health alerts routes
"""
import pytest
import requests
import os
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Test authentication and get token for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_login_success(self):
        """Test login with commander credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        print(f"Login successful, user role: {data['user'].get('role')}")


class TestNotificationRoutes:
    """Test notification system routes from notifications.py"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    def test_get_notifications(self, auth_headers):
        """GET /api/notifications - Get user notifications"""
        response = requests.get(f"{BASE_URL}/api/notifications", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} notifications")
    
    def test_get_unread_count(self, auth_headers):
        """GET /api/notifications/unread-count - Get unread count"""
        response = requests.get(f"{BASE_URL}/api/notifications/unread-count", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)
        print(f"Unread count: {data['count']}")
    
    def test_send_notification(self, auth_headers):
        """POST /api/notifications/send - Send notification (admin only)"""
        response = requests.post(f"{BASE_URL}/api/notifications/send", json={
            "title": "Test Notification",
            "message": "This is a test notification from pytest",
            "type": "info",
            "target_roles": ["all"]
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "notification_id" in data
        assert "recipients_count" in data
        print(f"Sent notification to {data['recipients_count']} recipients")
    
    def test_get_notification_preferences(self, auth_headers):
        """GET /api/notifications/preferences - Get user preferences"""
        response = requests.get(f"{BASE_URL}/api/notifications/preferences", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "email_enabled" in data or "user_id" in data
        print(f"Notification preferences: {data}")
    
    def test_mark_all_read(self, auth_headers):
        """PUT /api/notifications/read-all - Mark all as read"""
        response = requests.put(f"{BASE_URL}/api/notifications/read-all", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"Mark all read result: {data}")


class TestTrainingRoutes:
    """Test training officer routes from training.py"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    def test_get_training_summary(self, auth_headers):
        """GET /api/training/summary - Get training dashboard summary"""
        response = requests.get(f"{BASE_URL}/api/training/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "blister_checks_today" in data
        assert "counseling_today" in data
        assert "cadre_issues_open" in data
        print(f"Training summary: {data}")
    
    def test_get_blister_checks(self, auth_headers):
        """GET /api/training/blister-checks - Get blister checks"""
        response = requests.get(f"{BASE_URL}/api/training/blister-checks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} blister checks")
    
    def test_create_blister_check(self, auth_headers):
        """POST /api/training/blister-checks - Create blister check"""
        response = requests.post(f"{BASE_URL}/api/training/blister-checks", json={
            "cadet_name": "Test Cadet",
            "capid": "123456",
            "flight": "alpha",
            "squadron": "6th_cts",
            "severity": "mild",
            "location": "left heel",
            "description": "Small blister from marching",
            "treatment_given": "Moleskin applied",
            "follow_up_needed": False
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["cadet_name"] == "Test Cadet"
        print(f"Created blister check: {data['id']}")
    
    def test_get_counseling_logs(self, auth_headers):
        """GET /api/training/counseling-logs - Get counseling logs"""
        response = requests.get(f"{BASE_URL}/api/training/counseling-logs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} counseling logs")
    
    def test_get_cadre_issues(self, auth_headers):
        """GET /api/training/cadre-issues - Get cadre issues"""
        response = requests.get(f"{BASE_URL}/api/training/cadre-issues", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} cadre issues")


class TestCheckInRoutes:
    """Test check-in system routes from checkin.py"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    def test_get_check_in_roster(self, auth_headers):
        """GET /api/check-in/roster - Get check-in roster"""
        response = requests.get(f"{BASE_URL}/api/check-in/roster", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "participant_id" in data[0]
            assert "steps" in data[0]
            assert "completed_steps" in data[0]
        print(f"Found {len(data)} participants in check-in roster")
    
    def test_get_check_in_summary(self, auth_headers):
        """GET /api/check-in/summary - Get check-in summary stats"""
        response = requests.get(f"{BASE_URL}/api/check-in/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_participants" in data
        assert "fully_checked_in" in data
        assert "step_counts" in data
        print(f"Check-in summary: {data['fully_checked_in']}/{data['total_participants']} fully checked in")
    
    def test_check_in_step_with_participant(self, auth_headers):
        """POST /api/check-in/{id}/step - Check-in a participant for a step"""
        # First get a participant
        roster_response = requests.get(f"{BASE_URL}/api/check-in/roster", headers=auth_headers)
        assert roster_response.status_code == 200
        roster = roster_response.json()
        
        if len(roster) > 0:
            participant_id = roster[0]["participant_id"]
            response = requests.post(f"{BASE_URL}/api/check-in/{participant_id}/step", json={
                "step": "arrival",
                "notes": "Test check-in from pytest"
            }, headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            print(f"Checked in participant {participant_id} for arrival step")
        else:
            pytest.skip("No participants available for check-in test")


class TestBarracksRoutes:
    """Test barracks/bunk assignment routes from barracks.py"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    def test_get_barracks(self, auth_headers):
        """GET /api/barracks - Get all barracks with occupancy"""
        response = requests.get(f"{BASE_URL}/api/barracks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "barracks_id" in data[0]
        assert "capacity" in data[0]
        assert "assigned" in data[0]
        print(f"Found {len(data)} barracks")
    
    def test_get_barracks_detail(self, auth_headers):
        """GET /api/barracks/{id} - Get barracks detail with bunks"""
        response = requests.get(f"{BASE_URL}/api/barracks/TR-142B", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "barracks_id" in data
        assert "bunks" in data
        assert isinstance(data["bunks"], list)
        print(f"Barracks TR-142B has {len(data['bunks'])} bunks, {data['assigned']} assigned")
    
    def test_get_unassigned_participants(self, auth_headers):
        """GET /api/barracks/unassigned-participants - Get unassigned participants"""
        response = requests.get(f"{BASE_URL}/api/barracks/unassigned-participants", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} unassigned participants")
    
    def test_get_facility_buildings(self, auth_headers):
        """GET /api/facility/buildings - Get all facility buildings"""
        response = requests.get(f"{BASE_URL}/api/facility/buildings", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "id" in data[0]
        assert "type" in data[0]
        print(f"Found {len(data)} facility buildings")


class TestScheduleChangesRoutes:
    """Test schedule change request routes from schedule_changes.py"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    def test_get_schedule_changes(self, auth_headers):
        """GET /api/schedule-changes - Get schedule change requests"""
        response = requests.get(f"{BASE_URL}/api/schedule-changes", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} schedule change requests")
    
    def test_get_pending_count(self, auth_headers):
        """GET /api/schedule-changes/pending-count - Get pending count"""
        response = requests.get(f"{BASE_URL}/api/schedule-changes/pending-count", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        print(f"Pending schedule changes: {data['count']}")
    
    def test_submit_schedule_change(self, auth_headers):
        """POST /api/schedule-changes - Submit a schedule change request"""
        response = requests.post(f"{BASE_URL}/api/schedule-changes", json={
            "change_type": "modify",
            "event_title": "Test Event",
            "event_date": "2026-01-15",
            "current_time": "09:00",
            "requested_time": "10:00",
            "reason": "Testing schedule change submission"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"
        print(f"Created schedule change request: {data['id']}")


class TestHealthAlertsRoutes:
    """Test health alerts routes from health_alerts.py"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    def test_get_health_alerts(self, auth_headers):
        """GET /api/health-alerts/{id} - Get health alerts for a member"""
        response = requests.get(f"{BASE_URL}/api/health-alerts/test-member-id", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "member_id" in data
        assert "alerts" in data
        print(f"Health alerts response: {data}")
    
    def test_update_health_alerts(self, auth_headers):
        """PUT /api/health-alerts/{id} - Update health alerts"""
        response = requests.put(f"{BASE_URL}/api/health-alerts/test-member-id", json={
            "alerts": [
                {"type": "asthma", "shared_with": ["flight_commander"]}
            ],
            "notes": "Test health alert",
            "shared_notes": "Shared test note"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"Update health alerts result: {data}")


class TestDashboardAndCore:
    """Test core dashboard and auth endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    def test_get_dashboard_stats(self, auth_headers):
        """GET /api/stats/dashboard - Get dashboard stats"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        print(f"Dashboard stats: {data}")
    
    def test_get_dashboard_quickview(self, auth_headers):
        """GET /api/stats/dashboard-quickview - Get dashboard quickview"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        print(f"Dashboard quickview: {data}")
    
    def test_get_auth_me(self, auth_headers):
        """GET /api/auth/me - Get current user"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        print(f"Current user: {data.get('email')}, role: {data.get('role')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
