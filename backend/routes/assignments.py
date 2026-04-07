"""Assignments system — create, submit, grade with rubrics, and send reminders."""
from fastapi import Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import Response as FastAPIResponse
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import logging

from database import db, api_router, security, SENDGRID_API_KEY, SENDGRID_SENDER_EMAIL
from models import UserRole
from permissions import get_current_user, require_role
from routes.notifications import create_notification
from file_storage import put_object, get_object

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

CREATOR_ROLES = [
    UserRole.EXEC_CADRE, UserRole.EXECUTIVE_STAFF,
    UserRole.TRAINING_OFFICER, UserRole.COMMANDER, UserRole.DCP,
]

GRADER_ROLES = [
    UserRole.EXEC_CADRE, UserRole.EXECUTIVE_STAFF,
    UserRole.COMMANDER, UserRole.DCP,
]


# ── helpers ──────────────────────────────────────────────────────────────

async def _get_assignees(assignment: dict) -> list[dict]:
    """Return list of user dicts who should complete this assignment."""
    query = {"is_approved": True}
    if assignment.get("target_type") == "individual":
        target_ids = assignment.get("target_users", [])
        if not target_ids:
            return []
        query["id"] = {"$in": target_ids}
    elif assignment.get("target_type") == "flight":
        flights = assignment.get("target_flights", [])
        if not flights:
            return []
        query["flight"] = {"$in": flights}
    else:
        # all cadre
        query["role"] = {"$in": [UserRole.CADRE, UserRole.EXEC_CADRE]}
    return await db.users.find(query, {"_id": 0, "id": 1, "email": 1, "name": 1, "flight": 1}).to_list(500)


