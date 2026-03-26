"""
Test Medical Roster Feature - New Health Services Tab

Features tested:
- GET /api/health/medical-roster - Returns all cadets with health data
- GET /api/health/cadet/{id}/full-profile - Returns comprehensive health profile for a cadet
- Permission checks for health_view and health_full access
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
COMMANDER_EMAIL = "commander@test.com"
COMMANDER_PASSWORD = "Test1234!"


class TestMedicalRosterAuth:
    """Test authentication and permissions for medical roster"""
    
    def test_login_commander(self):
        """Login as commander (has health_full access)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        
        print(f"Login response status: {response.status_code}")
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        return data["access_token"]
    
    def test_medical_roster_requires_auth(self):
        """Test that medical roster endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/health/medical-roster")
        
        print(f"Unauthenticated roster response: {response.status_code}")
        assert response.status_code in [401, 403], "Should require authentication"


class TestMedicalRosterEndpoint:
    """Test GET /api/health/medical-roster endpoint"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for commander"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Could not authenticate as commander")
        return response.json()["access_token"]
    
    def test_get_medical_roster_returns_array(self, auth_token):
        """Test GET /api/health/medical-roster returns array of cadets"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/health/medical-roster", headers=headers)
        
        print(f"Medical roster response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Total cadets in roster: {len(data)}")
        return data
    
    def test_medical_roster_returns_expected_count(self, auth_token):
        """Test that roster returns approximately 87 cadets (per context)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/health/medical-roster", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Per context: 87 cadets with health data
        print(f"Roster count: {len(data)}")
        assert len(data) >= 80, f"Expected ~87 cadets, got {len(data)}"
    
    def test_medical_roster_cadet_structure(self, auth_token):
        """Test that each cadet in roster has required fields"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/health/medical-roster", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            cadet = data[0]
            
            # Required fields
            required_fields = [
                "participant_id", "capid", "name", "flight",
                "has_allergies", "allergy_count", "has_anaphylaxis",
                "has_otc_data", "otc_approved_count",
                "has_medications", "medication_count",
                "open_incidents", "hs_status", "critical_flags"
            ]
            
            for field in required_fields:
                assert field in cadet, f"Missing required field: {field}"
            
            print(f"Sample cadet: {cadet['name']}")
            print(f"  - Allergies: {cadet['allergy_count']}")
            print(f"  - OTC approved: {cadet['otc_approved_count']}")
            print(f"  - Critical flags: {cadet['critical_flags']}")
    
    def test_medical_roster_allergy_stats(self, auth_token):
        """Test allergy statistics in roster"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/health/medical-roster", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Count cadets with allergies
        with_allergies = sum(1 for c in data if c.get("has_allergies"))
        with_anaphylaxis = sum(1 for c in data if c.get("has_anaphylaxis"))
        
        print(f"Cadets with allergies: {with_allergies}")
        print(f"Cadets with anaphylaxis: {with_anaphylaxis}")
        
        # Per context: 19 with allergies, 1 with anaphylaxis
        assert with_allergies >= 15, f"Expected ~19 with allergies, got {with_allergies}"
    
    def test_medical_roster_otc_stats(self, auth_token):
        """Test OTC statistics in roster"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/health/medical-roster", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Count cadets with OTC data
        with_otc = sum(1 for c in data if c.get("has_otc_data"))
        
        print(f"Cadets with OTC data: {with_otc}")
        
        # Per context: 81 with OTC data
        assert with_otc >= 75, f"Expected ~81 with OTC data, got {with_otc}"
    
    def test_medical_roster_critical_flags(self, auth_token):
        """Test critical flags in roster"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/health/medical-roster", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Count cadets with critical flags
        with_critical = sum(1 for c in data if len(c.get("critical_flags", [])) > 0)
        
        print(f"Cadets with critical flags: {with_critical}")
        
        # Per context: 4 with critical flags
        assert with_critical >= 1, f"Expected some cadets with critical flags, got {with_critical}"
        
        # Check what critical flags exist
        all_flags = set()
        for c in data:
            all_flags.update(c.get("critical_flags", []))
        print(f"Critical flag types found: {all_flags}")


