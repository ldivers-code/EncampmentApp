"""
Health Services Module for CAP Encampment
Manages medication tracking, incident logging, and health status for cadets
Uses Google Sheets as backend for historical reporting
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import pandas as pd
import requests
from io import StringIO
import os

# Health Services Router
health_router = APIRouter(prefix="/api/health", tags=["Health Services"])

# ================= MODELS =================

class MedicationProfile(BaseModel):
    med_profile_id: Optional[str] = None
    event_id: str
    cadet_id_internal: str
    capid: str
    medication_name: str
    dose: str
    route: str  # oral, injection, topical, inhaled, etc.
    schedule_text: str  # "Every 8 hours", "With meals", etc.
    due_times: str  # "0800,1200,1800,2200"
    special_instructions: Optional[str] = None
    refrigeration_required: bool = False
    rescue_med_flag: bool = False  # EpiPen, inhaler, etc.
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: bool = True

class MedicationLogEntry(BaseModel):
    event_id: str
    cadet_id_internal: str
    capid: str
    med_profile_id: str
    date: str  # YYYY-MM-DD
    time_due: str  # HH:MM
    time_taken: Optional[str] = None  # HH:MM
    result: str  # taken, refused, missed, not_available, held
    observer_initials: str
    cadet_initials: Optional[str] = None
    notes: Optional[str] = None

class IncidentLogEntry(BaseModel):
    event_id: str
    cadet_id_internal: str
    capid: str
    incident_date: str
    incident_time: str
    incident_type: str  # medication_error, allergic_reaction, injury, illness, heat_related, behavioral, other
    related_medication: Optional[str] = None
    description: str
    parent_contacted: bool = False
    parent_contact_time: Optional[str] = None
    command_notified: bool = False
    resolution_status: str = "open"  # open, monitoring, resolved, escalated

class CustodyLogEntry(BaseModel):
    event_id: str
    cadet_id_internal: str
    capid: str
    medication_name: str
    action_type: str  # check_in, check_out, transfer, disposal
    quantity: Optional[str] = None
    notes: Optional[str] = None

class HealthSummary(BaseModel):
    cadet_id_internal: str
    capid: str
    cadet_name: str
    squadron: Optional[str] = None
    flight: Optional[str] = None
    medication_on_file: bool = False
    rescue_med_flag: bool = False
    active_med_count: int = 0
    medications: List[Dict] = []
    last_med_pass_time: Optional[str] = None
    next_dose_due: Optional[str] = None
    open_incidents: int = 0
    incident_status: str = "clear"  # clear, monitoring, active_incident
    final_hs_status: str = "cleared"  # cleared, restricted, medical_hold

# ================= REFERENCE DATA =================

RESULT_TYPES = ["taken", "refused", "missed", "not_available", "held", "self_administered"]
INCIDENT_TYPES = ["medication_error", "allergic_reaction", "injury", "illness", "heat_related", "behavioral", "hydration", "other"]
RESOLUTION_STATUSES = ["open", "monitoring", "resolved", "escalated", "parent_notified"]
CUSTODY_ACTIONS = ["check_in", "check_out", "transfer", "disposal", "count_verified"]
ROUTES = ["oral", "topical", "inhaled", "injection", "sublingual", "ophthalmic", "otic", "nasal", "other"]
HS_STATUSES = ["cleared", "restricted_activity", "restricted_heat", "medical_hold", "sent_home"]

# ================= HELPER FUNCTIONS =================

def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix"""
    return f"{prefix}{uuid.uuid4().hex[:12]}"

def get_current_timestamp() -> str:
    """Get current UTC timestamp in ISO format"""
    return datetime.now(timezone.utc).isoformat()

def parse_due_times(due_times_str: str) -> List[str]:
    """Parse comma-separated due times into list"""
    if not due_times_str:
        return []
    return [t.strip() for t in due_times_str.split(",") if t.strip()]

