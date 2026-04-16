"""
OTC Medication Permission Form Tests
Tests for Parent OTC Permission Form feature including:
- Parent GET/POST endpoints for OTC form
- Staff dashboard and review endpoints
- Role-based access control
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://cadre-hub.preview.emergentagent.com').rstrip('/')

# Test credentials
from conftest import COMMANDER_EMAIL, COMMANDER_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, TEST_CADRE_EMAIL, TEST_CADRE_PASSWORD
PARENT_EMAIL = PARENT_EMAIL
PARENT_CAPID = "718873"

# OTC Medications list (13 items)
OTC_MEDICATIONS = [
    "acetaminophen", "antifungal", "antihistamine", "bacitracin",
    "calamine", "claritin", "hydrocortisone", "ibuprofen",
    "orajel", "robitussin", "sunscreen", "tums", "visine"
]


class TestOTCPermissionsAuth:
    """Test authentication and role-based access"""
    
    @pytest.fixture(scope="class")
    def commander_token(self):
        """Get commander auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200, f"Commander login failed: {response.text}"
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    @pytest.fixture(scope="class")
    def parent_token(self):
        """Get parent auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARENT_EMAIL,
            "password": PARENT_PASSWORD
        })
        assert response.status_code == 200, f"Parent login failed: {response.text}"
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_commander_login(self, commander_token):
        """Verify commander can login"""
        assert commander_token is not None
        assert len(commander_token) > 10
        print(f"Commander token obtained: {commander_token[:20]}...")
    
    def test_parent_login(self, parent_token):
        """Verify parent can login"""
        assert parent_token is not None
        assert len(parent_token) > 10
        print(f"Parent token obtained: {parent_token[:20]}...")


class TestParentOTCEndpoints:
    """Test parent OTC permission form endpoints"""
    
    @pytest.fixture(scope="class")
    def parent_token(self):
        """Get parent auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARENT_EMAIL,
            "password": PARENT_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    @pytest.fixture(scope="class")
    def commander_token(self):
        """Get commander auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_get_parent_otc_form(self, parent_token):
        """GET /api/parent/my-cadet/otc-permission returns cadet info and form data"""
        response = requests.get(
            f"{BASE_URL}/api/parent/my-cadet/otc-permission",
            headers={"Authorization": f"Bearer {parent_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify cadet info
        assert "cadet" in data, "Response should contain cadet info"
        cadet = data["cadet"]
        assert "capid" in cadet, "Cadet should have capid"
        assert "name" in cadet, "Cadet should have name"
        assert "role" in cadet, "Cadet should have role (Student/Cadre)"
        print(f"Cadet info: {cadet['name']} (CAPID: {cadet['capid']}, Role: {cadet['role']})")
        
        # Verify medications list (13 items)
        assert "medications_list" in data, "Response should contain medications_list"
        meds_list = data["medications_list"]
        assert len(meds_list) == 13, f"Should have 13 medications, got {len(meds_list)}"
        for med in OTC_MEDICATIONS:
            assert med in meds_list, f"Missing medication: {med}"
        print(f"Medications list verified: {len(meds_list)} items")
        
        # Verify medication labels
        assert "medication_labels" in data, "Response should contain medication_labels"
        
        # Check form data (may be null if not submitted)
        if data.get("form"):
            form = data["form"]
            assert "status" in form, "Form should have status"
            assert "medications" in form, "Form should have medications"
            print(f"Form status: {form['status']}")
        else:
            print("Form not yet submitted (null)")
    
    def test_non_parent_cannot_access_parent_endpoint(self, commander_token):
        """Non-parent users get 403 on parent OTC endpoints"""
        response = requests.get(
            f"{BASE_URL}/api/parent/my-cadet/otc-permission",
            headers={"Authorization": f"Bearer {commander_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Commander correctly denied access to parent endpoint (403)")
    
    def test_submit_otc_form_missing_medication(self, parent_token):
        """POST rejects if any medication is missing (400 error)"""
        # Submit with only 12 medications (missing one)
        incomplete_meds = {med: True for med in OTC_MEDICATIONS[:12]}  # Missing last one
        
        response = requests.post(
            f"{BASE_URL}/api/parent/my-cadet/otc-permission",
            headers={"Authorization": f"Bearer {parent_token}", "Content-Type": "application/json"},
            json={
                "parent_name": "Test Parent",
                "parent_relationship": "Mother",
                "parent_phone": "555-555-5555",
                "parent_email": "test@example.com",
                "medications": incomplete_meds,
                "ack_otc_only": True,
                "ack_staff_discretion": True,
                "ack_prescription_separate": True,
                "ack_accurate_info": True,
                "notes_for_hso": "",
                "signature": "Test Parent"
            }
        )
        assert response.status_code == 400, f"Expected 400 for missing medication, got {response.status_code}: {response.text}"
        print("Correctly rejected submission with missing medication (400)")
    
    def test_submit_otc_form_missing_acknowledgments(self, parent_token):
        """POST rejects if acknowledgments not all true (400 error)"""
        all_meds = {med: True for med in OTC_MEDICATIONS}
        
        response = requests.post(
            f"{BASE_URL}/api/parent/my-cadet/otc-permission",
            headers={"Authorization": f"Bearer {parent_token}", "Content-Type": "application/json"},
            json={
                "parent_name": "Test Parent",
                "parent_relationship": "Mother",
                "parent_phone": "555-555-5555",
                "parent_email": "test@example.com",
                "medications": all_meds,
                "ack_otc_only": True,
                "ack_staff_discretion": False,  # Missing acknowledgment
                "ack_prescription_separate": True,
                "ack_accurate_info": True,
                "notes_for_hso": "",
                "signature": "Test Parent"
            }
        )
        assert response.status_code == 400, f"Expected 400 for missing acknowledgment, got {response.status_code}: {response.text}"
        print("Correctly rejected submission with missing acknowledgment (400)")


class TestStaffOTCEndpoints:
    """Test staff OTC dashboard and review endpoints"""
    
    @pytest.fixture(scope="class")
    def commander_token(self):
        """Get commander auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    @pytest.fixture(scope="class")
    def parent_token(self):
        """Get parent auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARENT_EMAIL,
            "password": PARENT_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_get_otc_dashboard(self, commander_token):
        """GET /api/otc-permissions/dashboard returns counts and items list"""
        response = requests.get(
            f"{BASE_URL}/api/otc-permissions/dashboard",
            headers={"Authorization": f"Bearer {commander_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify summary counts
        assert "total" in data, "Dashboard should have total count"
        assert "submitted" in data, "Dashboard should have submitted count"
        assert "reviewed" in data, "Dashboard should have reviewed count"
        assert "missing" in data, "Dashboard should have missing count"
        print(f"Dashboard counts - Total: {data['total']}, Submitted: {data['submitted']}, Reviewed: {data['reviewed']}, Missing: {data['missing']}")
        
        # Verify items list
        assert "items" in data, "Dashboard should have items list"
        items = data["items"]
        assert isinstance(items, list), "Items should be a list"
        
        # Verify medication labels
        assert "medication_labels" in data, "Dashboard should have medication_labels"
        
        # Check item structure if items exist
        if len(items) > 0:
            item = items[0]
            assert "capid" in item, "Item should have capid"
            assert "name" in item, "Item should have name"
            assert "status" in item, "Item should have status"
            assert "participant_type" in item, "Item should have participant_type"
            print(f"Sample item: {item['name']} - Status: {item['status']}, Type: {item['participant_type']}")
            
            # Check for medication answers if form submitted
            if item.get("medications"):
                assert isinstance(item["medications"], dict), "Medications should be a dict"
                print(f"  Medications: {len(item['medications'])} answers")
    
    def test_non_staff_cannot_access_dashboard(self, parent_token):
        """Non-staff users get 403 on dashboard endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/otc-permissions/dashboard",
            headers={"Authorization": f"Bearer {parent_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Parent correctly denied access to staff dashboard (403)")
    
    def test_get_specific_otc_form(self, commander_token):
        """GET /api/otc-permissions/{capid} returns form details"""
        # First get dashboard to find a submitted form
        dashboard_response = requests.get(
            f"{BASE_URL}/api/otc-permissions/dashboard",
            headers={"Authorization": f"Bearer {commander_token}"}
        )
        assert dashboard_response.status_code == 200
        dashboard = dashboard_response.json()
        
        # Find a submitted form
        submitted_items = [i for i in dashboard["items"] if i["status"] in ["submitted", "reviewed"]]
        if not submitted_items:
            pytest.skip("No submitted forms to test")
        
        capid = submitted_items[0]["capid"]
        
        # Get specific form
        response = requests.get(
            f"{BASE_URL}/api/otc-permissions/{capid}",
            headers={"Authorization": f"Bearer {commander_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        form = response.json()
        
        # Verify form structure
        assert "cadet_capid" in form, "Form should have cadet_capid"
        assert "cadet_name" in form, "Form should have cadet_name"
        assert "medications" in form, "Form should have medications"
        assert "status" in form, "Form should have status"
        assert "signature" in form, "Form should have signature"
        print(f"Form for {form['cadet_name']}: Status={form['status']}, Signed by {form.get('parent_name')}")
    
    def test_non_staff_cannot_review(self, parent_token):
        """Non-staff users get 403 on review endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/otc-permissions/{PARENT_CAPID}/review",
            headers={"Authorization": f"Bearer {parent_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Parent correctly denied access to review endpoint (403)")


class TestOTCFormSubmissionFlow:
    """Test complete OTC form submission flow"""
    
    @pytest.fixture(scope="class")
    def parent_token(self):
        """Get parent auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": PARENT_EMAIL,
            "password": PARENT_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    @pytest.fixture(scope="class")
    def commander_token(self):
        """Get commander auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_submit_valid_otc_form(self, parent_token):
        """POST /api/parent/my-cadet/otc-permission with all fields submits successfully"""
        # All 13 medications answered (12 Yes, 1 No for orajel)
        all_meds = {med: True for med in OTC_MEDICATIONS}
        all_meds["orajel"] = False  # One medication declined
        
        response = requests.post(
            f"{BASE_URL}/api/parent/my-cadet/otc-permission",
            headers={"Authorization": f"Bearer {parent_token}", "Content-Type": "application/json"},
            json={
                "parent_name": "Jane Hundley",
                "parent_relationship": "Mother",
                "parent_phone": "(555) 123-4567",
                "parent_email": PARENT_EMAIL,
                "medications": all_meds,
                "ack_otc_only": True,
                "ack_staff_discretion": True,
                "ack_prescription_separate": True,
                "ack_accurate_info": True,
                "notes_for_hso": "Athena is sensitive to codeine-based products",
                "signature": "Jane Hundley"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "message" in data, "Response should have message"
        assert "status" in data, "Response should have status"
        assert data["status"] == "submitted", f"Status should be 'submitted', got {data['status']}"
        print(f"Form submitted successfully: {data['message']}")
    
    def test_verify_submitted_form(self, parent_token):
        """Verify form data persisted correctly after submission"""
        response = requests.get(
            f"{BASE_URL}/api/parent/my-cadet/otc-permission",
            headers={"Authorization": f"Bearer {parent_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("form") is not None, "Form should exist after submission"
        form = data["form"]
        
        # Verify form fields
        assert form["parent_name"] == "Jane Hundley", "Parent name should match"
        assert form["parent_relationship"] == "Mother", "Relationship should match"
        assert form["signature"] == "Jane Hundley", "Signature should match"
        assert form["status"] in ["submitted", "reviewed"], f"Status should be submitted or reviewed, got {form['status']}"
        
        # Verify medications
        meds = form["medications"]
        assert len(meds) == 13, f"Should have 13 medication answers, got {len(meds)}"
        assert meds["orajel"] == False, "Orajel should be False"
        assert meds["acetaminophen"] == True, "Acetaminophen should be True"
        
        # Verify notes
        assert "codeine" in form.get("notes_for_hso", "").lower(), "Notes should contain codeine reference"
        
        print(f"Form verified - Status: {form['status']}, Medications: 12 Yes, 1 No")
    
    def test_form_appears_in_dashboard(self, commander_token):
        """Verify submitted form appears in staff dashboard"""
        response = requests.get(
            f"{BASE_URL}/api/otc-permissions/dashboard",
            headers={"Authorization": f"Bearer {commander_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find the parent's cadet in dashboard
        cadet_item = None
        for item in data["items"]:
            if item["capid"] == PARENT_CAPID:
                cadet_item = item
                break
        
        assert cadet_item is not None, f"Cadet {PARENT_CAPID} should appear in dashboard"
        assert cadet_item["status"] in ["submitted", "reviewed"], f"Status should be submitted/reviewed, got {cadet_item['status']}"
        assert cadet_item["medications"] is not None, "Medications should be present"
        assert cadet_item["medications"]["orajel"] == False, "Orajel should be False in dashboard"
        
        print(f"Cadet found in dashboard: {cadet_item['name']} - Status: {cadet_item['status']}")


class TestOTCReviewFlow:
    """Test staff review functionality"""
    
    @pytest.fixture(scope="class")
    def commander_token(self):
        """Get commander auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def test_review_submitted_form(self, commander_token):
        """POST /api/otc-permissions/{capid}/review marks form as reviewed"""
        # First check current status
        dashboard_response = requests.get(
            f"{BASE_URL}/api/otc-permissions/dashboard",
            headers={"Authorization": f"Bearer {commander_token}"}
        )
        assert dashboard_response.status_code == 200
        dashboard = dashboard_response.json()
        
        # Find a submitted (not yet reviewed) form
        submitted_items = [i for i in dashboard["items"] if i["status"] == "submitted"]
        
        if not submitted_items:
            # Check if already reviewed
            reviewed_items = [i for i in dashboard["items"] if i["status"] == "reviewed"]
            if reviewed_items:
                print(f"Form already reviewed. Reviewed count: {len(reviewed_items)}")
                return
            pytest.skip("No submitted forms to review")
        
        capid = submitted_items[0]["capid"]
        
        # Review the form
        response = requests.post(
            f"{BASE_URL}/api/otc-permissions/{capid}/review",
            headers={"Authorization": f"Bearer {commander_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["status"] == "reviewed", f"Status should be 'reviewed', got {data['status']}"
        print(f"Form for CAPID {capid} marked as reviewed")
        
        # Verify in dashboard
        verify_response = requests.get(
            f"{BASE_URL}/api/otc-permissions/dashboard",
            headers={"Authorization": f"Bearer {commander_token}"}
        )
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        
        reviewed_item = next((i for i in verify_data["items"] if i["capid"] == capid), None)
        assert reviewed_item is not None, "Item should still exist in dashboard"
        assert reviewed_item["status"] == "reviewed", "Status should be reviewed in dashboard"
        print(f"Verified: {reviewed_item['name']} status is now 'reviewed'")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
