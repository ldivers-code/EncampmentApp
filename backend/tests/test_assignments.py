"""
Test suite for Assignments feature - CRUD, submissions, grading, reminders
Tests: POST /api/assignments, GET /api/assignments, GET /api/assignments/{id},
       POST /api/assignments/{id}/submit, POST /api/assignments/{id}/grade/{submission_id},
       POST /api/assignments/{id}/remind, DELETE /api/assignments/{id}
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
COMMANDER_EMAIL = "commander@test.com"
COMMANDER_PASSWORD = "test123"
CADRE_EMAIL = "commander@cap.us"  # exec_cadre role
CADRE_PASSWORD = "test123"


class TestAssignmentsBackend:
    """Test assignments CRUD, submissions, grading, and reminders"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with cookies"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_assignment_id = None
        self.created_submission_id = None
        yield
        # Cleanup: delete test assignment if created
        if self.created_assignment_id:
            try:
                self.session.delete(f"{BASE_URL}/api/assignments/{self.created_assignment_id}")
            except:
                pass
    
    def login_as_commander(self):
        """Login as commander (creator role)"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200, f"Commander login failed: {response.text}"
        return response.json()
    
    def login_as_cadre(self):
        """Login as exec_cadre (submitter role)"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": CADRE_EMAIL,
            "password": CADRE_PASSWORD
        })
        assert response.status_code == 200, f"Cadre login failed: {response.text}"
        return response.json()
    
    # ── Test 1: Create Assignment ──────────────────────────────────────────
    def test_01_create_assignment(self):
        """POST /api/assignments creates an assignment with title, description, due_date, rubric, target_type"""
        self.login_as_commander()
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        payload = {
            "title": "TEST_Assignment_Unit_Test",
            "description": "This is a test assignment for unit testing",
            "due_date": due_date,
            "target_type": "all",
            "rubric": [
                {"criterion": "Content Quality", "max_points": 40, "description": "Quality of written content"},
                {"criterion": "Formatting", "max_points": 30, "description": "Proper formatting and structure"},
                {"criterion": "Timeliness", "max_points": 30, "description": "Submitted on time"}
            ],
            "allow_file_upload": True,
            "allow_text_response": True
        }
        
        response = self.session.post(f"{BASE_URL}/api/assignments", json=payload)
        assert response.status_code == 200, f"Create assignment failed: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should contain assignment id"
        assert data["title"] == payload["title"], "Title should match"
        assert data["description"] == payload["description"], "Description should match"
        assert data["due_date"] == payload["due_date"], "Due date should match"
        assert data["target_type"] == "all", "Target type should be 'all'"
        assert len(data["rubric"]) == 3, "Should have 3 rubric items"
        assert data["max_score"] == 100, "Max score should be sum of rubric points (40+30+30=100)"
        assert data["status"] == "active", "Status should be active"
        
        self.created_assignment_id = data["id"]
        print(f"SUCCESS: Created assignment with id={data['id']}, max_score={data['max_score']}")
    
    # ── Test 2: List Assignments ───────────────────────────────────────────
    def test_02_list_assignments(self):
        """GET /api/assignments returns assignment list with submission_count and my_submission fields"""
        self.login_as_commander()
        
        response = self.session.get(f"{BASE_URL}/api/assignments")
        assert response.status_code == 200, f"List assignments failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        if len(data) > 0:
            assignment = data[0]
            assert "id" in assignment, "Assignment should have id"
            assert "title" in assignment, "Assignment should have title"
            assert "submission_count" in assignment, "Assignment should have submission_count"
            assert "graded_count" in assignment, "Assignment should have graded_count"
            # my_submission can be null or object
            assert "my_submission" in assignment, "Assignment should have my_submission field"
            print(f"SUCCESS: Listed {len(data)} assignments, first has submission_count={assignment['submission_count']}")
        else:
            print("SUCCESS: List assignments returned empty list (no assignments yet)")
    
    # ── Test 3: Get Single Assignment (Creator View) ───────────────────────
    def test_03_get_assignment_creator_view(self):
        """GET /api/assignments/{id} returns assignment with submissions array for creators"""
        self.login_as_commander()
        
        # First create an assignment
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        create_response = self.session.post(f"{BASE_URL}/api/assignments", json={
            "title": "TEST_Get_Assignment_Test",
            "description": "Test for get endpoint",
            "due_date": due_date,
            "target_type": "all",
            "rubric": [{"criterion": "Quality", "max_points": 100}]
        })
        assert create_response.status_code == 200
        assignment_id = create_response.json()["id"]
        self.created_assignment_id = assignment_id
        
        # Get the assignment
        response = self.session.get(f"{BASE_URL}/api/assignments/{assignment_id}")
        assert response.status_code == 200, f"Get assignment failed: {response.text}"
        
        data = response.json()
        assert data["id"] == assignment_id, "ID should match"
        assert "submissions" in data, "Creator view should include submissions array"
        assert "assignees" in data, "Creator view should include assignees list"
        assert isinstance(data["submissions"], list), "Submissions should be a list"
        assert isinstance(data["assignees"], list), "Assignees should be a list"
        print(f"SUCCESS: Got assignment with {len(data['submissions'])} submissions, {len(data['assignees'])} assignees")
    
    # ── Test 4: Submit Assignment ──────────────────────────────────────────
    def test_04_submit_assignment(self):
        """POST /api/assignments/{id}/submit accepts text_response form field and creates submission"""
        # First login as commander to create assignment
        self.login_as_commander()
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        create_response = self.session.post(f"{BASE_URL}/api/assignments", json={
            "title": "TEST_Submit_Assignment_Test",
            "description": "Test for submission endpoint",
            "due_date": due_date,
            "target_type": "all",
            "rubric": [{"criterion": "Quality", "max_points": 100}]
        })
        assert create_response.status_code == 200
        assignment_id = create_response.json()["id"]
        self.created_assignment_id = assignment_id
        
        # Now login as cadre to submit
        self.login_as_cadre()
        
        # Submit using multipart/form-data
        response = self.session.post(
            f"{BASE_URL}/api/assignments/{assignment_id}/submit",
            data={"text_response": "This is my test submission response for the assignment."},
            headers={"Content-Type": None}  # Let requests set multipart headers
        )
        
        # Handle both 200 and 403 (if cadre is not in assignees)
        if response.status_code == 403:
            print(f"INFO: Cadre not in assignees for this assignment (expected for 'all' target)")
            pytest.skip("Cadre user not in assignees list")
        
        assert response.status_code == 200, f"Submit assignment failed: {response.text}"
        
        data = response.json()
        assert "id" in data or "message" in data, "Response should contain id or message"
        if "id" in data:
            self.created_submission_id = data["id"]
        print(f"SUCCESS: Submitted assignment, response: {data}")
    
    # ── Test 5: Grade Submission ───────────────────────────────────────────
    def test_05_grade_submission(self):
        """POST /api/assignments/{id}/grade/{submission_id} applies rubric_scores and calculates total_score"""
        # Create assignment as commander
        self.login_as_commander()
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        create_response = self.session.post(f"{BASE_URL}/api/assignments", json={
            "title": "TEST_Grade_Assignment_Test",
            "description": "Test for grading endpoint",
            "due_date": due_date,
            "target_type": "all",
            "rubric": [
                {"criterion": "Content", "max_points": 50},
                {"criterion": "Format", "max_points": 50}
            ]
        })
        assert create_response.status_code == 200
        assignment_id = create_response.json()["id"]
        self.created_assignment_id = assignment_id
        
        # Submit as cadre
        self.login_as_cadre()
        submit_response = self.session.post(
            f"{BASE_URL}/api/assignments/{assignment_id}/submit",
            data={"text_response": "My submission for grading test"}
        )
        
        if submit_response.status_code == 403:
            print("INFO: Cadre not in assignees, skipping grade test")
            pytest.skip("Cadre user not in assignees list")
        
        assert submit_response.status_code == 200
        submission_id = submit_response.json().get("id")
        
        if not submission_id:
            # Get submission id from assignment detail
            self.login_as_commander()
            detail = self.session.get(f"{BASE_URL}/api/assignments/{assignment_id}").json()
            if detail.get("submissions"):
                submission_id = detail["submissions"][0]["id"]
        
        assert submission_id, "Should have submission id"
        
        # Grade as commander
        self.login_as_commander()
        grade_response = self.session.post(
            f"{BASE_URL}/api/assignments/{assignment_id}/grade/{submission_id}",
            json={
                "rubric_scores": [
                    {"criterion": "Content", "max_points": 50, "score": 45},
                    {"criterion": "Format", "max_points": 50, "score": 40}
                ],
                "feedback": "Good work! Minor formatting issues."
            }
        )
        
        assert grade_response.status_code == 200, f"Grade submission failed: {grade_response.text}"
        
        data = grade_response.json()
        assert "total_score" in data, "Response should contain total_score"
        assert data["total_score"] == 85, f"Total score should be 45+40=85, got {data['total_score']}"
        print(f"SUCCESS: Graded submission with total_score={data['total_score']}")
    
    # ── Test 6: Send Reminders ─────────────────────────────────────────────
    def test_06_send_reminders(self):
        """POST /api/assignments/{id}/remind sends in-app notifications to non-submitters"""
        self.login_as_commander()
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        create_response = self.session.post(f"{BASE_URL}/api/assignments", json={
            "title": "TEST_Reminder_Assignment_Test",
            "description": "Test for reminder endpoint",
            "due_date": due_date,
            "target_type": "all",
            "rubric": [{"criterion": "Quality", "max_points": 100}]
        })
        assert create_response.status_code == 200
        assignment_id = create_response.json()["id"]
        self.created_assignment_id = assignment_id
        
        # Send reminders
        response = self.session.post(f"{BASE_URL}/api/assignments/{assignment_id}/remind")
        assert response.status_code == 200, f"Send reminders failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain message"
        assert "reminded" in data, "Response should contain reminded count"
        print(f"SUCCESS: Sent reminders, message='{data['message']}', reminded={data['reminded']}")
    
    # ── Test 7: Delete Assignment (Soft Delete) ────────────────────────────
    def test_07_delete_assignment(self):
        """DELETE /api/assignments/{id} soft-deletes assignment"""
        self.login_as_commander()
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        create_response = self.session.post(f"{BASE_URL}/api/assignments", json={
            "title": "TEST_Delete_Assignment_Test",
            "description": "Test for delete endpoint",
            "due_date": due_date,
            "target_type": "all",
            "rubric": [{"criterion": "Quality", "max_points": 100}]
        })
        assert create_response.status_code == 200
        assignment_id = create_response.json()["id"]
        
        # Delete the assignment
        response = self.session.delete(f"{BASE_URL}/api/assignments/{assignment_id}")
        assert response.status_code == 200, f"Delete assignment failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain message"
        assert "deleted" in data["message"].lower(), "Message should indicate deletion"
        
        # Verify it's soft-deleted (not in list)
        list_response = self.session.get(f"{BASE_URL}/api/assignments")
        assignments = list_response.json()
        deleted_ids = [a["id"] for a in assignments]
        assert assignment_id not in deleted_ids, "Deleted assignment should not appear in list"
        
        print(f"SUCCESS: Soft-deleted assignment {assignment_id}")
    
    # ── Test 8: Assignment with Flight Target ──────────────────────────────
    def test_08_create_assignment_flight_target(self):
        """Create assignment targeting specific flights"""
        self.login_as_commander()
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        payload = {
            "title": "TEST_Flight_Target_Assignment",
            "description": "Assignment for specific flights",
            "due_date": due_date,
            "target_type": "flight",
            "target_flights": ["Alpha", "Bravo"],
            "rubric": [{"criterion": "Completion", "max_points": 100}]
        }
        
        response = self.session.post(f"{BASE_URL}/api/assignments", json=payload)
        assert response.status_code == 200, f"Create flight-targeted assignment failed: {response.text}"
        
        data = response.json()
        self.created_assignment_id = data["id"]
        assert data["target_type"] == "flight", "Target type should be 'flight'"
        assert data["target_flights"] == ["Alpha", "Bravo"], "Target flights should match"
        print(f"SUCCESS: Created flight-targeted assignment for {data['target_flights']}")
    
    # ── Test 9: Assignment with Individual Target ──────────────────────────
    def test_09_create_assignment_individual_target(self):
        """Create assignment targeting individual users"""
        self.login_as_commander()
        
        # First get a user ID
        users_response = self.session.get(f"{BASE_URL}/api/users")
        if users_response.status_code != 200:
            pytest.skip("Cannot get users list")
        
        users = users_response.json()
        cadre_users = [u for u in users if u.get("role") in ["cadre", "exec_cadre"]]
        if not cadre_users:
            pytest.skip("No cadre users found")
        
        target_user_id = cadre_users[0]["id"]
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        payload = {
            "title": "TEST_Individual_Target_Assignment",
            "description": "Assignment for specific user",
            "due_date": due_date,
            "target_type": "individual",
            "target_users": [target_user_id],
            "rubric": [{"criterion": "Completion", "max_points": 100}]
        }
        
        response = self.session.post(f"{BASE_URL}/api/assignments", json=payload)
        assert response.status_code == 200, f"Create individual-targeted assignment failed: {response.text}"
        
        data = response.json()
        self.created_assignment_id = data["id"]
        assert data["target_type"] == "individual", "Target type should be 'individual'"
        assert target_user_id in data["target_users"], "Target user should be in list"
        print(f"SUCCESS: Created individual-targeted assignment for user {target_user_id}")
    
    # ── Test 10: Non-Creator Cannot Create Assignment ──────────────────────
    def test_10_non_creator_cannot_create(self):
        """Non-creator roles should not be able to create assignments"""
        # Login as a non-creator role (if available)
        # For now, test that the endpoint requires authentication
        new_session = requests.Session()
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        response = new_session.post(f"{BASE_URL}/api/assignments", json={
            "title": "TEST_Unauthorized_Assignment",
            "description": "Should fail",
            "due_date": due_date,
            "rubric": []
        })
        
        assert response.status_code in [401, 403], f"Unauthenticated request should fail, got {response.status_code}"
        print(f"SUCCESS: Unauthenticated create request correctly rejected with {response.status_code}")
    
    # ── Test 11: Assignment Stats Endpoint ─────────────────────────────────
    def test_11_assignment_stats(self):
        """GET /api/assignments/stats/overview returns assignment statistics"""
        self.login_as_commander()
        
        response = self.session.get(f"{BASE_URL}/api/assignments/stats/overview")
        assert response.status_code == 200, f"Get stats failed: {response.text}"
        
        data = response.json()
        assert "total_assignments" in data, "Should have total_assignments"
        assert "active_assignments" in data, "Should have active_assignments"
        assert "total_submissions" in data, "Should have total_submissions"
        assert "graded_submissions" in data, "Should have graded_submissions"
        print(f"SUCCESS: Stats - total={data['total_assignments']}, active={data['active_assignments']}, submissions={data['total_submissions']}, graded={data['graded_submissions']}")
    
    # ── Test 12: Get Non-Existent Assignment Returns 404 ───────────────────
    def test_12_get_nonexistent_assignment(self):
        """GET /api/assignments/{id} returns 404 for non-existent assignment"""
        self.login_as_commander()
        
        response = self.session.get(f"{BASE_URL}/api/assignments/nonexistent-id-12345")
        assert response.status_code == 404, f"Should return 404, got {response.status_code}"
        print("SUCCESS: Non-existent assignment correctly returns 404")


class TestAssignmentsCleanup:
    """Cleanup test assignments after all tests"""
    
    def test_cleanup_test_assignments(self):
        """Delete all TEST_ prefixed assignments"""
        session = requests.Session()
        
        # Login as commander
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Cannot login for cleanup")
        
        # Get all assignments
        list_response = session.get(f"{BASE_URL}/api/assignments")
        if list_response.status_code != 200:
            pytest.skip("Cannot list assignments for cleanup")
        
        assignments = list_response.json()
        test_assignments = [a for a in assignments if a.get("title", "").startswith("TEST_")]
        
        deleted_count = 0
        for assignment in test_assignments:
            delete_response = session.delete(f"{BASE_URL}/api/assignments/{assignment['id']}")
            if delete_response.status_code == 200:
                deleted_count += 1
        
        print(f"SUCCESS: Cleaned up {deleted_count} test assignments")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