async def _send_reminder_email(to_email: str, user_name: str, assignment_title: str, due_date: str, app_url: str = ""):
    if not SENDGRID_API_KEY:
        logging.warning("SendGrid not configured — skipping reminder email")
        return False
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
      <div style="background:#00205B;color:white;padding:20px;text-align:center">
        <h2>CAP Encampment — Assignment Reminder</h2>
      </div>
      <div style="padding:20px;background:#f5f5f5">
        <p>Hi {user_name},</p>
        <p>This is a reminder that the assignment <strong>{assignment_title}</strong> is due on <strong>{due_date}</strong>.</p>
        <p>Please log in to the app and submit your work before the deadline.</p>
        <a href="{app_url}/assignments" style="display:inline-block;padding:12px 24px;background:#00205B;color:white;text-decoration:none;border-radius:4px;margin-top:10px">View Assignment</a>
      </div>
    </div>
    """
    msg = Mail(from_email=SENDGRID_SENDER_EMAIL, to_emails=to_email,
               subject=f"Reminder: {assignment_title} — Due {due_date}", html_content=html)
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(msg)
        return True
    except Exception as e:
        logging.error(f"Reminder email failed for {to_email}: {e}")
        return False


# ── CRUD: Assignments ────────────────────────────────────────────────────

@api_router.post("/assignments")
async def create_assignment(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    user = await get_current_user(request, credentials)
    if user["role"] not in CREATOR_ROLES:
        raise HTTPException(403, "Only Exec Cadre, Exec Staff, and Training Officers can create assignments")

    body = await request.json()
    now = datetime.now(timezone.utc).isoformat()
    assignment_id = str(uuid.uuid4())

    rubric_items = body.get("rubric", [])
    max_score = sum(item.get("max_points", 10) for item in rubric_items) if rubric_items else 100

    doc = {
        "id": assignment_id,
        "title": body["title"],
        "description": body.get("description", ""),
        "due_date": body["due_date"],
        "target_type": body.get("target_type", "all"),  # all | flight | individual
        "target_flights": body.get("target_flights", []),
        "target_users": body.get("target_users", []),
        "rubric": rubric_items,
        "max_score": max_score,
        "allow_file_upload": body.get("allow_file_upload", True),
        "allow_text_response": body.get("allow_text_response", True),
        "status": "active",
        "created_by": user["id"],
        "created_by_name": user["name"],
        "created_at": now,
        "updated_at": now,
    }
    await db.assignments.insert_one(doc)

    # Notify assignees
    assignees = await _get_assignees(doc)
    if assignees:
        await create_notification(
            db, title="New Assignment",
            message=f"You have a new assignment: {doc['title']} — due {doc['due_date']}",
            notification_type="assignment",
            target_users=[a["id"] for a in assignees],
            link="/assignments",
            created_by=user["id"],
        )

    doc.pop("_id", None)
    return doc


@api_router.get("/assignments")
async def list_assignments(user: dict = Depends(get_current_user)):
    """List all assignments. Cadre only see ones targeted to them."""
    assignments = await db.assignments.find(
        {"status": {"$ne": "deleted"}}, {"_id": 0}
    ).sort("due_date", -1).to_list(500)

    # For non-creator roles, filter to only their assignments
    if user["role"] not in CREATOR_ROLES:
        filtered = []
        for a in assignments:
            if a.get("target_type") == "all":
                filtered.append(a)
            elif a.get("target_type") == "flight" and user.get("flight") in a.get("target_flights", []):
                filtered.append(a)
            elif a.get("target_type") == "individual" and user["id"] in a.get("target_users", []):
                filtered.append(a)
        assignments = filtered

    # Attach submission counts
    for a in assignments:
        total_subs = await db.assignment_submissions.count_documents({"assignment_id": a["id"]})
        graded_subs = await db.assignment_submissions.count_documents({"assignment_id": a["id"], "graded": True})
        a["submission_count"] = total_subs
        a["graded_count"] = graded_subs

        # Check if current user has submitted
        my_sub = await db.assignment_submissions.find_one(
            {"assignment_id": a["id"], "user_id": user["id"]}, {"_id": 0, "id": 1, "graded": 1}
        )
        a["my_submission"] = my_sub

    return assignments


@api_router.get("/assignments/{assignment_id}")
async def get_assignment(assignment_id: str, user: dict = Depends(get_current_user)):
    a = await db.assignments.find_one({"id": assignment_id, "status": {"$ne": "deleted"}}, {"_id": 0})
    if not a:
        raise HTTPException(404, "Assignment not found")
    # Attach submissions if creator/grader
    if user["role"] in CREATOR_ROLES:
        subs = await db.assignment_submissions.find(
            {"assignment_id": assignment_id}, {"_id": 0}
        ).to_list(500)
        a["submissions"] = subs
        # Attach assignees list
        assignees = await _get_assignees(a)
        a["assignees"] = assignees
    else:
        # Just attach own submission
        my_sub = await db.assignment_submissions.find_one(
            {"assignment_id": assignment_id, "user_id": user["id"]}, {"_id": 0}
        )
        a["my_submission"] = my_sub
    return a


@api_router.put("/assignments/{assignment_id}")
async def update_assignment(
    assignment_id: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    user = await get_current_user(request, credentials)
    if user["role"] not in CREATOR_ROLES:
        raise HTTPException(403, "Insufficient permissions")
    body = await request.json()
    now = datetime.now(timezone.utc).isoformat()

    update_fields = {}
    for field in ["title", "description", "due_date", "target_type", "target_flights",
                   "target_users", "rubric", "allow_file_upload", "allow_text_response", "status"]:
        if field in body:
            update_fields[field] = body[field]
    update_fields["updated_at"] = now

    if "rubric" in body:
        update_fields["max_score"] = sum(item.get("max_points", 10) for item in body["rubric"])

    result = await db.assignments.update_one(
        {"id": assignment_id}, {"$set": update_fields}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Assignment not found")
    return {"message": "Assignment updated"}


@api_router.delete("/assignments/{assignment_id}")
async def delete_assignment(assignment_id: str, user: dict = Depends(require_role(CREATOR_ROLES))):
    result = await db.assignments.update_one(
        {"id": assignment_id}, {"$set": {"status": "deleted"}}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Assignment not found")
    return {"message": "Assignment deleted"}


# ── Submissions ──────────────────────────────────────────────────────────

@api_router.post("/assignments/{assignment_id}/submit")
async def submit_assignment(
    assignment_id: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    text_response: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    user = await get_current_user(request, credentials)
    assignment = await db.assignments.find_one({"id": assignment_id, "status": "active"}, {"_id": 0})
    if not assignment:
        raise HTTPException(404, "Assignment not found or closed")

    # Check if user is an assignee
    assignees = await _get_assignees(assignment)
    if user["id"] not in [a["id"] for a in assignees]:
        raise HTTPException(403, "You are not assigned to this assignment")

    now = datetime.now(timezone.utc).isoformat()
    submission_id = str(uuid.uuid4())

    file_path = None
    file_name = None
    if file:
        contents = await file.read()
        file_path = f"assignments/{assignment_id}/{submission_id}/{file.filename}"
        put_object(file_path, contents, file.content_type or "application/octet-stream")
        file_name = file.filename

    # Upsert — allow re-submission
    existing = await db.assignment_submissions.find_one(
        {"assignment_id": assignment_id, "user_id": user["id"]}
    )
    if existing:
        update = {
            "text_response": text_response or existing.get("text_response", ""),
            "updated_at": now,
        }
        if file_path:
            update["file_path"] = file_path
            update["file_name"] = file_name
        # Reset grading on re-submit
        update["graded"] = False
        update["rubric_scores"] = []
        update["total_score"] = None
        update["feedback"] = ""
        update["graded_by"] = None
        update["graded_at"] = None

        await db.assignment_submissions.update_one(
            {"assignment_id": assignment_id, "user_id": user["id"]},
            {"$set": update}
        )
        return {"message": "Submission updated", "id": existing["id"]}
    else:
        doc = {
            "id": submission_id,
            "assignment_id": assignment_id,
            "user_id": user["id"],
            "user_name": user["name"],
            "user_flight": user.get("flight", ""),
            "text_response": text_response or "",
            "file_path": file_path,
            "file_name": file_name,
            "graded": False,
            "rubric_scores": [],
            "total_score": None,
            "feedback": "",
            "graded_by": None,
            "graded_at": None,
            "submitted_at": now,
            "updated_at": now,
        }
        await db.assignment_submissions.insert_one(doc)
        return {"message": "Assignment submitted", "id": submission_id}


@api_router.get("/assignments/{assignment_id}/submissions/{submission_id}/file")
async def get_submission_file(
    assignment_id: str,
    submission_id: str,
    user: dict = Depends(get_current_user),
):
    sub = await db.assignment_submissions.find_one(
        {"id": submission_id, "assignment_id": assignment_id}, {"_id": 0}
    )
    if not sub or not sub.get("file_path"):
        raise HTTPException(404, "File not found")
    # Allow owner or graders
    if sub["user_id"] != user["id"] and user["role"] not in GRADER_ROLES:
        raise HTTPException(403, "Access denied")
    data, content_type = get_object(sub["file_path"])
    return FastAPIResponse(content=data, media_type=content_type, headers={
        "Content-Disposition": f'attachment; filename="{sub.get("file_name", "file")}"'
    })


# ── Grading ──────────────────────────────────────────────────────────────

@api_router.post("/assignments/{assignment_id}/grade/{submission_id}")
async def grade_submission(
    assignment_id: str,
    submission_id: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    user = await get_current_user(request, credentials)
    if user["role"] not in GRADER_ROLES:
        raise HTTPException(403, "Only Exec Cadre can grade submissions")

    body = await request.json()
    rubric_scores = body.get("rubric_scores", [])
    feedback = body.get("feedback", "")
    total_score = sum(s.get("score", 0) for s in rubric_scores)

    now = datetime.now(timezone.utc).isoformat()
    result = await db.assignment_submissions.update_one(
        {"id": submission_id, "assignment_id": assignment_id},
        {"$set": {
            "graded": True,
            "rubric_scores": rubric_scores,
            "total_score": total_score,
            "feedback": feedback,
            "graded_by": user["id"],
            "graded_by_name": user["name"],
            "graded_at": now,
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Submission not found")

    # Notify the submitter
    sub = await db.assignment_submissions.find_one(
        {"id": submission_id}, {"_id": 0, "user_id": 1}
    )
    if sub:
        assignment = await db.assignments.find_one({"id": assignment_id}, {"_id": 0, "title": 1, "max_score": 1})
        title = assignment["title"] if assignment else "Assignment"
        await create_notification(
            db, title="Assignment Graded",
            message=f"Your submission for '{title}' has been graded: {total_score}/{assignment.get('max_score', 100)}",
            notification_type="assignment",
            target_users=[sub["user_id"]],
            link="/assignments",
            created_by=user["id"],
        )

    return {"message": "Submission graded", "total_score": total_score}


# ── Reminders ────────────────────────────────────────────────────────────

@api_router.post("/assignments/{assignment_id}/remind")
async def send_reminders(
    assignment_id: str,
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    user = await get_current_user(request, credentials)
    if user["role"] not in CREATOR_ROLES:
        raise HTTPException(403, "Insufficient permissions")

    assignment = await db.assignments.find_one({"id": assignment_id, "status": "active"}, {"_id": 0})
    if not assignment:
        raise HTTPException(404, "Assignment not found")

    assignees = await _get_assignees(assignment)
    submitted_ids = set()
    subs = await db.assignment_submissions.find(
        {"assignment_id": assignment_id}, {"_id": 0, "user_id": 1}
    ).to_list(500)
    submitted_ids = {s["user_id"] for s in subs}

    missing = [a for a in assignees if a["id"] not in submitted_ids]
    if not missing:
        return {"message": "All assignees have submitted", "reminded": 0}

    app_url = ""
    # In-app notification
    await create_notification(
        db, title="Assignment Reminder",
        message=f"Reminder: '{assignment['title']}' is due {assignment['due_date']}. Please submit your work.",
        notification_type="warning",
        target_users=[m["id"] for m in missing],
        link="/assignments",
        created_by=user["id"],
    )

    # Email reminders
    email_count = 0
    for m in missing:
        if m.get("email"):
            sent = await _send_reminder_email(
                m["email"], m["name"], assignment["title"], assignment["due_date"], app_url
            )
            if sent:
                email_count += 1

    return {
        "message": f"Sent reminders to {len(missing)} assignee(s). {email_count} emails sent.",
        "reminded": len(missing),
        "emails_sent": email_count,
    }


# ── Stats ────────────────────────────────────────────────────────────────

@api_router.get("/assignments/stats/overview")
async def assignment_stats(user: dict = Depends(get_current_user)):
    total = await db.assignments.count_documents({"status": {"$ne": "deleted"}})
    active = await db.assignments.count_documents({"status": "active"})
    total_subs = await db.assignment_submissions.count_documents({})
    graded = await db.assignment_submissions.count_documents({"graded": True})
    return {
        "total_assignments": total,
        "active_assignments": active,
        "total_submissions": total_subs,
        "graded_submissions": graded,
    }
