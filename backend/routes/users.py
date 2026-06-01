"""User Management, Approval, and Sync routes"""
from fastapi import Depends, HTTPException, BackgroundTasks
from typing import List
from datetime import datetime, timezone
import uuid
import os
import logging

from database import db, api_router
from models import (
    UserRole, UserUnitAssignment, AccessPermissions, UserResponse
)
from permissions import (
    get_default_permissions, get_current_user, require_role, send_approval_email
)
from role_groups import (
    FULL_ADMIN_ROLES, CADRE_LEAD_ROLES, cadre_lead_can_target, is_full_admin
)

logger = logging.getLogger(__name__)


async def auto_sync_org_chart(user_data: dict):
    """Sync the live org chart with a user's current assignment.

    Resolution: delegates to `org_chart_template.find_role_id_for_user` which
    maps a user's `cadre_position` + `role` + `flight` + `squadron` +
    `support_section` to the canonical position `role_id`.

    Side effects on `db.org_chart_roles`:
      1. If the user was previously assigned to some position, that
         position's `assigned_name` / `assigned_user_id` is cleared.
      2. The newly-resolved position gets `assigned_name` set to the
         user's full name and `assigned_user_id` to their UUID. For
         `single_occupant=False` positions, the user is added to a
         `assigned_user_ids` array instead of clobbering existing names.

    Safe to call from any code path — it never raises; failures are logged
    so a sync glitch can never block a user-management operation.
    """
    from org_chart_template import find_role_id_for_user, POSITION_BY_ID

    try:
        user_id = user_data.get("id")
        user_name = (user_data.get("name") or "").strip()
        if not user_id:
            return None

        new_role_id = find_role_id_for_user(user_data)
        now = datetime.now(timezone.utc).isoformat()

        # 1. Clear any previous assignments tied to this user_id (other than the new one).
        clear_query = {"assigned_user_id": user_id}
        if new_role_id:
            clear_query["role_id"] = {"$ne": new_role_id}
        await db.org_chart_roles.update_many(
            clear_query,
            {"$set": {"assigned_user_id": None, "assigned_name": "", "updated_at": now}},
        )
        await db.org_chart_roles.update_many(
            {"assigned_user_ids": user_id, **({"role_id": {"$ne": new_role_id}} if new_role_id else {})},
            {"$pull": {"assigned_user_ids": user_id}, "$set": {"updated_at": now}},
        )

        if not new_role_id:
            logger.info(
                "auto_sync_org_chart: cleared previous assignments for user=%s; "
                "no canonical position resolved for role=%s flight=%s squadron=%s "
                "support_section=%s cadre_position=%s",
                user_id, user_data.get("role"), user_data.get("flight"),
                user_data.get("squadron"), user_data.get("support_section"),
                user_data.get("cadre_position"),
            )
            return None

        position_meta = POSITION_BY_ID.get(new_role_id) or {}
        single_occupant = position_meta.get("single_occupant", True)
        existing = await db.org_chart_roles.find_one({"role_id": new_role_id}, {"_id": 0})
        if not existing:
            logger.warning("auto_sync_org_chart: position %s not in DB", new_role_id)
            return None

        if single_occupant:
            await db.org_chart_roles.update_one(
                {"role_id": new_role_id},
                {"$set": {
                    "assigned_name": user_name,
                    "assigned_user_id": user_id,
                    "assigned_participant_id": user_data.get("linked_participant_id"),
                    "updated_at": now,
                }},
            )
        else:
            # Multi-occupant: append name + id without clobbering peers.
            current_names = (existing.get("assigned_name") or "").strip()
            names_list = [n.strip() for n in current_names.split(";") if n.strip() and n.strip() != user_name]
            if user_name:
                names_list.append(user_name)
            await db.org_chart_roles.update_one(
                {"role_id": new_role_id},
                {
                    "$set": {
                        "assigned_name": "; ".join(names_list),
                        "updated_at": now,
                    },
                    "$addToSet": {"assigned_user_ids": user_id},
                },
            )

        logger.info(
            "auto_sync_org_chart: user=%s (%s) -> %s",
            user_id, user_name or user_data.get("email"), new_role_id,
        )
        return new_role_id
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("auto_sync_org_chart failed: %s", exc)
        return None


