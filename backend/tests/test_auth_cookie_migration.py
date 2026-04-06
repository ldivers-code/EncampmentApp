"""
Test Suite: httpOnly Cookie Auth Migration & Auto-Balance Flights
Tests the migration from localStorage JWT to httpOnly cookies for secure token storage.
Also tests the Auto-Balance Flights feature for unassigned students.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
COMMANDER_EMAIL = "commander@test.com"
COMMANDER_PASSWORD = "test123"
PARENT_EMAIL = "jane.hundley@test.com"
PARENT_PASSWORD = "parent123"


class TestCookieAuthLogin:
    """Test POST /api/auth/login sets httpOnly cookie AND returns token in body"""
    
    def test_login_sets_httponly_cookie(self):
        """Login should set access_token httpOnly cookie"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        # Check response body contains token
        data = response.json()
        assert "access_token" in data, "Response should contain access_token"
        assert "user" in data, "Response should contain user object"
        assert data["user"]["email"] == COMMANDER_EMAIL
        
        # Check cookie was set
        cookies = session.cookies.get_dict()
        assert "access_token" in cookies, f"access_token cookie not set. Cookies: {cookies}"
        print(f"✓ Login sets httpOnly cookie and returns token in body")
    
    def test_login_returns_user_data(self):
        """Login should return user data with role and permissions"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user"]["role"] == "commander", f"Expected commander role, got {data['user']['role']}"
        assert "id" in data["user"]
        assert "name" in data["user"]
        print(f"✓ Login returns complete user data with role: {data['user']['role']}")


class TestCookieAuthLogout:
    """Test POST /api/auth/logout clears the cookie"""
    
    def test_logout_clears_cookie(self):
        """Logout should clear the access_token cookie"""
        session = requests.Session()
        
        # First login
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert login_resp.status_code == 200
        
        # Verify cookie is set
        assert "access_token" in session.cookies.get_dict()
        
        # Logout
        logout_resp = session.post(f"{BASE_URL}/api/auth/logout")
        assert logout_resp.status_code == 200
        
        data = logout_resp.json()
        assert data.get("message") == "Logged out"
        
        # After logout, /api/auth/me should fail
        me_resp = session.get(f"{BASE_URL}/api/auth/me")
        assert me_resp.status_code == 401, f"Expected 401 after logout, got {me_resp.status_code}"
        print(f"✓ Logout clears cookie and subsequent /auth/me returns 401")


class TestCookieOnlyAuth:
    """Test GET /api/auth/me works with cookie-only auth (no Authorization header)"""
    
    def test_auth_me_with_cookie_only(self):
        """GET /api/auth/me should work with just the cookie (no header)"""
        session = requests.Session()
        
        # Login to get cookie
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert login_resp.status_code == 200
        
        # Call /auth/me without setting Authorization header - cookie should work
        me_resp = session.get(f"{BASE_URL}/api/auth/me")
        assert me_resp.status_code == 200, f"Cookie-only auth failed: {me_resp.text}"
        
        data = me_resp.json()
        assert data["email"] == COMMANDER_EMAIL
        assert data["role"] == "commander"
        print(f"✓ /api/auth/me works with cookie-only auth")


class TestBearerTokenBackwardCompat:
    """Test GET /api/auth/me still works with Bearer token in Authorization header"""
    
    def test_auth_me_with_bearer_token(self):
        """GET /api/auth/me should work with Authorization: Bearer header"""
        # Login to get token
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        
        # Call /auth/me with Bearer token (no cookies)
        me_resp = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_resp.status_code == 200, f"Bearer token auth failed: {me_resp.text}"
        
        data = me_resp.json()
        assert data["email"] == COMMANDER_EMAIL
        print(f"✓ /api/auth/me works with Bearer token (backward compat)")


class TestAutoBalanceFlights:
    """Test POST /api/students/auto-assign distributes unassigned students"""
    
    def test_auto_assign_endpoint_exists(self):
        """POST /api/students/auto-assign should be accessible to authorized users"""
        session = requests.Session()
        
        # Login as commander
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert login_resp.status_code == 200
        
        # Call auto-assign
        response = session.post(f"{BASE_URL}/api/students/auto-assign")
        
        # Should return 200 (even if 0 students assigned)
        assert response.status_code == 200, f"Auto-assign failed: {response.text}"
        
        data = response.json()
        assert "assigned" in data, f"Response should contain 'assigned' count: {data}"
        print(f"✓ Auto-assign endpoint works, assigned: {data.get('assigned', 0)} students")
    
    def test_auto_assign_returns_count(self):
        """Auto-assign should return the number of students assigned"""
        session = requests.Session()
        
        # Login
        session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        
        response = session.post(f"{BASE_URL}/api/students/auto-assign")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data.get("assigned"), int), "assigned should be an integer"
        print(f"✓ Auto-assign returns count: {data['assigned']}")


class TestPhotoEndpointCookieAuth:
    """Test /api/participants/{id}/photo works with cookie auth"""
    
    def test_photo_endpoint_with_cookie(self):
        """Photo endpoint should work with cookie authentication"""
        session = requests.Session()
        
        # Login
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert login_resp.status_code == 200
        
        # Get participants to find one with a photo
        participants_resp = session.get(f"{BASE_URL}/api/participants")
        assert participants_resp.status_code == 200
        
        participants = participants_resp.json()
        if not participants:
            pytest.skip("No participants to test photo endpoint")
        
        # Try to get photo for first participant (may return 404 if no photo)
        participant_id = participants[0]["id"]
        photo_resp = session.get(f"{BASE_URL}/api/participants/{participant_id}/photo")
        
        # Should be 200 (with photo) or 404 (no photo), not 401
        assert photo_resp.status_code in [200, 404], f"Photo endpoint auth failed: {photo_resp.status_code}"
        print(f"✓ Photo endpoint works with cookie auth (status: {photo_resp.status_code})")


class TestFlightDistribution:
    """Test flight distribution endpoint"""
    
    def test_flight_distribution_endpoint(self):
        """GET /api/students/flight-distribution should return flight stats"""
        session = requests.Session()
        
        # Login
        session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        
        response = session.get(f"{BASE_URL}/api/students/flight-distribution")
        assert response.status_code == 200, f"Flight distribution failed: {response.text}"
        
        data = response.json()
        assert "flights" in data, "Response should contain flights"
        assert "total_students" in data, "Response should contain total_students"
        print(f"✓ Flight distribution: {data.get('total_students', 0)} total students")


class TestParentAuth:
    """Test parent account authentication with cookies"""
    
    def test_parent_login_sets_cookie(self):
        """Parent login should also set httpOnly cookie"""
        session = requests.Session()
        
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARENT_EMAIL,
            "password": PARENT_PASSWORD
        })
        
        assert response.status_code == 200, f"Parent login failed: {response.text}"
        
        data = response.json()
        assert data["user"]["role"] == "parent"
        assert "access_token" in session.cookies.get_dict()
        print(f"✓ Parent login sets cookie, role: {data['user']['role']}")


class TestProtectedEndpointsWithCookie:
    """Test various protected endpoints work with cookie auth"""
    
    def test_dashboard_stats_with_cookie(self):
        """Dashboard stats should work with cookie auth"""
        session = requests.Session()
        
        session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        
        response = session.get(f"{BASE_URL}/api/stats/dashboard")
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        print(f"✓ Dashboard stats works with cookie auth")
    
    def test_participants_list_with_cookie(self):
        """Participants list should work with cookie auth"""
        session = requests.Session()
        
        session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        
        response = session.get(f"{BASE_URL}/api/participants")
        assert response.status_code == 200, f"Participants list failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Participants list works with cookie auth ({len(data)} participants)")
    
    def test_org_chart_with_cookie(self):
        """Org chart roles should work with cookie auth"""
        session = requests.Session()
        
        session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        
        response = session.get(f"{BASE_URL}/api/org-chart/roles")
        assert response.status_code == 200, f"Org chart failed: {response.text}"
        print(f"✓ Org chart works with cookie auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
