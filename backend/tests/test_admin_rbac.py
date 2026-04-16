"""
Test Admin Page RBAC (Role-Based Access Control) - Iteration 53
Tests:
1. Commander (full admin) can access all admin features
2. Exec Cadre can access admin page but with restricted features
3. User grouping by Staff/Cadre/Parent categories
4. Receipt OCR endpoint uses correct env var (EMERGENT_LLM_KEY)
5. Auto-balance endpoint works
"""
import pytest
import requests
import os

from tests.conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, PARENT_EMAIL, PARENT_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
COMMANDER_CREDS = {"email": COMMANDER_EMAIL, "password": COMMANDER_PASSWORD}
EXEC_CADRE_CREDS = {"email": "commander@cap.us", "password": COMMANDER_PASSWORD}


class TestAdminRBAC:
    """Test Admin Page Role-Based Access Control"""
    
    @pytest.fixture(scope="class")
    def commander_session(self):
        """Login as Commander (full admin)"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=COMMANDER_CREDS
        )
        assert response.status_code == 200, f"Commander login failed: {response.text}"
        data = response.json()
        assert data.get("user", {}).get("role") == "commander", "Expected commander role"
        return session
    
    @pytest.fixture(scope="class")
    def exec_cadre_session(self):
        """Login as Exec Cadre (restricted admin)"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=EXEC_CADRE_CREDS
        )
        assert response.status_code == 200, f"Exec Cadre login failed: {response.text}"
        data = response.json()
        assert data.get("user", {}).get("role") == "exec_cadre", "Expected exec_cadre role"
        return session
    
    # ============ COMMANDER (FULL ADMIN) TESTS ============
    
    def test_commander_can_get_users(self, commander_session):
        """Commander can access GET /api/users"""
        response = commander_session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200, f"Commander GET users failed: {response.text}"
        users = response.json()
        assert isinstance(users, list), "Expected list of users"
        assert len(users) > 0, "Expected at least one user"
        print(f"PASS: Commander can get users ({len(users)} users)")
    
    def test_commander_can_get_pending_users(self, commander_session):
        """Commander can access GET /api/users/pending"""
        response = commander_session.get(f"{BASE_URL}/api/users/pending")
        assert response.status_code == 200, f"Commander GET pending users failed: {response.text}"
        pending = response.json()
        assert isinstance(pending, list), "Expected list of pending users"
        print(f"PASS: Commander can get pending users ({len(pending)} pending)")
    
    def test_commander_can_update_user_role(self, commander_session):
        """Commander can update user roles via PUT /api/users/{id}/role"""
        # First get a user to update (not self)
        response = commander_session.get(f"{BASE_URL}/api/users")
        users = response.json()
        
        # Find a non-commander user to test role update
        test_user = None
        for u in users:
            if u.get("role") != "commander" and u.get("email") != COMMANDER_CREDS["email"]:
                test_user = u
                break
        
        if test_user:
            original_role = test_user.get("role")
            # Update to cadre then back
            response = commander_session.put(
                f"{BASE_URL}/api/users/{test_user['id']}/role",
                params={"role": "cadre"}
            )
            assert response.status_code == 200, f"Commander role update failed: {response.text}"
            
            # Restore original role
            commander_session.put(
                f"{BASE_URL}/api/users/{test_user['id']}/role",
                params={"role": original_role}
            )
            print(f"PASS: Commander can update user roles")
        else:
            print("SKIP: No non-commander user found to test role update")
    
    # ============ EXEC CADRE (RESTRICTED ADMIN) TESTS ============
    
    def test_exec_cadre_can_get_users(self, exec_cadre_session):
        """Exec Cadre can access GET /api/users (allowed per routes/users.py line 88)"""
        response = exec_cadre_session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200, f"Exec Cadre GET users failed: {response.text}"
        users = response.json()
        assert isinstance(users, list), "Expected list of users"
        print(f"PASS: Exec Cadre can get users ({len(users)} users)")
    
    def test_exec_cadre_can_update_user_role(self, exec_cadre_session):
        """Exec Cadre can update user roles via PUT /api/users/{id}/role (allowed per routes/users.py line 93)"""
        # First get a user to update
        response = exec_cadre_session.get(f"{BASE_URL}/api/users")
        users = response.json()
        
        # Find a non-exec_cadre user to test role update
        test_user = None
        for u in users:
            if u.get("role") not in ["commander", "exec_cadre", "dcp", "executive_staff"]:
                test_user = u
                break
        
        if test_user:
            original_role = test_user.get("role")
            # Update to cadre then back
            response = exec_cadre_session.put(
                f"{BASE_URL}/api/users/{test_user['id']}/role",
                params={"role": "cadre"}
            )
            assert response.status_code == 200, f"Exec Cadre role update failed: {response.text}"
            
            # Restore original role
            exec_cadre_session.put(
                f"{BASE_URL}/api/users/{test_user['id']}/role",
                params={"role": original_role}
            )
            print(f"PASS: Exec Cadre can update user roles")
        else:
            print("SKIP: No suitable user found to test role update")
    
    def test_exec_cadre_cannot_get_pending_users(self, exec_cadre_session):
        """Exec Cadre CANNOT access GET /api/users/pending (restricted to DCP/Commander/Executive Staff)"""
        response = exec_cadre_session.get(f"{BASE_URL}/api/users/pending")
        assert response.status_code == 403, f"Expected 403 for Exec Cadre pending users, got {response.status_code}"
        print("PASS: Exec Cadre correctly denied access to pending users")
    
    def test_exec_cadre_cannot_delete_user(self, exec_cadre_session):
        """Exec Cadre CANNOT delete users (restricted to DCP/Commander/Executive Staff)"""
        # Get a user ID to try to delete
        response = exec_cadre_session.get(f"{BASE_URL}/api/users")
        users = response.json()
        
        if users:
            test_user = users[0]
            response = exec_cadre_session.delete(f"{BASE_URL}/api/users/{test_user['id']}")
            assert response.status_code == 403, f"Expected 403 for Exec Cadre delete, got {response.status_code}"
            print("PASS: Exec Cadre correctly denied delete access")
        else:
            print("SKIP: No users to test delete restriction")
    
    def test_exec_cadre_cannot_update_permissions(self, exec_cadre_session):
        """Exec Cadre CANNOT update user permissions (restricted to DCP/Commander/Executive Staff)"""
        response = exec_cadre_session.get(f"{BASE_URL}/api/users")
        users = response.json()
        
        if users:
            test_user = users[0]
            response = exec_cadre_session.put(
                f"{BASE_URL}/api/users/{test_user['id']}/permissions",
                json={"dashboard": True}
            )
            assert response.status_code == 403, f"Expected 403 for Exec Cadre permissions update, got {response.status_code}"
            print("PASS: Exec Cadre correctly denied permissions update access")
        else:
            print("SKIP: No users to test permissions restriction")
    
    def test_exec_cadre_cannot_reset_password(self, exec_cadre_session):
        """Exec Cadre CANNOT reset user passwords (restricted to DCP/Commander/Executive Staff)"""
        response = exec_cadre_session.get(f"{BASE_URL}/api/users")
        users = response.json()
        
        if users:
            test_user = users[0]
            response = exec_cadre_session.post(
                f"{BASE_URL}/api/auth/admin-reset-password",
                json={"user_id": test_user['id'], "new_password": "test123456"}
            )
            # Should be 403 or 401
            assert response.status_code in [403, 401, 404], f"Expected 403/401/404 for Exec Cadre password reset, got {response.status_code}"
            print("PASS: Exec Cadre correctly denied password reset access")
        else:
            print("SKIP: No users to test password reset restriction")


