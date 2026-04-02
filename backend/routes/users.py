"""User Management, Approval, and Sync routes"""
from fastapi import Depends, HTTPException, BackgroundTasks
from typing import List
from datetime import datetime, timezone
import uuid
import os

from database import db, api_router
from models import (
    UserRole, UserUnitAssignment, AccessPermissions, UserResponse
)
from permissions import (
    get_default_permissions, get_current_user, require_role, send_approval_email
)


# ================= USER MANAGEMENT =================

@api_router.get("/users", response_model=List[UserResponse])
async def get_users(user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return [UserResponse(**u) for u in users]

@api_router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, role: str, user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))):
    valid_roles = [
        UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.LOGISTICS,
        UserRole.TRAINING_OFFICER, UserRole.FINANCE, UserRole.PLANS_PROGRAMS,
        UserRole.EXEC_CADRE, UserRole.STAFF, UserRole.CADRE, UserRole.HEALTH_SERVICES,
        UserRole.DINING_FACILITY, UserRole.SUPPORT_LOGISTICS, UserRole.SUPPORT_COMMS,
        UserRole.SUPPORT_PA, UserRole.SUPPORT_DINING, UserRole.SUPPORT_HEALTH,
        UserRole.SQUADRON_COMMANDER
    ]
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    result = await db.users.update_one(
        {"id": user_id}, 
        {"$set": {"role": role, "permissions": get_default_permissions(role)}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Role updated successfully"}

@api_router.put("/users/{user_id}/unit")
async def assign_user_unit(
    user_id: str, 
    assignment: UserUnitAssignment,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF, UserRole.PLANS_PROGRAMS]))
):
    target_user = await db.users.find_one({"id": user_id}, {"_id": 0, "role": 1})
    target_role = target_user.get("role", "") if target_user else ""
    is_support_role = target_role.startswith("support_") or target_role == "squadron_commander"
    
    valid_squadrons = [None, "", "staff", "support_cadre", "exec_cadre", "ops_cadre", "6th_cts", "21st_cts", "22nd_cts"]
    valid_flights = [None, "", "alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
    
    if assignment.squadron and assignment.squadron not in valid_squadrons:
        raise HTTPException(status_code=400, detail="Invalid squadron")
    if assignment.flight and assignment.flight not in valid_flights:
        raise HTTPException(status_code=400, detail="Invalid flight")
    
    no_flight_units = ["staff", "exec_cadre"]
    
    if assignment.squadron in no_flight_units and not is_support_role:
        assignment.flight = None
    
    flight_squadron_map = {
        "alpha": "6th_cts", "bravo": "6th_cts",
        "charlie": "21st_cts", "delta": "21st_cts",
        "echo": "22nd_cts", "foxtrot": "22nd_cts"
    }
    
    if assignment.flight and assignment.flight in flight_squadron_map:
        expected_squadron = flight_squadron_map[assignment.flight]
        if assignment.squadron in ("ops_cadre", "support_cadre") or is_support_role:
            pass
        elif assignment.squadron and assignment.squadron != expected_squadron:
            raise HTTPException(
                status_code=400, 
                detail=f"Flight {assignment.flight} belongs to {expected_squadron}"
            )
        else:
            assignment.squadron = expected_squadron
    
    result = await db.users.update_one(
        {"id": user_id}, 
        {"$set": {
            "squadron": assignment.squadron,
            "flight": assignment.flight,
            "support_section": assignment.support_section
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return UserResponse(**updated_user)

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))):
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}


# ================= USER APPROVAL ROUTES =================

@api_router.get("/users/pending")
async def get_pending_users(user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))):
    pending_users = await db.users.find(
        {"$or": [{"is_approved": False}, {"is_approved": None}]},
        {"_id": 0, "password_hash": 0}
    ).to_list(1000)
    return pending_users


