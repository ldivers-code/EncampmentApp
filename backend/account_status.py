"""Phase 4 — Canonical account-status computation.

Single source of truth for the six fields the backend exposes to the client
to drive routing & gating:

    is_approved                  bool
    linked_participant_id        str | None
    participant_link_status      "linked" | "unlinked"
    encampment_participant_type  "student" | "cadre" | "senior_staff" | "needs_review" | None
    permission_role              UserRole string
    duty_assignment              human-readable summary string | None

Plus one derived rollup used everywhere as the client routing primitive:

    account_status               "pending_approval" | "approved_unlinked" | "approved_linked"

Approval and participant-linking are TWO INDEPENDENT lifecycle steps:
  • An admin approves a user account (POST /api/users/{id}/approve).
  • An admin (separately) links the user to a roster participant
    (POST /api/users/{id}/link-participant).
The admin UI may chain them with an "Approve & Link" button, but each step
returns its own status so the operations remain auditable.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


async def compute_account_status(db, user: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve the six-field status payload for a user document.

    The lookup of the linked participant filters out removed (soft-deleted)
    participants so a user pointing at a stale removed roster row is reported
    as `unlinked` (which is the correct UX — they need re-linking).
    """
    is_approved = bool(user.get("is_approved"))
    linked_pid: Optional[str] = user.get("linked_participant_id")

    participant: Optional[Dict[str, Any]] = None
    if linked_pid:
        participant = await db.participants.find_one(
            {"id": linked_pid, "is_removed": {"$ne": True}},
            {
                "_id": 0, "id": 1, "participant_type": 1, "is_exec_cadre": 1,
                "flight": 1, "squadron": 1, "position": 1,
            },
        )

    link_status = "linked" if participant else "unlinked"
    encampment_ptype = (participant or {}).get("participant_type")

    if not is_approved:
        account_status = "pending_approval"
    elif link_status == "unlinked":
        account_status = "approved_unlinked"
    else:
        account_status = "approved_linked"

    duty_parts = []
    if user.get("cadre_position"):
        duty_parts.append(user["cadre_position"])
    if user.get("cadre_unit"):
        duty_parts.append(user["cadre_unit"])
    if (participant or {}).get("position"):
        duty_parts.append(participant["position"])
    flight = user.get("flight") or (participant or {}).get("flight")
    if flight:
        duty_parts.append(f"Flight {flight}")
    squadron = user.get("squadron") or (participant or {}).get("squadron")
    if squadron:
        duty_parts.append(squadron)
    duty_assignment = " / ".join([str(p) for p in duty_parts if p]) or None

    return {
        "is_approved": is_approved,
        "linked_participant_id": linked_pid,
        "participant_link_status": link_status,
        "encampment_participant_type": encampment_ptype,
        "permission_role": user.get("role"),
        "duty_assignment": duty_assignment,
        "account_status": account_status,
    }
