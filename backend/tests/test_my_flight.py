"""
Test module for My Flight Page APIs
Tests: /api/my-flight, /api/flights/{flight}/roster, /api/documents/by-flight/{flight}
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://wing-ops.preview.emergentagent.com')

class TestMyFlightAPIs:
    """Test My Flight page backend APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as commander
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "commander@test.cap.gov",
            "password": "test123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.user_data = login_response.json().get("user")
    
    # =============================================================
    # /api/my-flight endpoint tests
    # =============================================================
    
    def test_my_flight_endpoint_returns_200(self):
        """Test /api/my-flight returns 200"""
        response = self.session.get(f"{BASE_URL}/api/my-flight")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_my_flight_response_structure(self):
        """Test /api/my-flight returns expected structure"""
        response = self.session.get(f"{BASE_URL}/api/my-flight")
        assert response.status_code == 200
        
        data = response.json()
        # Check required fields
        assert "user_flight" in data
        assert "user_squadron" in data
        assert "user_role" in data
        assert "accessible_flights" in data
        assert "accessible_squadrons" in data
        assert "has_full_access" in data
    
    def test_commander_has_full_access(self):
        """Test commander has access to all flights"""
        response = self.session.get(f"{BASE_URL}/api/my-flight")
        assert response.status_code == 200
        
        data = response.json()
        assert data["has_full_access"] == True
        assert data["user_role"] == "commander"
        # Commander should have access to all 6 flights
        expected_flights = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
        for flight in expected_flights:
            assert flight in data["accessible_flights"], f"Flight {flight} not in accessible_flights"
    
    def test_my_flight_accessible_squadrons(self):
        """Test accessible squadrons are returned"""
        response = self.session.get(f"{BASE_URL}/api/my-flight")
        assert response.status_code == 200
        
        data = response.json()
        # Commander should have access to all 3 squadrons
        expected_squadrons = ["sq1", "sq2", "sq3"]
        for sq in expected_squadrons:
            assert sq in data["accessible_squadrons"], f"Squadron {sq} not in accessible_squadrons"
    
    # =============================================================
    # /api/flights/{flight}/roster endpoint tests
    # =============================================================
    
    def test_flight_roster_alpha(self):
        """Test /api/flights/alpha/roster returns 200"""
        response = self.session.get(f"{BASE_URL}/api/flights/alpha/roster")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_flight_roster_response_structure(self):
        """Test flight roster response has correct structure"""
        response = self.session.get(f"{BASE_URL}/api/flights/alpha/roster")
        assert response.status_code == 200
        
        data = response.json()
        # Check required fields
        assert "flight" in data
        assert "roster" in data
        assert "count" in data
        assert "cadre_count" in data
        assert "cadet_count" in data
        
        assert data["flight"] == "alpha"
        assert isinstance(data["roster"], list)
        assert isinstance(data["count"], int)
    
    def test_flight_roster_member_structure(self):
        """Test roster members have correct structure"""
        response = self.session.get(f"{BASE_URL}/api/flights/alpha/roster")
        assert response.status_code == 200
        
        data = response.json()
        
        # If there are roster members, check their structure
        if len(data["roster"]) > 0:
            member = data["roster"][0]
            # Check required member fields
            assert "id" in member
            assert "name" in member
            assert "is_student" in member
            # Position should be present (None for basic students)
    
    def test_all_flights_roster(self):
        """Test all flight roster endpoints"""
        flights = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
        
        for flight in flights:
            response = self.session.get(f"{BASE_URL}/api/flights/{flight}/roster")
            assert response.status_code == 200, f"Flight {flight} roster failed: {response.status_code}"
            
            data = response.json()
            assert data["flight"] == flight
    
    # =============================================================
    # /api/squadrons/{squadron}/roster endpoint tests
    # =============================================================
    
    def test_squadron_roster_sq1(self):
        """Test /api/squadrons/sq1/roster returns 200"""
        response = self.session.get(f"{BASE_URL}/api/squadrons/sq1/roster")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_squadron_roster_response_structure(self):
        """Test squadron roster response has correct structure"""
        response = self.session.get(f"{BASE_URL}/api/squadrons/sq1/roster")
        assert response.status_code == 200
        
        data = response.json()
        # Check required fields
        assert "squadron" in data
        assert "flights" in data
        assert "total_count" in data
        
        assert data["squadron"] == "sq1"
        assert isinstance(data["flights"], dict)
        # SQ1 should have alpha and bravo flights
        assert "alpha" in data["flights"]
        assert "bravo" in data["flights"]
    
    def test_squadron_roster_invalid_squadron(self):
        """Test invalid squadron returns 404"""
        response = self.session.get(f"{BASE_URL}/api/squadrons/invalid/roster")
        assert response.status_code == 404
    
    def test_all_squadrons_roster(self):
        """Test all squadron roster endpoints"""
        squadrons = {
            "sq1": ["alpha", "bravo"],
            "sq2": ["charlie", "delta"],
            "sq3": ["echo", "foxtrot"]
        }
        
        for squadron, expected_flights in squadrons.items():
            response = self.session.get(f"{BASE_URL}/api/squadrons/{squadron}/roster")
            assert response.status_code == 200, f"Squadron {squadron} roster failed: {response.status_code}"
            
            data = response.json()
            assert data["squadron"] == squadron
            for flight in expected_flights:
                assert flight in data["flights"], f"Flight {flight} not in {squadron} roster"
    
    # =============================================================
    # /api/documents/by-flight/{flight} endpoint tests
    # =============================================================
    
    def test_documents_by_flight_alpha(self):
        """Test /api/documents/by-flight/alpha returns 200"""
        response = self.session.get(f"{BASE_URL}/api/documents/by-flight/alpha")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_documents_by_flight_response_structure(self):
        """Test flight documents response has correct structure"""
        response = self.session.get(f"{BASE_URL}/api/documents/by-flight/alpha")
        assert response.status_code == 200
        
        data = response.json()
        # Check required fields
        assert "flight" in data
        assert "squadron" in data
        assert "documents" in data
        assert "total" in data
        
        assert data["flight"] == "alpha"
        assert data["squadron"] == "sq1"  # alpha is in sq1
        assert isinstance(data["documents"], dict)
    
    def test_documents_by_flight_categorization(self):
        """Test documents are properly categorized"""
        response = self.session.get(f"{BASE_URL}/api/documents/by-flight/alpha")
        assert response.status_code == 200
        
        data = response.json()
        
        # Documents should be grouped by category
        if data["total"] > 0:
            for category, docs in data["documents"].items():
                assert isinstance(docs, list)
                # Valid categories
                valid_categories = ["tlp", "pocket_class", "handbook", "sop", "form", "checklist", "reference", "other"]
                assert category in valid_categories, f"Invalid category: {category}"
    
    def test_all_flights_documents(self):
        """Test all flight document endpoints"""
        flights = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
        
        for flight in flights:
            response = self.session.get(f"{BASE_URL}/api/documents/by-flight/{flight}")
            assert response.status_code == 200, f"Flight {flight} documents failed: {response.status_code}"
            
            data = response.json()
            assert data["flight"] == flight
    
    # =============================================================
    # /api/documents/by-squadron/{squadron} endpoint tests
    # =============================================================
    
    def test_documents_by_squadron(self):
        """Test /api/documents/by-squadron/sq1 returns 200"""
        response = self.session.get(f"{BASE_URL}/api/documents/by-squadron/sq1")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_documents_by_squadron_structure(self):
        """Test squadron documents response has correct structure"""
        response = self.session.get(f"{BASE_URL}/api/documents/by-squadron/sq1")
        assert response.status_code == 200
        
        data = response.json()
        # Check required fields
        assert "squadron" in data
        assert "documents" in data
        assert "total" in data
        
        assert data["squadron"] == "sq1"
        assert isinstance(data["documents"], dict)
    
    # =============================================================
    # Document upload tests (commander only)
    # =============================================================
    
    def test_create_document_tlp(self):
        """Test creating a TLP document"""
        doc_data = {
            "title": f"TEST_TLP_{uuid.uuid4().hex[:8]}",
            "description": "Test TLP document",
            "doc_type": "tlp",
            "category": "tlp",
            "content": "Test content for TLP",
            "file_url": "https://example.com/test-tlp.pdf",
            "scope": "global"
        }
        
        response = self.session.post(f"{BASE_URL}/api/documents", json=doc_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["title"] == doc_data["title"]
        assert data["category"] == "tlp"
        assert data["scope"] == "global"
        
        # Verify document appears in flight documents (global should be visible to all)
        flight_docs = self.session.get(f"{BASE_URL}/api/documents/by-flight/alpha").json()
        doc_ids = []
        for cat_docs in flight_docs["documents"].values():
            for doc in cat_docs:
                doc_ids.append(doc["id"])
        assert data["id"] in doc_ids, "Document not found in flight documents"
        
        # Cleanup
        delete_response = self.session.delete(f"{BASE_URL}/api/documents/{data['id']}")
        assert delete_response.status_code == 200
    
    def test_create_document_flight_scoped(self):
        """Test creating a flight-scoped document"""
        doc_data = {
            "title": f"TEST_FLIGHT_DOC_{uuid.uuid4().hex[:8]}",
            "description": "Test flight document",
            "doc_type": "pocket_class",
            "category": "pocket_class",
            "content": "Flight-specific content",
            "file_url": "",
            "scope": "flight",
            "flight": "alpha"
        }
        
        response = self.session.post(f"{BASE_URL}/api/documents", json=doc_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["scope"] == "flight"
        assert data["flight"] == "alpha"
        
        # Verify document appears in alpha flight documents
        alpha_docs = self.session.get(f"{BASE_URL}/api/documents/by-flight/alpha").json()
        doc_ids = []
        for cat_docs in alpha_docs["documents"].values():
            for doc in cat_docs:
                doc_ids.append(doc["id"])
        assert data["id"] in doc_ids, "Document not found in alpha flight documents"
        
        # Verify document does NOT appear in bravo flight documents (it's flight-scoped to alpha)
        bravo_docs = self.session.get(f"{BASE_URL}/api/documents/by-flight/bravo").json()
        bravo_doc_ids = []
        for cat_docs in bravo_docs["documents"].values():
            for doc in cat_docs:
                bravo_doc_ids.append(doc["id"])
        assert data["id"] not in bravo_doc_ids, "Flight-scoped document incorrectly visible to other flight"
        
        # Cleanup
        delete_response = self.session.delete(f"{BASE_URL}/api/documents/{data['id']}")
        assert delete_response.status_code == 200
    
    def test_create_document_squadron_scoped(self):
        """Test creating a squadron-scoped document"""
        doc_data = {
            "title": f"TEST_SQ_DOC_{uuid.uuid4().hex[:8]}",
            "description": "Test squadron document",
            "doc_type": "sop",
            "category": "sop",
            "content": "Squadron-specific content",
            "scope": "squadron",
            "squadron": "sq1"
        }
        
        response = self.session.post(f"{BASE_URL}/api/documents", json=doc_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["scope"] == "squadron"
        assert data["squadron"] == "sq1"
        
        # Verify document appears in squadron documents
        sq_docs = self.session.get(f"{BASE_URL}/api/documents/by-squadron/sq1").json()
        doc_ids = []
        for cat_docs in sq_docs["documents"].values():
            for doc in cat_docs:
                doc_ids.append(doc["id"])
        assert data["id"] in doc_ids, "Document not found in squadron documents"
        
        # Cleanup
        delete_response = self.session.delete(f"{BASE_URL}/api/documents/{data['id']}")
        assert delete_response.status_code == 200
    
    def test_document_delete(self):
        """Test deleting a document"""
        # Create a document first
        doc_data = {
            "title": f"TEST_DELETE_{uuid.uuid4().hex[:8]}",
            "doc_type": "other",
            "category": "other",
            "scope": "global"
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/documents", json=doc_data)
        assert create_response.status_code == 200
        doc_id = create_response.json()["id"]
        
        # Delete the document
        delete_response = self.session.delete(f"{BASE_URL}/api/documents/{doc_id}")
        assert delete_response.status_code == 200
        
        # Verify it's deleted by trying to get it
        get_response = self.session.get(f"{BASE_URL}/api/documents/{doc_id}")
        assert get_response.status_code == 404
    
    # =============================================================
    # /api/documents/categories endpoint tests
    # =============================================================
    
    def test_document_categories(self):
        """Test /api/documents/categories returns document categories"""
        response = self.session.get(f"{BASE_URL}/api/documents/categories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        
        # Check expected categories are present (API returns list of strings)
        expected_categories = ["tlp", "pocket_class", "handbook", "sop", "form", "checklist", "reference", "other"]
        for cat in expected_categories:
            assert cat in data, f"Category {cat} not found in response"
    
    # =============================================================
    # List all flights endpoint test
    # =============================================================
    
    def test_get_flights_list(self):
        """Test /api/flights returns list of flights"""
        response = self.session.get(f"{BASE_URL}/api/flights")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 6  # 6 flights
        
        # Check flight structure
        flight_values = [f["value"] for f in data]
        expected = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
        for f in expected:
            assert f in flight_values
    
    def test_get_squadrons_list(self):
        """Test /api/squadrons returns list of squadrons"""
        response = self.session.get(f"{BASE_URL}/api/squadrons")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3  # 3 squadrons
        
        # Check squadron structure
        sq_values = [s["value"] for s in data]
        expected = ["sq1", "sq2", "sq3"]
        for s in expected:
            assert s in sq_values


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