@api_router.post("/users/{user_id}/approve")
async def approve_user(
    user_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
):
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "is_approved": True,
            "approved_by": user["id"],
            "approved_at": now
        }}
    )
    
    app_url = os.environ.get('APP_URL', 'https://tn-wing-roster.preview.emergentagent.com')
    background_tasks.add_task(
        send_approval_email,
        target_user.get('email'),
        target_user.get('name', 'Member'),
        app_url
    )
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {"message": "User approved successfully", "user": updated_user, "email_sent": True}


@api_router.put("/users/{user_id}/permissions")
async def update_user_permissions(
    user_id: str,
    permissions: AccessPermissions,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
):
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "permissions": permissions.model_dump(),
            "permissions_updated_at": now,
            "permissions_updated_by": user["id"]
        }}
    )
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {"message": "Permissions updated successfully", "user": updated_user}


@api_router.post("/users/{user_id}/reset-permissions")
async def reset_user_permissions(
    user_id: str,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
):
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    default_perms = get_default_permissions(target_user.get('role', UserRole.CADRE))
    now = datetime.now(timezone.utc).isoformat()
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "permissions": default_perms,
            "permissions_updated_at": now,
            "permissions_updated_by": user["id"]
        }}
    )
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {"message": "Permissions reset to role defaults", "user": updated_user}


@api_router.post("/users/{user_id}/link-participant")
async def link_user_to_participant(
    user_id: str,
    participant_id: str,
    auto_populate: bool = True,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
):
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    participant = await db.participants.find_one(
        {"$or": [{"id": participant_id}, {"capid": participant_id}]},
        {"_id": 0}
    )
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    now = datetime.now(timezone.utc).isoformat()
    update_fields = {
        "linked_participant_id": participant.get("id"),
        "capid": participant.get("capid"),
        "updated_at": now
    }
    
    if auto_populate:
        ptype = participant.get("participant_type", "")
        member_type = (participant.get("member_type") or "").upper()
        
        if member_type == "SENIOR" or ptype == "staff":
            update_fields["role"] = UserRole.STAFF
        elif ptype == "cadre":
            update_fields["role"] = UserRole.STAFF
        else:
            update_fields["role"] = UserRole.CADET
        
        profile_fields = [
            "rank", "unit", "wing", "region", "gender", "age", "shirt_size",
            "phone", "cell_phone", "email", "address", "city", "state", "zip_code",
            "emergency_contact", "emergency_phone",
            "cadet_parent_phone", "cadet_parent_email"
        ]
        for field in profile_fields:
            if participant.get(field):
                update_fields[field] = participant[field]
        
        if participant.get("first_name") and participant.get("last_name"):
            update_fields["name"] = f"{participant['first_name']} {participant['last_name']}"
    
    await db.users.update_one({"id": user_id}, {"$set": update_fields})
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {
        "message": "User linked to participant successfully",
        "user": updated_user,
        "participant": participant
    }


@api_router.get("/users/{user_id}/match-participants")
async def find_matching_participants(
    user_id: str,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
):
    target_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    matches = []
    
    if target_user.get("capid"):
        capid_match = await db.participants.find_one(
            {"capid": target_user["capid"]},
            {"_id": 0}
        )
        if capid_match:
            matches.append({"match_type": "capid", "participant": capid_match, "confidence": "high"})
    
    if target_user.get("email"):
        email_matches = await db.participants.find(
            {"email": {"$regex": target_user["email"], "$options": "i"}},
            {"_id": 0}
        ).to_list(5)
        for p in email_matches:
            if not any(m["participant"]["id"] == p["id"] for m in matches):
                matches.append({"match_type": "email", "participant": p, "confidence": "high"})
    
    if target_user.get("name"):
        name_parts = target_user["name"].split()
        if len(name_parts) >= 1:
            name_query = {
                "$or": [
                    {"first_name": {"$regex": name_parts[0], "$options": "i"}},
                    {"last_name": {"$regex": name_parts[-1], "$options": "i"}}
                ]
            }
            name_matches = await db.participants.find(name_query, {"_id": 0}).to_list(10)
            for p in name_matches:
                if not any(m["participant"]["id"] == p["id"] for m in matches):
                    matches.append({"match_type": "name", "participant": p, "confidence": "medium"})
    
    return {"user": target_user, "matches": matches[:10]}



