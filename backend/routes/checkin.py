"""Check-In System routes - multi-step in-processing"""
from fastapi import Depends, HTTPException
from datetime import datetime, timezone

from database import db, api_router
from models import UserRole, CheckInStepRequest
from permissions import get_current_user, get_user_permissions


CHECK_IN_STEPS = ["arrival", "paperwork", "bunk_assignment", "gear_issue"]
CHECK_IN_STEP_LABELS = {
    "arrival": "Arrival",
    "paperwork": "Paperwork",
    "bunk_assignment": "Bunk Assignment",
    "gear_issue": "Gear Issue"
}

CHECK_IN_ALLOWED_ROLES = [
    UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF,
    UserRole.PLANS_PROGRAMS, UserRole.LOGISTICS, UserRole.SUPPORT_LOGISTICS
]


def require_check_in_access():
    async def checker(user: dict = Depends(get_current_user)):
        perms = get_user_permissions(user)
        has_view = perms.get('check_in_view', False) if isinstance(perms, dict) else getattr(perms, 'check_in_view', False)
        if not has_view and user["role"] not in CHECK_IN_ALLOWED_ROLES:
            raise HTTPException(status_code=403, detail="No check-in access")
        return user
    return checker


def require_check_in_edit():
    async def checker(user: dict = Depends(get_current_user)):
        perms = get_user_permissions(user)
        has_edit = perms.get('check_in_edit', False) if isinstance(perms, dict) else getattr(perms, 'check_in_edit', False)
        if not has_edit and user["role"] not in CHECK_IN_ALLOWED_ROLES:
            raise HTTPException(status_code=403, detail="No check-in edit access")
        return user
    return checker


@api_router.get("/check-in/roster")
async def get_check_in_roster(
    category: str = None,
    user: dict = Depends(require_check_in_access())
):
    """Get all participants with their check-in status"""
    query = {"is_removed": {"$ne": True}}
    if category and category != "all":
        if category == "student":
            query["participant_type"] = {"$in": ["basic_student", "student"]}
        elif category == "staff":
            query["participant_type"] = "staff"
        elif category == "cadre":
            query["participant_type"] = {"$in": ["cadre", "exec_cadre"]}
    
    participants = await db.participants.find(
        query,
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "rank": 1,
         "capid": 1, "flight": 1, "squadron": 1, "participant_type": 1,
         "gender": 1, "age": 1, "wing": 1, "unit": 1}
    ).to_list(1000)
    
    check_ins = {}
    async for ci in db.check_ins.find({}, {"_id": 0}):
        check_ins[ci["participant_id"]] = ci
    
    roster = []
    for p in participants:
        ci = check_ins.get(p["id"], {})
        steps = ci.get("steps", {})
        
        completed_count = sum(1 for s in CHECK_IN_STEPS if steps.get(s, {}).get("completed", False))
        
        entry = {
            "participant_id": p["id"],
            "name": f"{p.get('last_name', '')}, {p.get('first_name', '')}",
            "rank": p.get("rank", ""),
            "capid": p.get("capid", ""),
            "flight": p.get("flight", ""),
            "squadron": p.get("squadron", ""),
            "category": "student" if p.get("participant_type") in ["basic_student", "student"] else p.get("participant_type", ""),
            "gender": p.get("gender", ""),
            "wing": p.get("wing", ""),
            "unit": p.get("unit", ""),
            "steps": {},
            "completed_steps": completed_count,
            "total_steps": len(CHECK_IN_STEPS),
            "fully_checked_in": completed_count == len(CHECK_IN_STEPS)
        }
        
        for step in CHECK_IN_STEPS:
            step_data = steps.get(step, {})
            entry["steps"][step] = {
                "completed": step_data.get("completed", False),
                "completed_at": step_data.get("completed_at"),
                "completed_by_name": step_data.get("completed_by_name"),
                "notes": step_data.get("notes", "")
            }
        
        roster.append(entry)
    
    roster.sort(key=lambda x: x["name"])
    return roster


