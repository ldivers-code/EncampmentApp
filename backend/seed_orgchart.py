"""
Canonical Org Chart seed driven by `org_chart_template.POSITION_TEMPLATE`.

Behaviour:
  * `build_orgchart()` — builds the full list of position docs from the
    canonical template. Default is **preserve mode**: assignments already
    in the DB are kept; new positions get the initial-assignment defaults;
    positions that no longer exist in the template are pruned.
  * `build_orgchart(reset=True)` — destructive: ignores existing DB state
    and applies INITIAL_ASSIGNMENTS to every node.

This module is invoked from two places:
  * `routes/orgchart.py` `POST /api/org-chart/seed` (admin-triggered seed)
  * `python seed_orgchart.py` (CLI for first-time deployment / migration)
"""
import asyncio
import os
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

from org_chart_template import POSITION_TEMPLATE, INITIAL_ASSIGNMENTS


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _node_from_template(p: dict, assigned_name: str, created_at: Optional[str] = None) -> dict:
    """Build one persisted org_chart_role document from a template entry."""
    now = _now_iso()
    return {
        "id": p["role_id"],
        "role_id": p["role_id"],
        "position_title": p["position_title"],
        "assigned_name": (assigned_name or "").strip(),
        "reports_to": p.get("reports_to"),
        "secondary_reports_to": p.get("secondary_reports_to"),
        "role_category": p.get("role_category", ""),
        "order": p.get("order", 0),
        "display_label": p.get("display_label", ""),
        "job_description": p.get("job_description", ""),
        "responsible_for": "",
        "supervises": "",
        "position_code": p.get("position_code", ""),
        "single_occupant": p.get("single_occupant", True),
        "allowed_participant_types": p.get("allowed_participant_types", []),
        "created_at": created_at or now,
        "updated_at": now,
    }


async def build_orgchart_nodes(db, reset: bool = False) -> list[dict]:
    """Compute the full set of org-chart docs that **should** exist.

    In preserve mode (default) we keep `assigned_name` from any existing
    record so manual edits / Exec Cadre role-sync writes are NOT clobbered.
    """
    existing_by_role: dict[str, dict] = {}
    if not reset:
        async for d in db.org_chart_roles.find({}, {"_id": 0}):
            existing_by_role[d.get("role_id")] = d

    nodes: list[dict] = []
    for p in POSITION_TEMPLATE:
        rid = p["role_id"]
        existing = existing_by_role.get(rid)
        if existing and not reset and (existing.get("assigned_name") or "").strip():
            # Preserve current assignment.
            assigned = existing["assigned_name"]
            created = existing.get("created_at")
        else:
            assigned = INITIAL_ASSIGNMENTS.get(rid, "")
            created = (existing or {}).get("created_at")
        nodes.append(_node_from_template(p, assigned, created_at=created))
    return nodes


async def apply_seed(db, reset: bool = False) -> dict:
    """Compute the canonical nodeset and reconcile it into Mongo.

    * inserts missing positions
    * updates positions whose template metadata (title/parent/category/order)
      changed — without touching `assigned_name` in preserve mode
    * deletes positions that no longer exist in the template
    Returns a summary dict for the API caller.
    """
    nodes = await build_orgchart_nodes(db, reset=reset)
    target_ids = {n["role_id"] for n in nodes}

    if reset:
        await db.org_chart_roles.delete_many({})
        if nodes:
            await db.org_chart_roles.insert_many([dict(n) for n in nodes])
        return {
            "mode": "reset",
            "inserted": len(nodes),
            "updated": 0,
            "deleted": 0,
            "preserved_assignments": 0,
            "total": len(nodes),
        }

    # Preserve-mode reconciliation
    existing_ids = {d["role_id"] async for d in db.org_chart_roles.find({}, {"_id": 0, "role_id": 1})}
    to_insert = [n for n in nodes if n["role_id"] not in existing_ids]
    if to_insert:
        await db.org_chart_roles.insert_many([dict(n) for n in to_insert])

    updated_count = 0
    preserved_count = 0
    for n in nodes:
        if n["role_id"] in existing_ids:
            # Update template-driven metadata but NOT assigned_name
            update = {k: v for k, v in n.items()
                      if k not in ("id", "assigned_name", "created_at", "_id")}
            res = await db.org_chart_roles.update_one(
                {"role_id": n["role_id"]}, {"$set": update}
            )
            if res.modified_count:
                updated_count += 1
            if (n.get("assigned_name") or "").strip():
                preserved_count += 1

    # Prune orphan positions (no longer in template)
    deleted = await db.org_chart_roles.delete_many(
        {"role_id": {"$nin": list(target_ids)}}
    )

    return {
        "mode": "preserve",
        "inserted": len(to_insert),
        "updated": updated_count,
        "deleted": deleted.deleted_count,
        "preserved_assignments": preserved_count,
        "total": len(nodes),
    }


def build_orgchart() -> list[dict]:
    """Backwards-compatible synchronous helper (no DB access — initial seed).

    Returns the canonical nodeset with INITIAL_ASSIGNMENTS applied. Used by
    legacy callers and the CLI entrypoint below.
    """
    return [
        _node_from_template(p, INITIAL_ASSIGNMENTS.get(p["role_id"], ""))
        for p in POSITION_TEMPLATE
    ]


async def main():
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "test_database")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    summary = await apply_seed(db, reset=False)
    print(f"Seed result: {summary}")

    count = await db.org_chart_roles.count_documents({})
    print(f"Verified position count: {count}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