@api_router.post("/sync/users-participants")
async def sync_users_to_participants(
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.PLANS_PROGRAMS]))
):
    all_users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(500)
    all_participants = await db.participants.find({"is_removed": {"$ne": True}}, {"_id": 0}).to_list(1000)
    
    p_by_capid = {p["capid"]: p for p in all_participants if p.get("capid")}
    p_ids = {p["id"] for p in all_participants}
    
    created_capids = set()
    
    linked = 0
    created = 0
    already_linked = 0
    skipped = 0
    now = datetime.now(timezone.utc).isoformat()
    
    for u in all_users:
        user_capid = (u.get("capid") or "").strip()
        user_id = u["id"]
        
        if u.get("linked_participant_id") and u["linked_participant_id"] in p_ids:
            already_linked += 1
            continue
        
        if user_capid and user_capid in p_by_capid:
            participant = p_by_capid[user_capid]
            await db.users.update_one(
                {"id": user_id},
                {"$set": {
                    "linked_participant_id": participant["id"],
                    "updated_at": now
                }}
            )
            linked += 1
            continue
        
        if not user_capid or not u.get("name"):
            skipped += 1
            continue
        
        if user_capid in created_capids:
            existing = await db.participants.find_one({"capid": user_capid, "is_removed": {"$ne": True}}, {"_id": 0, "id": 1})
            if existing:
                await db.users.update_one(
                    {"id": user_id},
                    {"$set": {"linked_participant_id": existing["id"], "updated_at": now}}
                )
                linked += 1
            else:
                skipped += 1
            continue
        
        role = u.get("role", "cadre")
        if role in ["dcp", "commander", "executive_staff", "staff", "finance", "plans_programs", "logistics", "training_officer", "health_services", "dining_facility"]:
            ptype = "staff"
            mtype = "SENIOR"
        elif role in ["squadron_commander", "exec_cadre"]:
            ptype = "cadre"
            mtype = "CADET"
        elif role.startswith("support_"):
            ptype = "cadre"
            mtype = "CADET"
        else:
            ptype = "cadre"
            mtype = "CADET"
        
        name_parts = (u.get("name") or "").split()
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[-1] if len(name_parts) > 1 else ""
        
        new_participant = {
            "id": str(uuid.uuid4()),
            "capid": user_capid,
            "first_name": first_name,
            "last_name": last_name,
            "name": u.get("name", ""),
            "email": u.get("email", ""),
            "rank": u.get("rank", ""),
            "unit": u.get("unit", ""),
            "wing": u.get("wing", ""),
            "gender": u.get("gender", ""),
            "age": u.get("age"),
            "phone": u.get("phone", ""),
            "cell_phone": u.get("cell_phone", ""),
            "participant_type": ptype,
            "member_type": mtype,
            "flight": u.get("flight", ""),
            "squadron": u.get("squadron", ""),
            "registration_status": "user_synced",
            "created_at": now,
            "updated_at": now,
            "is_removed": False
        }
        
        await db.participants.insert_one(new_participant)
        created_capids.add(user_capid)
        
        await db.users.update_one(
            {"id": user_id},
            {"$set": {
                "linked_participant_id": new_participant["id"],
                "updated_at": now
            }}
        )
        created += 1
    
    return {
        "message": f"Sync complete: {linked} linked, {created} created, {already_linked} already linked, {skipped} skipped",
        "linked": linked,
        "created": created,
        "already_linked": already_linked,
        "skipped": skipped,
        "total_users": len(all_users)
    }
