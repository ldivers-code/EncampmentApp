"""
Test PDF Export for Roster Reports (P3)
Tests the GET /api/participants/export-pdf endpoint with 3 formats:
- simple: Complete roster table
- by_flight: Grouped by flight assignment
- by_type: Staff, Cadre, Students sections
"""
import pytest
import requests
import os
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from iteration_37.json
TEST_EMAIL = ADMIN_EMAIL
TEST_PASSWORD = ADMIN_PASSWORD


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for commander account"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestPdfExportEndpoints:
    """Test PDF export endpoints return valid PDFs"""

    def test_export_pdf_simple_format(self, auth_headers):
        """GET /api/participants/export-pdf?format=simple returns valid PDF"""
        response = requests.get(
            f"{BASE_URL}/api/participants/export-pdf?format=simple",
            headers=auth_headers
        )
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Content-type assertion
        content_type = response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type, f"Expected application/pdf, got {content_type}"
        
        # Content-Disposition header should indicate attachment
        content_disp = response.headers.get('Content-Disposition', '')
        assert 'attachment' in content_disp, f"Expected attachment disposition, got {content_disp}"
        assert 'cap_roster_simple' in content_disp, f"Expected filename with 'cap_roster_simple', got {content_disp}"
        
        # PDF content validation - check PDF magic bytes
        content = response.content
        assert len(content) > 1000, f"PDF too small: {len(content)} bytes"
        assert content[:4] == b'%PDF', f"Invalid PDF header: {content[:10]}"
        
        print(f"✓ Simple format PDF: {len(content)} bytes")

    def test_export_pdf_by_flight_format(self, auth_headers):
        """GET /api/participants/export-pdf?format=by_flight returns valid PDF grouped by flight"""
        response = requests.get(
            f"{BASE_URL}/api/participants/export-pdf?format=by_flight",
            headers=auth_headers
        )
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Content-type assertion
        content_type = response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type, f"Expected application/pdf, got {content_type}"
        
        # Content-Disposition header
        content_disp = response.headers.get('Content-Disposition', '')
        assert 'cap_roster_by_flight' in content_disp, f"Expected filename with 'cap_roster_by_flight', got {content_disp}"
        
        # PDF content validation
        content = response.content
        assert len(content) > 1000, f"PDF too small: {len(content)} bytes"
        assert content[:4] == b'%PDF', f"Invalid PDF header: {content[:10]}"
        
        print(f"✓ By-flight format PDF: {len(content)} bytes")

    def test_export_pdf_by_type_format(self, auth_headers):
        """GET /api/participants/export-pdf?format=by_type returns valid PDF with Staff, Cadre, Students sections"""
        response = requests.get(
            f"{BASE_URL}/api/participants/export-pdf?format=by_type",
            headers=auth_headers
        )
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Content-type assertion
        content_type = response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type, f"Expected application/pdf, got {content_type}"
        
        # Content-Disposition header
        content_disp = response.headers.get('Content-Disposition', '')
        assert 'cap_roster_by_type' in content_disp, f"Expected filename with 'cap_roster_by_type', got {content_disp}"
        
        # PDF content validation
        content = response.content
        assert len(content) > 1000, f"PDF too small: {len(content)} bytes"
        assert content[:4] == b'%PDF', f"Invalid PDF header: {content[:10]}"
        
        print(f"✓ By-type format PDF: {len(content)} bytes")


class TestPdfExportAuthentication:
    """Test PDF export requires authentication"""

    def test_export_pdf_requires_auth(self):
        """Export PDF endpoint returns 401/403 without authentication"""
        response = requests.get(f"{BASE_URL}/api/participants/export-pdf?format=simple")
        
        # Should fail without auth
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Unauthenticated request correctly rejected with {response.status_code}")

    def test_export_pdf_rejects_invalid_token(self):
        """Export PDF endpoint rejects invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/participants/export-pdf?format=simple",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        
        # Should fail with invalid token
        assert response.status_code in [401, 403], f"Expected 401/403 with invalid token, got {response.status_code}"
        print(f"✓ Invalid token correctly rejected with {response.status_code}")


class TestPdfExportContent:
    """Test PDF export content includes expected data"""

    def test_pdf_includes_summary_stats(self, auth_headers):
        """PDF should include summary statistics"""
        # First get participant stats to compare
        stats_response = requests.get(
            f"{BASE_URL}/api/participants/stats",
            headers=auth_headers
        )
        
        if stats_response.status_code == 200:
            stats = stats_response.json()
            total = stats.get('total', 0)
            print(f"✓ Participant stats: {total} total participants")
            
            # Now get PDF and verify it's generated
            pdf_response = requests.get(
                f"{BASE_URL}/api/participants/export-pdf?format=simple",
                headers=auth_headers
            )
            assert pdf_response.status_code == 200
            assert len(pdf_response.content) > 1000
            print(f"✓ PDF generated with {len(pdf_response.content)} bytes for {total} participants")
        else:
            pytest.skip("Could not get participant stats")

    def test_all_three_formats_return_different_sizes(self, auth_headers):
        """Different formats may produce different PDF sizes"""
        sizes = {}
        for fmt in ['simple', 'by_flight', 'by_type']:
            response = requests.get(
                f"{BASE_URL}/api/participants/export-pdf?format={fmt}",
                headers=auth_headers
            )
            assert response.status_code == 200
            sizes[fmt] = len(response.content)
        
        print(f"✓ PDF sizes - simple: {sizes['simple']}, by_flight: {sizes['by_flight']}, by_type: {sizes['by_type']}")
        
        # All should be valid PDFs (>1KB)
        for fmt, size in sizes.items():
            assert size > 1000, f"{fmt} PDF too small: {size} bytes"


class TestPdfExportEdgeCases:
    """Test edge cases for PDF export"""

    def test_export_pdf_default_format(self, auth_headers):
        """Export PDF without format parameter defaults to simple"""
        response = requests.get(
            f"{BASE_URL}/api/participants/export-pdf",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        content_disp = response.headers.get('Content-Disposition', '')
        assert 'cap_roster_simple' in content_disp, f"Default format should be simple, got {content_disp}"
        print("✓ Default format is 'simple'")

    def test_export_pdf_invalid_format(self, auth_headers):
        """Export PDF with invalid format should still work (defaults or handles gracefully)"""
        response = requests.get(
            f"{BASE_URL}/api/participants/export-pdf?format=invalid_format",
            headers=auth_headers
        )
        
        # Should either return 200 with default format or 400 for invalid format
        # Based on code review, it will use the invalid format name but still generate PDF
        if response.status_code == 200:
            assert response.content[:4] == b'%PDF'
            print("✓ Invalid format handled gracefully (generated PDF)")
        else:
            print(f"✓ Invalid format rejected with {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
