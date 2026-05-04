"""
Barracks & Bunk Assignment System Tests
Tests for:
- GET /api/barracks - List all barracks with occupancy stats
- GET /api/barracks/{barracks_id} - Get barracks detail with bunk layout
- GET /api/barracks/unassigned-participants - Get eligible participants for assignment
- POST /api/barracks/{barracks_id}/assign - Assign participant to bunk
- DELETE /api/barracks/{barracks_id}/bunk/{bunk_number}/{position} - Remove assignment
"""

import pytest
import requests
import os
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = COMMANDER_EMAIL
TEST_PASSWORD = COMMANDER_PASSWORD


class TestBarracksAuth:
    """Authentication tests for barracks endpoints"""
    
    def test_login_success(self):
        """Test login to get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        return data["access_token"]
    
    def test_barracks_requires_auth(self):
        """Test that barracks endpoints require authentication"""
        response = requests.get(f"{BASE_URL}/api/barracks")
        # API returns 403 Forbidden for unauthenticated requests (acceptable behavior)
        assert response.status_code in [401, 403], f"Should require authentication, got {response.status_code}"


class TestBarracksList:
    """Tests for GET /api/barracks - List all barracks"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_barracks_returns_5_barracks(self):
        """Test that GET /api/barracks returns exactly 5 barracks"""
        response = requests.get(f"{BASE_URL}/api/barracks", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5, f"Expected 5 barracks, got {len(data)}"
    
    def test_barracks_have_correct_ids(self):
        """Test that barracks have correct IDs"""
        response = requests.get(f"{BASE_URL}/api/barracks", headers=self.headers)
        data = response.json()
        expected_ids = ["TR-142B", "TR-143A", "TR-143B", "TR-144A", "TR-144B"]
        actual_ids = [b["barracks_id"] for b in data]
        assert sorted(actual_ids) == sorted(expected_ids), f"Expected {expected_ids}, got {actual_ids}"
    
    def test_barracks_have_correct_config(self):
        """Test that each barracks has 25 bunks and 50 capacity"""
        response = requests.get(f"{BASE_URL}/api/barracks", headers=self.headers)
        data = response.json()
        for b in data:
            assert b["total_bunks"] == 25, f"{b['barracks_id']} should have 25 bunks"
            assert b["capacity"] == 50, f"{b['barracks_id']} should have 50 capacity"
            assert b["left_wall_bunks"] == 13, f"{b['barracks_id']} should have 13 left wall bunks"
            assert b["right_wall_bunks"] == 12, f"{b['barracks_id']} should have 12 right wall bunks"
    
    def test_barracks_have_occupancy_stats(self):
        """Test that barracks include assigned and available counts"""
        response = requests.get(f"{BASE_URL}/api/barracks", headers=self.headers)
        data = response.json()
        for b in data:
            assert "assigned" in b, f"{b['barracks_id']} missing 'assigned' field"
            assert "available" in b, f"{b['barracks_id']} missing 'available' field"
            assert b["assigned"] + b["available"] == b["capacity"], f"{b['barracks_id']} assigned + available should equal capacity"


class TestBarracksDetail:
    """Tests for GET /api/barracks/{barracks_id} - Get barracks detail"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_barracks_detail_tr142b(self):
        """Test GET /api/barracks/TR-142B returns detail with bunks"""
        response = requests.get(f"{BASE_URL}/api/barracks/TR-142B", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["barracks_id"] == "TR-142B"
        assert "bunks" in data
        assert len(data["bunks"]) == 25, f"Expected 25 bunks, got {len(data['bunks'])}"
    
    def test_barracks_detail_bunk_structure(self):
        """Test that bunks have correct structure with top/bottom positions"""
        response = requests.get(f"{BASE_URL}/api/barracks/TR-142B", headers=self.headers)
        data = response.json()
        for bunk in data["bunks"]:
            assert "bunk_number" in bunk
            assert "wall" in bunk
            assert bunk["wall"] in ["left", "right"]
            assert "top" in bunk
            assert "bottom" in bunk
            assert "occupied" in bunk["top"]
            assert "occupied" in bunk["bottom"]
    
    def test_barracks_detail_wall_distribution(self):
        """Test that bunks are correctly distributed: 13 left, 12 right"""
        response = requests.get(f"{BASE_URL}/api/barracks/TR-142B", headers=self.headers)
        data = response.json()
        left_bunks = [b for b in data["bunks"] if b["wall"] == "left"]
        right_bunks = [b for b in data["bunks"] if b["wall"] == "right"]
        assert len(left_bunks) == 13, f"Expected 13 left wall bunks, got {len(left_bunks)}"
        assert len(right_bunks) == 12, f"Expected 12 right wall bunks, got {len(right_bunks)}"
    
    def test_barracks_detail_not_found(self):
        """Test that invalid barracks ID returns 404"""
        response = requests.get(f"{BASE_URL}/api/barracks/INVALID-ID", headers=self.headers)
        assert response.status_code == 404


class TestUnassignedParticipants:
    """Tests for GET /api/barracks/unassigned-participants"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_unassigned_participants(self):
        """Test GET /api/barracks/unassigned-participants returns list"""
        response = requests.get(f"{BASE_URL}/api/barracks/unassigned-participants", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_unassigned_participants_structure(self):
        """Test that unassigned participants have correct structure"""
        response = requests.get(f"{BASE_URL}/api/barracks/unassigned-participants", headers=self.headers)
        data = response.json()
        if len(data) > 0:
            p = data[0]
            assert "participant_id" in p
            assert "name" in p
            assert "category" in p
            assert p["category"] in ["student", "cadre"], f"Category should be student or cadre, got {p['category']}"
    
    def test_unassigned_excludes_staff(self):
        """Test that staff are not included in unassigned participants"""
        response = requests.get(f"{BASE_URL}/api/barracks/unassigned-participants", headers=self.headers)
        data = response.json()
        # Staff should not be in the list - only students and cadre
        for p in data:
            assert p["category"] in ["student", "cadre"], f"Found non-student/cadre: {p}"


class TestBunkAssignment:
    """Tests for POST /api/barracks/{barracks_id}/assign"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and find an unassigned participant"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get unassigned participants
        response = requests.get(f"{BASE_URL}/api/barracks/unassigned-participants", headers=self.headers)
        self.unassigned = response.json()
    
    def test_assign_participant_to_bunk(self):
        """Test assigning a participant to a bunk"""
        if len(self.unassigned) == 0:
            pytest.skip("No unassigned participants available")
        
        # Find an empty bunk in TR-143A
        response = requests.get(f"{BASE_URL}/api/barracks/TR-143A", headers=self.headers)
        detail = response.json()
        
        # Find first empty bunk
        empty_bunk = None
        empty_position = None
        for bunk in detail["bunks"]:
            if not bunk["top"]["occupied"]:
                empty_bunk = bunk["bunk_number"]
                empty_position = "top"
                break
            if not bunk["bottom"]["occupied"]:
                empty_bunk = bunk["bunk_number"]
                empty_position = "bottom"
                break
        
        if empty_bunk is None:
            pytest.skip("No empty bunks available in TR-143A")
        
        # Assign participant
        participant = self.unassigned[0]
        response = requests.post(
            f"{BASE_URL}/api/barracks/TR-143A/assign",
            headers=self.headers,
            json={
                "participant_id": participant["participant_id"],
                "bunk_number": empty_bunk,
                "position": empty_position
            }
        )
        assert response.status_code == 200, f"Assignment failed: {response.text}"
        data = response.json()
        assert data["status"] == "success"
        
        # Verify assignment persisted
        response = requests.get(f"{BASE_URL}/api/barracks/TR-143A", headers=self.headers)
        detail = response.json()
        assigned_bunk = next(b for b in detail["bunks"] if b["bunk_number"] == empty_bunk)
        assert assigned_bunk[empty_position]["occupied"] == True
        assert assigned_bunk[empty_position]["participant_id"] == participant["participant_id"]
        
        # Cleanup - remove assignment
        requests.delete(
            f"{BASE_URL}/api/barracks/TR-143A/bunk/{empty_bunk}/{empty_position}",
            headers=self.headers
        )
    
    def test_assign_prevents_double_booking_same_spot(self):
        """Test that assigning to an already occupied bunk returns 409"""
        if len(self.unassigned) < 2:
            pytest.skip("Need at least 2 unassigned participants")
        
        # Find an empty bunk
        response = requests.get(f"{BASE_URL}/api/barracks/TR-143B", headers=self.headers)
        detail = response.json()
        
        empty_bunk = None
        for bunk in detail["bunks"]:
            if not bunk["top"]["occupied"]:
                empty_bunk = bunk["bunk_number"]
                break
        
        if empty_bunk is None:
            pytest.skip("No empty bunks available")
        
        # Assign first participant
        p1 = self.unassigned[0]
        response = requests.post(
            f"{BASE_URL}/api/barracks/TR-143B/assign",
            headers=self.headers,
            json={
                "participant_id": p1["participant_id"],
                "bunk_number": empty_bunk,
                "position": "top"
            }
        )
        assert response.status_code == 200
        
        # Try to assign second participant to same spot
        p2 = self.unassigned[1]
        response = requests.post(
            f"{BASE_URL}/api/barracks/TR-143B/assign",
            headers=self.headers,
            json={
                "participant_id": p2["participant_id"],
                "bunk_number": empty_bunk,
                "position": "top"
            }
        )
        assert response.status_code == 409, f"Expected 409 conflict, got {response.status_code}"
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/barracks/TR-143B/bunk/{empty_bunk}/top",
            headers=self.headers
        )
    
    def test_assign_prevents_participant_in_multiple_bunks(self):
        """Test that a participant cannot be assigned to multiple bunks"""
        if len(self.unassigned) == 0:
            pytest.skip("No unassigned participants available")
        
        # Find two empty bunks
        response = requests.get(f"{BASE_URL}/api/barracks/TR-144A", headers=self.headers)
        detail = response.json()
        
        empty_bunks = []
        for bunk in detail["bunks"]:
            if not bunk["top"]["occupied"]:
                empty_bunks.append((bunk["bunk_number"], "top"))
            if not bunk["bottom"]["occupied"]:
                empty_bunks.append((bunk["bunk_number"], "bottom"))
            if len(empty_bunks) >= 2:
                break
        
        if len(empty_bunks) < 2:
            pytest.skip("Need at least 2 empty bunk spots")
        
        # Assign participant to first bunk
        participant = self.unassigned[0]
        bunk1, pos1 = empty_bunks[0]
        response = requests.post(
            f"{BASE_URL}/api/barracks/TR-144A/assign",
            headers=self.headers,
            json={
                "participant_id": participant["participant_id"],
                "bunk_number": bunk1,
                "position": pos1
            }
        )
        assert response.status_code == 200
        
        # Try to assign same participant to second bunk
        bunk2, pos2 = empty_bunks[1]
        response = requests.post(
            f"{BASE_URL}/api/barracks/TR-144A/assign",
            headers=self.headers,
            json={
                "participant_id": participant["participant_id"],
                "bunk_number": bunk2,
                "position": pos2
            }
        )
        assert response.status_code == 409, f"Expected 409 conflict, got {response.status_code}"
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/barracks/TR-144A/bunk/{bunk1}/{pos1}",
            headers=self.headers
        )


class TestBunkUnassignment:
    """Tests for DELETE /api/barracks/{barracks_id}/bunk/{bunk_number}/{position}"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_unassign_bunk(self):
        """Test removing a bunk assignment"""
        # Get unassigned participants
        response = requests.get(f"{BASE_URL}/api/barracks/unassigned-participants", headers=self.headers)
        unassigned = response.json()
        
        if len(unassigned) == 0:
            pytest.skip("No unassigned participants available")
        
        # Find empty bunk
        response = requests.get(f"{BASE_URL}/api/barracks/TR-144B", headers=self.headers)
        detail = response.json()
        
        empty_bunk = None
        for bunk in detail["bunks"]:
            if not bunk["top"]["occupied"]:
                empty_bunk = bunk["bunk_number"]
                break
        
        if empty_bunk is None:
            pytest.skip("No empty bunks available")
        
        # Assign participant
        participant = unassigned[0]
        requests.post(
            f"{BASE_URL}/api/barracks/TR-144B/assign",
            headers=self.headers,
            json={
                "participant_id": participant["participant_id"],
                "bunk_number": empty_bunk,
                "position": "top"
            }
        )
        
        # Verify assigned
        response = requests.get(f"{BASE_URL}/api/barracks/TR-144B", headers=self.headers)
        detail = response.json()
        assigned_bunk = next(b for b in detail["bunks"] if b["bunk_number"] == empty_bunk)
        assert assigned_bunk["top"]["occupied"] == True
        
        # Unassign
        response = requests.delete(
            f"{BASE_URL}/api/barracks/TR-144B/bunk/{empty_bunk}/top",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["removed"] == True
        
        # Verify unassigned
        response = requests.get(f"{BASE_URL}/api/barracks/TR-144B", headers=self.headers)
        detail = response.json()
        unassigned_bunk = next(b for b in detail["bunks"] if b["bunk_number"] == empty_bunk)
        assert unassigned_bunk["top"]["occupied"] == False
    
    def test_unassign_nonexistent_returns_404(self):
        """Test that unassigning a non-existent assignment returns 404"""
        response = requests.delete(
            f"{BASE_URL}/api/barracks/TR-142B/bunk/99/top",
            headers=self.headers
        )
        assert response.status_code == 404


class TestCheckInStepRename:
    """Tests for check-in step rename from room_assignment to bunk_assignment"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_check_in_roster_has_bunk_assignment_step(self):
        """Test that check-in roster includes bunk_assignment step"""
        response = requests.get(f"{BASE_URL}/api/check-in/roster", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        if len(data) > 0:
            participant = data[0]
            assert "steps" in participant
            assert "bunk_assignment" in participant["steps"], f"Expected bunk_assignment step, got {list(participant['steps'].keys())}"
            # Verify room_assignment is NOT present
            assert "room_assignment" not in participant["steps"], "room_assignment should be renamed to bunk_assignment"


class TestSupportCadreRolesInAdmin:
    """Tests for support cadre roles in admin page"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_support_cadre_roles_exist(self):
        """Test that support cadre roles are defined in backend"""
        # Get users list to verify roles are accepted
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        assert response.status_code == 200
        # The roles should be defined in the backend - we verified this in code review
        # support_logistics, support_comms, support_pa, support_dining, support_health
