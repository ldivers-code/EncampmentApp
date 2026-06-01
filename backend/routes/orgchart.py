"""Org Chart routes - strict 1:1 dataset-driven org chart"""
from fastapi import Depends, HTTPException
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from database import db, api_router
from models import UserRole, OrgChartRoleCreate, OrgChartRoleUpdate, OrgChartRoleResponse
from permissions import get_current_user, require_role


async def enrich_role(role: dict) -> dict:
    """Add children list to a role and normalize field names"""
    # Normalize legacy field names
    if "title" in role and "position_title" not in role:
        role["position_title"] = role.pop("title")
    if "assigned_name" not in role:
        role["assigned_name"] = ""
    children = await db.org_chart_roles.find(
        {"reports_to": role["role_id"]},
        {"_id": 0, "role_id": 1}
    ).to_list(200)
    role["children"] = [c["role_id"] for c in children]
    return role


@api_router.get("/org-chart/roles")
async def get_org_chart_roles(raw: bool = False, user: dict = Depends(get_current_user)):
    """Get all org chart positions. Pass ?raw=true for flat list without enrichment."""
    roles = await db.org_chart_roles.find({}, {"_id": 0}).to_list(1000)
    if raw:
        return roles
    enriched = []
    for role in roles:
        r = await enrich_role(role)
        enriched.append(OrgChartRoleResponse(**r))
    return enriched


@api_router.get("/org-chart/roles/{role_id}", response_model=OrgChartRoleResponse)
async def get_org_chart_role(role_id: str, user: dict = Depends(get_current_user)):
    """Get single org chart position"""
    role = await db.org_chart_roles.find_one({"role_id": role_id}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=404, detail="Position not found")
    r = await enrich_role(role)
    return OrgChartRoleResponse(**r)


