"""Review Queue endpoints.

Participants are flagged for human review when:
  1. Their `SubEvents` cell was blank on the latest roster upload → they were
     stored as `participant_type='needs_review'`, `review_status='needs_review'`,
     `review_reason='Blank SubEvents/EventName in latest roster upload'`.
  2. They exist in the app but were NOT present in the latest spreadsheet →
     `review_status='needs_review'`, `review_reason='Exists in app but not in
     latest master roster upload'`.

This module exposes:
  * `GET  /api/review-queue`               — list review-flagged participants
  * `POST /api/review-queue/{id}/resolve`  — resolve with one of:
      action="approve_as_student" | "approve_as_cadre" |
             "approve_as_senior_staff" | "mark_cancelled" |
             "merge_into" (requires `merge_target_id`)
  * `GET  /api/review-queue/stats`         — counts for dashboard widgets
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from database import api_router, db
from models import UserRole
from permissions import require_role


# Roles allowed to act on the review queue. Commander/DCP/Executive Staff,
# and Plans/Programs (who manage the master roster).
REVIEW_QUEUE_ROLES = [
    UserRole.DCP,
    UserRole.COMMANDER,
    UserRole.EXECUTIVE_STAFF,
    UserRole.PLANS_PROGRAMS,
    UserRole.STAFF,
]


class ResolveAction(BaseModel):
    action: Literal[
        "approve_as_student",
        "approve_as_cadre",
        "approve_as_senior_staff",
        "mark_cancelled",
        "merge_into",
    ]
    merge_target_id: Optional[str] = Field(
        default=None,
        description="Required only when action='merge_into' — the id of the "
                    "participant to merge this row into.",
    )


def _review_query() -> dict:
    """Mongo filter for everything that needs human review."""
    return {
        "is_removed": {"$ne": True},
        "$or": [
            {"review_status": "needs_review"},
            {"participant_type": "needs_review"},
        ],
    }


def _scrub(p: dict) -> dict:
    """Strip Mongo internals; keep only roster-relevant fields."""
    p = dict(p)
    p.pop("_id", None)
    return p


@api_router.get("/review-queue/stats")
async def review_queue_stats(user: dict = Depends(require_role(REVIEW_QUEUE_ROLES))):
    """Dashboard counts. Returns:
      total: all review-flagged
      blank_subevents: rows with participant_type='needs_review'
      missing_from_upload: rows flagged because they aren't in the spreadsheet
      legacy: anything else (review_status set but no matching reason)
    """
    docs = await db.participants.find(_review_query(), {
        "_id": 0, "participant_type": 1, "review_reason": 1,
    }).to_list(2000)

    blank = sum(1 for d in docs if d.get("participant_type") == "needs_review")
    missing = sum(
        1 for d in docs
        if "not in latest" in (d.get("review_reason") or "").lower()
    )
    legacy = max(0, len(docs) - blank - missing)
    return {
        "total": len(docs),
        "blank_subevents": blank,
        "missing_from_upload": missing,
        "legacy": legacy,
    }


@api_router.get("/review-queue")
async def list_review_queue(
    limit: int = 200,
    user: dict = Depends(require_role(REVIEW_QUEUE_ROLES)),
):
    """Return every participant currently flagged for review, newest first."""
    cur = db.participants.find(_review_query(), {"_id": 0})
    cur = cur.sort("review_flagged_at", -1).limit(min(limit, 500))
    rows = await cur.to_list(length=min(limit, 500))
    return [_scrub(r) for r in rows]


@api_router.post("/review-queue/{participant_id}/resolve")
async def resolve_review(
    participant_id: str,
    action: ResolveAction,
    user: dict = Depends(require_role(REVIEW_QUEUE_ROLES)),
):
    """Resolve a review-flagged participant by one of five actions."""
    p = await db.participants.find_one({"id": participant_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")

    now = datetime.now(timezone.utc).isoformat()
    actor_id = user.get("id")
    actor_email = user.get("email")

    common_resolve_fields = {
        "review_status": None,
        "review_reason": None,
        "review_flagged_at": None,
        "review_flagged_by": None,
        "review_resolved_at": now,
        "review_resolved_by": actor_id,
        "updated_at": now,
    }

    if action.action == "mark_cancelled":
        await db.participants.update_one(
            {"id": participant_id},
            {"$set": {
                **common_resolve_fields,
                "is_removed": True,
                "removed_at": now,
                "removed_by": actor_id,
                "removed_reason": "Resolved from review queue (cancelled)",
            }},
        )
        return {"message": "Participant marked as cancelled", "id": participant_id}

    if action.action in ("approve_as_student", "approve_as_cadre",
                        "approve_as_senior_staff"):
        new_type = {
            "approve_as_student":      "student",
            "approve_as_cadre":        "cadre",
            "approve_as_senior_staff": "senior_staff",
        }[action.action]
        await db.participants.update_one(
            {"id": participant_id},
            {"$set": {
                **common_resolve_fields,
                "participant_type": new_type,
            }},
        )
        return {
            "message": f"Approved as {new_type}",
            "id": participant_id,
            "participant_type": new_type,
        }

    if action.action == "merge_into":
        if not action.merge_target_id:
            raise HTTPException(
                status_code=400,
                detail="merge_target_id is required for action='merge_into'.",
            )
        target = await db.participants.find_one(
            {"id": action.merge_target_id}, {"_id": 0},
        )
        if not target:
            raise HTTPException(status_code=404, detail="Merge target not found")

        # Carry over any non-empty fields from the duplicate INTO the target
        # WITHOUT clobbering values the target already has. Then soft-remove
        # the duplicate.
        merge_set: dict = {}
        for k, v in p.items():
            if k in ("id", "_id", "created_at", "is_removed", "removed_at",
                     "removed_by", "removed_reason"):
                continue
            if v in (None, "", []):
                continue
            if not target.get(k):
                merge_set[k] = v

        if merge_set:
            merge_set["updated_at"] = now
            await db.participants.update_one(
                {"id": action.merge_target_id},
                {"$set": merge_set},
            )

        await db.participants.update_one(
            {"id": participant_id},
            {"$set": {
                **common_resolve_fields,
                "is_removed": True,
                "removed_at": now,
                "removed_by": actor_id,
                "removed_reason": (
                    f"Resolved from review queue (merged into "
                    f"{action.merge_target_id})"
                ),
                "merged_into_id": action.merge_target_id,
            }},
        )
        # Audit row so we can see the merge after the fact.
        await db.review_resolutions.insert_one({
            "participant_id": participant_id,
            "target_id": action.merge_target_id,
            "action": "merge_into",
            "fields_carried": list(merge_set.keys()),
            "actor_id": actor_id,
            "actor_email": actor_email,
            "timestamp": now,
        })
        return {
            "message": "Merged into target",
            "id": participant_id,
            "merge_target_id": action.merge_target_id,
            "fields_carried": list(merge_set.keys()),
        }

    raise HTTPException(status_code=400, detail="Unknown action")