# ================= USER MANAGEMENT =================

@api_router.get("/users", response_model=List[UserResponse])
async def get_users(user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))):
    # Phase 3: listing ALL users (incl. senior-staff & admin accounts) is a
    # FULL ADMIN capability. Cadre-leads (EXEC_CADRE) MUST NOT receive a
    # senior-staff cross-cutting view. They can supervise their own cadre via
    # /flights/* and /reports/* endpoints instead.
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return [UserResponse(**u) for u in users]

# ─────────────────────────────────────────────────────────────────────────
# Role-management constants
# ─────────────────────────────────────────────────────────────────────────

# Roles an Exec Cadre user is allowed to manage. Cadre-only scope.
EXEC_CADRE_MANAGEABLE_ROLES: set[str] = {
    UserRole.CADRE,
    UserRole.EXEC_CADRE,
    UserRole.SQUADRON_COMMANDER,
    UserRole.SUPPORT_LOGISTICS,
    UserRole.SUPPORT_COMMS,
    UserRole.SUPPORT_PA,
    UserRole.SUPPORT_DINING,
    UserRole.SUPPORT_HEALTH,
}

# Roles a non-full-admin caller must NEVER be able to grant. These are
# system-level capabilities — only DCP / Commander / Executive Staff may
# set them.
PROTECTED_ROLES: set[str] = {
    UserRole.DCP,
    UserRole.COMMANDER,
    UserRole.EXECUTIVE_STAFF,
    UserRole.SUPERINTENDENT,
    UserRole.CHIEF_TRAINING_OFFICER,
}

FULL_ADMIN_ROLES_LOCAL: set[str] = {
    UserRole.DCP,
    UserRole.COMMANDER,
    UserRole.EXECUTIVE_STAFF,
}


async def _audit_role_change(actor: dict, target_user: dict,
                             previous_role: str | None, new_role: str) -> None:
    """Record every user-role change in the `role_audit_log` collection.
    Fields per acceptance test:
      * who made the change
      * whose role was changed
      * previous role
      * new role
      * timestamp
    """
    await db.role_audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "actor_user_id": actor.get("id"),
        "actor_email": actor.get("email"),
        "actor_role": actor.get("role"),
        "target_user_id": target_user.get("id"),
        "target_email": target_user.get("email"),
        "previous_role": previous_role,
        "new_role": new_role,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@api_router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: str,
    user: dict = Depends(require_role([
        UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF,
        UserRole.EXEC_CADRE,
    ])),
):
    """Update a user's role.

    Permission rules:
      * Full admin (DCP / Commander / Executive Staff) may set any valid role.
      * Exec Cadre may ONLY set roles within `EXEC_CADRE_MANAGEABLE_ROLES`
        (cadre + support cadre + squadron_commander + exec_cadre).
      * Exec Cadre may ONLY edit users who are themselves currently in a
        cadre-managed role — they cannot promote a student/parent or
        re-role a senior staff member.
      * Nobody but full admins can grant `PROTECTED_ROLES` (commander, dcp,
        executive_staff, superintendent, chief_training_officer).
      * Every change is recorded in `role_audit_log`.
    """
    valid_roles = [
        UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.LOGISTICS,
        UserRole.TRAINING_OFFICER, UserRole.FINANCE, UserRole.PLANS_PROGRAMS,
        UserRole.EXEC_CADRE, UserRole.STAFF, UserRole.CADRE, UserRole.STUDENT,
        UserRole.HEALTH_SERVICES,
        UserRole.DINING_FACILITY, UserRole.SUPPORT_LOGISTICS, UserRole.SUPPORT_COMMS,
        UserRole.SUPPORT_PA, UserRole.SUPPORT_DINING, UserRole.SUPPORT_HEALTH,
        UserRole.SQUADRON_COMMANDER, UserRole.PARENT,
        UserRole.SUPERINTENDENT, UserRole.CHIEF_TRAINING_OFFICER,
        UserRole.PUBLIC_AFFAIRS,
    ]
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")

    target = await db.users.find_one(
        {"id": user_id},
        {"_id": 0, "id": 1, "email": 1, "role": 1},
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    actor_role = user.get("role")
    previous_role = target.get("role")

    # ── Permission scoping ─────────────────────────────────────────────
    if actor_role not in FULL_ADMIN_ROLES_LOCAL:
        # Non-admin caller (Exec Cadre is the only other allowed role here).
        if actor_role != UserRole.EXEC_CADRE:
            # Defensive — require_role already enforced this, but keep the
            # double-check so a future router change doesn't open a hole.
            raise HTTPException(status_code=403, detail="Not authorised to change roles")

        # Exec Cadre may only manage cadre-side roles.
        if role not in EXEC_CADRE_MANAGEABLE_ROLES:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Exec Cadre may only assign cadre-side roles "
                    "(cadre, exec_cadre, squadron_commander, support_*)."
                ),
            )
        # And only edit users who are CURRENTLY in a cadre-managed role.
        if previous_role not in EXEC_CADRE_MANAGEABLE_ROLES:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Exec Cadre cannot modify a user whose current role "
                    f"({previous_role}) is not cadre-managed."
                ),
            )
        # Never let a non-admin grant protected/system roles.
        if role in PROTECTED_ROLES:
            raise HTTPException(
                status_code=403,
                detail="Only full admins can grant system-level roles.",
            )

    # ── Apply + audit ──────────────────────────────────────────────────
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"role": role, "permissions": get_default_permissions(role)}},
    )
    if result.modified_count == 0 and previous_role == role:
        # Idempotent no-op — still audit it so we can see attempted churn.
        await _audit_role_change(user, target, previous_role, role)
        return {"message": "Role unchanged (already set to this value)"}
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    await _audit_role_change(user, target, previous_role, role)

    # Auto-sync org chart after role change
    try:
        updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
        if updated_user:
            await auto_sync_org_chart(updated_user)
    except Exception as e:
        logger.error(f"Org chart auto-sync on role change failed: {e}")

    return {
        "message": "Role updated successfully",
        "previous_role": previous_role,
        "new_role": role,
    }


