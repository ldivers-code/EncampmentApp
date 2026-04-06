"""
Point Tracking API Tests
- Tests categories, scores, merits/demerits, leaderboards
- Tests commander full access badge
"""

import pytest
import requests
import os
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPointsTracking:
    """Test Point Tracking API endpoints"""
    
    auth_token = None
    user_info = None
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Login with commander account for full access"""
        if TestPointsTracking.auth_token is None:
            login_url = f"{BASE_URL}/api/auth/login"
            login_data = {
                "email": "commander@test.cap.gov",
                "password": COMMANDER_PASSWORD
            }
            response = requests.post(login_url, json=login_data)
            if response.status_code == 200:
                data = response.json()
                TestPointsTracking.auth_token = data.get("access_token")
                TestPointsTracking.user_info = data.get("user")
            else:
                pytest.skip(f"Login failed with status {response.status_code}")
        
        self.headers = {
            "Authorization": f"Bearer {TestPointsTracking.auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_get_score_categories(self):
        """Test GET /api/points/categories - should return category list"""
        response = requests.get(f"{BASE_URL}/api/points/categories", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Categories should be a list"
        print(f"Found {len(data)} categories")
        
        # Categories should exist if seeded
        if len(data) > 0:
            first_cat = data[0]
            assert "name" in first_cat, "Category should have name"
            assert "category_type" in first_cat, "Category should have category_type"
            print(f"First category: {first_cat.get('name')} ({first_cat.get('category_type')})")
    
    def test_seed_default_categories(self):
        """Test POST /api/points/categories/seed-defaults - should seed categories"""
        response = requests.post(f"{BASE_URL}/api/points/categories/seed-defaults", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should have message"
        print(f"Seed result: {data.get('message')}")
    
    def test_get_cumulative_standings(self):
        """Test GET /api/points/cumulative-standings - should return flight and squadron standings"""
        response = requests.get(f"{BASE_URL}/api/points/cumulative-standings", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "flights" in data, "Response should have flights"
        assert "squadrons" in data, "Response should have squadrons"
        assert "top_cadets" in data, "Response should have top_cadets"
        assert "top_cadre" in data, "Response should have top_cadre"
        
        # Check flights structure
        flights = data.get("flights", [])
        assert isinstance(flights, list), "Flights should be a list"
        
        if len(flights) > 0:
            flight = flights[0]
            assert "flight" in flight, "Flight should have flight identifier"
            assert "total_points" in flight, "Flight should have total_points"
            print(f"Top flight: {flight.get('flight')} with {flight.get('total_points')} points")
        
        # Check squadrons structure
        squadrons = data.get("squadrons", [])
        assert isinstance(squadrons, list), "Squadrons should be a list"
        
        if len(squadrons) > 0:
            sq = squadrons[0]
            assert "squadron" in sq, "Squadron should have squadron name"
            assert "total_points" in sq, "Squadron should have total_points"
            print(f"Top squadron: {sq.get('squadron')} with {sq.get('total_points')} points")
    
    def test_get_scores(self):
        """Test GET /api/points/scores - should return scores list"""
        response = requests.get(f"{BASE_URL}/api/points/scores", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Scores should be a list"
        print(f"Found {len(data)} scores")
        
        # Check if pre-recorded score exists (per context: Alpha flight has 95 points for Barracks Inspection)
        alpha_scores = [s for s in data if s.get("target_id") == "alpha"]
        if len(alpha_scores) > 0:
            print(f"Alpha flight has {len(alpha_scores)} scores recorded")
            for s in alpha_scores:
                print(f"  - {s.get('category_name', 'Unknown')}: {s.get('points')} pts")
    
    def test_get_merit_demerits(self):
        """Test GET /api/points/merits - should return merits/demerits list"""
        response = requests.get(f"{BASE_URL}/api/points/merits", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Merits should be a list"
        print(f"Found {len(data)} merit/demerit entries")
    
    def test_get_flight_leaderboard(self):
        """Test GET /api/points/leaderboard/flights - should return flight rankings"""
        response = requests.get(f"{BASE_URL}/api/points/leaderboard/flights", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Flight leaderboard should be a list"
        
        # All 6 flights should be in leaderboard
        expected_flights = ['alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot']
        actual_flights = [f.get("flight") for f in data]
        
        for flight in expected_flights:
            assert flight in actual_flights, f"Flight {flight} should be in leaderboard"
        
        print(f"Flight leaderboard order: {actual_flights}")
    
    def test_get_squadron_leaderboard(self):
        """Test GET /api/points/leaderboard/squadrons - should return squadron rankings"""
        response = requests.get(f"{BASE_URL}/api/points/leaderboard/squadrons", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Squadron leaderboard should be a list"
        
        # 3 squadrons should be in leaderboard
        assert len(data) >= 3, "Should have at least 3 squadrons"
        
        for sq in data:
            assert "squadron" in sq, "Squadron should have squadron name"
            assert "total_points" in sq, "Squadron should have total_points"
        
        print(f"Squadron standings: {[sq.get('squadron') for sq in data]}")
    
    def test_get_individual_leaderboard(self):
        """Test GET /api/points/leaderboard/individuals - should return individual rankings"""
        response = requests.get(f"{BASE_URL}/api/points/leaderboard/individuals", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Individual leaderboard should be a list"
        print(f"Found {len(data)} individuals in leaderboard")
    
    def test_get_daily_winners(self):
        """Test GET /api/points/daily-winners - should return daily winners"""
        today = "2026-01-20"  # Use a date within context
        response = requests.get(f"{BASE_URL}/api/points/daily-winners?date={today}", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "date" in data, "Response should have date"
        assert "flight_of_day" in data, "Response should have flight_of_day"
        assert "squadron_of_day" in data, "Response should have squadron_of_day"
        assert "cadet_of_day" in data, "Response should have cadet_of_day"
        assert "cadre_of_day" in data, "Response should have cadre_of_day"
        
        print(f"Daily winners for {today}:")
        print(f"  Flight: {data.get('flight_of_day')}")
        print(f"  Squadron: {data.get('squadron_of_day')}")
    
    def test_get_points_summary(self):
        """Test GET /api/points/summary - should return point tracking summary"""
        response = requests.get(f"{BASE_URL}/api/points/summary", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "total_score_entries" in data, "Response should have total_score_entries"
        assert "total_merits" in data, "Response should have total_merits"
        assert "total_demerits" in data, "Response should have total_demerits"
        assert "active_categories" in data, "Response should have active_categories"
        
        print(f"Points Summary:")
        print(f"  Score Entries: {data.get('total_score_entries')}")
        print(f"  Merits: {data.get('total_merits')}")
        print(f"  Demerits: {data.get('total_demerits')}")
        print(f"  Categories: {data.get('active_categories')}")
    
    def test_record_score(self):
        """Test POST /api/points/scores - record a new score"""
        # First get categories
        cat_response = requests.get(f"{BASE_URL}/api/points/categories", headers=self.headers)
        categories = cat_response.json()
        
        if len(categories) == 0:
            pytest.skip("No categories available to record score")
        
        category_id = categories[0].get("id")
        
        score_data = {
            "category_id": category_id,
            "target_type": "flight",
            "target_id": "bravo",
            "target_name": "Bravo Flight",
            "points": 85.0,
            "date": "2026-01-20",
            "notes": "TEST_point_tracking automated test score"
        }
        
        response = requests.post(f"{BASE_URL}/api/points/scores", json=score_data, headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should have id"
        assert data.get("points") == 85.0, "Points should be 85"
        assert data.get("target_id") == "bravo", "Target should be bravo"
        
        print(f"Created score with ID: {data.get('id')}")
        
        # Cleanup - delete the test score
        score_id = data.get("id")
        cleanup_response = requests.delete(f"{BASE_URL}/api/points/scores/{score_id}", headers=self.headers)
        if cleanup_response.status_code == 200:
            print(f"Cleaned up test score {score_id}")
    
    def test_commander_has_full_access(self):
        """Verify commander user has full access role"""
        user = TestPointsTracking.user_info
        assert user is not None, "User info should be available after login"
        
        # Commander should have role = commander
        role = user.get("role")
        assert role == "commander", f"Expected commander role, got {role}"
        
        print(f"User role: {role}")
        print(f"User name: {user.get('name')}")
    
    def test_participants_endpoint(self):
        """Test GET /api/participants - should return participants for merit/demerit assignment"""
        response = requests.get(f"{BASE_URL}/api/participants", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Participants should be a list"
        print(f"Found {len(data)} participants")


class TestScheduleFilter:
    """Test Schedule page filter - visible to all users"""
    
    auth_token = None
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Login with commander account"""
        if TestScheduleFilter.auth_token is None:
            login_url = f"{BASE_URL}/api/auth/login"
            login_data = {
                "email": "commander@test.cap.gov",
                "password": COMMANDER_PASSWORD
            }
            response = requests.post(login_url, json=login_data)
            if response.status_code == 200:
                data = response.json()
                TestScheduleFilter.auth_token = data.get("access_token")
            else:
                pytest.skip(f"Login failed with status {response.status_code}")
        
        self.headers = {
            "Authorization": f"Bearer {TestScheduleFilter.auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_schedule_endpoint_accessible(self):
        """Test GET /api/schedule - should be accessible"""
        response = requests.get(f"{BASE_URL}/api/schedule", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Schedule should be a list"
        print(f"Found {len(data)} schedule events")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