def get_next_due_time(due_times: List[str], current_time: str = None) -> Optional[str]:
    """Calculate the next due time from a list of times"""
    if not due_times:
        return None
    
    if current_time is None:
        current_time = datetime.now(timezone.utc).strftime("%H%M")
    
    current_minutes = int(current_time[:2]) * 60 + int(current_time[2:]) if len(current_time) >= 4 else 0
    
    for time_str in sorted(due_times):
        if len(time_str) >= 4:
            time_minutes = int(time_str[:2]) * 60 + int(time_str[2:])
            if time_minutes > current_minutes:
                return time_str
    
    # If no time found today, return first time tomorrow
    return due_times[0] if due_times else None

# ================= GOOGLE SHEETS INTEGRATION =================

class HealthSheetsManager:
    """Manager for Health Services Google Sheets operations"""
    
    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.base_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        
        # Sheet GIDs (will be set after sheets are created)
        self.sheet_gids = {
            "cadet_master": "0",
            "medication_profile": "1",
            "medication_log": "2", 
            "incident_log": "3",
            "custody_log": "4",
            "audit_log": "5",
            "reference_lists": "6"
        }
    
    def get_sheet_data(self, sheet_name: str) -> pd.DataFrame:
        """Fetch data from a specific sheet"""
        gid = self.sheet_gids.get(sheet_name, "0")
        url = f"{self.base_url}/export?format=csv&gid={gid}"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return pd.read_csv(StringIO(response.text))
        except Exception as e:
            print(f"Error fetching sheet {sheet_name}: {e}")
            return pd.DataFrame()
    
    def append_row(self, sheet_name: str, row_data: Dict) -> bool:
        """
        Append a row to a sheet (requires Google Sheets API)
        For now, we'll store in MongoDB and sync periodically
        """
        # This would use Google Sheets API for actual implementation
        # For MVP, we'll use MongoDB as primary store
        return True


# ================= DATABASE OPERATIONS =================
# Using MongoDB for real-time operations, syncing to Google Sheets for reporting

async def get_health_db(db):
    """Get health services collections"""
    return {
        "cadet_master": db.hs_cadet_master,
        "medication_profiles": db.hs_medication_profiles,
        "medication_log": db.hs_medication_log,
        "incident_log": db.hs_incident_log,
        "custody_log": db.hs_custody_log,
        "audit_log": db.hs_audit_log,
        "settings": db.hs_settings
    }

async def log_audit(db, event_id: str, table_name: str, record_id: str, 
                    action_type: str, field_changed: str = None,
                    old_value: str = None, new_value: str = None, 
                    changed_by: str = None):
    """Log an audit entry"""
    audit_entry = {
        "audit_id": generate_id("AUD"),
        "event_id": event_id,
        "table_name": table_name,
        "record_id": record_id,
        "action_type": action_type,
        "field_changed": field_changed,
        "old_value": old_value,
        "new_value": new_value,
        "changed_by": changed_by,
        "changed_at": get_current_timestamp()
    }
    await db.hs_audit_log.insert_one(audit_entry)
    return audit_entry

async def get_event_settings(db) -> Dict:
    """Get current event settings"""
    settings = await db.hs_settings.find_one({"type": "event_config"})
    if not settings:
        # Default to current year encampment
        settings = {
            "type": "event_config",
            "event_id": "2026_TN_ENCAMPMENT",
            "event_year": 2026,
            "event_name": "Tennessee Wing Encampment 2026"
        }
        await db.hs_settings.insert_one(settings)
    return settings

# ================= API ENDPOINT FUNCTIONS =================
# These will be imported and used in server.py

