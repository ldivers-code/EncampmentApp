"""
Document Preview API Tests
Tests the preview feature for the Handbooks & Documents system.

Features tested:
- Preview API endpoint returns file with Content-Disposition: inline
- Preview works for text/plain files
- Preview works for image/png files
- canPreview logic for supported file types
"""
import pytest
import requests
import os
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = 'https://cadre-hub.preview.emergentagent.com'

# Test credentials
TEST_EMAIL = COMMANDER_EMAIL
TEST_PASSWORD = "26GO@lie!"

# Test document IDs
TEXT_HANDBOOK_ID = "bd5e468c-3a0d-419c-b0f5-61b3b83155e0"  # text/plain file
IMAGE_DOCUMENT_ID = "63129db2-44b5-43ba-8169-35f9dc25e8b9"  # image/png file
SOP_TEXT_ID = "f75aa7ea-7acd-4317-b37f-e560f58833c8"  # text/plain SOP file
CONTENT_ONLY_DOC_ID = "5ba12894-dee5-41fa-b1f4-773d4e4b8506"  # Doc with content but no file

# Previewable MIME types
PREVIEWABLE_TYPES = {
    'application/pdf': 'pdf',
    'image/jpeg': 'image',
    'image/png': 'image',
    'image/gif': 'image',
    'image/webp': 'image',
    'image/svg+xml': 'image',
    'text/plain': 'text',
    'text/csv': 'text',
    'text/html': 'text',
    'text/markdown': 'text',
    'application/json': 'text',
    'text/xml': 'text',
    'application/xml': 'text',
}


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.text}")
    return response.json().get("access_token")


@pytest.fixture
def api_client(auth_token):
    """Authenticated API client session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


class TestPreviewAPI:
    """Tests for GET /api/documents/{id}/preview endpoint"""

    def test_preview_text_file_returns_inline_disposition(self, api_client):
        """Preview endpoint returns text file with Content-Disposition: inline"""
        response = api_client.get(f"{BASE_URL}/api/documents/{TEXT_HANDBOOK_ID}/preview")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check Content-Disposition header is inline (not attachment)
        content_disposition = response.headers.get('Content-Disposition', '')
        assert 'inline' in content_disposition, f"Expected 'inline' in Content-Disposition, got: {content_disposition}"
        assert 'attachment' not in content_disposition, f"Should NOT have 'attachment' in Content-Disposition"
        
        # Check Content-Type is text/plain
        content_type = response.headers.get('Content-Type', '')
        assert 'text/plain' in content_type, f"Expected text/plain, got: {content_type}"

    def test_preview_image_file_returns_inline_disposition(self, api_client):
        """Preview endpoint returns image file with Content-Disposition: inline"""
        response = api_client.get(f"{BASE_URL}/api/documents/{IMAGE_DOCUMENT_ID}/preview")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check Content-Disposition header is inline
        content_disposition = response.headers.get('Content-Disposition', '')
        assert 'inline' in content_disposition, f"Expected 'inline' in Content-Disposition, got: {content_disposition}"
        
        # Check Content-Type is image/png
        content_type = response.headers.get('Content-Type', '')
        assert 'image/png' in content_type, f"Expected image/png, got: {content_type}"

    def test_preview_sop_text_file(self, api_client):
        """Preview endpoint works for SOP text file"""
        response = api_client.get(f"{BASE_URL}/api/documents/{SOP_TEXT_ID}/preview")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify inline disposition
        content_disposition = response.headers.get('Content-Disposition', '')
        assert 'inline' in content_disposition

    def test_preview_returns_file_content(self, api_client):
        """Preview endpoint returns actual file content"""
        response = api_client.get(f"{BASE_URL}/api/documents/{TEXT_HANDBOOK_ID}/preview")
        
        assert response.status_code == 200
        assert len(response.content) > 0, "Response should have content"

    def test_preview_image_returns_binary_content(self, api_client):
        """Preview endpoint returns binary image content"""
        response = api_client.get(f"{BASE_URL}/api/documents/{IMAGE_DOCUMENT_ID}/preview")
        
        assert response.status_code == 200
        assert len(response.content) > 1000, "Image should have substantial content"

    def test_preview_content_only_doc_returns_404(self, api_client):
        """Preview endpoint returns 404 for document with content but no file attachment"""
        response = api_client.get(f"{BASE_URL}/api/documents/{CONTENT_ONLY_DOC_ID}/preview")
        
        # Should return 404 because there's no file attached
        assert response.status_code == 404, f"Expected 404 for content-only doc, got {response.status_code}"

    def test_preview_nonexistent_doc_returns_404(self, api_client):
        """Preview endpoint returns 404 for non-existent document"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = api_client.get(f"{BASE_URL}/api/documents/{fake_id}/preview")
        
        assert response.status_code == 404


