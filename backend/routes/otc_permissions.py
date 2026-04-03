"""OTC Medication Permission Form routes for parent authorization"""
from fastapi import Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, List
from datetime import datetime, timezone

from database import db, api_router
from models import UserRole
from permissions import get_current_user, require_role

OTC_MEDICATIONS = [
    "acetaminophen", "antifungal", "antihistamine", "bacitracin",
    "calamine", "claritin", "hydrocortisone", "ibuprofen",
    "orajel", "robitussin", "sunscreen", "tums", "visine"
]

MEDICATION_LABELS = {
    "acetaminophen": "Acetaminophen",
    "antifungal": "Antifungal",
    "antihistamine": "Antihistamine",
    "bacitracin": "Bacitracin",
    "calamine": "Calamine",
    "claritin": "Claritin",
    "hydrocortisone": "Hydrocortisone",
    "ibuprofen": "Ibuprofen",
    "orajel": "Orajel",
    "robitussin": "Robitussin",
    "sunscreen": "Sunscreen",
    "tums": "Tums",
    "visine": "Visine",
}


class OTCFormSubmission(BaseModel):
    parent_name: str
    parent_relationship: str
    parent_phone: str
    parent_email: str
    medications: Dict[str, bool]
    ack_otc_only: bool
    ack_staff_discretion: bool
    ack_prescription_separate: bool
    ack_accurate_info: bool
    notes_for_hso: Optional[str] = ""
    signature: str


@api_router.get("/parent/my-cadet/otc-permission")
async def get_parent_otc_form(user: dict = Depends(get_current_user)):
    """Parent gets their cadet's OTC permission form"""
    if user.get("role") != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Parent access only")

    capid = user.get("capid")
    if not capid:
        raise HTTPException(status_code=400, detail="No cadet linked to this parent account")

    participant = await db.participants.find_one(
        {"capid": str(capid), "is_removed": {"$ne": True}},
        {"_id": 0, "capid": 1, "first_name": 1, "last_name": 1, "rank": 1,
         "unit": 1, "squadron": 1, "participant_type": 1}
    )
    if not participant:
        raise HTTPException(status_code=404, detail="Cadet not found on roster")

    form = await db.otc_permissions.find_one(
        {"cadet_capid": str(capid)}, {"_id": 0}
    )

    cadet_role = "Student"
    ptype = (participant.get("participant_type") or "").lower()
    if "cadre" in ptype:
        cadet_role = "Cadre"

    return {
        "cadet": {
            "capid": participant.get("capid"),
            "name": f"{participant.get('rank', '')} {participant.get('last_name', '')}, {participant.get('first_name', '')}".strip(),
            "first_name": participant.get("first_name"),
            "last_name": participant.get("last_name"),
            "unit": participant.get("unit"),
            "squadron": participant.get("squadron"),
            "role": cadet_role,
        },
        "form": form,
        "medications_list": OTC_MEDICATIONS,
        "medication_labels": MEDICATION_LABELS,
    }


@api_router.post("/parent/my-cadet/otc-permission")
async def submit_otc_form(data: OTCFormSubmission, user: dict = Depends(get_current_user)):
    """Parent submits/updates OTC permission form for their cadet"""
    if user.get("role") != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Parent access only")

    capid = user.get("capid")
    if not capid:
        raise HTTPException(status_code=400, detail="No cadet linked to this parent account")

    participant = await db.participants.find_one(
        {"capid": str(capid), "is_removed": {"$ne": True}},
        {"_id": 0, "capid": 1, "first_name": 1, "last_name": 1, "rank": 1,
         "unit": 1, "squadron": 1, "participant_type": 1}
    )
    if not participant:
        raise HTTPException(status_code=404, detail="Cadet not found on roster")

    # Validate all medications answered
    for med in OTC_MEDICATIONS:
        if med not in data.medications:
            raise HTTPException(status_code=400, detail=f"Missing answer for {MEDICATION_LABELS.get(med, med)}")

    # Validate acknowledgments
    if not all([data.ack_otc_only, data.ack_staff_discretion,
                data.ack_prescription_separate, data.ack_accurate_info]):
        raise HTTPException(status_code=400, detail="All acknowledgments must be accepted")

    if not data.signature or len(data.signature.strip()) < 2:
        raise HTTPException(status_code=400, detail="Signature is required")

    now = datetime.now(timezone.utc).isoformat()

    cadet_role = "Student"
    ptype = (participant.get("participant_type") or "").lower()
    if "cadre" in ptype:
        cadet_role = "Cadre"

    form_doc = {
        "cadet_capid": str(capid),
        "cadet_name": f"{participant.get('rank', '')} {participant.get('last_name', '')}, {participant.get('first_name', '')}".strip(),
        "cadet_first_name": participant.get("first_name"),
        "cadet_last_name": participant.get("last_name"),
        "cadet_unit": participant.get("unit"),
        "cadet_squadron": participant.get("squadron"),
        "cadet_role": cadet_role,
        "parent_name": data.parent_name,
        "parent_relationship": data.parent_relationship,
        "parent_phone": data.parent_phone,
        "parent_email": data.parent_email,
        "parent_user_id": user.get("id"),
        "medications": data.medications,
        "ack_otc_only": data.ack_otc_only,
        "ack_staff_discretion": data.ack_staff_discretion,
        "ack_prescription_separate": data.ack_prescription_separate,
        "ack_accurate_info": data.ack_accurate_info,
        "notes_for_hso": data.notes_for_hso or "",
        "signature": data.signature,
        "signed_at": now,
        "status": "submitted",
        "submitted_at": now,
        "reviewed_by": None,
        "reviewed_at": None,
        "updated_at": now,
    }

    await db.otc_permissions.update_one(
        {"cadet_capid": str(capid)},
        {"$set": form_doc},
        upsert=True
    )

    # Update participant with OTC flag
    await db.participants.update_one(
        {"capid": str(capid)},
        {"$set": {"otc_permission_status": "submitted", "otc_permission_date": now}}
    )

    return {"message": "OTC Permission Form submitted successfully", "status": "submitted"}