async def get_cadet_health_summary(db, cadet_id: str, capid: str = None) -> Dict:
    """Get health summary for a specific cadet"""
    settings = await get_event_settings(db)
    event_id = settings["event_id"]
    
    # Find by cadet_id_internal or capid
    query = {"event_id": event_id}
    if cadet_id:
        query["cadet_id_internal"] = cadet_id
    elif capid:
        query["capid"] = capid
    
    # Get medication profiles
    med_profiles = await db.hs_medication_profiles.find({
        **query, "is_active": True
    }).to_list(100)
    
    # Get latest medication log entries
    med_logs = await db.hs_medication_log.find(query).sort("entered_at_timestamp", -1).limit(50).to_list(50)
    
    # Get open incidents
    incidents = await db.hs_incident_log.find({
        **query, "resolution_status": {"$in": ["open", "monitoring"]}
    }).to_list(50)
    
    # Get cadet master record
    cadet_record = await db.hs_cadet_master.find_one(query)
    
    # Calculate summary
    rescue_meds = [m for m in med_profiles if m.get("rescue_med_flag")]
    
    # Find next dose due
    next_due = None
    current_time = datetime.now(timezone.utc).strftime("%H%M")
    for med in med_profiles:
        due_times = parse_due_times(med.get("due_times", ""))
        med_next = get_next_due_time(due_times, current_time)
        if med_next and (next_due is None or med_next < next_due):
            next_due = med_next
    
    # Find last med pass
    last_pass = None
    if med_logs:
        last_pass = med_logs[0].get("time_taken") or med_logs[0].get("entered_at_timestamp")
    
    # Determine incident status
    incident_status = "clear"
    if incidents:
        escalated = any(i.get("resolution_status") == "escalated" for i in incidents)
        incident_status = "active_incident" if escalated else "monitoring"
    
    return {
        "cadet_id_internal": cadet_id,
        "capid": capid,
        "medication_on_file": len(med_profiles) > 0,
        "rescue_med_flag": len(rescue_meds) > 0,
        "active_med_count": len(med_profiles),
        "medications": [{
            "name": m.get("medication_name"),
            "dose": m.get("dose"),
            "schedule": m.get("schedule_text"),
            "due_times": m.get("due_times"),
            "rescue": m.get("rescue_med_flag", False),
            "refrigerated": m.get("refrigeration_required", False)
        } for m in med_profiles],
        "last_med_pass_time": last_pass,
        "next_dose_due": next_due,
        "open_incidents": len(incidents),
        "incident_status": incident_status,
        "final_hs_status": cadet_record.get("final_hs_status", "cleared") if cadet_record else "cleared"
    }

async def create_medication_profile(db, profile: Dict, user_id: str) -> Dict:
    """Create a new medication profile"""
    settings = await get_event_settings(db)
    
    profile_id = generate_id("MED")
    now = get_current_timestamp()
    
    profile_doc = {
        "med_profile_id": profile_id,
        "event_id": settings["event_id"],
        "cadet_id_internal": profile["cadet_id_internal"],
        "capid": profile["capid"],
        "medication_name": profile["medication_name"],
        "dose": profile["dose"],
        "route": profile.get("route", "oral"),
        "schedule_text": profile.get("schedule_text", ""),
        "due_times": profile.get("due_times", ""),
        "special_instructions": profile.get("special_instructions"),
        "refrigeration_required": profile.get("refrigeration_required", False),
        "rescue_med_flag": profile.get("rescue_med_flag", False),
        "start_date": profile.get("start_date"),
        "end_date": profile.get("end_date"),
        "entered_by": user_id,
        "entered_at": now,
        "is_active": True
    }
    
    await db.hs_medication_profiles.insert_one(profile_doc)
    
    # Update cadet master
    await update_cadet_master_summary(db, profile["cadet_id_internal"], profile["capid"])
    
    # Audit log
    await log_audit(db, settings["event_id"], "medication_profile", profile_id, 
                   "CREATE", changed_by=user_id)
    
    return profile_doc

async def log_medication_administration(db, entry: Dict, user_id: str) -> Dict:
    """Log a medication administration event (append-only)"""
    settings = await get_event_settings(db)
    
    log_id = generate_id("MLOG")
    now = get_current_timestamp()
    
    log_doc = {
        "med_log_id": log_id,
        "event_id": settings["event_id"],
        "event_year": settings["event_year"],
        "cadet_id_internal": entry["cadet_id_internal"],
        "capid": entry["capid"],
        "med_profile_id": entry["med_profile_id"],
        "date": entry["date"],
        "time_due": entry["time_due"],
        "time_taken": entry.get("time_taken"),
        "result": entry["result"],
        "observer_initials": entry["observer_initials"],
        "cadet_initials": entry.get("cadet_initials"),
        "notes": entry.get("notes"),
        "entered_by_user": user_id,
        "entered_at_timestamp": now
    }
    
    await db.hs_medication_log.insert_one(log_doc)
    
    # Audit log
    await log_audit(db, settings["event_id"], "medication_log", log_id, 
                   "CREATE", changed_by=user_id)
    
    return log_doc

