"""Schedule Change Request routes"""
from fastapi import Depends, HTTPException, Body
from datetime import datetime, timezone
import uuid

from database import db, api_router
from permissions import get_current_user


SCHEDULE_EDITOR_ROLES = ['dcp', 'commander', 'executive_staff', 'staff', 'plans_programs']


@api_router.get("/schedule-changes")
async def list_schedule_changes(status: str = None, user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["status"] = status
    if user.get("role") not in SCHEDULE_EDITOR_ROLES:
        query["submitted_by"] = user["id"]
    docs = await db.schedule_change_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return docs


@api_router.post("/schedule-changes")
async def submit_schedule_change(data: dict = Body(...), user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "change_type": data.get("change_type", "modify"),
        "event_title": data.get("event_title", ""),
        "event_date": data.get("event_date", ""),
        "current_time": data.get("current_time", ""),
        "requested_time": data.get("requested_time", ""),
        "requested_location": data.get("requested_location", ""),
        "reason": data.get("reason", ""),
        "details": data.get("details", ""),
        "status": "pending",
        "submitted_by": user["id"],
        "submitted_by_name": user.get("name", user.get("email")),
        "submitted_by_role": user.get("role", ""),
        "reviewed_by": None,
        "reviewed_by_name": None,
        "review_notes": None,
        "created_at": now,
        "reviewed_at": None,
    }
    await db.schedule_change_requests.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.put("/schedule-changes/{req_id}/review")
async def review_schedule_change(req_id: str, data: dict = Body(...), user: dict = Depends(get_current_user)):
    if user.get("role") not in SCHEDULE_EDITOR_ROLES:
        raise HTTPException(status_code=403, detail="Schedule editor access required")
    new_status = data.get("status", "approved")
    if new_status not in ["approved", "denied"]:
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'denied'")
    now = datetime.now(timezone.utc).isoformat()
    r = await db.schedule_change_requests.update_one(
        {"id": req_id, "status": "pending"},
        {"$set": {
            "status": new_status,
            "reviewed_by": user["id"],
            "reviewed_by_name": user.get("name", user.get("email")),
            "review_notes": data.get("notes", ""),
            "reviewed_at": now,
        }}
    )
    if r.modified_count == 0:
        raise HTTPException(status_code=404, detail="Request not found or already reviewed")
    return {"message": f"Request {new_status}"}


@api_router.get("/schedule-changes/pending-count")
async def pending_schedule_changes_count(user: dict = Depends(get_current_user)):
    if user.get("role") not in SCHEDULE_EDITOR_ROLES:
        return {"count": 0}
    count = await db.schedule_change_requests.count_documents({"status": "pending"})
    return {"count": count}