@api_router.get("/users/role-audit-log")
async def list_role_audit_log(
    limit: int = 200,
    user: dict = Depends(require_role([
        UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF,
        UserRole.EXEC_CADRE,
    ])),
):
    """List recent role changes.

    Full admins see everything. Exec Cadre sees only entries where they
    were the actor — they don't get to read senior-staff role changes.
    """
    query: dict = {}
    if user.get("role") == UserRole.EXEC_CADRE:
        query["actor_user_id"] = user.get("id")

    cur = db.role_audit_log.find(query, {"_id": 0}).sort("timestamp", -1).limit(min(limit, 500))
    return await cur.to_list(length=min(limit, 500))

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
            "support_section": assignment.support_section,
            "cadre_unit": assignment.cadre_unit,
            "cadre_position": assignment.cadre_position
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    
    # Auto-sync org chart position
    try:
        await auto_sync_org_chart(updated_user)
    except Exception as e:
        logger.error(f"Org chart auto-sync failed: {e}")
    
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
    """List unapproved users. Each entry now includes the Phase 4 status
    block so the admin UI can see at-a-glance whether the user already has
    a participant link (rare for pending users, but possible for parents)."""
    from account_status import compute_account_status
    pending_users = await db.users.find(
        {"$or": [{"is_approved": False}, {"is_approved": None}]},
        {"_id": 0, "password_hash": 0}
    ).to_list(1000)
    for u in pending_users:
        u["status"] = await compute_account_status(db, u)
    return pending_users


async def _resolve_user_for_approval(identifier: str):
    """Phase 4: tolerant lookup for the approval endpoint.

    Admin UI may send the user's UUID (the canonical identifier), but a
    stale pending list or a CSV-driven workflow may also send the email or
    CAPID. We try each in turn and return both the document and a label of
    HOW it was found so we can surface that in the response.
    """
    if not identifier:
        return None, None
    by_id = await db.users.find_one({"id": identifier})
    if by_id:
        return by_id, "id"
    ident_lower = identifier.strip().lower()
    by_email = await db.users.find_one({"email": {"$regex": f"^{ident_lower}$", "$options": "i"}})
    if by_email:
        return by_email, "email"
    by_capid = await db.users.find_one({"capid": identifier.strip()})
    if by_capid:
        return by_capid, "capid"
    return None, None