async def log_incident(db, entry: Dict, user_id: str) -> Dict:
    """Log a health incident (append-only)"""
    settings = await get_event_settings(db)
    
    incident_id = generate_id("INC")
    now = get_current_timestamp()
    
    incident_doc = {
        "incident_id": incident_id,
        "event_id": settings["event_id"],
        "event_year": settings["event_year"],
        "cadet_id_internal": entry["cadet_id_internal"],
        "capid": entry["capid"],
        "incident_date": entry["incident_date"],
        "incident_time": entry["incident_time"],
        "incident_type": entry["incident_type"],
        "related_medication": entry.get("related_medication"),
        "description": entry["description"],
        "parent_contacted": entry.get("parent_contacted", False),
        "parent_contact_time": entry.get("parent_contact_time"),
        "command_notified": entry.get("command_notified", False),
        "resolution_status": entry.get("resolution_status", "open"),
        "resolved_at": None,
        "entered_by_user": user_id,
        "entered_at_timestamp": now
    }
    
    await db.hs_incident_log.insert_one(incident_doc)
    
    # Update cadet master
    await update_cadet_master_summary(db, entry["cadet_id_internal"], entry["capid"])
    
    # Audit log
    await log_audit(db, settings["event_id"], "incident_log", incident_id, 
                   "CREATE", changed_by=user_id)
    
    return incident_doc

async def log_custody_action(db, entry: Dict, user_id: str) -> Dict:
    """Log a medication custody action (append-only)"""
    settings = await get_event_settings(db)
    
    custody_id = generate_id("CUS")
    now = get_current_timestamp()
    
    custody_doc = {
        "custody_log_id": custody_id,
        "event_id": settings["event_id"],
        "cadet_id_internal": entry["cadet_id_internal"],
        "capid": entry["capid"],
        "medication_name": entry["medication_name"],
        "action_type": entry["action_type"],
        "quantity": entry.get("quantity"),
        "performed_by": user_id,
        "performed_at": now,
        "notes": entry.get("notes")
    }
    
    await db.hs_custody_log.insert_one(custody_doc)
    
    # Audit log
    await log_audit(db, settings["event_id"], "custody_log", custody_id, 
                   "CREATE", changed_by=user_id)
    
    return custody_doc

async def update_cadet_master_summary(db, cadet_id: str, capid: str):
    """Update cadet master record with current summary values"""
    settings = await get_event_settings(db)
    event_id = settings["event_id"]
    
    # Get current counts
    med_profiles = await db.hs_medication_profiles.find({
        "event_id": event_id, 
        "cadet_id_internal": cadet_id,
        "is_active": True
    }).to_list(100)
    
    rescue_meds = [m for m in med_profiles if m.get("rescue_med_flag")]
    
    open_incidents = await db.hs_incident_log.count_documents({
        "event_id": event_id,
        "cadet_id_internal": cadet_id,
        "resolution_status": {"$in": ["open", "monitoring"]}
    })
    
    now = get_current_timestamp()
    
    # Upsert cadet master record
    await db.hs_cadet_master.update_one(
        {"event_id": event_id, "cadet_id_internal": cadet_id},
        {
            "$set": {
                "capid": capid,
                "medication_flag": len(med_profiles) > 0,
                "rescue_med_flag": len(rescue_meds) > 0,
                "active_med_count": len(med_profiles),
                "incident_open_flag": open_incidents > 0,
                "record_updated_at": now
            },
            "$setOnInsert": {
                "event_id": event_id,
                "event_year": settings["event_year"],
                "event_name": settings["event_name"],
                "cadet_id_internal": cadet_id,
                "final_hs_status": "cleared",
                "record_created_at": now
            }
        },
        upsert=True
    )

