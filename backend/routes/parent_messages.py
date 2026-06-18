"""Parent ↔ Exec Staff direct-contact channel.

Three pieces, per user spec:
  (a) In-app message threads — stored in `parent_messages`. Audit-friendly.
  (b) Email blast to every approved Exec Staff (role=executive_staff) so
      urgent messages don't wait for someone to open the app.
  (c) A read-only Exec Staff contact card endpoint so the parent UI can
      always show names + emails + phones, even before sending a message.

Recipients: ONLY users with `role=executive_staff` per user choice.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
import logging
import uuid

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from database import db, api_router, SENDGRID_API_KEY, SENDGRID_SENDER_EMAIL
from models import UserRole
from permissions import get_current_user

logger = logging.getLogger("parent_messages")

URGENCY_VALUES = ("question", "urgent", "emergency")
STATUS_VALUES = ("open", "in_progress", "resolved")


# ── Helpers ──────────────────────────────────────────────────────────
async def _exec_staff_users(projection: Optional[dict] = None) -> list[dict]:
    proj = projection or {"_id": 0, "id": 1, "name": 1, "email": 1, "phone": 1, "cell_phone": 1}
    return await db.users.find(
        {"role": UserRole.EXECUTIVE_STAFF, "is_approved": True},
        proj,
    ).to_list(200)


def _send_email(to_emails: list[str], subject: str, body_html: str) -> bool:
    """Fire-and-forget SendGrid send. Returns True on accepted, False on any error.
    The caller never raises — email failures must not break the user-facing flow.
    """
    if not SENDGRID_API_KEY or not SENDGRID_SENDER_EMAIL:
        logger.warning("SendGrid not configured — skipping email blast")
        return False
    if not to_emails:
        return False
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        recipients = [e for e in to_emails if e]
        if not recipients:
            return False
        msg = Mail(
            from_email=SENDGRID_SENDER_EMAIL,
            to_emails=recipients,
            subject=subject,
            html_content=body_html,
        )
        SendGridAPIClient(SENDGRID_API_KEY).send(msg)
        return True
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("SendGrid email failed: %s", exc)
        return False


def _require_parent(user: dict):
    if (user or {}).get("role") != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Parent access only")


def _require_exec_staff(user: dict):
    # Exec Staff (or full admins) can read / reply to parent messages.
    role = (user or {}).get("role")
    if role not in (UserRole.EXECUTIVE_STAFF, UserRole.COMMANDER, UserRole.DCP):
        raise HTTPException(status_code=403, detail="Exec Staff access only")


def _strip(s: Optional[str], maxlen: int) -> str:
    if not s:
        return ""
    return str(s).strip()[:maxlen]


# ── Pydantic ─────────────────────────────────────────────────────────
class ParentMessageCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=5000)
    urgency: str = "question"  # question | urgent | emergency


class ReplyBody(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class StatusUpdate(BaseModel):
    status: str  # open | in_progress | resolved


# ── Parent-side endpoints ────────────────────────────────────────────
@api_router.get("/parent/exec-contacts")
async def get_exec_contacts(user: dict = Depends(get_current_user)):
    """Return the Exec Staff contact card for the parent UI.

    Pulls every approved `role=executive_staff` user with safe fields only
    (name, email, phone). The Org Chart `assigned_user_id` link is used to
    surface the user's canonical position title when available.
    """
    _require_parent(user)
    users = await _exec_staff_users()
    if not users:
        return {"contacts": [], "note": "Exec Staff contacts not yet published."}

    # Look up org-chart positions for these users (best-effort)
    user_ids = [u["id"] for u in users if u.get("id")]
    pos_rows = await db.org_chart_roles.find(
        {"assigned_user_id": {"$in": user_ids}},
        {"_id": 0, "assigned_user_id": 1, "position_title": 1, "role_category": 1},
    ).to_list(500)
    pos_by_user = {p["assigned_user_id"]: p for p in pos_rows if p.get("assigned_user_id")}

    out = []
    for u in users:
        pos = pos_by_user.get(u["id"]) or {}
        out.append({
            "id": u["id"],
            "name": u.get("name", ""),
            "email": u.get("email", ""),
            "phone": u.get("phone") or u.get("cell_phone") or "",
            "position_title": pos.get("position_title", "Exec Staff"),
        })
    out.sort(key=lambda c: (c["name"] or "").lower())
    return {"contacts": out}


@api_router.post("/parent/messages")
async def create_parent_message(
    body: ParentMessageCreate,
    user: dict = Depends(get_current_user),
):
    """Parent sends a new message to Exec Staff.

    Persists a thread in `parent_messages` and fires an email blast to every
    approved Exec Staff. Always returns 200 — if SendGrid fails the message
    is still saved so Exec Staff sees it on their next portal refresh.
    """
    _require_parent(user)

    urgency = (body.urgency or "question").lower()
    if urgency not in URGENCY_VALUES:
        urgency = "question"

    now = datetime.now(timezone.utc).isoformat()
    msg_id = str(uuid.uuid4())

    cadet_id = user.get("linked_participant_id")
    cadet_name = None
    if cadet_id:
        cadet = await db.participants.find_one(
            {"id": cadet_id}, {"_id": 0, "first_name": 1, "last_name": 1},
        )
        if cadet:
            cadet_name = f"{cadet.get('last_name','')}, {cadet.get('first_name','')}".strip(", ")

    doc = {
        "id": msg_id,
        "parent_user_id": user.get("id"),
        "parent_name": user.get("name") or user.get("email"),
        "parent_email": user.get("email"),
        "cadet_participant_id": cadet_id,
        "cadet_name": cadet_name,
        "subject": _strip(body.subject, 200),
        "urgency": urgency,
        "status": "open",
        "thread": [{
            "id": str(uuid.uuid4()),
            "from_user_id": user.get("id"),
            "from_name": user.get("name") or user.get("email"),
            "from_role": "parent",
            "body": _strip(body.body, 5000),
            "created_at": now,
        }],
        "created_at": now,
        "updated_at": now,
    }
    await db.parent_messages.insert_one(doc)

    # Email blast — every approved Exec Staff
    staff = await _exec_staff_users()
    to_emails = [s.get("email") for s in staff if s.get("email")]
    urgency_label = {"question": "📋 Question",
                     "urgent": "⚠️ URGENT",
                     "emergency": "🚨 EMERGENCY"}[urgency]
    subj_prefix = "[Parent " + urgency.upper() + "]"
    email_html = f"""\
