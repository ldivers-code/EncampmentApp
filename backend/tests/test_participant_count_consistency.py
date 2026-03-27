"""
Test Participant Count Consistency Across All Pages
====================================================
Bug Fix Verification: is_removed filter added to all participant queries
Expected counts: Total=115, Students=40, Cadre=64, Staff=11

Tests verify:
1. GET /api/participants/stats returns consistent counts
2. GET /api/check-in/summary returns matching counts
3. GET /api/check-in/roster returns correct totals with proper categories
4. GET /api/check-in/roster?category=student returns only basic_student type
5. GET /api/check-in/roster?category=cadre returns only cadre/exec_cadre type
6. GET /api/check-in/roster?category=staff returns only staff type
7. GET /api/participants returns 115 active participants (no removed records)
8. GET /api/barracks/unassigned-participants excludes removed participants
9. POST /api/sync/users-participants is idempotent (no duplicate CAPIDs)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Expected counts based on bug fix
EXPECTED_TOTAL = 115
EXPECTED_STUDENTS = 40
EXPECTED_CADRE = 64
EXPECTED_STAFF = 11


class TestParticipantCountConsistency:
    """Test that participant counts are consistent across all endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "testadmin@cap.gov",
            "password": "TestPass123!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, f"No access_token in response: {data}"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    # ==================== PARTICIPANT STATS TESTS ====================
    
    def test_participants_stats_total_count(self, auth_headers):
        """Test GET /api/participants/stats returns correct total count"""
        response = requests.get(f"{BASE_URL}/api/participants/stats", headers=auth_headers)
        assert response.status_code == 200, f"Stats endpoint failed: {response.text}"
        
        data = response.json()
        assert "total" in data, f"No 'total' field in stats: {data}"
        assert data["total"] == EXPECTED_TOTAL, f"Expected total={EXPECTED_TOTAL}, got {data['total']}"
        print(f"✓ Participants stats total: {data['total']}")
    
    def test_participants_stats_student_count(self, auth_headers):
        """Test GET /api/participants/stats returns correct student count"""
        response = requests.get(f"{BASE_URL}/api/participants/stats", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "students" in data, f"No 'students' field in stats: {data}"
        assert data["students"] == EXPECTED_STUDENTS, f"Expected students={EXPECTED_STUDENTS}, got {data['students']}"
        print(f"✓ Participants stats students: {data['students']}")
    
    def test_participants_stats_cadre_count(self, auth_headers):
        """Test GET /api/participants/stats returns correct cadre count"""
        response = requests.get(f"{BASE_URL}/api/participants/stats", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "cadre" in data, f"No 'cadre' field in stats: {data}"
        assert data["cadre"] == EXPECTED_CADRE, f"Expected cadre={EXPECTED_CADRE}, got {data['cadre']}"
        print(f"✓ Participants stats cadre: {data['cadre']}")
    
    def test_participants_stats_staff_count(self, auth_headers):
        """Test GET /api/participants/stats returns correct staff count"""
        response = requests.get(f"{BASE_URL}/api/participants/stats", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "staff" in data, f"No 'staff' field in stats: {data}"
        assert data["staff"] == EXPECTED_STAFF, f"Expected staff={EXPECTED_STAFF}, got {data['staff']}"
        print(f"✓ Participants stats staff: {data['staff']}")
    
    # ==================== CHECK-IN SUMMARY TESTS ====================
    
    def test_checkin_summary_total_count(self, auth_headers):
        """Test GET /api/check-in/summary returns correct total count"""
        response = requests.get(f"{BASE_URL}/api/check-in/summary", headers=auth_headers)
        assert response.status_code == 200, f"Check-in summary failed: {response.text}"
        
        data = response.json()
        assert "total_participants" in data, f"No 'total_participants' field: {data}"
        assert data["total_participants"] == EXPECTED_TOTAL, f"Expected total={EXPECTED_TOTAL}, got {data['total_participants']}"
        print(f"✓ Check-in summary total: {data['total_participants']}")
    
    def test_checkin_summary_student_count(self, auth_headers):
        """Test GET /api/check-in/summary returns correct student count"""
        response = requests.get(f"{BASE_URL}/api/check-in/summary", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_students" in data, f"No 'total_students' field: {data}"
        assert data["total_students"] == EXPECTED_STUDENTS, f"Expected students={EXPECTED_STUDENTS}, got {data['total_students']}"
        print(f"✓ Check-in summary students: {data['total_students']}")
    
    def test_checkin_summary_cadre_count(self, auth_headers):
        """Test GET /api/check-in/summary returns correct cadre count"""
        response = requests.get(f"{BASE_URL}/api/check-in/summary", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_cadre" in data, f"No 'total_cadre' field: {data}"
        assert data["total_cadre"] == EXPECTED_CADRE, f"Expected cadre={EXPECTED_CADRE}, got {data['total_cadre']}"
        print(f"✓ Check-in summary cadre: {data['total_cadre']}")
    
    def test_checkin_summary_staff_count(self, auth_headers):
        """Test GET /api/check-in/summary returns correct staff count"""
        response = requests.get(f"{BASE_URL}/api/check-in/summary", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_staff" in data, f"No 'total_staff' field: {data}"
        assert data["total_staff"] == EXPECTED_STAFF, f"Expected staff={EXPECTED_STAFF}, got {data['total_staff']}"
        print(f"✓ Check-in summary staff: {data['total_staff']}")
    
    # ==================== CHECK-IN ROSTER TESTS ====================
    
    def test_checkin_roster_total_count(self, auth_headers):
        """Test GET /api/check-in/roster returns correct total count"""
        response = requests.get(f"{BASE_URL}/api/check-in/roster", headers=auth_headers)
        assert response.status_code == 200, f"Check-in roster failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert len(data) == EXPECTED_TOTAL, f"Expected {EXPECTED_TOTAL} participants, got {len(data)}"
        print(f"✓ Check-in roster total: {len(data)}")
    
    def test_checkin_roster_student_filter(self, auth_headers):
        """Test GET /api/check-in/roster?category=student returns only students"""
        response = requests.get(f"{BASE_URL}/api/check-in/roster?category=student", headers=auth_headers)
        assert response.status_code == 200, f"Check-in roster student filter failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert len(data) == EXPECTED_STUDENTS, f"Expected {EXPECTED_STUDENTS} students, got {len(data)}"
        
        # Verify all entries have category=student
        for entry in data:
            assert entry.get("category") == "student", f"Non-student in student filter: {entry}"
        
        print(f"✓ Check-in roster students: {len(data)}")
    
    def test_checkin_roster_cadre_filter(self, auth_headers):
        """Test GET /api/check-in/roster?category=cadre returns only cadre"""
        response = requests.get(f"{BASE_URL}/api/check-in/roster?category=cadre", headers=auth_headers)
        assert response.status_code == 200, f"Check-in roster cadre filter failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert len(data) == EXPECTED_CADRE, f"Expected {EXPECTED_CADRE} cadre, got {len(data)}"
        
        # Verify all entries have category=cadre or exec_cadre
        for entry in data:
            assert entry.get("category") in ["cadre", "exec_cadre"], f"Non-cadre in cadre filter: {entry}"
        
        print(f"✓ Check-in roster cadre: {len(data)}")
    
    def test_checkin_roster_staff_filter(self, auth_headers):
        """Test GET /api/check-in/roster?category=staff returns only staff"""
        response = requests.get(f"{BASE_URL}/api/check-in/roster?category=staff", headers=auth_headers)
        assert response.status_code == 200, f"Check-in roster staff filter failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert len(data) == EXPECTED_STAFF, f"Expected {EXPECTED_STAFF} staff, got {len(data)}"
        
        # Verify all entries have category=staff
        for entry in data:
            assert entry.get("category") == "staff", f"Non-staff in staff filter: {entry}"
        
        print(f"✓ Check-in roster staff: {len(data)}")
    
    # ==================== PARTICIPANTS LIST TESTS ====================
    
    def test_participants_list_count(self, auth_headers):
        """Test GET /api/participants returns correct count (no removed records)"""
        response = requests.get(f"{BASE_URL}/api/participants", headers=auth_headers)
        assert response.status_code == 200, f"Participants list failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert len(data) == EXPECTED_TOTAL, f"Expected {EXPECTED_TOTAL} participants, got {len(data)}"
        print(f"✓ Participants list total: {len(data)}")
    
    def test_participants_list_no_removed_records(self, auth_headers):
        """Test GET /api/participants excludes is_removed=True records"""
        response = requests.get(f"{BASE_URL}/api/participants", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        # Verify no participant has is_removed=True
        for p in data:
            assert p.get("is_removed") != True, f"Found removed participant: {p.get('id')}"
        
        print(f"✓ No removed records in participants list")
    
    def test_participants_list_category_breakdown(self, auth_headers):
        """Test GET /api/participants has correct category breakdown"""
        response = requests.get(f"{BASE_URL}/api/participants", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Count by participant_type
        students = sum(1 for p in data if p.get("participant_type") in ["basic_student", "student"])
        cadre = sum(1 for p in data if p.get("participant_type") in ["cadre", "exec_cadre"])
        staff = sum(1 for p in data if p.get("participant_type") == "staff")
        
        assert students == EXPECTED_STUDENTS, f"Expected {EXPECTED_STUDENTS} students, got {students}"
        assert cadre == EXPECTED_CADRE, f"Expected {EXPECTED_CADRE} cadre, got {cadre}"
        assert staff == EXPECTED_STAFF, f"Expected {EXPECTED_STAFF} staff, got {staff}"
        
        print(f"✓ Participants breakdown: students={students}, cadre={cadre}, staff={staff}")
    
    # ==================== BARRACKS UNASSIGNED TESTS ====================
    
    def test_barracks_unassigned_excludes_removed(self, auth_headers):
        """Test GET /api/barracks/unassigned-participants excludes removed participants"""
        response = requests.get(f"{BASE_URL}/api/barracks/unassigned-participants", headers=auth_headers)
        assert response.status_code == 200, f"Barracks unassigned failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        
        # The count should be <= total students + cadre (staff not included in barracks)
        max_expected = EXPECTED_STUDENTS + EXPECTED_CADRE
        assert len(data) <= max_expected, f"Too many unassigned: {len(data)} > {max_expected}"
        
        print(f"✓ Barracks unassigned count: {len(data)} (max expected: {max_expected})")
    
    def test_barracks_unassigned_only_students_and_cadre(self, auth_headers):
        """Test GET /api/barracks/unassigned-participants only includes students and cadre"""
        response = requests.get(f"{BASE_URL}/api/barracks/unassigned-participants", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify all entries are students or cadre (not staff)
        for entry in data:
            assert entry.get("category") in ["student", "cadre"], f"Invalid category in barracks: {entry}"
        
        print(f"✓ Barracks unassigned only contains students and cadre")
    
    # ==================== SYNC IDEMPOTENCY TESTS ====================
    
    def test_sync_is_idempotent(self, auth_headers):
        """Test POST /api/sync/users-participants is idempotent (no duplicate CAPIDs)"""
        # Run sync twice
        response1 = requests.post(f"{BASE_URL}/api/sync/users-participants", headers=auth_headers)
        assert response1.status_code == 200, f"First sync failed: {response1.text}"
        
        data1 = response1.json()
        print(f"First sync: linked={data1.get('linked')}, created={data1.get('created')}, already_linked={data1.get('already_linked')}")
        
        # Run sync again
        response2 = requests.post(f"{BASE_URL}/api/sync/users-participants", headers=auth_headers)
        assert response2.status_code == 200, f"Second sync failed: {response2.text}"
        
        data2 = response2.json()
        print(f"Second sync: linked={data2.get('linked')}, created={data2.get('created')}, already_linked={data2.get('already_linked')}")
        
        # Second sync should not create any new records
        assert data2.get("created", 0) == 0, f"Second sync created duplicates: {data2.get('created')}"
        assert data2.get("linked", 0) == 0, f"Second sync linked new records: {data2.get('linked')}"
        
        print(f"✓ Sync is idempotent - no duplicates created")
    
    # ==================== CROSS-ENDPOINT CONSISTENCY TESTS ====================
    
    def test_stats_and_summary_match(self, auth_headers):
        """Test that /api/participants/stats and /api/check-in/summary return matching counts"""
        stats_response = requests.get(f"{BASE_URL}/api/participants/stats", headers=auth_headers)
        summary_response = requests.get(f"{BASE_URL}/api/check-in/summary", headers=auth_headers)
        
        assert stats_response.status_code == 200
        assert summary_response.status_code == 200
        
        stats = stats_response.json()
        summary = summary_response.json()
        
        # Compare totals
        assert stats["total"] == summary["total_participants"], \
            f"Total mismatch: stats={stats['total']}, summary={summary['total_participants']}"
        
        # Compare students
        assert stats["students"] == summary["total_students"], \
            f"Students mismatch: stats={stats['students']}, summary={summary['total_students']}"
        
        # Compare cadre
        assert stats["cadre"] == summary["total_cadre"], \
            f"Cadre mismatch: stats={stats['cadre']}, summary={summary['total_cadre']}"
        
        # Compare staff
        assert stats["staff"] == summary["total_staff"], \
            f"Staff mismatch: stats={stats['staff']}, summary={summary['total_staff']}"
        
        print(f"✓ Stats and summary counts match perfectly")
    
    def test_roster_and_stats_match(self, auth_headers):
        """Test that /api/check-in/roster counts match /api/participants/stats"""
        stats_response = requests.get(f"{BASE_URL}/api/participants/stats", headers=auth_headers)
        roster_response = requests.get(f"{BASE_URL}/api/check-in/roster", headers=auth_headers)
        
        assert stats_response.status_code == 200
        assert roster_response.status_code == 200
        
        stats = stats_response.json()
        roster = roster_response.json()
        
        # Count roster by category
        roster_students = sum(1 for r in roster if r.get("category") == "student")
        roster_cadre = sum(1 for r in roster if r.get("category") in ["cadre", "exec_cadre"])
        roster_staff = sum(1 for r in roster if r.get("category") == "staff")
        
        assert len(roster) == stats["total"], \
            f"Total mismatch: roster={len(roster)}, stats={stats['total']}"
        assert roster_students == stats["students"], \
            f"Students mismatch: roster={roster_students}, stats={stats['students']}"
        assert roster_cadre == stats["cadre"], \
            f"Cadre mismatch: roster={roster_cadre}, stats={stats['cadre']}"
        assert roster_staff == stats["staff"], \
            f"Staff mismatch: roster={roster_staff}, stats={stats['staff']}"
        
        print(f"✓ Roster and stats counts match perfectly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