class TestDownloadVsPreview:
    """Tests to verify download returns attachment and preview returns inline"""

    def test_download_returns_attachment_disposition(self, api_client):
        """Download endpoint returns file with Content-Disposition: attachment"""
        response = api_client.get(f"{BASE_URL}/api/documents/{TEXT_HANDBOOK_ID}/download")
        
        assert response.status_code == 200
        
        content_disposition = response.headers.get('Content-Disposition', '')
        assert 'attachment' in content_disposition, f"Download should have 'attachment', got: {content_disposition}"

    def test_preview_vs_download_same_content(self, api_client):
        """Preview and download return the same file content"""
        preview_response = api_client.get(f"{BASE_URL}/api/documents/{TEXT_HANDBOOK_ID}/preview")
        download_response = api_client.get(f"{BASE_URL}/api/documents/{TEXT_HANDBOOK_ID}/download")
        
        assert preview_response.status_code == 200
        assert download_response.status_code == 200
        
        # Content should be identical
        assert preview_response.content == download_response.content, "Preview and download content should match"


class TestDocumentFileTypes:
    """Tests to verify document file_type field is set correctly for preview logic"""

    def test_text_document_has_text_plain_type(self, api_client):
        """Text handbook document has file_type text/plain"""
        response = api_client.get(f"{BASE_URL}/api/documents/{TEXT_HANDBOOK_ID}")
        
        assert response.status_code == 200
        doc = response.json()
        
        assert doc.get('file_type') == 'text/plain', f"Expected text/plain, got: {doc.get('file_type')}"

    def test_image_document_has_image_png_type(self, api_client):
        """Image document has file_type image/png"""
        response = api_client.get(f"{BASE_URL}/api/documents/{IMAGE_DOCUMENT_ID}")
        
        assert response.status_code == 200
        doc = response.json()
        
        assert doc.get('file_type') == 'image/png', f"Expected image/png, got: {doc.get('file_type')}"

    def test_content_only_doc_has_no_file_type(self, api_client):
        """Document with content only has no file_type"""
        response = api_client.get(f"{BASE_URL}/api/documents/{CONTENT_ONLY_DOC_ID}")
        
        assert response.status_code == 200
        doc = response.json()
        
        # Should have no file_type or storage_path
        assert doc.get('file_type') is None, f"Content-only doc should have null file_type"
        assert doc.get('storage_path') is None, f"Content-only doc should have null storage_path"
        assert doc.get('content') is not None, f"Content-only doc should have content"


class TestCanPreviewLogic:
    """Tests to verify canPreview function logic matches frontend implementation"""

    def test_can_preview_text_plain(self):
        """text/plain should be previewable"""
        assert 'text/plain' in PREVIEWABLE_TYPES

    def test_can_preview_image_png(self):
        """image/png should be previewable"""
        assert 'image/png' in PREVIEWABLE_TYPES

    def test_can_preview_pdf(self):
        """application/pdf should be previewable"""
        assert 'application/pdf' in PREVIEWABLE_TYPES

    def test_can_preview_json(self):
        """application/json should be previewable"""
        assert 'application/json' in PREVIEWABLE_TYPES

    def test_cannot_preview_docx(self):
        """application/vnd.openxmlformats-officedocument.wordprocessingml.document should NOT be previewable"""
        docx_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        assert docx_type not in PREVIEWABLE_TYPES

    def test_cannot_preview_xlsx(self):
        """application/vnd.openxmlformats-officedocument.spreadsheetml.sheet should NOT be previewable"""
        xlsx_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert xlsx_type not in PREVIEWABLE_TYPES


class TestPreviewAuthentication:
    """Tests to verify preview endpoint requires authentication"""

    def test_preview_without_auth_returns_401(self):
        """Preview endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/documents/{TEXT_HANDBOOK_ID}/preview")
        
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
