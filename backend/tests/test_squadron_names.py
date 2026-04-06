"""
Test suite for verifying squadron name refactoring from 'Squadron 1/2/3' to '6th CTS', '21st CTS', '22nd CTS'.
This test verifies that all API endpoints return the correct squadron labels.
"""
import pytest
import requests
import os
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSquadronNameRefactoring:
    """Tests for squadron name changes in API responses"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed - skipping tests")
    
    def test_squadrons_endpoint_returns_correct_labels(self):
        """Test /api/squadrons endpoint returns 6th CTS, 21st CTS, 22nd CTS labels"""
        response = self.session.get(f"{BASE_URL}/api/squadrons")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        squadrons = response.json()
        assert isinstance(squadrons, list), "Expected list response"
        
        # Extract all labels
        labels = [sq.get('label') for sq in squadrons]
        
        # Verify correct squadron names are present
        assert '6th CTS' in labels, "6th CTS should be in squadron labels"
        assert '21st CTS' in labels, "21st CTS should be in squadron labels"
        assert '22nd CTS' in labels, "22nd CTS should be in squadron labels"
        
        # Verify old names are NOT present
        assert 'Squadron 1' not in labels, "Squadron 1 should not be in labels"
        assert 'Squadron 2' not in labels, "Squadron 2 should not be in labels"
        assert 'Squadron 3' not in labels, "Squadron 3 should not be in labels"
        
        print(f"Squadron labels verified: {labels}")
    
    def test_squadrons_endpoint_values(self):
        """Test /api/squadrons endpoint returns correct values"""
        response = self.session.get(f"{BASE_URL}/api/squadrons")
        assert response.status_code == 200
        
        squadrons = response.json()
        
        # Extract values
        values = [sq.get('value') for sq in squadrons]
        
        # Verify expected values
        assert '6th_cts' in values, "6th_cts value should be present"
        assert '21st_cts' in values, "21st_cts value should be present"
        assert '22nd_cts' in values, "22nd_cts value should be present"
        
        # Verify old values are NOT present
        assert 'sq1' not in values, "sq1 should not be in values"
        assert 'sq2' not in values, "sq2 should not be in values"
        assert 'sq3' not in values, "sq3 should not be in values"
        
        print(f"Squadron values verified: {values}")
    
    def test_flights_endpoint_squadron_mapping(self):
        """Test /api/flights endpoint returns correct squadron mappings"""
        response = self.session.get(f"{BASE_URL}/api/flights")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        flights = response.json()
        assert isinstance(flights, list), "Expected list response"
        
        # Verify flight to squadron mapping
        expected_mappings = {
            'alpha': '6th_cts',
            'bravo': '6th_cts',
            'charlie': '21st_cts',
            'delta': '21st_cts',
            'echo': '22nd_cts',
            'foxtrot': '22nd_cts'
        }
        
        for flight in flights:
            flight_value = flight.get('value')
            squadron = flight.get('squadron')
            
            if flight_value in expected_mappings:
                expected_squadron = expected_mappings[flight_value]
                assert squadron == expected_squadron, f"Flight {flight_value} should map to {expected_squadron}, got {squadron}"
        
        # Verify old squadron values are NOT present
        squadrons_in_flights = [f.get('squadron') for f in flights]
        assert 'sq1' not in squadrons_in_flights, "sq1 should not be in flight squadrons"
        assert 'sq2' not in squadrons_in_flights, "sq2 should not be in flight squadrons"
        assert 'sq3' not in squadrons_in_flights, "sq3 should not be in flight squadrons"
        
        print(f"Flight mappings verified")
    
    def test_api_health(self):
        """Test API is responding correctly"""
        response = self.session.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert 'message' in data, "Response should contain message"
        print(f"API health check passed: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
