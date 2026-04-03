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
