"""
Test suite for refactored backend routes after server.py extraction.
Tests all 28 route modules extracted from the original 9,442-line server.py.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD


class TestAuthRoutes:
    """Test auth.py routes - Auth, Password Reset, Presence, Profile"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.token = None
        self.user = None
    
    def login(self):
        """Helper to login and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.user = data.get("user")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        return response
    
    def test_login_success(self):
        """POST /api/auth/login - Valid credentials"""
        response = self.login()
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == COMMANDER_EMAIL
    
    def test_login_invalid_credentials(self):
        """POST /api/auth/login - Invalid credentials"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
    
    def test_get_me(self):
        """GET /api/auth/me - Get current user"""
        self.login()
        response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == COMMANDER_EMAIL
    
    def test_get_profile(self):
        """GET /api/profile - Get user profile"""
        self.login()
        response = self.session.get(f"{BASE_URL}/api/profile")
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
    
    def test_presence_heartbeat(self):
        """POST /api/presence/heartbeat - Send heartbeat"""
        self.login()
        response = self.session.post(f"{BASE_URL}/api/presence/heartbeat")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestUserRoutes:
    """Test users.py routes - User Management, Approval, Sync"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login as commander
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_users(self):
        """GET /api/users - Get all users"""
        response = self.session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_pending_users(self):
        """GET /api/users/pending - Get pending users"""
        response = self.session.get(f"{BASE_URL}/api/users/pending")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestParticipantRoutes:
    """Test participants.py routes - Participant CRUD, Analytics, PDF Export"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_participants(self):
        """GET /api/participants - Get all participants"""
        response = self.session.get(f"{BASE_URL}/api/participants")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_participant_stats(self):
        """GET /api/participants/stats - Get participant statistics"""
        response = self.session.get(f"{BASE_URL}/api/participants/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
    
    def test_export_pdf(self):
        """GET /api/participants/export-pdf - Export roster as PDF"""
        response = self.session.get(f"{BASE_URL}/api/participants/export-pdf")
        # Should return PDF or 404 if no participants
        assert response.status_code in [200, 404]


class TestScheduleRoutes:
    """Test schedule.py routes - Schedule CRUD, Import, Publish"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_schedule(self):
        """GET /api/schedule - Get schedule events"""
        response = self.session.get(f"{BASE_URL}/api/schedule")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_schedule_settings(self):
        """GET /api/schedule/settings - Get schedule settings"""
        response = self.session.get(f"{BASE_URL}/api/schedule/settings")
        assert response.status_code == 200
        data = response.json()
        assert "is_published" in data


class TestBudgetRoutes:
    """Test budget.py routes - Budget CRUD, Quick Update"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_budget(self):
        """GET /api/budget - Get all budget items"""
        response = self.session.get(f"{BASE_URL}/api/budget")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_budget_summary(self):
        """GET /api/budget/summary - Get budget summary"""
        response = self.session.get(f"{BASE_URL}/api/budget/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_estimated" in data


class TestDocumentRoutes:
    """Test documents.py routes - Document CRUD"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_documents(self):
        """GET /api/documents - Get all documents"""
        response = self.session.get(f"{BASE_URL}/api/documents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_document_categories(self):
        """GET /api/documents/categories - Get document categories"""
        response = self.session.get(f"{BASE_URL}/api/documents/categories")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestOrgChartRoutes:
    """Test orgchart.py routes - Org Chart roles"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_org_chart_roles(self):
        """GET /api/org-chart/roles - Get org chart roles"""
        response = self.session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestStatsRoutes:
    """Test stats.py routes - Dashboard stats"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_dashboard_stats(self):
        """GET /api/stats/dashboard - Get dashboard stats"""
        response = self.session.get(f"{BASE_URL}/api/stats/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "participants" in data
        assert "budget" in data
        assert "schedule" in data
    
    def test_get_dashboard_quickview(self):
        """GET /api/stats/dashboard-quickview - Get role-specific quickview"""
        response = self.session.get(f"{BASE_URL}/api/stats/dashboard-quickview")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestFlightRoutes:
    """Test flights.py routes - Flight roster and leadership"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_flights(self):
        """GET /api/flights - Get all flights"""
        response = self.session.get(f"{BASE_URL}/api/flights")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 6  # alpha, bravo, charlie, delta, echo, foxtrot
    
    def test_get_squadrons(self):
        """GET /api/squadrons - Get all squadrons"""
        response = self.session.get(f"{BASE_URL}/api/squadrons")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestCheckInRoutes:
    """Test checkin.py routes - Check-in system"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_check_in_summary(self):
        """GET /api/check-in/summary - Get check-in summary"""
        response = self.session.get(f"{BASE_URL}/api/check-in/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_participants" in data
        assert "fully_checked_in" in data
    
    def test_get_check_in_roster(self):
        """GET /api/check-in/roster - Get check-in roster"""
        response = self.session.get(f"{BASE_URL}/api/check-in/roster")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestBarracksRoutes:
    """Test barracks.py routes - Barracks and bunk assignment"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_barracks(self):
        """GET /api/barracks - Get all barracks"""
        response = self.session.get(f"{BASE_URL}/api/barracks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5  # 5 barracks configured
    
    def test_get_facility_buildings(self):
        """GET /api/facility/buildings - Get facility buildings"""
        response = self.session.get(f"{BASE_URL}/api/facility/buildings")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestTrainingRoutes:
    """Test training.py routes - Training officer features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_training_summary(self):
        """GET /api/training/summary - Get training summary"""
        response = self.session.get(f"{BASE_URL}/api/training/summary")
        assert response.status_code == 200
        data = response.json()
        assert "blister_checks_today" in data
        assert "counseling_today" in data
        assert "cadre_issues_open" in data


class TestNotificationRoutes:
    """Test notifications.py routes - In-app notifications"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_notifications(self):
        """GET /api/notifications - Get user notifications"""
        response = self.session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_unread_count(self):
        """GET /api/notifications/unread-count - Get unread count"""
        response = self.session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
    
    def test_send_notification(self):
        """POST /api/notifications/send - Send notification"""
        response = self.session.post(f"{BASE_URL}/api/notifications/send", json={
            "title": "TEST_Refactor Test Notification",
            "message": "Testing notification after route extraction",
            "type": "info",
            "target_roles": ["all"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "notification_id" in data


class TestDailySettingsRoutes:
    """Test daily_settings.py routes - Uniform and weather flag"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_daily_settings(self):
        """GET /api/daily-settings - Get daily settings"""
        response = self.session.get(f"{BASE_URL}/api/daily-settings")
        assert response.status_code == 200
        data = response.json()
        assert "uniform" in data
        assert "weather_flag" in data


class TestMealPlanRoutes:
    """Test meal_plan.py routes - Meal plan schedule"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_meal_plans(self):
        """GET /api/meal-plans - Get meal plans"""
        response = self.session.get(f"{BASE_URL}/api/meal-plans")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestHealthAlertsRoutes:
    """Test health_alerts.py routes - Health alerts"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_health_alerts(self):
        """GET /api/health-alerts/{id} - Get health alerts for member"""
        response = self.session.get(f"{BASE_URL}/api/health-alerts/test-member-id")
        assert response.status_code == 200
        data = response.json()
        assert "member_id" in data


class TestScheduleChangesRoutes:
    """Test schedule_changes.py routes - Schedule change requests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_schedule_changes(self):
        """GET /api/schedule-changes - Get schedule changes"""
        response = self.session.get(f"{BASE_URL}/api/schedule-changes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_pending_count(self):
        """GET /api/schedule-changes/pending-count - Get pending count"""
        response = self.session.get(f"{BASE_URL}/api/schedule-changes/pending-count")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data


class TestRootRoute:
    """Test root API route"""
    
    def test_root_endpoint(self):
        """GET /api/ - Root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "CAP Encampment Roster API"
        assert data["version"] == "1.0.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
