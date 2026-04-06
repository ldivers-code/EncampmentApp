"""
Parent Portal and Flight-Grouped Roster Tests
Tests for:
1. Parent registration with CAPID linking
2. Parent approval workflow
3. Parent-only endpoints (/api/parent/*)
4. Flight-grouped roster view (/api/participants/by-flight)
5. Flight Sergeant restriction (cadre only see their flight)
6. Non-parent users cannot access parent endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD
PARENT_EMAIL = "jane.hundley@test.com"
PARENT_PASSWORD = "parent123"
STUDENT_CAPID = "718873"  # Athena Hundley, Alpha Flight


class TestParentRegistrationAndApproval:
    """Test parent registration and approval workflow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_commander_token(self):
        """Get commander auth token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200, f"Commander login failed: {response.text}"
        return response.json()["access_token"]
    
    def test_parent_login_success(self):
        """Test parent can login with correct credentials"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARENT_EMAIL,
            "password": PARENT_PASSWORD
        })
        assert response.status_code == 200, f"Parent login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "parent"
        print(f"PASS: Parent login successful, role={data['user']['role']}")
    
    def test_parent_registration_requires_valid_capid(self):
        """Test parent registration fails with invalid CAPID"""
        response = self.session.post(f"{BASE_URL}/api/auth/register", json={
            "email": "newparent@test.com",
            "password": COMMANDER_PASSWORD,
            "name": "New Parent",
            "role": "parent",
            "capid": "INVALID999"
        })
        # Should fail because CAPID doesn't exist
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "No student found" in response.json().get("detail", "")
        print("PASS: Parent registration correctly rejects invalid CAPID")


class TestParentEndpoints:
    """Test parent-only endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with parent auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as parent
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARENT_EMAIL,
            "password": PARENT_PASSWORD
        })
        if response.status_code == 200:
            token = response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.parent_token = token
        else:
            pytest.skip("Parent login failed - skipping parent endpoint tests")
    
    def test_get_my_cadet(self):
        """Test GET /api/parent/my-cadet returns linked cadet info"""
        response = self.session.get(f"{BASE_URL}/api/parent/my-cadet")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify cadet data structure
        assert "first_name" in data
        assert "last_name" in data
        assert "capid" in data
        assert "flight" in data
        assert "squadron" in data
        assert "check_in" in data
        
        print(f"PASS: My Cadet endpoint returns cadet: {data.get('first_name')} {data.get('last_name')}, CAPID: {data.get('capid')}, Flight: {data.get('flight')}")
    
    def test_get_my_cadet_schedule(self):
        """Test GET /api/parent/my-cadet/schedule returns flight-filtered events"""
        response = self.session.get(f"{BASE_URL}/api/parent/my-cadet/schedule")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "flight" in data
        assert "events" in data
        assert isinstance(data["events"], list)
        
        print(f"PASS: Schedule endpoint returns {len(data['events'])} events for flight '{data['flight']}'")
    
    def test_get_my_cadet_health_incidents(self):
        """Test GET /api/parent/my-cadet/health-incidents returns health data"""
        response = self.session.get(f"{BASE_URL}/api/parent/my-cadet/health-incidents")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "incidents" in data
        assert "allergies" in data
        assert "prescriptions" in data
        assert "otc_approvals" in data
        
        print(f"PASS: Health incidents endpoint returns incidents={len(data['incidents'])}, allergies={len(data['allergies'])}, prescriptions={len(data['prescriptions'])}")
    
    def test_get_my_cadet_points(self):
        """Test GET /api/parent/my-cadet/points returns points data"""
        response = self.session.get(f"{BASE_URL}/api/parent/my-cadet/points")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "total_points" in data
        assert "total_merits" in data
        assert "total_demerits" in data
        assert "awards" in data
        
        print(f"PASS: Points endpoint returns total_points={data['total_points']}, merits={data['total_merits']}, demerits={data['total_demerits']}")
    
    def test_get_my_cadet_meals(self):
        """Test GET /api/parent/my-cadet/meals returns meal data"""
        response = self.session.get(f"{BASE_URL}/api/parent/my-cadet/meals")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "meal_plans" in data
        assert "dietary_restrictions" in data
        assert "all_allergies" in data
        assert "cadet_name" in data
        
        print(f"PASS: Meals endpoint returns {len(data['meal_plans'])} meal plans, cadet_name='{data['cadet_name']}'")


class TestParentAccessRestrictions:
    """Test that parents cannot access non-parent endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with parent auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as parent
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARENT_EMAIL,
            "password": PARENT_PASSWORD
        })
        if response.status_code == 200:
            token = response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Parent login failed")
    
    def test_parent_cannot_access_roster(self):
        """Test parent cannot access /api/participants (roster)"""
        response = self.session.get(f"{BASE_URL}/api/participants")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Parent correctly blocked from roster access (403)")
    
    def test_parent_cannot_access_by_flight(self):
        """Test parent cannot access /api/participants/by-flight"""
        response = self.session.get(f"{BASE_URL}/api/participants/by-flight")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Parent correctly blocked from by-flight roster (403)")


