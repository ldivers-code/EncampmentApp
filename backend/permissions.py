"""Authentication helpers, permission checking, and RBAC utilities"""
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import logging

from database import db, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS, SENDGRID_API_KEY, SENDGRID_SENDER_EMAIL, security
from models import UserRole, DEFAULT_PERMISSIONS

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_default_permissions(role: str) -> dict:
    default = DEFAULT_PERMISSIONS.get(role, DEFAULT_PERMISSIONS[UserRole.CADRE])
    return default.model_dump()

def get_user_permissions(user: dict) -> dict:
    if user.get('permissions'):
        return user['permissions']
    return get_default_permissions(user.get('role', UserRole.CADRE))

async def send_approval_email(to_email: str, user_name: str, app_url: str = ""):
    if not SENDGRID_API_KEY:
        logging.warning("SendGrid API key not configured - skipping email notification")
        return False
    subject = "Your CAP Encampment Account Has Been Approved"
    html_content = f"""
    <!DOCTYPE html>
    <html><head><style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #00205B; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f5f5f5; }}
        .button {{ display: inline-block; padding: 12px 24px; background-color: #00205B; color: white; text-decoration: none; border-radius: 4px; margin-top: 15px; }}
        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
    </style></head>
    <body><div class="container">
        <div class="header"><h1>Civil Air Patrol</h1><h2>Tennessee Wing Encampment</h2></div>
        <div class="content">
            <h3>Welcome, {user_name}!</h3>
            <p>Your account for the CAP Encampment Management System has been approved.</p>
            <p>You now have full access based on your assigned role and permissions.</p>
            <a href="{app_url}/login" class="button">Log In Now</a>
        </div>
        <div class="footer"><p>Civil Air Patrol - United States Air Force Auxiliary</p></div>
    </div></body></html>
    """
    message = Mail(from_email=SENDGRID_SENDER_EMAIL, to_emails=to_email, subject=subject, html_content=html_content)
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logging.info(f"Approval email sent to {to_email}, status: {response.status_code}")
        return response.status_code == 202
    except Exception as e:
        logging.error(f"Failed to send approval email to {to_email}: {str(e)}")
        return False

def _extract_token(request: Request, credentials: Optional[HTTPAuthorizationCredentials]) -> str:
    """Extract JWT from httpOnly cookie, Authorization header, or query param."""
    # 1. httpOnly cookie (most secure)
    token = request.cookies.get("access_token")
    if token:
        return token
    # 2. Authorization: Bearer header (API clients, curl)
    if credentials and credentials.credentials:
        return credentials.credentials
    # 3. Query param (for img src tags)
    token = request.query_params.get("auth")
    if token:
        return token
    raise HTTPException(status_code=401, detail="Not authenticated")

async def get_current_user_pending_ok(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """Resolve the JWT to a user record. Does NOT enforce approval status — use
    only on endpoints that legitimately accept pending/unapproved users (e.g.
    /auth/me, /auth/status). For everything else, prefer get_current_user."""
    token = _extract_token(request, credentials)
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user['permissions'] = get_user_permissions(user)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """Resolve the JWT and ENFORCE that the account is approved.
    Returns 403 with reason='pending_approval' for pending users so the client
    can route them to a pending-approval screen instead of the app."""
    user = await get_current_user_pending_ok(request, credentials)
    if not user.get("is_approved"):
        raise HTTPException(
            status_code=403,
            detail={
                "reason": "pending_approval",
                "message": "Your account is awaiting approval. You will receive an email once an administrator approves your access.",
            },
        )
    return user


async def get_current_user_from_token(token: str):
    """Validate a raw JWT token string and return the user dict. Used for query-param auth."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user['permissions'] = get_user_permissions(user)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(allowed_roles: List[str]):
    async def role_checker(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ):
        user = await get_current_user(request, credentials)
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker

def require_health_view():
    async def checker(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ):
        user = await get_current_user(request, credentials)
        perms = user.get('permissions', {})
        if perms.get('health_view') or perms.get('health_full') or perms.get('page_health'):
            return user
        raise HTTPException(status_code=403, detail="Health Services access required")
    return checker

def require_health_full():
    async def checker(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ):
        user = await get_current_user(request, credentials)
        perms = user.get('permissions', {})
        if perms.get('health_full'):
            return user
        raise HTTPException(status_code=403, detail="Full Health Services access required")
    return checker

def require_check_in_access():
    async def checker(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    ):
        user = await get_current_user(request, credentials)
        perms = user.get('permissions', {})
        if perms.get('check_in_view') or perms.get('check_in_edit') or perms.get('page_check_in'):
            return user
        raise HTTPException(status_code=403, detail="Check-in access required")
    return checker

async def get_event_settings(database):
    settings = await database.event_settings.find_one({}, {"_id": 0})
    if not settings:
        settings = {"event_id": "tnwg_encampment_2026", "event_name": "2026 Tennessee Wing Encampment"}
        await database.event_settings.insert_one(settings)
    return settings