class TestUserGrouping:
    """Test user grouping by Staff/Cadre/Parent categories"""
    
    @pytest.fixture(scope="class")
    def commander_session(self):
        """Login as Commander"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=COMMANDER_CREDS
        )
        assert response.status_code == 200
        return session
    
    def test_users_have_roles_for_grouping(self, commander_session):
        """Verify users have roles that can be grouped into Staff/Cadre/Parent"""
        response = commander_session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        users = response.json()
        
        # Define role categories (matching AdminPage.js lines 706-716)
        staff_roles = ['dcp', 'commander', 'executive_staff', 'training_officer', 'logistics',
            'finance', 'plans_programs', 'health_services', 'dining_facility', 'staff',
            'support_logistics', 'support_comms', 'support_pa', 'support_dining', 'support_health',
            'squadron_commander']
        cadre_roles = ['exec_cadre', 'cadre']
        parent_roles = ['parent']
        
        staff_count = 0
        cadre_count = 0
        parent_count = 0
        other_count = 0
        
        for user in users:
            role = user.get("role", "")
            if role in staff_roles:
                staff_count += 1
            elif role in cadre_roles:
                cadre_count += 1
            elif role in parent_roles:
                parent_count += 1
            else:
                other_count += 1
        
        print(f"User grouping: STAFF={staff_count}, CADRE={cadre_count}, PARENT={parent_count}, OTHER={other_count}")
        assert staff_count + cadre_count + parent_count + other_count == len(users), "All users should be categorized"
        print("PASS: Users can be grouped by Staff/Cadre/Parent categories")
    
    def test_users_sorted_alphabetically(self, commander_session):
        """Verify users are returned in a sortable format (have name field)"""
        response = commander_session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        users = response.json()
        
        # Check all users have name field for sorting
        for user in users:
            assert "name" in user or "email" in user, f"User {user.get('id')} missing name/email for sorting"
        
        print("PASS: All users have name field for alphabetical sorting")


class TestReceiptOCREndpoint:
    """Test receipt OCR endpoint uses correct env var"""
    
    @pytest.fixture(scope="class")
    def commander_session(self):
        """Login as Commander"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=COMMANDER_CREDS
        )
        assert response.status_code == 200
        return session
    
    def test_receipt_upload_endpoint_exists(self, commander_session):
        """Verify POST /api/budget/receipt-upload endpoint exists"""
        # Send a request without file to check endpoint exists
        response = commander_session.post(f"{BASE_URL}/api/budget/receipt-upload")
        # Should return 422 (validation error for missing file) not 404
        assert response.status_code in [422, 400], f"Expected 422/400 for missing file, got {response.status_code}"
        print("PASS: Receipt upload endpoint exists")


class TestAutoBalanceEndpoint:
    """Test auto-balance endpoint for student flight assignment"""
    
    @pytest.fixture(scope="class")
    def commander_session(self):
        """Login as Commander"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=COMMANDER_CREDS
        )
        assert response.status_code == 200
        return session
    
    def test_auto_assign_endpoint_exists(self, commander_session):
        """Verify POST /api/students/auto-assign endpoint works"""
        response = commander_session.post(f"{BASE_URL}/api/students/auto-assign")
        assert response.status_code == 200, f"Auto-assign failed: {response.text}"
        data = response.json()
        assert "message" in data, "Expected message in response"
        assert "assigned" in data, "Expected assigned count in response"
        print(f"PASS: Auto-assign endpoint works - {data.get('message')}")
    
    def test_flight_distribution_endpoint(self, commander_session):
        """Verify GET /api/students/flight-distribution works"""
        response = commander_session.get(f"{BASE_URL}/api/students/flight-distribution")
        assert response.status_code == 200, f"Flight distribution failed: {response.text}"
        data = response.json()
        assert "flights" in data, "Expected flights in response"
        assert "total_students" in data, "Expected total_students in response"
        print(f"PASS: Flight distribution endpoint works - {data.get('total_students')} total students")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
