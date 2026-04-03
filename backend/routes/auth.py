"""Auth, Password Reset, Presence, and Profile routes"""
from fastapi import Depends, HTTPException, UploadFile, File
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid
import bcrypt
import os
import logging
import base64

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from database import db, api_router, SENDGRID_API_KEY, SENDGRID_SENDER_EMAIL
from models import (
    UserRole, UserCreate, UserLogin, UserProfileUpdate, UserResponse, TokenResponse,
    ChangePasswordRequest
)
from permissions import (
    hash_password, verify_password, create_token,
    get_default_permissions, get_current_user, require_role
)


# ================= AUTH ROUTES =================

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    email = user_data.email.strip().lower()
    existing = await db.users.find_one({"email": {"$regex": f"^{email}$", "$options": "i"}})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_count = await db.users.count_documents({})
    is_first_user = user_count == 0
    assigned_role = UserRole.COMMANDER if is_first_user else user_data.role
    
    valid_registration_roles = [UserRole.STAFF, UserRole.CADRE, UserRole.PARENT]
    if not is_first_user and assigned_role not in valid_registration_roles:
        assigned_role = UserRole.STAFF
    
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    default_permissions = get_default_permissions(assigned_role)
    
    # For parent registration, verify the CAPID belongs to a student participant
    linked_participant_id = None
    if assigned_role == UserRole.PARENT:
        student = await db.participants.find_one(
            {"capid": user_data.capid, "is_removed": {"$ne": True}},
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "flight": 1}
        )
        if not student:
            raise HTTPException(status_code=400, detail="No student found with this CAPID. Please verify your cadet's CAPID.")
        linked_participant_id = student["id"]
    
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "role": assigned_role,
        "capid": user_data.capid,
        "squadron": user_data.squadron,
        "flight": user_data.flight,
        "password_hash": hash_password(user_data.password),
        "created_at": now,
        "is_approved": is_first_user,
        "approved_by": user_id if is_first_user else None,
        "approved_at": now if is_first_user else None,
        "permissions": default_permissions,
        "linked_participant_id": linked_participant_id
    }
    await db.users.insert_one(user_doc)
    
    token = create_token(user_id, user_data.email, assigned_role)
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=user_data.email,
            name=user_data.name,
            role=assigned_role,
            capid=user_data.capid,
            squadron=user_data.squadron,
            flight=user_data.flight,
            created_at=now,
            is_approved=is_first_user,
            permissions=default_permissions
        )
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    email = credentials.email.strip().lower()
    user = await db.users.find_one({"email": {"$regex": f"^{email}$", "$options": "i"}}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user["id"], user["email"], user["role"])
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            capid=user.get("capid"),
            squadron=user.get("squadron"),
            flight=user.get("flight"),
            created_at=user["created_at"]
        )
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
        capid=user.get("capid"),
        squadron=user.get("squadron"),
        flight=user.get("flight"),
        created_at=user["created_at"],
        permissions=user.get("permissions")
    )


# ================= PASSWORD RESET ROUTES =================

RESET_TOKEN_EXPIRY_HOURS = 1

async def send_password_reset_email(to_email: str, reset_token: str, user_name: str) -> bool:
    if not SENDGRID_API_KEY or SENDGRID_API_KEY == "your_sendgrid_api_key_here":
        logging.warning("SendGrid API key not configured - cannot send reset email")
        return False
    
    reset_link = f"{os.environ.get('APP_URL', 'http://localhost:3000')}/reset-password?token={reset_token}"
    
    subject = "Password Reset Request - CAP Encampment"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #00205B; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 30px; background-color: #f9f9f9; }}
            .button {{ display: inline-block; padding: 12px 30px; background-color: #00205B; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
            .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>
            <div class="content">
                <p>Hello {user_name},</p>
                <p>We received a request to reset your password for the CAP Encampment Management System.</p>
                <p>Click the button below to reset your password:</p>
                <p style="text-align: center;">
                    <a href="{reset_link}" class="button">Reset Password</a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; font-size: 12px;">{reset_link}</p>
                <p><strong>This link will expire in 24 hours.</strong></p>
                <p>If you didn't request this password reset, please ignore this email or contact your commander.</p>
            </div>
            <div class="footer">
                <p>Tennessee Wing Civil Air Patrol</p>
                <p>Volunteers Serving America</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    message = Mail(
        from_email=SENDGRID_SENDER_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )
    
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logging.info(f"Password reset email sent to {to_email}, status: {response.status_code}")
        return response.status_code == 202
    except Exception as e:
        logging.error(f"Failed to send password reset email to {to_email}: {str(e)}")
        return False

@api_router.post("/auth/forgot-password")
async def forgot_password(email: str, capid: str):
    user = await db.users.find_one({"email": email.lower()})
    if not user:
        return {"message": "If an account with this email exists and the CAPID matches, you will receive a reset link."}
    
    user_capid = str(user.get("capid", "")).strip()
    provided_capid = str(capid).strip()
    
    if user_capid != provided_capid:
        return {"message": "If an account with this email exists and the CAPID matches, you will receive a reset link."}
    
    reset_token = str(uuid.uuid4())
    expiry = datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_EXPIRY_HOURS)
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "reset_token": reset_token,
            "reset_token_expiry": expiry.isoformat()
        }}
    )
    
    email_sent = await send_password_reset_email(user["email"], reset_token, user.get("name", "User"))
    
    if email_sent:
        return {"message": "If an account with this email exists and the CAPID matches, you will receive a reset link."}
    else:
        logging.warning("SendGrid not configured - returning token directly for testing")
        return {
            "message": "Email service not configured. Please contact your commander to reset your password.",
            "debug_token": reset_token
        }

