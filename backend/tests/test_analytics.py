"""
Test Analytics Dashboard Endpoints
- GET /api/participants/analytics/detailed - Comprehensive analytics
- GET /api/participants/pending-payments - Unpaid participants list
- GET /api/participants/analytics/export - CSV/Excel export
- GET /api/participants/analytics/summary-export - Multi-sheet Excel report
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for commander role"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "commander@test.cap.gov",
        "password": "Password123!"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Return auth headers for requests"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestAnalyticsEndpoints:
    """Tests for analytics API endpoints"""
    
    def test_detailed_analytics_endpoint_returns_200(self, auth_headers):
        """Test that detailed analytics endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/participants/analytics/detailed",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify top-level structure
        assert 'total_count' in data, "Missing total_count field"
        assert 'by_role' in data, "Missing by_role field"
        assert 'by_rank' in data, "Missing by_rank field"
        assert 'by_wing' in data, "Missing by_wing field"
        assert 'by_region' in data, "Missing by_region field"
        assert 'by_gender' in data, "Missing by_gender field"
        assert 'age_stats' in data, "Missing age_stats field"
        assert 'pending_payments' in data, "Missing pending_payments field"
        
        print(f"Analytics returned {data['total_count']} participants")
        
    def test_detailed_analytics_has_role_breakdown(self, auth_headers):
        """Test analytics has correct role structure (seniors, staff, cadre, students)"""
        response = requests.get(
            f"{BASE_URL}/api/participants/analytics/detailed",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        by_role = data.get('by_role', {})
        
        # Check all required role categories exist
        for role in ['seniors', 'staff', 'cadre', 'students']:
            assert role in by_role, f"Missing role: {role}"
            role_data = by_role[role]
            assert 'count' in role_data, f"Missing count for {role}"
            assert 'male' in role_data, f"Missing male count for {role}"
            assert 'female' in role_data, f"Missing female count for {role}"
            
        print(f"Role counts - Seniors: {by_role['seniors']['count']}, Staff: {by_role['staff']['count']}, Cadre: {by_role['cadre']['count']}, Students: {by_role['students']['count']}")
        
    def test_detailed_analytics_has_age_statistics(self, auth_headers):
        """Test analytics includes age statistics (avg, min, max)"""
        response = requests.get(
            f"{BASE_URL}/api/participants/analytics/detailed",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        age_stats = data.get('age_stats', {})
        total = age_stats.get('total', {})
        
        assert 'avg' in total, "Missing average age"
        assert 'min' in total, "Missing min age"
        assert 'max' in total, "Missing max age"
        
        print(f"Age stats - Avg: {total['avg']}, Min: {total['min']}, Max: {total['max']}")
        
    def test_detailed_analytics_has_pending_payments(self, auth_headers):
        """Test analytics includes pending payments list"""
        response = requests.get(
            f"{BASE_URL}/api/participants/analytics/detailed",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        pending = data.get('pending_payments', [])
        assert isinstance(pending, list), "pending_payments should be a list"
        
        if len(pending) > 0:
            # Verify structure of pending payment entry
            first = pending[0]
            assert 'capid' in first, "Missing capid in pending payment"
            assert 'name' in first, "Missing name in pending payment"
            
        print(f"Found {len(pending)} pending payments")


class TestPendingPaymentsEndpoint:
    """Tests for dedicated pending payments endpoint"""
    
    def test_pending_payments_endpoint_returns_200(self, auth_headers):
        """Test pending payments endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/participants/pending-payments",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert 'count' in data, "Missing count field"
        assert 'participants' in data, "Missing participants field"
        assert isinstance(data['participants'], list), "participants should be a list"
        
        print(f"Pending payments endpoint: {data['count']} unpaid participants")
        
    def test_pending_payments_has_contact_info(self, auth_headers):
        """Test pending payments includes contact info for follow-up"""
        response = requests.get(
            f"{BASE_URL}/api/participants/pending-payments",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if data['count'] > 0:
            participant = data['participants'][0]
            # Should have contact fields for follow-up
            assert 'email' in participant, "Missing email field"
            assert 'phone' in participant, "Missing phone field"
            assert 'participant_type' in participant, "Missing participant_type"
            assert 'unit' in participant, "Missing unit field"
            print(f"First unpaid: {participant.get('name')} - {participant.get('unit')}")
        else:
            print("No pending payments to verify")


class TestExportEndpoints:
    """Tests for export functionality"""
    
    def test_csv_export_returns_file(self, auth_headers):
        """Test CSV export returns a file download"""
        response = requests.get(
            f"{BASE_URL}/api/participants/analytics/export?format=csv",
            headers=auth_headers
        )
        assert response.status_code == 200, f"CSV export failed: {response.text}"
        
        # Check content type is CSV
        content_type = response.headers.get('content-type', '')
        assert 'text/csv' in content_type or 'application/octet-stream' in content_type, f"Unexpected content-type: {content_type}"
        
        # Check Content-Disposition header for filename
        content_disp = response.headers.get('content-disposition', '')
        assert 'attachment' in content_disp, "Missing attachment header"
        assert '.csv' in content_disp, "CSV filename not in header"
        
        # Verify we got actual content
        assert len(response.content) > 0, "Empty CSV file"
        
        print(f"CSV export: {len(response.content)} bytes")
        
    def test_excel_export_returns_file(self, auth_headers):
        """Test Excel export returns an xlsx file"""
        response = requests.get(
            f"{BASE_URL}/api/participants/analytics/export?format=excel",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Excel export failed: {response.text}"
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        assert 'spreadsheetml' in content_type or 'application/octet-stream' in content_type, f"Unexpected content-type: {content_type}"
        
        # Check Content-Disposition header for filename
        content_disp = response.headers.get('content-disposition', '')
        assert 'attachment' in content_disp, "Missing attachment header"
        assert '.xlsx' in content_disp, "Excel filename not in header"
        
        # Verify we got actual content
        assert len(response.content) > 0, "Empty Excel file"
        
        print(f"Excel export: {len(response.content)} bytes")
        
    def test_full_report_export_returns_multi_sheet_excel(self, auth_headers):
        """Test full summary report returns multi-sheet Excel"""
        response = requests.get(
            f"{BASE_URL}/api/participants/analytics/summary-export",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Summary export failed: {response.text}"
        
        # Check content type
        content_type = response.headers.get('content-type', '')
        assert 'spreadsheetml' in content_type or 'application/octet-stream' in content_type, f"Unexpected content-type: {content_type}"
        
        # Check Content-Disposition header
        content_disp = response.headers.get('content-disposition', '')
        assert 'attachment' in content_disp, "Missing attachment header"
        assert 'full_report' in content_disp or '.xlsx' in content_disp, "Report filename not in header"
        
        # Verify content size (multi-sheet should be larger)
        assert len(response.content) > 1000, f"File too small for multi-sheet Excel: {len(response.content)} bytes"
        
        print(f"Full report export: {len(response.content)} bytes")


class TestAnalyticsAuthentication:
    """Test that analytics endpoints require authentication"""
    
    def test_detailed_analytics_requires_auth(self):
        """Test detailed analytics requires authentication"""
        response = requests.get(f"{BASE_URL}/api/participants/analytics/detailed")
        assert response.status_code in [401, 403], f"Should require auth, got: {response.status_code}"
        
    def test_pending_payments_requires_auth(self):
        """Test pending payments requires authentication"""
        response = requests.get(f"{BASE_URL}/api/participants/pending-payments")
        assert response.status_code in [401, 403], f"Should require auth, got: {response.status_code}"
        
    def test_csv_export_requires_auth(self):
        """Test CSV export requires authentication"""
        response = requests.get(f"{BASE_URL}/api/participants/analytics/export")
        assert response.status_code in [401, 403], f"Should require auth, got: {response.status_code}"
        
    def test_excel_export_requires_auth(self):
        """Test Excel export requires authentication"""
        response = requests.get(f"{BASE_URL}/api/participants/analytics/export?format=excel")
        assert response.status_code in [401, 403], f"Should require auth, got: {response.status_code}"
        
    def test_summary_export_requires_auth(self):
        """Test summary export requires authentication"""
        response = requests.get(f"{BASE_URL}/api/participants/analytics/summary-export")
        assert response.status_code in [401, 403], f"Should require auth, got: {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