@api_router.post("/users/{user_id}/approve")
async def approve_user(
    user_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
):
    """Mark a pending user as approved. Phase 4 hardened.

    * Idempotent — re-approving a user returns 200 with already_approved=true
      and does NOT re-send the email.
    * Tolerant identifier lookup — accepts the canonical UUID `id`, the
      user's email, or their CAPID. The matched_by field in the response
      tells the caller which path resolved.
    * Always returns the canonical Phase 4 status block (six fields) so the
      caller knows both that approval succeeded AND the current linkage
      state — making the (separate) link-participant step's prerequisites
      explicit.

    Note: approval and participant-linking are deliberately SEPARATE steps.
    Use POST /api/users/{user_id}/link-participant?participant_id=... to
    attach a roster record after approval. The admin UI may chain them in
    an "Approve & Link" action, but each step is independently auditable.
    """
    if not user_id or len(user_id.strip()) < 3:
        raise HTTPException(
            status_code=400,
            detail={
                "reason": "invalid_identifier",
                "identifier": user_id,
                "message": "An identifier (UUID / email / CAPID) is required.",
            },
        )

    target_user, matched_by = await _resolve_user_for_approval(user_id)
    if not target_user:
        raise HTTPException(
            status_code=404,
            detail={
                "reason": "user_not_found",
                "identifier": user_id,
                "tried": ["id", "email", "capid"],
                "message": (
                    f"No user matched '{user_id}' on id, email, or CAPID. "
                    "Your pending list may be stale — refresh and try again. "
                    "If the user just registered, ask them to re-submit; if "
                    "they were already approved, look in /users instead of "
                    "/users/pending."
                ),
            },
        )

    from account_status import compute_account_status

    resolved_id = target_user["id"]
    if target_user.get("is_approved"):
        # Idempotent — already approved, don't re-send the email
        existing = await db.users.find_one({"id": resolved_id}, {"_id": 0, "password_hash": 0})
        return {
            "message": f"User '{existing.get('name') or existing.get('email')}' was already approved.",
            "already_approved": True,
            "matched_by": matched_by,
            "user": existing,
            "email_sent": False,
            "status": await compute_account_status(db, existing),
        }

    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": resolved_id},
        {"$set": {
            "is_approved": True,
            "approved_by": user["id"],
            "approved_at": now
        }}
    )

    app_url = os.environ.get('APP_URL', 'https://cadre-hub.preview.emergentagent.com')
    background_tasks.add_task(
        send_approval_email,
        target_user.get('email'),
        target_user.get('name', 'Member'),
        app_url
    )

    updated_user = await db.users.find_one({"id": resolved_id}, {"_id": 0, "password_hash": 0})
    return {
        "message": f"User '{updated_user.get('name') or updated_user.get('email')}' approved successfully.",
        "already_approved": False,
        "matched_by": matched_by,
        "user": updated_user,
        "email_sent": True,
        "status": await compute_account_status(db, updated_user),
    }