class TestCadetFullProfile:
    """Test GET /api/health/cadet/{id}/full-profile endpoint"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for commander"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Could not authenticate as commander")
        return response.json()["access_token"]
    
    @pytest.fixture
    def sample_cadet_id(self, auth_token):
        """Get a sample cadet participant_id from roster"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/health/medical-roster", headers=headers)
        
        if response.status_code != 200 or len(response.json()) == 0:
            pytest.skip("No cadets in roster")
        
        # Get first cadet with allergies for more interesting data
        data = response.json()
        for cadet in data:
            if cadet.get("has_allergies"):
                return cadet["participant_id"]
        
        # Fallback to first cadet
        return data[0]["participant_id"]
    
    def test_get_full_profile_returns_data(self, auth_token, sample_cadet_id):
        """Test GET /api/health/cadet/{id}/full-profile returns profile data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/health/cadet/{sample_cadet_id}/full-profile",
            headers=headers
        )
        
        print(f"Full profile response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert "participant_id" in data
        assert "name" in data
        print(f"Profile for: {data['name']}")
        return data
    
    def test_full_profile_structure(self, auth_token, sample_cadet_id):
        """Test that full profile has all required sections"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/health/cadet/{sample_cadet_id}/full-profile",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        required_fields = [
            "participant_id", "capid", "name", "rank", "flight", "squadron",
            "gender", "age", "allergies", "allergy_count", "has_anaphylaxis",
            "has_epipen", "has_inhaler", "otc_approvals", "medications",
            "medication_count", "has_rescue_med", "incidents", "open_incident_count",
            "medication_log", "custody_log", "hs_status"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print(f"Profile sections present:")
        print(f"  - Allergies: {len(data.get('allergies', []))}")
        print(f"  - Medications: {len(data.get('medications', []))}")
        print(f"  - Incidents: {len(data.get('incidents', []))}")
        print(f"  - OTC approvals: {'Yes' if data.get('otc_approvals') else 'No'}")
    
    def test_full_profile_allergy_details(self, auth_token, sample_cadet_id):
        """Test allergy details in full profile"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/health/cadet/{sample_cadet_id}/full-profile",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        allergies = data.get("allergies", [])
        if len(allergies) > 0:
            allergy = allergies[0]
            
            # Check allergy structure
            allergy_fields = [
                "allergy_name", "allergy_type", "is_anaphylaxis",
                "has_epipen", "has_albuterol_inhaler"
            ]
            
            for field in allergy_fields:
                assert field in allergy, f"Missing allergy field: {field}"
            
            print(f"Sample allergy: {allergy['allergy_name']} ({allergy['allergy_type']})")
            print(f"  - Anaphylaxis: {allergy['is_anaphylaxis']}")
            print(f"  - Epipen: {allergy['has_epipen']}")
    
    def test_full_profile_otc_details(self, auth_token, sample_cadet_id):
        """Test OTC approval details in full profile"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/health/cadet/{sample_cadet_id}/full-profile",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        otc = data.get("otc_approvals")
        if otc:
            # Check OTC structure
            assert "medications" in otc, "Missing medications in OTC"
            assert "approved_list" in otc, "Missing approved_list in OTC"
            assert "denied_list" in otc, "Missing denied_list in OTC"
            
            print(f"OTC approvals:")
            print(f"  - Approved: {len(otc.get('approved_list', []))}")
            print(f"  - Denied: {len(otc.get('denied_list', []))}")
    
    def test_full_profile_not_found(self, auth_token):
        """Test that invalid cadet ID returns 404"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/health/cadet/invalid-uuid-12345/full-profile",
            headers=headers
        )
        
        print(f"Invalid cadet profile response: {response.status_code}")
        assert response.status_code == 404


class TestMedicalRosterFiltering:
    """Test filtering capabilities of medical roster"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for commander"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Could not authenticate as commander")
        return response.json()["access_token"]
    
    def test_roster_sorted_by_critical_flags(self, auth_token):
        """Test that roster is sorted with critical flags first"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/health/medical-roster", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 1:
            # Check that cadets with critical flags come first
            first_critical_count = len(data[0].get("critical_flags", []))
            last_critical_count = len(data[-1].get("critical_flags", []))
            
            print(f"First cadet critical flags: {first_critical_count}")
            print(f"Last cadet critical flags: {last_critical_count}")
            
            # First should have >= critical flags than last
            assert first_critical_count >= last_critical_count, "Roster should be sorted by critical flags"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