@api_router.post("/org-chart/roles", response_model=OrgChartRoleResponse)
async def create_org_chart_role(
    data: OrgChartRoleCreate,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    """Create a new org chart position"""
    existing = await db.org_chart_roles.find_one({"role_id": data.role_id})
    if existing:
        raise HTTPException(status_code=400, detail="Role ID already exists")

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        **data.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    await db.org_chart_roles.insert_one(doc)
    doc.pop("_id", None)
    r = await enrich_role(doc)
    return OrgChartRoleResponse(**r)


@api_router.put("/org-chart/roles/{role_id}", response_model=OrgChartRoleResponse)
async def update_org_chart_role(
    role_id: str,
    data: OrgChartRoleUpdate,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    """Update an org chart position"""
    now = datetime.now(timezone.utc).isoformat()
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now

    result = await db.org_chart_roles.update_one({"role_id": role_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Position not found")

    role = await db.org_chart_roles.find_one({"role_id": role_id}, {"_id": 0})
    r = await enrich_role(role)
    return OrgChartRoleResponse(**r)


@api_router.delete("/org-chart/roles/{role_id}")
async def delete_org_chart_role(
    role_id: str,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    """Delete an org chart position"""
    subordinates = await db.org_chart_roles.count_documents({"reports_to": role_id})
    if subordinates > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete position with {subordinates} subordinate(s). Reassign them first."
        )
    result = await db.org_chart_roles.delete_one({"role_id": role_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Position not found")
    return {"message": "Position deleted"}


@api_router.get("/org-chart/template")
async def get_org_chart_template(user: dict = Depends(get_current_user)):
    """Return the **canonical** org-chart position template (read-only).

    This is the single source of truth for the position hierarchy — branch
    categories, parent/child relationships, allowed participant types, and
    job descriptions. The mobile app and the frontend visualizer both read
    this to render the chart skeleton, then merge in live assignments from
    `GET /api/org-chart/roles`.
    """
    from org_chart_template import POSITION_TEMPLATE, ALLOWED_CATEGORIES
    return {
        "version": "feb-2026",
        "categories": sorted(ALLOWED_CATEGORIES),
        "positions": POSITION_TEMPLATE,
        "count": len(POSITION_TEMPLATE),
    }


@api_router.put("/org-chart/roles/{role_id}/assign-user")
async def assign_user_to_position(
    role_id: str,
    body: dict,
    user: dict = Depends(require_role([
        UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF,
        UserRole.EXEC_CADRE,
    ])),
):
    """Assign an approved user to an org-chart position.

    Body: `{user_id: str, propagate: bool=true}`.

    * `propagate=True` (default) — applies the **inverse mapping** for this
      position to the target user's `role` + `flight` + `squadron` +
      `cadre_position` + `support_section`, then the same auto-sync that
      fires on `PUT /users/{id}/role` writes the chart row. This is the
      one true "single source of truth" path; the users table and the
      org chart stay aligned.

    * `propagate=False` — manual override: just sets `assigned_name` (and
      `assigned_user_id`) on the chart row without touching the user. Use
      sparingly — the next time the user's role/unit changes, the live
      sync may overwrite this manual entry.

    Exec Cadre scoping (same rules as `PUT /users/{id}/role`):
      * may only assign cadre-bucket users (current role ∈
        EXEC_CADRE_MANAGEABLE_ROLES) and into cadre-bucket positions.
      * may NOT grant protected/system roles.
    """
    from org_chart_template import derive_user_updates_for_position
    from routes.users import (
        auto_sync_org_chart,
        EXEC_CADRE_MANAGEABLE_ROLES,
        PROTECTED_ROLES,
        FULL_ADMIN_ROLES_LOCAL,
        _audit_role_change,
    )

    user_id = (body or {}).get("user_id")
    propagate = bool((body or {}).get("propagate", True))
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    position = await db.org_chart_roles.find_one({"role_id": role_id}, {"_id": 0})
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    target = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if not target.get("is_approved"):
        raise HTTPException(
            status_code=400,
            detail="User must be approved before being assigned to an org-chart position.",
        )

    now = datetime.now(timezone.utc).isoformat()

    # ── Manual-override path ──────────────────────────────────────────
    if not propagate:
        # Exec Cadre may NOT do raw assigned_name writes — keeps the
        # users-table the single source of truth for them.
        if user.get("role") not in FULL_ADMIN_ROLES_LOCAL:
            raise HTTPException(
                status_code=403,
                detail="Manual override requires full-admin privileges. "
                       "Use propagate=true so role/unit fields stay in sync.",
            )
        await db.org_chart_roles.update_one(
            {"role_id": role_id},
            {"$set": {
                "assigned_name": (target.get("name") or "").strip(),
                "assigned_user_id": target.get("id"),
                "updated_at": now,
            }},
        )
        updated = await db.org_chart_roles.find_one({"role_id": role_id}, {"_id": 0})
        return {"position": updated, "user": target, "propagated": False}

    # ── Propagate path ────────────────────────────────────────────────
    updates = derive_user_updates_for_position(role_id)
    if updates is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Position '{role_id}' has no canonical inverse mapping. "
                "Use propagate=false (admins only) to write the name directly."
            ),
        )

    actor_role = user.get("role")
    previous_role = target.get("role")
    new_role = updates.get("role", previous_role)

    # Exec Cadre scoping
    if actor_role not in FULL_ADMIN_ROLES_LOCAL:
        if actor_role != UserRole.EXEC_CADRE:
            raise HTTPException(status_code=403, detail="Not authorised")
        if new_role not in EXEC_CADRE_MANAGEABLE_ROLES:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Exec Cadre cannot assign role '{new_role}' "
                    f"(position requires a non-cadre role)."
                ),
            )
        if previous_role not in EXEC_CADRE_MANAGEABLE_ROLES:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Exec Cadre cannot reassign a user whose current role "
                    f"({previous_role}) is not cadre-managed."
                ),
            )
        if new_role in PROTECTED_ROLES:
            raise HTTPException(
                status_code=403,
                detail="Only full admins can grant system-level roles.",
            )

    # Apply the field deltas
    from permissions import get_default_permissions
    set_doc = dict(updates)
    if "role" in updates and updates["role"] != previous_role:
        set_doc["permissions"] = get_default_permissions(updates["role"])
    set_doc["updated_at"] = now

    await db.users.update_one({"id": user_id}, {"$set": set_doc})

    if "role" in updates and updates["role"] != previous_role:
        await _audit_role_change(user, target, previous_role, updates["role"])

    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    await auto_sync_org_chart(updated_user)

    position_after = await db.org_chart_roles.find_one({"role_id": role_id}, {"_id": 0})
    return {
        "position": position_after,
        "user": updated_user,
        "propagated": True,
        "applied_updates": updates,
    }


