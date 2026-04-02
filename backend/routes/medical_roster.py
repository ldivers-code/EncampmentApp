"""Medical Roster & Cadet Full Profile"""
from fastapi import Depends, HTTPException
from typing import List, Optional
from datetime import datetime, timezone

from database import db, api_router
from models import UserRole
from permissions import get_current_user, require_role, get_user_permissions, require_health_view

# ================= MEDICAL ROSTER & CADET FULL PROFILE =================

@api_router.get("/health/medical-roster")
async def get_medical_roster(user: dict = Depends(require_health_view())):
    """Get comprehensive medical roster - all cadets with any health data"""
    settings = await get_event_settings(db)
    event_id = settings["event_id"]
    
    perms = get_user_permissions(user)
    has_full = perms.get('health_full', False) if isinstance(perms, dict) else getattr(perms, 'health_full', False)

    # Gather all CAPIDs that have ANY health data
    allergy_capids = await db.hs_allergies.distinct("capid", {"event_id": event_id})
    otc_capids = await db.hs_otc_approvals.distinct("capid", {"event_id": event_id})
    med_capids = await db.hs_medication_profiles.distinct("capid", {"event_id": event_id, "is_active": True})
    
    # Get cadet master records for incident/status info
    master_records = {}
    async for rec in db.hs_cadet_master.find({"event_id": event_id}, {"_id": 0}):
        master_records[rec.get("cadet_id_internal", "")] = rec

    all_health_capids = set(allergy_capids) | set(otc_capids) | set(med_capids)
    
    # Also add participants with cadet_master records (incidents/medications tracked there)
    for rec in master_records.values():
        if rec.get("capid"):
            all_health_capids.add(rec["capid"])

    if not all_health_capids:
        return []

    # Match to participants
    participants = await db.participants.find(
        {"capid": {"$in": list(all_health_capids)}},
        {"_id": 0, "id": 1, "capid": 1, "first_name": 1, "last_name": 1, "rank": 1,
         "flight": 1, "squadron": 1, "gender": 1, "age": 1}
    ).to_list(500)
    
    # Build capid lookup
    capid_to_participant = {p.get("capid"): p for p in participants}
    
    # Aggregate allergy data per CAPID
    allergy_data = {}
    async for a in db.hs_allergies.find({"event_id": event_id}, {"_id": 0}):
        cid = a.get("capid")
        if cid not in allergy_data:
            allergy_data[cid] = []
        allergy_data[cid].append({
            "name": a.get("allergy_name", ""),
            "type": a.get("allergy_type", ""),
            "is_anaphylaxis": a.get("is_anaphylaxis", False),
            "has_epipen": a.get("has_epipen", False),
            "has_inhaler": a.get("has_albuterol_inhaler", False)
        })
    
    # Aggregate OTC data per CAPID
    otc_data = {}
    async for o in db.hs_otc_approvals.find({"event_id": event_id}, {"_id": 0}):
        cid = o.get("capid")
        approvals = o.get("approvals", {})
        approved_list = [med for med, val in approvals.items() if val]
        denied_list = [med for med, val in approvals.items() if not val]
        otc_data[cid] = {
            "has_any": o.get("has_any_approval", False),
            "approved": approved_list,
            "denied": denied_list,
            "total_approved": len(approved_list),
            "total_denied": len(denied_list)
        }
    
    # Aggregate medication profiles per CAPID
    med_data = {}
    async for m in db.hs_medication_profiles.find({"event_id": event_id, "is_active": True}, {"_id": 0}):
        cid = m.get("capid")
        if cid not in med_data:
            med_data[cid] = []
        med_data[cid].append({
            "name": m.get("medication_name", ""),
            "dose": m.get("dose", ""),
            "schedule": m.get("schedule_text", ""),
            "rescue": m.get("rescue_med_flag", False)
        })
    
    # Build roster
    roster = []
    for capid in all_health_capids:
        p = capid_to_participant.get(capid)
        if not p:
            continue
        
        allergies = allergy_data.get(capid, [])
        otc = otc_data.get(capid, {"has_any": False, "approved": [], "denied": [], "total_approved": 0, "total_denied": 0})
        meds = med_data.get(capid, [])
        master = master_records.get(p["id"], {})
        
        has_anaphylaxis = any(a.get("is_anaphylaxis") for a in allergies)
        has_epipen = any(a.get("has_epipen") for a in allergies)
        has_inhaler = any(a.get("has_inhaler") for a in allergies)
        has_rescue_med = any(m.get("rescue") for m in meds)
        
        entry = {
            "participant_id": p["id"],
            "capid": capid,
            "name": f"{p.get('last_name', '')}, {p.get('first_name', '')}",
            "rank": p.get("rank", ""),
            "flight": p.get("flight", ""),
            "squadron": p.get("squadron", ""),
            "gender": p.get("gender", ""),
            "age": p.get("age"),
            # Allergy flags
            "allergy_count": len(allergies),
            "has_allergies": len(allergies) > 0,
            "has_anaphylaxis": has_anaphylaxis,
            "has_epipen": has_epipen,
            "has_inhaler": has_inhaler,
            "allergy_names": [a["name"] for a in allergies],
            # OTC flags
            "has_otc_data": capid in otc_data,
            "otc_approved_count": otc.get("total_approved", 0),
            "otc_any_approved": otc.get("has_any", False),
            # Medication flags
            "medication_count": len(meds),
            "has_medications": len(meds) > 0,
            "has_rescue_med": has_rescue_med,
            # Incident/status flags
            "open_incidents": master.get("incident_open_count", 0),
            "hs_status": master.get("final_hs_status", "cleared"),
            # Critical flags for quick scanning
            "critical_flags": []
        }
        
        # Build critical flags list
        if has_anaphylaxis:
            entry["critical_flags"].append("ANAPHYLAXIS")
        if has_epipen:
            entry["critical_flags"].append("EPIPEN")
        if has_inhaler:
            entry["critical_flags"].append("INHALER")
        if has_rescue_med:
            entry["critical_flags"].append("RESCUE MED")
        if master.get("final_hs_status") == "medical_hold":
            entry["critical_flags"].append("MEDICAL HOLD")
        if master.get("incident_open_count", 0) > 0:
            entry["critical_flags"].append("OPEN INCIDENT")
        
        # Only include detailed allergy/med info for full access
        if has_full:
            entry["allergies_detail"] = allergies
            entry["otc_detail"] = otc
            entry["medications_detail"] = meds
        
        roster.append(entry)
    
    # Sort: critical flags first, then alphabetical
    roster.sort(key=lambda x: (-len(x["critical_flags"]), x["name"]))
    return roster