@api_router.post("/auth/reset-password")
async def reset_password(token: str, new_password: str):
    user = await db.users.find_one({"reset_token": token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    expiry_str = user.get("reset_token_expiry")
    if expiry_str:
        expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expiry:
            raise HTTPException(status_code=400, detail="Reset token has expired")
    
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": password_hash},
         "$unset": {"reset_token": "", "reset_token_expiry": ""}}
    )
    
    return {"message": "Password has been reset successfully"}

@api_router.post("/auth/verify-reset-token")
async def verify_reset_token(token: str):
    user = await db.users.find_one({"reset_token": token})
    if not user:
        return {"valid": False, "message": "Invalid reset token"}
    
    expiry_str = user.get("reset_token_expiry")
    if expiry_str:
        expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expiry:
            return {"valid": False, "message": "Reset token has expired"}
    
    return {"valid": True, "email": user.get("email")}

@api_router.post("/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: str,
    new_password: str,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
):
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"password_hash": password_hash},
         "$unset": {"reset_token": "", "reset_token_expiry": ""}}
    )
    
    return {"message": f"Password reset successfully for {target_user.get('name')}"}


# ================= ACTIVE USERS / PRESENCE ROUTES =================

ACTIVE_THRESHOLD_SECONDS = 60

@api_router.post("/presence/heartbeat")
async def heartbeat(user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"last_active": now, "is_online": True}}
    )
    return {"status": "ok", "timestamp": now}

@api_router.get("/presence/active-users")
async def get_active_users(user: dict = Depends(get_current_user)):
    threshold = datetime.now(timezone.utc) - timedelta(seconds=ACTIVE_THRESHOLD_SECONDS)
    threshold_iso = threshold.isoformat()
    
    active_users = await db.users.find(
        {
            "last_active": {"$gte": threshold_iso},
            "is_approved": True
        },
        {"_id": 0, "password_hash": 0, "permissions": 0}
    ).to_list(100)
    
    formatted = []
    for u in active_users:
        formatted.append({
            "id": u.get("id"),
            "name": u.get("name"),
            "role": u.get("role"),
            "last_active": u.get("last_active")
        })
    
    return {
        "count": len(formatted),
        "users": formatted
    }

@api_router.post("/presence/offline")
async def go_offline(user: dict = Depends(get_current_user)):
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"is_online": False}}
    )
    return {"status": "ok"}


# ================= PROFILE ROUTES =================

@api_router.get("/profile", response_model=UserResponse)
async def get_profile(user: dict = Depends(get_current_user)):
    return UserResponse(**user)


@api_router.put("/profile", response_model=UserResponse)
async def update_profile(
    profile_data: UserProfileUpdate,
    user: dict = Depends(get_current_user)
):
    now = datetime.now(timezone.utc).isoformat()
    
    update_fields = {k: v for k, v in profile_data.model_dump().items() if v is not None}
    update_fields["updated_at"] = now
    
    update_fields.pop("role", None)
    update_fields.pop("is_approved", None)
    update_fields.pop("approved_by", None)
    update_fields.pop("approved_at", None)
    
    if update_fields:
        await db.users.update_one({"id": user["id"]}, {"$set": update_fields})
    
    updated_user = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return UserResponse(**updated_user)


@api_router.post("/profile/photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be less than 5MB")
    
    encoded = base64.b64encode(contents).decode('utf-8')
    photo_url = f"data:{file.content_type};base64,{encoded}"
    
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"photo_url": photo_url, "updated_at": now}}
    )
    
    return {"message": "Photo uploaded successfully", "photo_url": photo_url}


@api_router.delete("/profile/photo")
async def delete_profile_photo(user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"photo_url": None, "updated_at": now}}
    )
    return {"message": "Photo deleted successfully"}


@api_router.post("/profile/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: dict = Depends(get_current_user)
):
    user_record = await db.users.find_one({"id": user["id"]})
    if not user_record:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(request.current_password, user_record["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    
    new_password_hash = hash_password(request.new_password)
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": new_password_hash}}
    )
    
    return {"message": "Password changed successfully"}
