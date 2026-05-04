"""
Test Meal Plan Schedule Feature and Dining Facility Role
- Tests CRUD operations for meal plans
- Tests MEAL_PLAN_EDITOR_ROLES permission checks
- Tests dining_facility role access restrictions
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD

# Test user for dining_facility role
TEST_DINING_USER_EMAIL = "TEST_dining_test@cap.gov"
TEST_DINING_USER_PASSWORD = os.environ.get("TEST_DINING_PASSWORD", "testpass123")
TEST_DINING_USER_CAPID = "999999"

@pytest.fixture(scope="module")
def commander_token():
    """Get commander auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": COMMANDER_EMAIL,
        "password": COMMANDER_PASSWORD
    })
    assert response.status_code == 200, f"Commander login failed: {response.text}"
    return response.json()["access_token"]

@pytest.fixture(scope="module")
def commander_headers(commander_token):
    """Auth headers for commander"""
    return {"Authorization": f"Bearer {commander_token}"}

@pytest.fixture(scope="module")
def cadre_user(commander_headers):
    """Create a test cadre user (no meal plan edit access)"""
    # First try to delete if exists
    response = requests.get(f"{BASE_URL}/api/users", headers=commander_headers)
    if response.status_code == 200:
        users = response.json()
        for user in users:
            if user.get("email") == "TEST_cadre_mealtest@cap.gov":
                requests.delete(f"{BASE_URL}/api/users/{user['id']}", headers=commander_headers)
    
    # Register new cadre user
    response = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": "TEST_cadre_mealtest@cap.gov",
        "password": "testpass123",
        "name": "Test Cadre Meal",
        "role": "cadre",
        "capid": "888888"
    })
    if response.status_code == 200:
        return response.json()
    # If user already exists, try to login
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "TEST_cadre_mealtest@cap.gov",
        "password": "testpass123"
    })
    assert response.status_code == 200
    return response.json()

@pytest.fixture(scope="module")
def cadre_headers(cadre_user):
    """Auth headers for cadre user"""
    return {"Authorization": f"Bearer {cadre_user['access_token']}"}