async def update_incident_status(db, incident_id: str, new_status: str, user_id: str, resolution_notes: str = None) -> Dict:
    """Update incident resolution status"""
    settings = await get_event_settings(db)
    now = get_current_timestamp()
    
    # Get old value for audit
    old_incident = await db.hs_incident_log.find_one({"incident_id": incident_id})
    if not old_incident:
        raise ValueError("Incident not found")
    
    old_status = old_incident.get("resolution_status")
    
    update_fields = {
        "resolution_status": new_status,
        "last_updated_by": user_id,
        "last_updated_at": now
    }
    
    if new_status == "resolved":
        update_fields["resolved_at"] = now
    
    if resolution_notes:
        update_fields["resolution_notes"] = resolution_notes
    
    await db.hs_incident_log.update_one(
        {"incident_id": incident_id},
        {"$set": update_fields}
    )
    
    # Update cadet master
    await update_cadet_master_summary(db, old_incident["cadet_id_internal"], old_incident["capid"])
    
    # Audit log
    await log_audit(db, settings["event_id"], "incident_log", incident_id,
                   "UPDATE", "resolution_status", old_status, new_status, user_id)
    
    return {"incident_id": incident_id, "new_status": new_status}

async def update_cadet_hs_status(db, cadet_id: str, capid: str, new_status: str, user_id: str) -> Dict:
    """Update cadet's final health services status"""
    settings = await get_event_settings(db)
    
    # Get old value for audit
    old_record = await db.hs_cadet_master.find_one({
        "event_id": settings["event_id"],
        "cadet_id_internal": cadet_id
    })
    old_status = old_record.get("final_hs_status") if old_record else None
    
    now = get_current_timestamp()
    
    await db.hs_cadet_master.update_one(
        {"event_id": settings["event_id"], "cadet_id_internal": cadet_id},
        {
            "$set": {
                "final_hs_status": new_status,
                "record_updated_at": now
            },
            "$setOnInsert": {
                "event_id": settings["event_id"],
                "event_year": settings["event_year"],
                "event_name": settings["event_name"],
                "cadet_id_internal": cadet_id,
                "capid": capid,
                "record_created_at": now
            }
        },
        upsert=True
    )
    
    # Audit log
    await log_audit(db, settings["event_id"], "cadet_master", cadet_id,
                   "UPDATE", "final_hs_status", old_status, new_status, user_id)
    
    return {"cadet_id": cadet_id, "final_hs_status": new_status}

# ================= DASHBOARD QUERIES =================

async def get_meds_due_dashboard(db, time_window_minutes: int = 30) -> List[Dict]:
    """Get medications due within the next X minutes"""
    settings = await get_event_settings(db)
    event_id = settings["event_id"]
    
    # Get current time
    now = datetime.now(timezone.utc)
    current_time = now.strftime("%H%M")
    current_minutes = int(current_time[:2]) * 60 + int(current_time[2:])
    
    # Get all active medication profiles
    profiles = await db.hs_medication_profiles.find({
        "event_id": event_id,
        "is_active": True
    }).to_list(500)
    
    meds_due = []
    
    for profile in profiles:
        due_times = parse_due_times(profile.get("due_times", ""))
        
        for time_str in due_times:
            if len(time_str) >= 4:
                time_minutes = int(time_str[:2]) * 60 + int(time_str[2:])
                diff = time_minutes - current_minutes
                
                # Due within window (including slightly past)
                if -15 <= diff <= time_window_minutes:
                    # Check if already administered today
                    today = now.strftime("%Y-%m-%d")
                    existing_log = await db.hs_medication_log.find_one({
                        "event_id": event_id,
                        "med_profile_id": profile["med_profile_id"],
                        "date": today,
                        "time_due": time_str
                    })
                    
                    status = "due"
                    if existing_log:
                        status = existing_log.get("result", "completed")
                    elif diff < 0:
                        status = "overdue"
                    
                    if status in ["due", "overdue"]:
                        meds_due.append({
                            "cadet_id_internal": profile["cadet_id_internal"],
                            "capid": profile["capid"],
                            "medication_name": profile["medication_name"],
                            "dose": profile["dose"],
                            "time_due": time_str,
                            "status": status,
                            "minutes_until": diff,
                            "rescue_med": profile.get("rescue_med_flag", False),
                            "med_profile_id": profile["med_profile_id"]
                        })
    
    # Sort by time due
    meds_due.sort(key=lambda x: x["minutes_until"])
    
    return meds_due

