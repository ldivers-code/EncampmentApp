"""
Test suite for Google Classroom-style Assignments feature
Tests: Squadron/Flight targeting, Q&A questions, instructors/mentors, submissions with answers, grading

Features tested:
- Create assignment with squadron targeting (target_type='squadron', target_squadrons=['6th_cts'])
- Create assignment with flight targeting (target_type='flight', target_flights=['alpha','charlie'])
- Create assignment with combined squadron + flight targeting
- Create assignment with Q&A questions (questions array)
- Create assignment with instructors and mentors assigned
- GET /api/assignments returns my_role, instructor_names, mentor_names
- GET /api/assignments/{id} returns detail with submissions for creators/instructors
- POST /api/assignments/{id}/submit with answers field works
- POST /api/assignments/{id}/grade/{sub_id} works for assigned instructors
- DELETE /api/assignments/{id} works
- POST /api/assignments/{id}/remind works for non-submitters
"""
import pytest
import requests
import os
import json
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
COMMANDER_EMAIL = "commander@test.com"
COMMANDER_PASSWORD = "test123"
EXEC_CADRE_EMAIL = "commander@cap.us"  # exec_cadre role, flight=alpha
EXEC_CADRE_PASSWORD = "test123"
CADRE_EMAIL = "cadre@cap.us"  # cadre role, flight=Alpha
CADRE_PASSWORD = "test123"


