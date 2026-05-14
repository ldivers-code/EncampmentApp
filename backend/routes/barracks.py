"""Barracks & Bunk Assignment System routes"""
from fastapi import Depends, HTTPException
from datetime import datetime, timezone

from database import db, api_router, get_active_participant_count
from models import BunkAssignRequest
from permissions import get_current_user


BARRACKS_CONFIG = [
    {
        "barracks_id": "TR-142B",
        "name": "TR-142B",
        "type": "open_bay",
        "left_wall_bunks": 13,
        "right_wall_bunks": 12,
        "total_bunks": 25,
        "capacity": 50,
        "description": "Open Bay Barracks"
    },
    {
        "barracks_id": "TR-143A",
        "name": "TR-143A",
        "type": "open_bay",
        "left_wall_bunks": 13,
        "right_wall_bunks": 12,
        "total_bunks": 25,
        "capacity": 50,
        "description": "Open Bay Barracks"
    },
    {
        "barracks_id": "TR-143B",
        "name": "TR-143B",
        "type": "open_bay",
        "left_wall_bunks": 13,
        "right_wall_bunks": 12,
        "total_bunks": 25,
        "capacity": 50,
        "description": "Open Bay Barracks"
    },
    {
        "barracks_id": "TR-144A",
        "name": "TR-144A",
        "type": "open_bay",
        "left_wall_bunks": 13,
        "right_wall_bunks": 12,
        "total_bunks": 25,
        "capacity": 50,
        "description": "Open Bay Barracks"
    },
    {
        "barracks_id": "TR-144B",
        "name": "TR-144B",
        "type": "open_bay",
        "left_wall_bunks": 13,
        "right_wall_bunks": 12,
        "total_bunks": 25,
        "capacity": 50,
        "description": "Open Bay Barracks"
    },
]

FACILITY_BUILDINGS = [
    {"id": "TR-142B", "name": "TR-142B", "type": "barracks", "label": "Open Bay Barracks"},
    {"id": "TR-143A", "name": "TR-143A", "type": "barracks", "label": "Open Bay Barracks"},
    {"id": "TR-143B", "name": "TR-143B", "type": "barracks", "label": "Open Bay Barracks"},
    {"id": "TR-144A", "name": "TR-144A", "type": "barracks", "label": "Open Bay Barracks"},
    {"id": "TR-144B", "name": "TR-144B", "type": "barracks", "label": "Open Bay Barracks"},
    {"id": "TR-105", "name": "TR-105", "type": "senior_barracks", "label": "Senior Barracks (Individual Rooms)"},
    {"id": "TR-106", "name": "TR-106", "type": "senior_barracks", "label": "Senior Barracks (Individual Rooms)"},
    {"id": "TR-107", "name": "TR-107", "type": "senior_barracks", "label": "Senior Barracks (Individual Rooms)"},
    {"id": "TR-3", "name": "TR-3", "type": "support", "label": "Support Building"},
    {"id": "TR-100", "name": "TR-100", "type": "dfac", "label": "DFAC (Dining Facility)"},
    {"id": "TR-5", "name": "TR-5", "type": "classroom", "label": "Classroom"},
    {"id": "TR-7", "name": "TR-7", "type": "classroom", "label": "Classroom"},
    {"id": "TR-101", "name": "TR-101", "type": "facility", "label": "Bathroom / Laundry"},
    {"id": "TR-12", "name": "TR-12", "type": "classroom", "label": "Small Classroom"},
    {"id": "TR-4", "name": "TR-4", "type": "dfac_classroom", "label": "Catering DFAC / Classroom"},
]


@api_router.get("/barracks")
async def get_barracks(user: dict = Depends(get_current_user)):
    """Get all barracks with occupancy stats (list shape, backwards-compatible)."""
    result = []
    for b in BARRACKS_CONFIG:
        assigned = await db.bunk_assignments.count_documents({"barracks_id": b["barracks_id"]})
        result.append({
            **b,
            "assigned": assigned,
            "available": b["capacity"] - assigned
        })
    return result


@api_router.get("/barracks/summary")
async def get_barracks_summary(user: dict = Depends(get_current_user)):
    """Phase 6: canonical barracks summary that pairs bunk capacity with the
    canonical encampment headcount. `active_participants` comes from
    `get_active_participant_count()` — same number the dashboard, roster,
    check-in, and food-planning screens show."""
    rows = []
    for b in BARRACKS_CONFIG:
        assigned = await db.bunk_assignments.count_documents({"barracks_id": b["barracks_id"]})
        rows.append({**b, "assigned": assigned, "available": b["capacity"] - assigned})
    total_capacity = sum(b["capacity"] for b in BARRACKS_CONFIG)
    total_assigned = sum(b["assigned"] for b in rows)
    return {
        "barracks": rows,
        "active_participants": await get_active_participant_count(),
        "total_capacity": total_capacity,
        "total_assigned": total_assigned,
        "total_available": total_capacity - total_assigned,
        "unassigned_participants": (
            await get_active_participant_count() - total_assigned
        ),
    }