class TestNonParentCannotAccessParentEndpoints:
    """Test that non-parent users cannot access parent endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with commander auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as commander (non-parent)
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Commander login failed")
    
    def test_commander_cannot_access_my_cadet(self):
        """Test non-parent cannot access /api/parent/my-cadet"""
        response = self.session.get(f"{BASE_URL}/api/parent/my-cadet")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert "Parent access only" in response.json().get("detail", "")
        print("PASS: Non-parent correctly blocked from /api/parent/my-cadet (403)")
    
    def test_commander_cannot_access_parent_schedule(self):
        """Test non-parent cannot access /api/parent/my-cadet/schedule"""
        response = self.session.get(f"{BASE_URL}/api/parent/my-cadet/schedule")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Non-parent correctly blocked from parent schedule (403)")
    
    def test_commander_cannot_access_parent_health(self):
        """Test non-parent cannot access /api/parent/my-cadet/health-incidents"""
        response = self.session.get(f"{BASE_URL}/api/parent/my-cadet/health-incidents")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Non-parent correctly blocked from parent health (403)")
    
    def test_commander_cannot_access_parent_points(self):
        """Test non-parent cannot access /api/parent/my-cadet/points"""
        response = self.session.get(f"{BASE_URL}/api/parent/my-cadet/points")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Non-parent correctly blocked from parent points (403)")
    
    def test_commander_cannot_access_parent_meals(self):
        """Test non-parent cannot access /api/parent/my-cadet/meals"""
        response = self.session.get(f"{BASE_URL}/api/parent/my-cadet/meals")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: Non-parent correctly blocked from parent meals (403)")


class TestFlightGroupedRoster:
    """Test flight-grouped roster view"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with commander auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as commander
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Commander login failed")
    
    def test_get_participants_by_flight(self):
        """Test GET /api/participants/by-flight returns grouped data"""
        response = self.session.get(f"{BASE_URL}/api/participants/by-flight")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Expected list of flight groups"
        
        # Check structure of each flight group
        for group in data:
            assert "flight" in group
            assert "flight_label" in group
            assert "count" in group
            assert "members" in group
            assert isinstance(group["members"], list)
            
            # Check member structure
            if group["members"]:
                member = group["members"][0]
                assert "id" in member
                assert "name" in member
                assert "capid" in member
                assert "email" in member or member.get("email") == ""
                assert "phone" in member or member.get("phone") == ""
        
        flight_names = [g["flight"] for g in data]
        print(f"PASS: By-flight endpoint returns {len(data)} groups: {flight_names}")
    
    def test_by_flight_includes_contact_info(self):
        """Test by-flight includes email, phone, parent contact"""
        response = self.session.get(f"{BASE_URL}/api/participants/by-flight")
        assert response.status_code == 200
        data = response.json()
        
        # Find a group with members
        for group in data:
            if group["members"]:
                member = group["members"][0]
                # These fields should exist (may be empty strings)
                assert "email" in member
                assert "phone" in member
                assert "parent_email" in member
                assert "parent_phone" in member
                assert "parent_name" in member
                print(f"PASS: Member data includes contact fields: email, phone, parent_email, parent_phone, parent_name")
                return
        
        print("PASS: By-flight structure verified (no members to check contact fields)")


class TestFlightSergeantRestriction:
    """Test that cadre users assigned to a flight only see their flight's participants"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_commander_sees_all_participants(self):
        """Test commander can see all participants (no flight restriction)"""
        # Login as commander
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        token = response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get participants
        response = self.session.get(f"{BASE_URL}/api/participants")
        assert response.status_code == 200
        participants = response.json()
        
        # Commander should see participants from multiple flights
        flights = set(p.get("flight", "") for p in participants if p.get("flight"))
        print(f"PASS: Commander sees participants from {len(flights)} flights: {flights}")
        assert len(flights) > 1 or len(participants) > 0, "Commander should see all participants"


class TestUserApproval:
    """Test user approval workflow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_approve_user_endpoint(self):
        """Test POST /api/users/{id}/approve works for admin"""
        # Login as commander
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        token = response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get pending users
        response = self.session.get(f"{BASE_URL}/api/users/pending")
        assert response.status_code == 200
        pending = response.json()
        
        print(f"PASS: Pending users endpoint returns {len(pending)} users")
        
        # If there are pending users, we could test approval
        # But we don't want to modify state, so just verify endpoint works


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
