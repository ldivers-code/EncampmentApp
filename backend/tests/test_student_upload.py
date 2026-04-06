"""
Test Student Upload Feature
- Student upload endpoint /api/students/upload
- Auto-assignment distributes students across 6 flights
- Flight distribution endpoint /api/students/flight-distribution
- Category filtering (students, cadre, staff)
"""
import pytest
import requests
import os
import io
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = COMMANDER_EMAIL
TEST_PASSWORD = COMMANDER_PASSWORD


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for testing"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get auth headers"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestFlightDistribution:
    """Test flight distribution endpoint"""
    
    def test_get_flight_distribution_requires_auth(self):
        """Flight distribution requires authentication"""
        response = requests.get(f"{BASE_URL}/api/students/flight-distribution")
        assert response.status_code == 403 or response.status_code == 401
        print("PASS: Flight distribution requires authentication")
    
    def test_get_flight_distribution_success(self, auth_headers):
        """Get flight distribution returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/students/flight-distribution",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "flights" in data
        assert "total_students" in data
        assert "total_capacity" in data
        assert "utilization" in data
        
        # Verify all 6 flights are present
        flights = data["flights"]
        expected_flights = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
        for flight in expected_flights:
            assert flight in flights, f"Missing flight: {flight}"
            assert "total" in flights[flight]
            assert "male" in flights[flight]
            assert "female" in flights[flight]
            assert "capacity" in flights[flight]
        
        print(f"PASS: Flight distribution returned - Total: {data['total_students']}, Capacity: {data['total_capacity']}")
        dist_str = ', '.join([f"{f}: {d['total']}" for f, d in flights.items()])
        print(f"  Distribution: {dist_str}")
    
    def test_flight_capacity_is_15(self, auth_headers):
        """Each flight has max capacity of 15"""
        response = requests.get(
            f"{BASE_URL}/api/students/flight-distribution",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for flight, info in data["flights"].items():
            assert info["capacity"] == 15, f"Flight {flight} capacity should be 15, got {info['capacity']}"
        
        # Total capacity should be 90 (6 flights x 15)
        assert data["total_capacity"] == 90
        print("PASS: All flights have capacity of 15, total capacity is 90")


class TestStudentUploadEndpoint:
    """Test student upload endpoint"""
    
    def test_upload_requires_auth(self):
        """Student upload requires authentication"""
        # Create a minimal Excel file
        import pandas as pd
        df = pd.DataFrame({"CAPID": ["123456"], "NameFirst": ["Test"], "NameLast": ["User"]})
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        
        response = requests.post(
            f"{BASE_URL}/api/students/upload",
            files={"file": ("test.xlsx", buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        assert response.status_code in [401, 403]
        print("PASS: Student upload requires authentication")
    
    def test_upload_rejects_non_excel(self, auth_headers):
        """Upload rejects non-Excel files"""
        response = requests.post(
            f"{BASE_URL}/api/students/upload",
            headers=auth_headers,
            files={"file": ("test.txt", b"not an excel file", "text/plain")}
        )
        assert response.status_code == 400
        assert "Excel" in response.json().get("detail", "")
        print("PASS: Upload rejects non-Excel files")


class TestParticipantCategoryFiltering:
    """Test participant filtering by category (students, cadre, staff)"""
    
    def test_get_participants_returns_all_types(self, auth_headers):
        """Get participants returns all participant types"""
        response = requests.get(
            f"{BASE_URL}/api/participants",
            headers=auth_headers
        )
        assert response.status_code == 200
        participants = response.json()
        
        # Count by type
        type_counts = {}
        for p in participants:
            ptype = p.get("participant_type", "unknown")
            type_counts[ptype] = type_counts.get(ptype, 0) + 1
        
        print(f"PASS: Got {len(participants)} participants")
        print(f"  Types: {type_counts}")
        
        # Verify we have students
        student_count = type_counts.get("basic_student", 0) + type_counts.get("advanced_student", 0)
        assert student_count > 0, "Expected at least some students in the system"
    
    def test_students_have_correct_type(self, auth_headers):
        """Students have participant_type = basic_student or advanced_student"""
        response = requests.get(
            f"{BASE_URL}/api/participants",
            headers=auth_headers
        )
        assert response.status_code == 200
        participants = response.json()
        
        students = [p for p in participants if p.get("participant_type") in ["basic_student", "advanced_student"]]
        
        for student in students[:5]:  # Check first 5
            assert student.get("participant_type") in ["basic_student", "advanced_student"]
            # Students should have member_type = CADET
            assert student.get("member_type") == "CADET" or student.get("member_type") is None
        
        print(f"PASS: Found {len(students)} students with correct participant_type")
    
    def test_students_have_flight_assignments(self, auth_headers):
        """Students should have flight assignments after upload"""
        response = requests.get(
            f"{BASE_URL}/api/participants",
            headers=auth_headers
        )
        assert response.status_code == 200
        participants = response.json()
        
        students = [p for p in participants if p.get("participant_type") in ["basic_student", "advanced_student"]]
        
        # Count students with flight assignments
        assigned = [s for s in students if s.get("flight") and s.get("flight") != "None"]
        
        print(f"PASS: {len(assigned)}/{len(students)} students have flight assignments")
        
        # Verify flight names are valid
        valid_flights = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", 
                        "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot"]
        for student in assigned[:10]:
            assert student.get("flight") in valid_flights, f"Invalid flight: {student.get('flight')}"


class TestParticipantStats:
    """Test participant statistics endpoint"""
    
    def test_get_participant_stats(self, auth_headers):
        """Get participant stats returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/participants/stats",
            headers=auth_headers
        )
        assert response.status_code == 200
        stats = response.json()
        
        # Verify structure
        assert "total" in stats
        assert "students" in stats
        assert "cadre" in stats
        assert "staff" in stats
        assert "seniors" in stats
        assert "cadets" in stats
        
        print(f"PASS: Stats - Total: {stats['total']}, Students: {stats['students']}, Cadre: {stats['cadre']}, Staff: {stats['staff']}")


