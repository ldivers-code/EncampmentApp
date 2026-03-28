"""Notification system routes - in-app + email notifications"""
from fastapi import Depends, HTTPException
from database import db, api_router, SENDGRID_API_KEY, SENDGRID_SENDER_EMAIL
from models import UserRole, NotificationPreferences
from permissions import get_current_user, require_role
from datetime import datetime, timezone
import uuid
import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


async def create_notification(
    db_ref,
    title: str,
    message: str,
    notification_type: str = "info",
    target_users: list = None,
    target_roles: list = None,
    link: str = None,
    created_by: str = None
):
    """Create in-app notifications for targeted users and optionally send emails"""
    now = datetime.now(timezone.utc).isoformat()
    notification_id = str(uuid.uuid4())

    # Determine recipient users
    recipients = []
    if target_users:
        recipients = target_users
    elif target_roles and "all" in target_roles:
        all_users = await db_ref.users.find({"is_approved": True}, {"_id": 0, "id": 1, "email": 1, "name": 1}).to_list(500)
        recipients = [u["id"] for u in all_users]
    elif target_roles:
        all_users = await db_ref.users.find({"is_approved": True, "role": {"$in": target_roles}}, {"_id": 0, "id": 1}).to_list(500)
        recipients = [u["id"] for u in all_users]

    if not recipients:
        # Fallback: notify all approved users
        all_users = await db_ref.users.find({"is_approved": True}, {"_id": 0, "id": 1}).to_list(500)
        recipients = [u["id"] for u in all_users]

    # Create notification document
    notification_doc = {
        "id": notification_id,
        "title": title,
        "message": message,
        "type": notification_type,
        "link": link,
        "created_by": created_by,
        "created_at": now,
        "target_roles": target_roles,
    }
    await db_ref.notifications.insert_one(notification_doc)

    # Create individual read-status entries for each recipient
    user_notifs = [{
        "id": str(uuid.uuid4()),
        "notification_id": notification_id,
        "user_id": uid,
        "is_read": False,
        "created_at": now
    } for uid in recipients]

    if user_notifs:
        await db_ref.user_notifications.insert_many(user_notifs)

    # Send email notifications to users with email enabled
    await send_notification_emails(db_ref, notification_id, title, message, link, recipients)

    return {"notification_id": notification_id, "recipients_count": len(recipients)}


