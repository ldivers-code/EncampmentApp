"""Org Chart routes - strict 1:1 dataset-driven org chart"""
from fastapi import Depends, HTTPException
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from database import db, api_router
from models import UserRole, OrgChartRoleCreate, OrgChartRoleUpdate, OrgChartRoleResponse
from permissions import get_current_user, require_role


async def enrich_role(role: dict) -> dict:
    """Add children list to a role"""
    children = await db.org_chart_roles.find(
        {"reports_to": role["role_id"]},
        {"_id": 0, "role_id": 1}
    ).to_list(200)
    role["children"] = [c["role_id"] for c in children]
    return role


@api_router.get("/org-chart/roles", response_model=List[OrgChartRoleResponse])
async def get_org_chart_roles(user: dict = Depends(get_current_user)):
    """Get all org chart positions"""
    roles = await db.org_chart_roles.find({}, {"_id": 0}).to_list(1000)
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


@api_router.post("/org-chart/seed")
async def seed_org_chart(
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
):
    """Re-seed the org chart from the spreadsheet data"""
    from seed_orgchart import build_orgchart

    # Wipe and reseed
    await db.org_chart_roles.delete_many({})
    nodes = build_orgchart()
    if nodes:
        await db.org_chart_roles.insert_many(nodes)
    return {"message": f"Seeded {len(nodes)} positions"}


@api_router.post("/org-chart/seed-defaults")
async def seed_default_org_chart(
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
):
    """Seed default org chart (alias for /seed)"""
    from seed_orgchart import build_orgchart

    await db.org_chart_roles.delete_many({})
    nodes = build_orgchart()
    if nodes:
        await db.org_chart_roles.insert_many(nodes)
    return {"message": f"Seeded {len(nodes)} positions"}
