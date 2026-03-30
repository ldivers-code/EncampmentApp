"""Training Officer routes - blister checks, counseling logs, cadre issues"""
from fastapi import Depends, HTTPException
from typing import Optional
from datetime import datetime, timezone
import uuid

from database import db, api_router
from models import UserRole
from permissions import get_current_user, require_role


TRAINING_ROLES = [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.TRAINING_OFFICER, UserRole.STAFF]

# --- Blister Checks ---

@api_router.get("/training/blister-checks")
async def get_blister_checks(
    date: Optional[str] = None,
    flight: Optional[str] = None,
    user: dict = Depends(require_role(TRAINING_ROLES))
):
    query = {}
    if date:
        query["date"] = date
    if flight:
        query["flight"] = flight.lower()
    if user["role"] == UserRole.TRAINING_OFFICER and user.get("squadron"):
        query["squadron"] = user["squadron"]
    
    checks = await db.training_blister_checks.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return checks

@api_router.post("/training/blister-checks")
async def create_blister_check(
    check: dict,
    user: dict = Depends(require_role(TRAINING_ROLES))
):
    doc = {
        "id": str(uuid.uuid4()),
        "cadet_name": check.get("cadet_name", ""),
        "capid": check.get("capid", ""),
        "flight": check.get("flight", "").lower(),
        "squadron": check.get("squadron", "").lower(),
        "date": check.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "severity": check.get("severity", "none"),
        "location": check.get("location", ""),
        "description": check.get("description", ""),
        "treatment_given": check.get("treatment_given", ""),
        "follow_up_needed": check.get("follow_up_needed", False),
        "status": check.get("status", "checked"),
        "created_by": user.get("id"),
        "created_by_name": user.get("name"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.training_blister_checks.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.put("/training/blister-checks/{check_id}")
async def update_blister_check(
    check_id: str,
    update: dict,
    user: dict = Depends(require_role(TRAINING_ROLES))
):
    allowed = {"severity", "location", "description", "treatment_given", "follow_up_needed", "status"}
    update_fields = {k: v for k, v in update.items() if k in allowed}
    update_fields["updated_by"] = user.get("id")
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.training_blister_checks.update_one(
        {"id": check_id}, {"$set": update_fields}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Check not found")
    return {"message": "Updated"}

# --- Counseling Logs ---

@api_router.get("/training/counseling-logs")
async def get_counseling_logs(
    date: Optional[str] = None,
    flight: Optional[str] = None,
    user: dict = Depends(require_role(TRAINING_ROLES))
):
    query = {}
    if date:
        query["date"] = date
    if flight:
        query["flight"] = flight.lower()
    if user["role"] == UserRole.TRAINING_OFFICER and user.get("squadron"):
        query["squadron"] = user["squadron"]
    
    logs = await db.training_counseling_logs.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return logs

@api_router.post("/training/counseling-logs")
async def create_counseling_log(
    log: dict,
    user: dict = Depends(require_role(TRAINING_ROLES))
):
    doc = {
        "id": str(uuid.uuid4()),
        "cadet_name": log.get("cadet_name", ""),
        "capid": log.get("capid", ""),
        "flight": log.get("flight", "").lower(),
        "squadron": log.get("squadron", "").lower(),
        "date": log.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "category": log.get("category", "general"),
        "reason": log.get("reason", ""),
        "outcome": log.get("outcome", ""),
        "follow_up_needed": log.get("follow_up_needed", False),
        "follow_up_date": log.get("follow_up_date"),
        "created_by": user.get("id"),
        "created_by_name": user.get("name"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.training_counseling_logs.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.put("/training/counseling-logs/{log_id}")
async def update_counseling_log(
    log_id: str,
    update: dict,
    user: dict = Depends(require_role(TRAINING_ROLES))
):
    allowed = {"category", "reason", "outcome", "follow_up_needed", "follow_up_date", "status"}
    update_fields = {k: v for k, v in update.items() if k in allowed}
    update_fields["updated_by"] = user.get("id")
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.training_counseling_logs.update_one(
        {"id": log_id}, {"$set": update_fields}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Log not found")
    return {"message": "Updated"}

# --- Cadre Issues ---

@api_router.get("/training/cadre-issues")
async def get_cadre_issues(
    date: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(require_role(TRAINING_ROLES))
):
    query = {}
    if date:
        query["date"] = date
    if status:
        query["status"] = status
    if user["role"] == UserRole.TRAINING_OFFICER and user.get("squadron"):
        query["squadron"] = user["squadron"]
    
    issues = await db.training_cadre_issues.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return issues

@api_router.post("/training/cadre-issues")
async def create_cadre_issue(
    issue: dict,
    user: dict = Depends(require_role(TRAINING_ROLES))
):
    doc = {
        "id": str(uuid.uuid4()),
        "cadre_name": issue.get("cadre_name", ""),
        "cadre_capid": issue.get("cadre_capid", ""),
        "flight": issue.get("flight", "").lower(),
        "squadron": issue.get("squadron", "").lower(),
        "date": issue.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "category": issue.get("category", "general"),
        "severity": issue.get("severity", "low"),
        "description": issue.get("description", ""),
        "action_taken": issue.get("action_taken", ""),
        "resolution_status": issue.get("resolution_status", "open"),
        "created_by": user.get("id"),
        "created_by_name": user.get("name"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.training_cadre_issues.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.put("/training/cadre-issues/{issue_id}")
async def update_cadre_issue(
    issue_id: str,
    update: dict,
    user: dict = Depends(require_role(TRAINING_ROLES))
):
    allowed = {"category", "severity", "description", "action_taken", "resolution_status"}
    update_fields = {k: v for k, v in update.items() if k in allowed}
    update_fields["updated_by"] = user.get("id")
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.training_cadre_issues.update_one(
        {"id": issue_id}, {"$set": update_fields}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {"message": "Updated"}

# --- Training Dashboard Summary ---

@api_router.get("/training/summary")
async def get_training_summary(
    user: dict = Depends(require_role(TRAINING_ROLES))
):
    query = {}
    if user["role"] == UserRole.TRAINING_OFFICER and user.get("squadron"):
        query["squadron"] = user["squadron"]
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_query = {**query, "date": today}
    
    blister_today = await db.training_blister_checks.count_documents(today_query)
    blisters_monitoring = await db.training_blister_checks.count_documents({**query, "status": "monitoring"})
    counseling_today = await db.training_counseling_logs.count_documents(today_query)
    counseling_followup = await db.training_counseling_logs.count_documents({**query, "follow_up_needed": True})
    issues_open = await db.training_cadre_issues.count_documents({**query, "resolution_status": {"$in": ["open", "in_progress"]}})
    issues_critical = await db.training_cadre_issues.count_documents({**query, "severity": "critical", "resolution_status": {"$ne": "resolved"}})
    
    return {
        "blister_checks_today": blister_today,
        "blisters_monitoring": blisters_monitoring,
        "counseling_today": counseling_today,
        "counseling_followup": counseling_followup,
        "cadre_issues_open": issues_open,
        "cadre_issues_critical": issues_critical
    }
