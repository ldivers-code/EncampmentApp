"""Health Alerts routes"""
from fastapi import Depends, HTTPException, Body
from datetime import datetime, timezone

from database import db, api_router
from permissions import get_current_user


HEALTH_ALERT_ITEMS = [
    "epipen", "fainting", "heat_sensitive", "sensory_issues", "seizures",
    "diabetes", "asthma", "severe_allergies", "wheelchair_mobility",
    "hearing_impaired", "vision_impaired", "other"
]

HEALTH_ALERT_LABELS = {
    "epipen": "Has EpiPen",
    "fainting": "Prone to Fainting",
    "heat_sensitive": "Heat Sensitive",
    "sensory_issues": "Sensory Issues",
    "seizures": "Seizure Risk",
    "diabetes": "Diabetes",
    "asthma": "Asthma",
    "severe_allergies": "Severe Allergies",
    "wheelchair_mobility": "Wheelchair / Mobility",
    "hearing_impaired": "Hearing Impaired",
    "vision_impaired": "Vision Impaired",
    "other": "Other"
}

SHARE_LEVELS = ["flight_commander", "squadron_commander", "exec_cadre"]


@api_router.get("/health-alerts/{member_id}")
async def get_health_alerts(member_id: str, user: dict = Depends(get_current_user)):
    role = user.get("role", "")
    doc = await db.health_alerts.find_one({"member_id": member_id}, {"_id": 0})
    if not doc:
        return {"member_id": member_id, "alerts": [], "notes": ""}

    if role in ["dcp", "commander", "executive_staff", "health_services"]:
        return doc

    filtered = []
    for alert in doc.get("alerts", []):
        shared = alert.get("shared_with", [])
        if role in ["exec_cadre"] and "exec_cadre" in shared:
            filtered.append(alert)
        elif role in ["cadre", "training_officer"] and "flight_commander" in shared:
            filtered.append(alert)
        elif role in ["staff", "plans_programs", "logistics"] and "squadron_commander" in shared:
            filtered.append(alert)
    return {"member_id": member_id, "alerts": filtered, "notes": doc.get("shared_notes", "")}


@api_router.put("/health-alerts/{member_id}")
async def update_health_alerts(member_id: str, data: dict = Body(...), user: dict = Depends(get_current_user)):
    if user.get("role") not in ["dcp", "commander", "executive_staff", "health_services"]:
        raise HTTPException(status_code=403, detail="Health Services access required")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "member_id": member_id,
        "alerts": data.get("alerts", []),
        "notes": data.get("notes", ""),
        "shared_notes": data.get("shared_notes", ""),
        "updated_by": user.get("name", user.get("email")),
        "updated_at": now,
    }
    await db.health_alerts.update_one(
        {"member_id": member_id}, {"$set": doc}, upsert=True
    )
    return {"message": "Health alerts updated"}


@api_router.get("/members/{member_id}/profile")
async def get_member_profile(member_id: str, user: dict = Depends(get_current_user)):
    member = await db.users.find_one({"id": member_id}, {"_id": 0, "password_hash": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member
