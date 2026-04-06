"""
Test suite for Live Budget Tracking features:
- Quick update actual value (PATCH /api/budget/{id}/actual)
- Mark as paid functionality (POST /api/budget/{id}/mark-paid)
- Variance calculations
- Payment status tracking
"""

import pytest
import requests
import os
from datetime import datetime
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data
COMMANDER_CREDENTIALS = {"email": COMMANDER_EMAIL, "password": COMMANDER_PASSWORD}


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for commander user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=COMMANDER_CREDENTIALS
    )
    if response.status_code != 200:
        # Try to register first
        register_response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={**COMMANDER_CREDENTIALS, "name": "Commander Test"}
        )
        if register_response.status_code == 200:
            return register_response.json()["access_token"]
        pytest.skip("Unable to authenticate")
    return response.json()["access_token"]


@pytest.fixture
def api_client(auth_token):
    """Session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture
def test_budget_item(api_client):
    """Create a test budget item for testing updates"""
    create_response = api_client.post(
        f"{BASE_URL}/api/budget",
        json={
            "category": "Facility",
            "item_name": "TEST_Live_Budget_Item",
            "estimated": 1000.0,
            "actual": 0.0,
            "item_type": "expense",
            "payment_status": "pending",
            "vendor": "Test Vendor"
        }
    )
    assert create_response.status_code == 200, f"Failed to create test item: {create_response.text}"
    item = create_response.json()
    yield item
    
    # Cleanup
    api_client.delete(f"{BASE_URL}/api/budget/{item['id']}")


class TestQuickUpdateActualAPI:
    """Test PATCH /api/budget/{id}/actual endpoint"""
    
    def test_quick_update_actual_value(self, api_client, test_budget_item):
        """Test updating actual value via PATCH endpoint"""
        item_id = test_budget_item["id"]
        
        # Update actual value
        response = api_client.patch(
            f"{BASE_URL}/api/budget/{item_id}/actual",
            json={"actual": 850.50}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify actual was updated
        assert data["actual"] == 850.50
        assert data["id"] == item_id
        assert data["estimated"] == 1000.0  # Should be unchanged
        
    def test_quick_update_actual_with_status(self, api_client, test_budget_item):
        """Test updating actual value with payment status"""
        item_id = test_budget_item["id"]
        
        response = api_client.patch(
            f"{BASE_URL}/api/budget/{item_id}/actual",
            json={
                "actual": 1050.00,
                "payment_status": "paid",
                "payment_date": "2026-01-15"
            }
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["actual"] == 1050.00
        assert data["payment_status"] == "paid"
        assert data["payment_date"] == "2026-01-15"
        
    def test_quick_update_preserves_other_fields(self, api_client, test_budget_item):
        """Verify other fields are preserved during quick update"""
        item_id = test_budget_item["id"]
        
        # Update actual
        response = api_client.patch(
            f"{BASE_URL}/api/budget/{item_id}/actual",
            json={"actual": 500.00}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify other fields are preserved
        assert data["category"] == "Facility"
        assert data["item_name"] == "TEST_Live_Budget_Item"
        assert data["vendor"] == "Test Vendor"
        assert data["item_type"] == "expense"
        
    def test_quick_update_nonexistent_item(self, api_client):
        """Test updating non-existent item returns 404"""
        response = api_client.patch(
            f"{BASE_URL}/api/budget/nonexistent-id/actual",
            json={"actual": 100.0}
        )
        
        assert response.status_code == 404


class TestMarkAsPaidAPI:
    """Test POST /api/budget/{id}/mark-paid endpoint"""
    
    def test_mark_as_paid_sets_status(self, api_client, test_budget_item):
        """Test mark-paid sets payment_status to paid"""
        item_id = test_budget_item["id"]
        
        response = api_client.post(f"{BASE_URL}/api/budget/{item_id}/mark-paid")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["payment_status"] == "paid"
        
    def test_mark_as_paid_sets_payment_date(self, api_client, test_budget_item):
        """Test mark-paid sets payment_date to today"""
        item_id = test_budget_item["id"]
        
        response = api_client.post(f"{BASE_URL}/api/budget/{item_id}/mark-paid")
        
        assert response.status_code == 200
        data = response.json()
        
        # Payment date should be today
        today = datetime.now().strftime("%Y-%m-%d")
        assert data["payment_date"] == today
        
    def test_mark_as_paid_sets_actual_to_estimated_if_zero(self, api_client):
        """Test mark-paid sets actual=estimated when actual is 0"""
        # Create item with actual=0
        create_response = api_client.post(
            f"{BASE_URL}/api/budget",
            json={
                "category": "Facility",
                "item_name": "TEST_Mark_Paid_No_Actual",
                "estimated": 500.0,
                "actual": 0.0,  # No actual value set
                "item_type": "expense",
                "payment_status": "pending"
            }
        )
        assert create_response.status_code == 200
        item = create_response.json()
        item_id = item["id"]
        
        try:
            # Mark as paid
            response = api_client.post(f"{BASE_URL}/api/budget/{item_id}/mark-paid")
            
            assert response.status_code == 200
            data = response.json()
            
            # Actual should now equal estimated
            assert data["actual"] == 500.0
            assert data["payment_status"] == "paid"
        finally:
            api_client.delete(f"{BASE_URL}/api/budget/{item_id}")
            
    def test_mark_as_paid_preserves_existing_actual(self, api_client):
        """Test mark-paid preserves actual value if already set"""
        # Create item with actual value
        create_response = api_client.post(
            f"{BASE_URL}/api/budget",
            json={
                "category": "Facility",
                "item_name": "TEST_Mark_Paid_With_Actual",
                "estimated": 500.0,
                "actual": 450.0,  # Has actual value
                "item_type": "expense",
                "payment_status": "pending"
            }
        )
        assert create_response.status_code == 200
        item = create_response.json()
        item_id = item["id"]
        
        try:
            # Mark as paid
            response = api_client.post(f"{BASE_URL}/api/budget/{item_id}/mark-paid")
            
            assert response.status_code == 200
            data = response.json()
            
            # Actual should remain 450 (not changed to estimated)
            assert data["actual"] == 450.0
            assert data["payment_status"] == "paid"
        finally:
            api_client.delete(f"{BASE_URL}/api/budget/{item_id}")
            
    def test_mark_as_paid_nonexistent_item(self, api_client):
        """Test mark-paid on non-existent item returns 404"""
        response = api_client.post(f"{BASE_URL}/api/budget/nonexistent-id/mark-paid")
        
        assert response.status_code == 404


class TestPaymentStatusFiltering:
    """Test filtering budget items by payment status"""
    
    def test_get_budget_includes_payment_status(self, api_client):
        """Verify budget items include payment_status field"""
        response = api_client.get(f"{BASE_URL}/api/budget")
        
        assert response.status_code == 200
        items = response.json()
        
        if len(items) > 0:
            # Check that payment_status field exists
            assert "payment_status" in items[0]
            # Payment status should be one of: pending, paid, cancelled
            for item in items[:5]:  # Check first 5
                assert item.get("payment_status") in ["pending", "paid", "cancelled", None]


class TestBudgetSummaryWithVariance:
    """Test budget summary includes variance calculations"""
    
    def test_budget_summary_returns_variance(self, api_client):
        """Verify budget summary returns variance data"""
        response = api_client.get(f"{BASE_URL}/api/budget/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify summary structure
        assert "total_estimated" in data
        assert "total_actual" in data
        assert "variance" in data
        assert "by_category" in data
        
        # Verify variance calculation
        expected_variance = data["total_estimated"] - data["total_actual"]
        assert data["variance"] == expected_variance


class TestAccessControlForNewEndpoints:
    """Test that new endpoints require finance access"""
    
    def test_quick_update_requires_auth(self):
        """Test PATCH /api/budget/{id}/actual requires authentication"""
        response = requests.patch(
            f"{BASE_URL}/api/budget/some-id/actual",
            json={"actual": 100.0}
        )
        
        assert response.status_code in [401, 403]
        
    def test_mark_paid_requires_auth(self):
        """Test POST /api/budget/{id}/mark-paid requires authentication"""
        response = requests.post(f"{BASE_URL}/api/budget/some-id/mark-paid")
        
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