@api_router.get("/users/{user_id}/status")
async def get_user_status(
    user_id: str,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
):
    """Phase 4: admin-only — return the canonical six-field status block for
    any target user. Mirrors GET /auth/status but for a target identified by
    UUID, email, or CAPID."""
    target_user, matched_by = await _resolve_user_for_approval(user_id)
    if not target_user:
        raise HTTPException(
            status_code=404,
            detail={
                "reason": "user_not_found",
                "identifier": user_id,
                "tried": ["id", "email", "capid"],
                "message": f"No user matched '{user_id}'.",
            },
        )
    from account_status import compute_account_status
    return {
        **(await compute_account_status(db, target_user)),
        "user_id": target_user.get("id"),
        "email": target_user.get("email"),
        "name": target_user.get("name"),
        "matched_by": matched_by,
    }


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
    """Link a user account to a roster participant. INDEPENDENT of approval —
    this only mutates linkage, never approval state. Returns the canonical
    Phase 4 status block so the caller knows the resulting account_status.
    """
    target_user, _ = await _resolve_user_for_approval(user_id)
    if not target_user:
        raise HTTPException(
            status_code=404,
            detail={
                "reason": "user_not_found",
                "identifier": user_id,
                "tried": ["id", "email", "capid"],
                "message": f"No user matched '{user_id}'.",
            },
        )
    resolved_user_id = target_user["id"]

    participant = await db.participants.find_one(
        {"$or": [{"id": participant_id}, {"capid": participant_id}]},
        {"_id": 0}
    )
    if not participant:
        raise HTTPException(
            status_code=404,
            detail={
                "reason": "participant_not_found",
                "identifier": participant_id,
                "tried": ["id", "capid"],
                "message": f"No participant matched '{participant_id}' on id or CAPID.",
            },
        )
    
    now = datetime.now(timezone.utc).isoformat()
    update_fields = {
        "linked_participant_id": participant.get("id"),
        "capid": participant.get("capid"),
        "updated_at": now
    }
    
    if auto_populate:
        ptype = (participant.get("participant_type") or "").lower()
        member_type = (participant.get("member_type") or "").upper()

        # Senior members & senior-staff sub-event applicants → senior staff role
        SENIOR_PTYPES = {"senior_staff", "staff", "senior_member"}
        # Cadre cadets (incl. legacy exec_cadre records). Exec Cadre is a duty
        # subset of cadre, not a senior-staff promotion path.
        CADRE_PTYPES = {"cadre", "exec_cadre"}
        # Students (incl. legacy basic_student / advanced_student labels).
        STUDENT_PTYPES = {"student", "basic_student", "advanced_student"}

        if member_type in ("SENIOR", "CADET SPONSOR") or ptype in SENIOR_PTYPES:
            update_fields["role"] = UserRole.STAFF
        elif ptype in CADRE_PTYPES:
            update_fields["role"] = UserRole.CADRE
        elif ptype in STUDENT_PTYPES:
            update_fields["role"] = UserRole.STUDENT
        # Any other ptype (e.g. "needs_review", blank) → don't auto-promote;
        # leave the user's current role untouched so admins can resolve manually.
        
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
    
    await db.users.update_one({"id": resolved_user_id}, {"$set": update_fields})
    
    updated_user = await db.users.find_one({"id": resolved_user_id}, {"_id": 0, "password_hash": 0})

    # Auto-sync org chart after participant linking (name + capid changed)
    try:
        await auto_sync_org_chart(updated_user)
    except Exception as e:
        logger.error(f"Org chart auto-sync on link-participant failed: {e}")

    from account_status import compute_account_status
    return {
        "message": "User linked to participant successfully",
        "user": updated_user,
        "participant": participant,
        "status": await compute_account_status(db, updated_user),
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


# ================= CADRE POSITION =================

ALLOWED_CADRE_POSITIONS = {
    "group_commander", "group_deputy_commander", "group_superintendent",
    "cadet_dean_academics", "cadet_squadron_commander", "cadet_first_sergeant",
    "flight_commander", "flight_sergeant",
    "squadron_training_officer", "flight_training_officer",
    "commandant_of_cadets", "chief_training_officer",
}


@api_router.put("/users/{user_id}/cadre-position")
async def set_cadre_position(
    user_id: str,
    body: dict,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.EXEC_CADRE]))
):
    """Set cadre position and unit for a user (admin)"""
    cadre_position = body.get("cadre_position")
    cadre_unit = body.get("cadre_unit")

    if cadre_position is not None and cadre_position not in ALLOWED_CADRE_POSITIONS:
        raise HTTPException(
            status_code=400,
            detail=f"cadre_position must be null or one of: {sorted(ALLOWED_CADRE_POSITIONS)}"
        )

    existing = await db.users.find_one({"id": user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    # Phase 3 cadre-lead scope guard: an EXEC_CADRE caller may set cadre
    # positions only on cadre / exec-cadre / student targets. Senior-staff or
    # admin accounts can only be modified by a full admin.
    if not cadre_lead_can_target(user, existing):
        raise HTTPException(
            status_code=403,
            detail="Cadre Leads may only assign cadre positions to cadre/student accounts."
        )

    now = datetime.now(timezone.utc).isoformat()
    patch = {
        "cadre_position": cadre_position,
        "cadre_unit": cadre_unit,
        "updated_at": now,
        "updated_by": user["id"],
    }
    await db.users.update_one({"id": user_id}, {"$set": patch})
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return updated
