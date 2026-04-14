"""Parent Portal routes - My Cadet dashboard"""
from fastapi import Depends, HTTPException
from datetime import datetime, timezone

from database import db, api_router
from models import UserRole
from permissions import get_current_user
from routes.notifications import create_notification


async def get_parent_and_cadet(user: dict):
    """Get parent user and their linked cadet participant"""
    if user.get("role") != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Parent access only")
    
    pid = user.get("linked_participant_id")
    if not pid:
        capid = user.get("capid", "")
        if capid:
            cadet = await db.participants.find_one(
                {"capid": capid, "is_removed": {"$ne": True}}, {"_id": 0}
            )
            if cadet:
                await db.users.update_one(
                    {"id": user["id"]},
                    {"$set": {"linked_participant_id": cadet["id"]}}
                )
                return cadet
        raise HTTPException(status_code=404, detail="No cadet linked to your account. Please contact administration.")
    
    cadet = await db.participants.find_one({"id": pid, "is_removed": {"$ne": True}}, {"_id": 0})
    if not cadet:
        raise HTTPException(status_code=404, detail="Linked cadet not found in the roster.")
    return cadet


@api_router.get("/parent/my-cadet")
async def get_my_cadet(user: dict = Depends(get_current_user)):
    """Get parent's linked cadet profile"""
    cadet = await get_parent_and_cadet(user)
    
    check_in = await db.check_ins.find_one({"participant_id": cadet["id"]}, {"_id": 0})
    bunk = await db.bunk_assignments.find_one({"participant_id": cadet["id"]}, {"_id": 0})
    
    allergies = await db.hs_allergies.find(
        {"participant_id": cadet["id"]}, {"_id": 0}
    ).to_list(50)
    
    dietary = []
    for a in allergies:
        if a.get("allergy_type") in ("food", "dietary"):
            dietary.append(a.get("allergen", ""))
    
    return {
        "id": cadet.get("id"),
        "first_name": cadet.get("first_name", ""),
        "last_name": cadet.get("last_name", ""),
        "capid": cadet.get("capid", ""),
        "rank": cadet.get("rank", ""),
        "flight": cadet.get("flight", ""),
        "squadron": cadet.get("squadron", ""),
        "participant_type": cadet.get("participant_type", ""),
        "gender": cadet.get("gender", ""),
        "age": cadet.get("age"),
        "unit": cadet.get("unit", ""),
        "wing": cadet.get("wing", ""),
        "check_in": check_in.get("steps", {}) if check_in else {},
        "barracks": {
            "barracks_id": bunk.get("barracks_id"),
            "bunk_number": bunk.get("bunk_number"),
            "position": bunk.get("position")
        } if bunk else None,
        "dietary_restrictions": dietary
    }


@api_router.get("/parent/my-cadet/schedule")
async def get_my_cadet_schedule(user: dict = Depends(get_current_user)):
    """Get schedule filtered by cadet's flight"""
    cadet = await get_parent_and_cadet(user)
    flight = (cadet.get("flight") or "").lower()
    
    query = {"is_draft": {"$ne": True}}
    events = await db.schedule.find(query, {"_id": 0}).sort("start_time", 1).to_list(500)
    
    filtered = []
    for e in events:
        target_flights = [f.lower() for f in (e.get("target_flights") or [])]
        if not target_flights or flight in target_flights or "all" in target_flights:
            filtered.append({
                "id": e.get("id"),
                "title": e.get("title", ""),
                "description": e.get("description", ""),
                "date": e.get("date", ""),
                "day_number": e.get("day_number"),
                "start_time": e.get("start_time", ""),
                "end_time": e.get("end_time", ""),
                "location": e.get("location", ""),
                "category": e.get("category", ""),
                "uniform": e.get("uniform", ""),
            })
    
    return {"flight": flight, "events": filtered}


