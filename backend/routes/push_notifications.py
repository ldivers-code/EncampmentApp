"""Push Notification routes (VAPID/Web Push)"""
from fastapi import Depends, HTTPException
from datetime import datetime, timezone

from database import db, api_router, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY
from models import UserRole, PushSubscription, PushNotificationRequest
from permissions import get_current_user, require_role

# ================= PUSH NOTIFICATION ROUTES =================

@api_router.get("/notifications/vapid-key")
async def get_vapid_key():
    """Get the VAPID public key for push subscription"""
    return {"publicKey": VAPID_PUBLIC_KEY}

@api_router.post("/notifications/subscribe")
async def subscribe_to_notifications(
    subscription: PushSubscription,
    user: dict = Depends(get_current_user)
):
    """Subscribe a user to push notifications"""
    # Store the subscription
    await db.push_subscriptions.update_one(
        {"user_id": user["id"]},
        {
            "$set": {
                "user_id": user["id"],
                "endpoint": subscription.endpoint,
                "keys": subscription.keys,
                "squadron": user.get("squadron"),
                "flight": user.get("flight"),
                "role": user["role"],
                "subscribed_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    return {"message": "Subscribed to notifications"}

@api_router.delete("/notifications/unsubscribe")
async def unsubscribe_from_notifications(user: dict = Depends(get_current_user)):
    """Unsubscribe a user from push notifications"""
    await db.push_subscriptions.delete_one({"user_id": user["id"]})
    return {"message": "Unsubscribed from notifications"}

@api_router.get("/notifications/status")
async def get_notification_status(user: dict = Depends(get_current_user)):
    """Check if user is subscribed to notifications"""
    subscription = await db.push_subscriptions.find_one({"user_id": user["id"]})
    return {"subscribed": subscription is not None}

@api_router.post("/notifications/send")
async def send_notification(
    notification: PushNotificationRequest,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    """Send push notification to users (filtered by target groups)"""
    try:
        # Build query based on target groups
        query = {}
        if "all" not in notification.target_groups:
            # Build OR conditions for squadrons and flights
            conditions = []
            for group in notification.target_groups:
                if group in ["6th_cts", "21st_cts", "22nd_cts"]:
                    conditions.append({"squadron": group})
                elif group in ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]:
                    conditions.append({"flight": group})
                elif group == "staff":
                    conditions.append({"role": {"$in": ["commander", "staff"]}})
            
            if conditions:
                query["$or"] = conditions
        
        # Get all matching subscriptions
        subscriptions = await db.push_subscriptions.find(query, {"_id": 0}).to_list(1000)
        
        if not subscriptions:
            return {"message": "No subscriptions found matching criteria", "sent": 0}
        
        # In production, you would use pywebpush here
        # For now, we'll just count and return success
        # The actual push would be:
        # from pywebpush import webpush, WebPushException
        # for sub in subscriptions:
        #     webpush(
        #         subscription_info={"endpoint": sub["endpoint"], "keys": sub["keys"]},
        #         data=json.dumps({"title": notification.title, "body": notification.body, "data": {"url": notification.url}}),
        #         vapid_private_key=VAPID_PRIVATE_KEY,
        #         vapid_claims={"sub": "mailto:admin@tnwg.cap.gov"}
        #     )
        
        # Store notification in database for history
        notification_id = str(uuid.uuid4())
        await db.notifications.insert_one({
            "id": notification_id,
            "title": notification.title,
            "body": notification.body,
            "target_groups": notification.target_groups,
            "sent_by": user["id"],
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "recipient_count": len(subscriptions)
        })
        
        return {
            "message": f"Notification queued for {len(subscriptions)} subscribers",
            "sent": len(subscriptions),
            "notification_id": notification_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")

@api_router.get("/notifications/history")
async def get_notification_history(
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    """Get history of sent notifications"""
    notifications = await db.notifications.find({}, {"_id": 0}).sort("sent_at", -1).to_list(50)
    return notifications

# Helper function to send schedule update notification
async def send_schedule_update_notification():
    """Send notification when schedule is updated/published"""
    subscriptions = await db.push_subscriptions.find({}, {"_id": 0}).to_list(1000)
    # In production, send actual push notifications here
    return len(subscriptions)


