"""Health Services API and Medical Data Import"""
from fastapi import Depends, HTTPException, UploadFile, File
from typing import List, Optional
from datetime import datetime, timezone
from io import BytesIO
import uuid
import logging
import pandas as pd

from database import db, api_router
from models import UserRole
from permissions import get_current_user, require_role

# ================= HEALTH SERVICES API =================

from health_services import (
    get_cadet_health_summary, create_medication_profile, log_medication_administration,
    log_incident, log_custody_action, update_incident_status, update_cadet_hs_status,
    get_meds_due_dashboard, get_overdue_meds, get_open_incidents, get_historical_report,
    get_reference_lists, get_event_settings, generate_id, get_current_timestamp,
    RESULT_TYPES, INCIDENT_TYPES, RESOLUTION_STATUSES, CUSTODY_ACTIONS, ROUTES, HS_STATUSES
)

def require_health_view():
    """Dependency to check health view permission"""
    async def check_permission(user: dict = Depends(get_current_user)):
        perms = get_user_permissions(user)
        # Handle both dict and AccessPermissions object
        health_view = perms.get('health_view', False) if isinstance(perms, dict) else getattr(perms, 'health_view', False)
        health_full = perms.get('health_full', False) if isinstance(perms, dict) else getattr(perms, 'health_full', False)
        if not health_view and not health_full:
            raise HTTPException(status_code=403, detail="Health Services access required")
        return user
    return check_permission

def require_health_full():
    """Dependency to check full health services permission"""
    async def check_permission(user: dict = Depends(get_current_user)):
        perms = get_user_permissions(user)
        # Handle both dict and AccessPermissions object
        health_full = perms.get('health_full', False) if isinstance(perms, dict) else getattr(perms, 'health_full', False)
        if not health_full:
            raise HTTPException(status_code=403, detail="Full Health Services access required")
        return user
    return check_permission

# Health Services Settings
@api_router.get("/health/settings")
async def get_health_settings(user: dict = Depends(require_health_view())):
    """Get current event settings for health services"""
    settings = await get_event_settings(db)
    settings.pop("_id", None)
    return settings

@api_router.post("/health/settings")
async def update_health_settings(
    settings_data: dict,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.HEALTH_SERVICES]))
):
    """Update health services event settings"""
    await db.hs_settings.update_one(
        {"type": "event_config"},
        {"$set": {
            "event_id": settings_data.get("event_id"),
            "event_year": settings_data.get("event_year"),
            "event_name": settings_data.get("event_name")
        }},
        upsert=True
    )
    return {"message": "Settings updated"}

# Reference Data
@api_router.get("/health/reference-lists")
async def get_health_reference_lists(user: dict = Depends(require_health_view())):
    """Get reference lists for dropdowns"""
    return get_reference_lists()

# Cadet Health Summary
@api_router.get("/health/cadet/{cadet_id}/summary")
async def get_cadet_health_summary_endpoint(
    cadet_id: str,
    user: dict = Depends(require_health_view())
):
    """Get health summary for a specific cadet"""
    summary = await get_cadet_health_summary(db, cadet_id)
    
    # If user doesn't have full access, hide medication details
    perms = get_user_permissions(user)
    health_full = perms.get('health_full', False) if isinstance(perms, dict) else getattr(perms, 'health_full', False)
    if not health_full:
        # Staff can see basic info but not medication details
        summary["medications"] = []
        summary["medication_on_file"] = summary.get("active_med_count", 0) > 0
    
    return summary

@api_router.get("/health/cadet/by-capid/{capid}/summary")
async def get_cadet_health_summary_by_capid(
    capid: str,
    user: dict = Depends(require_health_view())
):
    """Get health summary for a cadet by CAPID"""
    summary = await get_cadet_health_summary(db, None, capid)
    
    perms = get_user_permissions(user)
    health_full = perms.get('health_full', False) if isinstance(perms, dict) else getattr(perms, 'health_full', False)
    if not health_full:
        summary["medications"] = []
        summary["medication_on_file"] = summary.get("active_med_count", 0) > 0
    
    return summary

