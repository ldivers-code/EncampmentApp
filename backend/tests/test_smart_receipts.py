"""
Test Smart Receipt Upload and Confirmation Endpoints
Tests for:
- POST /api/budget/receipt-upload - Upload receipt image with auto-categorization
- POST /api/budget/receipt-confirm - Confirm receipt items and add to budget
- GET /api/budget/receipt-uploads - Get receipt upload history
"""
import pytest
import requests
import os
import io

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
        data = response.json()
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestSmartReceiptUpload:
    """Tests for POST /api/budget/receipt-upload"""
    
    def test_receipt_upload_requires_auth(self):
        """Verify endpoint requires authentication"""
        # Create a simple test image
        files = {'file': ('test.jpg', b'fake image content', 'image/jpeg')}
        response = requests.post(f"{BASE_URL}/api/budget/receipt-upload", files=files)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Receipt upload requires authentication")
    
    def test_receipt_upload_invalid_format(self, auth_headers):
        """Verify endpoint rejects unsupported file formats"""
        files = {'file': ('test.txt', b'text content', 'text/plain')}
        response = requests.post(
            f"{BASE_URL}/api/budget/receipt-upload",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "Supported formats" in response.json().get("detail", "")
        print("PASS: Invalid file format rejected")
    
    def test_receipt_upload_accepts_jpg(self, auth_headers):
        """Verify endpoint accepts JPG files and returns parsed data"""
        # Create a minimal valid JPEG (1x1 pixel)
        # This is a valid minimal JPEG file
        jpeg_bytes = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
            0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
            0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
            0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
            0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
            0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
            0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
            0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
            0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
            0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
            0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
            0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
            0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
            0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
            0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
            0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
            0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
            0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD5, 0xDB, 0x20, 0xA8, 0xF1, 0x7E, 0xCD,
            0xBF, 0xFF, 0xD9
        ])
        
        files = {'file': ('test_receipt.jpg', jpeg_bytes, 'image/jpeg')}
        response = requests.post(
            f"{BASE_URL}/api/budget/receipt-upload",
            files=files,
            headers=auth_headers,
            timeout=60
        )
        
        # Should return 200 even if OCR fails (graceful fallback)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "receipt_id" in data, "Response should contain receipt_id"
        assert "line_items" in data, "Response should contain line_items"
        assert "available_categories" in data, "Response should contain available_categories"
        assert isinstance(data["line_items"], list), "line_items should be a list"
        assert isinstance(data["available_categories"], list), "available_categories should be a list"
        
        print(f"PASS: Receipt upload accepted - receipt_id: {data['receipt_id']}")
        print(f"  - Line items: {len(data['line_items'])}")
        print(f"  - Available categories: {len(data['available_categories'])}")
        
        return data
    
    def test_receipt_upload_accepts_png(self, auth_headers):
        """Verify endpoint accepts PNG files"""
        # Minimal valid PNG (1x1 pixel, red)
        png_bytes = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
            0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xDE, 0x00, 0x00, 0x00,
            0x0C, 0x49, 0x44, 0x41, 0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
            0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x05, 0xFE, 0xD4, 0xEF, 0x00, 0x00,
            0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        
        files = {'file': ('test_receipt.png', png_bytes, 'image/png')}
        response = requests.post(
            f"{BASE_URL}/api/budget/receipt-upload",
            files=files,
            headers=auth_headers,
            timeout=60
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "receipt_id" in data
        print("PASS: PNG file accepted")


class TestReceiptConfirm:
    """Tests for POST /api/budget/receipt-confirm"""
    
    def test_confirm_requires_auth(self):
        """Verify endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/budget/receipt-confirm", json={
            "receipt_id": "test-id",
            "items": []
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Receipt confirm requires authentication")
    
    def test_confirm_requires_receipt_id(self, auth_headers):
        """Verify endpoint requires receipt_id"""
        response = requests.post(
            f"{BASE_URL}/api/budget/receipt-confirm",
            json={"items": [{"description": "Test", "amount": 10, "category": "Logistics"}]},
            headers=auth_headers
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: Receipt confirm requires receipt_id")
    
    def test_confirm_requires_items(self, auth_headers):
        """Verify endpoint requires items"""
        response = requests.post(
            f"{BASE_URL}/api/budget/receipt-confirm",
            json={"receipt_id": "test-id", "items": []},
            headers=auth_headers
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASS: Receipt confirm requires items")
    
    def test_confirm_creates_budget_items(self, auth_headers):
        """Test full flow: upload receipt then confirm items"""
        # First upload a receipt
        jpeg_bytes = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
            0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
            0x00, 0xFB, 0xD5, 0xDB, 0x20, 0xA8, 0xF1, 0x7E, 0xCD, 0xBF, 0xFF, 0xD9
        ])
        
        files = {'file': ('confirm_test.jpg', jpeg_bytes, 'image/jpeg')}
        upload_response = requests.post(
            f"{BASE_URL}/api/budget/receipt-upload",
            files=files,
            headers=auth_headers,
            timeout=60
        )
        
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        receipt_id = upload_response.json()["receipt_id"]
        
        # Now confirm with test items
        confirm_response = requests.post(
            f"{BASE_URL}/api/budget/receipt-confirm",
            json={
                "receipt_id": receipt_id,
                "items": [
                    {"description": "TEST_Office Supplies", "amount": 25.99, "category": "Logistics", "vendor": "Test Store"},
                    {"description": "TEST_Food Items", "amount": 45.50, "category": "DFAC Budget", "vendor": "Test Store"}
                ]
            },
            headers=auth_headers
        )
        
        assert confirm_response.status_code == 200, f"Confirm failed: {confirm_response.text}"
        data = confirm_response.json()
        
        assert "message" in data, "Response should contain message"
        assert "items" in data, "Response should contain items"
        assert len(data["items"]) == 2, f"Expected 2 items, got {len(data['items'])}"
        
        # Verify created items have correct structure
        for item in data["items"]:
            assert "id" in item, "Created item should have id"
            assert "category" in item, "Created item should have category"
            assert "payment_status" in item, "Created item should have payment_status"
            assert item["payment_status"] == "paid", "Created items should be marked as paid"
        
        print(f"PASS: Receipt confirm created {len(data['items'])} budget items")
        print(f"  - Message: {data['message']}")


class TestReceiptUploads:
    """Tests for GET /api/budget/receipt-uploads"""
    
    def test_get_uploads_requires_auth(self):
        """Verify endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/budget/receipt-uploads")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Get receipt uploads requires authentication")
    
    def test_get_uploads_returns_list(self, auth_headers):
        """Verify endpoint returns list of uploads"""
        response = requests.get(
            f"{BASE_URL}/api/budget/receipt-uploads",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        
        # If there are uploads, verify structure
        if len(data) > 0:
            upload = data[0]
            assert "id" in upload, "Upload should have id"
            assert "filename" in upload, "Upload should have filename"
            assert "status" in upload, "Upload should have status"
            assert "uploaded_at" in upload, "Upload should have uploaded_at"
            print(f"PASS: Get receipt uploads returned {len(data)} records")
            print(f"  - First upload: {upload.get('filename')} ({upload.get('status')})")
        else:
            print("PASS: Get receipt uploads returned empty list (no uploads yet)")


class TestBudgetRegressionChecks:
    """Regression tests for existing budget functionality"""
    
    def test_budget_items_endpoint(self, auth_headers):
        """Verify budget items endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/budget", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Budget items should be a list"
        print(f"PASS: Budget items endpoint works - {len(data)} items")
    
    def test_budget_summary_endpoint(self, auth_headers):
        """Verify budget summary endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/budget/summary", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "total_estimated" in data or "estimated_income" in data, "Summary should have totals"
        print(f"PASS: Budget summary endpoint works")
    
    def test_payment_summary_endpoint(self, auth_headers):
        """Verify payment summary endpoint still works (regression)"""
        response = requests.get(f"{BASE_URL}/api/participants/payment-summary", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "total" in data or "participants" in data, "Payment summary should have data"
        print(f"PASS: Payment summary endpoint works (regression)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