async def get_overdue_meds(db) -> List[Dict]:
    """Get medications that are past due and not administered"""
    settings = await get_event_settings(db)
    event_id = settings["event_id"]
    
    now = datetime.now(timezone.utc)
    current_time = now.strftime("%H%M")
    current_minutes = int(current_time[:2]) * 60 + int(current_time[2:])
    today = now.strftime("%Y-%m-%d")
    
    profiles = await db.hs_medication_profiles.find({
        "event_id": event_id,
        "is_active": True
    }).to_list(500)
    
    overdue = []
    
    for profile in profiles:
        due_times = parse_due_times(profile.get("due_times", ""))
        
        for time_str in due_times:
            if len(time_str) >= 4:
                time_minutes = int(time_str[:2]) * 60 + int(time_str[2:])
                
                # Past due by more than 15 minutes
                if current_minutes - time_minutes > 15:
                    # Check if administered
                    existing_log = await db.hs_medication_log.find_one({
                        "event_id": event_id,
                        "med_profile_id": profile["med_profile_id"],
                        "date": today,
                        "time_due": time_str,
                        "result": {"$in": ["taken", "self_administered"]}
                    })
                    
                    if not existing_log:
                        overdue.append({
                            "cadet_id_internal": profile["cadet_id_internal"],
                            "capid": profile["capid"],
                            "medication_name": profile["medication_name"],
                            "dose": profile["dose"],
                            "time_due": time_str,
                            "minutes_overdue": current_minutes - time_minutes,
                            "rescue_med": profile.get("rescue_med_flag", False),
                            "med_profile_id": profile["med_profile_id"]
                        })
    
    # Sort by most overdue first
    overdue.sort(key=lambda x: -x["minutes_overdue"])
    
    return overdue

async def get_open_incidents(db) -> List[Dict]:
    """Get all open incidents"""
    settings = await get_event_settings(db)
    
    incidents = await db.hs_incident_log.find({
        "event_id": settings["event_id"],
        "resolution_status": {"$in": ["open", "monitoring", "escalated"]}
    }).sort("entered_at_timestamp", -1).to_list(200)
    
    # Remove MongoDB _id
    for inc in incidents:
        inc.pop("_id", None)
    
    return incidents

async def get_historical_report(db, event_year: int = None, squadron: str = None, 
                                cadet_id: str = None) -> Dict:
    """Get historical summary report with filters"""
    query = {}
    
    if event_year:
        query["event_year"] = event_year
    if squadron:
        query["squadron"] = squadron
    if cadet_id:
        query["cadet_id_internal"] = cadet_id
    
    # Get medication log stats
    med_log_pipeline = [
        {"$match": query} if query else {"$match": {}},
        {"$group": {
            "_id": "$result",
            "count": {"$sum": 1}
        }}
    ]
    med_stats = await db.hs_medication_log.aggregate(med_log_pipeline).to_list(20)
    
    # Get incident stats
    incident_pipeline = [
        {"$match": query} if query else {"$match": {}},
        {"$group": {
            "_id": "$incident_type",
            "count": {"$sum": 1}
        }}
    ]
    incident_stats = await db.hs_incident_log.aggregate(incident_pipeline).to_list(20)
    
    # Get cadet count
    cadet_query = {}
    if event_year:
        cadet_query["event_year"] = event_year
    if squadron:
        cadet_query["squadron"] = squadron
        
    cadet_count = await db.hs_cadet_master.count_documents(cadet_query or {})
    med_count = await db.hs_cadet_master.count_documents({**cadet_query, "medication_flag": True})
    
    return {
        "filters": {"event_year": event_year, "squadron": squadron, "cadet_id": cadet_id},
        "cadet_count": cadet_count,
        "cadets_with_medications": med_count,
        "medication_administration": {stat["_id"]: stat["count"] for stat in med_stats},
        "incidents_by_type": {stat["_id"]: stat["count"] for stat in incident_stats}
    }

# ================= REFERENCE DATA ENDPOINTS =================

def get_reference_lists() -> Dict:
    """Get all reference lists for dropdowns"""
    return {
        "result_types": RESULT_TYPES,
        "incident_types": INCIDENT_TYPES,
        "resolution_statuses": RESOLUTION_STATUSES,
        "custody_actions": CUSTODY_ACTIONS,
        "routes": ROUTES,
        "hs_statuses": HS_STATUSES,
        "squadrons": ["6th CTS", "21st CTS", "22nd CTS"],
        "flights": ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot"]
    }