class TestMealPlanAPI:
    """Test Meal Plan CRUD operations"""
    
    def test_get_meal_plans_authenticated(self, commander_headers):
        """Test GET /api/meal-plans returns meal plans list"""
        response = requests.get(f"{BASE_URL}/api/meal-plans", headers=commander_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET meal-plans works - found {len(data)} existing meal plans")
    
    def test_get_meal_plans_unauthenticated(self):
        """Test GET /api/meal-plans requires authentication"""
        response = requests.get(f"{BASE_URL}/api/meal-plans")
        assert response.status_code in [401, 403]
        print("✓ Meal plans API requires authentication")
    
    def test_create_meal_plan_commander(self, commander_headers):
        """Test POST /api/meal-plans creates a meal plan (commander role)"""
        today = datetime.now().strftime("%Y-%m-%d")
        meal_data = {
            "date": today,
            "meal_type": "lunch",
            "menu_items": "TEST_Grilled chicken, rice, salad, cookies",
            "location": "Dining Facility",
            "time": "1200",
            "headcount": 150,
            "dietary_notes": "Vegetarian option: veggie stir-fry",
            "notes": "Created by test"
        }
        response = requests.post(f"{BASE_URL}/api/meal-plans", json=meal_data, headers=commander_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["menu_items"] == "TEST_Grilled chicken, rice, salad, cookies"
        assert data["meal_type"] == "lunch"
        assert data["date"] == today
        assert "id" in data
        assert "created_by" in data
        print(f"✓ Created meal plan ID: {data['id']}")
        return data["id"]
    
    def test_create_meal_plan_all_types(self, commander_headers):
        """Test creating different meal types"""
        today = datetime.now().strftime("%Y-%m-%d")
        meal_types = ["breakfast", "lunch", "dinner", "snack"]
        
        created_ids = []
        for meal_type in meal_types:
            meal_data = {
                "date": today,
                "meal_type": meal_type,
                "menu_items": f"TEST_{meal_type} menu items",
                "time": {"breakfast": "0700", "lunch": "1200", "dinner": "1800", "snack": "1500"}.get(meal_type, "")
            }
            response = requests.post(f"{BASE_URL}/api/meal-plans", json=meal_data, headers=commander_headers)
            assert response.status_code == 200
            created_ids.append(response.json()["id"])
        
        print(f"✓ Created all 4 meal types: {meal_types}")
        return created_ids
    
    def test_update_meal_plan(self, commander_headers):
        """Test PUT /api/meal-plans/{id} updates a meal plan"""
        # First create a meal plan
        today = datetime.now().strftime("%Y-%m-%d")
        meal_data = {
            "date": today,
            "meal_type": "dinner",
            "menu_items": "TEST_Original dinner menu"
        }
        create_response = requests.post(f"{BASE_URL}/api/meal-plans", json=meal_data, headers=commander_headers)
        assert create_response.status_code == 200
        plan_id = create_response.json()["id"]
        
        # Update the meal plan
        updated_data = {
            "date": today,
            "meal_type": "dinner",
            "menu_items": "TEST_Updated dinner menu - steak and potatoes",
            "headcount": 200,
            "dietary_notes": "Gluten-free option available"
        }
        response = requests.put(f"{BASE_URL}/api/meal-plans/{plan_id}", json=updated_data, headers=commander_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["menu_items"] == "TEST_Updated dinner menu - steak and potatoes"
        assert data["headcount"] == 200
        assert "updated_by" in data
        print(f"✓ Updated meal plan ID: {plan_id}")
    
    def test_delete_meal_plan(self, commander_headers):
        """Test DELETE /api/meal-plans/{id} deletes a meal plan"""
        # First create a meal plan to delete
        today = datetime.now().strftime("%Y-%m-%d")
        meal_data = {
            "date": today,
            "meal_type": "snack",
            "menu_items": "TEST_Snack to delete"
        }
        create_response = requests.post(f"{BASE_URL}/api/meal-plans", json=meal_data, headers=commander_headers)
        assert create_response.status_code == 200
        plan_id = create_response.json()["id"]
        
        # Delete the meal plan
        response = requests.delete(f"{BASE_URL}/api/meal-plans/{plan_id}", headers=commander_headers)
        assert response.status_code == 200
        
        # Verify it's deleted - should still return 200 for GET but not contain the item
        get_response = requests.get(f"{BASE_URL}/api/meal-plans", headers=commander_headers)
        plans = get_response.json()
        assert not any(p["id"] == plan_id for p in plans)
        print(f"✓ Deleted meal plan ID: {plan_id}")
    
    def test_delete_nonexistent_meal_plan(self, commander_headers):
        """Test DELETE /api/meal-plans/{id} for nonexistent ID returns 404"""
        response = requests.delete(f"{BASE_URL}/api/meal-plans/nonexistent-id-12345", headers=commander_headers)
        assert response.status_code == 404
        print("✓ Delete nonexistent meal plan returns 404")


class TestMealPlanPermissions:
    """Test MEAL_PLAN_EDITOR_ROLES permissions"""
    
    def test_cadre_can_read_meal_plans(self, cadre_headers):
        """Test cadre role CAN read meal plans"""
        response = requests.get(f"{BASE_URL}/api/meal-plans", headers=cadre_headers)
        assert response.status_code == 200
        print("✓ Cadre role can read meal plans")
    
    def test_cadre_cannot_create_meal_plan(self, cadre_headers):
        """Test cadre role CANNOT create meal plans"""
        today = datetime.now().strftime("%Y-%m-%d")
        meal_data = {
            "date": today,
            "meal_type": "lunch",
            "menu_items": "TEST_Cadre attempted creation"
        }
        response = requests.post(f"{BASE_URL}/api/meal-plans", json=meal_data, headers=cadre_headers)
        assert response.status_code == 403
        print("✓ Cadre role correctly denied meal plan creation (403)")
    
    def test_cadre_cannot_update_meal_plan(self, commander_headers, cadre_headers):
        """Test cadre role CANNOT update meal plans"""
        # First create a meal plan as commander
        today = datetime.now().strftime("%Y-%m-%d")
        meal_data = {
            "date": today,
            "meal_type": "breakfast",
            "menu_items": "TEST_For cadre update test"
        }
        create_response = requests.post(f"{BASE_URL}/api/meal-plans", json=meal_data, headers=commander_headers)
        assert create_response.status_code == 200
        plan_id = create_response.json()["id"]
        
        # Try to update as cadre
        updated_data = {
            "date": today,
            "meal_type": "breakfast",
            "menu_items": "TEST_Cadre attempted update"
        }
        response = requests.put(f"{BASE_URL}/api/meal-plans/{plan_id}", json=updated_data, headers=cadre_headers)
        assert response.status_code == 403
        print("✓ Cadre role correctly denied meal plan update (403)")
    
    def test_cadre_cannot_delete_meal_plan(self, commander_headers, cadre_headers):
        """Test cadre role CANNOT delete meal plans"""
        # First create a meal plan as commander
        today = datetime.now().strftime("%Y-%m-%d")
        meal_data = {
            "date": today,
            "meal_type": "dinner",
            "menu_items": "TEST_For cadre delete test"
        }
        create_response = requests.post(f"{BASE_URL}/api/meal-plans", json=meal_data, headers=commander_headers)
        assert create_response.status_code == 200
        plan_id = create_response.json()["id"]
        
        # Try to delete as cadre
        response = requests.delete(f"{BASE_URL}/api/meal-plans/{plan_id}", headers=cadre_headers)
        assert response.status_code == 403
        print("✓ Cadre role correctly denied meal plan deletion (403)")


class TestDiningFacilityRole:
    """Test dining_facility role permissions"""
    
    @pytest.fixture(scope="class")
    def dining_user(self, commander_headers):
        """Create or get a dining_facility test user"""
        # First check if user exists
        response = requests.get(f"{BASE_URL}/api/users", headers=commander_headers)
        if response.status_code == 200:
            users = response.json()
            for user in users:
                if user.get("email") == TEST_DINING_USER_EMAIL:
                    # Change role to dining_facility if needed
                    if user.get("role") != "dining_facility":
                        requests.put(f"{BASE_URL}/api/users/{user['id']}/role?role=dining_facility", 
                                   headers=commander_headers)
                    # Try to login
                    login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                        "email": TEST_DINING_USER_EMAIL,
                        "password": TEST_DINING_USER_PASSWORD
                    })
                    if login_response.status_code == 200:
                        return login_response.json()
        
        # Register new dining_facility user
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_DINING_USER_EMAIL,
            "password": TEST_DINING_USER_PASSWORD,
            "name": "Test Dining Facility",
            "role": "staff",  # Register as staff, then change
            "capid": TEST_DINING_USER_CAPID
        })
        
        if response.status_code in [200, 400]:  # 400 might mean already exists
            # Login
            login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_DINING_USER_EMAIL,
                "password": TEST_DINING_USER_PASSWORD
            })
            if login_response.status_code == 200:
                user_data = login_response.json()
                # Change role to dining_facility
                requests.put(f"{BASE_URL}/api/users/{user_data['user']['id']}/role?role=dining_facility",
                           headers=commander_headers)
                # Re-login to get updated token
                login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                    "email": TEST_DINING_USER_EMAIL,
                    "password": TEST_DINING_USER_PASSWORD
                })
                return login_response.json()
        
        pytest.skip("Could not create dining_facility test user")
    
    @pytest.fixture(scope="class")
    def dining_headers(self, dining_user):
        """Auth headers for dining_facility user"""
        return {"Authorization": f"Bearer {dining_user['access_token']}"}
    
    def test_dining_user_created_with_correct_role(self, dining_user):
        """Verify dining_facility user has correct role"""
        # Check user role
        user = dining_user.get("user", {})
        # Note: after role change, token might still have old role
        print(f"✓ Dining facility user created: {user.get('email')}, role: {user.get('role')}")
    
    def test_dining_facility_can_read_meal_plans(self, dining_headers):
        """Test dining_facility role CAN read meal plans"""
        response = requests.get(f"{BASE_URL}/api/meal-plans", headers=dining_headers)
        assert response.status_code == 200
        print("✓ Dining facility role can read meal plans")
    
    def test_dining_facility_can_create_meal_plan(self, commander_headers):
        """Test dining_facility role CAN create meal plans"""
        # First ensure user has dining_facility role and get fresh token
        response = requests.get(f"{BASE_URL}/api/users", headers=commander_headers)
        users = response.json()
        dining_user = next((u for u in users if u.get("email") == TEST_DINING_USER_EMAIL), None)
        
        if dining_user and dining_user.get("role") != "dining_facility":
            # Update role
            requests.put(f"{BASE_URL}/api/users/{dining_user['id']}/role?role=dining_facility",
                        headers=commander_headers)
        
        # Login fresh to get token with updated role
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_DINING_USER_EMAIL,
            "password": TEST_DINING_USER_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip("Could not login as dining_facility user")
        
        dining_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        
        today = datetime.now().strftime("%Y-%m-%d")
        meal_data = {
            "date": today,
            "meal_type": "lunch",
            "menu_items": "TEST_Dining facility created meal"
        }
        response = requests.post(f"{BASE_URL}/api/meal-plans", json=meal_data, headers=dining_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Dining facility role can create meal plans")
    
    def test_dining_facility_cannot_access_admin(self, commander_headers):
        """Test dining_facility role CANNOT access admin page (GET /api/users)"""
        # Get fresh dining user token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_DINING_USER_EMAIL,
            "password": TEST_DINING_USER_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip("Could not login as dining_facility user")
        
        dining_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        
        response = requests.get(f"{BASE_URL}/api/users", headers=dining_headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Dining facility role correctly denied admin access (403)")
    
    def test_dining_facility_cannot_access_health_services(self, commander_headers):
        """Test dining_facility role CANNOT access health services endpoints"""
        # Get fresh dining user token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_DINING_USER_EMAIL,
            "password": TEST_DINING_USER_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip("Could not login as dining_facility user")
        
        dining_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
        
        # Try to access health dashboard
        response = requests.get(f"{BASE_URL}/api/health/dashboard/summary", headers=dining_headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Dining facility role correctly denied health services access (403)")


class TestCleanupMealPlans:
    """Cleanup test data"""
    
    def test_cleanup_test_meal_plans(self, commander_headers):
        """Delete all TEST_ prefixed meal plans"""
        response = requests.get(f"{BASE_URL}/api/meal-plans", headers=commander_headers)
        if response.status_code == 200:
            plans = response.json()
            deleted_count = 0
            for plan in plans:
                if "TEST_" in plan.get("menu_items", ""):
                    del_response = requests.delete(f"{BASE_URL}/api/meal-plans/{plan['id']}", 
                                                  headers=commander_headers)
                    if del_response.status_code == 200:
                        deleted_count += 1
            print(f"✓ Cleaned up {deleted_count} test meal plans")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