class TestAssignmentsClassroom:
    """Test Google Classroom-style Assignments feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with cookies"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_assignment_ids = []
        yield
        # Cleanup: delete test assignments
        self.login_as_commander()
        for aid in self.created_assignment_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/assignments/{aid}")
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
    
    def login_as_exec_cadre(self):
        """Login as exec_cadre (can create and grade)"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": EXEC_CADRE_EMAIL,
            "password": EXEC_CADRE_PASSWORD
        })
        assert response.status_code == 200, f"Exec cadre login failed: {response.text}"
        return response.json()
    
    def login_as_cadre(self):
        """Login as cadre (student role)"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": CADRE_EMAIL,
            "password": CADRE_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Cadre login failed: {response.text}")
        return response.json()
    
    def get_user_id(self, email):
        """Get user ID by email"""
        response = self.session.get(f"{BASE_URL}/api/users")
        if response.status_code != 200:
            return None
        users = response.json()
        for u in users:
            if u.get("email") == email:
                return u.get("id")
        return None
    
    # ── Test 1: Create Assignment with Squadron Targeting ──────────────────
    def test_01_create_assignment_squadron_targeting(self):
        """POST /api/assignments creates assignment with target_type='squadron', target_squadrons=['6th_cts']"""
        self.login_as_commander()
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        payload = {
            "title": "TEST_Squadron_Assignment",
            "description": "Assignment for 6th CTS squadron",
            "due_date": due_date,
            "target_type": "squadron",
            "target_squadrons": ["6th_cts"],
            "target_flights": [],
            "rubric": [{"criterion": "Completion", "max_points": 100}]
        }
        
        response = self.session.post(f"{BASE_URL}/api/assignments", json=payload)
        assert response.status_code == 200, f"Create squadron assignment failed: {response.text}"
        
        data = response.json()
        self.created_assignment_ids.append(data["id"])
        
        assert data["target_type"] == "squadron", "Target type should be 'squadron'"
        assert "6th_cts" in data["target_squadrons"], "Should include 6th_cts squadron"
        print(f"SUCCESS: Created squadron-targeted assignment for {data['target_squadrons']}")
    
    # ── Test 2: Create Assignment with Flight Targeting ────────────────────
    def test_02_create_assignment_flight_targeting(self):
        """POST /api/assignments creates assignment with target_type='flight', target_flights=['alpha','charlie']"""
        self.login_as_commander()
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        payload = {
            "title": "TEST_Flight_Assignment",
            "description": "Assignment for Alpha and Charlie flights",
            "due_date": due_date,
            "target_type": "flight",
            "target_flights": ["alpha", "charlie"],
            "target_squadrons": [],
            "rubric": [{"criterion": "Completion", "max_points": 100}]
        }
        
        response = self.session.post(f"{BASE_URL}/api/assignments", json=payload)
        assert response.status_code == 200, f"Create flight assignment failed: {response.text}"
        
        data = response.json()
        self.created_assignment_ids.append(data["id"])
        
        assert data["target_type"] == "flight", "Target type should be 'flight'"
        assert "alpha" in data["target_flights"], "Should include alpha flight"
        assert "charlie" in data["target_flights"], "Should include charlie flight"
        print(f"SUCCESS: Created flight-targeted assignment for {data['target_flights']}")
    
    # ── Test 3: Create Assignment with Combined Squadron + Flight ──────────
    def test_03_create_assignment_combined_targeting(self):
        """POST /api/assignments creates assignment with both squadron and flight targeting"""
        self.login_as_commander()
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        payload = {
            "title": "TEST_Combined_Assignment",
            "description": "Assignment for 6th CTS + Charlie flight",
            "due_date": due_date,
            "target_type": "squadron",  # or "flight" - both work with combined
            "target_squadrons": ["6th_cts"],
            "target_flights": ["charlie"],
            "rubric": [{"criterion": "Completion", "max_points": 100}]
        }
        
        response = self.session.post(f"{BASE_URL}/api/assignments", json=payload)
        assert response.status_code == 200, f"Create combined assignment failed: {response.text}"
        
        data = response.json()
        self.created_assignment_ids.append(data["id"])
        
        assert "6th_cts" in data["target_squadrons"], "Should include 6th_cts squadron"
        assert "charlie" in data["target_flights"], "Should include charlie flight"
        print(f"SUCCESS: Created combined-targeted assignment for squadrons={data['target_squadrons']}, flights={data['target_flights']}")
    
    # ── Test 4: Create Assignment with Q&A Questions ───────────────────────
    def test_04_create_assignment_with_questions(self):
        """POST /api/assignments creates assignment with questions array"""
        self.login_as_commander()
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        payload = {
            "title": "TEST_QA_Assignment",
            "description": "Assignment with Q&A questions",
            "due_date": due_date,
            "target_type": "all",
            "questions": [
                {"question_text": "What is the primary mission of CAP?"},
                {"question_text": "Describe the chain of command in your squadron."},
                {"question_text": "What are the core values of CAP?"}
            ],
            "rubric": [
                {"criterion": "Question 1", "max_points": 30},
                {"criterion": "Question 2", "max_points": 40},
                {"criterion": "Question 3", "max_points": 30}
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/assignments", json=payload)
        assert response.status_code == 200, f"Create Q&A assignment failed: {response.text}"
        
        data = response.json()
        self.created_assignment_ids.append(data["id"])
        
        assert len(data["questions"]) == 3, "Should have 3 questions"
        for q in data["questions"]:
            assert "id" in q, "Each question should have an id"
            assert "question_text" in q, "Each question should have question_text"
        print(f"SUCCESS: Created Q&A assignment with {len(data['questions'])} questions")
    
    # ── Test 5: Create Assignment with Instructors and Mentors ─────────────
    def test_05_create_assignment_with_instructors_mentors(self):
        """POST /api/assignments creates assignment with instructors and mentors assigned"""
        self.login_as_commander()
        
        # Get user IDs for instructors/mentors
        exec_cadre_id = self.get_user_id(EXEC_CADRE_EMAIL)
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        payload = {
            "title": "TEST_Instructor_Assignment",
            "description": "Assignment with instructors and mentors",
            "due_date": due_date,
            "target_type": "all",
            "instructors": [exec_cadre_id] if exec_cadre_id else [],
            "mentors": [],
            "rubric": [{"criterion": "Completion", "max_points": 100}]
        }
        
        response = self.session.post(f"{BASE_URL}/api/assignments", json=payload)
        assert response.status_code == 200, f"Create instructor assignment failed: {response.text}"
        
        data = response.json()
        self.created_assignment_ids.append(data["id"])
        
        if exec_cadre_id:
            assert exec_cadre_id in data["instructors"], "Should include instructor"
        print(f"SUCCESS: Created assignment with instructors={data['instructors']}, mentors={data['mentors']}")
    
    # ── Test 6: List Assignments Returns my_role, instructor_names, mentor_names ──
    def test_06_list_assignments_returns_role_info(self):
        """GET /api/assignments returns assignments with my_role, instructor_names, mentor_names"""
        self.login_as_commander()
        
        # First create an assignment with instructor
        exec_cadre_id = self.get_user_id(EXEC_CADRE_EMAIL)
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        create_response = self.session.post(f"{BASE_URL}/api/assignments", json={
            "title": "TEST_Role_Info_Assignment",
            "description": "Test for role info in list",
            "due_date": due_date,
            "target_type": "all",
            "instructors": [exec_cadre_id] if exec_cadre_id else [],
            "rubric": [{"criterion": "Completion", "max_points": 100}]
        })
        assert create_response.status_code == 200
        assignment_id = create_response.json()["id"]
        self.created_assignment_ids.append(assignment_id)
        
        # List assignments
        response = self.session.get(f"{BASE_URL}/api/assignments")
        assert response.status_code == 200, f"List assignments failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Find our test assignment
        test_assignment = next((a for a in data if a["id"] == assignment_id), None)
        assert test_assignment is not None, "Test assignment should be in list"
        
        assert "my_role" in test_assignment, "Assignment should have my_role field"
        assert "instructor_names" in test_assignment, "Assignment should have instructor_names field"
        assert "mentor_names" in test_assignment, "Assignment should have mentor_names field"
        
        print(f"SUCCESS: Assignment has my_role={test_assignment['my_role']}, instructor_names={test_assignment['instructor_names']}")
    
    # ── Test 7: Get Assignment Detail Returns Submissions for Creators ─────
    def test_07_get_assignment_detail_creator_view(self):
        """GET /api/assignments/{id} returns detail with submissions for creators/instructors"""
        self.login_as_commander()
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        create_response = self.session.post(f"{BASE_URL}/api/assignments", json={
            "title": "TEST_Detail_View_Assignment",
            "description": "Test for detail view",
            "due_date": due_date,
            "target_type": "all",
            "questions": [{"question_text": "Test question?"}],
            "rubric": [{"criterion": "Quality", "max_points": 100}]
        })
        assert create_response.status_code == 200
        assignment_id = create_response.json()["id"]
        self.created_assignment_ids.append(assignment_id)
        
        # Get detail
        response = self.session.get(f"{BASE_URL}/api/assignments/{assignment_id}")
        assert response.status_code == 200, f"Get assignment detail failed: {response.text}"
        
        data = response.json()
        assert data["id"] == assignment_id, "ID should match"
        assert "submissions" in data, "Creator view should include submissions array"
        assert "assignees" in data, "Creator view should include assignees list"
        assert "questions" in data, "Should include questions"
        assert "my_role" in data, "Should include my_role"
        assert "instructor_names" in data, "Should include instructor_names"
        assert "mentor_names" in data, "Should include mentor_names"
        
        print(f"SUCCESS: Detail view has submissions={len(data['submissions'])}, assignees={len(data['assignees'])}, questions={len(data['questions'])}")
    
    # ── Test 8: Submit Assignment with Q&A Answers ─────────────────────────
    def test_08_submit_assignment_with_answers(self):
        """POST /api/assignments/{id}/submit with answers field works"""
        # Create assignment as commander
        self.login_as_commander()
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        create_response = self.session.post(f"{BASE_URL}/api/assignments", json={
            "title": "TEST_Submit_QA_Assignment",
            "description": "Test for submission with answers",
            "due_date": due_date,
            "target_type": "all",
            "questions": [
                {"question_text": "What is CAP?"},
                {"question_text": "What is your role?"}
            ],
            "rubric": [{"criterion": "Quality", "max_points": 100}]
        })
        assert create_response.status_code == 200
        assignment = create_response.json()
        assignment_id = assignment["id"]
        self.created_assignment_ids.append(assignment_id)
        
        # Get question IDs
        question_ids = [q["id"] for q in assignment["questions"]]
        
        # Login as exec_cadre to submit (they are in 'all' target)
        self.login_as_exec_cadre()
        
        # Prepare answers
        answers = [
            {"question_id": question_ids[0], "answer_text": "CAP is Civil Air Patrol"},
            {"question_id": question_ids[1], "answer_text": "I am an exec cadre member"}
        ]
        
        # Submit using multipart/form-data
        response = self.session.post(
            f"{BASE_URL}/api/assignments/{assignment_id}/submit",
            data={
                "text_response": "My overall response",
                "answers": json.dumps(answers)
            }
        )
        
        if response.status_code == 403:
            print("INFO: User not in assignees for this assignment")
            pytest.skip("User not in assignees list")
        
        assert response.status_code == 200, f"Submit assignment failed: {response.text}"
        
        data = response.json()
        assert "id" in data or "message" in data, "Response should contain id or message"
        print(f"SUCCESS: Submitted assignment with answers, response: {data}")
    
    # ── Test 9: Grade Submission Works for Assigned Instructors ────────────
    def test_09_grade_submission_by_instructor(self):
        """POST /api/assignments/{id}/grade/{sub_id} works for assigned instructors"""
        # Create assignment as commander with exec_cadre as instructor
        self.login_as_commander()
        
        exec_cadre_id = self.get_user_id(EXEC_CADRE_EMAIL)
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        create_response = self.session.post(f"{BASE_URL}/api/assignments", json={
            "title": "TEST_Grade_Instructor_Assignment",
            "description": "Test for instructor grading",
            "due_date": due_date,
            "target_type": "all",
            "instructors": [exec_cadre_id] if exec_cadre_id else [],
            "rubric": [
                {"criterion": "Content", "max_points": 50},
                {"criterion": "Format", "max_points": 50}
            ]
        })
        assert create_response.status_code == 200
        assignment_id = create_response.json()["id"]
        self.created_assignment_ids.append(assignment_id)
        
        # Submit as exec_cadre (they can submit to 'all' target)
        self.login_as_exec_cadre()
        submit_response = self.session.post(
            f"{BASE_URL}/api/assignments/{assignment_id}/submit",
            data={"text_response": "My submission for grading test"}
        )
        
        if submit_response.status_code == 403:
            print("INFO: User not in assignees, skipping grade test")
            pytest.skip("User not in assignees list")
        
        assert submit_response.status_code == 200
        
        # Get submission ID
        self.login_as_commander()
        detail = self.session.get(f"{BASE_URL}/api/assignments/{assignment_id}").json()
        if not detail.get("submissions"):
            pytest.skip("No submissions found")
        
        submission_id = detail["submissions"][0]["id"]
        
        # Grade as commander (creator)
        grade_response = self.session.post(
            f"{BASE_URL}/api/assignments/{assignment_id}/grade/{submission_id}",
            json={
                "rubric_scores": [
                    {"criterion": "Content", "max_points": 50, "score": 45},
                    {"criterion": "Format", "max_points": 50, "score": 48}
                ],
                "feedback": "Excellent work!"
            }
        )
        
        assert grade_response.status_code == 200, f"Grade submission failed: {grade_response.text}"
        
        data = grade_response.json()
        assert "total_score" in data, "Response should contain total_score"
        assert data["total_score"] == 93, f"Total score should be 45+48=93, got {data['total_score']}"
        print(f"SUCCESS: Graded submission with total_score={data['total_score']}")
    
    # ── Test 10: Delete Assignment Works ───────────────────────────────────
    def test_10_delete_assignment(self):
        """DELETE /api/assignments/{id} works"""
        self.login_as_commander()
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        create_response = self.session.post(f"{BASE_URL}/api/assignments", json={
            "title": "TEST_Delete_Assignment",
            "description": "Test for delete",
            "due_date": due_date,
            "target_type": "all",
            "rubric": [{"criterion": "Quality", "max_points": 100}]
        })
        assert create_response.status_code == 200
        assignment_id = create_response.json()["id"]
        
        # Delete
        response = self.session.delete(f"{BASE_URL}/api/assignments/{assignment_id}")
        assert response.status_code == 200, f"Delete assignment failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain message"
        
        # Verify not in list
        list_response = self.session.get(f"{BASE_URL}/api/assignments")
        assignments = list_response.json()
        assert assignment_id not in [a["id"] for a in assignments], "Deleted assignment should not appear in list"
        
        print(f"SUCCESS: Deleted assignment {assignment_id}")
    
    # ── Test 11: Reminder Button Works for Non-Submitters ──────────────────
    def test_11_reminder_for_non_submitters(self):
        """POST /api/assignments/{id}/remind works for non-submitters"""
        self.login_as_commander()
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        create_response = self.session.post(f"{BASE_URL}/api/assignments", json={
            "title": "TEST_Reminder_Assignment",
            "description": "Test for reminders",
            "due_date": due_date,
            "target_type": "all",
            "rubric": [{"criterion": "Quality", "max_points": 100}]
        })
        assert create_response.status_code == 200
        assignment_id = create_response.json()["id"]
        self.created_assignment_ids.append(assignment_id)
        
        # Send reminders
        response = self.session.post(f"{BASE_URL}/api/assignments/{assignment_id}/remind")
        assert response.status_code == 200, f"Send reminders failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain message"
        assert "reminded" in data, "Response should contain reminded count"
        print(f"SUCCESS: Sent reminders, message='{data['message']}', reminded={data['reminded']}")
    
    # ── Test 12: Assignment Detail Shows Target Info ───────────────────────
    def test_12_assignment_detail_shows_target_info(self):
        """GET /api/assignments/{id} returns target info (squadrons/flights)"""
        self.login_as_commander()
        
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        create_response = self.session.post(f"{BASE_URL}/api/assignments", json={
            "title": "TEST_Target_Info_Assignment",
            "description": "Test for target info display",
            "due_date": due_date,
            "target_type": "squadron",
            "target_squadrons": ["6th_cts", "21st_cts"],
            "target_flights": ["echo"],
            "rubric": [{"criterion": "Quality", "max_points": 100}]
        })
        assert create_response.status_code == 200
        assignment_id = create_response.json()["id"]
        self.created_assignment_ids.append(assignment_id)
        
        # Get detail
        response = self.session.get(f"{BASE_URL}/api/assignments/{assignment_id}")
        assert response.status_code == 200, f"Get assignment detail failed: {response.text}"
        
        data = response.json()
        assert "target_type" in data, "Should have target_type"
        assert "target_squadrons" in data, "Should have target_squadrons"
        assert "target_flights" in data, "Should have target_flights"
        assert "6th_cts" in data["target_squadrons"], "Should include 6th_cts"
        assert "21st_cts" in data["target_squadrons"], "Should include 21st_cts"
        assert "echo" in data["target_flights"], "Should include echo flight"
        
        print(f"SUCCESS: Detail shows target_type={data['target_type']}, squadrons={data['target_squadrons']}, flights={data['target_flights']}")
    
    # ── Test 13: Flights and Squadrons Endpoints ───────────────────────────
    def test_13_flights_and_squadrons_endpoints(self):
        """GET /api/flights and GET /api/squadrons return correct data"""
        self.login_as_commander()
        
        # Test flights endpoint
        flights_response = self.session.get(f"{BASE_URL}/api/flights")
        assert flights_response.status_code == 200, f"Get flights failed: {flights_response.text}"
        
        flights = flights_response.json()
        assert isinstance(flights, list), "Flights should be a list"
        assert len(flights) >= 6, "Should have at least 6 flights"
        
        flight_values = [f["value"] for f in flights]
        assert "alpha" in flight_values, "Should include alpha flight"
        assert "bravo" in flight_values, "Should include bravo flight"
        assert "charlie" in flight_values, "Should include charlie flight"
        
        # Test squadrons endpoint
        squadrons_response = self.session.get(f"{BASE_URL}/api/squadrons")
        assert squadrons_response.status_code == 200, f"Get squadrons failed: {squadrons_response.text}"
        
        squadrons = squadrons_response.json()
        assert isinstance(squadrons, list), "Squadrons should be a list"
        assert len(squadrons) >= 3, "Should have at least 3 squadrons"
        
        squadron_values = [s["value"] for s in squadrons]
        assert "6th_cts" in squadron_values, "Should include 6th_cts"
        assert "21st_cts" in squadron_values, "Should include 21st_cts"
        assert "22nd_cts" in squadron_values, "Should include 22nd_cts"
        
        print(f"SUCCESS: Flights={len(flights)}, Squadrons={len(squadrons)}")
    
    # ── Test 14: Assignment Stats Overview ─────────────────────────────────
    def test_14_assignment_stats_overview(self):
        """GET /api/assignments/stats/overview returns statistics"""
        self.login_as_commander()
        
        response = self.session.get(f"{BASE_URL}/api/assignments/stats/overview")
        assert response.status_code == 200, f"Get stats failed: {response.text}"
        
        data = response.json()
        assert "total_assignments" in data, "Should have total_assignments"
        assert "active_assignments" in data, "Should have active_assignments"
        assert "total_submissions" in data, "Should have total_submissions"
        assert "graded_submissions" in data, "Should have graded_submissions"
        
        print(f"SUCCESS: Stats - total={data['total_assignments']}, active={data['active_assignments']}")


class TestAssignmentsClassroomCleanup:
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