# ============ STAFF ENDPOINTS ============

STAFF_ROLES = [
    UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.DCP,
    UserRole.HEALTH_SERVICES, UserRole.TRAINING_OFFICER,
    UserRole.SQUADRON_COMMANDER
]


@api_router.get("/otc-permissions/dashboard")
async def get_otc_dashboard(user: dict = Depends(get_current_user)):
    """Staff dashboard showing all OTC permission forms and missing status"""
    if user.get("role") not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")

    # Get all participants (students + cadre)
    participants = await db.participants.find(
        {"is_removed": {"$ne": True}},
        {"_id": 0, "capid": 1, "first_name": 1, "last_name": 1, "rank": 1,
         "unit": 1, "squadron": 1, "flight": 1, "participant_type": 1,
         "otc_permission_status": 1}
    ).to_list(2000)

    # Get all submitted forms
    forms = await db.otc_permissions.find({}, {"_id": 0}).to_list(2000)
    forms_by_capid = {f["cadet_capid"]: f for f in forms}

    dashboard_items = []
    total = 0
    submitted = 0
    reviewed = 0
    missing = 0

    for p in participants:
        capid = p.get("capid", "")
        ptype = (p.get("participant_type") or "").lower()

        # Only include students and cadre (skip senior_member staff without forms)
        if "student" not in ptype and "cadre" not in ptype:
            continue

        total += 1
        form = forms_by_capid.get(capid)

        status = "not_started"
        if form:
            status = form.get("status", "submitted")
            if status == "submitted":
                submitted += 1
            elif status == "reviewed":
                reviewed += 1
        else:
            missing += 1

        role_label = "Student" if "student" in ptype else "Cadre"

        item = {
            "capid": capid,
            "name": f"{p.get('rank', '')} {p.get('last_name', '')}, {p.get('first_name', '')}".strip(),
            "flight": p.get("flight", ""),
            "squadron": p.get("squadron", ""),
            "unit": p.get("unit", ""),
            "participant_type": role_label,
            "status": status,
            "medications": form.get("medications") if form else None,
            "parent_name": form.get("parent_name") if form else None,
            "submitted_at": form.get("submitted_at") if form else None,
            "reviewed_by": form.get("reviewed_by") if form else None,
            "reviewed_at": form.get("reviewed_at") if form else None,
            "notes_for_hso": form.get("notes_for_hso") if form else None,
        }
        dashboard_items.append(item)

    return {
        "total": total,
        "submitted": submitted,
        "reviewed": reviewed,
        "missing": missing,
        "items": dashboard_items,
        "medication_labels": MEDICATION_LABELS,
    }


@api_router.get("/otc-permissions/{capid}")
async def get_otc_form_detail(capid: str, user: dict = Depends(get_current_user)):
    """Staff view of a specific cadet's OTC permission form"""
    if user.get("role") not in STAFF_ROLES and user.get("role") != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Access denied")

    # Parents can only view their own cadet
    if user.get("role") == UserRole.PARENT:
        if str(user.get("capid")) != capid:
            raise HTTPException(status_code=403, detail="Can only view your own cadet's form")

    form = await db.otc_permissions.find_one({"cadet_capid": capid}, {"_id": 0})
    if not form:
        raise HTTPException(status_code=404, detail="OTC form not found for this cadet")

    return form


@api_router.post("/otc-permissions/{capid}/review")
async def review_otc_form(capid: str, user: dict = Depends(get_current_user)):
    """HSO/Commander marks an OTC form as reviewed"""
    if user.get("role") not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff access required")

    now = datetime.now(timezone.utc).isoformat()

    result = await db.otc_permissions.update_one(
        {"cadet_capid": capid, "status": "submitted"},
        {"$set": {
            "status": "reviewed",
            "reviewed_by": user.get("name", user.get("email")),
            "reviewed_at": now,
        }}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Form not found or already reviewed")

    await db.participants.update_one(
        {"capid": capid},
        {"$set": {"otc_permission_status": "reviewed"}}
    )

    return {"message": "Form marked as reviewed", "status": "reviewed"}