@api_router.get("/barracks/unassigned-participants")
async def get_unassigned_participants(user: dict = Depends(get_current_user)):
    """Get all participants not yet assigned to a bunk"""
    assigned_ids = await db.bunk_assignments.distinct("participant_id")
    
    participants = await db.participants.find(
        {"id": {"$nin": assigned_ids}, "is_removed": {"$ne": True}, "participant_type": {"$in": ["basic_student", "student", "advanced_student", "cadre", "exec_cadre"]}},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "capid": 1,
         "flight": 1, "squadron": 1, "participant_type": 1, "gender": 1}
    ).to_list(500)
    
    result = []
    for p in participants:
        result.append({
            "participant_id": p["id"],
            "name": f"{p.get('last_name', '')}, {p.get('first_name', '')}",
            "capid": p.get("capid", ""),
            "flight": p.get("flight", ""),
            "squadron": p.get("squadron", ""),
            "category": "student" if p.get("participant_type") in ["basic_student", "student", "advanced_student"] else "cadre",
            "gender": p.get("gender", "")
        })
    
    result.sort(key=lambda x: x["name"])
    return result


@api_router.get("/barracks/{barracks_id}")
async def get_barracks_detail(barracks_id: str, user: dict = Depends(get_current_user)):
    """Get barracks detail with all bunk assignments"""
    config = next((b for b in BARRACKS_CONFIG if b["barracks_id"] == barracks_id), None)
    if not config:
        raise HTTPException(status_code=404, detail="Barracks not found")
    
    assignments = {}
    async for a in db.bunk_assignments.find({"barracks_id": barracks_id}, {"_id": 0}):
        key = f"{a['bunk_number']}_{a['position']}"
        assignments[key] = a
    
    bunks = []
    for i in range(1, config["total_bunks"] + 1):
        wall = "left" if i <= config["left_wall_bunks"] else "right"
        wall_index = i if wall == "left" else i - config["left_wall_bunks"]
        
        top_key = f"{i}_top"
        bottom_key = f"{i}_bottom"
        top_assign = assignments.get(top_key, None)
        bottom_assign = assignments.get(bottom_key, None)
        
        bunks.append({
            "bunk_number": i,
            "wall": wall,
            "wall_index": wall_index,
            "top": {
                "occupied": top_assign is not None,
                "participant_id": top_assign.get("participant_id") if top_assign else None,
                "participant_name": top_assign.get("participant_name") if top_assign else None,
                "participant_type": top_assign.get("participant_type") if top_assign else None,
                "flight": top_assign.get("flight") if top_assign else None,
            },
            "bottom": {
                "occupied": bottom_assign is not None,
                "participant_id": bottom_assign.get("participant_id") if bottom_assign else None,
                "participant_name": bottom_assign.get("participant_name") if bottom_assign else None,
                "participant_type": bottom_assign.get("participant_type") if bottom_assign else None,
                "flight": bottom_assign.get("flight") if bottom_assign else None,
            }
        })
    
    assigned_count = await db.bunk_assignments.count_documents({"barracks_id": barracks_id})
    
    return {
        **config,
        "bunks": bunks,
        "assigned": assigned_count,
        "available": config["capacity"] - assigned_count
    }


@api_router.post("/barracks/{barracks_id}/assign")
async def assign_bunk(
    barracks_id: str,
    request: BunkAssignRequest,
    user: dict = Depends(get_current_user)
):
    """Assign a participant to a bunk"""
    config = next((b for b in BARRACKS_CONFIG if b["barracks_id"] == barracks_id), None)
    if not config:
        raise HTTPException(status_code=404, detail="Barracks not found")
    
    if request.position not in ("top", "bottom"):
        raise HTTPException(status_code=400, detail="Position must be 'top' or 'bottom'")
    
    if request.bunk_number < 1 or request.bunk_number > config["total_bunks"]:
        raise HTTPException(status_code=400, detail=f"Bunk number must be 1-{config['total_bunks']}")
    
    existing = await db.bunk_assignments.find_one({
        "barracks_id": barracks_id,
        "bunk_number": request.bunk_number,
        "position": request.position
    })
    if existing:
        raise HTTPException(status_code=409, detail="This bunk spot is already occupied")
    
    already_assigned = await db.bunk_assignments.find_one({
        "participant_id": request.participant_id
    })
    if already_assigned:
        raise HTTPException(
            status_code=409,
            detail=f"Participant already assigned to {already_assigned['barracks_id']} Bunk {already_assigned['bunk_number']} ({already_assigned['position']})"
        )
    
    participant = await db.participants.find_one({"id": request.participant_id}, {"_id": 0})
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "barracks_id": barracks_id,
        "bunk_number": request.bunk_number,
        "position": request.position,
        "participant_id": request.participant_id,
        "participant_name": f"{participant.get('last_name', '')}, {participant.get('first_name', '')}",
        "participant_type": participant.get("participant_type", ""),
        "flight": participant.get("flight", ""),
        "capid": participant.get("capid", ""),
        "assigned_by": user["id"],
        "assigned_by_name": user.get("name", user.get("email", "")),
        "assigned_at": now
    }
    await db.bunk_assignments.insert_one(doc)
    
    return {"status": "success", "barracks_id": barracks_id, "bunk_number": request.bunk_number, "position": request.position}


@api_router.delete("/barracks/{barracks_id}/bunk/{bunk_number}/{position}")
async def unassign_bunk(
    barracks_id: str,
    bunk_number: int,
    position: str,
    user: dict = Depends(get_current_user)
):
    """Remove a bunk assignment"""
    result = await db.bunk_assignments.delete_one({
        "barracks_id": barracks_id,
        "bunk_number": bunk_number,
        "position": position
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No assignment found")
    return {"status": "success", "removed": True}


@api_router.get("/facility/buildings")
async def get_facility_buildings(user: dict = Depends(get_current_user)):
    """Get all facility buildings"""
    return FACILITY_BUILDINGS
