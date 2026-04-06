"""
Tests for Handbooks & Documents Upload System
Features:
- POST /api/documents/upload (file upload to object storage)
- GET /api/documents/{id}/download (file download)
- GET /api/documents (list with file fields)
- POST /api/documents (create document without file)
- PUT /api/documents/{id} (update document)
- DELETE /api/documents/{id} (delete document)
"""
import pytest
import requests
import os
import uuid
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials (Commander role)
TEST_EMAIL = COMMANDER_EMAIL
TEST_PASSWORD = "26GO@lie!"

# Existing test handbook ID for download testing
EXISTING_HANDBOOK_ID = "bd5e468c-3a0d-419c-b0f5-61b3b83155e0"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for commander user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    return response.json().get("access_token")


@pytest.fixture
def auth_headers(auth_token):
    """Create headers with authentication token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestDocumentUploadAPI:
    """Test POST /api/documents/upload endpoint"""

    def test_upload_handbook_with_file(self, auth_headers):
        """Upload a handbook with a file to object storage"""
        # Create a test text file
        test_content = b"This is a test handbook content for CAP Encampment"
        files = {
            'file': ('test_handbook.txt', test_content, 'text/plain')
        }
        data = {
            'title': f'TEST_Handbook_{uuid.uuid4().hex[:8]}',
            'description': 'Test handbook uploaded via API',
            'doc_type': 'handbook',
            'category': 'training_guide'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documents/upload",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == 200, f"Upload failed: {response.status_code} - {response.text}"
        result = response.json()
        
        # Verify response contains file fields
        assert 'id' in result, "Missing document id"
        assert result['title'] == data['title'], f"Title mismatch: {result['title']} != {data['title']}"
        assert result['doc_type'] == 'handbook', f"doc_type mismatch: {result['doc_type']}"
        assert result['storage_path'] is not None, "storage_path should be set for uploaded files"
        assert result['file_name'] == 'test_handbook.txt', f"file_name mismatch: {result.get('file_name')}"
        assert result['file_size'] > 0, f"file_size should be > 0: {result.get('file_size')}"
        assert result['file_type'] == 'text/plain', f"file_type mismatch: {result.get('file_type')}"
        
        print(f"✓ Handbook uploaded successfully: {result['id']}")
        return result['id']

    def test_upload_official_document_with_file(self, auth_headers):
        """Upload an official document with a file"""
        test_content = b"Official CAPF Document Test Content"
        files = {
            'file': ('capf_60_80.pdf', test_content, 'application/pdf')
        }
        data = {
            'title': f'TEST_CAPF_60_80_{uuid.uuid4().hex[:8]}',
            'description': 'Test official document',
            'doc_type': 'official_document'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documents/upload",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Upload failed: {response.status_code} - {response.text}"
        result = response.json()
        
        assert result['doc_type'] == 'official_document'
        assert result['storage_path'] is not None
        assert result['file_name'] == 'capf_60_80.pdf'
        
        print(f"✓ Official document uploaded successfully: {result['id']}")
        return result['id']

    def test_upload_without_title_fails(self, auth_headers):
        """Upload should fail without required title"""
        files = {
            'file': ('test.txt', b'test content', 'text/plain')
        }
        # Missing title
        data = {
            'description': 'Test without title',
            'doc_type': 'handbook'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documents/upload",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        # Should fail with validation error (422)
        assert response.status_code == 422, f"Expected 422, got: {response.status_code}"
        print("✓ Upload without title correctly rejected")


class TestDocumentDownloadAPI:
    """Test GET /api/documents/{id}/download endpoint"""

    def test_download_existing_handbook(self, auth_headers):
        """Download the existing test handbook if it has a file"""
        # First check if the document has a storage_path
        response = requests.get(
            f"{BASE_URL}/api/documents/{EXISTING_HANDBOOK_ID}",
            headers=auth_headers
        )
        
        if response.status_code == 404:
            pytest.skip("Test handbook not found")
        
        doc = response.json()
        if not doc.get('storage_path'):
            pytest.skip("Test handbook has no attached file")
        
        # Try to download
        response = requests.get(
            f"{BASE_URL}/api/documents/{EXISTING_HANDBOOK_ID}/download",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Download failed: {response.status_code} - {response.text}"
        assert len(response.content) > 0, "Downloaded file is empty"
        assert 'Content-Disposition' in response.headers
        
        print(f"✓ Document downloaded successfully: {len(response.content)} bytes")

    def test_download_nonexistent_document_fails(self, auth_headers):
        """Download should fail for non-existent document"""
        fake_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/documents/{fake_id}/download",
            headers=auth_headers
        )
        
        assert response.status_code == 404, f"Expected 404, got: {response.status_code}"
        print("✓ Download non-existent document correctly returns 404")

    def test_download_uploaded_document(self, auth_headers):
        """Upload a document then download it to verify round-trip"""
        # Upload
        test_content = b"Round-trip test content for download verification"
        files = {
            'file': ('roundtrip_test.txt', test_content, 'text/plain')
        }
        data = {
            'title': f'TEST_Roundtrip_{uuid.uuid4().hex[:8]}',
            'doc_type': 'handbook'
        }
        
        upload_response = requests.post(
            f"{BASE_URL}/api/documents/upload",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        assert upload_response.status_code == 200
        doc_id = upload_response.json()['id']
        
        # Download
        download_response = requests.get(
            f"{BASE_URL}/api/documents/{doc_id}/download",
            headers=auth_headers
        )
        
        assert download_response.status_code == 200
        assert download_response.content == test_content, "Downloaded content does not match uploaded content"
        
        print(f"✓ Round-trip upload/download verified for document {doc_id}")


class TestDocumentListAPI:
    """Test GET /api/documents endpoint"""

    def test_list_documents_includes_file_fields(self, auth_headers):
        """Verify document list includes new file storage fields"""
        response = requests.get(
            f"{BASE_URL}/api/documents",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        documents = response.json()
        
        assert isinstance(documents, list), "Response should be a list"
        
        # Find a document with a storage_path
        docs_with_files = [d for d in documents if d.get('storage_path')]
        
        if docs_with_files:
            doc = docs_with_files[0]
            # Verify file fields are present
            assert 'storage_path' in doc, "Missing storage_path field"
            assert 'file_name' in doc, "Missing file_name field"
            assert 'file_size' in doc, "Missing file_size field"
            assert 'file_type' in doc, "Missing file_type field"
            print(f"✓ Document list includes file fields: storage_path, file_name, file_size, file_type")
        else:
            print("✓ Document list returns successfully (no documents with files found)")

    def test_filter_handbooks_only(self, auth_headers):
        """Handbooks page filters by doc_type=handbook"""
        response = requests.get(
            f"{BASE_URL}/api/documents",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        documents = response.json()
        
        handbooks = [d for d in documents if d.get('doc_type') == 'handbook']
        print(f"✓ Found {len(handbooks)} handbooks out of {len(documents)} documents")


class TestDocumentCRUD:
    """Test Create, Read, Update, Delete operations"""

    def test_create_document_without_file(self, auth_headers):
        """Create a document without a file attachment"""
        data = {
            'title': f'TEST_TextDoc_{uuid.uuid4().hex[:8]}',
            'description': 'Text-only document',
            'doc_type': 'reference',
            'content': 'This is the document content stored as text'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documents",
            json=data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.json()
        
        assert result['title'] == data['title']
        assert result['content'] == data['content']
        assert result.get('storage_path') is None, "Text-only doc should not have storage_path"
        
        print(f"✓ Text document created: {result['id']}")
        return result['id']

    def test_update_document(self, auth_headers):
        """Update an existing document's metadata"""
        # First create a document
        create_data = {
            'title': f'TEST_ToUpdate_{uuid.uuid4().hex[:8]}',
            'description': 'Original description',
            'doc_type': 'handbook'
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/documents",
            json=create_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        doc_id = create_response.json()['id']
        
        # Update the document
        update_data = {
            'title': create_data['title'] + '_Updated',
            'description': 'Updated description',
            'doc_type': 'handbook',
            'category': 'sop'
        }
        
        update_response = requests.put(
            f"{BASE_URL}/api/documents/{doc_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert update_response.status_code == 200
        result = update_response.json()
        
        assert result['title'] == update_data['title']
        assert result['description'] == update_data['description']
        assert result['category'] == 'sop'
        assert result['version'] == 2, "Version should increment on update"
        
        print(f"✓ Document updated successfully: {doc_id}")

    def test_delete_document(self, auth_headers):
        """Delete a document"""
        # First create a document
        create_data = {
            'title': f'TEST_ToDelete_{uuid.uuid4().hex[:8]}',
            'doc_type': 'handbook'
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/documents",
            json=create_data,
            headers=auth_headers
        )
        assert create_response.status_code == 200
        doc_id = create_response.json()['id']
        
        # Delete the document
        delete_response = requests.delete(
            f"{BASE_URL}/api/documents/{doc_id}",
            headers=auth_headers
        )
        
        assert delete_response.status_code == 200
        
        # Verify document is deleted
        get_response = requests.get(
            f"{BASE_URL}/api/documents/{doc_id}",
            headers=auth_headers
        )
        
        assert get_response.status_code == 404, "Document should be deleted"
        print(f"✓ Document deleted successfully: {doc_id}")


class TestRoleBasedAccess:
    """Test role-based upload permissions"""

    def test_commander_can_upload(self, auth_headers):
        """Commander role should be able to upload documents"""
        files = {
            'file': ('commander_test.txt', b'Commander upload test', 'text/plain')
        }
        data = {
            'title': f'TEST_CmdUpload_{uuid.uuid4().hex[:8]}',
            'doc_type': 'handbook'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documents/upload",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        print("✓ Commander can upload documents")


class TestCleanup:
    """Clean up test documents"""
    
    def test_cleanup_test_documents(self, auth_headers):
        """Delete documents created during testing"""
        response = requests.get(
            f"{BASE_URL}/api/documents",
            headers=auth_headers
        )
        
        if response.status_code != 200:
            pytest.skip("Could not fetch documents for cleanup")
        
        documents = response.json()
        test_docs = [d for d in documents if d.get('title', '').startswith('TEST_')]
        
        deleted = 0
        for doc in test_docs:
            del_response = requests.delete(
                f"{BASE_URL}/api/documents/{doc['id']}",
                headers=auth_headers
            )
            if del_response.status_code == 200:
                deleted += 1
        
        print(f"✓ Cleaned up {deleted} test documents")
