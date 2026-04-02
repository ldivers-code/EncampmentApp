"""Notification Badges API"""
from fastapi import Depends, HTTPException
from datetime import datetime, timezone

from database import db, api_router
from models import UserRole
from permissions import get_current_user

# ================= NOTIFICATION BADGES API =================

@api_router.get("/notification-badges")
async def get_notification_badges(user: dict = Depends(get_current_user)):
    """Get notification badge counts for sidebar items"""
    user_role = user.get('role')
    user_flight = user.get('flight', '').lower() if user.get('flight') else None
    user_squadron = user.get('squadron', '').lower() if user.get('squadron') else None
    
    badges = {}
    
    # Reports needing attention (for authorized roles)
    full_access_roles = [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.EXEC_CADRE, UserRole.STAFF, UserRole.PLANS_PROGRAMS]
    
    if user_role in full_access_roles:
        # Count escalated reports needing attention (all levels in the chain)
        escalated_count = await db.flight_reports.count_documents({
            "status": {"$in": [
                "escalated_flight_commander", "escalated_squadron", 
                "escalated_exec", "escalated_dcs", "escalated_commander", "at_commander"
            ]},
            "commander_issues.has_issues": True
        })
        
        # Count unreviewed reports
        unreviewed_count = await db.flight_reports.count_documents({
            "status": "submitted"
        })
        
        if escalated_count > 0 or unreviewed_count > 0:
            badges['my-flight'] = {
                "count": escalated_count + unreviewed_count,
                "type": "alert" if escalated_count > 0 else "info",
                "label": f"{escalated_count} escalated" if escalated_count > 0 else f"{unreviewed_count} unreviewed"
            }
    elif user_flight:
        # For flight staff - show unreviewed reports for their flight
        unreviewed_count = await db.flight_reports.count_documents({
            "flight": user_flight,
            "status": "submitted"
        })
        if unreviewed_count > 0:
            badges['my-flight'] = {
                "count": unreviewed_count,
                "type": "info",
                "label": f"{unreviewed_count} pending"
            }
    
    # Admin badges (for commanders)
    if user_role in [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]:
        # Pending user approvals
        pending_users = await db.users.count_documents({"is_approved": False})
        if pending_users > 0:
            badges['admin'] = {
                "count": pending_users,
                "type": "alert",
                "label": f"{pending_users} pending approval"
            }
    
    # Unread notifications count
    unread_notifications = await db.notifications.count_documents({
        "target_groups": {"$in": [user_role, "all"]},
        "read_by": {"$ne": user.get('id')}
    })
    if unread_notifications > 0:
        badges['notifications'] = {
            "count": unread_notifications,
            "type": "info"
        }
    
    # Schedule updates (events in the last hour)
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    
    # Check for any schedule updates in the last hour
    one_hour_ago = (now - timedelta(hours=1)).isoformat()
    recent_schedule_updates = await db.schedule_events.count_documents({
        "updated_at": {"$gte": one_hour_ago}
    })
    if recent_schedule_updates > 0:
        badges['schedule'] = {
            "count": recent_schedule_updates,
            "type": "info",
            "label": "Recently updated"
        }
    
    # Financial tracker - pending receipts (for finance role)
    if user_role in [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.FINANCE, UserRole.PLANS_PROGRAMS]:
        pending_receipts = await db.receipts.count_documents({
            "status": {"$in": ["pending", "submitted"]}
        })
        if pending_receipts > 0:
            badges['budget'] = {
                "count": pending_receipts,
                "type": "info",
                "label": f"{pending_receipts} pending receipts"
            }
    
    return badges