@api_router.get("/parent/my-cadet/health-incidents")
async def get_my_cadet_health_incidents(user: dict = Depends(get_current_user)):
    """Get health incidents for parent's cadet"""
    cadet = await get_parent_and_cadet(user)
    
    incidents = await db.hs_incidents.find(
        {"participant_id": cadet["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    allergies = await db.hs_allergies.find(
        {"participant_id": cadet["id"]}, {"_id": 0}
    ).to_list(50)
    
    otc = await db.hs_otc_approvals.find(
        {"participant_id": cadet["id"]}, {"_id": 0}
    ).to_list(50)
    
    prescriptions = await db.hs_prescriptions.find(
        {"participant_id": cadet["id"]}, {"_id": 0}
    ).to_list(50)
    
    return {
        "incidents": incidents,
        "allergies": allergies,
        "otc_approvals": otc,
        "prescriptions": prescriptions
    }


@api_router.get("/parent/my-cadet/med-diary")
async def get_my_cadet_med_diary(user: dict = Depends(get_current_user)):
    """Get medication diary for parent's cadet — shows when meds were taken"""
    cadet = await get_parent_and_cadet(user)
    entries = await db.hs_med_diary.find(
        {"participant_id": cadet["id"]}, {"_id": 0}
    ).sort("administered_at", -1).to_list(200)
    return entries



@api_router.get("/parent/my-cadet/points")
async def get_my_cadet_points(user: dict = Depends(get_current_user)):
    """Get points and awards for parent's cadet"""
    cadet = await get_parent_and_cadet(user)
    
    entries = await db.score_entries.find(
        {"participant_id": cadet["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    
    merits = await db.merit_demerits.find(
        {"participant_id": cadet["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    
    awards = await db.honor_awards.find(
        {"participant_id": cadet["id"]}, {"_id": 0}
    ).to_list(50)
    
    total_points = sum(e.get("points", 0) for e in entries)
    total_merits = sum(1 for m in merits if m.get("type") == "merit")
    total_demerits = sum(1 for m in merits if m.get("type") == "demerit")
    
    return {
        "total_points": total_points,
        "total_merits": total_merits,
        "total_demerits": total_demerits,
        "entries": entries[:20],
        "merits": merits[:20],
        "awards": awards
    }


@api_router.get("/parent/my-cadet/meals")
async def get_my_cadet_meals(user: dict = Depends(get_current_user)):
    """Get meal schedule with dietary restrictions"""
    cadet = await get_parent_and_cadet(user)
    
    meal_plans = await db.meal_plans.find({}, {"_id": 0}).sort("date", 1).to_list(100)
    
    allergies = await db.hs_allergies.find(
        {"participant_id": cadet["id"]}, {"_id": 0}
    ).to_list(50)
    
    dietary_restrictions = [a.get("allergen", "") for a in allergies if a.get("allergy_type") in ("food", "dietary")]
    all_allergies = [a.get("allergen", "") for a in allergies]
    
    return {
        "meal_plans": meal_plans,
        "dietary_restrictions": dietary_restrictions,
        "all_allergies": all_allergies,
        "cadet_name": f"{cadet.get('first_name', '')} {cadet.get('last_name', '')}"
    }


async def notify_parent_health_incident(participant_id: str, incident_type: str, title: str, message: str):
    """Send in-app notification to parent when their cadet has a health incident"""
    parent_users = await db.users.find(
        {
            "role": UserRole.PARENT,
            "linked_participant_id": participant_id,
            "is_approved": True
        },
        {"_id": 0, "id": 1}
    ).to_list(10)
    
    for parent in parent_users:
        await create_notification(
            user_id=parent["id"],
            title=title,
            message=message,
            notif_type="health_alert"
        )
    
    parents_by_capid = []
    participant = await db.participants.find_one({"id": participant_id}, {"_id": 0, "capid": 1})
    if participant and participant.get("capid"):
        parents_by_capid = await db.users.find(
            {
                "role": UserRole.PARENT,
                "capid": participant["capid"],
                "linked_participant_id": {"$ne": participant_id},
                "is_approved": True
            },
            {"_id": 0, "id": 1}
        ).to_list(10)
        
        for parent in parents_by_capid:
            await create_notification(
                user_id=parent["id"],
                title=title,
                message=message,
                notif_type="health_alert"
            )
    
    return len(parent_users) + len(parents_by_capid)


# ================= ADMIN PORTAL CONFIG & PREVIEW =================

ADMIN_ROLES = [UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]

@api_router.get("/parent/portal-config")
async def get_portal_config(user: dict = Depends(get_current_user)):
    """Get the parent portal widget configuration."""
    config = await db.settings.find_one({"type": "parent_portal_config"}, {"_id": 0})
    if not config:
        config = {
            "type": "parent_portal_config",
            "widgets": {
                "overview": {"visible": True, "size": "full", "order": 0},
                "schedule": {"visible": True, "size": "full", "order": 1},
                "health": {"visible": True, "size": "half", "order": 2},
                "points": {"visible": True, "size": "half", "order": 3},
                "meals": {"visible": True, "size": "full", "order": 4},
                "otc_form": {"visible": True, "size": "full", "order": 5}
            }
        }
    return config

@api_router.put("/parent/portal-config")
async def update_portal_config(
    data: dict,
    user: dict = Depends(get_current_user)
):
    """Update the parent portal widget configuration. Admin only."""
    if user.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access only")
    
    widgets = data.get("widgets", {})
    await db.settings.update_one(
        {"type": "parent_portal_config"},
        {"$set": {
            "type": "parent_portal_config",
            "widgets": widgets,
            "updated_by": user["id"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    return {"message": "Portal configuration saved"}

@api_router.get("/parent/admin-preview/participants")
async def get_preview_participants(
    user: dict = Depends(get_current_user)
):
    """Get list of participants for admin preview selection."""
    if user.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access only")
    
    participants = await db.participants.find(
        {"is_removed": {"$ne": True}, "participant_type": {"$in": ["basic_student", "cadre"]}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "flight": 1, "squadron": 1, "capid": 1, "participant_type": 1}
    ).to_list(500)
    return sorted(participants, key=lambda p: f"{p.get('last_name', '')} {p.get('first_name', '')}")

@api_router.get("/parent/admin-preview/{participant_id}")
async def admin_preview_cadet(
    participant_id: str,
    user: dict = Depends(get_current_user)
):
    """Admin preview of a cadet's parent portal data."""
    if user.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access only")
    
    cadet = await db.participants.find_one(
        {"id": participant_id, "is_removed": {"$ne": True}}, {"_id": 0}
    )
    if not cadet:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    check_in = await db.check_ins.find_one({"participant_id": participant_id}, {"_id": 0})
    bunk = await db.bunk_assignments.find_one({"participant_id": participant_id}, {"_id": 0})
    allergies = await db.hs_allergies.find({"participant_id": participant_id}, {"_id": 0}).to_list(50)
    
    dietary = []
    for a in allergies:
        if a.get("allergen"):
            dietary.append(a["allergen"])
    
    return {
        **cadet,
        "check_in_status": check_in.get("status") if check_in else None,
        "bunk_assignment": bunk.get("bunk_number") if bunk else None,
        "building": bunk.get("building") if bunk else None,
        "dietary_restrictions": dietary,
        "allergies": allergies
    }

@api_router.get("/parent/admin-preview/{participant_id}/schedule")
async def admin_preview_schedule(participant_id: str, user: dict = Depends(get_current_user)):
    if user.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access only")
    cadet = await db.participants.find_one({"id": participant_id}, {"_id": 0, "flight": 1, "squadron": 1})
    if not cadet:
        return []
    flight = cadet.get("flight")
    squadron = cadet.get("squadron")
    query = {"$or": [{"target_groups": "all"}]}
    if flight:
        query["$or"].append({"target_groups": flight})
    if squadron:
        query["$or"].append({"target_groups": squadron})
    events = await db.schedule_events.find(query, {"_id": 0}).sort("date", 1).to_list(200)
    return events

@api_router.get("/parent/admin-preview/{participant_id}/health")
async def admin_preview_health(participant_id: str, user: dict = Depends(get_current_user)):
    if user.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access only")
    incidents = await db.hs_incidents.find({"participant_id": participant_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return incidents

@api_router.get("/parent/admin-preview/{participant_id}/points")
async def admin_preview_points(participant_id: str, user: dict = Depends(get_current_user)):
    if user.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access only")
    points = await db.points.find({"participant_id": participant_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return points

@api_router.get("/parent/admin-preview/{participant_id}/meals")
async def admin_preview_meals(participant_id: str, user: dict = Depends(get_current_user)):
    if user.get("role") not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access only")
    meals = await db.meal_plans.find({}, {"_id": 0}).sort("date", 1).to_list(200)
    return meals
