import requests
import json
import sys
from datetime import datetime

class CAPEncampmentAPITester:
    def __init__(self):
        self.base_url = "https://squadron-ops-center.preview.emergentagent.com/api"
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith('/') else f"{self.base_url}{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            result = {
                "test_name": name,
                "method": method,
                "endpoint": endpoint,
                "expected_status": expected_status,
                "actual_status": response.status_code,
                "success": success,
                "response_data": {}
            }

            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    result["response_data"] = response.json()
                except:
                    result["response_data"] = {"message": "Non-JSON response"}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    result["error"] = error_data
                    print(f"   Error: {error_data}")
                except:
                    result["error"] = response.text
                    print(f"   Error: {response.text}")

            self.test_results.append(result)
            return success, result["response_data"] if success else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            result = {
                "test_name": name,
                "method": method,
                "endpoint": endpoint,
                "expected_status": expected_status,
                "actual_status": "ERROR",
                "success": False,
                "error": str(e)
            }
            self.test_results.append(result)
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root Endpoint", "GET", "/", 200)

    def test_user_registration(self):
        """Test user registration - Commander role"""
        timestamp = datetime.now().strftime("%H%M%S")
        test_data = {
            "email": f"commander{timestamp}@capunit.org",
            "password": "SecurePass123!",
            "name": f"Commander Test User {timestamp}",
            "role": "commander",
            "capid": f"CMD{timestamp}"
        }
        
        success, response = self.run_test(
            "User Registration (Commander)",
            "POST",
            "/auth/register",
            200,
            data=test_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            self.commander_data = test_data
            print(f"   Token acquired for commander user")
            return True
        return False

    def test_user_login(self):
        """Test user login"""
        if not hasattr(self, 'commander_data'):
            print("❌ Skipping login test - registration failed")
            return False
            
        login_data = {
            "email": self.commander_data["email"],
            "password": self.commander_data["password"]
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "/auth/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            return True
        return False

    def test_get_current_user(self):
        """Test get current user profile"""
        return self.run_test("Get Current User", "GET", "/auth/me", 200)

    def test_dashboard_stats(self):
        """Test dashboard stats endpoint"""
        return self.run_test("Dashboard Stats", "GET", "/stats/dashboard", 200)

    def test_create_participant(self):
        """Test creating a participant"""
        timestamp = datetime.now().strftime("%H%M%S")
        participant_data = {
            "capid": f"CADET{timestamp}",
            "rank": "C/Amn",
            "last_name": "TestLastName",
            "first_name": "TestFirstName",
            "unit": "TN001",
            "wing": "TN",
            "region": "SER",
            "gender": "M",
            "age": 16,
            "email": f"cadet{timestamp}@capunit.org",
            "phone": "555-1234",
            "shirt_size": "M",
            "participant_type": "basic_student",
            "squadron": "Alpha",
            "flight": "1",
            "position": "Element Leader",
            "paid": False,
            "first_encampment": True,
            "religious_preference": "Protestant",
            "emergency_contact": "Parent: 555-5678",
            "notes": "Test participant"
        }
        
        success, response = self.run_test(
            "Create Participant",
            "POST",
            "/participants",
            200,
            data=participant_data
        )
        
        if success and 'id' in response:
            self.participant_id = response['id']
            return True
        return False

    def test_get_participants(self):
        """Test getting participants list"""
        return self.run_test("Get Participants", "GET", "/participants", 200)

    def test_get_participant_by_id(self):
        """Test getting specific participant"""
        if not hasattr(self, 'participant_id'):
            print("❌ Skipping get participant test - participant creation failed")
            return False
        return self.run_test(f"Get Participant by ID", "GET", f"/participants/{self.participant_id}", 200)

    def test_update_participant(self):
        """Test updating a participant"""
        if not hasattr(self, 'participant_id'):
            print("❌ Skipping update participant test - participant creation failed")
            return False
            
        update_data = {
            "capid": "CADET999",
            "rank": "C/A1C",
            "last_name": "UpdatedLastName",
            "first_name": "UpdatedFirstName",
            "unit": "TN002",
            "wing": "TN",
            "region": "SER",
            "gender": "F",
            "age": 17,
            "email": "updated@capunit.org",
            "phone": "555-9999",
            "shirt_size": "L",
            "participant_type": "advanced_student",
            "squadron": "Bravo",
            "flight": "2",
            "position": "Flight Sergeant",
            "paid": True,
            "first_encampment": False,
            "religious_preference": "Catholic",
            "emergency_contact": "Guardian: 555-0000",
            "notes": "Updated test participant"
        }
        
        return self.run_test(
            "Update Participant",
            "PUT",
            f"/participants/{self.participant_id}",
            200,
            data=update_data
        )

    def test_create_schedule_event(self):
        """Test creating a schedule event"""
        timestamp = datetime.now().strftime("%H%M%S")
        event_data = {
            "title": f"Test Event {timestamp}",
            "description": "This is a test event for API validation",
            "date": "2024-08-15",
            "start_time": "08:00",
            "end_time": "09:00",
            "location": "Parade Ground",
            "event_type": "training"
        }
        
        success, response = self.run_test(
            "Create Schedule Event",
            "POST",
            "/schedule",
            200,
            data=event_data
        )
        
        if success and 'id' in response:
            self.event_id = response['id']
            return True
        return False

    def test_get_schedule(self):
        """Test getting schedule events"""
        return self.run_test("Get Schedule", "GET", "/schedule", 200)

    def test_update_schedule_event(self):
        """Test updating a schedule event"""
        if not hasattr(self, 'event_id'):
            print("❌ Skipping update event test - event creation failed")
            return False
            
        update_data = {
            "title": "Updated Test Event",
            "description": "Updated description",
            "date": "2024-08-16",
            "start_time": "09:00",
            "end_time": "10:00",
            "location": "Updated Location",
            "event_type": "ceremony"
        }
        
        return self.run_test(
            "Update Schedule Event",
            "PUT",
            f"/schedule/{self.event_id}",
            200,
            data=update_data
        )

    def test_create_budget_item(self):
        """Test creating a budget item"""
        timestamp = datetime.now().strftime("%H%M%S")
        budget_data = {
            "category": "Commandants Budget",
            "subcategory": "Test Category",
            "item_name": f"Test Budget Item {timestamp}",
            "estimated": 100.50,
            "actual": 95.25,
            "notes": "Test budget item for API validation"
        }
        
        success, response = self.run_test(
            "Create Budget Item",
            "POST",
            "/budget",
            200,
            data=budget_data
        )
        
        if success and 'id' in response:
            self.budget_id = response['id']
            return True
        return False

    def test_get_budget(self):
        """Test getting budget items"""
        return self.run_test("Get Budget", "GET", "/budget", 200)

    def test_budget_summary(self):
        """Test budget summary endpoint"""
        return self.run_test("Budget Summary", "GET", "/budget/summary", 200)

    def test_create_document(self):
        """Test creating a document"""
        timestamp = datetime.now().strftime("%H%M%S")
        doc_data = {
            "title": f"Test Document {timestamp}",
            "description": "Test document for API validation",
            "doc_type": "handbook",
            "content": "This is test content for the document",
            "file_url": None
        }
        
        success, response = self.run_test(
            "Create Document",
            "POST",
            "/documents",
            200,
            data=doc_data
        )
        
        if success and 'id' in response:
            self.doc_id = response['id']
            return True
        return False

    def test_get_documents(self):
        """Test getting documents"""
        return self.run_test("Get Documents", "GET", "/documents", 200)

    def test_get_users(self):
        """Test getting users (commander only)"""
        return self.run_test("Get Users (Commander Only)", "GET", "/users", 200)

    def test_role_access_control(self):
        """Test role-based access control by creating a cadet user and testing access"""
        # First, create a cadet user
        timestamp = datetime.now().strftime("%H%M%S")
        cadet_data = {
            "email": f"cadet{timestamp}@capunit.org",
            "password": "CadetPass123!",
            "name": f"Cadet Test User {timestamp}",
            "role": "cadet",
            "capid": f"CDT{timestamp}"
        }
        
        success, response = self.run_test(
            "Create Cadet User",
            "POST",
            "/auth/register",
            200,
            data=cadet_data
        )
        
        if not success:
            return False
        
        # Store current commander token
        commander_token = self.token
        
        # Login as cadet
        cadet_login = {
            "email": cadet_data["email"],
            "password": cadet_data["password"]
        }
        
        success, response = self.run_test(
            "Cadet Login",
            "POST",
            "/auth/login",
            200,
            data=cadet_login
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            
            # Test cadet trying to create participant (should fail)
            cadet_participant_data = {
                "capid": f"FAIL{timestamp}",
                "rank": "C/AB",
                "last_name": "FailTest",
                "first_name": "Should",
                "unit": "TN999"
            }
            
            self.run_test(
                "Cadet Create Participant (Should Fail)",
                "POST",
                "/participants",
                403,  # Expecting forbidden
                data=cadet_participant_data
            )
            
            # Test cadet accessing users endpoint (should fail)
            self.run_test(
                "Cadet Get Users (Should Fail)",
                "GET",
                "/users",
                403  # Expecting forbidden
            )
            
            # Restore commander token
            self.token = commander_token
            return True
        
        return False

    def test_delete_operations(self):
        """Test delete operations"""
        results = []
        
        # Delete budget item
        if hasattr(self, 'budget_id'):
            success, _ = self.run_test("Delete Budget Item", "DELETE", f"/budget/{self.budget_id}", 200)
            results.append(success)
        
        # Delete schedule event
        if hasattr(self, 'event_id'):
            success, _ = self.run_test("Delete Schedule Event", "DELETE", f"/schedule/{self.event_id}", 200)
            results.append(success)
        
        # Delete document
        if hasattr(self, 'doc_id'):
            success, _ = self.run_test("Delete Document", "DELETE", f"/documents/{self.doc_id}", 200)
            results.append(success)
        
        # Delete participant (last to avoid affecting other tests)
        if hasattr(self, 'participant_id'):
            success, _ = self.run_test("Delete Participant", "DELETE", f"/participants/{self.participant_id}", 200)
            results.append(success)
        
        return all(results) if results else True

def main():
    print("🚀 Starting CAP Encampment API Tests")
    print("=" * 50)
    
    tester = CAPEncampmentAPITester()
    
    # Test sequence
    test_sequence = [
        ("Root Endpoint", tester.test_root_endpoint),
        ("User Registration", tester.test_user_registration),
        ("User Login", tester.test_user_login),
        ("Get Current User", tester.test_get_current_user),
        ("Dashboard Stats", tester.test_dashboard_stats),
        ("Create Participant", tester.test_create_participant),
        ("Get Participants", tester.test_get_participants),
        ("Get Participant by ID", tester.test_get_participant_by_id),
        ("Update Participant", tester.test_update_participant),
        ("Create Schedule Event", tester.test_create_schedule_event),
        ("Get Schedule", tester.test_get_schedule),
        ("Update Schedule Event", tester.test_update_schedule_event),
        ("Create Budget Item", tester.test_create_budget_item),
        ("Get Budget", tester.test_get_budget),
        ("Budget Summary", tester.test_budget_summary),
        ("Create Document", tester.test_create_document),
        ("Get Documents", tester.test_get_documents),
        ("Get Users (Commander)", tester.test_get_users),
        ("Role Access Control", tester.test_role_access_control),
        ("Delete Operations", tester.test_delete_operations)
    ]
    
    failed_tests = []
    
    for test_name, test_func in test_sequence:
        try:
            success = test_func()
            if not success:
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ {test_name} crashed: {str(e)}")
            failed_tests.append(test_name)
    
    # Print final results
    print("\n" + "=" * 50)
    print("📊 FINAL TEST RESULTS")
    print("=" * 50)
    print(f"Total Tests: {tester.tests_run}")
    print(f"Passed: {tester.tests_passed}")
    print(f"Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "0%")
    
    if failed_tests:
        print(f"\n❌ Failed Tests: {', '.join(failed_tests)}")
    else:
        print(f"\n✅ All tests passed!")
    
    # Save detailed results
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump({
            "summary": {
                "total_tests": tester.tests_run,
                "passed": tester.tests_passed,
                "failed": tester.tests_run - tester.tests_passed,
                "success_rate": (tester.tests_passed/tester.tests_run*100) if tester.tests_run > 0 else 0,
                "failed_test_names": failed_tests
            },
            "detailed_results": tester.test_results
        }, indent=2)
    
    print(f"\n📄 Detailed results saved to: /app/backend_test_results.json")
    
    return 0 if not failed_tests else 1

if __name__ == "__main__":
    sys.exit(main())