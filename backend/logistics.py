"""
Logistics Module - Backend API
All CRUD endpoints for the 10 logistics sub-modules.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from datetime import datetime, timezone
from typing import Optional
import uuid

LOGISTICS_ADMIN_ROLES = ["commander", "executive_staff", "logistics"]

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def new_id():
    return str(uuid.uuid4())

def today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def create_logistics_router(db, get_current_user):
    """Create and return a fully configured logistics router"""
    router = APIRouter(prefix="/api/logistics", tags=["logistics"])

    async def require_admin(user=Depends(get_current_user)):
        if user.get("role") not in LOGISTICS_ADMIN_ROLES:
            raise HTTPException(status_code=403, detail="Logistics admin access required")
        return user

    # ====================== DASHBOARD ======================

    @router.get("/dashboard")
    async def logistics_dashboard(user=Depends(get_current_user)):
        inv_total = await db.log_inventory.count_documents({})
        inv_issued = await db.log_inventory.count_documents({"quantity_issued": {"$gt": 0}})
        inv_low = await db.log_inventory.count_documents({"$expr": {"$lte": ["$quantity_available", "$reorder_threshold"]}})
        radios_out = await db.log_radios.count_documents({"status": "checked_out"})
        radios_avail = await db.log_radios.count_documents({"status": "available"})
        radios_overdue = await db.log_radios.count_documents({"status": "overdue"})
        vehicles_in_use = await db.log_vehicles.count_documents({"status": "in_use"})
        vehicles_avail = await db.log_vehicles.count_documents({"status": "available"})
        vehicles_overdue = await db.log_vehicles.count_documents({"status": "overdue"})
        supply_open = await db.log_supply_requests.count_documents({"status": {"$in": ["pending", "approved"]}})
        lost_unclaimed = await db.log_lost_found.count_documents({"status": "unclaimed"})
        overdue_radios = await db.log_radios.find({"status": "overdue"}, {"_id": 0}).to_list(20)
        overdue_vehicles = await db.log_vehicles.find({"status": "overdue"}, {"_id": 0}).to_list(20)
        return {
            "inventory_total": inv_total, "inventory_issued": inv_issued, "inventory_low_stock": inv_low,
            "radios_checked_out": radios_out, "radios_available": radios_avail, "radios_overdue": radios_overdue,
            "vehicles_in_use": vehicles_in_use, "vehicles_available": vehicles_avail, "vehicles_overdue": vehicles_overdue,
            "supply_requests_open": supply_open, "lost_found_unclaimed": lost_unclaimed,
            "overdue_radios": overdue_radios, "overdue_vehicles": overdue_vehicles
        }

    # ====================== INVENTORY ======================

    @router.get("/inventory")
    async def list_inventory(category: str = None, issued: str = None, search: str = None, user=Depends(get_current_user)):
        query = {}
        if category: query["category"] = category
        if issued == "true": query["quantity_issued"] = {"$gt": 0}
        if search:
            query["$or"] = [{"item_name": {"$regex": search, "$options": "i"}}, {"item_id": {"$regex": search, "$options": "i"}}, {"assigned_to": {"$regex": search, "$options": "i"}}]
        return await db.log_inventory.find(query, {"_id": 0}).sort("item_name", 1).to_list(500)

    @router.post("/inventory")
    async def create_inventory_item(item: dict = Body(...), user=Depends(require_admin)):
        doc = {"id": new_id(), "item_name": item.get("item_name",""), "category": item.get("category","miscellaneous"),
               "item_id": item.get("item_id",""), "quantity_available": item.get("quantity_available",0),
               "quantity_issued": item.get("quantity_issued",0), "storage_location": item.get("storage_location",""),
               "condition": item.get("condition","good"), "assigned_to": item.get("assigned_to",""),
               "reorder_threshold": item.get("reorder_threshold",0), "last_inventory_check": item.get("last_inventory_check",today_str()),
               "notes": item.get("notes",""), "created_by": user["id"], "created_at": now_iso()}
        await db.log_inventory.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @router.put("/inventory/{item_id}")
    async def update_inventory_item(item_id: str, update: dict = Body(...), user=Depends(require_admin)):
        allowed = {"item_name","category","item_id","quantity_available","quantity_issued","storage_location","condition","assigned_to","reorder_threshold","last_inventory_check","notes"}
        fields = {k: v for k, v in update.items() if k in allowed}
        fields["updated_by"] = user["id"]; fields["updated_at"] = now_iso()
        r = await db.log_inventory.update_one({"id": item_id}, {"$set": fields})
        if r.modified_count == 0: raise HTTPException(status_code=404, detail="Not found")
        return {"message": "Updated"}

    @router.delete("/inventory/{item_id}")
    async def delete_inventory_item(item_id: str, user=Depends(require_admin)):
        r = await db.log_inventory.delete_one({"id": item_id})
        if r.deleted_count == 0: raise HTTPException(status_code=404, detail="Not found")
        return {"message": "Deleted"}

    # ====================== LOST AND FOUND ======================

    @router.get("/lost-found")
    async def list_lost_found(status: str = None, search: str = None, user=Depends(get_current_user)):
        query = {}
        if status: query["status"] = status
        if search: query["$or"] = [{"item_description": {"$regex": search, "$options": "i"}}, {"found_by": {"$regex": search, "$options": "i"}}]
        return await db.log_lost_found.find(query, {"_id": 0}).sort("date_found", -1).to_list(500)

    @router.post("/lost-found")
    async def create_lost_found(item: dict = Body(...), user=Depends(require_admin)):
        doc = {"id": new_id(), "item_description": item.get("item_description",""), "date_found": item.get("date_found",today_str()),
               "time_found": item.get("time_found",""), "location_found": item.get("location_found",""),
               "found_by": item.get("found_by",""), "storage_location": item.get("storage_location",""),
               "claimed_by": "", "date_returned": "", "status": "unclaimed", "notes": item.get("notes",""),
               "created_by": user["id"], "created_at": now_iso()}
        await db.log_lost_found.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @router.put("/lost-found/{item_id}")
    async def update_lost_found(item_id: str, update: dict = Body(...), user=Depends(require_admin)):
        allowed = {"item_description","date_found","time_found","location_found","found_by","storage_location","claimed_by","date_returned","status","notes"}
        fields = {k: v for k, v in update.items() if k in allowed}
        fields["updated_at"] = now_iso()
        await db.log_lost_found.update_one({"id": item_id}, {"$set": fields})
        return {"message": "Updated"}

    # ====================== RADIO CHECK OUT / CHECK IN ======================

    @router.get("/radios")
    async def list_radios(status: str = None, user=Depends(get_current_user)):
        query = {}
        if status: query["status"] = status
        radios = await db.log_radios.find(query, {"_id": 0}).sort([("status", 1), ("radio_number", 1)]).to_list(500)
        now = datetime.now(timezone.utc)
        for r in radios:
            if r.get("status") == "checked_out" and r.get("expected_return"):
                try:
                    exp = datetime.fromisoformat(r["expected_return"].replace("Z","+00:00"))
                    if now > exp:
                        r["status"] = "overdue"
                        r["overdue_minutes"] = int((now - exp).total_seconds() / 60)
                        await db.log_radios.update_one({"id": r["id"]}, {"$set": {"status": "overdue"}})
                except: pass
        radios.sort(key=lambda x: (0 if x.get("status") == "overdue" else 1, x.get("radio_number","")))
        return radios

    @router.post("/radios/checkout")
    async def checkout_radio(data: dict = Body(...), user=Depends(require_admin)):
        doc = {"id": new_id(), "radio_number": data.get("radio_number",""), "assigned_to": data.get("assigned_to",""),
               "position": data.get("position",""), "call_sign": data.get("call_sign",""), "channel": data.get("channel",""),
               "time_out": data.get("time_out", now_iso()), "expected_return": data.get("expected_return",""),
               "time_in": "", "condition_out": data.get("condition_out","good"), "condition_in": "",
               "battery_issued": data.get("battery_issued", False), "spare_battery_issued": data.get("spare_battery_issued", False),
               "notes": data.get("notes",""), "status": "checked_out",
               "created_by": user["id"], "created_by_name": user["name"], "created_at": now_iso()}
        await db.log_radios.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @router.put("/radios/{radio_id}/checkin")
    async def checkin_radio(radio_id: str, data: dict = Body(...), user=Depends(require_admin)):
        fields = {"time_in": data.get("time_in", now_iso()), "condition_in": data.get("condition_in","good"),
                  "status": "returned" if data.get("condition_in","good") != "needs_maintenance" else "maintenance_needed",
                  "notes": data.get("notes",""), "checked_in_by": user["id"], "checked_in_at": now_iso()}
        await db.log_radios.update_one({"id": radio_id}, {"$set": fields})
        return {"message": "Checked in"}

    @router.put("/radios/{radio_id}")
    async def update_radio(radio_id: str, update: dict = Body(...), user=Depends(require_admin)):
        allowed = {"assigned_to","position","call_sign","channel","expected_return","status","notes","condition_out"}
        fields = {k: v for k, v in update.items() if k in allowed}
        fields["updated_at"] = now_iso()
        await db.log_radios.update_one({"id": radio_id}, {"$set": fields})
        return {"message": "Updated"}

    @router.post("/radios/reset-available")
    async def reset_radio_available(data: dict = Body(...), user=Depends(require_admin)):
        await db.log_radios.update_one({"id": data.get("id")}, {"$set": {
            "status": "available", "assigned_to": "", "position": "", "call_sign": "",
            "time_out": "", "time_in": "", "expected_return": "", "condition_out": "good", "condition_in": "",
            "notes": "", "updated_at": now_iso()}})
        return {"message": "Reset"}

    # ====================== COMMUNICATIONS LOG ======================

    @router.get("/comms-log")
    async def list_comms_log(call_sign: str = None, priority: str = None, user=Depends(get_current_user)):
        query = {}
        if call_sign: query["call_sign"] = {"$regex": call_sign, "$options": "i"}
        if priority: query["priority"] = priority
        return await db.log_comms.find(query, {"_id": 0}).sort("time", -1).to_list(500)

    @router.post("/comms-log")
    async def create_comms_entry(entry: dict = Body(...), user=Depends(require_admin)):
        doc = {"id": new_id(), "time": entry.get("time", now_iso()), "call_sign": entry.get("call_sign",""),
               "operator": entry.get("operator",""), "message_summary": entry.get("message_summary",""),
               "priority": entry.get("priority","routine"), "notes": entry.get("notes",""),
               "created_by": user["id"], "created_by_name": user["name"], "created_at": now_iso()}
        await db.log_comms.insert_one(doc)
        doc.pop("_id", None)
        return doc

    # ====================== CALL SIGN DIRECTORY ======================

    @router.get("/callsigns")
    async def list_callsigns(status: str = None, category: str = None, user=Depends(get_current_user)):
        query = {}
        if status: query["status"] = status
        if category: query["staff_category"] = category
        return await db.log_callsigns.find(query, {"_id": 0}).sort("call_sign", 1).to_list(500)

    @router.post("/callsigns")
    async def create_callsign(data: dict = Body(...), user=Depends(require_admin)):
        doc = {"id": new_id(), "call_sign": data.get("call_sign",""), "assigned_member": data.get("assigned_member",""),
               "assigned_role": data.get("assigned_role",""), "staff_category": data.get("staff_category",""),
               "radio_number": data.get("radio_number",""), "channel": data.get("channel",""),
               "alternate_member": data.get("alternate_member",""), "alternate_role": data.get("alternate_role",""),
               "notes": data.get("notes",""), "status": data.get("status","active"),
               "created_by": user["id"], "created_at": now_iso()}
        await db.log_callsigns.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @router.put("/callsigns/{cs_id}")
    async def update_callsign(cs_id: str, update: dict = Body(...), user=Depends(require_admin)):
        allowed = {"call_sign","assigned_member","assigned_role","staff_category","radio_number","channel","alternate_member","alternate_role","notes","status"}
        fields = {k: v for k, v in update.items() if k in allowed}
        fields["updated_at"] = now_iso()
        await db.log_callsigns.update_one({"id": cs_id}, {"$set": fields})
        return {"message": "Updated"}

    @router.delete("/callsigns/{cs_id}")
    async def delete_callsign(cs_id: str, user=Depends(require_admin)):
        await db.log_callsigns.delete_one({"id": cs_id})
        return {"message": "Deleted"}

    # ====================== VEHICLE ASSIGNMENTS ======================

    @router.get("/vehicles")
    async def list_vehicles(status: str = None, user=Depends(get_current_user)):
        query = {}
        if status: query["status"] = status
        vehicles = await db.log_vehicles.find(query, {"_id": 0}).sort("vehicle_name", 1).to_list(500)
        now = datetime.now(timezone.utc)
        for v in vehicles:
            if v.get("status") == "in_use" and v.get("expected_return"):
                try:
                    exp = datetime.fromisoformat(v["expected_return"].replace("Z","+00:00"))
                    if now > exp:
                        v["status"] = "overdue"
                        v["overdue_minutes"] = int((now - exp).total_seconds() / 60)
                        await db.log_vehicles.update_one({"id": v["id"]}, {"$set": {"status": "overdue"}})
                except: pass
        vehicles.sort(key=lambda x: (0 if x.get("status") == "overdue" else 1, x.get("vehicle_name","")))
        return vehicles

    @router.post("/vehicles")
    async def create_vehicle(data: dict = Body(...), user=Depends(require_admin)):
        doc = {"id": new_id(), "vehicle_name": data.get("vehicle_name",""), "driver": data.get("driver",""),
               "purpose": data.get("purpose",""), "departure_time": data.get("departure_time", now_iso()),
               "expected_return": data.get("expected_return",""), "actual_return": "",
               "passenger_count": data.get("passenger_count",0), "fuel_level_out": data.get("fuel_level_out",""),
               "fuel_level_in": "", "status": "in_use", "notes": data.get("notes",""),
               "created_by": user["id"], "created_by_name": user["name"], "created_at": now_iso()}
        await db.log_vehicles.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @router.put("/vehicles/{v_id}/return")
    async def return_vehicle(v_id: str, data: dict = Body(...), user=Depends(require_admin)):
        fields = {"actual_return": data.get("actual_return", now_iso()), "fuel_level_in": data.get("fuel_level_in",""),
                  "status": "returned", "notes": data.get("notes",""), "returned_by": user["id"], "returned_at": now_iso()}
        await db.log_vehicles.update_one({"id": v_id}, {"$set": fields})
        return {"message": "Returned"}

    @router.put("/vehicles/{v_id}")
    async def update_vehicle(v_id: str, update: dict = Body(...), user=Depends(require_admin)):
        allowed = {"vehicle_name","driver","purpose","expected_return","status","passenger_count","fuel_level_out","notes"}
        fields = {k: v for k, v in update.items() if k in allowed}
        fields["updated_at"] = now_iso()
        await db.log_vehicles.update_one({"id": v_id}, {"$set": fields})
        return {"message": "Updated"}

    # ====================== VEHICLE LOG ======================

    @router.get("/vehicle-log")
    async def list_vehicle_log(vehicle: str = None, driver: str = None, date: str = None, user=Depends(get_current_user)):
        query = {}
        if vehicle: query["vehicle_name"] = {"$regex": vehicle, "$options": "i"}
        if driver: query["driver"] = {"$regex": driver, "$options": "i"}
        if date: query["date"] = date
        return await db.log_vehicle_log.find(query, {"_id": 0}).sort("date", -1).to_list(500)

    @router.post("/vehicle-log")
    async def create_vehicle_log(data: dict = Body(...), user=Depends(require_admin)):
        start = data.get("start_mileage", 0); end = data.get("end_mileage", 0)
        try: total = float(end) - float(start) if end and start else 0
        except: total = 0
        doc = {"id": new_id(), "vehicle_name": data.get("vehicle_name",""), "driver": data.get("driver",""),
               "date": data.get("date", today_str()), "start_mileage": start, "end_mileage": end,
               "total_miles": round(total, 1), "purpose": data.get("purpose",""),
               "fuel_purchased": data.get("fuel_purchased",""), "maintenance_issue": data.get("maintenance_issue",""),
               "notes": data.get("notes",""), "created_by": user["id"], "created_at": now_iso()}
        await db.log_vehicle_log.insert_one(doc)
        doc.pop("_id", None)
        return doc

    # ====================== FACILITIES ======================

    @router.get("/facilities")
    async def list_facilities(status: str = None, user=Depends(get_current_user)):
        query = {}
        if status: query["status"] = status
        return await db.log_facilities.find(query, {"_id": 0}).sort("item_name", 1).to_list(500)

    @router.post("/facilities")
    async def create_facility(data: dict = Body(...), user=Depends(require_admin)):
        doc = {"id": new_id(), "item_name": data.get("item_name",""), "location": data.get("location",""),
               "responsible_staff": data.get("responsible_staff",""), "status": data.get("status","ready"),
               "notes": data.get("notes",""), "created_by": user["id"], "created_at": now_iso()}
        await db.log_facilities.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @router.put("/facilities/{f_id}")
    async def update_facility(f_id: str, update: dict = Body(...), user=Depends(require_admin)):
        allowed = {"item_name","location","responsible_staff","status","notes"}
        fields = {k: v for k, v in update.items() if k in allowed}
        fields["updated_at"] = now_iso()
        await db.log_facilities.update_one({"id": f_id}, {"$set": fields})
        return {"message": "Updated"}

    # ====================== SUPPLY REQUESTS ======================

    @router.get("/supply-requests")
    async def list_supply_requests(status: str = None, user=Depends(get_current_user)):
        query = {}
        if status: query["status"] = status
        return await db.log_supply_requests.find(query, {"_id": 0}).sort([("status", 1), ("date_requested", -1)]).to_list(500)

    @router.post("/supply-requests")
    async def create_supply_request(data: dict = Body(...), user=Depends(get_current_user)):
        doc = {"id": new_id(), "requestor": data.get("requestor", user["name"]),
               "requestor_role": data.get("requestor_role", user.get("role","")),
               "item_requested": data.get("item_requested",""), "quantity": data.get("quantity",1),
               "purpose": data.get("purpose",""), "priority": data.get("priority","normal"),
               "date_requested": today_str(), "needed_by": data.get("needed_by",""),
               "approved_by": "", "issued_by": "", "status": "pending", "notes": data.get("notes",""),
               "created_by": user["id"], "created_by_name": user["name"], "created_at": now_iso()}
        await db.log_supply_requests.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @router.put("/supply-requests/{req_id}/approve")
    async def approve_supply_request(req_id: str, data: dict = Body(...), user=Depends(require_admin)):
        s = data.get("status","approved")
        fields = {"status": s, "approved_by": user["name"], "approved_at": now_iso()}
        if data.get("notes"): fields["notes"] = data["notes"]
        await db.log_supply_requests.update_one({"id": req_id}, {"$set": fields})
        return {"message": f"Request {s}"}

    @router.put("/supply-requests/{req_id}/issue")
    async def issue_supply_request(req_id: str, user=Depends(require_admin)):
        await db.log_supply_requests.update_one({"id": req_id}, {"$set": {"status": "issued", "issued_by": user["name"], "issued_at": now_iso()}})
        return {"message": "Issued"}

    @router.put("/supply-requests/{req_id}/complete")
    async def complete_supply_request(req_id: str, user=Depends(require_admin)):
        await db.log_supply_requests.update_one({"id": req_id}, {"$set": {"status": "completed", "completed_at": now_iso()}})
        return {"message": "Completed"}

    return router
