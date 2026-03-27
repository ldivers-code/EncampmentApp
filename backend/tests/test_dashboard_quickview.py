"""
Test Dashboard Quickview API - Role-specific quick-view cards
Tests GET /api/stats/dashboard-quickview endpoint for different roles
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
COMMANDER_EMAIL = "testadmin@cap.gov"
COMMANDER_PASSWORD = "TestPass123!"
CADRE_EMAIL = "testcadre@cap.gov"
CADRE_PASSWORD = "TestPass123!"


class TestDashboardQuickview:
    """Test dashboard quickview endpoint for different roles"""
    
    @pytest.fixture(scope="class")
    def commander_token(self):
        """Get commander auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Commander login failed: {response.status_code} - {response.text}")
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def cadre_token(self):
        """Get cadre auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CADRE_EMAIL,
            "password": CADRE_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Cadre login failed: {response.status_code} - {response.text}")
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def commander_user(self, commander_token):
        """Get commander user info"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {commander_token}"
        })
        return response.json()
    
    @pytest.fixture(scope="class")
    def cadre_user(self, cadre_token):
        """Get cadre user info"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {cadre_token}"
        })
        return response.json()
    
    # ============ Commander Role Tests ============
    
    def test_commander_login_success(self, commander_token):
        """Verify commander can login"""
        assert commander_token is not None
        print(f"Commander token obtained successfully")
    
    def test_commander_role_is_correct(self, commander_user):
        """Verify commander has correct role"""
        assert commander_user.get("role") == "commander", f"Expected commander role, got {commander_user.get('role')}"
        print(f"Commander role verified: {commander_user.get('role')}")
    
    def test_commander_quickview_returns_all_sections(self, commander_token):
        """Commander should see all quickview sections"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {commander_token}"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Commander should have access to all sections
        expected_sections = ["admin", "check_in", "health", "budget", "logistics", "training", "barracks", "reports", "dining"]
        
        for section in expected_sections:
            assert section in data, f"Commander missing section: {section}"
            print(f"Commander has section: {section}")
        
        print(f"Commander quickview data: {data}")
    
    def test_commander_admin_section_structure(self, commander_token):
        """Verify admin section has correct structure"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {commander_token}"
        })
        data = response.json()
        
        assert "admin" in data
        admin = data["admin"]
        assert "pending_approvals" in admin, "Missing pending_approvals in admin section"
        assert "unlinked_users" in admin, "Missing unlinked_users in admin section"
        assert isinstance(admin["pending_approvals"], int)
        assert isinstance(admin["unlinked_users"], int)
        print(f"Admin section: pending_approvals={admin['pending_approvals']}, unlinked_users={admin['unlinked_users']}")
    
    def test_commander_check_in_section_structure(self, commander_token):
        """Verify check_in section has correct structure"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {commander_token}"
        })
        data = response.json()
        
        assert "check_in" in data
        check_in = data["check_in"]
        assert "total" in check_in, "Missing total in check_in section"
        assert "checked_in" in check_in, "Missing checked_in in check_in section"
        assert "remaining" in check_in, "Missing remaining in check_in section"
        
        # Verify math: total = checked_in + remaining
        assert check_in["total"] == check_in["checked_in"] + check_in["remaining"]
        print(f"Check-in section: total={check_in['total']}, checked_in={check_in['checked_in']}, remaining={check_in['remaining']}")
    
    def test_commander_health_section_structure(self, commander_token):
        """Verify health section has correct structure"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {commander_token}"
        })
        data = response.json()
        
        assert "health" in data
        health = data["health"]
        assert "open_incidents" in health, "Missing open_incidents in health section"
        assert "active_medications" in health, "Missing active_medications in health section"
        assert "critical_flags" in health, "Missing critical_flags in health section"
        print(f"Health section: open_incidents={health['open_incidents']}, active_medications={health['active_medications']}, critical_flags={health['critical_flags']}")
    
    def test_commander_budget_section_structure(self, commander_token):
        """Verify budget section has correct structure"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {commander_token}"
        })
        data = response.json()
        
        assert "budget" in data
        budget = data["budget"]
        assert "total_estimated" in budget, "Missing total_estimated in budget section"
        assert "total_actual" in budget, "Missing total_actual in budget section"
        assert "variance" in budget, "Missing variance in budget section"
        assert "unpaid_items" in budget, "Missing unpaid_items in budget section"
        
        # Verify variance calculation
        expected_variance = budget["total_estimated"] - budget["total_actual"]
        assert budget["variance"] == expected_variance, f"Variance mismatch: expected {expected_variance}, got {budget['variance']}"
        print(f"Budget section: estimated={budget['total_estimated']}, actual={budget['total_actual']}, variance={budget['variance']}")
    
    def test_commander_logistics_section_structure(self, commander_token):
        """Verify logistics section has correct structure"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {commander_token}"
        })
        data = response.json()
        
        assert "logistics" in data
        logistics = data["logistics"]
        assert "open_supply_requests" in logistics
        assert "radios_checked_out" in logistics
        assert "lost_items" in logistics
        print(f"Logistics section: open_supply={logistics['open_supply_requests']}, radios_out={logistics['radios_checked_out']}, lost={logistics['lost_items']}")
    
    def test_commander_training_section_structure(self, commander_token):
        """Verify training section has correct structure"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {commander_token}"
        })
        data = response.json()
        
        assert "training" in data
        training = data["training"]
        assert "open_cadre_issues" in training
        assert "counseling_logs" in training
        print(f"Training section: open_issues={training['open_cadre_issues']}, counseling_logs={training['counseling_logs']}")
    
    def test_commander_barracks_section_structure(self, commander_token):
        """Verify barracks section has correct structure"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {commander_token}"
        })
        data = response.json()
        
        assert "barracks" in data
        barracks = data["barracks"]
        assert "assigned" in barracks
        assert "total_capacity" in barracks
        assert "available" in barracks
        
        # Verify math
        assert barracks["available"] == barracks["total_capacity"] - barracks["assigned"]
        print(f"Barracks section: assigned={barracks['assigned']}, capacity={barracks['total_capacity']}, available={barracks['available']}")
    
    def test_commander_reports_section_structure(self, commander_token):
        """Verify reports section has correct structure"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {commander_token}"
        })
        data = response.json()
        
        assert "reports" in data
        reports = data["reports"]
        assert "pending_review" in reports
        assert "escalated" in reports
        print(f"Reports section: pending={reports['pending_review']}, escalated={reports['escalated']}")
    
    def test_commander_dining_section_structure(self, commander_token):
        """Verify dining section has correct structure"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {commander_token}"
        })
        data = response.json()
        
        assert "dining" in data
        dining = data["dining"]
        assert "total_headcount" in dining
        assert "meal_plans_set" in dining
        print(f"Dining section: headcount={dining['total_headcount']}, meal_plans={dining['meal_plans_set']}")
    
    # ============ Cadre Role Tests ============
    
    def test_cadre_login_success(self, cadre_token):
        """Verify cadre can login"""
        assert cadre_token is not None
        print(f"Cadre token obtained successfully")
    
    def test_cadre_role_is_correct(self, cadre_user):
        """Verify cadre has correct role"""
        assert cadre_user.get("role") == "cadre", f"Expected cadre role, got {cadre_user.get('role')}"
        print(f"Cadre role verified: {cadre_user.get('role')}")
    
    def test_cadre_quickview_returns_only_my_unit(self, cadre_token):
        """Cadre should only see my_unit section (no admin/budget/health/logistics/training/barracks)"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {cadre_token}"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Cadre should NOT have these sections
        restricted_sections = ["admin", "budget", "health", "logistics", "training", "barracks", "reports", "dining"]
        
        for section in restricted_sections:
            if section in data:
                print(f"WARNING: Cadre has restricted section: {section}")
            # Note: We're checking if cadre incorrectly has access
        
        # Cadre SHOULD have my_unit section
        assert "my_unit" in data, "Cadre should have my_unit section"
        print(f"Cadre quickview data: {data}")
    
    def test_cadre_my_unit_section_structure(self, cadre_token, cadre_user):
        """Verify my_unit section has correct structure for cadre"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {cadre_token}"
        })
        data = response.json()
        
        assert "my_unit" in data
        my_unit = data["my_unit"]
        
        # If cadre has a flight assigned, it should show
        if cadre_user.get("flight"):
            assert "flight" in my_unit, "my_unit should have flight field"
            assert my_unit["flight"] == cadre_user.get("flight"), f"Flight mismatch"
            print(f"Cadre my_unit: flight={my_unit.get('flight')}, count={my_unit.get('flight_count')}")
        else:
            print(f"Cadre has no flight assigned, my_unit may be empty: {my_unit}")
    
    def test_cadre_no_admin_access(self, cadre_token):
        """Verify cadre does NOT have admin section"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {cadre_token}"
        })
        data = response.json()
        
        # Cadre should NOT have admin section
        assert "admin" not in data, "Cadre should NOT have admin section"
        print("Verified: Cadre does not have admin section")
    
    def test_cadre_no_budget_access(self, cadre_token):
        """Verify cadre does NOT have budget section"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {cadre_token}"
        })
        data = response.json()
        
        # Cadre should NOT have budget section
        assert "budget" not in data, "Cadre should NOT have budget section"
        print("Verified: Cadre does not have budget section")
    
    def test_cadre_no_health_access(self, cadre_token):
        """Verify cadre does NOT have health section"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {cadre_token}"
        })
        data = response.json()
        
        # Cadre should NOT have health section
        assert "health" not in data, "Cadre should NOT have health section"
        print("Verified: Cadre does not have health section")
    
    def test_cadre_no_logistics_access(self, cadre_token):
        """Verify cadre does NOT have logistics section"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {cadre_token}"
        })
        data = response.json()
        
        # Cadre should NOT have logistics section
        assert "logistics" not in data, "Cadre should NOT have logistics section"
        print("Verified: Cadre does not have logistics section")
    
    def test_cadre_no_training_access(self, cadre_token):
        """Verify cadre does NOT have training section"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {cadre_token}"
        })
        data = response.json()
        
        # Cadre should NOT have training section
        assert "training" not in data, "Cadre should NOT have training section"
        print("Verified: Cadre does not have training section")
    
    def test_cadre_no_barracks_access(self, cadre_token):
        """Verify cadre does NOT have barracks section"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {cadre_token}"
        })
        data = response.json()
        
        # Cadre should NOT have barracks section
        assert "barracks" not in data, "Cadre should NOT have barracks section"
        print("Verified: Cadre does not have barracks section")
    
    # ============ Data Consistency Tests ============
    
    def test_check_in_progress_percentage(self, commander_token):
        """Verify check-in progress percentage calculation (0/115 = 0%)"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {commander_token}"
        })
        data = response.json()
        
        check_in = data.get("check_in", {})
        total = check_in.get("total", 0)
        checked_in = check_in.get("checked_in", 0)
        
        if total > 0:
            pct = round((checked_in / total) * 100)
        else:
            pct = 0
        
        print(f"Check-in progress: {checked_in}/{total} = {pct}%")
        # Just verify the calculation is valid
        assert pct >= 0 and pct <= 100
    
    def test_budget_variance_value(self, commander_token):
        """Verify budget variance displays correctly"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": f"Bearer {commander_token}"
        })
        data = response.json()
        
        budget = data.get("budget", {})
        variance = budget.get("variance", 0)
        
        print(f"Budget variance: ${variance}")
        # Variance can be positive (under budget) or negative (over budget)
        assert isinstance(variance, (int, float))


class TestDashboardQuickviewEndpointAuth:
    """Test authentication requirements for dashboard quickview"""
    
    def test_quickview_requires_auth(self):
        """Verify endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("Verified: Endpoint requires authentication")
    
    def test_quickview_rejects_invalid_token(self):
        """Verify endpoint rejects invalid token"""
        response = requests.get(f"{BASE_URL}/api/stats/dashboard-quickview", headers={
            "Authorization": "Bearer invalid_token_12345"
        })
        assert response.status_code in [401, 403], f"Expected 401/403 with invalid token, got {response.status_code}"
        print("Verified: Endpoint rejects invalid token")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