@api_router.put("/org-chart/roles/{role_id}/clear-assignment")
async def clear_position_assignment(
    role_id: str,
    user: dict = Depends(require_role([
        UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF,
        UserRole.EXEC_CADRE,
    ])),
):
    """Clear `assigned_name` and `assigned_user_id` on a position.

    Does NOT modify the user's role/unit fields — only blanks the chart
    slot. The next role/unit change for the previously-assigned user will
    re-sync them into whatever their current role implies.
    """
    position = await db.org_chart_roles.find_one({"role_id": role_id}, {"_id": 0})
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    now = datetime.now(timezone.utc).isoformat()
    await db.org_chart_roles.update_one(
        {"role_id": role_id},
        {"$set": {"assigned_name": "", "assigned_user_id": None, "updated_at": now}},
    )
    return {"message": f"Cleared assignment on {role_id}", "role_id": role_id}


@api_router.post("/org-chart/resync-from-users")
async def resync_org_chart_from_users(
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
):
    """Rebuild every org-chart assignment from the current users collection.

    Walks every approved user, resolves their canonical position via
    `org_chart_template.find_role_id_for_user`, and writes the resulting
    `assigned_name` / `assigned_user_id` onto the matching `org_chart_roles`
    row. Useful after a bulk migration, a tab-by-tab upload, or when an
    operator wants to "rebuild now" instead of waiting for the next live
    role change.

    Does NOT delete template positions — for that use `POST /seed`.
    """
    from routes.users import auto_sync_org_chart  # local import to avoid cycle

    now = datetime.now(timezone.utc).isoformat()
    # Clear every dynamic assignment first so removed users disappear too.
    await db.org_chart_roles.update_many(
        {},
        {"$set": {
            "assigned_user_id": None,
            "assigned_user_ids": [],
            "assigned_name": "",
            "updated_at": now,
        }},
    )

    users = await db.users.find(
        {"is_approved": True}, {"_id": 0, "password_hash": 0}
    ).to_list(2000)

    synced = 0
    skipped = 0
    for u in users:
        result = await auto_sync_org_chart(u)
        if result:
            synced += 1
        else:
            skipped += 1

    return {
        "message": f"Resynced org chart from {len(users)} users",
        "synced": synced,
        "skipped": skipped,
        "total_users": len(users),
    }


@api_router.post("/org-chart/seed")
async def seed_org_chart(
    reset: bool = False,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
):
    """Reconcile `org_chart_roles` against the canonical template.

    Default behaviour (`reset=False`):
      * Adds positions present in the template but missing from the DB.
      * Updates template-driven metadata (title, parent, category, order)
        on existing rows but **preserves `assigned_name`** so manual edits
        and Exec Cadre role-sync writes survive the reseed.
      * Prunes any orphan positions that are no longer in the template.

    `reset=True` is destructive — wipes everything and re-seeds with the
    INITIAL_ASSIGNMENTS defaults. Use only when intentionally rebuilding.
    """
    from seed_orgchart import apply_seed
    summary = await apply_seed(db, reset=reset)
    return {
        "message": (
            f"Seeded {summary['total']} positions "
            f"(mode={summary['mode']}, inserted={summary['inserted']}, "
            f"updated={summary['updated']}, deleted={summary['deleted']}, "
            f"preserved={summary['preserved_assignments']})"
        ),
        **summary,
    }


@api_router.post("/org-chart/seed-defaults")
async def seed_default_org_chart(
    reset: bool = True,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
):
    """Reset the org chart to template defaults (destructive by default).

    Distinct from `/seed`: this endpoint defaults to `reset=True` and is
    the explicit "blow it away and start over" affordance.
    """
    from seed_orgchart import apply_seed
    summary = await apply_seed(db, reset=reset)
    return {"message": f"Seeded {summary['total']} positions (reset={reset})", **summary}
