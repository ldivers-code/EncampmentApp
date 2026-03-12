"""
Status Board Module - Backend API
Control View (staff editing) + Display View (projector read-only)
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from datetime import datetime, timezone
from typing import Optional
import uuid

# Roles that can edit status board data
SB_EDITOR_ROLES = [
    "commander", "executive_staff", "staff", "plans_programs",
    "logistics", "health_services", "training_officer"
]
# Roles that can trigger emergency banner
SB_EMERGENCY_ROLES = ["commander", "executive_staff"]


def now_iso():
    return datetime.now(timezone.utc).isoformat()

def new_id():
    return str(uuid.uuid4())


def create_statusboard_router(db, get_current_user):
    router = APIRouter(prefix="/api/statusboard", tags=["statusboard"])

    async def require_editor(user=Depends(get_current_user)):
        if user.get("role") not in SB_EDITOR_ROLES:
            raise HTTPException(status_code=403, detail="Status board editor access required")
        return user

    async def require_emergency(user=Depends(get_current_user)):
        if user.get("role") not in SB_EMERGENCY_ROLES:
            raise HTTPException(status_code=403, detail="Emergency banner requires commander access")
        return user

    async def log_audit(action, details, user):
        await db.sb_audit_log.insert_one({
            "id": new_id(),
            "action": action,
            "details": details,
            "user_id": user.get("id"),
            "user_name": user.get("name", user.get("email")),
            "timestamp": now_iso(),
        })

    # =================== DISPLAY DATA (read-only, no auth for projector) ===================

    @router.get("/display")
    async def get_display_data():
        """Single endpoint returning all data needed for projector display"""
        flights = await db.sb_flights.find({}, {"_id": 0}).sort("name", 1).to_list(50)
        issues = await db.sb_issues.find(
            {"status": {"$in": ["open", "in_progress"]}},
            {"_id": 0}
        ).sort("severity", 1).to_list(20)
        announcements = await db.sb_announcements.find(
            {"active": True}, {"_id": 0}
        ).sort("priority", 1).to_list(10)
        resources = await db.sb_resources.find({}, {"_id": 0}).to_list(50)
        settings = await db.sb_display_settings.find_one({"_id": "settings"})
        schedule = await db.sb_schedule_events.find(
            {"status": {"$ne": "cancelled"}},
            {"_id": 0}
        ).sort("start_time", 1).to_list(50)

        s = settings or {}
        return {
            "flights": flights,
            "issues": issues,
            "announcements": announcements,
            "resources": resources,
            "schedule": schedule,
            "settings": {
                "dark_mode": s.get("dark_mode", True),
                "auto_rotate_enabled": s.get("auto_rotate_enabled", True),
                "auto_rotate_seconds": s.get("auto_rotate_seconds", 25),
                "show_footer": s.get("show_footer", True),
                "show_clock": s.get("show_clock", True),
                "emergency_banner_active": s.get("emergency_banner_active", False),
                "emergency_banner_message": s.get("emergency_banner_message", ""),
                "heat_category": s.get("heat_category", "green"),
                "weather_condition": s.get("weather_condition", "Clear"),
                "encampment_day": s.get("encampment_day", "Day 1"),
                "encampment_phase": s.get("encampment_phase", "Operations"),
            },
            "last_updated": now_iso(),
        }

    # =================== FLIGHTS ===================

    @router.get("/flights")
    async def list_flights(user=Depends(get_current_user)):
        return await db.sb_flights.find({}, {"_id": 0}).sort("name", 1).to_list(50)

    @router.post("/flights")
    async def create_flight(data: dict = Body(...), user=Depends(require_editor)):
        doc = {
            "id": new_id(),
            "name": data.get("name", ""),
            "current_location": data.get("current_location", ""),
            "current_status": data.get("current_status", "Standing By"),
            "status_level": data.get("status_level", "green"),
            "short_note": data.get("short_note", ""),
            "updated_by": user.get("name", user.get("email")),
            "updated_at": now_iso(),
        }
        await db.sb_flights.insert_one(doc)
        doc.pop("_id", None)
        await log_audit("flight_created", f"Flight '{doc['name']}' created", user)
        return doc

    @router.put("/flights/{fid}")
    async def update_flight(fid: str, data: dict = Body(...), user=Depends(require_editor)):
        update = {
            "current_location": data.get("current_location", ""),
            "current_status": data.get("current_status", ""),
            "status_level": data.get("status_level", "green"),
            "short_note": data.get("short_note", ""),
            "updated_by": user.get("name", user.get("email")),
            "updated_at": now_iso(),
        }
        if "name" in data:
            update["name"] = data["name"]
        r = await db.sb_flights.update_one({"id": fid}, {"$set": update})
        if r.modified_count == 0:
            raise HTTPException(status_code=404, detail="Flight not found")
        await log_audit("flight_updated", f"Flight '{update.get('name', fid)}' status → {update['current_status']}", user)
        return {"message": "Updated"}

    @router.delete("/flights/{fid}")
    async def delete_flight(fid: str, user=Depends(require_editor)):
        r = await db.sb_flights.delete_one({"id": fid})
        if r.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Not found")
        await log_audit("flight_deleted", f"Flight {fid} deleted", user)
        return {"message": "Deleted"}

    # =================== ISSUES ===================

    @router.get("/issues")
    async def list_issues(user=Depends(get_current_user)):
        return await db.sb_issues.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)

    @router.post("/issues")
    async def create_issue(data: dict = Body(...), user=Depends(require_editor)):
        doc = {
            "id": new_id(),
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "severity": data.get("severity", "medium"),
            "assigned_section": data.get("assigned_section", ""),
            "status": "open",
            "created_by": user.get("name", user.get("email")),
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        await db.sb_issues.insert_one(doc)
        doc.pop("_id", None)
        await log_audit("issue_created", f"Issue '{doc['title']}' ({doc['severity']})", user)
        return doc

    @router.put("/issues/{iid}")
    async def update_issue(iid: str, data: dict = Body(...), user=Depends(require_editor)):
        update = {k: v for k, v in data.items() if k != "id"}
        update["updated_at"] = now_iso()
        r = await db.sb_issues.update_one({"id": iid}, {"$set": update})
        if r.modified_count == 0:
            raise HTTPException(status_code=404, detail="Not found")
        await log_audit("issue_updated", f"Issue {iid} updated: {list(update.keys())}", user)
        return {"message": "Updated"}

    # =================== ANNOUNCEMENTS ===================

    @router.get("/announcements")
    async def list_announcements(user=Depends(get_current_user)):
        return await db.sb_announcements.find({}, {"_id": 0}).sort("priority", 1).to_list(50)

    @router.post("/announcements")
    async def create_announcement(data: dict = Body(...), user=Depends(require_editor)):
        doc = {
            "id": new_id(),
            "message": data.get("message", ""),
            "priority": data.get("priority", "normal"),
            "active": True,
            "created_by": user.get("name", user.get("email")),
            "created_at": now_iso(),
        }
        await db.sb_announcements.insert_one(doc)
        doc.pop("_id", None)
        await log_audit("announcement_created", f"Announcement: {doc['message'][:50]}", user)
        return doc

    @router.put("/announcements/{aid}")
    async def update_announcement(aid: str, data: dict = Body(...), user=Depends(require_editor)):
        update = {k: v for k, v in data.items() if k != "id"}
        r = await db.sb_announcements.update_one({"id": aid}, {"$set": update})
        if r.modified_count == 0:
            raise HTTPException(status_code=404, detail="Not found")
        await log_audit("announcement_updated", f"Announcement {aid} updated", user)
        return {"message": "Updated"}

    @router.delete("/announcements/{aid}")
    async def delete_announcement(aid: str, user=Depends(require_editor)):
        await db.sb_announcements.delete_one({"id": aid})
        await log_audit("announcement_deleted", f"Announcement {aid} deleted", user)
        return {"message": "Deleted"}

    # =================== SCHEDULE EVENTS ===================

    @router.get("/schedule")
    async def list_schedule(user=Depends(get_current_user)):
        return await db.sb_schedule_events.find({}, {"_id": 0}).sort("start_time", 1).to_list(100)

    @router.post("/schedule")
    async def create_schedule_event(data: dict = Body(...), user=Depends(require_editor)):
        doc = {
            "id": new_id(),
            "title": data.get("title", ""),
            "start_time": data.get("start_time", ""),
            "end_time": data.get("end_time", ""),
            "location": data.get("location", ""),
            "section": data.get("section", ""),
            "status": data.get("status", "scheduled"),
            "display_priority": data.get("display_priority", "normal"),
            "created_by": user.get("name", user.get("email")),
            "created_at": now_iso(),
        }
        await db.sb_schedule_events.insert_one(doc)
        doc.pop("_id", None)
        await log_audit("schedule_created", f"Event '{doc['title']}' at {doc['start_time']}", user)
        return doc

    @router.put("/schedule/{sid}")
    async def update_schedule_event(sid: str, data: dict = Body(...), user=Depends(require_editor)):
        update = {k: v for k, v in data.items() if k != "id"}
        update["updated_at"] = now_iso()
        r = await db.sb_schedule_events.update_one({"id": sid}, {"$set": update})
        if r.modified_count == 0:
            raise HTTPException(status_code=404, detail="Not found")
        await log_audit("schedule_updated", f"Event {sid} updated", user)
        return {"message": "Updated"}

    @router.delete("/schedule/{sid}")
    async def delete_schedule_event(sid: str, user=Depends(require_editor)):
        await db.sb_schedule_events.delete_one({"id": sid})
        return {"message": "Deleted"}

    # =================== RESOURCES ===================

    @router.get("/resources")
    async def list_resources(user=Depends(get_current_user)):
        return await db.sb_resources.find({}, {"_id": 0}).sort("type", 1).to_list(100)

    @router.post("/resources")
    async def create_resource(data: dict = Body(...), user=Depends(require_editor)):
        doc = {
            "id": new_id(),
            "type": data.get("type", "equipment"),
            "name": data.get("name", ""),
            "status": data.get("status", "available"),
            "assigned_to": data.get("assigned_to", ""),
            "location": data.get("location", ""),
            "notes": data.get("notes", ""),
            "updated_at": now_iso(),
        }
        await db.sb_resources.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @router.put("/resources/{rid}")
    async def update_resource(rid: str, data: dict = Body(...), user=Depends(require_editor)):
        update = {k: v for k, v in data.items() if k != "id"}
        update["updated_at"] = now_iso()
        r = await db.sb_resources.update_one({"id": rid}, {"$set": update})
        if r.modified_count == 0:
            raise HTTPException(status_code=404, detail="Not found")
        return {"message": "Updated"}

    # =================== DISPLAY SETTINGS ===================

    @router.get("/settings")
    async def get_settings(user=Depends(get_current_user)):
        s = await db.sb_display_settings.find_one({"_id": "settings"})
        if not s:
            return {
                "dark_mode": True, "auto_rotate_enabled": True, "auto_rotate_seconds": 25,
                "show_footer": True, "show_clock": True,
                "emergency_banner_active": False, "emergency_banner_message": "",
                "heat_category": "green", "weather_condition": "Clear",
                "encampment_day": "Day 1", "encampment_phase": "Operations",
            }
        s.pop("_id", None)
        return s

    @router.put("/settings")
    async def update_settings(data: dict = Body(...), user=Depends(require_editor)):
        safe = {k: v for k, v in data.items() if k not in ("_id", "emergency_banner_active", "emergency_banner_message")}
        safe["updated_at"] = now_iso()
        safe["updated_by"] = user.get("name", user.get("email"))
        await db.sb_display_settings.update_one({"_id": "settings"}, {"$set": safe}, upsert=True)
        await log_audit("settings_updated", f"Display settings updated: {list(safe.keys())}", user)
        return {"message": "Settings updated"}

    @router.put("/emergency")
    async def update_emergency_banner(data: dict = Body(...), user=Depends(require_emergency)):
        update = {
            "emergency_banner_active": data.get("active", False),
            "emergency_banner_message": data.get("message", ""),
            "emergency_updated_by": user.get("name", user.get("email")),
            "emergency_updated_at": now_iso(),
        }
        await db.sb_display_settings.update_one({"_id": "settings"}, {"$set": update}, upsert=True)
        action = "emergency_activated" if update["emergency_banner_active"] else "emergency_deactivated"
        await log_audit(action, f"Emergency: {update['emergency_banner_message']}", user)
        return {"message": "Emergency banner updated"}

    # =================== AUDIT LOG ===================

    @router.get("/audit")
    async def get_audit_log(limit: int = 50, user=Depends(get_current_user)):
        return await db.sb_audit_log.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)

    # =================== SEED DATA ===================

    @router.post("/seed")
    async def seed_data(user=Depends(require_editor)):
        """Seed sample data for testing"""
        now = now_iso()
        uname = user.get("name", "System")

        # Flights
        flights = [
            {"id": new_id(), "name": "Alpha Flight", "current_location": "Classroom A", "current_status": "Academic Block", "status_level": "green", "short_note": "On schedule", "updated_by": uname, "updated_at": now},
            {"id": new_id(), "name": "Bravo Flight", "current_location": "Drill Pad", "current_status": "Drill & Ceremony", "status_level": "green", "short_note": "", "updated_by": uname, "updated_at": now},
            {"id": new_id(), "name": "Charlie Flight", "current_location": "DFAC", "current_status": "Lunch", "status_level": "blue", "short_note": "Running 5 min behind", "updated_by": uname, "updated_at": now},
            {"id": new_id(), "name": "Delta Flight", "current_location": "Field House", "current_status": "PT / Fitness", "status_level": "green", "short_note": "", "updated_by": uname, "updated_at": now},
            {"id": new_id(), "name": "Echo Flight", "current_location": "Barracks", "current_status": "Uniform Change", "status_level": "yellow", "short_note": "Heat recovery break", "updated_by": uname, "updated_at": now},
            {"id": new_id(), "name": "Cadre", "current_location": "HQ", "current_status": "Staff Meeting", "status_level": "green", "short_note": "", "updated_by": uname, "updated_at": now},
        ]

        # Schedule events
        events = [
            {"id": new_id(), "title": "Lunch - All Flights", "start_time": "1200", "end_time": "1300", "location": "DFAC", "section": "Logistics", "status": "scheduled", "display_priority": "normal", "created_by": uname, "created_at": now},
            {"id": new_id(), "title": "Commander's Call", "start_time": "1400", "end_time": "1430", "location": "Auditorium", "section": "Command", "status": "scheduled", "display_priority": "high", "created_by": uname, "created_at": now},
            {"id": new_id(), "title": "Evening Colors", "start_time": "1700", "end_time": "1715", "location": "Parade Field", "section": "Command", "status": "scheduled", "display_priority": "normal", "created_by": uname, "created_at": now},
            {"id": new_id(), "title": "Dinner", "start_time": "1730", "end_time": "1830", "location": "DFAC", "section": "Logistics", "status": "scheduled", "display_priority": "normal", "created_by": uname, "created_at": now},
            {"id": new_id(), "title": "Study Hall / Free Time", "start_time": "1900", "end_time": "2030", "location": "Barracks", "section": "Commandant", "status": "scheduled", "display_priority": "normal", "created_by": uname, "created_at": now},
        ]

        # Issues
        issues = [
            {"id": new_id(), "title": "Projector bulb out in Room 204", "description": "Main projector not working", "severity": "medium", "assigned_section": "Logistics", "status": "open", "created_by": uname, "created_at": now, "updated_at": now},
            {"id": new_id(), "title": "Low water supply at Field House", "description": "Water cooler needs refill", "severity": "high", "assigned_section": "Logistics", "status": "in_progress", "created_by": uname, "created_at": now, "updated_at": now},
        ]

        # Announcements
        announcements = [
            {"id": new_id(), "message": "Hydration reminder - drink water regularly. Heat Cat is GREEN.", "priority": "normal", "active": True, "created_by": uname, "created_at": now},
            {"id": new_id(), "message": "Uniform for tomorrow: ABU / BDU. Check dashboard for details.", "priority": "normal", "active": True, "created_by": uname, "created_at": now},
        ]

        # Resources
        resources = [
            {"id": new_id(), "type": "radio", "name": "Radio 1", "status": "checked_out", "assigned_to": "Alpha Flight TAC", "location": "Field", "notes": "", "updated_at": now},
            {"id": new_id(), "type": "radio", "name": "Radio 2", "status": "available", "assigned_to": "", "location": "HQ", "notes": "", "updated_at": now},
            {"id": new_id(), "type": "vehicle", "name": "Van 1 (White)", "status": "in_use", "assigned_to": "Logistics", "location": "DFAC Run", "notes": "Back by 1300", "updated_at": now},
            {"id": new_id(), "type": "vehicle", "name": "Van 2 (Blue)", "status": "available", "assigned_to": "", "location": "Parking Lot", "notes": "", "updated_at": now},
            {"id": new_id(), "type": "equipment", "name": "PA System", "status": "in_use", "assigned_to": "Auditorium", "location": "Auditorium", "notes": "", "updated_at": now},
        ]

        # Settings
        settings = {
            "_id": "settings",
            "dark_mode": True, "auto_rotate_enabled": True, "auto_rotate_seconds": 25,
            "show_footer": True, "show_clock": True,
            "emergency_banner_active": False, "emergency_banner_message": "",
            "heat_category": "green", "weather_condition": "Clear, 85F",
            "encampment_day": "Day 3", "encampment_phase": "Training Operations",
            "updated_at": now,
        }

        # Clear and insert
        await db.sb_flights.delete_many({})
        await db.sb_issues.delete_many({})
        await db.sb_announcements.delete_many({})
        await db.sb_resources.delete_many({})
        await db.sb_schedule_events.delete_many({})
        await db.sb_display_settings.delete_many({})

        await db.sb_flights.insert_many(flights)
        await db.sb_schedule_events.insert_many(events)
        await db.sb_issues.insert_many(issues)
        await db.sb_announcements.insert_many(announcements)
        await db.sb_resources.insert_many(resources)
        await db.sb_display_settings.insert_one(settings)

        await log_audit("seed_data", "Status board seeded with sample data", user)
        return {"message": "Seeded", "flights": len(flights), "events": len(events), "issues": len(issues)}

    return router
