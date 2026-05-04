"""
Budget Features Test Suite
Tests for:
- Budget CRUD operations (create, read, update, delete budget items)
- Food expense settings (cost per person per day configuration)
- Receipt upload/delete functionality
- Finance role access restrictions
- Budget summary API
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

# Test credentials
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD
CADET_EMAIL = "cadet_test_budget@test.com"
CADET_PASSWORD = os.environ.get("TEST_CADET_PASSWORD", "cadetpass123")
FINANCE_EMAIL = "finance_test@test.com"
FINANCE_PASSWORD = os.environ.get("TEST_FINANCE_PASSWORD", "financepass123")


class TestBudgetSetup:
    """Setup tests - ensure commander user exists and can login"""
    
    @pytest.fixture(scope="class")
    def commander_token(self):
        """Get commander auth token"""
        # First try to login
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        
        if response.status_code == 200:
            return response.json().get("access_token")
        
        # If login fails, register the commander
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD,
            "name": "Test Commander",
            "role": "commander"
        })
        
        if response.status_code == 200:
            return response.json().get("access_token")
        
        pytest.skip("Cannot authenticate as commander")
    
    def test_commander_can_login(self, commander_token):
        """Test that commander token is obtained"""
        assert commander_token is not None
        print(f"SUCCESS: Commander authenticated")


class TestBudgetCRUD:
    """Test Budget CRUD operations"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for commander"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Commander login failed")
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    def created_item_id(self, auth_headers):
        """Create a test budget item and return its ID"""
        response = requests.post(f"{BASE_URL}/api/budget", json={
            "category": "Food & Meals",
            "item_name": "TEST_Catering Service",
            "estimated": 500.00,
            "actual": 0.00,
            "vendor": "ABC Catering",
            "item_type": "expense",
            "payment_status": "pending",
            "notes": "Test budget item for cleanup"
        }, headers=auth_headers)
        
        if response.status_code == 200:
            item_id = response.json().get("id")
            yield item_id
            # Cleanup: delete the item
            requests.delete(f"{BASE_URL}/api/budget/{item_id}", headers=auth_headers)
        else:
            yield None
    
    def test_get_budget_returns_list(self, auth_headers):
        """GET /api/budget returns array of budget items"""
        response = requests.get(f"{BASE_URL}/api/budget", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: GET /api/budget returns list with {len(data)} items")
    
    def test_create_budget_item(self, auth_headers):
        """POST /api/budget creates a new budget item"""
        test_item = {
            "category": "Logistics",
            "item_name": "TEST_Transportation Fuel",
            "estimated": 350.00,
            "actual": 325.50,
            "vendor": "Shell Gas Station",
            "item_type": "expense",
            "payment_status": "paid",
            "notes": "Test item - please delete"
        }
        
        response = requests.post(f"{BASE_URL}/api/budget", json=test_item, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["category"] == "Logistics"
        assert data["item_name"] == "TEST_Transportation Fuel"
        assert data["estimated"] == 350.00
        assert data["actual"] == 325.50
        assert data["vendor"] == "Shell Gas Station"
        assert data["item_type"] == "expense"
        assert data["payment_status"] == "paid"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/budget/{data['id']}", headers=auth_headers)
        print("SUCCESS: Budget item created with all required fields")
    
    def test_create_income_item(self, auth_headers):
        """POST /api/budget can create income items"""
        income_item = {
            "category": "Income",
            "item_name": "TEST_Registration Fees",
            "estimated": 5000.00,
            "actual": 4850.00,
            "vendor": "Wing HQ",
            "item_type": "income",
            "payment_status": "paid",
            "notes": "Student registration fees"
        }
        
        response = requests.post(f"{BASE_URL}/api/budget", json=income_item, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["item_type"] == "income"
        assert data["category"] == "Income"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/budget/{data['id']}", headers=auth_headers)
        print("SUCCESS: Income budget item created")
    
    def test_update_budget_item(self, auth_headers, created_item_id):
        """PUT /api/budget/{id} updates existing budget item"""
        if not created_item_id:
            pytest.skip("No item ID available")
        
        update_data = {
            "category": "Food & Meals",
            "item_name": "TEST_Catering Service Updated",
            "estimated": 600.00,
            "actual": 575.00,
            "vendor": "XYZ Catering",
            "item_type": "expense",
            "payment_status": "paid",
            "notes": "Updated test item"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/budget/{created_item_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["item_name"] == "TEST_Catering Service Updated"
        assert data["estimated"] == 600.00
        assert data["actual"] == 575.00
        assert data["payment_status"] == "paid"
        print("SUCCESS: Budget item updated")
    
    def test_delete_budget_item(self, auth_headers):
        """DELETE /api/budget/{id} removes budget item"""
        # Create an item to delete
        response = requests.post(f"{BASE_URL}/api/budget", json={
            "category": "Supplies",
            "item_name": "TEST_Delete_Me",
            "estimated": 100.00,
            "actual": 0.00,
            "item_type": "expense"
        }, headers=auth_headers)
        
        assert response.status_code == 200
        item_id = response.json().get("id")
        
        # Delete the item
        delete_response = requests.delete(
            f"{BASE_URL}/api/budget/{item_id}",
            headers=auth_headers
        )
        
        assert delete_response.status_code == 200
        
        # Verify deletion by trying to get budget and checking item is gone
        get_response = requests.get(f"{BASE_URL}/api/budget", headers=auth_headers)
        items = get_response.json()
        item_ids = [i["id"] for i in items]
        assert item_id not in item_ids
        print("SUCCESS: Budget item deleted and verified removal")


class TestBudgetSummary:
    """Test Budget Summary API"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for commander"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Commander login failed")
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_budget_summary(self, auth_headers):
        """GET /api/budget/summary returns summary data"""
        response = requests.get(f"{BASE_URL}/api/budget/summary", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "total_estimated" in data
        assert "total_actual" in data
        assert "variance" in data
        assert "by_category" in data
        
        # Data types
        assert isinstance(data["total_estimated"], (int, float))
        assert isinstance(data["total_actual"], (int, float))
        assert isinstance(data["by_category"], dict)
        
        print(f"SUCCESS: Budget summary - Est: ${data['total_estimated']}, Actual: ${data['total_actual']}")


class TestFoodExpenseSettings:
    """Test Food Expense Settings (cost per person per day)"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for commander"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Commander login failed")
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_food_expense_settings(self, auth_headers):
        """GET /api/budget/food-settings returns food expense configuration"""
        response = requests.get(f"{BASE_URL}/api/budget/food-settings", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "cost_per_person_per_day" in data
        assert "total_participants" in data
        assert "total_days" in data
        assert "total_food_budget" in data
        
        # Validate calculation: total = cost * participants * days
        expected_total = data["cost_per_person_per_day"] * data["total_participants"] * data["total_days"]
        assert data["total_food_budget"] == expected_total
        
        print(f"SUCCESS: Food settings - ${data['cost_per_person_per_day']}/person/day × {data['total_participants']} people × {data['total_days']} days = ${data['total_food_budget']}")
    
    def test_update_food_expense_settings(self, auth_headers):
        """PUT /api/budget/food-settings updates settings"""
        # First get current settings
        get_response = requests.get(f"{BASE_URL}/api/budget/food-settings", headers=auth_headers)
        original_settings = get_response.json()
        
        # Update settings
        new_settings = {
            "cost_per_person_per_day": 18.50,
            "total_participants": 120,
            "total_days": 7,
            "notes": "Updated from test"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/budget/food-settings",
            json=new_settings,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["cost_per_person_per_day"] == 18.50
        assert data["total_participants"] == 120
        assert data["total_days"] == 7
        
        # Verify calculation
        expected_total = 18.50 * 120 * 7  # 15540.0
        assert data["total_food_budget"] == expected_total
        
        print(f"SUCCESS: Food settings updated - total_food_budget = ${data['total_food_budget']}")
        
        # Restore original settings
        requests.put(f"{BASE_URL}/api/budget/food-settings", json={
            "cost_per_person_per_day": original_settings.get("cost_per_person_per_day", 15.0),
            "total_participants": original_settings.get("total_participants", 0),
            "total_days": original_settings.get("total_days", 8)
        }, headers=auth_headers)
    
    def test_partial_update_food_settings(self, auth_headers):
        """PUT /api/budget/food-settings allows partial updates"""
        # Only update cost_per_person_per_day
        response = requests.put(
            f"{BASE_URL}/api/budget/food-settings",
            json={"cost_per_person_per_day": 20.00},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["cost_per_person_per_day"] == 20.00
        
        print("SUCCESS: Partial update of food settings works")
        
        # Restore
        requests.put(f"{BASE_URL}/api/budget/food-settings", 
                     json={"cost_per_person_per_day": 15.0}, headers=auth_headers)


class TestFinanceRoleAccess:
    """Test Finance role can access budget, Cadet cannot"""
    
    @pytest.fixture(scope="class")
    def commander_headers(self):
        """Get commander headers to manage roles"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Commander login failed")
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def finance_user_token(self, commander_headers):
        """Create and get finance user token"""
        # Try to login first
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": FINANCE_EMAIL,
            "password": FINANCE_PASSWORD
        })
        
        if response.status_code == 200:
            user = response.json().get("user")
            # Update role to finance if not already
            if user.get("role") != "finance":
                requests.put(
                    f"{BASE_URL}/api/users/{user['id']}/role?role=finance",
                    headers=commander_headers
                )
            return response.json().get("access_token")
        
        # Register new finance user
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": FINANCE_EMAIL,
            "password": FINANCE_PASSWORD,
            "name": "Test Finance User",
            "role": "cadet"  # Will be promoted to finance
        })
        
        if response.status_code == 200:
            user = response.json().get("user")
            # Update to finance role
            requests.put(
                f"{BASE_URL}/api/users/{user['id']}/role?role=finance",
                headers=commander_headers
            )
            # Re-login to get new token with updated role
            login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": FINANCE_EMAIL,
                "password": FINANCE_PASSWORD
            })
            return login_response.json().get("access_token")
        
        return None
    
    @pytest.fixture(scope="class")
    def cadet_user_token(self):
        """Create and get cadet user token"""
        # Try to login first
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CADET_EMAIL,
            "password": CADET_PASSWORD
        })
        
        if response.status_code == 200:
            return response.json().get("access_token")
        
        # Register new cadet user
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": CADET_EMAIL,
            "password": CADET_PASSWORD,
            "name": "Test Cadet User",
            "role": "cadet"
        })
        
        if response.status_code == 200:
            return response.json().get("access_token")
        
        return None
    
    def test_finance_role_can_access_budget(self, finance_user_token):
        """Finance role can GET /api/budget"""
        if not finance_user_token:
            pytest.skip("Finance user not created")
        
        headers = {"Authorization": f"Bearer {finance_user_token}"}
        response = requests.get(f"{BASE_URL}/api/budget", headers=headers)
        
        # Finance should have access
        assert response.status_code == 200
        print("SUCCESS: Finance role can access budget")
    
    def test_finance_role_can_access_food_settings(self, finance_user_token):
        """Finance role can GET /api/budget/food-settings"""
        if not finance_user_token:
            pytest.skip("Finance user not created")
        
        headers = {"Authorization": f"Bearer {finance_user_token}"}
        response = requests.get(f"{BASE_URL}/api/budget/food-settings", headers=headers)
        
        assert response.status_code == 200
        print("SUCCESS: Finance role can access food settings")
    
    def test_cadet_cannot_access_budget(self, cadet_user_token):
        """Cadet role gets 403 on GET /api/budget"""
        if not cadet_user_token:
            pytest.skip("Cadet user not created")
        
        headers = {"Authorization": f"Bearer {cadet_user_token}"}
        response = requests.get(f"{BASE_URL}/api/budget", headers=headers)
        
        assert response.status_code == 403
        assert "restricted" in response.json().get("detail", "").lower() or "access" in response.json().get("detail", "").lower()
        print("SUCCESS: Cadet role denied budget access (403)")
    
    def test_cadet_cannot_access_food_settings(self, cadet_user_token):
        """Cadet role gets 403 on GET /api/budget/food-settings"""
        if not cadet_user_token:
            pytest.skip("Cadet user not created")
        
        headers = {"Authorization": f"Bearer {cadet_user_token}"}
        response = requests.get(f"{BASE_URL}/api/budget/food-settings", headers=headers)
        
        assert response.status_code == 403
        print("SUCCESS: Cadet role denied food settings access (403)")
    
    def test_cadet_cannot_create_budget_item(self, cadet_user_token):
        """Cadet role gets 403 on POST /api/budget"""
        if not cadet_user_token:
            pytest.skip("Cadet user not created")
        
        headers = {"Authorization": f"Bearer {cadet_user_token}"}
        response = requests.post(f"{BASE_URL}/api/budget", json={
            "category": "Supplies",
            "item_name": "Should Fail",
            "estimated": 100,
            "item_type": "expense"
        }, headers=headers)
        
        assert response.status_code == 403
        print("SUCCESS: Cadet role cannot create budget items (403)")


class TestReceiptUpload:
    """Test receipt upload functionality"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for commander"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Commander login failed")
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    def budget_item_for_receipt(self, auth_headers):
        """Create a budget item for receipt testing"""
        response = requests.post(f"{BASE_URL}/api/budget", json={
            "category": "Supplies",
            "item_name": "TEST_Receipt_Upload_Item",
            "estimated": 150.00,
            "actual": 145.00,
            "item_type": "expense"
        }, headers=auth_headers)
        
        if response.status_code == 200:
            item_id = response.json().get("id")
            yield item_id
            # Cleanup
            requests.delete(f"{BASE_URL}/api/budget/{item_id}", headers=auth_headers)
        else:
            yield None
    
    def test_upload_receipt_to_budget_item(self, auth_headers, budget_item_for_receipt):
        """POST /api/budget/{id}/receipt uploads image"""
        if not budget_item_for_receipt:
            pytest.skip("No budget item created")
        
        # Create a simple test image (1x1 pixel PNG)
        import base64
        # This is a minimal valid PNG
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        
        files = {
            'file': ('receipt.png', png_data, 'image/png')
        }
        
        response = requests.post(
            f"{BASE_URL}/api/budget/{budget_item_for_receipt}/receipt",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "uploaded" in data["message"].lower()
        print("SUCCESS: Receipt uploaded to budget item")
    
    def test_delete_receipt_from_budget_item(self, auth_headers, budget_item_for_receipt):
        """DELETE /api/budget/{id}/receipt removes receipt"""
        if not budget_item_for_receipt:
            pytest.skip("No budget item created")
        
        # First upload a receipt
        import base64
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        
        files = {'file': ('receipt.png', png_data, 'image/png')}
        requests.post(
            f"{BASE_URL}/api/budget/{budget_item_for_receipt}/receipt",
            files=files,
            headers=auth_headers
        )
        
        # Now delete the receipt
        response = requests.delete(
            f"{BASE_URL}/api/budget/{budget_item_for_receipt}/receipt",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert "deleted" in response.json().get("message", "").lower()
        print("SUCCESS: Receipt deleted from budget item")
    
    def test_upload_receipt_invalid_file_type(self, auth_headers, budget_item_for_receipt):
        """POST /api/budget/{id}/receipt rejects invalid file types"""
        if not budget_item_for_receipt:
            pytest.skip("No budget item created")
        
        # Try to upload a text file (not allowed)
        files = {
            'file': ('invalid.txt', b'This is not an image', 'text/plain')
        }
        
        response = requests.post(
            f"{BASE_URL}/api/budget/{budget_item_for_receipt}/receipt",
            files=files,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        print("SUCCESS: Invalid file type rejected (400)")


class TestAdminPageFinanceRole:
    """Test that Admin page shows Finance role option"""
    
    @pytest.fixture(scope="class")
    def commander_headers(self):
        """Get commander headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Commander login failed")
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_update_user_role_to_finance(self, commander_headers):
        """Commander can update user role to 'finance'"""
        # Get list of users
        response = requests.get(f"{BASE_URL}/api/users", headers=commander_headers)
        assert response.status_code == 200
        
        users = response.json()
        if len(users) < 2:
            pytest.skip("Need at least 2 users to test role update")
        
        # Find a non-commander user to update
        test_user = None
        for user in users:
            if user["role"] != "commander":
                test_user = user
                break
        
        if not test_user:
            pytest.skip("No non-commander user to test")
        
        original_role = test_user["role"]
        
        # Update role to finance
        response = requests.put(
            f"{BASE_URL}/api/users/{test_user['id']}/role?role=finance",
            headers=commander_headers
        )
        
        assert response.status_code == 200
        
        # Verify the change
        verify_response = requests.get(f"{BASE_URL}/api/users", headers=commander_headers)
        updated_users = verify_response.json()
        updated_user = next((u for u in updated_users if u["id"] == test_user["id"]), None)
        
        assert updated_user is not None
        assert updated_user["role"] == "finance"
        
        print("SUCCESS: User role updated to 'finance'")
        
        # Restore original role
        requests.put(
            f"{BASE_URL}/api/users/{test_user['id']}/role?role={original_role}",
            headers=commander_headers
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