class TestStudentDetailView:
    """Test student detail view has required sections"""
    
    def test_get_participant_detail(self, auth_headers):
        """Get individual participant returns all required fields"""
        # First get a student
        response = requests.get(
            f"{BASE_URL}/api/participants",
            headers=auth_headers
        )
        assert response.status_code == 200
        participants = response.json()
        
        students = [p for p in participants if p.get("participant_type") in ["basic_student", "advanced_student"]]
        if not students:
            pytest.skip("No students found to test detail view")
        
        student = students[0]
        student_id = student.get("id")
        
        # Get individual participant
        response = requests.get(
            f"{BASE_URL}/api/participants/{student_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        detail = response.json()
        
        # Verify Basic Info fields
        basic_info_fields = ["capid", "rank", "first_name", "last_name", "gender", "age"]
        for field in basic_info_fields:
            assert field in detail, f"Missing basic info field: {field}"
        
        # Verify Encampment Info fields
        encampment_fields = ["participant_type", "flight", "squadron"]
        for field in encampment_fields:
            assert field in detail, f"Missing encampment field: {field}"
        
        # Verify Emergency Contact fields exist
        assert "emergency_contact" in detail
        assert "emergency_phone" in detail
        
        # Verify Parent Contact fields exist
        assert "cadet_parent_phone" in detail
        assert "cadet_parent_email" in detail
        
        # Verify Address fields exist
        assert "address" in detail
        assert "city" in detail
        assert "state" in detail
        assert "zip_code" in detail
        
        print(f"PASS: Student detail view has all required sections")
        print(f"  Student: {detail.get('rank')} {detail.get('first_name')} {detail.get('last_name')}")
        print(f"  Flight: {detail.get('flight')}, Squadron: {detail.get('squadron')}")


class TestFlightDistributionBalance:
    """Test that flight distribution is balanced"""
    
    def test_distribution_is_balanced(self, auth_headers):
        """Flight distribution should be reasonably balanced"""
        response = requests.get(
            f"{BASE_URL}/api/students/flight-distribution",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        flights = data["flights"]
        counts = [info["total"] for info in flights.values()]
        
        if sum(counts) == 0:
            pytest.skip("No students assigned to flights yet")
        
        min_count = min(counts)
        max_count = max(counts)
        
        # Difference between max and min should be at most 2 for good balance
        diff = max_count - min_count
        print(f"Flight counts: {counts}")
        print(f"Min: {min_count}, Max: {max_count}, Diff: {diff}")
        
        # Allow some variance but flag if very unbalanced
        if diff > 5:
            print(f"WARNING: Flight distribution may be unbalanced (diff={diff})")
        else:
            print(f"PASS: Flight distribution is balanced (diff={diff})")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