@api_router.get("/health/cadet/{cadet_id}/full-profile")
async def get_cadet_full_health_profile(
    cadet_id: str,
    user: dict = Depends(require_health_view())
):
    """Get comprehensive health profile for a single cadet by participant ID"""
    settings = await get_event_settings(db)
    event_id = settings["event_id"]
    
    perms = get_user_permissions(user)
    has_full = perms.get('health_full', False) if isinstance(perms, dict) else getattr(perms, 'health_full', False)
    
    # Get participant info
    participant = await db.participants.find_one({"id": cadet_id}, {"_id": 0})
    if not participant:
        raise HTTPException(status_code=404, detail="Cadet not found")
    
    capid = participant.get("capid", "")
    
    profile = {
        "participant_id": cadet_id,
        "capid": capid,
        "name": f"{participant.get('last_name', '')}, {participant.get('first_name', '')}",
        "rank": participant.get("rank", ""),
        "flight": participant.get("flight", ""),
        "squadron": participant.get("squadron", ""),
        "gender": participant.get("gender", ""),
        "age": participant.get("age"),
    }
    
    # Get allergies
    allergies = []
    async for a in db.hs_allergies.find({"event_id": event_id, "capid": capid}, {"_id": 0}):
        allergies.append({
            "allergy_id": a.get("allergy_id"),
            "allergy_name": a.get("allergy_name", ""),
            "allergy_type": a.get("allergy_type", ""),
            "is_anaphylaxis": a.get("is_anaphylaxis", False),
            "has_epipen": a.get("has_epipen", False),
            "has_albuterol_inhaler": a.get("has_albuterol_inhaler", False),
            "typical_reactions": a.get("typical_reactions", ""),
            "treatments": a.get("treatments", ""),
            "other_reactions": a.get("other_reactions", ""),
            "other_medications": a.get("other_medications", ""),
            "contact_name": a.get("contact_name", ""),
            "emergency_contact": a.get("emergency_contact", ""),
            "commander_name": a.get("commander_name", ""),
            "commander_contact": a.get("commander_contact", "")
        })
    profile["allergies"] = allergies
    profile["allergy_count"] = len(allergies)
    profile["has_anaphylaxis"] = any(a.get("is_anaphylaxis") for a in allergies)
    profile["has_epipen"] = any(a.get("has_epipen") for a in allergies)
    profile["has_inhaler"] = any(a.get("has_albuterol_inhaler") for a in allergies)
    
    # Get OTC approvals
    otc = await db.hs_otc_approvals.find_one({"event_id": event_id, "capid": capid}, {"_id": 0})
    if otc:
        approvals = otc.get("approvals", {})
        profile["otc_approvals"] = {
            "has_any": otc.get("has_any_approval", False),
            "medications": {med: approved for med, approved in approvals.items()},
            "approved_list": [med for med, val in approvals.items() if val],
            "denied_list": [med for med, val in approvals.items() if not val],
            "organization": otc.get("organization", ""),
            "email": otc.get("email", "")
        }
    else:
        profile["otc_approvals"] = None
    
    # Get active medication profiles (restricted to full access)
    medications = []
    if has_full:
        async for m in db.hs_medication_profiles.find(
            {"event_id": event_id, "capid": capid, "is_active": True}, {"_id": 0}
        ):
            medications.append({
                "med_profile_id": m.get("med_profile_id"),
                "medication_name": m.get("medication_name", ""),
                "dose": m.get("dose", ""),
                "route": m.get("route", ""),
                "schedule_text": m.get("schedule_text", ""),
                "due_times": m.get("due_times", ""),
                "special_instructions": m.get("special_instructions", ""),
                "refrigeration_required": m.get("refrigeration_required", False),
                "rescue_med_flag": m.get("rescue_med_flag", False),
                "start_date": m.get("start_date"),
                "end_date": m.get("end_date")
            })
    profile["medications"] = medications
    profile["medication_count"] = len(medications)
    profile["has_rescue_med"] = any(m.get("rescue_med_flag") for m in medications)
    
    # Get incidents
    incidents = []
    async for inc in db.hs_incident_log.find(
        {"event_id": event_id, "cadet_id_internal": cadet_id}, {"_id": 0}
    ).sort("incident_date", -1):
        incidents.append({
            "incident_id": inc.get("incident_id"),
            "incident_date": inc.get("incident_date", ""),
            "incident_time": inc.get("incident_time", ""),
            "incident_type": inc.get("incident_type", ""),
            "description": inc.get("description", ""),
            "resolution_status": inc.get("resolution_status", ""),
            "parent_contacted": inc.get("parent_contacted", False),
            "command_notified": inc.get("command_notified", False),
            "related_medication": inc.get("related_medication", "")
        })
    profile["incidents"] = incidents
    profile["open_incident_count"] = sum(1 for i in incidents if i.get("resolution_status") in ("open", "monitoring", "escalated"))
    
    # Get medication log (last 20 entries) - only for full access
    med_log = []
    if has_full:
        async for log in db.hs_medication_log.find(
            {"event_id": event_id, "cadet_id_internal": cadet_id}, {"_id": 0}
        ).sort("date", -1).limit(20):
            med_log.append({
                "date": log.get("date", ""),
                "time_due": log.get("time_due", ""),
                "time_taken": log.get("time_taken", ""),
                "result": log.get("result", ""),
                "medication_name": log.get("medication_name", ""),
                "observer_initials": log.get("observer_initials", ""),
                "notes": log.get("notes", "")
            })
    profile["medication_log"] = med_log
    
    # Get custody log - only for full access
    custody_log = []
    if has_full:
        async for c in db.hs_custody_log.find(
            {"event_id": event_id, "cadet_id_internal": cadet_id}, {"_id": 0}
        ).sort("created_at", -1):
            custody_log.append({
                "medication_name": c.get("medication_name", ""),
                "action_type": c.get("action_type", ""),
                "quantity": c.get("quantity", ""),
                "notes": c.get("notes", ""),
                "created_at": c.get("created_at", "")
            })
    profile["custody_log"] = custody_log
    
    # Get cadet master status
    master = await db.hs_cadet_master.find_one(
        {"event_id": event_id, "cadet_id_internal": cadet_id}, {"_id": 0}
    )
    profile["hs_status"] = master.get("final_hs_status", "cleared") if master else "cleared"
    
    # Health alerts/notes
    alerts = await db.health_alerts.find_one({"member_id": cadet_id}, {"_id": 0})
    profile["health_notes"] = alerts.get("notes", "") if alerts else ""
    profile["shared_notes"] = alerts.get("shared_notes", "") if alerts else ""
    
    return profile


# Schedule Changes extracted to routes/schedule_changes.py
# Health Alerts extracted to routes/health_alerts.py