@api_router.get("/check-in/summary")
async def get_check_in_summary(user: dict = Depends(require_check_in_access())):
    """Get check-in summary stats"""
    base_filter = {"is_removed": {"$ne": True}}
    total_participants = await db.participants.count_documents(base_filter)
    total_students = await db.participants.count_documents({**base_filter, "participant_type": {"$in": ["basic_student", "student"]}})
    total_staff = await db.participants.count_documents({**base_filter, "participant_type": "staff"})
    total_cadre = await db.participants.count_documents({**base_filter, "participant_type": {"$in": ["cadre", "exec_cadre"]}})
    
    check_ins = await db.check_ins.find({}, {"_id": 0}).to_list(1000)
    
    fully_checked = 0
    step_counts = {s: 0 for s in CHECK_IN_STEPS}
    
    p_types = {}
    async for p in db.participants.find({}, {"_id": 0, "id": 1, "participant_type": 1}):
        p_types[p["id"]] = p.get("participant_type", "")
    
    cat_checked = {"student": 0, "staff": 0, "cadre": 0}
    
    for ci in check_ins:
        steps = ci.get("steps", {})
        completed = sum(1 for s in CHECK_IN_STEPS if steps.get(s, {}).get("completed", False))
        if completed == len(CHECK_IN_STEPS):
            fully_checked += 1
            pt = p_types.get(ci["participant_id"], "")
            if pt in ["basic_student", "student"]:
                cat_checked["student"] += 1
            elif pt == "staff":
                cat_checked["staff"] += 1
            elif pt in ["cadre", "exec_cadre"]:
                cat_checked["cadre"] += 1
        for s in CHECK_IN_STEPS:
            if steps.get(s, {}).get("completed", False):
                step_counts[s] += 1
    
    return {
        "total_participants": total_participants,
        "total_students": total_students,
        "total_staff": total_staff,
        "total_cadre": total_cadre,
        "fully_checked_in": fully_checked,
        "not_checked_in": total_participants - fully_checked,
        "category_checked": cat_checked,
        "step_counts": step_counts,
        "step_labels": CHECK_IN_STEP_LABELS
    }


@api_router.post("/check-in/{participant_id}/step")
async def check_in_step(
    participant_id: str,
    request: CheckInStepRequest,
    user: dict = Depends(require_check_in_edit())
):
    """Check-in a participant for a specific step"""
    if request.step not in CHECK_IN_STEPS:
        raise HTTPException(status_code=400, detail=f"Invalid step. Must be one of: {CHECK_IN_STEPS}")
    
    participant = await db.participants.find_one({"id": participant_id}, {"_id": 0, "id": 1})
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    existing = await db.check_ins.find_one({"participant_id": participant_id})
    
    step_data = {
        "completed": True,
        "completed_at": now,
        "completed_by": user["id"],
        "completed_by_name": user.get("name", user.get("email", "")),
        "notes": request.notes
    }
    
    if existing:
        await db.check_ins.update_one(
            {"participant_id": participant_id},
            {"$set": {
                f"steps.{request.step}": step_data,
                "updated_at": now
            }}
        )
    else:
        doc = {
            "participant_id": participant_id,
            "steps": {request.step: step_data},
            "created_at": now,
            "updated_at": now
        }
        await db.check_ins.insert_one(doc)
    
    return {"status": "success", "step": request.step, "completed_at": now}