<div style="font-family: Arial, sans-serif; color: #111;">
  <h2 style="color:#00205B;margin:0 0 12px;">{urgency_label} — New parent message</h2>
  <p style="margin:0 0 6px;"><strong>From:</strong> {doc['parent_name']}
     {f"(parent of <em>{cadet_name}</em>)" if cadet_name else ""}</p>
  <p style="margin:0 0 6px;"><strong>Subject:</strong> {doc['subject']}</p>
  <hr style="border:none;border-top:1px solid #ddd;margin:12px 0;">
  <p style="white-space:pre-wrap;line-height:1.45;margin:0 0 12px;">{doc['thread'][0]['body']}</p>
  <hr style="border:none;border-top:1px solid #ddd;margin:12px 0;">
  <p style="color:#666;font-size:12px;margin:0;">Reply by opening the Parent Messages queue in the encampment app.</p>
</div>"""
    email_sent = _send_email(to_emails, f"{subj_prefix} {doc['subject']}", email_html)

    # Also create an in-app notification so the badge updates immediately
    try:
        from routes.notifications import create_notification
        await create_notification(
            db,
            title=f"{urgency_label} parent message",
            message=f"{doc['parent_name']}: {doc['subject']}",
            notification_type=("alert" if urgency != "question" else "info"),
            target_roles=[UserRole.EXECUTIVE_STAFF, UserRole.COMMANDER, UserRole.DCP],
            link="/admin?tab=parent-messages",
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to create in-app notification for parent message: %s", exc)

    return {
        "id": msg_id,
        "status": "open",
        "email_sent": email_sent,
        "recipients_count": len(to_emails),
    }


@api_router.get("/parent/messages")
async def list_my_parent_messages(user: dict = Depends(get_current_user)):
    """List the parent's own threads (newest first)."""
    _require_parent(user)
    cur = db.parent_messages.find(
        {"parent_user_id": user.get("id")}, {"_id": 0},
    ).sort("updated_at", -1)
    return await cur.to_list(200)


