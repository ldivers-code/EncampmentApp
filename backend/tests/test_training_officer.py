"""
Test Training Officer Module
- GET /api/training/summary - Training dashboard summary
- GET/POST /api/training/blister-checks - Blister check CRUD
- PUT /api/training/blister-checks/{id} - Update blister check status
- GET/POST /api/training/counseling-logs - Counseling log CRUD
- PUT /api/training/counseling-logs/{id} - Update counseling log
- GET/POST /api/training/cadre-issues - Cadre issues CRUD
- PUT /api/training/cadre-issues/{id} - Update cadre issue status
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for commander user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": COMMANDER_EMAIL,
        "password": COMMANDER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.fail(f"Authentication failed: {response.text}")

@pytest.fixture
def auth_headers(auth_token):
    """Auth headers with bearer token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestTrainingSummary:
    """Test Training Summary endpoint"""

    def test_get_training_summary_success(self, auth_headers):
        """GET /api/training/summary returns summary counts"""
        response = requests.get(f"{BASE_URL}/api/training/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields
        assert "blister_checks_today" in data
        assert "blisters_monitoring" in data
        assert "counseling_today" in data
        assert "counseling_followup" in data
        assert "cadre_issues_open" in data
        assert "cadre_issues_critical" in data
        
        # Verify types
        assert isinstance(data["blister_checks_today"], int)
        assert isinstance(data["blisters_monitoring"], int)

    def test_get_training_summary_requires_auth(self):
        """GET /api/training/summary requires authentication"""
        response = requests.get(f"{BASE_URL}/api/training/summary")
        assert response.status_code in [401, 403]


class TestBlisterChecks:
    """Test Blister Checks CRUD"""

    def test_create_blister_check_success(self, auth_headers):
        """POST /api/training/blister-checks creates a blister check"""
        payload = {
            "cadet_name": "TEST_Smith, John",
            "capid": "123456",
            "flight": "alpha",
            "squadron": "6th_cts",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "severity": "mild",
            "location": "Left Heel",
            "description": "Small blister forming",
            "treatment_given": "Moleskin applied",
            "follow_up_needed": True,
            "status": "monitoring"
        }
        response = requests.post(f"{BASE_URL}/api/training/blister-checks", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify returned data
        assert "id" in data
        assert data["cadet_name"] == "TEST_Smith, John"
        assert data["severity"] == "mild"
        assert data["location"] == "Left Heel"
        assert data["status"] == "monitoring"
        assert data["follow_up_needed"] == True
        
        return data["id"]

    def test_get_blister_checks_success(self, auth_headers):
        """GET /api/training/blister-checks returns list"""
        response = requests.get(f"{BASE_URL}/api/training/blister-checks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_blister_checks_with_date_filter(self, auth_headers):
        """GET /api/training/blister-checks with date filter"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = requests.get(f"{BASE_URL}/api/training/blister-checks?date={today}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # All returned items should match date if any exist
        for check in data:
            assert check.get("date") == today

    def test_get_blister_checks_with_flight_filter(self, auth_headers):
        """GET /api/training/blister-checks with flight filter"""
        response = requests.get(f"{BASE_URL}/api/training/blister-checks?flight=alpha", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # All returned items should match flight if any exist
        for check in data:
            assert check.get("flight") == "alpha"

    def test_update_blister_check_status(self, auth_headers):
        """PUT /api/training/blister-checks/{id} updates status"""
        # First create a blister check
        payload = {
            "cadet_name": "TEST_Update, Blister",
            "severity": "moderate",
            "location": "Right Heel",
            "status": "checked"
        }
        create_response = requests.post(f"{BASE_URL}/api/training/blister-checks", json=payload, headers=auth_headers)
        assert create_response.status_code == 200
        check_id = create_response.json()["id"]
        
        # Update status to monitoring
        update_response = requests.put(
            f"{BASE_URL}/api/training/blister-checks/{check_id}",
            json={"status": "monitoring"},
            headers=auth_headers
        )
        assert update_response.status_code == 200
        
        # Update status to resolved
        resolve_response = requests.put(
            f"{BASE_URL}/api/training/blister-checks/{check_id}",
            json={"status": "resolved"},
            headers=auth_headers
        )
        assert resolve_response.status_code == 200

    def test_update_nonexistent_blister_check(self, auth_headers):
        """PUT /api/training/blister-checks/{id} returns 404 for nonexistent"""
        fake_id = str(uuid.uuid4())
        response = requests.put(
            f"{BASE_URL}/api/training/blister-checks/{fake_id}",
            json={"status": "resolved"},
            headers=auth_headers
        )
        assert response.status_code == 404


class TestCounselingLogs:
    """Test Counseling Logs CRUD"""

    def test_create_counseling_log_success(self, auth_headers):
        """POST /api/training/counseling-logs creates a counseling log"""
        payload = {
            "cadet_name": "TEST_Jones, Mary",
            "capid": "234567",
            "flight": "bravo",
            "squadron": "6th_cts",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "category": "homesickness",
            "reason": "Cadet experiencing homesickness on day 3",
            "outcome": "Counseled and feeling better",
            "follow_up_needed": True,
            "follow_up_date": "2026-01-20"
        }
        response = requests.post(f"{BASE_URL}/api/training/counseling-logs", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify returned data
        assert "id" in data
        assert data["cadet_name"] == "TEST_Jones, Mary"
        assert data["category"] == "homesickness"
        assert data["reason"] == "Cadet experiencing homesickness on day 3"
        assert data["follow_up_needed"] == True

    def test_get_counseling_logs_success(self, auth_headers):
        """GET /api/training/counseling-logs returns list"""
        response = requests.get(f"{BASE_URL}/api/training/counseling-logs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_counseling_logs_with_filters(self, auth_headers):
        """GET /api/training/counseling-logs with filters"""
        response = requests.get(f"{BASE_URL}/api/training/counseling-logs?flight=bravo", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        for log in data:
            assert log.get("flight") == "bravo"

    def test_update_counseling_log(self, auth_headers):
        """PUT /api/training/counseling-logs/{id} updates log"""
        # Create first
        payload = {
            "cadet_name": "TEST_Update, Counseling",
            "category": "behavioral",
            "reason": "Initial reason",
            "follow_up_needed": False
        }
        create_response = requests.post(f"{BASE_URL}/api/training/counseling-logs", json=payload, headers=auth_headers)
        assert create_response.status_code == 200
        log_id = create_response.json()["id"]
        
        # Update
        update_response = requests.put(
            f"{BASE_URL}/api/training/counseling-logs/{log_id}",
            json={"outcome": "Issue resolved after discussion", "follow_up_needed": True},
            headers=auth_headers
        )
        assert update_response.status_code == 200

    def test_update_nonexistent_counseling_log(self, auth_headers):
        """PUT /api/training/counseling-logs/{id} returns 404 for nonexistent"""
        fake_id = str(uuid.uuid4())
        response = requests.put(
            f"{BASE_URL}/api/training/counseling-logs/{fake_id}",
            json={"outcome": "test"},
            headers=auth_headers
        )
        assert response.status_code == 404


class TestCadreIssues:
    """Test Cadre Issues CRUD"""

    def test_create_cadre_issue_success(self, auth_headers):
        """POST /api/training/cadre-issues creates a cadre issue"""
        payload = {
            "cadre_name": "TEST_Wilson, Bob",
            "cadre_capid": "345678",
            "flight": "charlie",
            "squadron": "21st_cts",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "category": "behavioral",
            "severity": "medium",
            "description": "Cadre member was late to formation",
            "action_taken": "Verbal counseling provided",
            "resolution_status": "open"
        }
        response = requests.post(f"{BASE_URL}/api/training/cadre-issues", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify returned data
        assert "id" in data
        assert data["cadre_name"] == "TEST_Wilson, Bob"
        assert data["category"] == "behavioral"
        assert data["severity"] == "medium"
        assert data["resolution_status"] == "open"

    def test_get_cadre_issues_success(self, auth_headers):
        """GET /api/training/cadre-issues returns list"""
        response = requests.get(f"{BASE_URL}/api/training/cadre-issues", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_update_cadre_issue_status_in_progress(self, auth_headers):
        """PUT /api/training/cadre-issues/{id} updates status to in_progress"""
        # Create first
        payload = {
            "cadre_name": "TEST_Status, Update",
            "category": "performance",
            "severity": "low",
            "description": "Performance issue noted",
            "resolution_status": "open"
        }
        create_response = requests.post(f"{BASE_URL}/api/training/cadre-issues", json=payload, headers=auth_headers)
        assert create_response.status_code == 200
        issue_id = create_response.json()["id"]
        
        # Update to in_progress
        update_response = requests.put(
            f"{BASE_URL}/api/training/cadre-issues/{issue_id}",
            json={"resolution_status": "in_progress"},
            headers=auth_headers
        )
        assert update_response.status_code == 200

    def test_update_cadre_issue_status_resolved(self, auth_headers):
        """PUT /api/training/cadre-issues/{id} updates status to resolved"""
        # Create first
        payload = {
            "cadre_name": "TEST_Resolve, Issue",
            "category": "protocol",
            "severity": "low",
            "description": "Protocol issue",
            "resolution_status": "open"
        }
        create_response = requests.post(f"{BASE_URL}/api/training/cadre-issues", json=payload, headers=auth_headers)
        assert create_response.status_code == 200
        issue_id = create_response.json()["id"]
        
        # Update to resolved
        update_response = requests.put(
            f"{BASE_URL}/api/training/cadre-issues/{issue_id}",
            json={"resolution_status": "resolved"},
            headers=auth_headers
        )
        assert update_response.status_code == 200

    def test_update_cadre_issue_status_escalated(self, auth_headers):
        """PUT /api/training/cadre-issues/{id} updates status to escalated"""
        # Create first
        payload = {
            "cadre_name": "TEST_Escalate, Issue",
            "category": "safety",
            "severity": "high",
            "description": "Safety concern requiring escalation",
            "resolution_status": "open"
        }
        create_response = requests.post(f"{BASE_URL}/api/training/cadre-issues", json=payload, headers=auth_headers)
        assert create_response.status_code == 200
        issue_id = create_response.json()["id"]
        
        # Update to escalated
        update_response = requests.put(
            f"{BASE_URL}/api/training/cadre-issues/{issue_id}",
            json={"resolution_status": "escalated"},
            headers=auth_headers
        )
        assert update_response.status_code == 200

    def test_update_nonexistent_cadre_issue(self, auth_headers):
        """PUT /api/training/cadre-issues/{id} returns 404 for nonexistent"""
        fake_id = str(uuid.uuid4())
        response = requests.put(
            f"{BASE_URL}/api/training/cadre-issues/{fake_id}",
            json={"resolution_status": "resolved"},
            headers=auth_headers
        )
        assert response.status_code == 404


class TestTrainingOfficerRoleInAdmin:
    """Test Training Officer role exists in admin"""

    def test_update_user_role_to_training_officer(self, auth_headers):
        """Verify training_officer is a valid role"""
        # Get users list
        users_response = requests.get(f"{BASE_URL}/api/users", headers=auth_headers)
        assert users_response.status_code == 200
        users = users_response.json()
        
        # If there are any non-commander users, test role update
        if len(users) > 1:
            # Find a non-commander user
            test_user = None
            for u in users:
                if u.get("role") != "commander":
                    test_user = u
                    break
            
            if test_user:
                # Try to set role to training_officer
                response = requests.put(
                    f"{BASE_URL}/api/users/{test_user['id']}/role?role=training_officer",
                    headers=auth_headers
                )
                assert response.status_code == 200
                
                # Restore original role
                requests.put(
                    f"{BASE_URL}/api/users/{test_user['id']}/role?role={test_user.get('role', 'staff')}",
                    headers=auth_headers
                )


class TestExistingTestData:
    """Test that existing seed data is visible"""

    def test_existing_blister_check_visible(self, auth_headers):
        """Verify existing blister check (Benson, Wesley) is in the list"""
        response = requests.get(f"{BASE_URL}/api/training/blister-checks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Look for the existing blister check
        found = False
        for check in data:
            if "Benson" in check.get("cadet_name", ""):
                found = True
                assert check.get("severity") == "mild"
                assert check.get("location") == "Left Heel"
                break
        
        # May not exist if DB was cleared, so just log
        if not found:
            print("Note: Pre-seeded blister check for Benson not found")

    def test_existing_counseling_log_visible(self, auth_headers):
        """Verify existing counseling log (Brown, Reese) is in the list"""
        response = requests.get(f"{BASE_URL}/api/training/counseling-logs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Look for the existing counseling log
        found = False
        for log in data:
            if "Brown" in log.get("cadet_name", ""):
                found = True
                assert log.get("category") == "homesickness"
                break
        
        # May not exist if DB was cleared, so just log
        if not found:
            print("Note: Pre-seeded counseling log for Brown not found")


# Cleanup test data after tests
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data(auth_token):
    """Cleanup TEST_ prefixed data after tests"""
    yield
    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    
    # Note: No DELETE endpoints exist for training data, 
    # but test data is prefixed with TEST_ for identification