@api_router.delete("/check-in/{participant_id}/step/{step}")
async def undo_check_in_step(
    participant_id: str,
    step: str,
    user: dict = Depends(require_check_in_edit())
):
    """Undo a check-in step for a participant"""
    if step not in CHECK_IN_STEPS:
        raise HTTPException(status_code=400, detail=f"Invalid step. Must be one of: {CHECK_IN_STEPS}")
    
    now = datetime.now(timezone.utc).isoformat()
    
    result = await db.check_ins.update_one(
        {"participant_id": participant_id},
        {"$set": {
            f"steps.{step}": {"completed": False},
            "updated_at": now
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="No check-in record found")
    
    return {"status": "success", "step": step, "undone": True}


@api_router.post("/check-in/{participant_id}/check-all")
async def check_in_all_steps(
    participant_id: str,
    user: dict = Depends(require_check_in_edit())
):
    """Check-in all steps at once for a participant"""
    participant = await db.participants.find_one({"id": participant_id}, {"_id": 0, "id": 1})
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    now = datetime.now(timezone.utc).isoformat()
    steps = {}
    for step in CHECK_IN_STEPS:
        steps[step] = {
            "completed": True,
            "completed_at": now,
            "completed_by": user["id"],
            "completed_by_name": user.get("name", user.get("email", "")),
            "notes": ""
        }
    
    await db.check_ins.update_one(
        {"participant_id": participant_id},
        {"$set": {"steps": steps, "updated_at": now}},
        upsert=True
    )
    
    return {"status": "success", "all_checked": True}


@api_router.delete("/check-in/{participant_id}/undo-all")
async def undo_all_check_in(
    participant_id: str,
    user: dict = Depends(require_check_in_edit())
):
    """Undo all check-in steps for a participant"""
    result = await db.check_ins.delete_one({"participant_id": participant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No check-in record found")
    
    return {"status": "success", "all_undone": True}


# ================= CONTRABAND =================
# Connected to check-in flow (per-cadet), data stored in logistics collection

import uuid

@api_router.get("/check-in/{participant_id}/contraband")
async def get_participant_contraband(
    participant_id: str,
    user: dict = Depends(require_check_in_access())
):
    """Get contraband items for a participant"""
    items = await db.contraband.find(
        {"participant_id": participant_id}, {"_id": 0}
    ).sort("confiscated_at", -1).to_list(50)
    return items


@api_router.post("/check-in/{participant_id}/contraband")
async def add_contraband(
    participant_id: str,
    item: dict,
    user: dict = Depends(require_check_in_edit())
):
    """Log a contraband item confiscated during in-processing"""
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "participant_id": participant_id,
        "item_name": item.get("item_name", ""),
        "description": item.get("description", ""),
        "category": item.get("category", "other"),
        "quantity": item.get("quantity", 1),
        "storage_location": item.get("storage_location", ""),
        "confiscated_at": item.get("confiscated_at", now),
        "confiscated_by": user.get("name", user.get("id")),
        "confiscated_by_id": user["id"],
        "returned": False,
        "returned_at": None,
        "returned_to": None,
        "notes": item.get("notes", ""),
        "created_at": now,
    }
    await db.contraband.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.put("/check-in/contraband/{item_id}")
async def update_contraband(
    item_id: str,
    updates: dict,
    user: dict = Depends(require_check_in_edit())
):
    """Update a contraband record"""
    allowed = {"item_name", "description", "category", "quantity", "storage_location", "notes"}
    upd = {k: v for k, v in updates.items() if k in allowed}
    upd["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.contraband.update_one({"id": item_id}, {"$set": upd})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    updated = await db.contraband.find_one({"id": item_id}, {"_id": 0})
    return updated


@api_router.put("/check-in/contraband/{item_id}/return")
async def return_contraband(
    item_id: str,
    data: dict,
    user: dict = Depends(require_check_in_edit())
):
    """Mark contraband as returned"""
    now = datetime.now(timezone.utc).isoformat()
    upd = {
        "returned": True,
        "returned_at": now,
        "returned_to": data.get("returned_to", ""),
        "returned_by": user.get("name", user.get("id")),
        "returned_by_id": user["id"],
        "return_notes": data.get("notes", ""),
    }
    result = await db.contraband.update_one({"id": item_id}, {"$set": upd})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    updated = await db.contraband.find_one({"id": item_id}, {"_id": 0})
    return updated


@api_router.delete("/check-in/contraband/{item_id}")
async def delete_contraband(
    item_id: str,
    user: dict = Depends(require_check_in_edit())
):
    """Delete a contraband record"""
    result = await db.contraband.delete_one({"id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Deleted"}


@api_router.get("/logistics/contraband")
async def get_all_contraband(
    returned: bool = None,
    user: dict = Depends(require_check_in_access())
):
    """Get all contraband items across all participants (logistics view)"""
    query = {}
    if returned is not None:
        query["returned"] = returned
    items = await db.contraband.find(query, {"_id": 0}).sort("confiscated_at", -1).to_list(500)
    # Enrich with participant names
    for item in items:
        p = await db.participants.find_one(
            {"id": item["participant_id"]},
            {"_id": 0, "first_name": 1, "last_name": 1, "rank": 1, "flight": 1}
        )
        if p:
            item["participant_name"] = f"{p.get('rank','')} {p.get('last_name','')}, {p.get('first_name','')}"
            item["flight"] = p.get("flight")
    return items