# Medication Profiles
@api_router.get("/health/cadet/{cadet_id}/medications")
async def get_cadet_medications(
    cadet_id: str,
    user: dict = Depends(require_health_full())
):
    """Get all medication profiles for a cadet"""
    settings = await get_event_settings(db)
    profiles = await db.hs_medication_profiles.find({
        "event_id": settings["event_id"],
        "cadet_id_internal": cadet_id
    }).to_list(100)
    
    for p in profiles:
        p.pop("_id", None)
    
    return profiles

@api_router.post("/health/cadet/{cadet_id}/medications")
async def create_cadet_medication(
    cadet_id: str,
    medication: dict,
    user: dict = Depends(require_health_full())
):
    """Create a new medication profile for a cadet"""
    medication["cadet_id_internal"] = cadet_id
    result = await create_medication_profile(db, medication, user["id"])
    result.pop("_id", None)
    return result

@api_router.put("/health/medications/{med_profile_id}")
async def update_medication_profile(
    med_profile_id: str,
    updates: dict,
    user: dict = Depends(require_health_full())
):
    """Update a medication profile"""
    # Don't allow changing certain fields
    updates.pop("med_profile_id", None)
    updates.pop("event_id", None)
    updates.pop("cadet_id_internal", None)
    updates.pop("capid", None)
    updates.pop("entered_by", None)
    updates.pop("entered_at", None)
    
    result = await db.hs_medication_profiles.update_one(
        {"med_profile_id": med_profile_id},
        {"$set": updates}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Medication profile not found")
    
    return {"message": "Medication profile updated"}

@api_router.put("/health/medications/{med_profile_id}/deactivate")
async def deactivate_medication(
    med_profile_id: str,
    user: dict = Depends(require_health_full())
):
    """Deactivate a medication profile (soft delete)"""
    settings = await get_event_settings(db)
    
    result = await db.hs_medication_profiles.update_one(
        {"med_profile_id": med_profile_id},
        {"$set": {"is_active": False, "end_date": get_current_timestamp()[:10]}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Medication profile not found")
    
    # Log audit
    from health_services import log_audit
    await log_audit(db, settings["event_id"], "medication_profile", med_profile_id,
                   "DEACTIVATE", changed_by=user["id"])
    
    return {"message": "Medication deactivated"}

# Medication Administration Log
@api_router.get("/health/cadet/{cadet_id}/medication-log")
async def get_cadet_medication_log(
    cadet_id: str,
    limit: int = 100,
    user: dict = Depends(require_health_full())
):
    """Get medication administration history for a cadet"""
    settings = await get_event_settings(db)
    logs = await db.hs_medication_log.find({
        "event_id": settings["event_id"],
        "cadet_id_internal": cadet_id
    }).sort("entered_at_timestamp", -1).limit(limit).to_list(limit)
    
    for log in logs:
        log.pop("_id", None)
    
    return logs

@api_router.post("/health/cadet/{cadet_id}/medication-log")
async def log_medication_admin(
    cadet_id: str,
    entry: dict,
    user: dict = Depends(require_health_full())
):
    """Log a medication administration event"""
    entry["cadet_id_internal"] = cadet_id
    result = await log_medication_administration(db, entry, user["id"])
    result.pop("_id", None)
    return result

# Incident Log
@api_router.get("/health/cadet/{cadet_id}/incidents")
async def get_cadet_incidents(
    cadet_id: str,
    user: dict = Depends(require_health_view())
):
    """Get incident history for a cadet"""
    settings = await get_event_settings(db)
    incidents = await db.hs_incident_log.find({
        "event_id": settings["event_id"],
        "cadet_id_internal": cadet_id
    }).sort("entered_at_timestamp", -1).to_list(100)
    
    for inc in incidents:
        inc.pop("_id", None)
    
    return incidents

@api_router.post("/health/cadet/{cadet_id}/incidents")
async def log_cadet_incident(
    cadet_id: str,
    entry: dict,
    user: dict = Depends(require_health_full())
):
    """Log a health incident for a cadet"""
    entry["cadet_id_internal"] = cadet_id
    result = await log_incident(db, entry, user["id"])
    result.pop("_id", None)
    return result

@api_router.put("/health/incidents/{incident_id}/status")
async def update_incident_status_endpoint(
    incident_id: str,
    status_data: dict,
    user: dict = Depends(require_health_full())
):
    """Update incident resolution status"""
    new_status = status_data.get("status")
    notes = status_data.get("notes")
    
    if new_status not in RESOLUTION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    result = await update_incident_status(db, incident_id, new_status, user["id"], notes)
    return result

# Custody Log
@api_router.get("/health/cadet/{cadet_id}/custody-log")
async def get_cadet_custody_log(
    cadet_id: str,
    user: dict = Depends(require_health_full())
):
    """Get medication custody history for a cadet"""
    settings = await get_event_settings(db)
    logs = await db.hs_custody_log.find({
        "event_id": settings["event_id"],
        "cadet_id_internal": cadet_id
    }).sort("performed_at", -1).to_list(100)
    
    for log in logs:
        log.pop("_id", None)
    
    return logs

@api_router.post("/health/cadet/{cadet_id}/custody-log")
async def log_custody(
    cadet_id: str,
    entry: dict,
    user: dict = Depends(require_health_full())
):
    """Log a medication custody action"""
    entry["cadet_id_internal"] = cadet_id
    result = await log_custody_action(db, entry, user["id"])
    result.pop("_id", None)
    return result

# Cadet Health Status
@api_router.put("/health/cadet/{cadet_id}/status")
async def update_cadet_status(
    cadet_id: str,
    status_data: dict,
    user: dict = Depends(require_health_full())
):
    """Update cadet's final health services status"""
    new_status = status_data.get("status")
    capid = status_data.get("capid", "")
    
    if new_status not in HS_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    result = await update_cadet_hs_status(db, cadet_id, capid, new_status, user["id"])
    return result

# Dashboard Endpoints
@api_router.get("/health/dashboard/meds-due")
async def get_meds_due(
    window_minutes: int = 30,
    user: dict = Depends(require_health_full())
):
    """Get medications due within the specified time window"""
    # Enrich with cadet names
    meds = await get_meds_due_dashboard(db, window_minutes)
    
    for med in meds:
        participant = await db.participants.find_one(
            {"id": med["cadet_id_internal"]},
            {"_id": 0, "first_name": 1, "last_name": 1, "flight": 1, "squadron": 1}
        )
        if participant:
            med["cadet_name"] = f"{participant.get('last_name', '')}, {participant.get('first_name', '')}"
            med["flight"] = participant.get("flight")
            med["squadron"] = participant.get("squadron")
    
    return meds

@api_router.get("/health/dashboard/overdue")
async def get_overdue(user: dict = Depends(require_health_full())):
    """Get overdue medications"""
    meds = await get_overdue_meds(db)
    
    for med in meds:
        participant = await db.participants.find_one(
            {"id": med["cadet_id_internal"]},
            {"_id": 0, "first_name": 1, "last_name": 1, "flight": 1, "squadron": 1}
        )
        if participant:
            med["cadet_name"] = f"{participant.get('last_name', '')}, {participant.get('first_name', '')}"
            med["flight"] = participant.get("flight")
            med["squadron"] = participant.get("squadron")
    
    return meds

@api_router.get("/health/dashboard/open-incidents")
async def get_open_incidents_endpoint(user: dict = Depends(require_health_view())):
    """Get all open incidents"""
    incidents = await get_open_incidents(db)
    
    for inc in incidents:
        participant = await db.participants.find_one(
            {"id": inc["cadet_id_internal"]},
            {"_id": 0, "first_name": 1, "last_name": 1, "flight": 1, "squadron": 1}
        )
        if participant:
            inc["cadet_name"] = f"{participant.get('last_name', '')}, {participant.get('first_name', '')}"
            inc["flight"] = participant.get("flight")
            inc["squadron"] = participant.get("squadron")
    
    return incidents

@api_router.get("/health/dashboard/summary")
async def get_health_dashboard_summary(user: dict = Depends(require_health_view())):
    """Get overall health services dashboard summary"""
    settings = await get_event_settings(db)
    event_id = settings["event_id"]
    
    # Count cadets with health records
    total_cadets = await db.hs_cadet_master.count_documents({"event_id": event_id})
    with_meds = await db.hs_cadet_master.count_documents({"event_id": event_id, "medication_flag": True})
    rescue_meds = await db.hs_cadet_master.count_documents({"event_id": event_id, "rescue_med_flag": True})
    open_incidents = await db.hs_incident_log.count_documents({
        "event_id": event_id,
        "resolution_status": {"$in": ["open", "monitoring"]}
    })
    
    # Get meds due now
    meds_due = await get_meds_due_dashboard(db, 30)
    overdue = await get_overdue_meds(db)
    
    return {
        "event_id": event_id,
        "event_name": settings["event_name"],
        "total_cadets_tracked": total_cadets,
        "cadets_with_medications": with_meds,
        "cadets_with_rescue_meds": rescue_meds,
        "open_incidents": open_incidents,
        "meds_due_now": len(meds_due),
        "overdue_meds": len(overdue)
    }

@api_router.get("/health/reports/historical")
async def get_historical_report_endpoint(
    event_year: int = None,
    squadron: str = None,
    cadet_id: str = None,
    user: dict = Depends(require_health_full())
):
    """Get historical reporting data"""
    return await get_historical_report(db, event_year, squadron, cadet_id)

# Search Endpoints
@api_router.get("/health/search/cadets")
async def search_health_cadets(
    q: str = None,
    squadron: str = None,
    flight: str = None,
    has_medication: bool = None,
    has_incident: bool = None,
    user: dict = Depends(require_health_view())
):
    """Search cadets with health data"""
    settings = await get_event_settings(db)
    event_id = settings["event_id"]
    
    # Build query for participants
    participant_query = {}
    if squadron:
        participant_query["squadron"] = squadron
    if flight:
        participant_query["flight"] = flight
    
    participants = await db.participants.find(
        participant_query,
        {"_id": 0, "id": 1, "capid": 1, "first_name": 1, "last_name": 1, "flight": 1, "squadron": 1}
    ).to_list(500)
    
    # Filter by search term
    if q:
        q_lower = q.lower()
        participants = [p for p in participants if 
                       q_lower in f"{p.get('first_name', '')} {p.get('last_name', '')}".lower() or
                       q_lower in str(p.get('capid', ''))]
    
    # Enrich with health data
    results = []
    for p in participants:
        health_record = await db.hs_cadet_master.find_one({
            "event_id": event_id,
            "cadet_id_internal": p["id"]
        })
        
        has_med = health_record.get("medication_flag", False) if health_record else False
        has_inc = health_record.get("incident_open_flag", False) if health_record else False
        
        # Apply health filters
        if has_medication is not None and has_med != has_medication:
            continue
        if has_incident is not None and has_inc != has_incident:
            continue
        
        results.append({
            "cadet_id": p["id"],
            "capid": p.get("capid"),
            "name": f"{p.get('last_name', '')}, {p.get('first_name', '')}",
            "flight": p.get("flight"),
            "squadron": p.get("squadron"),
            "has_medication": has_med,
            "has_open_incident": has_inc,
            "hs_status": health_record.get("final_hs_status", "cleared") if health_record else "cleared"
        })
    
    return results

# Audit Log
@api_router.get("/health/audit-log")
async def get_audit_log(
    limit: int = 100,
    table_name: str = None,
    record_id: str = None,
    user: dict = Depends(require_health_full())
):
    """Get health services audit log"""
    settings = await get_event_settings(db)
    
    query = {"event_id": settings["event_id"]}
    if table_name:
        query["table_name"] = table_name
    if record_id:
        query["record_id"] = record_id
    
    logs = await db.hs_audit_log.find(query).sort("changed_at", -1).limit(limit).to_list(limit)
    
    for log in logs:
        log.pop("_id", None)
    
    return logs





# ================= HEALTH SERVICES - MEDICAL DATA IMPORT =================

OTC_MEDICATIONS = [
    "Acetaminophen", "Antifungal", "Antihistamine", "Bacitracin", "Calamine",
    "Claritin", "Hydrocortisone", "Ibuprofen", "Orajel", "Robitussin",
    "Sunscreen", "Tums", "Visine"
]

@api_router.post("/health/import/medical-data")
async def import_medical_data(
    file: UploadFile = File(...),
    user: dict = Depends(require_health_full())
):
    """Import medical data from CAP Excel reports (OTC Approvals or Allergies)"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are supported")
    
    contents = await file.read()
    try:
        df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse Excel file: {str(e)}")
    
    columns = [c.strip() for c in df.columns.tolist()]
    
    # Detect file type
    if "AllergyName" in columns or "AllergyType" in columns:
        return await _import_allergies(df, user)
    elif "Acetaminophen" in columns or "Ibuprofen" in columns:
        return await _import_otc_approvals(df, user)
    else:
        raise HTTPException(status_code=400, detail="Unrecognized file format. Expected OTC Medication Approvals or Allergies Report.")

async def _import_allergies(df: pd.DataFrame, user: dict) -> dict:
    """Import allergies from CAP AllergiesReport Excel"""
    from health_services import get_event_settings, generate_id, get_current_timestamp, log_audit
    
    settings = await get_event_settings(db)
    event_id = settings["event_id"]
    now = get_current_timestamp()
    user_id = user.get("id", "system")
    
    imported = 0
    skipped = 0
    matched_cadets = set()
    errors = []
    
    for _, row in df.iterrows():
        capid = str(row.get("CAPID", "")).strip()
        full_name = str(row.get("FullName", "")).strip()
        allergy_name = str(row.get("AllergyName", "")).strip()
        
        if not capid or not full_name or not allergy_name or allergy_name == "nan":
            skipped += 1
            continue
        
        # Match to roster participant by CAPID
        participant = await db.participants.find_one({"capid": capid}, {"_id": 0})
        cadet_name = full_name
        if participant:
            cadet_name = f"{participant.get('last_name', '')}, {participant.get('first_name', '')}"
        
        # Check for duplicate
        existing = await db.hs_allergies.find_one({
            "event_id": event_id,
            "capid": capid,
            "allergy_name": allergy_name
        })
        if existing:
            skipped += 1
            continue
        
        allergy_doc = {
            "allergy_id": generate_id("ALG"),
            "event_id": event_id,
            "capid": capid,
            "cadet_name": cadet_name,
            "allergy_name": allergy_name,
            "allergy_type": str(row.get("AllergyType", "")).strip() if pd.notna(row.get("AllergyType")) else "",
            "is_anaphylaxis": str(row.get("IsAnaphyaxis", "No")).strip().lower() == "yes",
            "has_epipen": str(row.get("HasEpipen", "No")).strip().lower() == "yes",
            "has_albuterol_inhaler": str(row.get("HasAlbuterolInhaler", "No")).strip().lower() == "yes",
            "typical_reactions": str(row.get("TypicalReactions", "")).strip() if pd.notna(row.get("TypicalReactions")) else "",
            "treatments": str(row.get("Treatments", "")).strip() if pd.notna(row.get("Treatments")) else "",
            "other_reactions": str(row.get("OtherReactions", "")).strip() if pd.notna(row.get("OtherReactions")) else "",
            "other_medications": str(row.get("OtherMedications", "")).strip() if pd.notna(row.get("OtherMedications")) else "",
            "contact_name": str(row.get("ContactName", "")).strip() if pd.notna(row.get("ContactName")) else "",
            "emergency_contact": str(row.get("EmergencyContact", "")).strip() if pd.notna(row.get("EmergencyContact")) else "",
            "commander_name": str(row.get("CommanderName", "")).strip() if pd.notna(row.get("CommanderName")) else "",
            "commander_contact": str(row.get("CommanderContact", "")).strip() if pd.notna(row.get("CommanderContact")) else "",
            "imported_by": user_id,
            "imported_at": now
        }
        
        await db.hs_allergies.insert_one(allergy_doc)
        imported += 1
        matched_cadets.add(capid)
    
    # Audit log
    await log_audit(db, event_id, "hs_allergies", "BULK_IMPORT", "CREATE",
                   "import_count", None, str(imported), user_id)
    
    return {
        "type": "allergies",
        "total_rows": len(df),
        "imported": imported,
        "skipped": skipped,
        "unique_cadets": len(matched_cadets),
        "errors": errors[:10]
    }

async def _import_otc_approvals(df: pd.DataFrame, user: dict) -> dict:
    """Import OTC medication approvals from CAP report"""
    from health_services import get_event_settings, generate_id, get_current_timestamp, log_audit
    
    settings = await get_event_settings(db)
    event_id = settings["event_id"]
    now = get_current_timestamp()
    user_id = user.get("id", "system")
    
    imported = 0
    skipped = 0
    updated = 0
    
    for _, row in df.iterrows():
        capid = str(row.get("CAPID", "")).strip()
        first_name = str(row.get("FirstName", "")).strip() if pd.notna(row.get("FirstName")) else ""
        last_name = str(row.get("LastName", "")).strip() if pd.notna(row.get("LastName")) else ""
        
        if not capid or capid == "nan":
            skipped += 1
            continue
        
        # Build OTC approvals dict
        otc_approvals = {}
        for med in OTC_MEDICATIONS:
            val = str(row.get(med, "Not Entered")).strip()
            otc_approvals[med.lower()] = val.lower() == "yes"
        
        # Check if any approvals exist
        has_any = any(otc_approvals.values())
        
        # Upsert
        existing = await db.hs_otc_approvals.find_one({
            "event_id": event_id,
            "capid": capid
        })
        
        doc = {
            "event_id": event_id,
            "capid": capid,
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": str(row.get("MiddleName", "")).strip() if pd.notna(row.get("MiddleName")) else "",
            "organization": str(row.get("Organization", "")).strip() if pd.notna(row.get("Organization")) else "",
            "email": str(row.get("CadetEmailString", "")).strip() if pd.notna(row.get("CadetEmailString")) else "",
            "approvals": otc_approvals,
            "has_any_approval": has_any,
            "imported_by": user_id,
            "imported_at": now
        }
        
        if existing:
            await db.hs_otc_approvals.update_one(
                {"event_id": event_id, "capid": capid},
                {"$set": doc}
            )
            updated += 1
        else:
            doc["otc_id"] = generate_id("OTC")
            await db.hs_otc_approvals.insert_one(doc)
            imported += 1
    
    await log_audit(db, event_id, "hs_otc_approvals", "BULK_IMPORT", "CREATE",
                   "import_count", None, str(imported + updated), user_id)
    
    return {
        "type": "otc_approvals",
        "total_rows": len(df),
        "imported": imported,
        "updated": updated,
        "skipped": skipped
    }


@api_router.get("/health/cadet/{cadet_id}/allergies")
async def get_cadet_allergies(
    cadet_id: str,
    user: dict = Depends(require_health_view())
):
    """Get allergies for a cadet (by CAPID)"""
    settings = await get_event_settings(db)
    allergies = await db.hs_allergies.find(
        {"event_id": settings["event_id"], "capid": cadet_id}
    ).to_list(100)
    for a in allergies:
        a.pop("_id", None)
    return allergies


@api_router.post("/health/cadet/{cadet_id}/allergies")
async def add_cadet_allergy(
    cadet_id: str,
    allergy: dict,
    user: dict = Depends(require_health_full())
):
    """Add an allergy record for a cadet"""
    settings = await get_event_settings(db)
    now = datetime.now(timezone.utc).isoformat()
    allergy_doc = {
        "id": str(uuid.uuid4()),
        "event_id": settings["event_id"],
        "capid": cadet_id,
        "allergy_name": allergy.get("allergy_name", ""),
        "allergy_type": allergy.get("allergy_type", "Other"),
        "is_anaphylaxis": allergy.get("is_anaphylaxis", False),
        "has_epipen": allergy.get("has_epipen", False),
        "has_albuterol_inhaler": allergy.get("has_albuterol_inhaler", False),
        "typical_reactions": allergy.get("typical_reactions", ""),
        "other_reactions": allergy.get("other_reactions", ""),
        "treatments": allergy.get("treatments", ""),
        "other_medications": allergy.get("other_medications", ""),
        "contact_name": allergy.get("contact_name", ""),
        "emergency_contact": allergy.get("emergency_contact", ""),
        "commander_name": allergy.get("commander_name", ""),
        "commander_contact": allergy.get("commander_contact", ""),
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now
    }
    await db.hs_allergies.insert_one(allergy_doc)
    allergy_doc.pop("_id", None)
    return allergy_doc


@api_router.put("/health/allergies/{allergy_id}")
async def update_allergy(
    allergy_id: str,
    allergy: dict,
    user: dict = Depends(require_health_full())
):
    """Update an allergy record"""
    now = datetime.now(timezone.utc).isoformat()
    update_fields = {k: v for k, v in allergy.items() if k not in ["id", "event_id", "capid", "_id"]}
    update_fields["updated_at"] = now
    update_fields["updated_by"] = user["id"]
    result = await db.hs_allergies.update_one({"id": allergy_id}, {"$set": update_fields})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Allergy record not found")
    updated = await db.hs_allergies.find_one({"id": allergy_id}, {"_id": 0})
    return updated


@api_router.delete("/health/allergies/{allergy_id}")
async def delete_allergy(
    allergy_id: str,
    user: dict = Depends(require_health_full())
):
    """Delete an allergy record"""
    result = await db.hs_allergies.delete_one({"id": allergy_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Allergy record not found")
    return {"message": "Allergy record deleted"}


@api_router.get("/health/cadet/{cadet_id}/otc-approvals")
async def get_cadet_otc_approvals(
    cadet_id: str,
    user: dict = Depends(require_health_view())
):
    """Get OTC medication approvals for a cadet (by CAPID)"""
    settings = await get_event_settings(db)
    approval = await db.hs_otc_approvals.find_one(
        {"event_id": settings["event_id"], "capid": cadet_id}
    )
    if approval:
        approval.pop("_id", None)
    return approval or {}


@api_router.put("/health/cadet/{cadet_id}/otc-approvals")
async def update_cadet_otc_approvals(
    cadet_id: str,
    otc_data: dict,
    user: dict = Depends(require_health_full())
):
    """Create or update OTC medication approvals for a cadet"""
    settings = await get_event_settings(db)
    now = datetime.now(timezone.utc).isoformat()
    
    medications = otc_data.get("medications", {})
    approved_list = [med for med, approved in medications.items() if approved]
    denied_list = [med for med, approved in medications.items() if not approved]
    
    update_doc = {
        "event_id": settings["event_id"],
        "capid": cadet_id,
        "medications": medications,
        "approved_list": approved_list,
        "denied_list": denied_list,
        "has_any_approval": len(approved_list) > 0,
        "organization": otc_data.get("organization", ""),
        "updated_at": now,
        "updated_by": user["id"]
    }
    
    result = await db.hs_otc_approvals.update_one(
        {"event_id": settings["event_id"], "capid": cadet_id},
        {"$set": update_doc, "$setOnInsert": {"created_at": now, "id": str(uuid.uuid4())}},
        upsert=True
    )
    
    updated = await db.hs_otc_approvals.find_one(
        {"event_id": settings["event_id"], "capid": cadet_id}, {"_id": 0}
    )
    return updated


@api_router.get("/health/import/summary")
async def get_import_summary(user: dict = Depends(require_health_view())):
    """Get summary of imported health data"""
    settings = await get_event_settings(db)
    event_id = settings["event_id"]
    
    allergy_count = await db.hs_allergies.count_documents({"event_id": event_id})
    allergy_cadets = len(await db.hs_allergies.distinct("capid", {"event_id": event_id}))
    otc_count = await db.hs_otc_approvals.count_documents({"event_id": event_id})
    otc_approved = await db.hs_otc_approvals.count_documents({"event_id": event_id, "has_any_approval": True})
    
    return {
        "allergy_records": allergy_count,
        "cadets_with_allergies": allergy_cadets,
        "otc_records": otc_count,
        "otc_with_approvals": otc_approved
    }