@api_router.post("/parent/messages/{message_id}/reply")
async def parent_reply(
    message_id: str,
    body: ReplyBody,
    user: dict = Depends(get_current_user),
):
    """Parent adds a reply to one of their own threads. Re-opens if resolved."""
    _require_parent(user)
    msg = await db.parent_messages.find_one(
        {"id": message_id, "parent_user_id": user.get("id")}, {"_id": 0},
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Message thread not found")
    now = datetime.now(timezone.utc).isoformat()
    reply = {
        "id": str(uuid.uuid4()),
        "from_user_id": user.get("id"),
        "from_name": user.get("name") or user.get("email"),
        "from_role": "parent",
        "body": _strip(body.body, 5000),
        "created_at": now,
    }
    new_status = "open" if msg.get("status") == "resolved" else msg.get("status", "open")
    await db.parent_messages.update_one(
        {"id": message_id},
        {"$push": {"thread": reply}, "$set": {"updated_at": now, "status": new_status}},
    )

    # Email blast Exec Staff again so they see the parent's follow-up
    staff = await _exec_staff_users()
    to_emails = [s.get("email") for s in staff if s.get("email")]
    _send_email(
        to_emails,
        f"[Parent Reply] {msg.get('subject','')}",
        f"<p><strong>{reply['from_name']}</strong> replied to the parent thread "
        f"<em>{msg.get('subject','')}</em>:</p>"
        f"<p style='white-space:pre-wrap;'>{reply['body']}</p>",
    )
    return {"ok": True}


# ── Exec Staff-side endpoints ────────────────────────────────────────
@api_router.get("/exec/parent-messages")
async def list_all_parent_messages(
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """List every parent message for the Exec Staff inbox (filterable)."""
    _require_exec_staff(user)
    q: dict = {}
    if status and status in STATUS_VALUES:
        q["status"] = status
    if urgency and urgency in URGENCY_VALUES:
        q["urgency"] = urgency
    cur = db.parent_messages.find(q, {"_id": 0}).sort([
        # Sort: emergency first, then urgent, then newest
        ("status", 1),     # open before resolved
        ("updated_at", -1),
    ])
    rows = await cur.to_list(500)
    # Counts for the dashboard badge
    open_count = sum(1 for r in rows if r.get("status") != "resolved")
    emergency_open = sum(
        1 for r in rows
        if r.get("urgency") == "emergency" and r.get("status") != "resolved"
    )
    return {
        "messages": rows,
        "open_count": open_count,
        "emergency_open": emergency_open,
        "total": len(rows),
    }


@api_router.post("/exec/parent-messages/{message_id}/reply")
async def exec_reply(
    message_id: str,
    body: ReplyBody,
    user: dict = Depends(get_current_user),
):
    """Exec Staff (or admin) replies to a parent thread. Emails the parent."""
    _require_exec_staff(user)
    msg = await db.parent_messages.find_one({"id": message_id}, {"_id": 0})
    if not msg:
        raise HTTPException(status_code=404, detail="Message thread not found")
    now = datetime.now(timezone.utc).isoformat()
    reply = {
        "id": str(uuid.uuid4()),
        "from_user_id": user.get("id"),
        "from_name": user.get("name") or user.get("email"),
        "from_role": "exec",
        "body": _strip(body.body, 5000),
        "created_at": now,
    }
    new_status = "in_progress" if msg.get("status") == "open" else msg.get("status", "in_progress")
    await db.parent_messages.update_one(
        {"id": message_id},
        {"$push": {"thread": reply}, "$set": {"updated_at": now, "status": new_status}},
    )

    parent_email = msg.get("parent_email")
    if parent_email:
        _send_email(
            [parent_email],
            f"Re: {msg.get('subject','')} — Encampment Exec Staff",
            f"""<div style="font-family:Arial,sans-serif;color:#111;">
  <p>Hello {msg.get('parent_name','')},</p>
  <p>{reply['from_name']} from Encampment Exec Staff replied to your message:</p>
  <blockquote style="border-left:3px solid #00205B;padding-left:12px;color:#333;white-space:pre-wrap;">
    {reply['body']}
  </blockquote>
  <p style="color:#666;font-size:12px;">Continue the thread by signing in to the Parent Portal and opening
  the <em>Contact Exec Staff</em> tab.</p>
</div>""",
        )
    return {"ok": True}


@api_router.put("/exec/parent-messages/{message_id}/status")
async def update_message_status(
    message_id: str,
    body: StatusUpdate,
    user: dict = Depends(get_current_user),
):
    _require_exec_staff(user)
    if body.status not in STATUS_VALUES:
        raise HTTPException(status_code=400, detail=f"status must be one of {STATUS_VALUES}")
    now = datetime.now(timezone.utc).isoformat()
    res = await db.parent_messages.update_one(
        {"id": message_id},
        {"$set": {"status": body.status, "updated_at": now,
                  "resolved_at": now if body.status == "resolved" else None,
                  "resolved_by": user.get("id") if body.status == "resolved" else None}},
    )
    if not res.matched_count:
        raise HTTPException(status_code=404, detail="Message thread not found")
    return {"ok": True, "status": body.status}
