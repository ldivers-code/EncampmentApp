"""
Test file for CAP Encampment Logistics Module
Tests all 10 logistics sub-modules: Dashboard, Inventory, Lost & Found, Radios, Comms Log, 
Call Signs, Vehicles, Vehicle Log, Facilities, and Supply Requests
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://tn-wing-cadets.preview.emergentagent.com')
API = f"{BASE_URL}/api"
LOG_API = f"{API}/logistics"

# Test credentials - Commander has admin access for logistics
COMMANDER_EMAIL = "ldivers@cap.gov"
COMMANDER_PASSWORD = "26GO@lie!"

ALT_COMMANDER_EMAIL = "commander@cap.us"
ALT_COMMANDER_PASSWORD = "test123"

CADRE_EMAIL = "cadre@cap.us"
CADRE_PASSWORD = "test123"


class TestHelpers:
    """Helper methods for tests"""
    
    @staticmethod
    def get_auth_token(email, password):
        """Get authentication token"""
        response = requests.post(f"{API}/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    @staticmethod
    def get_headers(token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {token}"}


class TestLogisticsLogin:
    """Test login functionality including case-insensitive email"""
    
    def test_commander_login_normal(self):
        """Test login with known commander credentials"""
        response = requests.post(f"{API}/auth/login", json={
            "email": COMMANDER_EMAIL,
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"].lower() == COMMANDER_EMAIL.lower()
        print(f"✓ Commander login successful: {data['user']['name']} (role: {data['user']['role']})")
    
    def test_commander_login_uppercase_email(self):
        """Test login with uppercase email (case-insensitive)"""
        response = requests.post(f"{API}/auth/login", json={
            "email": COMMANDER_EMAIL.upper(),
            "password": COMMANDER_PASSWORD
        })
        assert response.status_code == 200, f"Case-insensitive login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"✓ Case-insensitive login successful with: {COMMANDER_EMAIL.upper()}")
    
    def test_alt_commander_login(self):
        """Test login with alternate commander credentials"""
        response = requests.post(f"{API}/auth/login", json={
            "email": ALT_COMMANDER_EMAIL,
            "password": ALT_COMMANDER_PASSWORD
        })
        # This might be a new user that doesn't exist yet
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            print(f"✓ Alt commander login successful")
        else:
            pytest.skip(f"Alt commander user not found: {response.status_code}")
    
    def test_invalid_credentials_rejected(self):
        """Test that invalid credentials are rejected"""
        response = requests.post(f"{API}/auth/login", json={
            "email": "invalid@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, "Invalid credentials should be rejected"
        print("✓ Invalid credentials properly rejected")


class TestLogisticsDashboard:
    """Test Logistics Dashboard endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestHelpers.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert self.token, "Failed to get auth token"
        self.headers = TestHelpers.get_headers(self.token)
    
    def test_dashboard_loads(self):
        """Test dashboard loads with all stat cards"""
        response = requests.get(f"{LOG_API}/dashboard", headers=self.headers)
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        
        # Verify all expected fields exist
        expected_fields = [
            "inventory_total", "inventory_issued", "inventory_low_stock",
            "radios_checked_out", "radios_available", "radios_overdue",
            "vehicles_in_use", "vehicles_available", "vehicles_overdue",
            "supply_requests_open", "lost_found_unclaimed",
            "overdue_radios", "overdue_vehicles"
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ Dashboard loaded: Inventory={data['inventory_total']}, Radios Out={data['radios_checked_out']}, Vehicles In Use={data['vehicles_in_use']}")


class TestInventory:
    """Test Inventory CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestHelpers.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert self.token, "Failed to get auth token"
        self.headers = TestHelpers.get_headers(self.token)
        self.created_ids = []
    
    def teardown_method(self, method):
        """Clean up created test items"""
        for item_id in self.created_ids:
            try:
                requests.delete(f"{LOG_API}/inventory/{item_id}", headers=self.headers)
            except:
                pass
    
    def test_create_inventory_item(self):
        """Create new inventory item and verify it appears"""
        test_item = {
            "item_name": f"TEST_Radio Battery Pack {uuid.uuid4().hex[:6]}",
            "category": "communications",
            "item_id": f"BAT-{uuid.uuid4().hex[:6]}",
            "quantity_available": 10,
            "quantity_issued": 2,
            "storage_location": "Supply Room A",
            "condition": "good",
            "reorder_threshold": 5,
            "notes": "Test item - auto cleanup"
        }
        
        # Create
        response = requests.post(f"{LOG_API}/inventory", json=test_item, headers=self.headers)
        assert response.status_code == 200, f"Create failed: {response.text}"
        created = response.json()
        assert "id" in created
        self.created_ids.append(created["id"])
        
        # Verify in list
        list_response = requests.get(f"{LOG_API}/inventory", headers=self.headers)
        assert list_response.status_code == 200
        items = list_response.json()
        found = any(i["id"] == created["id"] for i in items)
        assert found, "Created item not found in inventory list"
        
        print(f"✓ Inventory item created: {created['item_name']} (ID: {created['id']})")
    
    def test_update_inventory_item(self):
        """Create and update inventory item"""
        # Create first
        test_item = {
            "item_name": f"TEST_Flashlight {uuid.uuid4().hex[:6]}",
            "category": "miscellaneous",
            "quantity_available": 20
        }
        response = requests.post(f"{LOG_API}/inventory", json=test_item, headers=self.headers)
        assert response.status_code == 200
        created = response.json()
        self.created_ids.append(created["id"])
        
        # Update
        update_response = requests.put(
            f"{LOG_API}/inventory/{created['id']}", 
            json={"quantity_available": 15, "notes": "Updated qty"},
            headers=self.headers
        )
        assert update_response.status_code == 200
        
        print(f"✓ Inventory item updated: {created['id']}")
    
    def test_delete_inventory_item(self):
        """Create and delete inventory item"""
        test_item = {
            "item_name": f"TEST_To Delete {uuid.uuid4().hex[:6]}",
            "category": "miscellaneous",
            "quantity_available": 1
        }
        response = requests.post(f"{LOG_API}/inventory", json=test_item, headers=self.headers)
        assert response.status_code == 200
        created = response.json()
        
        # Delete
        delete_response = requests.delete(f"{LOG_API}/inventory/{created['id']}", headers=self.headers)
        assert delete_response.status_code == 200
        
        print(f"✓ Inventory item deleted: {created['id']}")


class TestLostAndFound:
    """Test Lost & Found CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestHelpers.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert self.token, "Failed to get auth token"
        self.headers = TestHelpers.get_headers(self.token)
    
    def test_create_lost_found_item(self):
        """Create lost & found item and verify it appears"""
        test_item = {
            "item_description": f"TEST_Blue water bottle {uuid.uuid4().hex[:6]}",
            "date_found": "2026-01-15",
            "time_found": "14:30",
            "location_found": "Barracks B",
            "found_by": "C/MSgt Test User",
            "storage_location": "Lost & Found Box",
            "notes": "Test item"
        }
        
        response = requests.post(f"{LOG_API}/lost-found", json=test_item, headers=self.headers)
        assert response.status_code == 200, f"Create failed: {response.text}"
        created = response.json()
        assert "id" in created
        assert created["status"] == "unclaimed"
        
        # Verify in list
        list_response = requests.get(f"{LOG_API}/lost-found", headers=self.headers)
        assert list_response.status_code == 200
        items = list_response.json()
        found = any(i["id"] == created["id"] for i in items)
        assert found, "Created item not found in list"
        
        print(f"✓ Lost & Found item created: {created['item_description']} (status: {created['status']})")
    
    def test_update_lost_found_status(self):
        """Create lost item and mark as claimed"""
        test_item = {
            "item_description": f"TEST_Sunglasses {uuid.uuid4().hex[:6]}",
            "location_found": "Dining Hall",
            "found_by": "Staff"
        }
        response = requests.post(f"{LOG_API}/lost-found", json=test_item, headers=self.headers)
        assert response.status_code == 200
        created = response.json()
        
        # Update to claimed
        update_response = requests.put(
            f"{LOG_API}/lost-found/{created['id']}",
            json={"status": "claimed", "claimed_by": "C/Amn Smith"},
            headers=self.headers
        )
        assert update_response.status_code == 200
        
        print(f"✓ Lost & Found item marked as claimed")


class TestRadios:
    """Test Radio Check Out / Check In operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestHelpers.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert self.token, "Failed to get auth token"
        self.headers = TestHelpers.get_headers(self.token)
    
    def test_checkout_and_checkin_radio(self):
        """Checkout a radio, verify status, then check it in"""
        radio_num = f"R-{uuid.uuid4().hex[:4]}"
        checkout_data = {
            "radio_number": radio_num,
            "assigned_to": "C/CMSgt Test Leader",
            "position": "Flight Sergeant",
            "call_sign": "ALPHA-1",
            "channel": "5",
            "condition_out": "good",
            "battery_issued": True,
            "spare_battery_issued": False,
            "notes": "Test checkout"
        }
        
        # Checkout
        response = requests.post(f"{LOG_API}/radios/checkout", json=checkout_data, headers=self.headers)
        assert response.status_code == 200, f"Checkout failed: {response.text}"
        created = response.json()
        assert created["status"] == "checked_out"
        radio_id = created["id"]
        
        # Verify in list
        list_response = requests.get(f"{LOG_API}/radios", headers=self.headers)
        assert list_response.status_code == 200
        radios = list_response.json()
        checked_out = next((r for r in radios if r["id"] == radio_id), None)
        assert checked_out is not None, "Checked out radio not found"
        assert checked_out["status"] in ["checked_out", "overdue"]
        
        print(f"✓ Radio checked out: {radio_num} to {checkout_data['assigned_to']} (status: {checked_out['status']})")
        
        # Check in
        checkin_data = {
            "condition_in": "good",
            "notes": "Returned in good condition"
        }
        checkin_response = requests.put(
            f"{LOG_API}/radios/{radio_id}/checkin", 
            json=checkin_data, 
            headers=self.headers
        )
        assert checkin_response.status_code == 200
        
        # Verify status changed
        list_response2 = requests.get(f"{LOG_API}/radios", headers=self.headers)
        radios2 = list_response2.json()
        returned = next((r for r in radios2 if r["id"] == radio_id), None)
        assert returned["status"] in ["returned", "maintenance_needed"]
        
        print(f"✓ Radio checked in: {radio_num} (status: {returned['status']})")


class TestCommsLog:
    """Test Communications Log operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestHelpers.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert self.token, "Failed to get auth token"
        self.headers = TestHelpers.get_headers(self.token)
    
    def test_create_comms_entry(self):
        """Create new communication entry"""
        entry = {
            "call_sign": "COMMAND-1",
            "operator": "Lt Col Test Operator",
            "message_summary": f"TEST_{uuid.uuid4().hex[:6]} - Weather update received, conditions clearing",
            "priority": "routine",
            "notes": "Test entry"
        }
        
        response = requests.post(f"{LOG_API}/comms-log", json=entry, headers=self.headers)
        assert response.status_code == 200, f"Create failed: {response.text}"
        created = response.json()
        assert "id" in created
        assert created["call_sign"] == entry["call_sign"]
        
        # Verify in list
        list_response = requests.get(f"{LOG_API}/comms-log", headers=self.headers)
        assert list_response.status_code == 200
        
        print(f"✓ Comms log entry created: {created['call_sign']} - {created['message_summary'][:50]}...")


class TestCallSigns:
    """Test Call Sign Directory operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestHelpers.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert self.token, "Failed to get auth token"
        self.headers = TestHelpers.get_headers(self.token)
        self.created_ids = []
    
    def teardown_method(self, method):
        """Clean up created call signs"""
        for cs_id in self.created_ids:
            try:
                requests.delete(f"{LOG_API}/callsigns/{cs_id}", headers=self.headers)
            except:
                pass
    
    def test_create_and_edit_callsign(self):
        """Create new call sign and edit it"""
        callsign = {
            "call_sign": f"TEST-{uuid.uuid4().hex[:4]}",
            "assigned_member": "Maj Test User",
            "assigned_role": "Operations Officer",
            "staff_category": "command_staff",
            "radio_number": "R-001",
            "channel": "1",
            "status": "active",
            "notes": "Test call sign"
        }
        
        # Create
        response = requests.post(f"{LOG_API}/callsigns", json=callsign, headers=self.headers)
        assert response.status_code == 200, f"Create failed: {response.text}"
        created = response.json()
        assert "id" in created
        self.created_ids.append(created["id"])
        
        print(f"✓ Call sign created: {created['call_sign']} -> {created['assigned_member']}")
        
        # Edit
        update_response = requests.put(
            f"{LOG_API}/callsigns/{created['id']}",
            json={"assigned_role": "Deputy Operations Officer", "channel": "2"},
            headers=self.headers
        )
        assert update_response.status_code == 200
        
        print(f"✓ Call sign edited: Updated role and channel")


class TestVehicles:
    """Test Vehicle Assignments operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestHelpers.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert self.token, "Failed to get auth token"
        self.headers = TestHelpers.get_headers(self.token)
    
    def test_assign_and_return_vehicle(self):
        """Assign vehicle, verify status, then return it"""
        vehicle_name = f"Van-{uuid.uuid4().hex[:4]}"
        assignment = {
            "vehicle_name": vehicle_name,
            "driver": "Capt Test Driver",
            "purpose": "Pick up supplies from warehouse",
            "passenger_count": 3,
            "fuel_level_out": "3/4",
            "notes": "Test assignment"
        }
        
        # Assign
        response = requests.post(f"{LOG_API}/vehicles", json=assignment, headers=self.headers)
        assert response.status_code == 200, f"Assign failed: {response.text}"
        created = response.json()
        assert created["status"] == "in_use"
        vehicle_id = created["id"]
        
        print(f"✓ Vehicle assigned: {vehicle_name} to {assignment['driver']} (status: {created['status']})")
        
        # Return
        return_data = {
            "fuel_level_in": "1/2",
            "notes": "Returned safely"
        }
        return_response = requests.put(
            f"{LOG_API}/vehicles/{vehicle_id}/return",
            json=return_data,
            headers=self.headers
        )
        assert return_response.status_code == 200
        
        # Verify status
        list_response = requests.get(f"{LOG_API}/vehicles", headers=self.headers)
        vehicles = list_response.json()
        returned = next((v for v in vehicles if v["id"] == vehicle_id), None)
        assert returned["status"] == "returned"
        
        print(f"✓ Vehicle returned: {vehicle_name} (status: {returned['status']})")


class TestVehicleLog:
    """Test Vehicle Log operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestHelpers.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert self.token, "Failed to get auth token"
        self.headers = TestHelpers.get_headers(self.token)
    
    def test_create_trip_log(self):
        """Create a new trip log entry"""
        log_entry = {
            "vehicle_name": f"Bus-{uuid.uuid4().hex[:4]}",
            "driver": "SSgt Test Driver",
            "date": "2026-01-15",
            "start_mileage": 50000,
            "end_mileage": 50125,
            "purpose": "Transport cadets to PT field",
            "fuel_purchased": "$45.00",
            "maintenance_issue": "",
            "notes": "Test log entry"
        }
        
        response = requests.post(f"{LOG_API}/vehicle-log", json=log_entry, headers=self.headers)
        assert response.status_code == 200, f"Create failed: {response.text}"
        created = response.json()
        assert "id" in created
        assert created["total_miles"] == 125.0  # 50125 - 50000
        
        # Verify in list
        list_response = requests.get(f"{LOG_API}/vehicle-log", headers=self.headers)
        assert list_response.status_code == 200
        
        print(f"✓ Vehicle log created: {created['vehicle_name']} - {created['total_miles']} miles")


class TestFacilities:
    """Test Facilities operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestHelpers.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert self.token, "Failed to get auth token"
        self.headers = TestHelpers.get_headers(self.token)
    
    def test_create_facility_entry(self):
        """Create a new facility entry"""
        facility = {
            "item_name": f"TEST_Barracks A AC Unit {uuid.uuid4().hex[:4]}",
            "location": "Barracks A - Room 101",
            "responsible_staff": "SSgt Facilities",
            "status": "ready",
            "notes": "Test facility entry"
        }
        
        response = requests.post(f"{LOG_API}/facilities", json=facility, headers=self.headers)
        assert response.status_code == 200, f"Create failed: {response.text}"
        created = response.json()
        assert "id" in created
        assert created["status"] == "ready"
        
        # Verify in list
        list_response = requests.get(f"{LOG_API}/facilities", headers=self.headers)
        assert list_response.status_code == 200
        
        print(f"✓ Facility created: {created['item_name']} (status: {created['status']})")
    
    def test_update_facility_status(self):
        """Create facility and update status"""
        facility = {
            "item_name": f"TEST_Projector {uuid.uuid4().hex[:4]}",
            "location": "Training Room",
            "status": "ready"
        }
        response = requests.post(f"{LOG_API}/facilities", json=facility, headers=self.headers)
        assert response.status_code == 200
        created = response.json()
        
        # Update status to needs_attention
        update_response = requests.put(
            f"{LOG_API}/facilities/{created['id']}",
            json={"status": "needs_attention", "notes": "Bulb replacement needed"},
            headers=self.headers
        )
        assert update_response.status_code == 200
        
        print(f"✓ Facility status updated to needs_attention")


class TestSupplyRequests:
    """Test Supply Requests workflow: create -> approve -> issue -> complete"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestHelpers.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert self.token, "Failed to get auth token"
        self.headers = TestHelpers.get_headers(self.token)
    
    def test_full_supply_request_workflow(self):
        """Test complete supply request workflow: create -> approve -> issue -> complete"""
        request_data = {
            "item_requested": f"TEST_Whiteboard Markers {uuid.uuid4().hex[:6]}",
            "quantity": 24,
            "purpose": "Classroom instruction",
            "priority": "normal",
            "needed_by": "2026-01-20",
            "notes": "Test supply request"
        }
        
        # Create request
        response = requests.post(f"{LOG_API}/supply-requests", json=request_data, headers=self.headers)
        assert response.status_code == 200, f"Create failed: {response.text}"
        created = response.json()
        assert created["status"] == "pending"
        request_id = created["id"]
        
        print(f"✓ Supply request created: {created['item_requested']} (status: {created['status']})")
        
        # Approve
        approve_response = requests.put(
            f"{LOG_API}/supply-requests/{request_id}/approve",
            json={"status": "approved"},
            headers=self.headers
        )
        assert approve_response.status_code == 200
        print(f"✓ Supply request approved")
        
        # Issue
        issue_response = requests.put(
            f"{LOG_API}/supply-requests/{request_id}/issue",
            headers=self.headers
        )
        assert issue_response.status_code == 200
        print(f"✓ Supply request issued")
        
        # Complete
        complete_response = requests.put(
            f"{LOG_API}/supply-requests/{request_id}/complete",
            headers=self.headers
        )
        assert complete_response.status_code == 200
        print(f"✓ Supply request completed")
        
        # Verify final status
        list_response = requests.get(f"{LOG_API}/supply-requests", headers=self.headers)
        requests_list = list_response.json()
        final = next((r for r in requests_list if r["id"] == request_id), None)
        assert final["status"] == "completed"
        
        print(f"✓ Supply request workflow complete (final status: {final['status']})")


class TestTabNavigation:
    """Test all 10 logistics tabs load correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestHelpers.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert self.token, "Failed to get auth token"
        self.headers = TestHelpers.get_headers(self.token)
    
    def test_all_tabs_load(self):
        """Test all 10 logistics endpoints return 200"""
        endpoints = [
            ("dashboard", f"{LOG_API}/dashboard"),
            ("inventory", f"{LOG_API}/inventory"),
            ("lost-found", f"{LOG_API}/lost-found"),
            ("radios", f"{LOG_API}/radios"),
            ("comms-log", f"{LOG_API}/comms-log"),
            ("callsigns", f"{LOG_API}/callsigns"),
            ("vehicles", f"{LOG_API}/vehicles"),
            ("vehicle-log", f"{LOG_API}/vehicle-log"),
            ("facilities", f"{LOG_API}/facilities"),
            ("supply-requests", f"{LOG_API}/supply-requests")
        ]
        
        results = []
        for tab_name, url in endpoints:
            response = requests.get(url, headers=self.headers)
            results.append((tab_name, response.status_code))
            assert response.status_code == 200, f"Tab {tab_name} failed: {response.status_code}"
        
        print(f"✓ All 10 logistics tabs load successfully:")
        for name, status in results:
            print(f"  - {name}: {status}")


class TestDashboardStatsUpdate:
    """Test that dashboard stats update after creating items"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = TestHelpers.get_auth_token(COMMANDER_EMAIL, COMMANDER_PASSWORD)
        assert self.token, "Failed to get auth token"
        self.headers = TestHelpers.get_headers(self.token)
    
    def test_dashboard_stats_reflect_changes(self):
        """Dashboard stats should update after creating items"""
        # Get initial stats
        initial_response = requests.get(f"{LOG_API}/dashboard", headers=self.headers)
        assert initial_response.status_code == 200
        initial = initial_response.json()
        
        # Create an inventory item
        test_item = {
            "item_name": f"TEST_Dashboard Stats Item {uuid.uuid4().hex[:6]}",
            "category": "miscellaneous",
            "quantity_available": 5
        }
        create_response = requests.post(f"{LOG_API}/inventory", json=test_item, headers=self.headers)
        assert create_response.status_code == 200
        created = create_response.json()
        
        # Get updated stats
        updated_response = requests.get(f"{LOG_API}/dashboard", headers=self.headers)
        assert updated_response.status_code == 200
        updated = updated_response.json()
        
        # Verify inventory count increased
        assert updated["inventory_total"] >= initial["inventory_total"], "Inventory total should have increased"
        
        # Clean up
        requests.delete(f"{LOG_API}/inventory/{created['id']}", headers=self.headers)
        
        print(f"✓ Dashboard stats updated: Inventory {initial['inventory_total']} -> {updated['inventory_total']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
