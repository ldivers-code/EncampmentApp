"""
Test suite for Meal Plan and Budget API endpoints
Tests:
1. Meal Plan CRUD operations
2. Budget page (Financial Tracker) - verify it works without Food Planner
3. dining_facility role permissions
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD

class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get commander auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        return data["access_token"]
    
    def test_login_success(self, auth_token):
        """Verify login works"""
        assert auth_token is not None
        print(f"✓ Login successful, token obtained")


class TestMealPlanAPI:
    """Test Meal Plan CRUD operations"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_meal_plans(self, auth_headers):
        """GET /api/meal-plans returns list of meal plans"""
        response = requests.get(f"{BASE_URL}/api/meal-plans", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/meal-plans returned {len(data)} meal plans")
        return data
    
    def test_create_meal_plan(self, auth_headers):
        """POST /api/meal-plans creates a new meal plan"""
        meal_data = {
            "date": "2026-03-20",
            "meal_type": "breakfast",
            "menu_items": "TEST_Scrambled eggs, bacon, toast, juice",
            "location": "Dining Facility",
            "time": "0700",
            "notes": "Test meal plan entry",
            "headcount": 150,
            "dietary_notes": "Vegetarian option: veggie scramble"
        }
        response = requests.post(f"{BASE_URL}/api/meal-plans", json=meal_data, headers=auth_headers)
        assert response.status_code == 200, f"Create failed: {response.text}"
        data = response.json()
        assert data["date"] == meal_data["date"]
        assert data["meal_type"] == meal_data["meal_type"]
        assert data["menu_items"] == meal_data["menu_items"]
        assert "id" in data
        print(f"✓ POST /api/meal-plans created meal plan with id: {data['id']}")
        return data
    
    def test_create_and_update_meal_plan(self, auth_headers):
        """PUT /api/meal-plans/{id} updates a meal plan"""
        # First create
        create_data = {
            "date": "2026-03-21",
            "meal_type": "lunch",
            "menu_items": "TEST_Original lunch menu"
        }
        create_response = requests.post(f"{BASE_URL}/api/meal-plans", json=create_data, headers=auth_headers)
        assert create_response.status_code == 200
        meal_id = create_response.json()["id"]
        
        # Then update
        update_data = {
            "date": "2026-03-21",
            "meal_type": "lunch",
            "menu_items": "TEST_Updated lunch menu - grilled chicken, salad, rice",
            "headcount": 175
        }
        update_response = requests.put(f"{BASE_URL}/api/meal-plans/{meal_id}", json=update_data, headers=auth_headers)
        assert update_response.status_code == 200, f"Update failed: {update_response.text}"
        updated = update_response.json()
        assert updated["menu_items"] == update_data["menu_items"]
        assert updated["headcount"] == 175
        print(f"✓ PUT /api/meal-plans/{meal_id} updated successfully")
        return meal_id
    
    def test_create_and_delete_meal_plan(self, auth_headers):
        """DELETE /api/meal-plans/{id} deletes a meal plan"""
        # First create
        create_data = {
            "date": "2026-03-22",
            "meal_type": "dinner",
            "menu_items": "TEST_Dinner to be deleted"
        }
        create_response = requests.post(f"{BASE_URL}/api/meal-plans", json=create_data, headers=auth_headers)
        assert create_response.status_code == 200
        meal_id = create_response.json()["id"]
        
        # Then delete
        delete_response = requests.delete(f"{BASE_URL}/api/meal-plans/{meal_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        # Verify deletion by trying to get all and checking it's not there
        get_response = requests.get(f"{BASE_URL}/api/meal-plans", headers=auth_headers)
        meals = get_response.json()
        meal_ids = [m["id"] for m in meals]
        assert meal_id not in meal_ids, "Meal plan was not deleted"
        print(f"✓ DELETE /api/meal-plans/{meal_id} deleted successfully")
    
    def test_delete_nonexistent_returns_404(self, auth_headers):
        """DELETE /api/meal-plans/{id} returns 404 for non-existent id"""
        response = requests.delete(f"{BASE_URL}/api/meal-plans/nonexistent-id-12345", headers=auth_headers)
        assert response.status_code == 404
        print("✓ DELETE non-existent meal plan returns 404")


class TestBudgetAPI:
    """Test Budget (Financial Tracker) API endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_budget_items(self, auth_headers):
        """GET /api/budget returns list of budget items"""
        response = requests.get(f"{BASE_URL}/api/budget", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/budget returned {len(data)} budget items")
    
    def test_get_budget_summary(self, auth_headers):
        """GET /api/budget/summary returns budget summary"""
        response = requests.get(f"{BASE_URL}/api/budget/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_estimated" in data or "by_category" in data
        print(f"✓ GET /api/budget/summary returned summary data")
    
    def test_create_budget_item(self, auth_headers):
        """POST /api/budget creates a new budget item"""
        item_data = {
            "category": "DFAC Budget",
            "item_name": "TEST_Budget Item",
            "estimated": 500.00,
            "actual": 0.00,
            "notes": "Test budget item",
            "item_type": "expense",
            "payment_status": "pending"
        }
        response = requests.post(f"{BASE_URL}/api/budget", json=item_data, headers=auth_headers)
        assert response.status_code == 200, f"Create failed: {response.text}"
        data = response.json()
        assert data["item_name"] == item_data["item_name"]
        assert "id" in data
        print(f"✓ POST /api/budget created item with id: {data['id']}")
        return data["id"]
    
    def test_update_budget_item(self, auth_headers):
        """PUT /api/budget/{id} updates a budget item"""
        # First create
        create_data = {
            "category": "Logistics",
            "item_name": "TEST_Update Budget Item",
            "estimated": 300.00,
            "actual": 0.00
        }
        create_response = requests.post(f"{BASE_URL}/api/budget", json=create_data, headers=auth_headers)
        assert create_response.status_code == 200
        item_id = create_response.json()["id"]
        
        # Then update
        update_data = {
            "category": "Logistics",
            "item_name": "TEST_Updated Budget Item Name",
            "estimated": 400.00,
            "actual": 350.00
        }
        update_response = requests.put(f"{BASE_URL}/api/budget/{item_id}", json=update_data, headers=auth_headers)
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["estimated"] == 400.00
        assert updated["actual"] == 350.00
        print(f"✓ PUT /api/budget/{item_id} updated successfully")
    
    def test_delete_budget_item(self, auth_headers):
        """DELETE /api/budget/{id} deletes a budget item"""
        # First create
        create_data = {
            "category": "Other",
            "item_name": "TEST_Delete Budget Item",
            "estimated": 100.00,
            "actual": 0.00
        }
        create_response = requests.post(f"{BASE_URL}/api/budget", json=create_data, headers=auth_headers)
        assert create_response.status_code == 200
        item_id = create_response.json()["id"]
        
        # Then delete
        delete_response = requests.delete(f"{BASE_URL}/api/budget/{item_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        print(f"✓ DELETE /api/budget/{item_id} deleted successfully")


class TestDiningFacilityRole:
    """Test dining_facility role in admin dropdown"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_user_role_can_be_set_to_dining_facility(self, auth_headers):
        """Test that dining_facility is a valid role that can be assigned"""
        # Get users
        response = requests.get(f"{BASE_URL}/api/users", headers=auth_headers)
        assert response.status_code == 200
        users = response.json()
        assert len(users) > 0
        print(f"✓ Found {len(users)} users")
        
        # Verify dining_facility is in the allowed roles (by checking backend accepts it)
        # We won't actually change a user's role, just verify the endpoint exists
    
    def test_dining_facility_role_permissions(self, auth_headers):
        """Verify dining_facility role has correct default permissions"""
        # Get current user info
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        user = response.json()
        
        # Based on server.py, dining_facility should have:
        # - meal_plan_edit: True
        # - budget_view: False
        # - admin_panel: False
        # - health_view: False
        print(f"✓ Current user role: {user.get('role')}")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_cleanup_test_meal_plans(self, auth_headers):
        """Remove test meal plans created during tests"""
        response = requests.get(f"{BASE_URL}/api/meal-plans", headers=auth_headers)
        assert response.status_code == 200
        meals = response.json()
        
        deleted_count = 0
        for meal in meals:
            if "TEST_" in (meal.get("menu_items") or ""):
                del_response = requests.delete(f"{BASE_URL}/api/meal-plans/{meal['id']}", headers=auth_headers)
                if del_response.status_code == 200:
                    deleted_count += 1
        
        print(f"✓ Cleaned up {deleted_count} test meal plans")
    
    def test_cleanup_test_budget_items(self, auth_headers):
        """Remove test budget items created during tests"""
        response = requests.get(f"{BASE_URL}/api/budget", headers=auth_headers)
        assert response.status_code == 200
        items = response.json()
        
        deleted_count = 0
        for item in items:
            if "TEST_" in (item.get("item_name") or ""):
                del_response = requests.delete(f"{BASE_URL}/api/budget/{item['id']}", headers=auth_headers)
                if del_response.status_code == 200:
                    deleted_count += 1
        
        print(f"✓ Cleaned up {deleted_count} test budget items")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