async def send_notification_emails(db_ref, notification_id, title, message, link, user_ids):
    """Send email notifications to users who have email enabled"""
    if not SENDGRID_API_KEY:
        logging.info(f"[MOCKED] Email notification: {title} to {len(user_ids)} users")
        return

    users = await db_ref.users.find(
        {"id": {"$in": user_ids}, "is_approved": True},
        {"_id": 0, "email": 1, "name": 1, "id": 1}
    ).to_list(500)

    # Check user notification preferences
    for user in users:
        prefs = await db_ref.notification_preferences.find_one(
            {"user_id": user["id"]}, {"_id": 0}
        )
        if prefs and not prefs.get("email_enabled", True):
            continue

        try:
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #00205B; color: white; padding: 16px 24px;">
                    <h2 style="margin: 0;">CAP Encampment</h2>
                </div>
                <div style="padding: 24px; background-color: #f8fafc; border: 1px solid #e2e8f0;">
                    <h3 style="color: #00205B; margin-top: 0;">{title}</h3>
                    <p style="color: #475569;">{message}</p>
                    {f'<a href="{link}" style="display: inline-block; padding: 10px 20px; background-color: #00205B; color: white; text-decoration: none; border-radius: 4px; margin-top: 12px;">View Details</a>' if link else ''}
                </div>
                <div style="text-align: center; padding: 16px; font-size: 12px; color: #94a3b8;">
                    <p>Tennessee Wing Civil Air Patrol Encampment</p>
                </div>
            </div>
            """
            sg_message = Mail(
                from_email=SENDGRID_SENDER_EMAIL,
                to_emails=user["email"],
                subject=f"[CAP Encampment] {title}",
                html_content=html_content
            )
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            sg.send(sg_message)
        except Exception as e:
            logging.error(f"Failed to email {user['email']}: {e}")


# ─── API Routes ───

@api_router.get("/notifications")
async def get_user_notifications(user: dict = Depends(get_current_user)):
    """Get notifications for the current user"""
    user_notifs = await db.user_notifications.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)

    notification_ids = [n["notification_id"] for n in user_notifs]
    notifications = await db.notifications.find(
        {"id": {"$in": notification_ids}},
        {"_id": 0}
    ).to_list(50)

    notif_map = {n["id"]: n for n in notifications}

    result = []
    for un in user_notifs:
        notif = notif_map.get(un["notification_id"], {})
        result.append({
            "id": un["id"],
            "notification_id": un["notification_id"],
            "title": notif.get("title", ""),
            "message": notif.get("message", ""),
            "type": notif.get("type", "info"),
            "link": notif.get("link"),
            "is_read": un.get("is_read", False),
            "created_at": un.get("created_at", ""),
        })

    return result


@api_router.get("/notifications/unread-count")
async def get_unread_count(user: dict = Depends(get_current_user)):
    """Get count of unread notifications"""
    count = await db.user_notifications.count_documents(
        {"user_id": user["id"], "is_read": False}
    )
    return {"count": count}


@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: dict = Depends(get_current_user)):
    """Mark a notification as read"""
    result = await db.user_notifications.update_one(
        {"id": notification_id, "user_id": user["id"]},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Marked as read"}


@api_router.put("/notifications/read-all")
async def mark_all_read(user: dict = Depends(get_current_user)):
    """Mark all notifications as read"""
    now = datetime.now(timezone.utc).isoformat()
    result = await db.user_notifications.update_many(
        {"user_id": user["id"], "is_read": False},
        {"$set": {"is_read": True, "read_at": now}}
    )
    return {"message": f"Marked {result.modified_count} as read"}


@api_router.post("/notifications/send")
async def send_notification(
    data: dict,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.PLANS_PROGRAMS]))
):
    """Admin: Send a notification to targeted users/roles"""
    result = await create_notification(
        db,
        title=data.get("title", ""),
        message=data.get("message", ""),
        notification_type=data.get("type", "info"),
        target_roles=data.get("target_roles", ["all"]),
        target_users=data.get("target_users"),
        link=data.get("link"),
        created_by=user["id"]
    )
    return result


@api_router.get("/notifications/preferences")
async def get_notification_preferences(user: dict = Depends(get_current_user)):
    """Get user's notification preferences"""
    prefs = await db.notification_preferences.find_one(
        {"user_id": user["id"]}, {"_id": 0}
    )
    if not prefs:
        prefs = {
            "user_id": user["id"],
            "schedule_changes": True,
            "daily_digest": True,
            "announcements": True,
            "email_enabled": True,
            "in_app_enabled": True
        }
    return prefs


@api_router.put("/notifications/preferences")
async def update_notification_preferences(
    prefs: NotificationPreferences,
    user: dict = Depends(get_current_user)
):
    """Update user's notification preferences"""
    now = datetime.now(timezone.utc).isoformat()
    prefs_dict = prefs.model_dump()
    prefs_dict["user_id"] = user["id"]
    prefs_dict["updated_at"] = now

    await db.notification_preferences.update_one(
        {"user_id": user["id"]},
        {"$set": prefs_dict, "$setOnInsert": {"created_at": now}},
        upsert=True
    )
    return prefs_dict


@api_router.get("/notifications/admin/config")
async def get_notification_config(
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.PLANS_PROGRAMS]))
):
    """Get notification configuration (who gets notified for what)"""
    config = await db.notification_config.find_one({}, {"_id": 0})
    if not config:
        config = {
            "schedule_change_roles": ["all"],
            "daily_digest_roles": ["all"],
            "announcement_roles": ["all"],
            "email_enabled_global": bool(SENDGRID_API_KEY),
        }
    return config


@api_router.put("/notifications/admin/config")
async def update_notification_config(
    data: dict,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.PLANS_PROGRAMS]))
):
    """Update notification configuration"""
    now = datetime.now(timezone.utc).isoformat()
    data["updated_at"] = now
    data["updated_by"] = user["id"]
    await db.notification_config.update_one(
        {},
        {"$set": data},
        upsert=True
    )
    return data
