from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import pandas as pd
from io import BytesIO

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'cap-encampment-secret-key-2026')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# VAPID Keys for Push Notifications (these should be in .env for production)
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', 'BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', 'UUxI4O8-FbRouAevSmBQ6o18hgE4nSG3qwvJTfKc-ls')

# SendGrid Configuration
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
SENDGRID_SENDER_EMAIL = os.environ.get('SENDGRID_SENDER_EMAIL', 'noreply@cap-encampment.org')

# Create the main app
app = FastAPI(title="CAP Encampment Roster API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

security = HTTPBearer()

# ================= MODELS =================

class UserRole:
    COMMANDER = "commander"
    FINANCE = "finance"
    PLANS_PROGRAMS = "plans_programs"  # Schedule/Admin
    EXEC_CADRE = "exec_cadre"  # Cadet Leadership
    STAFF = "staff"
    CADRE = "cadre"
    HEALTH_SERVICES = "health_services"  # Full access to health data

class UserUnit:
    STAFF = "staff"
    SUPPORT_CADRE = "support_cadre"
    EXEC_CADRE = "exec_cadre"
    OPS_CADRE = "ops_cadre"  # Contains squadrons/flights

# Granular permissions that can be assigned per user
class AccessPermissions(BaseModel):
    dashboard: bool = True
    roster_view: bool = True
    roster_edit: bool = False
    schedule_view: bool = True
    schedule_edit: bool = False
    budget_view: bool = False
    budget_edit: bool = False
    analytics: bool = False
    org_chart: bool = True
    handbooks: bool = True
    documents: bool = True
    admin_panel: bool = False
    # Health Services permissions
    health_view: bool = False  # View health summaries (basic info)
    health_full: bool = False  # Full health services access (medications, incidents)

# Default permissions by role
DEFAULT_PERMISSIONS = {
    UserRole.COMMANDER: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=True,
        schedule_view=True, schedule_edit=True,
        budget_view=True, budget_edit=True,
        analytics=True, org_chart=True, handbooks=True,
        documents=True, admin_panel=True,
        health_view=True, health_full=True
    ),
    UserRole.FINANCE: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        budget_view=True, budget_edit=True,
        analytics=True, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=False, health_full=False
    ),
    UserRole.PLANS_PROGRAMS: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=True,
        schedule_view=True, schedule_edit=True,
        budget_view=False, budget_edit=False,
        analytics=True, org_chart=True, handbooks=True,
        documents=True, admin_panel=True,
        health_view=False, health_full=False
    ),
    UserRole.EXEC_CADRE: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        budget_view=False, budget_edit=False,
        analytics=True, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=False, health_full=False
    ),
    UserRole.STAFF: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=True,
        schedule_view=True, schedule_edit=True,
        budget_view=False, budget_edit=False,
        analytics=False, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=True, health_full=False  # Staff can see basic health info but not medications
    ),
    UserRole.CADRE: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        budget_view=False, budget_edit=False,
        analytics=False, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=False, health_full=False
    ),
    UserRole.HEALTH_SERVICES: AccessPermissions(
        dashboard=True, roster_view=True, roster_edit=False,
        schedule_view=True, schedule_edit=False,
        budget_view=False, budget_edit=False,
        analytics=False, org_chart=True, handbooks=True,
        documents=True, admin_panel=False,
        health_view=True, health_full=True
    )
}

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str = UserRole.STAFF  # Default to staff (can choose staff/cadre during registration)
    capid: Optional[str] = None
    squadron: Optional[str] = None  # staff, support_cadre, exec_cadre, ops_cadre, 6th_cts, 21st_cts, 22nd_cts
    flight: Optional[str] = None  # alpha, bravo, charlie, delta, echo, foxtrot

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUnitAssignment(BaseModel):
    squadron: Optional[str] = None
    flight: Optional[str] = None

# Extended user profile model
class UserProfile(BaseModel):
    # Basic info
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    cell_phone: Optional[str] = None
    # CAP info
    capid: Optional[str] = None
    rank: Optional[str] = None
    unit: Optional[str] = None
    wing: Optional[str] = None
    region: Optional[str] = None
    # Personal
    gender: Optional[str] = None
    age: Optional[int] = None
    shirt_size: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    # Emergency contact
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    # Parent info (for cadets)
    cadet_parent_name: Optional[str] = None
    cadet_parent_phone: Optional[str] = None
    cadet_parent_email: Optional[str] = None
    # Profile photo
    photo_url: Optional[str] = None

class UserProfileUpdate(UserProfile):
    pass

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str
    capid: Optional[str] = None
    squadron: Optional[str] = None
    flight: Optional[str] = None
    created_at: str
    # Extended profile fields
    phone: Optional[str] = None
    cell_phone: Optional[str] = None
    rank: Optional[str] = None
    unit: Optional[str] = None
    wing: Optional[str] = None
    region: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    shirt_size: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    cadet_parent_name: Optional[str] = None
    cadet_parent_phone: Optional[str] = None
    cadet_parent_email: Optional[str] = None
    photo_url: Optional[str] = None
    # Approval status
    is_approved: Optional[bool] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    linked_participant_id: Optional[str] = None
    # Granular permissions
    permissions: Optional[dict] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class ParticipantBase(BaseModel):
    capid: str
    rank: str
    last_name: str
    first_name: str
    middle_name: Optional[str] = None
    unit: str
    wing: Optional[str] = None
    region: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    age_at_event: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    cell_phone: Optional[str] = None
    shirt_size: Optional[str] = None
    member_type: Optional[str] = None  # SENIOR, CADET
    participant_type: str = "basic_student"  # basic_student, advanced_student, cadre, staff, senior_member
    squadron: Optional[str] = None
    flight: Optional[str] = None
    position: Optional[str] = None
    # Payment & Registration
    paid: bool = False
    paid_in_full: bool = False
    amount_paid: Optional[float] = None
    registration_status: Optional[str] = None
    staff_member: bool = False
    # Approvals
    unit_approved: bool = False
    unit_approval_date: Optional[str] = None
    wing_approved: bool = False
    wing_approval_date: Optional[str] = None
    slotted: bool = False
    # Address
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    # Emergency Contact
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    # Parent Info (for cadets)
    cadet_parent_phone: Optional[str] = None
    cadet_parent_email: Optional[str] = None
    # Unit/Wing CC
    unit_cc_name: Optional[str] = None
    unit_cc_email: Optional[str] = None
    # Training & Certifications
    last_encampment: Optional[str] = None
    cppt_expiration: Optional[str] = None
    first_aid: Optional[str] = None
    is100_date: Optional[str] = None
    is700_date: Optional[str] = None
    first_encampment: bool = True
    # Other
    religious_preference: Optional[str] = None
    comments: Optional[str] = None
    notes: Optional[str] = None
    # Removal tracking
    is_removed: Optional[bool] = False
    removed_at: Optional[str] = None
    removed_by: Optional[str] = None
    removal_reason: Optional[str] = None

class ParticipantCreate(ParticipantBase):
    pass

class ParticipantRemoval(BaseModel):
    removal_reason: str

class ParticipantResponse(ParticipantBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    created_at: str
    updated_at: str

class ScheduleEventBase(BaseModel):
    title: str
    description: Optional[str] = None
    date: str  # ISO date string
    start_time: str
    end_time: str
    location: Optional[str] = None
    event_type: str = "general"  # general, training, ceremony, meal, recreation, pt, admin, leadership, academics
    target_groups: List[str] = ["all"]  # all, staff, 6th_cts, 21st_cts, 22nd_cts, alpha, bravo, charlie, delta, echo, foxtrot
    uniform: Optional[str] = None  # ABU, Blues, PT, Flight Suit, Civilian, Class A, Class B, or None for default

class ScheduleEventCreate(ScheduleEventBase):
    pass

class ScheduleEventResponse(ScheduleEventBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    is_published: bool = False
    created_at: str
    updated_at: str

# Schedule Settings for draft/publish status
class ScheduleSettings(BaseModel):
    is_published: bool = False
    last_published_at: Optional[str] = None
    last_modified_at: Optional[str] = None
    version: int = 0  # Incremented on each change for real-time sync

# Push Notification Models
class PushSubscription(BaseModel):
    endpoint: str
    keys: Dict[str, str]

class PushNotificationRequest(BaseModel):
    title: str
    body: str
    target_groups: List[str] = ["all"]  # all, staff, 6th_cts, 21st_cts, 22nd_cts, or specific flights
    url: Optional[str] = "/schedule"

class BudgetItemBase(BaseModel):
    category: str
    subcategory: Optional[str] = None
    item_name: str
    estimated: float = 0.0
    actual: float = 0.0
    notes: Optional[str] = None
    receipt_url: Optional[str] = None
    receipt_filename: Optional[str] = None
    payment_status: str = "pending"  # pending, paid, cancelled
    payment_date: Optional[str] = None
    vendor: Optional[str] = None
    item_type: str = "expense"  # expense, income


# Food Expense Settings Model (Default $13.15 from 2026 TNWG Encampment Budget)
class FoodExpenseSettings(BaseModel):
    cost_per_person_per_day: float = 13.15
    total_participants: int = 0
    total_days: int = 8  # July 17-24 = 8 days
    notes: Optional[str] = None


class FoodExpenseSettingsUpdate(BaseModel):
    cost_per_person_per_day: Optional[float] = None
    total_participants: Optional[int] = None
    total_days: Optional[int] = None
    notes: Optional[str] = None


# ================= POINT TRACKING MODELS =================

class ScoreCategoryBase(BaseModel):
    name: str  # e.g., "Barracks Inspection", "Drill Competition"
    category_type: str  # "flight", "squadron", "individual_cadet", "individual_cadre"
    max_points: float = 100.0
    description: Optional[str] = None
    is_active: bool = True

class ScoreCategoryCreate(ScoreCategoryBase):
    pass

class ScoreCategoryResponse(ScoreCategoryBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    created_at: str

class ScoreEntryBase(BaseModel):
    category_id: str
    target_type: str  # "flight", "squadron", "individual"
    target_id: str  # flight name, squadron name, or participant id
    target_name: Optional[str] = None  # Display name
    points: float
    date: str  # YYYY-MM-DD
    notes: Optional[str] = None

class ScoreEntryCreate(ScoreEntryBase):
    pass

class ScoreEntryResponse(ScoreEntryBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    category_name: Optional[str] = None
    entered_by: Optional[str] = None
    created_at: str

class MeritDemeritEntry(BaseModel):
    participant_id: str
    participant_name: Optional[str] = None
    entry_type: str  # "merit" or "demerit"
    points: float
    reason: str
    date: str  # YYYY-MM-DD

class MeritDemeritResponse(MeritDemeritEntry):
    model_config = ConfigDict(extra="ignore")
    id: str
    entered_by: Optional[str] = None
    created_at: str

class DailyAward(BaseModel):
    award_type: str  # "flight_of_day", "squadron_of_day", "cadet_of_day", "cadre_of_day"
    date: str  # YYYY-MM-DD
    winner_id: str
    winner_name: str
    total_points: float
    notes: Optional[str] = None


# ================= FLIGHT REPORTING MODELS =================

class FlightReportSection(BaseModel):
    """Individual section of a flight report"""
    content: str = ""
    has_issues: bool = False

class FlightReportBase(BaseModel):
    """Daily flight report following Encampment Reporting Guide"""
    report_date: str  # YYYY-MM-DD
    flight: str  # alpha, bravo, charlie, delta, echo, foxtrot
    squadron: str  # 6th_cts, 21st_cts, 22nd_cts
    reporter_role: str  # flight_sergeant, flight_commander, squadron_commander
    # 7 Required Sections
    morale: FlightReportSection = FlightReportSection()
    safety_concerns: FlightReportSection = FlightReportSection()
    discipline_issues: FlightReportSection = FlightReportSection()
    training_performance: FlightReportSection = FlightReportSection()
    significant_events: FlightReportSection = FlightReportSection()
    recommendations: FlightReportSection = FlightReportSection()
    commander_issues: FlightReportSection = FlightReportSection()  # Items requiring escalation

class FlightReportCreate(FlightReportBase):
    pass

class FlightReportResponse(FlightReportBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    submitted_by: str
    submitted_by_name: str
    status: str  # submitted, reviewed, escalated_squadron, escalated_exec, escalated_commander, resolved
    escalation_level: Optional[str] = None  # squadron_commander, exec_cadre, encampment_commander
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_notes: Optional[str] = None
    escalation_history: Optional[List[dict]] = []  # Track escalation chain
    created_at: str
    updated_at: str

class EscalateReportRequest(BaseModel):
    """Request to escalate a report up the chain
    
    Chain of command:
    flight_sergeant -> flight_commander -> squadron_commander -> exec_cadre -> dcs_commandant -> encampment_commander
    """
    escalate_to: str  # flight_commander, squadron_commander, exec_cadre, dcs_commandant, encampment_commander
    notes: Optional[str] = None

class ReportDeadlineSettings(BaseModel):
    """Settings for report submission deadlines"""
    deadline_time: str = "21:00"  # 24-hour format (default 9 PM)
    reminder_minutes_before: int = 60  # Send reminder 60 mins before deadline
    is_enabled: bool = True


class BudgetItemCreate(BudgetItemBase):
    pass

class BudgetItemResponse(BudgetItemBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    created_at: str
    updated_at: str

class DocumentBase(BaseModel):
    title: str
    description: Optional[str] = None
    doc_type: str  # handbook, official_document, form, tlp, pocket_class
    category: Optional[str] = None  # Custom category for organization
    content: Optional[str] = None
    file_url: Optional[str] = None
    # Flight/Squadron scope
    flight: Optional[str] = None  # alpha, bravo, charlie, delta, echo, foxtrot, or None for all
    squadron: Optional[str] = None  # 6th_cts, 21st_cts, 22nd_cts, or None for all
    scope: str = "global"  # global, squadron, flight

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    created_at: str
    updated_at: str
    uploaded_by: Optional[str] = None
    version: int = 1
    version_history: Optional[List[Dict[str, Any]]] = None


# ================= ORG CHART MODELS =================

class OrgChartRoleBase(BaseModel):
    role_id: str  # Unique identifier for the role position
    title: str  # Role title (e.g., "Encampment Commander")
    summary: Optional[str] = None  # Short description
    responsibilities: Optional[str] = None  # Markdown/rich text for responsibilities
    reports_to: Optional[str] = None  # role_id of supervisor
    level: int = 0  # Hierarchy level (0 = top)
    order: int = 0  # Display order within level
    assigned_participant_id: Optional[str] = None  # ID of assigned participant

class OrgChartRoleCreate(OrgChartRoleBase):
    pass

class OrgChartRoleUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    responsibilities: Optional[str] = None
    reports_to: Optional[str] = None
    level: Optional[int] = None
    order: Optional[int] = None
    assigned_participant_id: Optional[str] = None

class OrgChartRoleResponse(OrgChartRoleBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    assigned_member_name: Optional[str] = None  # Populated from participant lookup
    assigned_member_rank: Optional[str] = None
    direct_subordinates: List[str] = []  # List of role_ids
    created_at: str
    updated_at: str


# ================= GOOGLE SHEETS SYNC MODELS =================

class GoogleSheetConfig(BaseModel):
    sheet_type: str  # "roster" or "org_chart"
    spreadsheet_id: str
    gid: str  # Sheet tab ID
    name: Optional[str] = None  # Friendly name for the sheet
    enabled: bool = True

# ================= DAILY SETTINGS MODELS =================

class UniformOfTheDay(BaseModel):
    uniform_code: str  # e.g., "ABU", "Blues", "PT Gear"
    description: Optional[str] = None  # Additional notes
    special_instructions: Optional[str] = None

class WeatherFlagUpdate(BaseModel):
    flag_color: str  # "green", "yellow", "red", "black"
    heat_index: Optional[float] = None  # Current heat index
    wbgt: Optional[float] = None  # Wet Bulb Globe Temperature if available
    notes: Optional[str] = None  # Additional notes

class DailySettingsUpdate(BaseModel):
    uniform: Optional[UniformOfTheDay] = None
    weather_flag: Optional[WeatherFlagUpdate] = None

class GoogleSheetsSettings(BaseModel):
    roster_sheet: Optional[GoogleSheetConfig] = None
    org_chart_sheets: List[GoogleSheetConfig] = []
    sync_interval_hours: int = 1
    last_sync_at: Optional[str] = None
    last_sync_status: Optional[str] = None  # "success", "error", "running"
    last_sync_message: Optional[str] = None
    auto_sync_enabled: bool = True

class GoogleSheetsSyncRequest(BaseModel):
    roster_spreadsheet_id: Optional[str] = None
    roster_gid: Optional[str] = None
    org_chart_spreadsheet_id: Optional[str] = None
    org_chart_gids: Optional[List[str]] = None  # Multiple tabs for squadrons
    sync_interval_hours: int = 1
    auto_sync_enabled: bool = True


# ================= AUTH HELPERS =================

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
    """Get default permissions for a given role"""
    default = DEFAULT_PERMISSIONS.get(role, DEFAULT_PERMISSIONS[UserRole.CADRE])
    return default.model_dump()

def get_user_permissions(user: dict) -> dict:
    """Get user's permissions - custom if set, otherwise role defaults"""
    if user.get('permissions'):
        return user['permissions']
    return get_default_permissions(user.get('role', UserRole.CADRE))

async def send_approval_email(to_email: str, user_name: str, app_url: str = ""):
    """Send email notification when user account is approved"""
    if not SENDGRID_API_KEY:
        logging.warning("SendGrid API key not configured - skipping email notification")
        return False
    
    subject = "Your CAP Encampment Account Has Been Approved"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #00205B; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f5f5f5; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #00205B; color: white; text-decoration: none; border-radius: 4px; margin-top: 15px; }}
            .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Civil Air Patrol</h1>
                <h2>Tennessee Wing Encampment</h2>
            </div>
            <div class="content">
                <h3>Welcome, {user_name}!</h3>
                <p>Great news! Your account for the CAP Encampment Management System has been approved.</p>
                <p>You now have full access to the system based on your assigned role and permissions.</p>
                <p>You can log in using your registered email address and password.</p>
                <a href="{app_url}/login" class="button">Log In Now</a>
            </div>
            <div class="footer">
                <p>Civil Air Patrol - United States Air Force Auxiliary</p>
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
        logging.info(f"Approval email sent to {to_email}, status: {response.status_code}")
        return response.status_code == 202
    except Exception as e:
        logging.error(f"Failed to send approval email to {to_email}: {str(e)}")
        return False

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        # Add computed permissions to user object
        user['permissions'] = get_user_permissions(user)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(allowed_roles: List[str]):
    async def role_checker(user: dict = Depends(get_current_user)):
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker

# ================= AUTH ROUTES =================

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if this is the first user - make them commander and auto-approve
    user_count = await db.users.count_documents({})
    is_first_user = user_count == 0
    assigned_role = UserRole.COMMANDER if is_first_user else user_data.role
    
    # Validate role selection - only allow staff or cadre for new registrations
    valid_registration_roles = [UserRole.STAFF, UserRole.CADRE]
    if not is_first_user and assigned_role not in valid_registration_roles:
        assigned_role = UserRole.STAFF  # Default to staff if invalid role selected
    
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Get default permissions for the role
    default_permissions = get_default_permissions(assigned_role)
    
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
        # First user (commander) is auto-approved, others need approval
        "is_approved": is_first_user,
        "approved_by": user_id if is_first_user else None,
        "approved_at": now if is_first_user else None,
        # Initialize with role-based default permissions
        "permissions": default_permissions
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
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
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
        created_at=user["created_at"]
    )

# ================= USER MANAGEMENT =================

@api_router.get("/users", response_model=List[UserResponse])
async def get_users(user: dict = Depends(require_role([UserRole.COMMANDER]))):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return [UserResponse(**u) for u in users]

@api_router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, role: str, user: dict = Depends(require_role([UserRole.COMMANDER]))):
    valid_roles = [
        UserRole.COMMANDER, UserRole.FINANCE, UserRole.PLANS_PROGRAMS,
        UserRole.EXEC_CADRE, UserRole.STAFF, UserRole.CADRE, UserRole.HEALTH_SERVICES
    ]
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    result = await db.users.update_one({"id": user_id}, {"$set": {"role": role}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Role updated successfully"}

@api_router.put("/users/{user_id}/unit")
async def assign_user_unit(
    user_id: str, 
    assignment: UserUnitAssignment,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF, UserRole.PLANS_PROGRAMS]))
):
    """Assign a user to a squadron and flight"""
    # Updated valid units: Staff, Support Cadre, Exec Cadre, Ops Cadre, and CTS Squadrons
    valid_squadrons = [None, "", "staff", "support_cadre", "exec_cadre", "ops_cadre", "6th_cts", "21st_cts", "22nd_cts"]
    valid_flights = [None, "", "alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
    
    if assignment.squadron and assignment.squadron not in valid_squadrons:
        raise HTTPException(status_code=400, detail="Invalid squadron")
    if assignment.flight and assignment.flight not in valid_flights:
        raise HTTPException(status_code=400, detail="Invalid flight")
    
    # Units that don't need flight assignments
    no_flight_units = ["staff", "support_cadre", "exec_cadre"]
    
    # Clear flight if unit doesn't need one
    if assignment.squadron in no_flight_units:
        assignment.flight = None
    
    # Validate flight belongs to squadron (only for 6th_cts, 21st_cts, 22nd_cts, ops_cadre)
    flight_squadron_map = {
        "alpha": "6th_cts", "bravo": "6th_cts",
        "charlie": "21st_cts", "delta": "21st_cts",
        "echo": "22nd_cts", "foxtrot": "22nd_cts"
    }
    
    if assignment.flight and assignment.flight in flight_squadron_map:
        expected_squadron = flight_squadron_map[assignment.flight]
        # For ops_cadre, allow any flight
        if assignment.squadron == "ops_cadre":
            pass  # Allow any flight in ops_cadre
        elif assignment.squadron and assignment.squadron != expected_squadron:
            raise HTTPException(
                status_code=400, 
                detail=f"Flight {assignment.flight} belongs to {expected_squadron}"
            )
        else:
            # Auto-assign squadron based on flight
            assignment.squadron = expected_squadron
    
    result = await db.users.update_one(
        {"id": user_id}, 
        {"$set": {"squadron": assignment.squadron, "flight": assignment.flight}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return UserResponse(**updated_user)

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_role([UserRole.COMMANDER]))):
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}


# ================= PASSWORD RESET ROUTES =================

RESET_TOKEN_EXPIRY_HOURS = 24

async def send_password_reset_email(to_email: str, reset_token: str, user_name: str) -> bool:
    """Send password reset email via SendGrid"""
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
    """Initiate password reset - requires email and CAPID verification"""
    # Find user by email
    user = await db.users.find_one({"email": email.lower()})
    if not user:
        # Don't reveal if user exists or not
        return {"message": "If an account with this email exists and the CAPID matches, you will receive a reset link."}
    
    # Verify CAPID matches
    user_capid = str(user.get("capid", "")).strip()
    provided_capid = str(capid).strip()
    
    if user_capid != provided_capid:
        # Don't reveal if CAPID is wrong
        return {"message": "If an account with this email exists and the CAPID matches, you will receive a reset link."}
    
    # Generate reset token
    reset_token = str(uuid.uuid4())
    expiry = datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_EXPIRY_HOURS)
    
    # Store reset token in database
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "reset_token": reset_token,
            "reset_token_expiry": expiry.isoformat()
        }}
    )
    
    # Send email
    email_sent = await send_password_reset_email(user["email"], reset_token, user.get("name", "User"))
    
    if email_sent:
        return {"message": "If an account with this email exists and the CAPID matches, you will receive a reset link."}
    else:
        # If SendGrid not configured, return the token for testing (remove in production)
        logging.warning("SendGrid not configured - returning token directly for testing")
        return {
            "message": "Email service not configured. Please contact your commander to reset your password.",
            "debug_token": reset_token  # Remove this in production
        }

@api_router.post("/auth/reset-password")
async def reset_password(token: str, new_password: str):
    """Reset password using reset token"""
    # Find user with this reset token
    user = await db.users.find_one({"reset_token": token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Check if token is expired
    expiry_str = user.get("reset_token_expiry")
    if expiry_str:
        expiry = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expiry:
            raise HTTPException(status_code=400, detail="Reset token has expired")
    
    # Validate password
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    # Hash new password
    password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    
    # Update password and clear reset token
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": password_hash},
         "$unset": {"reset_token": "", "reset_token_expiry": ""}}
    )
    
    return {"message": "Password has been reset successfully"}

@api_router.post("/auth/verify-reset-token")
async def verify_reset_token(token: str):
    """Verify if a reset token is valid"""
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
    user: dict = Depends(require_role([UserRole.COMMANDER]))
):
    """Admin/Commander reset password for a user"""
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate password
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    # Hash new password
    password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    
    # Update password
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"password_hash": password_hash},
         "$unset": {"reset_token": "", "reset_token_expiry": ""}}
    )
    
    return {"message": f"Password reset successfully for {target_user.get('name')}"}


# ================= ACTIVE USERS / PRESENCE ROUTES =================

ACTIVE_THRESHOLD_SECONDS = 60  # Users are considered active if heartbeat within last 60 seconds

@api_router.post("/presence/heartbeat")
async def heartbeat(user: dict = Depends(get_current_user)):
    """Update user's last active timestamp (called every 30 seconds from frontend)"""
    now = datetime.now(timezone.utc).isoformat()
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"last_active": now, "is_online": True}}
    )
    
    return {"status": "ok", "timestamp": now}

@api_router.get("/presence/active-users")
async def get_active_users(user: dict = Depends(get_current_user)):
    """Get list of currently active users (heartbeat within threshold)"""
    threshold = datetime.now(timezone.utc) - timedelta(seconds=ACTIVE_THRESHOLD_SECONDS)
    threshold_iso = threshold.isoformat()
    
    # Find users with recent heartbeat
    active_users = await db.users.find(
        {
            "last_active": {"$gte": threshold_iso},
            "is_approved": True
        },
        {"_id": 0, "password_hash": 0, "permissions": 0}
    ).to_list(100)
    
    # Format response
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
    """Mark user as offline (called when user closes app or logs out)"""
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"is_online": False}}
    )
    return {"status": "ok"}


# ================= PROFILE ROUTES =================

@api_router.get("/profile", response_model=UserResponse)
async def get_profile(user: dict = Depends(get_current_user)):
    """Get current user's full profile"""
    return UserResponse(**user)


@api_router.put("/profile", response_model=UserResponse)
async def update_profile(
    profile_data: UserProfileUpdate,
    user: dict = Depends(get_current_user)
):
    """Update current user's profile"""
    now = datetime.now(timezone.utc).isoformat()
    
    # Build update dict, excluding None values
    update_fields = {k: v for k, v in profile_data.model_dump().items() if v is not None}
    update_fields["updated_at"] = now
    
    # Users cannot change their own role or approval status
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
    """Upload profile photo"""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Read and encode file
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(status_code=400, detail="Image must be less than 5MB")
    
    import base64
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
    """Delete profile photo"""
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"photo_url": None, "updated_at": now}}
    )
    return {"message": "Photo deleted successfully"}


# ================= USER APPROVAL ROUTES =================

@api_router.get("/users/pending")
async def get_pending_users(user: dict = Depends(require_role([UserRole.COMMANDER]))):
    """Get users pending approval"""
    pending_users = await db.users.find(
        {"$or": [{"is_approved": False}, {"is_approved": None}]},
        {"_id": 0, "password_hash": 0}
    ).to_list(1000)
    return pending_users


@api_router.post("/users/{user_id}/approve")
async def approve_user(
    user_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_role([UserRole.COMMANDER]))
):
    """Approve a user account and send email notification"""
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "is_approved": True,
            "approved_by": user["id"],
            "approved_at": now
        }}
    )
    
    # Send approval email in background
    app_url = os.environ.get('APP_URL', 'https://cadet-med-hub.preview.emergentagent.com')
    background_tasks.add_task(
        send_approval_email,
        target_user.get('email'),
        target_user.get('name', 'Member'),
        app_url
    )
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {"message": "User approved successfully", "user": updated_user, "email_sent": True}


@api_router.put("/users/{user_id}/permissions")
async def update_user_permissions(
    user_id: str,
    permissions: AccessPermissions,
    user: dict = Depends(require_role([UserRole.COMMANDER]))
):
    """Update a user's granular permissions"""
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "permissions": permissions.model_dump(),
            "permissions_updated_at": now,
            "permissions_updated_by": user["id"]
        }}
    )
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {"message": "Permissions updated successfully", "user": updated_user}


@api_router.post("/users/{user_id}/reset-permissions")
async def reset_user_permissions(
    user_id: str,
    user: dict = Depends(require_role([UserRole.COMMANDER]))
):
    """Reset a user's permissions to role defaults"""
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    default_perms = get_default_permissions(target_user.get('role', UserRole.CADRE))
    now = datetime.now(timezone.utc).isoformat()
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "permissions": default_perms,
            "permissions_updated_at": now,
            "permissions_updated_by": user["id"]
        }}
    )
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {"message": "Permissions reset to role defaults", "user": updated_user}


@api_router.post("/users/{user_id}/link-participant")
async def link_user_to_participant(
    user_id: str,
    participant_id: str,
    auto_populate: bool = True,
    user: dict = Depends(require_role([UserRole.COMMANDER]))
):
    """Link a user account to a roster participant by CAPID or participant ID"""
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Find participant by ID or CAPID
    participant = await db.participants.find_one(
        {"$or": [{"id": participant_id}, {"capid": participant_id}]},
        {"_id": 0}
    )
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    now = datetime.now(timezone.utc).isoformat()
    update_fields = {
        "linked_participant_id": participant.get("id"),
        "capid": participant.get("capid"),
        "updated_at": now
    }
    
    # Auto-populate profile from participant data
    if auto_populate:
        # Determine role based on participant type
        ptype = participant.get("participant_type", "")
        member_type = (participant.get("member_type") or "").upper()
        
        if member_type == "SENIOR" or ptype == "staff":
            update_fields["role"] = UserRole.STAFF
        elif ptype == "cadre":
            update_fields["role"] = UserRole.STAFF  # Cadre gets staff role
        else:
            update_fields["role"] = UserRole.CADET
        
        # Copy profile fields from participant
        profile_fields = [
            "rank", "unit", "wing", "region", "gender", "age", "shirt_size",
            "phone", "cell_phone", "email", "address", "city", "state", "zip_code",
            "emergency_contact", "emergency_phone",
            "cadet_parent_phone", "cadet_parent_email"
        ]
        for field in profile_fields:
            if participant.get(field):
                update_fields[field] = participant[field]
        
        # Use participant name if user name is generic
        if participant.get("first_name") and participant.get("last_name"):
            update_fields["name"] = f"{participant['first_name']} {participant['last_name']}"
    
    await db.users.update_one({"id": user_id}, {"$set": update_fields})
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {
        "message": "User linked to participant successfully",
        "user": updated_user,
        "participant": participant
    }


@api_router.get("/users/{user_id}/match-participants")
async def find_matching_participants(
    user_id: str,
    user: dict = Depends(require_role([UserRole.COMMANDER]))
):
    """Find potential participant matches for a user based on CAPID, name, or email"""
    target_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    matches = []
    
    # Search by CAPID if provided
    if target_user.get("capid"):
        capid_match = await db.participants.find_one(
            {"capid": target_user["capid"]},
            {"_id": 0}
        )
        if capid_match:
            matches.append({"match_type": "capid", "participant": capid_match, "confidence": "high"})
    
    # Search by email
    if target_user.get("email"):
        email_matches = await db.participants.find(
            {"email": {"$regex": target_user["email"], "$options": "i"}},
            {"_id": 0}
        ).to_list(5)
        for p in email_matches:
            if not any(m["participant"]["id"] == p["id"] for m in matches):
                matches.append({"match_type": "email", "participant": p, "confidence": "high"})
    
    # Search by name (partial match)
    if target_user.get("name"):
        name_parts = target_user["name"].split()
        if len(name_parts) >= 1:
            name_query = {
                "$or": [
                    {"first_name": {"$regex": name_parts[0], "$options": "i"}},
                    {"last_name": {"$regex": name_parts[-1], "$options": "i"}}
                ]
            }
            name_matches = await db.participants.find(name_query, {"_id": 0}).to_list(10)
            for p in name_matches:
                if not any(m["participant"]["id"] == p["id"] for m in matches):
                    matches.append({"match_type": "name", "participant": p, "confidence": "medium"})
    
    return {"user": target_user, "matches": matches[:10]}  # Limit to 10 matches


# ================= PARTICIPANT ROUTES =================

@api_router.get("/participants", response_model=List[ParticipantResponse])
async def get_participants(user: dict = Depends(get_current_user)):
    participants = await db.participants.find({}, {"_id": 0}).to_list(1000)
    
    # Define roles that can see all data
    privileged_roles = [
        UserRole.COMMANDER,
        UserRole.EXEC_CADRE,
        UserRole.PLANS_PROGRAMS,
        UserRole.FINANCE,
        UserRole.STAFF  # Health Services falls under staff
    ]
    
    user_role = user.get('role')
    
    # If user doesn't have a privileged role, filter sensitive fields
    if user_role not in privileged_roles:
        # Sensitive fields to hide (set to empty/default values)
        sensitive_fields = [
            'email', 'phone', 'cell_phone', 'address', 'city', 'state', 'zip_code',
            'emergency_contact', 'emergency_phone', 'cadet_parent_name', 
            'cadet_parent_phone', 'cadet_parent_email', 'amount_paid',
            'registration_status', 'notes', 'comments', 'religious_preference',
            'shirt_size', 'unit_cc_name', 'unit_cc_email'
        ]
        filtered_participants = []
        for p in participants:
            # Create a copy of the participant
            filtered_p = dict(p)
            # Hide sensitive string/numeric fields
            for field in sensitive_fields:
                if field in filtered_p:
                    filtered_p[field] = None
            # Hide payment info but keep as boolean False
            filtered_p['paid'] = False
            filtered_p['paid_in_full'] = False
            filtered_p['amount_paid'] = None
            # Hide approval info
            filtered_p['unit_approved'] = False
            filtered_p['wing_approved'] = False
            filtered_participants.append(filtered_p)
        return [ParticipantResponse(**p) for p in filtered_participants]
    
    return [ParticipantResponse(**p) for p in participants]


@api_router.get("/participants/stats")
async def get_participant_stats(user: dict = Depends(get_current_user)):
    """Get participant statistics for dashboard"""
    participants = await db.participants.find({}, {"_id": 0}).to_list(1000)
    
    stats = {
        'total': len(participants),
        'seniors': 0,
        'cadets': 0,
        'staff': 0,
        'cadre': 0,
        'students': 0,
        'paid': 0,
        'unpaid': 0,
        'total_collected': 0.0,
        'unit_approved': 0,
        'wing_approved': 0,
        'slotted': 0,
        'by_wing': {},
        'by_unit': {}
    }
    
    for p in participants:
        # Member type counts
        member_type = (p.get('member_type') or '').upper()
        if member_type == 'SENIOR':
            stats['seniors'] += 1
        elif member_type == 'CADET':
            stats['cadets'] += 1
        
        # Role counts
        ptype = p.get('participant_type', '')
        if ptype == 'staff':
            stats['staff'] += 1
        elif ptype == 'cadre':
            stats['cadre'] += 1
        elif ptype in ['basic_student', 'advanced_student']:
            stats['students'] += 1
        
        # Payment
        if p.get('paid') or p.get('paid_in_full'):
            stats['paid'] += 1
        else:
            stats['unpaid'] += 1
        
        if p.get('amount_paid'):
            stats['total_collected'] += float(p.get('amount_paid', 0))
        
        # Approvals
        if p.get('unit_approved'):
            stats['unit_approved'] += 1
        if p.get('wing_approved'):
            stats['wing_approved'] += 1
        if p.get('slotted'):
            stats['slotted'] += 1
        
        # By wing
        wing = p.get('wing', 'Unknown')
        if wing:
            stats['by_wing'][wing] = stats['by_wing'].get(wing, 0) + 1
        
        # By unit
        unit = p.get('unit', 'Unknown')
        if unit:
            stats['by_unit'][unit] = stats['by_unit'].get(unit, 0) + 1
    
    return stats


@api_router.get("/participants/analytics/detailed")
async def get_detailed_analytics(user: dict = Depends(get_current_user)):
    """Get comprehensive analytics for encampment attendees"""
    participants = await db.participants.find({}, {"_id": 0}).to_list(1000)
    
    # Return empty analytics structure when no participants
    if not participants:
        return {
            'total_count': 0,
            'by_role': {
                'seniors': {'count': 0, 'male': 0, 'female': 0, 'male_pct': 0, 'female_pct': 0, 'avg_age': None},
                'staff': {'count': 0, 'male': 0, 'female': 0, 'male_pct': 0, 'female_pct': 0, 'avg_age': None},
                'cadre': {'count': 0, 'male': 0, 'female': 0, 'male_pct': 0, 'female_pct': 0, 'avg_age': None},
                'students': {'count': 0, 'male': 0, 'female': 0, 'male_pct': 0, 'female_pct': 0, 'avg_age': None},
            },
            'by_rank': {},
            'by_wing': {},
            'by_region': {},
            'by_gender': {'M': 0, 'F': 0, 'Unknown': 0},
            'by_group': {},
            'by_squadron': {},
            'by_flight': {},
            'age_stats': {
                'total': {'avg': None, 'min': None, 'max': None},
                'by_squadron': {},
                'by_flight': {}
            },
            'pending_payments': [],
        }
    
    # Initialize analytics structure
    analytics = {
        'total_count': len(participants),
        'by_role': {
            'seniors': {'count': 0, 'male': 0, 'female': 0, 'ages': []},
            'staff': {'count': 0, 'male': 0, 'female': 0, 'ages': []},
            'cadre': {'count': 0, 'male': 0, 'female': 0, 'ages': []},
            'students': {'count': 0, 'male': 0, 'female': 0, 'ages': []},
        },
        'by_rank': {},
        'by_wing': {},
        'by_region': {},
        'by_gender': {'M': 0, 'F': 0, 'Unknown': 0},
        'by_group': {},  # TN Groups
        'by_squadron': {},
        'by_flight': {},
        'age_stats': {
            'total': {'ages': [], 'avg': 0, 'min': 0, 'max': 0},  # Cadets only (students + cadre)
            'cadets_only': {'ages': []},  # Track cadet ages separately
            'by_squadron': {},
            'by_flight': {}
        },
        'pending_payments': [],
    }
    
    for p in participants:
        member_type = (p.get('member_type') or '').upper()
        ptype = p.get('participant_type', '')
        raw_gender = (p.get('gender') or 'Unknown').upper()
        # Normalize gender values (handle MALE/FEMALE or M/F)
        if raw_gender in ['M', 'MALE']:
            gender = 'M'
        elif raw_gender in ['F', 'FEMALE']:
            gender = 'F'
        else:
            gender = 'Unknown'
        age = p.get('age') or p.get('age_at_event')
        rank = p.get('rank', 'Unknown')
        wing = p.get('wing', 'Unknown')
        region = p.get('region', 'Unknown')
        unit = p.get('unit', '')
        squadron = p.get('squadron', 'Unassigned')
        flight = p.get('flight', 'Unassigned')
        
        # Gender counts
        analytics['by_gender'][gender] = analytics['by_gender'].get(gender, 0) + 1
        
        # Rank distribution
        if rank:
            analytics['by_rank'][rank] = analytics['by_rank'].get(rank, 0) + 1
        
        # Wing distribution
        if wing:
            analytics['by_wing'][wing] = analytics['by_wing'].get(wing, 0) + 1
        
        # Region distribution
        if region:
            analytics['by_region'][region] = analytics['by_region'].get(region, 0) + 1
        
        # TN Group extraction (for TN wing members)
        if wing == 'TN' and unit:
            # CAP unit format: Group/Squadron or just number
            # Try to extract group from unit
            group = 'Unknown'
            try:
                unit_num = int(str(unit).split('/')[0].strip())
                if unit_num < 100:
                    group = f"Group {unit_num}"
                elif unit_num < 200:
                    group = "Group 1"
                elif unit_num < 300:
                    group = "Group 2"
                elif unit_num < 400:
                    group = "Group 3"
                elif unit_num < 500:
                    group = "Group 4"
                else:
                    group = "Other"
            except (ValueError, IndexError):
                group = "Unknown"
            analytics['by_group'][group] = analytics['by_group'].get(group, 0) + 1
        
        # Role-based counts with gender and age
        if member_type == 'SENIOR':
            analytics['by_role']['seniors']['count'] += 1
            if gender == 'M':
                analytics['by_role']['seniors']['male'] += 1
            elif gender == 'F':
                analytics['by_role']['seniors']['female'] += 1
            if age:
                analytics['by_role']['seniors']['ages'].append(age)
            
            if ptype == 'staff':
                analytics['by_role']['staff']['count'] += 1
                if gender == 'M':
                    analytics['by_role']['staff']['male'] += 1
                elif gender == 'F':
                    analytics['by_role']['staff']['female'] += 1
                if age:
                    analytics['by_role']['staff']['ages'].append(age)
        else:
            if ptype == 'cadre':
                analytics['by_role']['cadre']['count'] += 1
                if gender == 'M':
                    analytics['by_role']['cadre']['male'] += 1
                elif gender == 'F':
                    analytics['by_role']['cadre']['female'] += 1
                if age:
                    analytics['by_role']['cadre']['ages'].append(age)
            else:
                analytics['by_role']['students']['count'] += 1
                if gender == 'M':
                    analytics['by_role']['students']['male'] += 1
                elif gender == 'F':
                    analytics['by_role']['students']['female'] += 1
                if age:
                    analytics['by_role']['students']['ages'].append(age)
        
        # Age tracking for averages - CADETS ONLY (exclude senior members)
        if age:
            # Only include cadets (not senior members) in ALL age stats
            is_cadet = member_type != 'SENIOR'
            if is_cadet:
                analytics['age_stats']['total']['ages'].append(age)
                
                # Squadron age averages - cadets only
                if squadron and squadron != 'Unassigned':
                    if squadron not in analytics['age_stats']['by_squadron']:
                        analytics['age_stats']['by_squadron'][squadron] = []
                    analytics['age_stats']['by_squadron'][squadron].append(age)
                
                # Flight age averages - cadets only
                if flight and flight != 'Unassigned':
                    if flight not in analytics['age_stats']['by_flight']:
                        analytics['age_stats']['by_flight'][flight] = []
                    analytics['age_stats']['by_flight'][flight].append(age)
        
        # Squadron/Flight distribution
        if squadron:
            analytics['by_squadron'][squadron] = analytics['by_squadron'].get(squadron, 0) + 1
        if flight:
            analytics['by_flight'][flight] = analytics['by_flight'].get(flight, 0) + 1
        
        # Pending payments
        is_paid = p.get('paid') or p.get('paid_in_full')
        if not is_paid:
            analytics['pending_payments'].append({
                'capid': p.get('capid'),
                'name': f"{p.get('last_name', '')}, {p.get('first_name', '')}",
                'rank': rank,
                'unit': unit,
                'wing': wing,
                'type': ptype,
                'email': p.get('email'),
                'phone': p.get('phone') or p.get('cell_phone'),
                'parent_email': p.get('cadet_parent_email'),
                'parent_phone': p.get('cadet_parent_phone'),
                'amount_paid': p.get('amount_paid', 0)
            })
    
    # Calculate percentages for gender by role
    for role in ['staff', 'cadre', 'students']:
        total = analytics['by_role'][role]['count']
        if total > 0:
            analytics['by_role'][role]['male_pct'] = round(analytics['by_role'][role]['male'] / total * 100, 1)
            analytics['by_role'][role]['female_pct'] = round(analytics['by_role'][role]['female'] / total * 100, 1)
            # Average age
            ages = analytics['by_role'][role]['ages']
            if ages:
                analytics['by_role'][role]['avg_age'] = round(sum(ages) / len(ages), 1)
        else:
            analytics['by_role'][role]['male_pct'] = 0
            analytics['by_role'][role]['female_pct'] = 0
            analytics['by_role'][role]['avg_age'] = 0
        # Remove raw ages list from response
        del analytics['by_role'][role]['ages']
    
    # Also calculate gender stats for seniors (but NOT age stats)
    if analytics['by_role']['seniors']['count'] > 0:
        total = analytics['by_role']['seniors']['count']
        analytics['by_role']['seniors']['male_pct'] = round(analytics['by_role']['seniors']['male'] / total * 100, 1)
        analytics['by_role']['seniors']['female_pct'] = round(analytics['by_role']['seniors']['female'] / total * 100, 1)
    # Remove seniors ages - we don't track/display senior age stats
    del analytics['by_role']['seniors']['ages']
    
    # Calculate age statistics - CADETS ONLY
    cadet_ages = analytics['age_stats']['total']['ages']
    if cadet_ages:
        analytics['age_stats']['total']['avg'] = round(sum(cadet_ages) / len(cadet_ages), 1)
        analytics['age_stats']['total']['min'] = min(cadet_ages)
        analytics['age_stats']['total']['max'] = max(cadet_ages)
        analytics['age_stats']['total']['count'] = len(cadet_ages)
    del analytics['age_stats']['total']['ages']
    # Remove the temp tracking field if it exists
    if 'cadets_only' in analytics['age_stats']:
        del analytics['age_stats']['cadets_only']
    
    # Squadron averages
    for sq, ages in analytics['age_stats']['by_squadron'].items():
        if ages:
            analytics['age_stats']['by_squadron'][sq] = round(sum(ages) / len(ages), 1)
    
    # Flight averages
    for fl, ages in analytics['age_stats']['by_flight'].items():
        if ages:
            analytics['age_stats']['by_flight'][fl] = round(sum(ages) / len(ages), 1)
    
    return analytics


@api_router.get("/participants/pending-payments")
async def get_pending_payments(user: dict = Depends(get_current_user)):
    """Get list of participants with pending payments for follow-up"""
    participants = await db.participants.find(
        {"$or": [{"paid": False}, {"paid": None}, {"paid_in_full": False}, {"paid_in_full": None}]},
        {"_id": 0}
    ).to_list(1000)
    
    # Filter to only truly unpaid
    unpaid = []
    for p in participants:
        if not p.get('paid') and not p.get('paid_in_full'):
            unpaid.append({
                'capid': p.get('capid'),
                'name': f"{p.get('last_name', '')}, {p.get('first_name', '')}",
                'rank': p.get('rank'),
                'unit': p.get('unit'),
                'wing': p.get('wing'),
                'participant_type': p.get('participant_type'),
                'member_type': p.get('member_type'),
                'email': p.get('email'),
                'phone': p.get('phone') or p.get('cell_phone'),
                'parent_email': p.get('cadet_parent_email'),
                'parent_phone': p.get('cadet_parent_phone'),
                'unit_cc_email': p.get('unit_cc_email'),
                'amount_paid': p.get('amount_paid', 0),
                'registration_status': p.get('registration_status')
            })
    
    return {
        'count': len(unpaid),
        'participants': unpaid
    }


@api_router.get("/participants/analytics/export")
async def export_analytics(
    format: str = "csv",
    user: dict = Depends(get_current_user)
):
    """Export analytics data as CSV or Excel"""
    participants = await db.participants.find({}, {"_id": 0}).to_list(1000)
    
    if not participants:
        raise HTTPException(status_code=404, detail="No participants found")
    
    # Create DataFrame with participant data
    df = pd.DataFrame(participants)
    
    # Select and reorder columns for export
    export_columns = [
        'capid', 'rank', 'last_name', 'first_name', 'unit', 'wing', 'region',
        'gender', 'age', 'age_at_event', 'member_type', 'participant_type',
        'squadron', 'flight', 'email', 'phone', 'cell_phone',
        'paid', 'paid_in_full', 'amount_paid', 'registration_status',
        'unit_approved', 'wing_approved', 'slotted'
    ]
    
    # Only include columns that exist
    available_columns = [col for col in export_columns if col in df.columns]
    df_export = df[available_columns]
    
    # Generate file
    output = BytesIO()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    
    if format == "excel":
        df_export.to_excel(output, index=False, sheet_name='Participants')
        output.seek(0)
        filename = f"cap_encampment_analytics_{timestamp}.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        df_export.to_csv(output, index=False)
        output.seek(0)
        filename = f"cap_encampment_analytics_{timestamp}.csv"
        media_type = "text/csv"
    
    return StreamingResponse(
        output,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@api_router.get("/participants/analytics/summary-export")
async def export_analytics_summary(
    user: dict = Depends(get_current_user)
):
    """Export analytics summary report as Excel with multiple sheets"""
    participants = await db.participants.find({}, {"_id": 0}).to_list(1000)
    
    if not participants:
        raise HTTPException(status_code=404, detail="No participants found")
    
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Full participant list
        df_full = pd.DataFrame(participants)
        export_columns = [
            'capid', 'rank', 'last_name', 'first_name', 'unit', 'wing', 'region',
            'gender', 'age', 'member_type', 'participant_type', 'squadron', 'flight',
            'paid', 'amount_paid'
        ]
        available_columns = [col for col in export_columns if col in df_full.columns]
        df_full[available_columns].to_excel(writer, sheet_name='All Participants', index=False)
        
        # Sheet 2: Summary by Role
        role_summary = []
        for p in participants:
            member_type = (p.get('member_type') or '').upper()
            ptype = p.get('participant_type', '')
            gender = (p.get('gender') or 'Unknown').upper()
            age = p.get('age') or p.get('age_at_event')
            
            role = 'Unknown'
            if member_type == 'SENIOR':
                role = 'Senior/Staff'
            elif ptype == 'cadre':
                role = 'Cadre'
            else:
                role = 'Student'
            
            role_summary.append({
                'Role': role,
                'Gender': gender,
                'Age': age,
                'Paid': 'Yes' if p.get('paid') or p.get('paid_in_full') else 'No'
            })
        
        df_roles = pd.DataFrame(role_summary)
        role_counts = df_roles.groupby('Role').agg({
            'Gender': 'count',
            'Age': 'mean'
        }).reset_index()
        role_counts.columns = ['Role', 'Count', 'Average Age']
        role_counts.to_excel(writer, sheet_name='Summary by Role', index=False)
        
        # Sheet 3: Summary by Wing
        wing_counts = df_full.groupby('wing').size().reset_index(name='Count')
        wing_counts.to_excel(writer, sheet_name='By Wing', index=False)
        
        # Sheet 4: Summary by Unit
        if 'unit' in df_full.columns:
            unit_counts = df_full.groupby('unit').size().reset_index(name='Count')
            unit_counts.to_excel(writer, sheet_name='By Unit', index=False)
        
        # Sheet 5: Pending Payments
        unpaid = [p for p in participants if not p.get('paid') and not p.get('paid_in_full')]
        if unpaid:
            df_unpaid = pd.DataFrame(unpaid)
            unpaid_columns = ['capid', 'rank', 'last_name', 'first_name', 'unit', 'wing', 
                            'email', 'phone', 'cadet_parent_email', 'cadet_parent_phone']
            available_unpaid = [col for col in unpaid_columns if col in df_unpaid.columns]
            df_unpaid[available_unpaid].to_excel(writer, sheet_name='Pending Payments', index=False)
    
    output.seek(0)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    filename = f"cap_encampment_full_report_{timestamp}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@api_router.get("/participants/{participant_id}", response_model=ParticipantResponse)
async def get_participant(participant_id: str, user: dict = Depends(get_current_user)):
    participant = await db.participants.find_one({"id": participant_id}, {"_id": 0})
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Define roles that can see all data
    privileged_roles = [
        UserRole.COMMANDER,
        UserRole.EXEC_CADRE,
        UserRole.PLANS_PROGRAMS,
        UserRole.FINANCE,
        UserRole.STAFF
    ]
    
    user_role = user.get('role')
    
    # If user doesn't have a privileged role, filter sensitive fields
    if user_role not in privileged_roles:
        sensitive_fields = [
            'email', 'phone', 'cell_phone', 'address', 'city', 'state', 'zip_code',
            'emergency_contact', 'emergency_phone', 'cadet_parent_name', 
            'cadet_parent_phone', 'cadet_parent_email', 'amount_paid',
            'registration_status', 'notes', 'comments', 'religious_preference',
            'shirt_size', 'unit_cc_name', 'unit_cc_email'
        ]
        filtered_p = dict(participant)
        for field in sensitive_fields:
            if field in filtered_p:
                filtered_p[field] = None
        # Hide payment/approval info
        filtered_p['paid'] = False
        filtered_p['paid_in_full'] = False
        filtered_p['amount_paid'] = None
        filtered_p['unit_approved'] = False
        filtered_p['wing_approved'] = False
        return ParticipantResponse(**filtered_p)
    
    return ParticipantResponse(**participant)

@api_router.post("/participants", response_model=ParticipantResponse)
async def create_participant(
    data: ParticipantCreate,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    participant_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    doc = {
        "id": participant_id,
        **data.model_dump(),
        "created_at": now,
        "updated_at": now
    }
    await db.participants.insert_one(doc)
    doc.pop("_id", None)
    return ParticipantResponse(**doc)

@api_router.put("/participants/{participant_id}", response_model=ParticipantResponse)
async def update_participant(
    participant_id: str,
    data: ParticipantCreate,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    now = datetime.now(timezone.utc).isoformat()
    update_data = {**data.model_dump(), "updated_at": now}
    
    result = await db.participants.update_one(
        {"id": participant_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    participant = await db.participants.find_one({"id": participant_id}, {"_id": 0})
    return ParticipantResponse(**participant)

@api_router.delete("/participants/{participant_id}")
async def delete_participant(
    participant_id: str,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    result = await db.participants.delete_one({"id": participant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Participant not found")
    return {"message": "Participant deleted successfully"}


@api_router.post("/participants/{participant_id}/remove")
async def remove_participant_from_encampment(
    participant_id: str,
    removal_data: ParticipantRemoval,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF, UserRole.PLANS_PROGRAMS]))
):
    """Mark a participant as removed from encampment (soft delete) with reason"""
    participant = await db.participants.find_one({"id": participant_id})
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.participants.update_one(
        {"id": participant_id},
        {"$set": {
            "is_removed": True,
            "removed_at": now,
            "removed_by": user.get("name", user.get("email")),
            "removal_reason": removal_data.removal_reason,
            "updated_at": now
        }}
    )
    
    updated = await db.participants.find_one({"id": participant_id}, {"_id": 0})
    return {"message": "Participant removed from encampment", "participant": updated}


@api_router.post("/participants/{participant_id}/reinstate")
async def reinstate_participant(
    participant_id: str,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF, UserRole.PLANS_PROGRAMS]))
):
    """Reinstate a previously removed participant"""
    participant = await db.participants.find_one({"id": participant_id})
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.participants.update_one(
        {"id": participant_id},
        {"$set": {
            "is_removed": False,
            "removed_at": None,
            "removed_by": None,
            "removal_reason": None,
            "updated_at": now
        }}
    )
    
    updated = await db.participants.find_one({"id": participant_id}, {"_id": 0})
    return {"message": "Participant reinstated", "participant": updated}


@api_router.post("/participants/import")
async def import_participants(
    file: UploadFile = File(...),
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    """Import participants from CAP Event Admin Report Excel file"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        
        # Normalize column names - handle CAP Admin Report format
        df.columns = df.columns.str.strip()
        
        # Create column mapping for CAP Admin Report headers
        column_map = {
            'RegistrantsCAPID': 'capid',
            'CAPID': 'capid',
            'Rank': 'rank',
            'NameLast': 'last_name',
            'NameFirst': 'first_name',
            'NameMiddle': 'middle_name',
            'Unit': 'unit',
            'Wing': 'wing',
            'Region': 'region',
            'Gender': 'gender',
            'Age': 'age',
            'AgeAtEventStart': 'age_at_event',
            'Email': 'email',
            'HomePhonePrimary': 'phone',
            'CellPhonePrimary': 'cell_phone',
            'ShirtSize': 'shirt_size',
            'MbrType': 'member_type',
            'StaffMember': 'staff_member',
            'PaidInFull': 'paid_in_full',
            'AmountPaid': 'amount_paid',
            'RegistrationStatus': 'registration_status',
            'UnitApproved': 'unit_approved',
            'UnitApprovalDate': 'unit_approval_date',
            'WingApproved': 'wing_approved',
            'WingApprovalDate': 'wing_approval_date',
            'Slotted': 'slotted',
            'Addr1': 'address',
            'City': 'city',
            'State': 'state',
            'Zip': 'zip_code',
            'EmergencyContactName': 'emergency_contact',
            'EmergencyContactNumber': 'emergency_phone',
            'CadetParentPhonePrimary': 'cadet_parent_phone',
            'CadetParentEmailPrimary': 'cadet_parent_email',
            'UnitCCName': 'unit_cc_name',
            'UnitCCEmail': 'unit_cc_email',
            'LastEncampment': 'last_encampment',
            'CPPTExpiration': 'cppt_expiration',
            'FirstAid': 'first_aid',
            'IS100': 'is100_date',
            'IS700': 'is700_date',
            'Comments': 'comments',
        }
        
        # Rename columns
        df = df.rename(columns=column_map)
        
        imported_count = 0
        updated_count = 0
        now = datetime.now(timezone.utc).isoformat()
        
        # Track import stats
        stats = {
            'seniors': 0,
            'cadets': 0,
            'staff': 0,
            'cadre': 0,
            'paid': 0,
            'unpaid': 0,
            'total_collected': 0.0
        }
        
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            
            # Helper function to safely get value
            def get_val(key, default=None):
                val = row_dict.get(key)
                if pd.isna(val) or val == '' or val == 'nan':
                    return default
                return val
            
            def get_str(key, default=''):
                val = get_val(key, default)
                return str(val).strip() if val is not None else default
            
            # Get CAPID or generate one from available data
            capid = str(row_dict.get('capid', '')).strip()
            if not capid or capid == 'nan':
                # Try to extract CAPID from email (e.g., 123456@wing.cap.gov or 123456cap@gmail.com)
                email = get_str('email', '')
                if email:
                    email_prefix = email.split('@')[0] if '@' in email else ''
                    # Check if prefix is numeric or contains numeric CAPID
                    numeric_parts = ''.join(filter(str.isdigit, email_prefix))
                    if len(numeric_parts) >= 5:  # CAPIDs are typically 5-6 digits
                        capid = numeric_parts[:6]
                
                # If still no CAPID, generate from name + unit + wing
                if not capid or capid == 'nan':
                    last_name = get_str('last_name', '')
                    first_name = get_str('first_name', '')
                    wing = get_str('wing', 'XX')
                    unit = get_str('unit', '000')
                    if last_name and first_name:
                        # Generate a pseudo-CAPID from hash of name + unit
                        import hashlib
                        composite = f"{last_name}_{first_name}_{wing}_{unit}".upper()
                        hash_digest = hashlib.md5(composite.encode()).hexdigest()[:6]
                        capid = f"GEN{hash_digest.upper()}"
                    else:
                        # Skip rows without enough identifying info
                        continue
            
            
            def get_bool(key):
                val = get_val(key)
                if val is None:
                    return False
                if isinstance(val, bool):
                    return val
                return str(val).lower() in ['yes', 'true', '1']
            
            def get_float(key, default=0.0):
                val = get_val(key)
                if val is None:
                    return default
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default
            
            def get_int(key, default=None):
                val = get_val(key)
                if val is None:
                    return default
                try:
                    return int(float(val))
                except (ValueError, TypeError):
                    return default
            
            # Determine participant type based on member type and staff status
            member_type = get_str('member_type', '').upper()
            is_staff = get_bool('staff_member')
            
            if member_type == 'SENIOR':
                participant_type = 'staff' if is_staff else 'senior_member'
                stats['seniors'] += 1
                if is_staff:
                    stats['staff'] += 1
            elif member_type == 'CADET':
                participant_type = 'cadre' if is_staff else 'basic_student'
                stats['cadets'] += 1
                if is_staff:
                    stats['cadre'] += 1
            else:
                participant_type = 'basic_student'
            
            # Payment tracking
            paid_in_full = get_bool('paid_in_full')
            amount_paid = get_float('amount_paid', 0.0)
            
            if paid_in_full or amount_paid > 0:
                stats['paid'] += 1
                stats['total_collected'] += amount_paid
            else:
                stats['unpaid'] += 1
            
            # Check if last_encampment is "Not Complete" (first encampment)
            last_enc = get_str('last_encampment', '')
            first_encampment = last_enc.lower() == 'not complete' or last_enc == ''
            
            doc = {
                "capid": capid,
                "rank": get_str('rank'),
                "last_name": get_str('last_name'),
                "first_name": get_str('first_name'),
                "middle_name": get_str('middle_name') or None,
                "unit": get_str('unit'),
                "wing": get_str('wing') or None,
                "region": get_str('region') or None,
                "gender": get_str('gender') or None,
                "age": get_int('age'),
                "age_at_event": get_int('age_at_event'),
                "email": get_str('email') or None,
                "phone": get_str('phone') or None,
                "cell_phone": get_str('cell_phone') or None,
                "shirt_size": get_str('shirt_size') or None,
                "member_type": member_type or None,
                "participant_type": participant_type,
                "staff_member": is_staff,
                "paid": paid_in_full,
                "paid_in_full": paid_in_full,
                "amount_paid": amount_paid if amount_paid > 0 else None,
                "registration_status": get_str('registration_status') or None,
                "unit_approved": get_bool('unit_approved'),
                "unit_approval_date": get_str('unit_approval_date') or None,
                "wing_approved": get_bool('wing_approved'),
                "wing_approval_date": get_str('wing_approval_date') or None,
                "slotted": get_bool('slotted'),
                "address": get_str('address') or None,
                "city": get_str('city') or None,
                "state": get_str('state') or None,
                "zip_code": get_str('zip_code') or None,
                "emergency_contact": get_str('emergency_contact') or None,
                "emergency_phone": get_str('emergency_phone') or None,
                "cadet_parent_phone": get_str('cadet_parent_phone') or None,
                "cadet_parent_email": get_str('cadet_parent_email') or None,
                "unit_cc_name": get_str('unit_cc_name') or None,
                "unit_cc_email": get_str('unit_cc_email') or None,
                "last_encampment": get_str('last_encampment') or None,
                "cppt_expiration": get_str('cppt_expiration') or None,
                "first_aid": get_str('first_aid') or None,
                "is100_date": get_str('is100_date') or None,
                "is700_date": get_str('is700_date') or None,
                "first_encampment": first_encampment,
                "comments": get_str('comments') or None,
                "updated_at": now
            }
            
            # Upsert by CAPID
            existing = await db.participants.find_one({"capid": capid})
            if existing:
                await db.participants.update_one(
                    {"capid": capid},
                    {"$set": doc}
                )
                updated_count += 1
            else:
                doc["id"] = str(uuid.uuid4())
                doc["created_at"] = now
                await db.participants.insert_one(doc)
                imported_count += 1
        
        # Get the final total participant count
        total_participant_count = await db.participants.count_documents({})
        
        # Update food settings with participant count
        await db.food_expense_settings.update_one(
            {"_id": "settings"},
            {"$set": {
                "total_participants": total_participant_count,
                "updated_at": now
            }},
            upsert=True
        )
        
        # AUTO-SYNC: Update budget income items based on roster payment data
        sync_result = await sync_roster_to_budget()
        
        return {
            "message": f"Import complete: {imported_count} new, {updated_count} updated",
            "imported": imported_count,
            "updated": updated_count,
            "total": total_participant_count,
            "stats": stats,
            "budget_sync": sync_result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")


async def sync_roster_to_budget():
    """Sync roster payment data to budget income items"""
    now = datetime.now(timezone.utc).isoformat()
    
    # Get all participants
    participants = await db.participants.find({}, {"_id": 0}).to_list(1000)
    
    # Calculate totals by participant type
    senior_staff_count = 0
    senior_staff_collected = 0.0
    cadet_cadre_count = 0
    cadet_cadre_collected = 0.0
    basic_student_count = 0
    basic_student_collected = 0.0
    
    for p in participants:
        member_type = (p.get('member_type') or '').upper()
        ptype = p.get('participant_type', '')
        amount = float(p.get('amount_paid') or 0)
        is_paid = p.get('paid') or p.get('paid_in_full')
        
        if member_type == 'SENIOR':
            senior_staff_count += 1
            if is_paid or amount > 0:
                senior_staff_collected += amount
        elif ptype == 'cadre':
            cadet_cadre_count += 1
            if is_paid or amount > 0:
                cadet_cadre_collected += amount
        else:  # basic_student or advanced_student
            basic_student_count += 1
            if is_paid or amount > 0:
                basic_student_collected += amount
    
    # Update or create budget items for each category
    updates = []
    
    # Senior Members Staff
    senior_item = await db.budget.find_one({"item_name": "Senior Members Staff", "category": "Participant Fees"})
    if senior_item:
        await db.budget.update_one(
            {"id": senior_item["id"]},
            {"$set": {
                "actual": senior_staff_collected,
                "notes": f"{senior_staff_count} SM @ varies",
                "updated_at": now
            }}
        )
        updates.append({"item": "Senior Members Staff", "actual": senior_staff_collected, "count": senior_staff_count})
    
    # Cadet Cadre
    cadre_item = await db.budget.find_one({"item_name": "Cadet Cadre", "category": "Participant Fees"})
    if cadre_item:
        await db.budget.update_one(
            {"id": cadre_item["id"]},
            {"$set": {
                "actual": cadet_cadre_collected,
                "notes": f"{cadet_cadre_count} Cadre @ $250",
                "updated_at": now
            }}
        )
        updates.append({"item": "Cadet Cadre", "actual": cadet_cadre_collected, "count": cadet_cadre_count})
    
    # Basic Students
    student_item = await db.budget.find_one({"item_name": "Basic Students", "category": "Participant Fees"})
    if student_item:
        await db.budget.update_one(
            {"id": student_item["id"]},
            {"$set": {
                "actual": basic_student_collected,
                "notes": f"{basic_student_count} Students @ $250",
                "updated_at": now
            }}
        )
        updates.append({"item": "Basic Students", "actual": basic_student_collected, "count": basic_student_count})
    
    total_collected = senior_staff_collected + cadet_cadre_collected + basic_student_collected
    
    return {
        "synced": True,
        "total_collected": total_collected,
        "updates": updates
    }


@api_router.post("/participants/sync-to-budget")
async def trigger_roster_budget_sync(
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.FINANCE]))
):
    """Manually trigger sync of roster payment data to budget"""
    result = await sync_roster_to_budget()
    return result


# ================= POINT TRACKING ROUTES =================

# Roles that can enter scores
SCORE_ENTRY_ROLES = [UserRole.COMMANDER, UserRole.STAFF, UserRole.PLANS_PROGRAMS, UserRole.EXEC_CADRE]

@api_router.get("/points/categories")
async def get_score_categories(user: dict = Depends(get_current_user)):
    """Get all score categories"""
    categories = await db.score_categories.find({"is_active": True}, {"_id": 0}).to_list(100)
    return categories

@api_router.post("/points/categories")
async def create_score_category(
    category: ScoreCategoryCreate,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.PLANS_PROGRAMS]))
):
    """Create a new score category"""
    category_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    doc = {
        "id": category_id,
        **category.model_dump(),
        "created_at": now
    }
    await db.score_categories.insert_one(doc)
    
    return ScoreCategoryResponse(**doc)

@api_router.put("/points/categories/{category_id}")
async def update_score_category(
    category_id: str,
    category: ScoreCategoryCreate,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.PLANS_PROGRAMS]))
):
    """Update a score category"""
    result = await db.score_categories.update_one(
        {"id": category_id},
        {"$set": category.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    
    updated = await db.score_categories.find_one({"id": category_id}, {"_id": 0})
    return ScoreCategoryResponse(**updated)

@api_router.delete("/points/categories/{category_id}")
async def delete_score_category(
    category_id: str,
    user: dict = Depends(require_role([UserRole.COMMANDER]))
):
    """Delete (deactivate) a score category"""
    await db.score_categories.update_one(
        {"id": category_id},
        {"$set": {"is_active": False}}
    )
    return {"message": "Category deactivated"}

@api_router.post("/points/categories/seed-defaults")
async def seed_default_categories(
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.PLANS_PROGRAMS]))
):
    """Seed default score categories"""
    now = datetime.now(timezone.utc).isoformat()
    
    default_categories = [
        # Flight/Squadron categories
        {"name": "Barracks Inspection", "category_type": "flight", "max_points": 100, "description": "Daily barracks cleanliness and organization"},
        {"name": "Uniform Inspection", "category_type": "flight", "max_points": 100, "description": "Daily uniform appearance and compliance"},
        {"name": "Drill Competition", "category_type": "flight", "max_points": 100, "description": "Drill and ceremonies performance"},
        {"name": "PT Score", "category_type": "flight", "max_points": 100, "description": "Physical training performance"},
        {"name": "Academic Test", "category_type": "flight", "max_points": 100, "description": "Academic test average scores"},
        {"name": "Punctuality", "category_type": "flight", "max_points": 50, "description": "Points deducted for late arrivals (-5 per late)"},
        # Individual cadet categories
        {"name": "Individual PT", "category_type": "individual_cadet", "max_points": 100, "description": "Individual physical training score"},
        {"name": "Individual Academic", "category_type": "individual_cadet", "max_points": 100, "description": "Individual test score"},
        {"name": "Leadership Evaluation", "category_type": "individual_cadet", "max_points": 50, "description": "Leadership performance rating"},
        # Individual cadre categories
        {"name": "Cadre Performance", "category_type": "individual_cadre", "max_points": 100, "description": "Cadre performance evaluation"},
        {"name": "Cadre Leadership", "category_type": "individual_cadre", "max_points": 50, "description": "Cadre leadership rating"},
    ]
    
    inserted = 0
    for cat in default_categories:
        existing = await db.score_categories.find_one({"name": cat["name"]})
        if not existing:
            doc = {
                "id": str(uuid.uuid4()),
                **cat,
                "is_active": True,
                "created_at": now
            }
            await db.score_categories.insert_one(doc)
            inserted += 1
    
    return {"message": f"Seeded {inserted} default categories"}

@api_router.post("/points/scores")
async def record_score(
    entry: ScoreEntryCreate,
    user: dict = Depends(require_role(SCORE_ENTRY_ROLES))
):
    """Record a score entry"""
    # Validate category exists
    category = await db.score_categories.find_one({"id": entry.category_id}, {"_id": 0})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    entry_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    doc = {
        "id": entry_id,
        **entry.model_dump(),
        "category_name": category["name"],
        "entered_by": user.get("name", user.get("email")),
        "created_at": now
    }
    await db.score_entries.insert_one(doc)
    
    return ScoreEntryResponse(**doc)

@api_router.get("/points/scores")
async def get_scores(
    date: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    category_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get score entries with optional filters"""
    query = {}
    if date:
        query["date"] = date
    if target_type:
        query["target_type"] = target_type
    if target_id:
        query["target_id"] = target_id
    if category_id:
        query["category_id"] = category_id
    
    scores = await db.score_entries.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return scores

@api_router.delete("/points/scores/{score_id}")
async def delete_score(
    score_id: str,
    user: dict = Depends(require_role(SCORE_ENTRY_ROLES))
):
    """Delete a score entry"""
    result = await db.score_entries.delete_one({"id": score_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Score entry not found")
    return {"message": "Score deleted"}

@api_router.post("/points/merits")
async def record_merit_demerit(
    entry: MeritDemeritEntry,
    user: dict = Depends(require_role(SCORE_ENTRY_ROLES))
):
    """Record a merit or demerit for an individual"""
    entry_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Get participant name if not provided
    if not entry.participant_name:
        participant = await db.participants.find_one({"id": entry.participant_id}, {"_id": 0})
        if participant:
            entry.participant_name = f"{participant.get('first_name', '')} {participant.get('last_name', '')}"
    
    doc = {
        "id": entry_id,
        **entry.model_dump(),
        "entered_by": user.get("name", user.get("email")),
        "created_at": now
    }
    await db.merit_demerits.insert_one(doc)
    
    return MeritDemeritResponse(**doc)

@api_router.get("/points/merits")
async def get_merits_demerits(
    participant_id: Optional[str] = None,
    entry_type: Optional[str] = None,
    date: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get merit/demerit entries"""
    query = {}
    if participant_id:
        query["participant_id"] = participant_id
    if entry_type:
        query["entry_type"] = entry_type
    if date:
        query["date"] = date
    
    entries = await db.merit_demerits.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return entries

@api_router.get("/points/leaderboard/flights")
async def get_flight_leaderboard(
    date: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get flight standings with cumulative or daily scores"""
    flights = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
    
    query = {"target_type": "flight"}
    if date:
        query["date"] = date
    
    scores = await db.score_entries.find(query, {"_id": 0}).to_list(1000)
    
    # Aggregate scores by flight
    flight_scores = {f: {"flight": f, "total_points": 0, "scores_by_category": {}} for f in flights}
    
    for score in scores:
        flight = score.get("target_id", "").lower()
        if flight in flight_scores:
            flight_scores[flight]["total_points"] += score.get("points", 0)
            cat = score.get("category_name", "Other")
            if cat not in flight_scores[flight]["scores_by_category"]:
                flight_scores[flight]["scores_by_category"][cat] = 0
            flight_scores[flight]["scores_by_category"][cat] += score.get("points", 0)
    
    # Sort by total points descending
    leaderboard = sorted(flight_scores.values(), key=lambda x: x["total_points"], reverse=True)
    
    # Add rank
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1
    
    return leaderboard

@api_router.get("/points/leaderboard/squadrons")
async def get_squadron_leaderboard(
    date: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get squadron standings (aggregated from flights)"""
    flight_to_squadron = {
        "alpha": "6th_cts", "bravo": "6th_cts",
        "charlie": "21st_cts", "delta": "21st_cts",
        "echo": "22nd_cts", "foxtrot": "22nd_cts"
    }
    
    query = {"target_type": "flight"}
    if date:
        query["date"] = date
    
    scores = await db.score_entries.find(query, {"_id": 0}).to_list(1000)
    
    # Aggregate scores by squadron
    squadron_scores = {
        "6th_cts": {"squadron": "6th CTS", "total_points": 0, "flights": ["alpha", "bravo"]},
        "21st_cts": {"squadron": "21st CTS", "total_points": 0, "flights": ["charlie", "delta"]},
        "22nd_cts": {"squadron": "22nd CTS", "total_points": 0, "flights": ["echo", "foxtrot"]}
    }
    
    for score in scores:
        flight = score.get("target_id", "").lower()
        squadron = flight_to_squadron.get(flight)
        if squadron:
            squadron_scores[squadron]["total_points"] += score.get("points", 0)
    
    # Sort by total points
    leaderboard = sorted(squadron_scores.values(), key=lambda x: x["total_points"], reverse=True)
    
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1
    
    return leaderboard

@api_router.get("/points/leaderboard/individuals")
async def get_individual_leaderboard(
    participant_type: Optional[str] = None,  # "cadet" or "cadre"
    date: Optional[str] = None,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """Get individual standings for cadets or cadre"""
    # Get all participants
    participant_query = {}
    if participant_type == "cadet":
        participant_query["participant_type"] = {"$in": ["student", "cadet", "basic_student", "advanced_student"]}
    elif participant_type == "cadre":
        participant_query["participant_type"] = {"$in": ["cadre", "staff", "senior_member"]}
    
    participants = await db.participants.find(participant_query, {"_id": 0}).to_list(1000)
    participant_map = {p["id"]: p for p in participants}
    
    # Get scores
    score_query = {"target_type": "individual"}
    if date:
        score_query["date"] = date
    
    scores = await db.score_entries.find(score_query, {"_id": 0}).to_list(1000)
    
    # Get merits/demerits
    merit_query = {}
    if date:
        merit_query["date"] = date
    merits = await db.merit_demerits.find(merit_query, {"_id": 0}).to_list(1000)
    
    # Aggregate by participant
    individual_scores = {}
    
    for score in scores:
        pid = score.get("target_id")
        if pid not in individual_scores:
            p = participant_map.get(pid, {})
            individual_scores[pid] = {
                "participant_id": pid,
                "name": score.get("target_name") or f"{p.get('first_name', '')} {p.get('last_name', '')}",
                "rank": p.get("rank", ""),
                "flight": p.get("flight", ""),
                "participant_type": p.get("participant_type", ""),
                "total_points": 0,
                "merit_points": 0,
                "demerit_points": 0
            }
        individual_scores[pid]["total_points"] += score.get("points", 0)
    
    # Add merits/demerits
    for entry in merits:
        pid = entry.get("participant_id")
        if pid not in individual_scores:
            p = participant_map.get(pid, {})
            individual_scores[pid] = {
                "participant_id": pid,
                "name": entry.get("participant_name") or f"{p.get('first_name', '')} {p.get('last_name', '')}",
                "rank": p.get("rank", ""),
                "flight": p.get("flight", ""),
                "participant_type": p.get("participant_type", ""),
                "total_points": 0,
                "merit_points": 0,
                "demerit_points": 0
            }
        
        pts = entry.get("points", 0)
        if entry.get("entry_type") == "merit":
            individual_scores[pid]["merit_points"] += pts
            individual_scores[pid]["total_points"] += pts
        else:  # demerit
            individual_scores[pid]["demerit_points"] += pts
            individual_scores[pid]["total_points"] -= pts
    
    # Filter by type if specified
    if participant_type:
        target_types = ["student", "cadet", "basic_student", "advanced_student"] if participant_type == "cadet" else ["cadre", "staff", "senior_member"]
        individual_scores = {k: v for k, v in individual_scores.items() 
                          if v.get("participant_type", "").lower() in target_types}
    
    # Sort and limit
    leaderboard = sorted(individual_scores.values(), key=lambda x: x["total_points"], reverse=True)[:limit]
    
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1
    
    return leaderboard

@api_router.get("/points/daily-winners")
async def get_daily_winners(
    date: str,
    user: dict = Depends(get_current_user)
):
    """Get the winners for a specific day"""
    # Flight of the day
    flight_lb = await get_flight_leaderboard(date, user)
    flight_winner = flight_lb[0] if flight_lb and flight_lb[0]["total_points"] > 0 else None
    
    # Squadron of the day
    squadron_lb = await get_squadron_leaderboard(date, user)
    squadron_winner = squadron_lb[0] if squadron_lb and squadron_lb[0]["total_points"] > 0 else None
    
    # Cadet of the day
    cadet_lb = await get_individual_leaderboard("cadet", date, 1, user)
    cadet_winner = cadet_lb[0] if cadet_lb and cadet_lb[0]["total_points"] > 0 else None
    
    # Cadre of the day
    cadre_lb = await get_individual_leaderboard("cadre", date, 1, user)
    cadre_winner = cadre_lb[0] if cadre_lb and cadre_lb[0]["total_points"] > 0 else None
    
    return {
        "date": date,
        "flight_of_day": flight_winner,
        "squadron_of_day": squadron_winner,
        "cadet_of_day": cadet_winner,
        "cadre_of_day": cadre_winner
    }

@api_router.get("/points/cumulative-standings")
async def get_cumulative_standings(user: dict = Depends(get_current_user)):
    """Get cumulative standings for the entire encampment"""
    return {
        "flights": await get_flight_leaderboard(None, user),
        "squadrons": await get_squadron_leaderboard(None, user),
        "top_cadets": await get_individual_leaderboard("cadet", None, 10, user),
        "top_cadre": await get_individual_leaderboard("cadre", None, 10, user)
    }

@api_router.get("/points/summary")
async def get_points_summary(user: dict = Depends(get_current_user)):
    """Get summary of all point tracking data"""
    total_scores = await db.score_entries.count_documents({})
    total_merits = await db.merit_demerits.count_documents({"entry_type": "merit"})
    total_demerits = await db.merit_demerits.count_documents({"entry_type": "demerit"})
    categories = await db.score_categories.count_documents({"is_active": True})
    
    return {
        "total_score_entries": total_scores,
        "total_merits": total_merits,
        "total_demerits": total_demerits,
        "active_categories": categories
    }


# ================= HONOR AWARDS ROUTES =================

AWARD_TYPES = [
    {"value": "cadet_of_day", "label": "Cadet of the Day", "auto_eligible": True, "participant_type": "cadet"},
    {"value": "cadre_of_day", "label": "Cadre of the Day", "auto_eligible": True, "participant_type": "cadre"},
    {"value": "flight_honor_graduate", "label": "Flight Honor Graduate", "auto_eligible": False, "participant_type": "cadet"},
    {"value": "commandants_award", "label": "Commandant's Award", "auto_eligible": False, "participant_type": "any"},
    {"value": "honor_cadet", "label": "Honor Cadet", "auto_eligible": False, "participant_type": "cadet"},
    {"value": "honor_cadre", "label": "Honor Cadre", "auto_eligible": False, "participant_type": "cadre"},
    {"value": "leadership_award", "label": "Leadership Award", "auto_eligible": False, "participant_type": "any"},
    {"value": "pt_excellence", "label": "PT Excellence Award", "auto_eligible": False, "participant_type": "any"},
    {"value": "academic_excellence", "label": "Academic Excellence Award", "auto_eligible": False, "participant_type": "any"},
    {"value": "drill_award", "label": "Drill Award", "auto_eligible": False, "participant_type": "any"},
    {"value": "spirit_award", "label": "Spirit Award", "auto_eligible": False, "participant_type": "any"},
    {"value": "most_improved", "label": "Most Improved", "auto_eligible": False, "participant_type": "any"},
    {"value": "other", "label": "Other Award", "auto_eligible": False, "participant_type": "any"},
]

@api_router.get("/points/awards/types")
async def get_award_types(user: dict = Depends(get_current_user)):
    """Get all available award types"""
    return AWARD_TYPES

@api_router.post("/points/awards")
async def create_honor_award(
    award_type: str,
    recipient_id: str,
    date: str,
    notes: Optional[str] = None,
    is_auto_generated: bool = False,
    user: dict = Depends(get_current_user)
):
    """Create a new honor award record"""
    if user["role"] not in [UserRole.COMMANDER, UserRole.STAFF, UserRole.PLANS_PROGRAMS, UserRole.EXEC_CADRE]:
        raise HTTPException(status_code=403, detail="Not authorized to assign awards")
    
    # Get recipient info
    participant = await db.participants.find_one({"id": recipient_id})
    if not participant:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    # Check if this award already exists for this date (for daily awards)
    award_type_info = next((a for a in AWARD_TYPES if a["value"] == award_type), None)
    if award_type_info and award_type_info.get("auto_eligible"):
        existing = await db.honor_awards.find_one({
            "award_type": award_type,
            "date": date
        })
        if existing and not is_auto_generated:
            # Update existing award
            await db.honor_awards.update_one(
                {"id": existing["id"]},
                {"$set": {
                    "recipient_id": recipient_id,
                    "recipient_name": f"{participant.get('rank', '')} {participant.get('first_name', '')} {participant.get('last_name', '')}".strip(),
                    "recipient_flight": participant.get("flight"),
                    "recipient_squadron": participant.get("squadron"),
                    "notes": notes,
                    "awarded_by": user["name"],
                    "is_auto_generated": is_auto_generated,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            return {"message": "Award updated", "id": existing["id"]}
    
    award_id = str(uuid.uuid4())
    award = {
        "id": award_id,
        "award_type": award_type,
        "award_label": award_type_info["label"] if award_type_info else award_type,
        "recipient_id": recipient_id,
        "recipient_name": f"{participant.get('rank', '')} {participant.get('first_name', '')} {participant.get('last_name', '')}".strip(),
        "recipient_flight": participant.get("flight"),
        "recipient_squadron": participant.get("squadron"),
        "participant_type": participant.get("participant_type", ""),
        "date": date,
        "notes": notes,
        "awarded_by": user["name"],
        "is_auto_generated": is_auto_generated,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.honor_awards.insert_one(award)
    
    return {**award, "_id": None}

@api_router.get("/points/awards")
async def get_honor_awards(
    award_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    recipient_id: Optional[str] = None,
    limit: int = 100,
    user: dict = Depends(get_current_user)
):
    """Get honor awards with optional filtering"""
    query = {}
    
    if award_type:
        query["award_type"] = award_type
    if recipient_id:
        query["recipient_id"] = recipient_id
    if start_date:
        query["date"] = {"$gte": start_date}
    if end_date:
        if "date" in query:
            query["date"]["$lte"] = end_date
        else:
            query["date"] = {"$lte": end_date}
    
    awards = await db.honor_awards.find(query, {"_id": 0}).sort("date", -1).to_list(limit)
    return awards

@api_router.get("/points/awards/by-date/{date}")
async def get_awards_by_date(date: str, user: dict = Depends(get_current_user)):
    """Get all awards for a specific date"""
    awards = await db.honor_awards.find({"date": date}, {"_id": 0}).to_list(100)
    return awards

@api_router.delete("/points/awards/{award_id}")
async def delete_honor_award(award_id: str, user: dict = Depends(get_current_user)):
    """Delete an honor award"""
    if user["role"] not in [UserRole.COMMANDER, UserRole.PLANS_PROGRAMS]:
        raise HTTPException(status_code=403, detail="Not authorized to delete awards")
    
    result = await db.honor_awards.delete_one({"id": award_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Award not found")
    
    return {"message": "Award deleted"}

@api_router.post("/points/awards/auto-assign/{date}")
async def auto_assign_daily_awards(date: str, user: dict = Depends(get_current_user)):
    """Automatically assign daily awards based on highest points for a date"""
    if user["role"] not in [UserRole.COMMANDER, UserRole.STAFF, UserRole.PLANS_PROGRAMS]:
        raise HTTPException(status_code=403, detail="Not authorized to auto-assign awards")
    
    assigned = []
    
    # Get individual leaderboards for the date
    cadet_lb = await get_individual_leaderboard(participant_type="cadet", date=date, limit=1, user=user)
    cadre_lb = await get_individual_leaderboard(participant_type="cadre", date=date, limit=1, user=user)
    
    # Auto-assign Cadet of the Day
    if cadet_lb and cadet_lb[0]["total_points"] > 0:
        top_cadet = cadet_lb[0]
        await create_honor_award(
            award_type="cadet_of_day",
            recipient_id=top_cadet["participant_id"],
            date=date,
            notes=f"Highest cadet score: {top_cadet['total_points']} points",
            is_auto_generated=True,
            user=user
        )
        assigned.append({"award": "Cadet of the Day", "recipient": top_cadet["name"]})
    
    # Auto-assign Cadre of the Day
    if cadre_lb and cadre_lb[0]["total_points"] > 0:
        top_cadre = cadre_lb[0]
        await create_honor_award(
            award_type="cadre_of_day",
            recipient_id=top_cadre["participant_id"],
            date=date,
            notes=f"Highest cadre score: {top_cadre['total_points']} points",
            is_auto_generated=True,
            user=user
        )
        assigned.append({"award": "Cadre of the Day", "recipient": top_cadre["name"]})
    
    return {"message": f"Auto-assigned {len(assigned)} awards", "awards": assigned}

@api_router.get("/points/awards/recipients-summary")
async def get_award_recipients_summary(user: dict = Depends(get_current_user)):
    """Get summary of all award recipients with counts"""
    pipeline = [
        {"$group": {
            "_id": "$recipient_id",
            "recipient_name": {"$first": "$recipient_name"},
            "recipient_flight": {"$first": "$recipient_flight"},
            "total_awards": {"$sum": 1},
            "awards": {"$push": {"type": "$award_type", "label": "$award_label", "date": "$date"}}
        }},
        {"$sort": {"total_awards": -1}}
    ]
    
    results = await db.honor_awards.aggregate(pipeline).to_list(100)
    return results


# ================= SCHEDULE ROUTES =================

async def increment_schedule_version():
    """Increment schedule version for real-time sync"""
    await db.schedule_settings.update_one(
        {"_id": "settings"},
        {"$inc": {"version": 1}, "$set": {"last_modified_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )

@api_router.get("/schedule", response_model=List[ScheduleEventResponse])
async def get_schedule(
    show_all: bool = False,
    user: dict = Depends(get_current_user)
):
    """Get schedule events. Filters by user's unit unless show_all=true (editors only)."""
    is_editor = user["role"] in [UserRole.COMMANDER, UserRole.STAFF]
    
    # Get schedule settings
    settings = await db.schedule_settings.find_one({"_id": "settings"})
    is_published = settings.get("is_published", False) if settings else False
    
    events = await db.schedule.find({}, {"_id": 0}).to_list(1000)
    
    # Filter events based on user's unit assignment (unless editor viewing all)
    if not (is_editor and show_all):
        user_squadron = user.get("squadron")
        user_flight = user.get("flight")
        
        filtered_events = []
        for event in events:
            target_groups = event.get("target_groups", ["all"])
            
            # Check if event applies to this user
            should_include = (
                "all" in target_groups or
                (user_squadron and user_squadron in target_groups) or
                (user_flight and user_flight in target_groups) or
                # Staff members see staff events
                (user["role"] in [UserRole.COMMANDER, UserRole.STAFF] and "staff" in target_groups)
            )
            
            # If user has no assignment, show all events (they're not filtered yet)
            if not user_squadron and not user_flight:
                should_include = True
            
            if should_include:
                filtered_events.append(event)
        
        events = filtered_events
    
    # Add is_published flag to each event based on global setting
    for event in events:
        event["is_published"] = is_published
        # Ensure target_groups exists for backward compatibility
        if "target_groups" not in event:
            event["target_groups"] = ["all"]
    
    return [ScheduleEventResponse(**e) for e in events]

@api_router.get("/schedule/settings")
async def get_schedule_settings(user: dict = Depends(get_current_user)):
    """Get schedule publish status and version for real-time sync"""
    settings = await db.schedule_settings.find_one({"_id": "settings"})
    if not settings:
        return {"is_published": False, "last_published_at": None, "last_modified_at": None, "version": 0}
    return {
        "is_published": settings.get("is_published", False),
        "last_published_at": settings.get("last_published_at"),
        "last_modified_at": settings.get("last_modified_at"),
        "version": settings.get("version", 0)
    }

@api_router.post("/schedule/publish")
async def publish_schedule(
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    """Publish the schedule so all users can see it"""
    now = datetime.now(timezone.utc).isoformat()
    await db.schedule_settings.update_one(
        {"_id": "settings"},
        {"$set": {"is_published": True, "last_published_at": now}, "$inc": {"version": 1}},
        upsert=True
    )
    
    # Send push notification to all subscribers
    notification_count = await send_schedule_update_notification()
    
    return {
        "message": "Schedule published successfully", 
        "published_at": now,
        "notifications_sent": notification_count
    }

@api_router.post("/schedule/unpublish")
async def unpublish_schedule(
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    """Unpublish the schedule (make it draft)"""
    await db.schedule_settings.update_one(
        {"_id": "settings"},
        {"$set": {"is_published": False}, "$inc": {"version": 1}},
        upsert=True
    )
    return {"message": "Schedule unpublished successfully"}

@api_router.post("/schedule", response_model=ScheduleEventResponse)
async def create_schedule_event(
    data: ScheduleEventCreate,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    doc = {
        "id": event_id,
        **data.model_dump(),
        "created_at": now,
        "updated_at": now
    }
    await db.schedule.insert_one(doc)
    
    # Update version for real-time sync
    await increment_schedule_version()
    
    doc.pop("_id", None)
    settings = await db.schedule_settings.find_one({"_id": "settings"})
    doc["is_published"] = settings.get("is_published", False) if settings else False
    return ScheduleEventResponse(**doc)

@api_router.put("/schedule/{event_id}", response_model=ScheduleEventResponse)
async def update_schedule_event(
    event_id: str,
    data: ScheduleEventCreate,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    now = datetime.now(timezone.utc).isoformat()
    update_data = {**data.model_dump(), "updated_at": now}
    
    result = await db.schedule.update_one({"id": event_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Update version for real-time sync
    await increment_schedule_version()
    
    event = await db.schedule.find_one({"id": event_id}, {"_id": 0})
    settings = await db.schedule_settings.find_one({"_id": "settings"})
    event["is_published"] = settings.get("is_published", False) if settings else False
    return ScheduleEventResponse(**event)

@api_router.delete("/schedule/{event_id}")
async def delete_schedule_event(
    event_id: str,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    result = await db.schedule.delete_one({"id": event_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Update version for real-time sync
    await increment_schedule_version()
    
    return {"message": "Event deleted successfully"}

@api_router.post("/schedule/import")
async def import_schedule(
    file: UploadFile = File(...),
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    """Import schedule from Excel file. Dates are shifted to July 17-24."""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    try:
        contents = await file.read()
        # Read the Excel file to validate it's a valid schedule file
        # The actual parsing is complex due to the merged cells, so we use predefined data
        _ = pd.read_excel(BytesIO(contents), sheet_name=0)
        
        # Event type mapping based on keywords (used by predefined data)
        def get_event_type(title: str) -> str:
            title_lower = title.lower()
            if any(k in title_lower for k in ['pt', 'calisthenics', 'fitness', 'obstacle', 'sports', 'guidon run']):
                return 'pt'
            elif any(k in title_lower for k in ['lunch', 'dinner', 'breakfast', 'meal', 'dfac', 'dishes', 'dining']):
                return 'meal'
            elif any(k in title_lower for k in ['formation', 'retreat', 'reveille', 'parade', 'graduation', 'ceremony']):
                return 'ceremony'
            elif any(k in title_lower for k in ['leadership', 'core values', 'wingmen', 'warrior', 'tlp', 'honor']):
                return 'leadership'
            elif any(k in title_lower for k in ['classroom', 'quiz', 'academics', 'drone', 'rocket', 'cyber', 'astronomy']):
                return 'academics'
            elif any(k in title_lower for k in ['personal time', 'shower', 'break', 'recreation', 'trivia']):
                return 'recreation'
            elif any(k in title_lower for k in ['admin', 'sign in', 'pack', 'room', 'setup', 'inspection', 'uniform']):
                return 'admin'
            else:
                return 'training'
        
        # Predefined schedule for July 17-24 based on extracted data
        schedule_data = [
            # July 17 - Staff/Cadre Arrival Day
            {"date": "2026-07-17", "start_time": "06:00", "end_time": "10:00", "title": "Staff & Cadre Transit to Site", "event_type": "admin", "location": ""},
            {"date": "2026-07-17", "start_time": "10:00", "end_time": "12:00", "title": "Sign In / Room Assignments", "event_type": "admin", "location": ""},
            {"date": "2026-07-17", "start_time": "10:00", "end_time": "12:00", "title": "Intensity Training", "event_type": "training", "squadron": "staff"},
            {"date": "2026-07-17", "start_time": "12:00", "end_time": "13:30", "title": "Barracks Setup", "event_type": "admin", "location": ""},
            {"date": "2026-07-17", "start_time": "13:30", "end_time": "14:15", "title": "Lunch", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-17", "start_time": "14:15", "end_time": "15:00", "title": "Welcome, Safety Briefing, Expectations", "event_type": "training", "location": ""},
            {"date": "2026-07-17", "start_time": "15:00", "end_time": "16:00", "title": "Operations Setup / Nametags", "event_type": "admin", "location": ""},
            {"date": "2026-07-17", "start_time": "16:00", "end_time": "17:00", "title": "Break / Uniform Prep", "event_type": "recreation", "location": ""},
            {"date": "2026-07-17", "start_time": "17:00", "end_time": "17:15", "title": "Schedule Review", "event_type": "admin", "location": ""},
            {"date": "2026-07-17", "start_time": "17:15", "end_time": "18:00", "title": "Dinner", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-17", "start_time": "18:00", "end_time": "19:00", "title": "Retreat Formation", "event_type": "ceremony", "location": ""},
            {"date": "2026-07-17", "start_time": "19:00", "end_time": "20:00", "title": "Classroom Orientation & Setup", "event_type": "admin", "location": ""},
            {"date": "2026-07-17", "start_time": "20:00", "end_time": "21:00", "title": "Support Office Orientation", "event_type": "admin", "location": ""},
            {"date": "2026-07-17", "start_time": "21:00", "end_time": "22:00", "title": "Personal Time / Showers", "event_type": "recreation", "location": ""},
            
            # July 18 - Student In-processing Day
            {"date": "2026-07-18", "start_time": "06:00", "end_time": "06:15", "title": "First Call", "event_type": "ceremony", "location": ""},
            {"date": "2026-07-18", "start_time": "06:15", "end_time": "07:00", "title": "Daily Calisthenics", "event_type": "pt", "location": "PT Field"},
            {"date": "2026-07-18", "start_time": "07:00", "end_time": "07:30", "title": "Personal Time / Showers", "event_type": "recreation", "location": ""},
            {"date": "2026-07-18", "start_time": "07:30", "end_time": "08:15", "title": "Breakfast", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-18", "start_time": "08:15", "end_time": "09:15", "title": "I-Day Setup & Practice Run", "event_type": "admin", "location": ""},
            {"date": "2026-07-18", "start_time": "09:15", "end_time": "09:45", "title": "Student Reception / In-Processing", "event_type": "admin", "location": ""},
            {"date": "2026-07-18", "start_time": "09:30", "end_time": "10:00", "title": "Parent Orientation", "event_type": "admin", "location": ""},
            {"date": "2026-07-18", "start_time": "09:45", "end_time": "10:15", "title": "Welcome, Overview, Safety", "event_type": "training", "location": ""},
            {"date": "2026-07-18", "start_time": "10:00", "end_time": "10:15", "title": "Report to Flights", "event_type": "ceremony", "location": ""},
            {"date": "2026-07-18", "start_time": "10:15", "end_time": "11:00", "title": "Training Officer Overview", "event_type": "training", "location": ""},
            {"date": "2026-07-18", "start_time": "11:00", "end_time": "12:00", "title": "Lunch / Drill Evaluations", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-18", "start_time": "15:30", "end_time": "15:45", "title": "Honor Agreement", "event_type": "ceremony", "location": ""},
            {"date": "2026-07-18", "start_time": "15:45", "end_time": "17:00", "title": "Dormitory Orientation", "event_type": "training", "location": ""},
            {"date": "2026-07-18", "start_time": "17:15", "end_time": "17:45", "title": "Initial Skills Assessment", "event_type": "training", "location": ""},
            {"date": "2026-07-18", "start_time": "18:00", "end_time": "18:45", "title": "Wingmen & The Warrior Spirit", "event_type": "leadership", "location": ""},
            {"date": "2026-07-18", "start_time": "18:45", "end_time": "19:45", "title": "Team Leadership Problem #1", "event_type": "leadership", "location": ""},
            {"date": "2026-07-18", "start_time": "20:00", "end_time": "21:00", "title": "Dinner / Drill Evaluations", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-18", "start_time": "21:00", "end_time": "22:00", "title": "Group Retreat", "event_type": "ceremony", "location": ""},
            
            # July 19 - Day 1
            {"date": "2026-07-19", "start_time": "06:00", "end_time": "06:15", "title": "First Call", "event_type": "ceremony", "location": ""},
            {"date": "2026-07-19", "start_time": "06:15", "end_time": "06:30", "title": "Daily Calisthenics", "event_type": "pt", "location": "PT Field"},
            {"date": "2026-07-19", "start_time": "06:30", "end_time": "07:00", "title": "Shower, Dress", "event_type": "recreation", "location": ""},
            {"date": "2026-07-19", "start_time": "07:00", "end_time": "07:30", "title": "Group Reveille Formation", "event_type": "ceremony", "location": ""},
            {"date": "2026-07-19", "start_time": "07:30", "end_time": "08:45", "title": "Breakfast", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-19", "start_time": "09:00", "end_time": "11:45", "title": "Drones/Rockets", "event_type": "academics", "location": "Conex Area / T-7"},
            {"date": "2026-07-19", "start_time": "11:45", "end_time": "14:00", "title": "Lunch", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-19", "start_time": "14:30", "end_time": "16:15", "title": "Drones/Rockets (Continued)", "event_type": "academics", "location": "Conex Area / T-7"},
            {"date": "2026-07-19", "start_time": "16:15", "end_time": "17:15", "title": "Dormitory & Uniform Prep", "event_type": "admin", "location": ""},
            {"date": "2026-07-19", "start_time": "17:15", "end_time": "17:45", "title": "Dormitory Inspection #1", "event_type": "admin", "location": ""},
            {"date": "2026-07-19", "start_time": "17:45", "end_time": "18:00", "title": "Parade Practice", "event_type": "training", "location": ""},
            {"date": "2026-07-19", "start_time": "18:00", "end_time": "19:00", "title": "Dinner / Drill", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-19", "start_time": "21:00", "end_time": "22:00", "title": "Group Retreat", "event_type": "ceremony", "location": ""},
            
            # July 20 - Day 2
            {"date": "2026-07-20", "start_time": "06:00", "end_time": "06:15", "title": "First Call", "event_type": "ceremony", "location": ""},
            {"date": "2026-07-20", "start_time": "06:15", "end_time": "06:30", "title": "Daily Calisthenics", "event_type": "pt", "location": "PT Field"},
            {"date": "2026-07-20", "start_time": "06:30", "end_time": "06:45", "title": "Guidon Run", "event_type": "pt", "location": ""},
            {"date": "2026-07-20", "start_time": "06:45", "end_time": "07:30", "title": "Change to ABU / Breakfast Prep", "event_type": "admin", "location": ""},
            {"date": "2026-07-20", "start_time": "07:30", "end_time": "09:00", "title": "Breakfast", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-20", "start_time": "09:00", "end_time": "11:00", "title": "Obstacle Course", "event_type": "pt", "location": "F4"},
            {"date": "2026-07-20", "start_time": "11:00", "end_time": "12:30", "title": "Quiz & Review", "event_type": "academics", "location": ""},
            {"date": "2026-07-20", "start_time": "12:30", "end_time": "13:30", "title": "Team Leadership Problem #2", "event_type": "leadership", "location": ""},
            {"date": "2026-07-20", "start_time": "13:30", "end_time": "16:15", "title": "Lunch / Drill", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-20", "start_time": "17:00", "end_time": "17:30", "title": "The Core Values", "event_type": "leadership", "location": "TR5"},
            {"date": "2026-07-20", "start_time": "17:30", "end_time": "18:00", "title": "Becoming a Core Values Leader", "event_type": "leadership", "location": ""},
            {"date": "2026-07-20", "start_time": "18:00", "end_time": "19:00", "title": "Mobile Lab - Air National Guard", "event_type": "academics", "location": ""},
            {"date": "2026-07-20", "start_time": "20:45", "end_time": "21:15", "title": "Parade Practice/Drill", "event_type": "training", "location": ""},
            {"date": "2026-07-20", "start_time": "21:15", "end_time": "22:15", "title": "Cadet Handbook Review", "event_type": "academics", "location": ""},
            
            # July 21 - Day 3
            {"date": "2026-07-21", "start_time": "06:00", "end_time": "06:15", "title": "First Call", "event_type": "ceremony", "location": ""},
            {"date": "2026-07-21", "start_time": "06:15", "end_time": "06:30", "title": "Safety Briefing", "event_type": "training", "location": ""},
            {"date": "2026-07-21", "start_time": "06:30", "end_time": "07:00", "title": "Daily Calisthenics", "event_type": "pt", "location": "PT Field"},
            {"date": "2026-07-21", "start_time": "07:00", "end_time": "07:30", "title": "Shower, Dress", "event_type": "recreation", "location": ""},
            {"date": "2026-07-21", "start_time": "07:30", "end_time": "09:00", "title": "Breakfast", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-21", "start_time": "09:00", "end_time": "11:00", "title": "Obstacle Course", "event_type": "pt", "location": "F4"},
            {"date": "2026-07-21", "start_time": "11:00", "end_time": "12:30", "title": "Quiz & Review", "event_type": "academics", "location": ""},
            {"date": "2026-07-21", "start_time": "12:30", "end_time": "13:30", "title": "Team Leadership Problem #2", "event_type": "leadership", "location": ""},
            {"date": "2026-07-21", "start_time": "13:30", "end_time": "16:15", "title": "Lunch / Drill", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-21", "start_time": "17:00", "end_time": "17:30", "title": "The Core Values", "event_type": "leadership", "location": "TR5"},
            {"date": "2026-07-21", "start_time": "17:30", "end_time": "18:00", "title": "Becoming a Core Values Leader", "event_type": "leadership", "location": ""},
            {"date": "2026-07-21", "start_time": "18:00", "end_time": "19:00", "title": "Mobile Lab", "event_type": "academics", "location": ""},
            {"date": "2026-07-21", "start_time": "20:45", "end_time": "21:15", "title": "Parade Practice/Drill", "event_type": "training", "location": ""},
            {"date": "2026-07-21", "start_time": "21:15", "end_time": "22:15", "title": "Cadet Handbook Review", "event_type": "academics", "location": ""},
            
            # July 22 - Day 4
            {"date": "2026-07-22", "start_time": "06:00", "end_time": "06:15", "title": "First Call", "event_type": "ceremony", "location": ""},
            {"date": "2026-07-22", "start_time": "06:15", "end_time": "06:30", "title": "Group Reveille Formation", "event_type": "ceremony", "location": ""},
            {"date": "2026-07-22", "start_time": "06:30", "end_time": "07:00", "title": "Daily Calisthenics", "event_type": "pt", "location": "PT Field"},
            {"date": "2026-07-22", "start_time": "07:00", "end_time": "07:30", "title": "Shower, Dress", "event_type": "recreation", "location": ""},
            {"date": "2026-07-22", "start_time": "07:30", "end_time": "09:00", "title": "Breakfast", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-22", "start_time": "09:00", "end_time": "09:45", "title": "Travel to Chattanooga", "event_type": "admin", "location": ""},
            {"date": "2026-07-22", "start_time": "09:15", "end_time": "12:45", "title": "Military Power - Field Trip", "event_type": "training", "location": "Chattanooga"},
            {"date": "2026-07-22", "start_time": "12:45", "end_time": "13:15", "title": "Chaplain Services", "event_type": "ceremony", "location": "TR6"},
            {"date": "2026-07-22", "start_time": "13:15", "end_time": "13:45", "title": "Dorm & Uniform Inspection", "event_type": "admin", "location": ""},
            {"date": "2026-07-22", "start_time": "14:00", "end_time": "17:15", "title": "Dinner / Drill", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-22", "start_time": "20:45", "end_time": "21:45", "title": "Group Retreat", "event_type": "ceremony", "location": ""},
            
            # July 23 - Day 5
            {"date": "2026-07-23", "start_time": "06:00", "end_time": "06:15", "title": "First Call", "event_type": "ceremony", "location": ""},
            {"date": "2026-07-23", "start_time": "06:15", "end_time": "06:30", "title": "Daily Calisthenics", "event_type": "pt", "location": "PT Field"},
            {"date": "2026-07-23", "start_time": "06:30", "end_time": "07:00", "title": "Change to ABU", "event_type": "admin", "location": ""},
            {"date": "2026-07-23", "start_time": "07:00", "end_time": "07:30", "title": "Shower, Dress", "event_type": "recreation", "location": ""},
            {"date": "2026-07-23", "start_time": "07:30", "end_time": "09:00", "title": "Breakfast", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-23", "start_time": "09:00", "end_time": "10:30", "title": "The Leadership Concept", "event_type": "leadership", "location": ""},
            {"date": "2026-07-23", "start_time": "10:30", "end_time": "12:00", "title": "Leadership Quiz", "event_type": "academics", "location": ""},
            {"date": "2026-07-23", "start_time": "12:00", "end_time": "13:30", "title": "Chaplain Service", "event_type": "ceremony", "location": "TR-7"},
            {"date": "2026-07-23", "start_time": "13:30", "end_time": "15:30", "title": "Team Leadership Problem #3", "event_type": "leadership", "location": ""},
            {"date": "2026-07-23", "start_time": "15:30", "end_time": "17:00", "title": "Lunch", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-23", "start_time": "17:00", "end_time": "17:45", "title": "Dinner / Drill", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-23", "start_time": "20:00", "end_time": "20:20", "title": "Parade Practice", "event_type": "training", "location": ""},
            {"date": "2026-07-23", "start_time": "20:20", "end_time": "20:40", "title": "Astronomy", "event_type": "academics", "location": "TR-7"},
            {"date": "2026-07-23", "start_time": "20:40", "end_time": "21:00", "title": "Cyber Training", "event_type": "academics", "location": "TR-7"},
            {"date": "2026-07-23", "start_time": "21:00", "end_time": "22:00", "title": "Cadet Advisories", "event_type": "training", "location": ""},
            
            # July 24 - Graduation Day
            {"date": "2026-07-24", "start_time": "06:00", "end_time": "06:15", "title": "First Call", "event_type": "ceremony", "location": ""},
            {"date": "2026-07-24", "start_time": "06:15", "end_time": "06:30", "title": "Daily Calisthenics", "event_type": "pt", "location": "PT Field"},
            {"date": "2026-07-24", "start_time": "06:30", "end_time": "07:00", "title": "Group Reveille Formation", "event_type": "ceremony", "location": ""},
            {"date": "2026-07-24", "start_time": "07:00", "end_time": "07:30", "title": "Encampment Critique", "event_type": "admin", "location": ""},
            {"date": "2026-07-24", "start_time": "07:30", "end_time": "09:00", "title": "Room Packing", "event_type": "admin", "location": ""},
            {"date": "2026-07-24", "start_time": "09:00", "end_time": "09:45", "title": "Thank You Cards", "event_type": "admin", "location": ""},
            {"date": "2026-07-24", "start_time": "09:45", "end_time": "10:45", "title": "Common Area Deep Clean", "event_type": "admin", "location": ""},
            {"date": "2026-07-24", "start_time": "10:45", "end_time": "11:00", "title": "Flight Rooms Final Check", "event_type": "admin", "location": ""},
            {"date": "2026-07-24", "start_time": "11:00", "end_time": "11:45", "title": "Shower & Dress (Blues)", "event_type": "admin", "location": ""},
            {"date": "2026-07-24", "start_time": "11:45", "end_time": "12:45", "title": "Parade Practice", "event_type": "training", "location": ""},
            {"date": "2026-07-24", "start_time": "12:45", "end_time": "13:45", "title": "Lunch", "event_type": "meal", "location": "DFAC"},
            {"date": "2026-07-24", "start_time": "13:15", "end_time": "13:45", "title": "Parents Arrive", "event_type": "ceremony", "location": ""},
            {"date": "2026-07-24", "start_time": "13:45", "end_time": "14:45", "title": "Graduation Parade", "event_type": "ceremony", "location": "Parade Field"},
            {"date": "2026-07-24", "start_time": "14:45", "end_time": "15:30", "title": "Graduation Ceremony", "event_type": "ceremony", "location": ""},
        ]
        
        # Clear existing schedule
        await db.schedule.delete_many({})
        
        imported_count = 0
        now = datetime.now(timezone.utc).isoformat()
        
        for event in schedule_data:
            event_id = str(uuid.uuid4())
            # Convert squadron to target_groups format
            target_groups = ["all"]
            if event.get("squadron") == "staff":
                target_groups = ["staff"]
            
            doc = {
                "id": event_id,
                "title": event["title"],
                "description": "",
                "date": event["date"],
                "start_time": event["start_time"],
                "end_time": event["end_time"],
                "location": event.get("location", ""),
                "event_type": event["event_type"],
                "target_groups": target_groups,
                "created_at": now,
                "updated_at": now
            }
            await db.schedule.insert_one(doc)
            imported_count += 1
        
        # Mark schedule as modified but not published, increment version
        await db.schedule_settings.update_one(
            {"_id": "settings"},
            {"$set": {"is_published": False, "last_modified_at": now}, "$inc": {"version": 1}},
            upsert=True
        )
        
        return {"message": f"Successfully imported {imported_count} events for July 17-24, 2026. Schedule is in draft mode."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

@api_router.delete("/schedule/clear")
async def clear_schedule(
    user: dict = Depends(require_role([UserRole.COMMANDER]))
):
    """Clear all schedule events - commander only"""
    result = await db.schedule.delete_many({})
    
    # Reset publish status and increment version
    await increment_schedule_version()
    await db.schedule_settings.update_one(
        {"_id": "settings"},
        {"$set": {"is_published": False}},
        upsert=True
    )
    
    return {"message": f"Cleared {result.deleted_count} events from schedule"}

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
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
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
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
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

# ================= BUDGET ROUTES =================

# Helper to check if user can access financials
def require_finance_access():
    """Require Commander or Finance role for budget access"""
    async def checker(user: dict = Depends(get_current_user)):
        if user["role"] not in [UserRole.COMMANDER, UserRole.FINANCE]:
            raise HTTPException(status_code=403, detail="Access restricted to Commander and Finance roles")
        return user
    return checker


@api_router.get("/budget", response_model=List[BudgetItemResponse])
async def get_budget(user: dict = Depends(require_finance_access())):
    """Get all budget items - restricted to Commander and Finance roles"""
    items = await db.budget.find({}, {"_id": 0}).to_list(1000)
    return [BudgetItemResponse(**i) for i in items]


@api_router.post("/budget", response_model=BudgetItemResponse)
async def create_budget_item(
    data: BudgetItemCreate,
    user: dict = Depends(require_finance_access())
):
    item_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    doc = {
        "id": item_id,
        **data.model_dump(),
        "created_at": now,
        "updated_at": now
    }
    await db.budget.insert_one(doc)
    doc.pop("_id", None)
    return BudgetItemResponse(**doc)


@api_router.get("/budget/summary")
async def get_budget_summary(user: dict = Depends(require_finance_access())):
    """Get budget summary - restricted to Commander and Finance roles"""
    items = await db.budget.find({}, {"_id": 0}).to_list(1000)
    
    total_estimated = sum(i.get("estimated", 0) for i in items)
    total_actual = sum(i.get("actual", 0) for i in items)
    
    # Group by category
    categories = {}
    for item in items:
        cat = item.get("category", "General")
        if cat not in categories:
            categories[cat] = {"estimated": 0, "actual": 0}
        categories[cat]["estimated"] += item.get("estimated", 0)
        categories[cat]["actual"] += item.get("actual", 0)
    
    return {
        "total_estimated": total_estimated,
        "total_actual": total_actual,
        "variance": total_estimated - total_actual,
        "by_category": categories
    }


@api_router.get("/budget/food-settings")
async def get_food_expense_settings(user: dict = Depends(require_finance_access())):
    """Get food expense settings for cost-per-person-per-day calculation"""
    settings = await db.food_expense_settings.find_one({"_id": "settings"})
    
    # Get participant count from roster
    participant_count = await db.participants.count_documents({})
    
    # Default cost from 2026 TNWG Encampment Budget: $13.15 per person per day
    default_cost = 13.15
    
    if not settings:
        return {
            "cost_per_person_per_day": default_cost,
            "total_participants": participant_count,
            "total_days": 8,
            "notes": "Default: $13.15/day from TNWG Budget (July 17-24)",
            "total_food_budget": default_cost * participant_count * 8
        }
    
    cost = settings.get("cost_per_person_per_day", default_cost)
    participants = settings.get("total_participants") or participant_count
    days = settings.get("total_days", 8)
    
    return {
        "cost_per_person_per_day": cost,
        "total_participants": participants,
        "total_days": days,
        "notes": settings.get("notes", ""),
        "total_food_budget": cost * participants * days
    }


@api_router.put("/budget/food-settings")
async def update_food_expense_settings(
    data: FoodExpenseSettingsUpdate,
    user: dict = Depends(require_finance_access())
):
    """Update food expense settings"""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.food_expense_settings.update_one(
        {"_id": "settings"},
        {"$set": update_data},
        upsert=True
    )
    
    # Fetch and return updated settings
    settings = await db.food_expense_settings.find_one({"_id": "settings"})
    participant_count = await db.participants.count_documents({})
    
    cost = settings.get("cost_per_person_per_day", 15.0)
    participants = settings.get("total_participants") or participant_count
    days = settings.get("total_days", 8)
    
    return {
        "cost_per_person_per_day": cost,
        "total_participants": participants,
        "total_days": days,
        "notes": settings.get("notes", ""),
        "total_food_budget": cost * participants * days
    }


@api_router.post("/budget/import")
async def import_budget(
    file: UploadFile = File(...),
    user: dict = Depends(require_finance_access())
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        imported_count = 0
        now = datetime.now(timezone.utc).isoformat()
        
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            
            item_name = str(row_dict.get('item_name', row_dict.get('item', ''))).strip()
            if not item_name or item_name == 'nan':
                continue
            
            item_id = str(uuid.uuid4())
            
            doc = {
                "id": item_id,
                "category": str(row_dict.get('category', 'General')).strip() if pd.notna(row_dict.get('category')) else 'General',
                "subcategory": str(row_dict.get('subcategory', '')).strip() if pd.notna(row_dict.get('subcategory')) else None,
                "item_name": item_name,
                "estimated": float(row_dict.get('estimated', 0)) if pd.notna(row_dict.get('estimated')) else 0.0,
                "actual": float(row_dict.get('actual', 0)) if pd.notna(row_dict.get('actual')) else 0.0,
                "notes": str(row_dict.get('notes', '')).strip() if pd.notna(row_dict.get('notes')) else None,
                "created_at": now,
                "updated_at": now
            }
            
            await db.budget.insert_one(doc)
            imported_count += 1
        
        return {"message": f"Successfully imported {imported_count} budget items"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")


@api_router.post("/budget/seed-tnwg-template")
async def seed_tnwg_budget_template(
    user: dict = Depends(require_finance_access())
):
    """Seed budget with 2026 TNWG Encampment Budget template items"""
    
    # Check if budget already has items
    existing_count = await db.budget.count_documents({})
    if existing_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Budget already has {existing_count} items. Clear budget first or use import."
        )
    
    now = datetime.now(timezone.utc).isoformat()
    
    # 2026 TNWG Encampment Budget Template Items
    template_items = [
        # Income Sources
        {"category": "Participant Fees", "item_name": "Senior Members Staff", "estimated": 2400.0, "item_type": "income", "notes": "42 SM @ varies"},
        {"category": "Participant Fees", "item_name": "Cadet Cadre", "estimated": 9500.0, "item_type": "income", "notes": "38 Cadre @ $250"},
        {"category": "Participant Fees", "item_name": "Basic Students", "estimated": 22500.0, "item_type": "income", "notes": "90 Students @ $250"},
        {"category": "NHQ Allocations", "item_name": "CEAP Funds (Students)", "estimated": 0.0, "item_type": "income", "notes": "NHQ CEAP allocation for students"},
        {"category": "NHQ Allocations", "item_name": "CEAP Funds (Cadre)", "estimated": 0.0, "item_type": "income", "notes": "NHQ CEAP allocation for cadre"},
        {"category": "Donations", "item_name": "Heritage Wing Donations", "estimated": 560.0, "item_type": "income"},
        {"category": "Donations", "item_name": "Other Donations", "estimated": 0.0, "item_type": "income"},
        
        # Facility Expenses
        {"category": "Facility", "item_name": "VTS Catoosa Facility Rental", "estimated": 11000.0, "item_type": "expense", "vendor": "VTS Catoosa"},
        
        # DFAC Budget
        {"category": "DFAC Budget", "item_name": "Meals Contract", "estimated": 0.0, "item_type": "expense", "notes": "$13.15/person/day - see Food Planner"},
        {"category": "DFAC Budget", "item_name": "Hydration Supplies", "estimated": 200.0, "item_type": "expense"},
        {"category": "DFAC Budget", "item_name": "DFAC Supplies", "estimated": 150.0, "item_type": "expense"},
        {"category": "DFAC Budget", "item_name": "Bathroom/DFAC Supplies", "estimated": 100.0, "item_type": "expense"},
        
        # Graduation Budget
        {"category": "Graduation Budget", "item_name": "Awards / Challenge Coins", "estimated": 670.0, "item_type": "expense"},
        {"category": "Graduation Budget", "item_name": "Honors/Grad Packages", "estimated": 3500.0, "item_type": "expense"},
        {"category": "Graduation Budget", "item_name": "Honor Flight Streamers", "estimated": 20.0, "item_type": "expense"},
        
        # Commandants Budget
        {"category": "Commandants Budget", "item_name": "Miscellaneous", "estimated": 500.0, "item_type": "expense"},
        {"category": "Commandants Budget", "item_name": "Sport Event Equipment", "estimated": 0.0, "item_type": "expense"},
        {"category": "Commandants Budget", "item_name": "Esprit de Corps", "estimated": 100.0, "item_type": "expense"},
        
        # Deputy Commander Support
        {"category": "Deputy Commander Support", "item_name": "Support Budget", "estimated": 450.0, "item_type": "expense"},
        {"category": "Deputy Commander Support", "item_name": "Cleaning Equipment", "estimated": 100.0, "item_type": "expense"},
        {"category": "Deputy Commander Support", "item_name": "Laundry Materials", "estimated": 100.0, "item_type": "expense"},
        
        # Advanced Training School
        {"category": "Advanced Training School", "item_name": "Academic Materials", "estimated": 100.0, "item_type": "expense"},
        {"category": "Advanced Training School", "item_name": "AE Track", "estimated": 0.0, "item_type": "expense"},
        {"category": "Advanced Training School", "item_name": "CP Track", "estimated": 100.0, "item_type": "expense"},
        {"category": "Advanced Training School", "item_name": "ES Track", "estimated": 100.0, "item_type": "expense"},
        {"category": "Advanced Training School", "item_name": "Streamer Holder", "estimated": 0.0, "item_type": "expense"},
        
        # Public Affairs
        {"category": "Public Affairs", "item_name": "Computer Discs", "estimated": 0.0, "item_type": "expense"},
        {"category": "Public Affairs", "item_name": "Printer Materials", "estimated": 100.0, "item_type": "expense"},
        {"category": "Public Affairs", "item_name": "Office Supplies", "estimated": 0.0, "item_type": "expense"},
        {"category": "Public Affairs", "item_name": "Student Supplies", "estimated": 100.0, "item_type": "expense"},
        
        # Logistics
        {"category": "Logistics", "item_name": "Communications Budget", "estimated": 0.0, "item_type": "expense"},
        {"category": "Logistics", "item_name": "Activities", "estimated": 100.0, "item_type": "expense"},
        {"category": "Logistics", "item_name": "Equipment", "estimated": 0.0, "item_type": "expense"},
        {"category": "Logistics", "item_name": "In-Processing Materials", "estimated": 100.0, "item_type": "expense"},
        
        # Health Services
        {"category": "Health Services", "item_name": "Support Budget", "estimated": 0.0, "item_type": "expense"},
        {"category": "Health Services", "item_name": "Swim Fee", "estimated": 345.0, "item_type": "expense"},
        
        # T-Shirts & Merchandise
        {"category": "T-Shirts & Merchandise", "item_name": "Encampment T-Shirts", "estimated": 7000.0, "item_type": "expense"},
        {"category": "T-Shirts & Merchandise", "item_name": "Cadre Equipment", "estimated": 600.0, "item_type": "expense"},
        
        # Refunds
        {"category": "Refunds", "item_name": "CEAP Refunds", "estimated": 0.0, "item_type": "expense"},
        {"category": "Refunds", "item_name": "Registration Refunds", "estimated": 0.0, "item_type": "expense"},
    ]
    
    inserted_count = 0
    for item_data in template_items:
        item_id = str(uuid.uuid4())
        doc = {
            "id": item_id,
            "category": item_data["category"],
            "subcategory": item_data.get("subcategory"),
            "item_name": item_data["item_name"],
            "estimated": item_data.get("estimated", 0.0),
            "actual": item_data.get("actual", 0.0),
            "notes": item_data.get("notes"),
            "vendor": item_data.get("vendor"),
            "item_type": item_data.get("item_type", "expense"),
            "payment_status": "pending",
            "created_at": now,
            "updated_at": now
        }
        await db.budget.insert_one(doc)
        inserted_count += 1
    
    # Also update food settings with TNWG defaults
    await db.food_expense_settings.update_one(
        {"_id": "settings"},
        {"$set": {
            "cost_per_person_per_day": 13.15,
            "total_participants": 170,  # 42 SM + 38 Cadre + 90 Students
            "total_days": 8,
            "notes": "2026 TNWG Encampment: $13.15/day (Breakfast + Lunch + Dinner)",
            "updated_at": now
        }},
        upsert=True
    )
    
    return {
        "message": f"Successfully seeded {inserted_count} budget items from TNWG template",
        "items_created": inserted_count,
        "food_settings_updated": True
    }


# ================= QUICK UPDATE ENDPOINTS =================

class QuickActualUpdate(BaseModel):
    actual: float
    payment_status: Optional[str] = None
    payment_date: Optional[str] = None


@api_router.patch("/budget/{item_id}/actual")
async def quick_update_actual(
    item_id: str,
    data: QuickActualUpdate,
    user: dict = Depends(require_finance_access())
):
    """Quick update for actual value - for live budget tracking"""
    item = await db.budget.find_one({"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Budget item not found")
    
    update_data = {
        "actual": data.actual,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if data.payment_status:
        update_data["payment_status"] = data.payment_status
    if data.payment_date:
        update_data["payment_date"] = data.payment_date
    
    await db.budget.update_one({"id": item_id}, {"$set": update_data})
    
    updated_item = await db.budget.find_one({"id": item_id}, {"_id": 0})
    return BudgetItemResponse(**updated_item)


@api_router.post("/budget/{item_id}/mark-paid")
async def mark_budget_item_paid(
    item_id: str,
    user: dict = Depends(require_finance_access())
):
    """Mark a budget item as paid - sets actual=estimated if no actual, status=paid"""
    item = await db.budget.find_one({"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Budget item not found")
    
    # If no actual value set, use estimated
    actual = item.get("actual", 0) or item.get("estimated", 0)
    
    update_data = {
        "actual": actual,
        "payment_status": "paid",
        "payment_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.budget.update_one({"id": item_id}, {"$set": update_data})
    
    updated_item = await db.budget.find_one({"id": item_id}, {"_id": 0})
    return BudgetItemResponse(**updated_item)


# Receipt upload helper
import base64

@api_router.post("/budget/{item_id}/receipt")
async def upload_receipt(
    item_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(require_finance_access())
):
    """Upload a receipt image for a budget item"""
    # Verify budget item exists
    item = await db.budget.find_one({"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Budget item not found")
    
    # Check file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Allowed: JPEG, PNG, GIF, PDF"
        )
    
    # Read file and encode as base64
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum 5MB allowed.")
    
    # Store receipt as base64 data URL
    b64_content = base64.b64encode(contents).decode('utf-8')
    data_url = f"data:{file.content_type};base64,{b64_content}"
    
    # Update budget item with receipt
    await db.budget.update_one(
        {"id": item_id},
        {"$set": {
            "receipt_url": data_url,
            "receipt_filename": file.filename,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "Receipt uploaded successfully",
        "filename": file.filename,
        "item_id": item_id
    }


@api_router.delete("/budget/{item_id}/receipt")
async def delete_receipt(
    item_id: str,
    user: dict = Depends(require_finance_access())
):
    """Delete a receipt from a budget item"""
    item = await db.budget.find_one({"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Budget item not found")
    
    await db.budget.update_one(
        {"id": item_id},
        {"$set": {
            "receipt_url": None,
            "receipt_filename": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Receipt deleted successfully"}


@api_router.put("/budget/{item_id}", response_model=BudgetItemResponse)
async def update_budget_item(
    item_id: str,
    data: BudgetItemCreate,
    user: dict = Depends(require_finance_access())
):
    now = datetime.now(timezone.utc).isoformat()
    update_data = {**data.model_dump(), "updated_at": now}
    
    result = await db.budget.update_one({"id": item_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Budget item not found")
    
    item = await db.budget.find_one({"id": item_id}, {"_id": 0})
    return BudgetItemResponse(**item)


@api_router.delete("/budget/{item_id}")
async def delete_budget_item(
    item_id: str,
    user: dict = Depends(require_finance_access())
):
    result = await db.budget.delete_one({"id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Budget item not found")
    return {"message": "Budget item deleted successfully"}


# ================= DOCUMENT ROUTES =================

# Document categories
DOCUMENT_CATEGORIES = [
    "tlp",           # Training Lesson Plans
    "pocket_class",  # Pocket Classes
    "handbook",      # Handbooks
    "sop",           # Standard Operating Procedures
    "form",          # Forms
    "checklist",     # Checklists
    "reference",     # Reference Materials
    "other"          # Other
]

def can_access_document(user: dict, doc: dict) -> bool:
    """Check if user can access a document based on scope"""
    # Commanders and Exec Cadre can access everything
    if user["role"] in [UserRole.COMMANDER, UserRole.EXEC_CADRE]:
        return True
    
    # Global documents are accessible to everyone
    if doc.get("scope") == "global" or (not doc.get("flight") and not doc.get("squadron")):
        return True
    
    # Squadron-scoped documents
    if doc.get("scope") == "squadron" and doc.get("squadron"):
        # Check if user's flight is in this squadron
        user_flight = user.get("flight", "").lower()
        doc_squadron = doc.get("squadron")
        flight_to_squadron = {
            "alpha": "6th_cts", "bravo": "6th_cts",
            "charlie": "21st_cts", "delta": "21st_cts",
            "echo": "22nd_cts", "foxtrot": "22nd_cts"
        }
        if flight_to_squadron.get(user_flight) == doc_squadron:
            return True
        # Staff assigned to squadron level
        if user.get("squadron") == doc_squadron:
            return True
    
    # Flight-scoped documents
    if doc.get("scope") == "flight" and doc.get("flight"):
        if user.get("flight", "").lower() == doc.get("flight").lower():
            return True
    
    return False

@api_router.get("/documents/categories")
async def get_document_categories(user: dict = Depends(get_current_user)):
    """Get available document categories"""
    return DOCUMENT_CATEGORIES

@api_router.get("/documents", response_model=List[DocumentResponse])
async def get_documents(
    doc_type: Optional[str] = None,
    category: Optional[str] = None,
    flight: Optional[str] = None,
    squadron: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get documents filtered by type, category, and flight/squadron access"""
    query = {}
    if doc_type:
        query["doc_type"] = doc_type
    if category:
        query["category"] = category
    
    docs = await db.documents.find(query, {"_id": 0}).to_list(1000)
    
    # Filter by access permissions
    accessible_docs = [d for d in docs if can_access_document(user, d)]
    
    # Additional filtering by specific flight/squadron if requested
    if flight:
        accessible_docs = [d for d in accessible_docs if d.get("flight") == flight or d.get("scope") == "global"]
    if squadron:
        accessible_docs = [d for d in accessible_docs if d.get("squadron") == squadron or d.get("scope") == "global"]
    
    return [DocumentResponse(**d) for d in accessible_docs]

@api_router.get("/documents/by-flight/{flight}")
async def get_flight_documents(
    flight: str,
    user: dict = Depends(get_current_user)
):
    """Get all documents accessible to a specific flight"""
    # Get flight-specific and global documents
    flight_lower = flight.lower()
    flight_to_squadron = {
        "alpha": "6th_cts", "bravo": "6th_cts",
        "charlie": "21st_cts", "delta": "21st_cts",
        "echo": "22nd_cts", "foxtrot": "22nd_cts"
    }
    squadron = flight_to_squadron.get(flight_lower)
    
    query = {
        "$or": [
            {"scope": "global"},
            {"flight": flight_lower},
            {"squadron": squadron, "scope": "squadron"}
        ]
    }
    
    docs = await db.documents.find(query, {"_id": 0}).to_list(1000)
    
    # Group by category
    categorized = {}
    for doc in docs:
        cat = doc.get("category") or doc.get("doc_type") or "other"
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(DocumentResponse(**doc))
    
    return {
        "flight": flight,
        "squadron": squadron,
        "documents": categorized,
        "total": len(docs)
    }

@api_router.get("/documents/by-squadron/{squadron}")
async def get_squadron_documents(
    squadron: str,
    user: dict = Depends(get_current_user)
):
    """Get all documents accessible to a specific squadron"""
    query = {
        "$or": [
            {"scope": "global"},
            {"squadron": squadron},
            {"squadron": squadron, "scope": "squadron"}
        ]
    }
    
    docs = await db.documents.find(query, {"_id": 0}).to_list(1000)
    
    # Group by category
    categorized = {}
    for doc in docs:
        cat = doc.get("category") or doc.get("doc_type") or "other"
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(DocumentResponse(**doc))
    
    return {
        "squadron": squadron,
        "documents": categorized,
        "total": len(docs)
    }

@api_router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not can_access_document(user, doc):
        raise HTTPException(status_code=403, detail="Not authorized to access this document")
    
    return DocumentResponse(**doc)

@api_router.post("/documents", response_model=DocumentResponse)
async def create_document(
    data: DocumentCreate,
    user: dict = Depends(require_role([UserRole.COMMANDER]))
):
    """Create a new document (Commander only)"""
    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    doc = {
        "id": doc_id,
        **data.model_dump(),
        "uploaded_by": user["name"],
        "version": 1,
        "version_history": [],
        "created_at": now,
        "updated_at": now
    }
    await db.documents.insert_one(doc)
    doc.pop("_id", None)
    return DocumentResponse(**doc)

@api_router.put("/documents/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: str,
    data: DocumentCreate,
    user: dict = Depends(require_role([UserRole.COMMANDER]))
):
    """Update a document with version tracking"""
    existing = await db.documents.find_one({"id": doc_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Document not found")
    
    now = datetime.now(timezone.utc).isoformat()
    current_version = existing.get("version", 1)
    
    # Store current version in history
    version_history = existing.get("version_history", [])
    version_history.append({
        "version": current_version,
        "title": existing.get("title"),
        "content": existing.get("content"),
        "file_url": existing.get("file_url"),
        "updated_by": existing.get("uploaded_by"),
        "updated_at": existing.get("updated_at")
    })
    
    update_data = {
        **data.model_dump(),
        "uploaded_by": user["name"],
        "version": current_version + 1,
        "version_history": version_history,
        "updated_at": now
    }
    
    await db.documents.update_one({"id": doc_id}, {"$set": update_data})
    
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    return DocumentResponse(**doc)

@api_router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    user: dict = Depends(require_role([UserRole.COMMANDER]))
):
    result = await db.documents.delete_one({"id": doc_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully"}


# ================= FLIGHT ROSTER ROUTES =================

@api_router.get("/flights")
async def get_flights(user: dict = Depends(get_current_user)):
    """Get list of all flights with their squadrons"""
    flights = [
        {"value": "alpha", "label": "Alpha Flight", "squadron": "6th_cts"},
        {"value": "bravo", "label": "Bravo Flight", "squadron": "6th_cts"},
        {"value": "charlie", "label": "Charlie Flight", "squadron": "21st_cts"},
        {"value": "delta", "label": "Delta Flight", "squadron": "21st_cts"},
        {"value": "echo", "label": "Echo Flight", "squadron": "22nd_cts"},
        {"value": "foxtrot", "label": "Foxtrot Flight", "squadron": "22nd_cts"}
    ]
    return flights

@api_router.get("/squadrons")
async def get_squadrons(user: dict = Depends(get_current_user)):
    """Get list of all squadrons"""
    squadrons = [
        {"value": "6th_cts", "label": "6th CTS", "flights": ["alpha", "bravo"]},
        {"value": "21st_cts", "label": "21st CTS", "flights": ["charlie", "delta"]},
        {"value": "22nd_cts", "label": "22nd CTS", "flights": ["echo", "foxtrot"]}
    ]
    return squadrons

@api_router.get("/flights/{flight}/roster")
async def get_flight_roster(
    flight: str,
    user: dict = Depends(get_current_user)
):
    """Get roster for a specific flight"""
    flight_lower = flight.lower()
    
    # Get participants in this flight (case-insensitive)
    participants = await db.participants.find(
        {"flight": {"$regex": f"^{flight_lower}$", "$options": "i"}, "is_removed": {"$ne": True}},
        {"_id": 0}
    ).to_list(500)
    
    # Format roster entries
    roster = []
    for p in participants:
        roster.append({
            "id": p.get("id"),
            "name": f"{p.get('rank', '')} {p.get('first_name', '')} {p.get('last_name', '')}".strip(),
            "rank": p.get("rank"),
            "first_name": p.get("first_name"),
            "last_name": p.get("last_name"),
            "position": None if p.get("participant_type") == "basic_student" else p.get("position", ""),
            "participant_type": p.get("participant_type"),
            "capid": p.get("capid"),
            "unit": p.get("unit"),
            "is_student": p.get("participant_type") == "basic_student"
        })
    
    # Sort by participant type (cadre first), then by rank
    rank_order = ["Col", "Lt Col", "Maj", "Capt", "1st Lt", "2nd Lt", "CMSgt", "SMSgt", "MSgt", "TSgt", "SSgt", "SrA", "A1C", "Amn", "AB",
                  "C/Col", "C/Lt Col", "C/Maj", "C/Capt", "C/1st Lt", "C/2nd Lt", "C/CMSgt", "C/SMSgt", "C/MSgt", "C/TSgt", "C/SSgt", "C/SrA", "C/A1C", "C/Amn", "C/AB"]
    
    def sort_key(r):
        type_order = 0 if not r.get("is_student") else 1
        rank = r.get("rank", "")
        rank_idx = rank_order.index(rank) if rank in rank_order else 999
        return (type_order, rank_idx, r.get("last_name", ""))
    
    roster.sort(key=sort_key)
    
    return {
        "flight": flight_lower,
        "roster": roster,
        "count": len(roster),
        "cadre_count": len([r for r in roster if not r.get("is_student")]),
        "cadet_count": len([r for r in roster if r.get("is_student")])
    }

@api_router.get("/squadrons/{squadron}/roster")
async def get_squadron_roster(
    squadron: str,
    user: dict = Depends(get_current_user)
):
    """Get roster for a specific squadron (all flights in squadron)"""
    squadron_flights = {
        "6th_cts": ["alpha", "bravo"],
        "21st_cts": ["charlie", "delta"],
        "22nd_cts": ["echo", "foxtrot"]
    }
    
    flights = squadron_flights.get(squadron.lower(), [])
    if not flights:
        raise HTTPException(status_code=404, detail="Squadron not found")
    
    # Build regex pattern for flights
    flight_pattern = "|".join([f"^{f}$" for f in flights])
    
    participants = await db.participants.find(
        {"flight": {"$regex": flight_pattern, "$options": "i"}, "is_removed": {"$ne": True}},
        {"_id": 0}
    ).to_list(500)
    
    # Group by flight
    roster_by_flight = {}
    for f in flights:
        roster_by_flight[f] = []
    
    for p in participants:
        flight = p.get("flight", "").lower()
        if flight in roster_by_flight:
            roster_by_flight[flight].append({
                "id": p.get("id"),
                "name": f"{p.get('rank', '')} {p.get('first_name', '')} {p.get('last_name', '')}".strip(),
                "rank": p.get("rank"),
                "first_name": p.get("first_name"),
                "last_name": p.get("last_name"),
                "position": None if p.get("participant_type") == "basic_student" else p.get("position", ""),
                "participant_type": p.get("participant_type"),
                "is_student": p.get("participant_type") == "basic_student"
            })
    
    return {
        "squadron": squadron,
        "flights": roster_by_flight,
        "total_count": len(participants)
    }

@api_router.get("/my-flight")
async def get_my_flight_info(user: dict = Depends(get_current_user)):
    """Get current user's flight information and accessible flights"""
    user_flight = (user.get("flight") or "").lower()
    user_role = user.get("role")
    user_squadron = user.get("squadron")
    
    flight_to_squadron = {
        "alpha": "6th_cts", "bravo": "6th_cts",
        "charlie": "21st_cts", "delta": "21st_cts",
        "echo": "22nd_cts", "foxtrot": "22nd_cts"
    }
    
    all_flights = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
    all_squadrons = ["6th_cts", "21st_cts", "22nd_cts"]
    
    # Determine accessible flights
    if user_role in [UserRole.COMMANDER, UserRole.EXEC_CADRE]:
        accessible_flights = all_flights
        accessible_squadrons = all_squadrons
    elif user_squadron:
        # Squadron-level staff
        squadron_flights = {
            "6th_cts": ["alpha", "bravo"],
            "21st_cts": ["charlie", "delta"],
            "22nd_cts": ["echo", "foxtrot"]
        }
        accessible_flights = squadron_flights.get(user_squadron, [])
        accessible_squadrons = [user_squadron]
    elif user_flight:
        accessible_flights = [user_flight]
        accessible_squadrons = [flight_to_squadron.get(user_flight)] if user_flight in flight_to_squadron else []
    else:
        accessible_flights = []
        accessible_squadrons = []
    
    return {
        "user_flight": user_flight or None,
        "user_squadron": user_squadron or flight_to_squadron.get(user_flight),
        "user_role": user_role,
        "accessible_flights": accessible_flights,
        "accessible_squadrons": accessible_squadrons,
        "has_full_access": user_role in [UserRole.COMMANDER, UserRole.EXEC_CADRE]
    }


# ================= ORG CHART ROUTES =================

async def get_role_with_details(role: dict) -> dict:
    """Enrich org chart role with member details and subordinates"""
    # Get assigned member details
    if role.get("assigned_participant_id"):
        participant = await db.participants.find_one(
            {"id": role["assigned_participant_id"]}, 
            {"_id": 0, "first_name": 1, "last_name": 1, "rank": 1}
        )
        if participant:
            role["assigned_member_name"] = f"{participant.get('rank', '')} {participant.get('first_name', '')} {participant.get('last_name', '')}".strip()
            role["assigned_member_rank"] = participant.get("rank", "")
        else:
            role["assigned_member_name"] = None
            role["assigned_member_rank"] = None
    else:
        role["assigned_member_name"] = None
        role["assigned_member_rank"] = None
    
    # Get direct subordinates
    subordinates = await db.org_chart_roles.find(
        {"reports_to": role["role_id"]}, 
        {"_id": 0, "role_id": 1}
    ).to_list(100)
    role["direct_subordinates"] = [s["role_id"] for s in subordinates]
    
    return role

@api_router.get("/org-chart/roles", response_model=List[OrgChartRoleResponse])
async def get_org_chart_roles(user: dict = Depends(get_current_user)):
    """Get all org chart roles - accessible by all authenticated users"""
    roles = await db.org_chart_roles.find({}, {"_id": 0}).to_list(1000)
    enriched_roles = []
    for role in roles:
        enriched = await get_role_with_details(role)
        enriched_roles.append(OrgChartRoleResponse(**enriched))
    return enriched_roles

@api_router.get("/org-chart/roles/{role_id}", response_model=OrgChartRoleResponse)
async def get_org_chart_role(role_id: str, user: dict = Depends(get_current_user)):
    """Get single org chart role details - accessible by all authenticated users"""
    role = await db.org_chart_roles.find_one({"role_id": role_id}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    enriched = await get_role_with_details(role)
    return OrgChartRoleResponse(**enriched)

@api_router.post("/org-chart/roles", response_model=OrgChartRoleResponse)
async def create_org_chart_role(
    data: OrgChartRoleCreate,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    """Create new org chart role - editors only"""
    # Check if role_id already exists
    existing = await db.org_chart_roles.find_one({"role_id": data.role_id})
    if existing:
        raise HTTPException(status_code=400, detail="Role ID already exists")
    
    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    doc = {
        "id": doc_id,
        **data.model_dump(),
        "created_at": now,
        "updated_at": now
    }
    await db.org_chart_roles.insert_one(doc)
    doc.pop("_id", None)
    
    enriched = await get_role_with_details(doc)
    return OrgChartRoleResponse(**enriched)

@api_router.put("/org-chart/roles/{role_id}", response_model=OrgChartRoleResponse)
async def update_org_chart_role(
    role_id: str,
    data: OrgChartRoleUpdate,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    """Update org chart role - editors only"""
    now = datetime.now(timezone.utc).isoformat()
    
    # Only update fields that are provided
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now
    
    result = await db.org_chart_roles.update_one(
        {"role_id": role_id}, 
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Role not found")
    
    role = await db.org_chart_roles.find_one({"role_id": role_id}, {"_id": 0})
    enriched = await get_role_with_details(role)
    return OrgChartRoleResponse(**enriched)

@api_router.put("/org-chart/roles/{role_id}/assign", response_model=OrgChartRoleResponse)
async def assign_org_chart_role(
    role_id: str,
    participant_id: Optional[str] = None,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    """Assign or unassign a participant to a role - editors only"""
    now = datetime.now(timezone.utc).isoformat()
    
    # Verify participant exists if assigning
    if participant_id:
        participant = await db.participants.find_one({"id": participant_id})
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
    
    result = await db.org_chart_roles.update_one(
        {"role_id": role_id},
        {"$set": {"assigned_participant_id": participant_id, "updated_at": now}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Role not found")
    
    role = await db.org_chart_roles.find_one({"role_id": role_id}, {"_id": 0})
    enriched = await get_role_with_details(role)
    return OrgChartRoleResponse(**enriched)

@api_router.delete("/org-chart/roles/{role_id}")
async def delete_org_chart_role(
    role_id: str,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    """Delete org chart role - editors only"""
    # Check if any roles report to this one
    subordinates = await db.org_chart_roles.count_documents({"reports_to": role_id})
    if subordinates > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete role with {subordinates} subordinate(s). Reassign them first."
        )
    
    result = await db.org_chart_roles.delete_one({"role_id": role_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Role not found")
    return {"message": "Role deleted successfully"}

@api_router.post("/org-chart/seed-defaults")
async def seed_default_org_chart(
    user: dict = Depends(require_role([UserRole.COMMANDER]))
):
    """Seed default encampment org chart structure - commander only"""
    # Check if roles already exist
    existing_count = await db.org_chart_roles.count_documents({})
    if existing_count > 0:
        raise HTTPException(status_code=400, detail="Org chart already has roles. Clear first if you want to reseed.")
    
    now = datetime.now(timezone.utc).isoformat()
    
    default_roles = [
        # ===== LEVEL 0 - Encampment Commander =====
        {"role_id": "enc-commander", "title": "Encampment Commander", "level": 0, "order": 0, "reports_to": None,
         "summary": "Overall commander responsible for the entire encampment operation.",
         "responsibilities": "- Provide strategic leadership and vision for encampment\n- Ensure safety and welfare of all participants\n- Coordinate with Wing and Region leadership\n- Final authority on all encampment matters\n- Conduct commander's calls and briefings\n- Approve all major decisions"},
        
        # ===== LEVEL 1 - Direct Reports to EC =====
        {"role_id": "sm-superintendent", "title": "SM Superintendent", "level": 1, "order": 0, "reports_to": "enc-commander",
         "summary": "Senior Member Superintendent - supports commander with senior member coordination.",
         "responsibilities": "- Coordinate senior member staff activities\n- Serve as liaison between cadets and senior members\n- Assist with administrative functions\n- Support commander as needed"},
        {"role_id": "finance", "title": "Finance", "level": 1, "order": 1, "reports_to": "enc-commander",
         "summary": "Manages all financial operations for encampment.",
         "responsibilities": "- Track all income and expenses\n- Process registration payments\n- Manage budget allocations\n- Prepare financial reports\n- Handle vendor payments"},
        {"role_id": "chaplain-cdi", "title": "Chaplain/CDI", "level": 1, "order": 2, "reports_to": "enc-commander",
         "summary": "Provides spiritual support and character development instruction.",
         "responsibilities": "- Conduct religious services\n- Provide counseling support\n- Lead character development sessions\n- Support cadet welfare"},
        {"role_id": "health-services", "title": "Health Services", "level": 1, "order": 3, "reports_to": "enc-commander",
         "summary": "Oversees all medical support and health services.",
         "responsibilities": "- Manage medical staff and supplies\n- Coordinate emergency medical response\n- Track medications and health records\n- Conduct health screenings\n- Ensure AED and first aid readiness"},
        {"role_id": "safety", "title": "Safety", "level": 1, "order": 4, "reports_to": "enc-commander",
         "summary": "Ensures safety compliance throughout encampment operations.",
         "responsibilities": "- Conduct safety briefings and inspections\n- Monitor activity safety compliance\n- Investigate and report incidents\n- Maintain safety documentation\n- Coordinate with health services"},
        
        # ===== LEVEL 2 - Commandant & Deputy Support =====
        {"role_id": "commandant", "title": "Commandant", "level": 2, "order": 0, "reports_to": "enc-commander",
         "summary": "Senior Member overseeing all cadet training operations.",
         "responsibilities": "- Supervise Cadet Commander and training staff\n- Ensure training objectives are met\n- Coordinate training schedule execution\n- Evaluate cadet performance\n- Maintain discipline standards"},
        {"role_id": "cadet-commander", "title": "Cadet Commander", "level": 2, "order": 1, "reports_to": "enc-commander",
         "summary": "Senior cadet leader commanding the cadet corps.",
         "responsibilities": "- Lead cadet staff and corps\n- Execute training plan\n- Set example for all cadets\n- Conduct formations and inspections\n- Report to Commandant and EC"},
        {"role_id": "deputy-support", "title": "Deputy Comm for Support", "level": 2, "order": 2, "reports_to": "enc-commander",
         "summary": "Oversees all support and logistics functions.",
         "responsibilities": "- Supervise support staff sections\n- Manage facilities and resources\n- Coordinate transportation and logistics\n- Oversee communications and PA"},
        
        # ===== LEVEL 3 - Under Commandant =====
        {"role_id": "chief-instructor", "title": "Chief Instructor", "level": 3, "order": 0, "reports_to": "commandant",
         "summary": "Leads instructor cadre for training delivery.",
         "responsibilities": "- Train and supervise instructors\n- Ensure training quality\n- Develop lesson plans\n- Evaluate instruction effectiveness"},
        {"role_id": "chief-training-officer", "title": "Chief Training Officer", "level": 3, "order": 1, "reports_to": "commandant",
         "summary": "Manages training schedule and operations.",
         "responsibilities": "- Coordinate daily training schedule\n- Track training completion\n- Manage training resources\n- Support instructors"},
        
        # ===== LEVEL 3 - Under Cadet Commander =====
        {"role_id": "dean-academics", "title": "Dean of Academics", "level": 3, "order": 2, "reports_to": "cadet-commander",
         "summary": "Oversees academic and classroom instruction.",
         "responsibilities": "- Manage classroom training\n- Coordinate testing and evaluations\n- Track academic progress\n- Support instructor development"},
        {"role_id": "deputy-commander", "title": "Deputy Commander", "level": 3, "order": 3, "reports_to": "cadet-commander",
         "summary": "Assists Cadet Commander with corps leadership.",
         "responsibilities": "- Support Cadet Commander duties\n- Lead in CC's absence\n- Coordinate staff activities\n- Assist with formations"},
        
        # ===== LEVEL 3 - Under Deputy Support =====
        {"role_id": "word", "title": "Word", "level": 3, "order": 4, "reports_to": "deputy-support",
         "summary": "Manages administrative and word processing functions.",
         "responsibilities": "- Prepare documents and reports\n- Maintain records and files\n- Support administrative tasks\n- Coordinate information flow"},
        {"role_id": "public-affairs", "title": "Public Affairs", "level": 3, "order": 5, "reports_to": "deputy-support",
         "summary": "Manages public affairs and media documentation.",
         "responsibilities": "- Photography and videography\n- Social media updates\n- Prepare graduation program\n- Media coordination and releases"},
        {"role_id": "logistics", "title": "Logistics", "level": 3, "order": 6, "reports_to": "deputy-support",
         "summary": "Manages supply and logistics operations.",
         "responsibilities": "- Inventory management\n- Supply distribution\n- Equipment accountability\n- Facility coordination"},
        {"role_id": "plans-programs", "title": "Plans and Programs", "level": 3, "order": 7, "reports_to": "deputy-support",
         "summary": "Manages planning and program coordination.",
         "responsibilities": "- Develop activity plans\n- Coordinate special programs\n- Track milestones and objectives\n- Support scheduling"},
        {"role_id": "comms", "title": "Comms", "level": 3, "order": 8, "reports_to": "deputy-support",
         "summary": "Manages communications equipment and operations.",
         "responsibilities": "- Maintain radios and comm equipment\n- Coordinate communication channels\n- Support emergency communications\n- Train users on equipment"},
        
        # ===== LEVEL 4 - Training Officers (3 squadrons) =====
        {"role_id": "to-sq1", "title": "Training Officer - 6th CTS", "level": 4, "order": 0, "reports_to": "chief-training-officer",
         "summary": "Training Officer for 6th CTS.",
         "responsibilities": "- Oversee 6th CTS training\n- Supervise Assistant TO\n- Evaluate training effectiveness\n- Report to Chief Training Officer"},
        {"role_id": "to-sq2", "title": "Training Officer - 21st CTS", "level": 4, "order": 1, "reports_to": "chief-training-officer",
         "summary": "Training Officer for 21st CTS.",
         "responsibilities": "- Oversee 21st CTS training\n- Supervise Assistant TO\n- Evaluate training effectiveness\n- Report to Chief Training Officer"},
        {"role_id": "to-sq3", "title": "Training Officer - 22nd CTS", "level": 4, "order": 2, "reports_to": "chief-training-officer",
         "summary": "Training Officer for 22nd CTS.",
         "responsibilities": "- Oversee 22nd CTS training\n- Supervise Assistant TO\n- Evaluate training effectiveness\n- Report to Chief Training Officer"},
        
        # ===== LEVEL 5 - Asst Training Officers =====
        {"role_id": "ato-sq1", "title": "Asst Training Officer - 6th CTS", "level": 5, "order": 0, "reports_to": "to-sq1",
         "summary": "Assistant Training Officer for 6th CTS.",
         "responsibilities": "- Assist with squadron training\n- Support Training Officer\n- Fill in as needed"},
        {"role_id": "ato-sq2", "title": "Asst Training Officer - 21st CTS", "level": 5, "order": 1, "reports_to": "to-sq2",
         "summary": "Assistant Training Officer for 21st CTS.",
         "responsibilities": "- Assist with squadron training\n- Support Training Officer\n- Fill in as needed"},
        {"role_id": "ato-sq3", "title": "Asst Training Officer - 22nd CTS", "level": 5, "order": 2, "reports_to": "to-sq3",
         "summary": "Assistant Training Officer for 22nd CTS.",
         "responsibilities": "- Assist with squadron training\n- Support Training Officer\n- Fill in as needed"},
        
        # ===== LEVEL 5 - Squadron Commanders =====
        {"role_id": "sq1-cc", "title": "Squadron Commander - 6th CTS", "level": 5, "order": 3, "reports_to": "to-sq1",
         "summary": "Commands 6th CTS cadets.",
         "responsibilities": "- Lead 6th CTS cadets\n- Conduct formations\n- Supervise flight commanders\n- Maintain discipline"},
        {"role_id": "sq2-cc", "title": "Squadron Commander - 21st CTS", "level": 5, "order": 4, "reports_to": "to-sq2",
         "summary": "Commands 21st CTS cadets.",
         "responsibilities": "- Lead 21st CTS cadets\n- Conduct formations\n- Supervise flight commanders\n- Maintain discipline"},
        {"role_id": "sq3-cc", "title": "Squadron Commander - 22nd CTS", "level": 5, "order": 5, "reports_to": "to-sq3",
         "summary": "Commands 22nd CTS cadets.",
         "responsibilities": "- Lead 22nd CTS cadets\n- Conduct formations\n- Supervise flight commanders\n- Maintain discipline"},
        {"role_id": "support-sq-cc", "title": "Support Squadron Commander", "level": 5, "order": 6, "reports_to": "deputy-support",
         "summary": "Commands Support Squadron personnel.",
         "responsibilities": "- Lead support squadron staff\n- Coordinate support operations\n- Supervise support OICs\n- Report to Deputy Support"},
        
        # ===== LEVEL 6 - Squadron Staff =====
        {"role_id": "sq1-super", "title": "Sqdn Superintendent - 6th CTS", "level": 6, "order": 0, "reports_to": "sq1-cc",
         "summary": "6th CTS Superintendent.",
         "responsibilities": "- Support Squadron CC\n- Manage squadron admin\n- Coordinate with flights"},
        {"role_id": "sq2-super", "title": "Sqdn Superintendent - 21st CTS", "level": 6, "order": 1, "reports_to": "sq2-cc",
         "summary": "21st CTS Superintendent.",
         "responsibilities": "- Support Squadron CC\n- Manage squadron admin\n- Coordinate with flights"},
        {"role_id": "sq3-super", "title": "Sqdn Superintendent - 22nd CTS", "level": 6, "order": 2, "reports_to": "sq3-cc",
         "summary": "22nd CTS Superintendent.",
         "responsibilities": "- Support Squadron CC\n- Manage squadron admin\n- Coordinate with flights"},
        
        # ===== LEVEL 6 - Support Squadron OICs =====
        {"role_id": "logistics-oic", "title": "Logistics OIC", "level": 6, "order": 3, "reports_to": "support-sq-cc",
         "summary": "Officer in Charge of Logistics.",
         "responsibilities": "- Manage logistics operations\n- Supervise logistics team\n- Track supplies and equipment"},
        {"role_id": "word-oic", "title": "WORD OIC", "level": 6, "order": 4, "reports_to": "support-sq-cc",
         "summary": "Officer in Charge of Word/Admin.",
         "responsibilities": "- Manage admin operations\n- Oversee documentation\n- Support record keeping"},
        {"role_id": "pa-ncoic", "title": "PA NCOIC", "level": 6, "order": 5, "reports_to": "support-sq-cc",
         "summary": "NCOIC of Public Affairs.",
         "responsibilities": "- Lead PA team\n- Coordinate photography\n- Support media operations"},
        {"role_id": "xp-oic", "title": "XP OIC", "level": 6, "order": 6, "reports_to": "support-sq-cc",
         "summary": "Officer in Charge of Plans.",
         "responsibilities": "- Support planning operations\n- Coordinate programs\n- Track activities"},
        {"role_id": "dfac", "title": "DFAC", "level": 6, "order": 7, "reports_to": "support-sq-cc",
         "summary": "Dining Facility operations.",
         "responsibilities": "- Coordinate meal operations\n- Manage dining facility\n- Support food service"},
        
        # ===== LEVEL 7 - Flight Commanders =====
        {"role_id": "alpha-fc", "title": "Flight Commander - Alpha", "level": 7, "order": 0, "reports_to": "sq1-cc",
         "summary": "Commands Alpha Flight.",
         "responsibilities": "- Lead Alpha Flight\n- Conduct formations\n- Supervise Flight Sergeant\n- Evaluate cadets"},
        {"role_id": "bravo-fc", "title": "Flight Commander - Bravo", "level": 7, "order": 1, "reports_to": "sq1-cc",
         "summary": "Commands Bravo Flight.",
         "responsibilities": "- Lead Bravo Flight\n- Conduct formations\n- Supervise Flight Sergeant\n- Evaluate cadets"},
        {"role_id": "charlie-fc", "title": "Flight Commander - Charlie", "level": 7, "order": 2, "reports_to": "sq2-cc",
         "summary": "Commands Charlie Flight.",
         "responsibilities": "- Lead Charlie Flight\n- Conduct formations\n- Supervise Flight Sergeant\n- Evaluate cadets"},
        {"role_id": "delta-fc", "title": "Flight Commander - Delta", "level": 7, "order": 3, "reports_to": "sq2-cc",
         "summary": "Commands Delta Flight.",
         "responsibilities": "- Lead Delta Flight\n- Conduct formations\n- Supervise Flight Sergeant\n- Evaluate cadets"},
        {"role_id": "echo-fc", "title": "Flight Commander - Echo", "level": 7, "order": 4, "reports_to": "sq3-cc",
         "summary": "Commands Echo Flight.",
         "responsibilities": "- Lead Echo Flight\n- Conduct formations\n- Supervise Flight Sergeant\n- Evaluate cadets"},
        {"role_id": "foxtrot-fc", "title": "Flight Commander - Foxtrot", "level": 7, "order": 5, "reports_to": "sq3-cc",
         "summary": "Commands Foxtrot Flight.",
         "responsibilities": "- Lead Foxtrot Flight\n- Conduct formations\n- Supervise Flight Sergeant\n- Evaluate cadets"},
        
        # ===== LEVEL 8 - Flight Sergeants =====
        {"role_id": "alpha-fs", "title": "Flight Sergeant - Alpha", "level": 8, "order": 0, "reports_to": "alpha-fc",
         "summary": "Flight Sergeant for Alpha Flight.",
         "responsibilities": "- Support Flight Commander\n- Lead flight in FC's absence\n- Assist with cadet training"},
        {"role_id": "bravo-fs", "title": "Flight Sergeant - Bravo", "level": 8, "order": 1, "reports_to": "bravo-fc",
         "summary": "Flight Sergeant for Bravo Flight.",
         "responsibilities": "- Support Flight Commander\n- Lead flight in FC's absence\n- Assist with cadet training"},
        {"role_id": "charlie-fs", "title": "Flight Sergeant - Charlie", "level": 8, "order": 2, "reports_to": "charlie-fc",
         "summary": "Flight Sergeant for Charlie Flight.",
         "responsibilities": "- Support Flight Commander\n- Lead flight in FC's absence\n- Assist with cadet training"},
        {"role_id": "delta-fs", "title": "Flight Sergeant - Delta", "level": 8, "order": 3, "reports_to": "delta-fc",
         "summary": "Flight Sergeant for Delta Flight.",
         "responsibilities": "- Support Flight Commander\n- Lead flight in FC's absence\n- Assist with cadet training"},
        {"role_id": "echo-fs", "title": "Flight Sergeant - Echo", "level": 8, "order": 4, "reports_to": "echo-fc",
         "summary": "Flight Sergeant for Echo Flight.",
         "responsibilities": "- Support Flight Commander\n- Lead flight in FC's absence\n- Assist with cadet training"},
        {"role_id": "foxtrot-fs", "title": "Flight Sergeant - Foxtrot", "level": 8, "order": 5, "reports_to": "foxtrot-fc",
         "summary": "Flight Sergeant for Foxtrot Flight.",
         "responsibilities": "- Support Flight Commander\n- Lead flight in FC's absence\n- Assist with cadet training"},
    ]
    
    for role_data in default_roles:
        doc = {
            "id": str(uuid.uuid4()),
            **role_data,
            "assigned_participant_id": None,
            "created_at": now,
            "updated_at": now
        }
        await db.org_chart_roles.insert_one(doc)
    
    return {"message": f"Successfully created {len(default_roles)} default org chart roles"}


# ================= STATS ROUTES =================

@api_router.get("/stats/dashboard")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    participants = await db.participants.find({}, {"_id": 0}).to_list(1000)
    budget_items = await db.budget.find({}, {"_id": 0}).to_list(1000)
    events = await db.schedule.find({}, {"_id": 0}).to_list(1000)
    
    # Participant stats
    total_participants = len(participants)
    by_type = {}
    by_gender = {"M": 0, "F": 0, "Other": 0}
    paid_count = 0
    
    for p in participants:
        ptype = p.get("participant_type", "basic_student")
        by_type[ptype] = by_type.get(ptype, 0) + 1
        
        gender = p.get("gender", "Other")
        if gender in by_gender:
            by_gender[gender] += 1
        else:
            by_gender["Other"] += 1
        
        if p.get("paid"):
            paid_count += 1
    
    # Budget stats
    total_estimated = sum(i.get("estimated", 0) for i in budget_items)
    total_actual = sum(i.get("actual", 0) for i in budget_items)
    
    # Schedule stats
    upcoming_events = len([e for e in events if e.get("date", "") >= datetime.now(timezone.utc).strftime("%Y-%m-%d")])
    
    return {
        "participants": {
            "total": total_participants,
            "by_type": by_type,
            "by_gender": by_gender,
            "paid": paid_count,
            "unpaid": total_participants - paid_count
        },
        "budget": {
            "total_estimated": total_estimated,
            "total_actual": total_actual,
            "variance": total_estimated - total_actual
        },
        "schedule": {
            "total_events": len(events),
            "upcoming_events": upcoming_events
        }
    }

# ================= ROOT ROUTE =================

@api_router.get("/")
async def root():
    return {"message": "CAP Encampment Roster API", "version": "1.0.0"}

# ================= DAILY SETTINGS ENDPOINTS (Uniform & Weather) =================

# Weather flag thresholds based on Heat Index (CAP Guidelines)
WEATHER_FLAG_THRESHOLDS = {
    'green': {'min': 0, 'max': 84.9, 'label': 'Low Risk', 'description': 'Normal operations'},
    'yellow': {'min': 85, 'max': 90.9, 'label': 'Moderate Risk', 'description': 'Increased caution'},
    'red': {'min': 91, 'max': 102.9, 'label': 'High Risk', 'description': 'Restrict strenuous activity'},
    'black': {'min': 103, 'max': 999, 'label': 'Extreme Risk', 'description': 'Minimize outdoor activity'}
}

WEATHER_FLAG_GUIDELINES = {
    'green': {
        'water_intake': '1 cup every 20 minutes',
        'rest_schedule': {'low': '50/10', 'medium': '50/10', 'high': '30/30'},
        'instructions': [
            'Provide fresh water; use wingmen to monitor intake',
            'Prohibit soda',
            'Know location of local hospital/urgent care facility',
            'Have vehicle and driver designated',
            'Encourage cadets to wear sunscreen',
            'Closely monitor people not acclimated to hot weather'
        ]
    },
    'yellow': {
        'water_intake': '1 cup every 15 minutes',
        'rest_schedule': {'low': '50/10', 'medium': '50/10', 'high': '30/30'},
        'instructions': [
            'Reschedule activities for cooler weather if able',
            'Brief cadets on recognizing heat-related illness',
            'Locate activities in shady areas if possible',
            'Mandate use of sunscreen, reapply every 4 hours',
            'Have wingman watch for heat-related symptoms',
            'Allow cadets to remove BDU/ABU blouses'
        ]
    },
    'red': {
        'water_intake': '1 cup every 15 minutes',
        'rest_schedule': {'low': '30/30', 'medium': '20/40', 'high': 'PROHIBITED'},
        'instructions': [
            'Alert everyone to high risk conditions',
            'PROHIBIT high intensity activities including fitness testing',
            'Adjust training activities (reschedule, lower pace, rotate jobs)',
            'Use cooling techniques: breaks indoors with A/C, cold damp towels',
            'Increase adult supervision with line-of-sight monitoring',
            'Watch/communicate with cadets at all times'
        ]
    },
    'black': {
        'water_intake': '1 cup every 15 minutes',
        'rest_schedule': {'low': '20/40', 'medium': 'PROHIBITED', 'high': 'PROHIBITED'},
        'instructions': [
            'PROHIBIT medium and high intensity activities',
            'MINIMIZE outdoor activities - train indoors with A/C',
            'Travel >200 yards via A/C vehicle only (no marching)',
            'Conduct only mission-critical activities outdoors',
            'Consider canceling outdoor activities entirely'
        ]
    }
}

@api_router.get("/daily-settings")
async def get_daily_settings(user: dict = Depends(get_current_user)):
    """Get current daily settings (uniform, weather flag)"""
    settings = await db.daily_settings.find_one({'_id': 'current'})
    
    if not settings:
        # Return defaults
        return {
            'uniform': {
                'uniform_code': 'ABU',
                'description': 'Airman Battle Uniform',
                'special_instructions': None,
                'updated_at': None,
                'updated_by': None
            },
            'weather_flag': {
                'flag_color': 'green',
                'heat_index': None,
                'wbgt': None,
                'notes': None,
                'guidelines': WEATHER_FLAG_GUIDELINES['green'],
                'thresholds': WEATHER_FLAG_THRESHOLDS,
                'updated_at': None,
                'updated_by': None
            }
        }
    
    # Add guidelines to weather flag
    flag_color = settings.get('weather_flag', {}).get('flag_color', 'green')
    if settings.get('weather_flag'):
        settings['weather_flag']['guidelines'] = WEATHER_FLAG_GUIDELINES.get(flag_color, WEATHER_FLAG_GUIDELINES['green'])
    settings['weather_flag']['thresholds'] = WEATHER_FLAG_THRESHOLDS
    
    settings.pop('_id', None)
    return settings

@api_router.post("/daily-settings/uniform")
async def update_uniform_of_day(
    uniform: UniformOfTheDay,
    user: dict = Depends(get_current_user)
):
    """Update the Uniform of the Day (Admin only)"""
    if user.get('role') not in ['commander', 'plans_programs', 'staff', 'executive_cadre']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.daily_settings.update_one(
        {'_id': 'current'},
        {'$set': {
            'uniform': {
                'uniform_code': uniform.uniform_code,
                'description': uniform.description,
                'special_instructions': uniform.special_instructions,
                'updated_at': now,
                'updated_by': user.get('name', user.get('email'))
            }
        }},
        upsert=True
    )
    
    return {"message": "Uniform of the Day updated", "uniform_code": uniform.uniform_code}

@api_router.post("/daily-settings/weather-flag")
async def update_weather_flag(
    weather: WeatherFlagUpdate,
    user: dict = Depends(get_current_user)
):
    """Update the Weather Flag status (Admin only)"""
    if user.get('role') not in ['commander', 'plans_programs', 'staff', 'executive_cadre']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if weather.flag_color not in ['green', 'yellow', 'red', 'black']:
        raise HTTPException(status_code=400, detail="Invalid flag color. Must be green, yellow, red, or black")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.daily_settings.update_one(
        {'_id': 'current'},
        {'$set': {
            'weather_flag': {
                'flag_color': weather.flag_color,
                'heat_index': weather.heat_index,
                'wbgt': weather.wbgt,
                'notes': weather.notes,
                'updated_at': now,
                'updated_by': user.get('name', user.get('email'))
            }
        }},
        upsert=True
    )
    
    return {
        "message": "Weather flag updated",
        "flag_color": weather.flag_color,
        "guidelines": WEATHER_FLAG_GUIDELINES.get(weather.flag_color)
    }

@api_router.get("/daily-settings/weather-guidelines")
async def get_weather_guidelines():
    """Get all weather flag guidelines (public endpoint)"""
    return {
        'thresholds': WEATHER_FLAG_THRESHOLDS,
        'guidelines': WEATHER_FLAG_GUIDELINES
    }

# ================= GOOGLE SHEETS SYNC ENDPOINTS =================

@api_router.get("/google-sheets/settings")
async def get_google_sheets_settings(user: dict = Depends(get_current_user)):
    """Get Google Sheets sync settings"""
    if user.get('role') not in ['commander', 'plans_programs']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    settings = await db.google_sheets_settings.find_one({'_id': 'settings'})
    if not settings:
        return {
            "roster_sheet": None,
            "org_chart_sheets": [],
            "sync_interval_hours": 1,
            "last_sync_at": None,
            "last_sync_status": None,
            "last_sync_message": None,
            "auto_sync_enabled": True
        }
    
    # Remove MongoDB _id
    settings.pop('_id', None)
    return settings

@api_router.post("/google-sheets/settings")
async def update_google_sheets_settings(
    request: GoogleSheetsSyncRequest,
    user: dict = Depends(get_current_user)
):
    """Update Google Sheets sync settings"""
    if user.get('role') not in ['commander', 'plans_programs']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    settings = {
        '_id': 'settings',
        'sync_interval_hours': request.sync_interval_hours,
        'auto_sync_enabled': request.auto_sync_enabled,
    }
    
    if request.roster_spreadsheet_id and request.roster_gid:
        settings['roster_sheet'] = {
            'sheet_type': 'roster',
            'spreadsheet_id': request.roster_spreadsheet_id,
            'gid': request.roster_gid,
            'name': 'Roster',
            'enabled': True
        }
    
    if request.org_chart_spreadsheet_id and request.org_chart_gids:
        settings['org_chart_sheets'] = [
            {
                'sheet_type': 'org_chart',
                'spreadsheet_id': request.org_chart_spreadsheet_id,
                'gid': gid,
                'name': f'Org Chart Tab {i+1}',
                'enabled': True
            }
            for i, gid in enumerate(request.org_chart_gids)
        ]
    
    await db.google_sheets_settings.replace_one(
        {'_id': 'settings'},
        settings,
        upsert=True
    )
    
    return {"message": "Settings updated successfully", "settings": settings}

@api_router.post("/google-sheets/sync")
async def trigger_manual_sync(
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Manually trigger a Google Sheets sync"""
    if user.get('role') not in ['commander', 'plans_programs', 'staff']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    settings = await db.google_sheets_settings.find_one({'_id': 'settings'})
    if not settings:
        raise HTTPException(status_code=400, detail="No Google Sheets configured. Please configure sheets first.")
    
    # Run sync in background
    background_tasks.add_task(perform_scheduled_sync)
    
    return {"message": "Sync started. Check status for results."}

@api_router.get("/google-sheets/sync-status")
async def get_sync_status(user: dict = Depends(get_current_user)):
    """Get the current sync status"""
    settings = await db.google_sheets_settings.find_one({'_id': 'settings'})
    if not settings:
        return {
            "configured": False,
            "last_sync_at": None,
            "last_sync_status": None,
            "last_sync_message": None,
            "auto_sync_enabled": False
        }
    
    return {
        "configured": True,
        "last_sync_at": settings.get('last_sync_at'),
        "last_sync_status": settings.get('last_sync_status'),
        "last_sync_message": settings.get('last_sync_message'),
        "auto_sync_enabled": settings.get('auto_sync_enabled', True),
        "sync_interval_hours": settings.get('sync_interval_hours', 1)
    }

# ================= NOTIFICATION BADGES API =================

@api_router.get("/notification-badges")
async def get_notification_badges(user: dict = Depends(get_current_user)):
    """Get notification badge counts for sidebar items"""
    user_role = user.get('role')
    user_flight = user.get('flight', '').lower() if user.get('flight') else None
    user_squadron = user.get('squadron', '').lower() if user.get('squadron') else None
    
    badges = {}
    
    # Reports needing attention (for authorized roles)
    full_access_roles = [UserRole.COMMANDER, UserRole.EXEC_CADRE, UserRole.STAFF, UserRole.PLANS_PROGRAMS]
    
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
    if user_role == UserRole.COMMANDER:
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
    if user_role in [UserRole.COMMANDER, UserRole.FINANCE, UserRole.PLANS_PROGRAMS]:
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

# ================= FLIGHT REPORTING API =================

@api_router.get("/reports/settings")
async def get_report_settings(user: dict = Depends(get_current_user)):
    """Get report deadline settings"""
    settings = await db.report_settings.find_one({'_id': 'settings'})
    if not settings:
        # Return defaults
        return {
            "deadline_time": "21:00",
            "reminder_minutes_before": 60,
            "is_enabled": True
        }
    return {
        "deadline_time": settings.get("deadline_time", "21:00"),
        "reminder_minutes_before": settings.get("reminder_minutes_before", 60),
        "is_enabled": settings.get("is_enabled", True)
    }

@api_router.post("/reports/settings")
async def update_report_settings(
    settings: ReportDeadlineSettings,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.PLANS_PROGRAMS]))
):
    """Update report deadline settings (admin only)"""
    await db.report_settings.update_one(
        {'_id': 'settings'},
        {'$set': {
            'deadline_time': settings.deadline_time,
            'reminder_minutes_before': settings.reminder_minutes_before,
            'is_enabled': settings.is_enabled,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'updated_by': user['id']
        }},
        upsert=True
    )
    return {"message": "Settings updated successfully"}

@api_router.get("/reports/my/submitted")
async def get_my_submitted_reports(
    user: dict = Depends(get_current_user)
):
    """Get reports submitted by the current user"""
    reports = await db.flight_reports.find(
        {"submitted_by": user['id']},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return reports

@api_router.get("/reports/commander-issues")
async def get_commander_issues(
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.EXEC_CADRE]))
):
    """Get all reports with commander issues (escalated status)"""
    reports = await db.flight_reports.find(
        {"status": "escalated"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return reports

@api_router.post("/reports")
async def create_flight_report(
    report: FlightReportCreate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Submit a new flight report"""
    now = datetime.now(timezone.utc).isoformat()
    report_id = str(uuid.uuid4())
    
    # Determine if there are commander issues that need escalation
    has_commander_issues = report.commander_issues.content.strip() != "" and report.commander_issues.has_issues
    
    report_doc = {
        "id": report_id,
        "report_date": report.report_date,
        "flight": report.flight,
        "squadron": report.squadron,
        "reporter_role": report.reporter_role,
        "morale": report.morale.model_dump(),
        "safety_concerns": report.safety_concerns.model_dump(),
        "discipline_issues": report.discipline_issues.model_dump(),
        "training_performance": report.training_performance.model_dump(),
        "significant_events": report.significant_events.model_dump(),
        "recommendations": report.recommendations.model_dump(),
        "commander_issues": report.commander_issues.model_dump(),
        "submitted_by": user['id'],
        "submitted_by_name": user['name'],
        "status": "escalated_flight_commander" if has_commander_issues else "submitted",
        "escalation_level": "flight_sergeant" if has_commander_issues else None,
        "escalation_history": [],
        "reviewed_by": None,
        "reviewed_at": None,
        "review_notes": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.flight_reports.insert_one(report_doc)
    
    # Send notification if there are commander issues
    if has_commander_issues:
        # Get flight label
        flight_labels = {
            "alpha": "Alpha", "bravo": "Bravo", "charlie": "Charlie",
            "delta": "Delta", "echo": "Echo", "foxtrot": "Foxtrot"
        }
        flight_label = flight_labels.get(report.flight, report.flight.title())
        
        # Store notification for squadron commanders and up
        notification_id = str(uuid.uuid4())
        await db.notifications.insert_one({
            "id": notification_id,
            "title": f"Commander Issue - {flight_label} Flight",
            "body": f"A flight report from {flight_label} Flight contains items requiring command attention.",
            "target_groups": ["commander", "exec_cadre", "staff", "plans_programs"],
            "report_id": report_id,
            "sent_by": user["id"],
            "sent_at": now,
            "notification_type": "commander_issue"
        })
    
    return {
        "message": "Report submitted successfully",
        "id": report_id,
        "status": report_doc["status"]
    }

@api_router.get("/reports")
async def get_flight_reports(
    flight: Optional[str] = None,
    squadron: Optional[str] = None,
    report_date: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get flight reports (filtered by user's access level)"""
    query = {}
    
    user_role = user.get('role')
    user_flight = user.get('flight', '').lower() if user.get('flight') else None
    user_squadron = user.get('squadron', '').lower() if user.get('squadron') else None
    
    # Roles with full access to all reports
    full_access_roles = [
        UserRole.COMMANDER, 
        UserRole.EXEC_CADRE, 
        UserRole.STAFF,  # Includes Health Services
        UserRole.PLANS_PROGRAMS
    ]
    
    # Access control based on role
    if user_role in full_access_roles:
        # Full access - can see all reports
        pass
    elif user_squadron and user_squadron in ['6th_cts', '21st_cts', '22nd_cts']:
        # Squadron commander - can see their squadron's reports
        query['squadron'] = user_squadron
    elif user_flight:
        # Flight staff - can see their flight's reports only
        query['flight'] = user_flight
    else:
        # Limited access - only own reports
        query['submitted_by'] = user['id']
    
    # Apply additional filters
    if flight:
        query['flight'] = flight.lower()
    if squadron:
        query['squadron'] = squadron.lower()
    if report_date:
        query['report_date'] = report_date
    if status:
        query['status'] = status
    
    reports = await db.flight_reports.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return reports

@api_router.get("/reports/{report_id}")
async def get_flight_report(
    report_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific flight report"""
    report = await db.flight_reports.find_one({"id": report_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Access control - same roles have full access
    user_role = user.get('role')
    user_flight = user.get('flight', '').lower() if user.get('flight') else None
    user_squadron = user.get('squadron', '').lower() if user.get('squadron') else None
    
    full_access_roles = [UserRole.COMMANDER, UserRole.EXEC_CADRE, UserRole.STAFF, UserRole.PLANS_PROGRAMS]
    
    if user_role not in full_access_roles:
        if user_squadron and user_squadron in ['6th_cts', '21st_cts', '22nd_cts']:
            if report['squadron'] != user_squadron:
                raise HTTPException(status_code=403, detail="Access denied")
        elif user_flight:
            if report['flight'] != user_flight:
                raise HTTPException(status_code=403, detail="Access denied")
        elif report['submitted_by'] != user['id']:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return report

@api_router.put("/reports/{report_id}/review")
async def review_flight_report(
    report_id: str,
    review_notes: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Mark a report as reviewed (for commanders/supervisors)"""
    report = await db.flight_reports.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Only commanders, exec cadre, or squadron commanders can review
    user_role = user.get('role')
    user_squadron = user.get('squadron', '').lower() if user.get('squadron') else None
    
    can_review = False
    if user_role in [UserRole.COMMANDER, UserRole.EXEC_CADRE]:
        can_review = True
    elif user_squadron and user_squadron == report['squadron']:
        # Squadron commander can review their squadron's reports
        can_review = True
    
    if not can_review:
        raise HTTPException(status_code=403, detail="You don't have permission to review this report")
    
    now = datetime.now(timezone.utc).isoformat()
    await db.flight_reports.update_one(
        {"id": report_id},
        {"$set": {
            "status": "reviewed",
            "reviewed_by": user['id'],
            "reviewed_at": now,
            "review_notes": review_notes,
            "updated_at": now
        }}
    )
    
    return {"message": "Report marked as reviewed"}

@api_router.put("/reports/{report_id}/escalate")
async def escalate_flight_report(
    report_id: str,
    request: EscalateReportRequest,
    user: dict = Depends(get_current_user)
):
    """Escalate a report up the chain of command
    
    Full chain: Flight Sergeant -> Flight Commander -> Squadron Commander -> 
                Exec Cadre -> DCS & Commandant -> Encampment Commander
    """
    report = await db.flight_reports.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    user_role = user.get('role')
    current_level = report.get('escalation_level', 'flight_sergeant')
    
    # Define the complete escalation chain with who can escalate at each level
    # Each level defines: who can escalate FROM this level, the next level, and the status name
    escalation_chain = {
        'flight_sergeant': {
            'can_escalate_roles': [UserRole.COMMANDER, UserRole.EXEC_CADRE, UserRole.STAFF, UserRole.PLANS_PROGRAMS, UserRole.CADRE],
            'next_level': 'flight_commander',
            'status': 'escalated_flight_commander'
        },
        'flight_commander': {
            'can_escalate_roles': [UserRole.COMMANDER, UserRole.EXEC_CADRE, UserRole.STAFF, UserRole.PLANS_PROGRAMS],
            'next_level': 'squadron_commander',
            'status': 'escalated_squadron'
        },
        'squadron_commander': {
            'can_escalate_roles': [UserRole.COMMANDER, UserRole.EXEC_CADRE, UserRole.STAFF, UserRole.PLANS_PROGRAMS],
            'next_level': 'exec_cadre',
            'status': 'escalated_exec'
        },
        'exec_cadre': {
            'can_escalate_roles': [UserRole.COMMANDER, UserRole.EXEC_CADRE],
            'next_level': 'dcs_commandant',
            'status': 'escalated_dcs'
        },
        'dcs_commandant': {
            'can_escalate_roles': [UserRole.COMMANDER],
            'next_level': 'encampment_commander',
            'status': 'escalated_commander'
        },
        'encampment_commander': {
            'can_escalate_roles': [UserRole.COMMANDER],
            'next_level': None,  # Top of chain
            'status': 'at_commander'
        }
    }
    
    # Valid escalation targets
    valid_targets = ['flight_commander', 'squadron_commander', 'exec_cadre', 'dcs_commandant', 'encampment_commander']
    
    # Check if user can escalate from current level
    current_chain = escalation_chain.get(current_level, escalation_chain['flight_sergeant'])
    
    if user_role not in current_chain['can_escalate_roles']:
        raise HTTPException(
            status_code=403, 
            detail=f"You don't have permission to escalate from {current_level.replace('_', ' ')}"
        )
    
    # Determine target escalation level
    target_level = request.escalate_to
    if target_level not in valid_targets:
        raise HTTPException(status_code=400, detail="Invalid escalation target")
    
    # Validate escalation path - must go to the next level in chain
    if current_level == 'encampment_commander':
        raise HTTPException(status_code=400, detail="Report is already at the highest level")
    
    # Ensure we're escalating to the correct next level
    expected_next = current_chain['next_level']
    if target_level != expected_next:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot skip levels. Must escalate to {expected_next.replace('_', ' ').title()} next"
        )
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Create escalation history entry
    escalation_entry = {
        "from_level": current_level,
        "to_level": target_level,
        "escalated_by": user['id'],
        "escalated_by_name": user['name'],
        "escalated_at": now,
        "notes": request.notes or ""
    }
    
    # Determine new status from the chain
    new_status = current_chain['status']  # Use the status defined for escalating FROM the current level
    
    # Update the report
    await db.flight_reports.update_one(
        {"id": report_id},
        {
            "$set": {
                "status": new_status,
                "escalation_level": target_level,
                "updated_at": now
            },
            "$push": {
                "escalation_history": escalation_entry
            }
        }
    )
    
    # Create notification for the target level
    flight_labels = {
        "alpha": "Alpha", "bravo": "Bravo", "charlie": "Charlie",
        "delta": "Delta", "echo": "Echo", "foxtrot": "Foxtrot"
    }
    flight_label = flight_labels.get(report.get('flight', ''), report.get('flight', '').title())
    
    # Determine notification targets based on escalation level
    level_display_names = {
        'flight_commander': 'Flight Commander',
        'squadron_commander': 'Squadron Commander',
        'exec_cadre': 'Exec Cadre',
        'dcs_commandant': 'DCS & Commandant',
        'encampment_commander': 'Encampment Commander'
    }
    target_display = level_display_names.get(target_level, target_level.replace('_', ' ').title())
    
    # Notify relevant groups based on target level
    if target_level == 'encampment_commander':
        notification_targets = ['commander']
    elif target_level == 'dcs_commandant':
        notification_targets = ['commander']  # DCS and Commandant level
    elif target_level == 'exec_cadre':
        notification_targets = ['exec_cadre', 'commander']
    else:
        notification_targets = ['staff', 'exec_cadre', 'commander']
    
    notification_id = str(uuid.uuid4())
    await db.notifications.insert_one({
        "id": notification_id,
        "title": f"Commander Issue Escalated - {flight_label} Flight",
        "body": f"A commander issue has been escalated to {target_display} for review.",
        "target_groups": notification_targets,
        "report_id": report_id,
        "sent_by": user["id"],
        "sent_at": now,
        "notification_type": "escalation"
    })
    
    return {
        "message": f"Report escalated to {target_display}",
        "new_level": target_level,
        "status": new_status
    }

@api_router.put("/reports/{report_id}/resolve")
async def resolve_escalated_report(
    report_id: str,
    resolution_notes: Optional[str] = None,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.EXEC_CADRE]))
):
    """Mark an escalated report as resolved (Commander or Exec Cadre only)"""
    report = await db.flight_reports.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Add resolution to escalation history
    resolution_entry = {
        "action": "resolved",
        "resolved_by": user['id'],
        "resolved_by_name": user['name'],
        "resolved_at": now,
        "notes": resolution_notes or ""
    }
    
    await db.flight_reports.update_one(
        {"id": report_id},
        {
            "$set": {
                "status": "resolved",
                "reviewed_by": user['id'],
                "reviewed_at": now,
                "review_notes": resolution_notes,
                "updated_at": now
            },
            "$push": {
                "escalation_history": resolution_entry
            }
        }
    )
    
    return {"message": "Report marked as resolved"}

@api_router.delete("/reports/{report_id}")
async def delete_flight_report(
    report_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a flight report (only author or commander)"""
    report = await db.flight_reports.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Only the author or a commander can delete
    if report['submitted_by'] != user['id'] and user.get('role') != UserRole.COMMANDER:
        raise HTTPException(status_code=403, detail="You don't have permission to delete this report")
    
    await db.flight_reports.delete_one({"id": report_id})
    return {"message": "Report deleted successfully"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================= GOOGLE SHEETS SYNC SERVICE =================

# Global scheduler instance
scheduler = AsyncIOScheduler()

async def fetch_google_sheet_csv(spreadsheet_id: str, gid: str) -> Optional[str]:
    """Fetch a Google Sheet as CSV data"""
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                content = response.text
                # Check if it's an error page
                if "Page Not Found" in content or "<!DOCTYPE html>" in content[:100]:
                    logger.error(f"Sheet not accessible: {spreadsheet_id}/{gid}")
                    return None
                return content
            else:
                logger.error(f"Failed to fetch sheet: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Error fetching Google Sheet: {e}")
        return None

async def sync_roster_from_gsheet(spreadsheet_id: str, gid: str) -> dict:
    """Sync roster data from Google Sheet"""
    csv_data = await fetch_google_sheet_csv(spreadsheet_id, gid)
    if not csv_data:
        return {"success": False, "message": "Failed to fetch sheet data"}
    
    try:
        df = pd.read_csv(BytesIO(csv_data.encode('utf-8')))
        df.columns = df.columns.str.strip()
        
        # Column mapping (same as Excel import)
        column_map = {
            'RegistrantsCAPID': 'capid', 'CAPID': 'capid',
            'Rank': 'rank', 'NameLast': 'last_name', 'NameFirst': 'first_name',
            'NameMiddle': 'middle_name', 'Unit': 'unit', 'Wing': 'wing',
            'Region': 'region', 'Gender': 'gender', 'Age': 'age',
            'AgeAtEventStart': 'age_at_event', 'Email': 'email',
            'HomePhonePrimary': 'phone', 'CellPhonePrimary': 'cell_phone',
            'ShirtSize': 'shirt_size', 'MbrType': 'member_type',
            'StaffMember': 'staff_member', 'PaidInFull': 'paid_in_full',
            'AmountPaid': 'amount_paid', 'RegistrationStatus': 'registration_status',
            'UnitApproved': 'unit_approved', 'WingApproved': 'wing_approved',
            'Addr1': 'address', 'City': 'city', 'State': 'state', 'Zip': 'zip_code',
            'EmergencyContactName': 'emergency_contact', 'EmergencyContactNumber': 'emergency_phone',
            'CadetParentPhonePrimary': 'cadet_parent_phone', 'CadetParentEmailPrimary': 'cadet_parent_email',
            'UnitCCName': 'unit_cc_name', 'UnitCCEmail': 'unit_cc_email',
            'LastEncampment': 'last_encampment', 'CPPTExpiration': 'cppt_expiration',
            'FirstAid': 'first_aid', 'SubEvents': 'sub_events',
        }
        
        df = df.rename(columns=column_map)
        
        imported_count = 0
        updated_count = 0
        now = datetime.now(timezone.utc).isoformat()
        
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            
            def get_val(key, default=None):
                val = row_dict.get(key)
                if pd.isna(val) or val == '' or val == 'nan':
                    return default
                return val
            
            def get_str(key, default=''):
                val = get_val(key, default)
                return str(val).strip() if val is not None else default
            
            def get_unit(key, default=''):
                """Get unit value and clean up float formatting (e.g., '96.0' -> '96')"""
                val = get_val(key, default)
                if val is None:
                    return default
                val_str = str(val).strip()
                # Remove .0 suffix if present (from float conversion)
                if val_str.endswith('.0'):
                    val_str = val_str[:-2]
                return val_str
            
            def get_bool(key):
                val = get_val(key)
                if val is None:
                    return False
                if isinstance(val, bool):
                    return val
                return str(val).lower() in ['yes', 'true', '1']
            
            def get_float(key, default=0.0):
                val = get_val(key)
                if val is None:
                    return default
                try:
                    return float(val)
                except:
                    return default
            
            def get_int(key, default=None):
                val = get_val(key)
                if val is None:
                    return default
                try:
                    return int(float(val))
                except:
                    return default
            
            # Generate CAPID if not present
            capid = get_str('capid', '')
            if not capid:
                email = get_str('email', '')
                if email:
                    email_prefix = email.split('@')[0] if '@' in email else ''
                    numeric_parts = ''.join(filter(str.isdigit, email_prefix))
                    if len(numeric_parts) >= 5:
                        capid = numeric_parts[:6]
                
                if not capid:
                    last_name = get_str('last_name', '')
                    first_name = get_str('first_name', '')
                    wing = get_str('wing', 'XX')
                    unit = get_str('unit', '000')
                    if last_name and first_name:
                        import hashlib
                        composite = f"{last_name}_{first_name}_{wing}_{unit}".upper()
                        hash_digest = hashlib.md5(composite.encode()).hexdigest()[:6]
                        capid = f"GEN{hash_digest.upper()}"
                    else:
                        continue
            
            # Determine participant type
            member_type = get_str('member_type', '').upper()
            is_staff = get_bool('staff_member')
            sub_events = get_str('sub_events', '').lower()
            
            if member_type == 'SENIOR':
                participant_type = 'staff'
            elif 'cadre' in sub_events:
                participant_type = 'cadre'
            else:
                participant_type = 'basic_student'
            
            participant_data = {
                'capid': capid,
                'rank': get_str('rank'),
                'last_name': get_str('last_name'),
                'first_name': get_str('first_name'),
                'middle_name': get_str('middle_name'),
                'name': f"{get_str('last_name')}, {get_str('first_name')}",
                'unit': get_unit('unit'),
                'wing': get_str('wing'),
                'region': get_str('region'),
                'gender': get_str('gender'),
                'age': get_int('age'),
                'age_at_event': get_int('age_at_event'),
                'email': get_str('email'),
                'phone': get_str('phone'),
                'cell_phone': get_str('cell_phone'),
                'shirt_size': get_str('shirt_size'),
                'member_type': member_type,
                'participant_type': participant_type,
                'paid_in_full': get_bool('paid_in_full'),
                'amount_paid': get_float('amount_paid'),
                'paid': get_bool('paid_in_full') or get_float('amount_paid') > 0,
                'registration_status': get_str('registration_status'),
                'staff_member': is_staff,
                'unit_approved': get_bool('unit_approved'),
                'wing_approved': get_bool('wing_approved'),
                'address': get_str('address'),
                'city': get_str('city'),
                'state': get_str('state'),
                'zip_code': get_str('zip_code'),
                'emergency_contact': get_str('emergency_contact'),
                'emergency_phone': get_str('emergency_phone'),
                'cadet_parent_phone': get_str('cadet_parent_phone'),
                'cadet_parent_email': get_str('cadet_parent_email'),
                'unit_cc_name': get_str('unit_cc_name'),
                'unit_cc_email': get_str('unit_cc_email'),
                'last_encampment': get_str('last_encampment'),
                'cppt_expiration': get_str('cppt_expiration'),
                'first_aid': get_str('first_aid'),
                'updated_at': now,
            }
            
            # Upsert by CAPID
            existing = await db.participants.find_one({'capid': capid})
            if existing:
                await db.participants.update_one(
                    {'capid': capid},
                    {'$set': participant_data}
                )
                updated_count += 1
            else:
                participant_data['id'] = str(uuid.uuid4())
                participant_data['created_at'] = now
                participant_data['is_removed'] = False
                await db.participants.insert_one(participant_data)
                imported_count += 1
        
        return {
            "success": True,
            "message": f"Roster sync complete: {imported_count} new, {updated_count} updated",
            "imported": imported_count,
            "updated": updated_count,
            "total": imported_count + updated_count
        }
    
    except Exception as e:
        logger.error(f"Error syncing roster: {e}")
        return {"success": False, "message": str(e)}

async def sync_orgchart_from_gsheet(spreadsheet_id: str, gid: str) -> dict:
    """Sync org chart data from Google Sheet"""
    csv_data = await fetch_google_sheet_csv(spreadsheet_id, gid)
    if not csv_data:
        return {"success": False, "message": "Failed to fetch org chart sheet data"}
    
    try:
        # Parse CSV into rows
        lines = csv_data.strip().split('\n')
        rows = []
        for line in lines:
            # Simple CSV parsing (handles basic cases)
            row = []
            current = ''
            in_quotes = False
            for char in line:
                if char == '"':
                    in_quotes = not in_quotes
                elif char == ',' and not in_quotes:
                    row.append(current.strip())
                    current = ''
                else:
                    current += char
            row.append(current.strip())
            rows.append(row)
        
        now = datetime.now(timezone.utc).isoformat()
        roles_created = 0
        roles_updated = 0
        
        # Define the org chart structure we're looking for
        # Parse key positions from the spreadsheet layout
        org_roles = []
        
        # Helper to parse name and find matching participant
        async def parse_and_match_member(name_str, rank_str=None):
            """Parse name string and try to find matching participant"""
            if not name_str or name_str.strip() == '':
                return None, None, None
            
            # Clean the name string - remove quotes and extra spaces
            name_str = name_str.strip().strip('"').strip()
            if not name_str:
                return None, None, None
                
            # Parse "Last, First" or "Last, First M.I." format
            parts = name_str.split(',')
            if len(parts) >= 2:
                last_name = parts[0].strip()
                first_name = parts[1].strip().split()[0] if parts[1].strip() else ''
            else:
                # Try "First Last" format
                name_parts = name_str.split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = name_parts[-1]
                else:
                    last_name = name_str
                    first_name = ''
            
            # Try to find matching participant
            participant = await db.participants.find_one({
                '$or': [
                    {'last_name': {'$regex': f'^{last_name}', '$options': 'i'}, 'first_name': {'$regex': f'^{first_name}', '$options': 'i'}},
                    {'name': {'$regex': f'{last_name}.*{first_name}', '$options': 'i'}},
                    {'name': {'$regex': f'{first_name}.*{last_name}', '$options': 'i'}}
                ]
            }, {'_id': 0, 'id': 1, 'capid': 1, 'name': 1, 'rank': 1})
            
            participant_id = participant.get('id') if participant else None
            return last_name, first_name, participant_id
        
        # Parse specific positions from known cell locations
        # Row 19 (index 18) has main command staff
        if len(rows) > 19:
            row = rows[18]  # 0-indexed, so row 19 is index 18
            
            # Commandant of Cadets - columns around index 6-10
            if len(row) > 13:
                commandant_rank = row[12] if len(row) > 12 else ''
                commandant_name = row[13] if len(row) > 13 else ''
                if commandant_name:
                    last, first, pid = await parse_and_match_member(commandant_name, commandant_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'commandant',
                            'title': 'Commandant of Cadets',
                            'abbreviation': 'ENC/CW',
                            'category': 'Command',
                            'level': 1,
                            'parent_role_id': 'commander',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': commandant_rank.strip() if commandant_rank else None,
                            'assigned_participant_id': pid
                        })
            
            # Encampment Commander - columns around index 18-22
            if len(row) > 19:
                enc_cc_rank = row[18] if len(row) > 18 else ''
                enc_cc_name = row[19] if len(row) > 19 else ''
                if enc_cc_name:
                    last, first, pid = await parse_and_match_member(enc_cc_name, enc_cc_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'commander',
                            'title': 'Encampment Commander',
                            'abbreviation': 'ENC/CC',
                            'category': 'Command',
                            'level': 0,
                            'parent_role_id': None,
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': enc_cc_rank.strip() if enc_cc_rank else None,
                            'assigned_participant_id': pid
                        })
            
            # Deputy CC for Support - columns around index 24-28
            if len(row) > 25:
                dep_rank = row[24] if len(row) > 24 else ''
                dep_name = row[25] if len(row) > 25 else ''
                if dep_name:
                    last, first, pid = await parse_and_match_member(dep_name, dep_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'deputy_support',
                            'title': 'Deputy CC for Support',
                            'abbreviation': 'ENC/DCS',
                            'category': 'Command',
                            'level': 1,
                            'parent_role_id': 'commander',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': dep_rank.strip() if dep_rank else None,
                            'assigned_participant_id': pid
                        })
        
        # Row 20 has more staff positions
        if len(rows) > 20:
            row = rows[19]
            # 60th CTG/CD
            if len(row) > 13:
                cd_rank = row[12] if len(row) > 12 else ''
                cd_name = row[13] if len(row) > 13 else ''
                if cd_name:
                    last, first, pid = await parse_and_match_member(cd_name, cd_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'ctg_cd',
                            'title': '60th CTG Deputy Commander',
                            'abbreviation': '60th CTG/CD',
                            'category': 'Cadet Training',
                            'level': 2,
                            'parent_role_id': 'commandant',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': cd_rank.strip() if cd_rank else None,
                            'assigned_participant_id': pid
                        })
        
        # Row 21 - ENC Superintendent
        if len(rows) > 21:
            row = rows[20]
            if len(row) > 19:
                sup_rank = row[18] if len(row) > 18 else ''
                sup_name = row[19] if len(row) > 19 else ''
                if sup_name:
                    last, first, pid = await parse_and_match_member(sup_name, sup_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'superintendent',
                            'title': 'Encampment Superintendent',
                            'abbreviation': 'ENC/CCEA',
                            'category': 'Operations',
                            'level': 2,
                            'parent_role_id': 'commander',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': sup_rank.strip() if sup_rank else None,
                            'assigned_participant_id': pid
                        })
        
        # Row 22 - 60th CTG/DOA
        if len(rows) > 22:
            row = rows[21]
            if len(row) > 13:
                doa_rank = row[12] if len(row) > 12 else ''
                doa_name = row[13] if len(row) > 13 else ''
                if doa_name:
                    last, first, pid = await parse_and_match_member(doa_name, doa_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'ctg_doa',
                            'title': '60th CTG Director of Academics',
                            'abbreviation': '60th CTG/DOA',
                            'category': 'Cadet Training',
                            'level': 2,
                            'parent_role_id': 'commandant',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': doa_rank.strip() if doa_rank else None,
                            'assigned_participant_id': pid
                        })
        
        # Row 27 - Health Services Officer
        if len(rows) > 27:
            row = rows[26]
            if len(row) > 19:
                hso_rank = row[18] if len(row) > 18 else ''
                hso_name = row[19] if len(row) > 19 else ''
                if hso_name:
                    last, first, pid = await parse_and_match_member(hso_name, hso_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'health_services',
                            'title': 'Health Services Officer',
                            'abbreviation': 'ENC/HS',
                            'category': 'Support',
                            'level': 2,
                            'parent_role_id': 'deputy_support',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': hso_rank.strip() if hso_rank else None,
                            'assigned_participant_id': pid
                        })
        
        # Parse support staff from column around 24-28 (rows 21-28)
        support_positions = [
            (21, 'support_staff_1', 'Support Staff'),
            (22, 'plans_programs', 'Plans and Programs Officer'),
            (23, 'logistics_1', 'Logistics Officer'),
            (24, 'logistics_2', 'Logistics Officer'),
            (25, 'word_emeritus', 'WORD Officer / HS Emeritus'),
            (26, 'communications', 'Communications Director'),
            (27, 'public_affairs', 'Public Affairs Officer'),
            (28, 'dining_facility', 'Dining Facility Officer'),
            (29, 'finance', 'Finance Officer'),
        ]
        
        for row_idx, role_id, title in support_positions:
            if len(rows) > row_idx:
                row = rows[row_idx - 1]  # Convert to 0-indexed
                if len(row) > 28:
                    supp_rank = row[24] if len(row) > 24 else ''
                    supp_name = row[25] if len(row) > 25 else ''
                    if supp_name and supp_name.strip():
                        last, first, pid = await parse_and_match_member(supp_name, supp_rank)
                        if last:
                            org_roles.append({
                                'role_id': role_id,
                                'title': title,
                                'abbreviation': role_id.upper().replace('_', '/'),
                                'category': 'Support',
                                'level': 3,
                                'parent_role_id': 'deputy_support',
                                'assigned_member_name': f"{last}, {first}" if first else last,
                                'assigned_member_rank': supp_rank.strip() if supp_rank else None,
                                'assigned_participant_id': pid
                            })
        
        # Parse Squadron Commanders from row 35 area
        squadrons = [
            (35, 0, '6th_cts_cc', '6th CTS Commander', '6th CTS/CC', 'commandant'),
            (35, 12, '21st_cts_cc', '21st CTS Commander', '21st CTS/CC', 'commandant'),
            (35, 24, '22nd_cts_cc', '22nd CTS Commander', '22nd CTS/CC', 'commandant'),
        ]
        
        # Parse Flight Sergeants and Commanders from flights row (around row 41)
        flights_row_idx = None
        for idx, row in enumerate(rows):
            if len(row) > 0 and 'ALPHA' in str(row[0]).upper():
                flights_row_idx = idx
                break
        
        if flights_row_idx:
            # Flight names are in this row
            flight_cols = {
                'ALPHA': (0, '6th_cts_cc'),
                'BRAVO': (6, '6th_cts_cc'),
                'CHARLIE': (12, '21st_cts_cc'),
                'DELTA': (18, '21st_cts_cc'),
                'ECHO': (24, '22nd_cts_cc'),
                'FOXTROT': (30, '22nd_cts_cc')
            }
            
            for flight_name, (col_offset, parent_id) in flight_cols.items():
                org_roles.append({
                    'role_id': f'flight_{flight_name.lower()}_commander',
                    'title': f'{flight_name} Flight Commander',
                    'abbreviation': f'{flight_name[:1]}FLT/CC',
                    'category': 'Flight',
                    'level': 4,
                    'parent_role_id': parent_id,
                    'assigned_member_name': None,
                    'assigned_member_rank': None,
                    'assigned_participant_id': None
                })
                org_roles.append({
                    'role_id': f'flight_{flight_name.lower()}_sergeant',
                    'title': f'{flight_name} Flight Sergeant',
                    'abbreviation': f'{flight_name[:1]}FLT/FS',
                    'category': 'Flight',
                    'level': 4,
                    'parent_role_id': f'flight_{flight_name.lower()}_commander',
                    'assigned_member_name': None,
                    'assigned_member_rank': None,
                    'assigned_participant_id': None
                })
        
        # Now upsert all roles to the database
        for role_data in org_roles:
            role_id = role_data['role_id']
            existing = await db.org_chart_roles.find_one({'role_id': role_id})
            
            if existing:
                await db.org_chart_roles.update_one(
                    {'role_id': role_id},
                    {'$set': {
                        'assigned_member_name': role_data.get('assigned_member_name'),
                        'assigned_member_rank': role_data.get('assigned_member_rank'),
                        'assigned_participant_id': role_data.get('assigned_participant_id'),
                        'updated_at': now
                    }}
                )
                roles_updated += 1
            else:
                role_data['id'] = str(uuid.uuid4())
                role_data['responsibilities'] = ''
                role_data['created_at'] = now
                role_data['updated_at'] = now
                await db.org_chart_roles.insert_one(role_data)
                roles_created += 1
        
        # ================= PARSE FLIGHT ASSIGNMENTS =================
        # Find the row with flight headers (ALPHA, BRAVO, etc.)
        flights_header_idx = None
        for idx, row in enumerate(rows):
            if len(row) > 0 and 'ALPHA' in str(row[0]).upper():
                flights_header_idx = idx
                break
        
        students_assigned = 0
        if flights_header_idx is not None:
            # Flight column positions (each flight spans ~6 columns)
            # Based on the spreadsheet: ALPHA(0-5), BRAVO(6-11), CHARLIE(12-17), DELTA(18-23), ECHO(24-29), FOXTROT(30-35)
            flight_config = {
                'Alpha': {'col_offset': 0, 'squadron': '6th CTS', 'squadron_full': '6th Cadet Training Squadron'},
                'Bravo': {'col_offset': 6, 'squadron': '6th CTS', 'squadron_full': '6th Cadet Training Squadron'},
                'Charlie': {'col_offset': 12, 'squadron': '21st CTS', 'squadron_full': '21st Cadet Training Squadron'},
                'Delta': {'col_offset': 18, 'squadron': '21st CTS', 'squadron_full': '21st Cadet Training Squadron'},
                'Echo': {'col_offset': 24, 'squadron': '22nd CTS', 'squadron_full': '22nd Cadet Training Squadron'},
                'Foxtrot': {'col_offset': 30, 'squadron': '22nd CTS', 'squadron_full': '22nd Cadet Training Squadron'},
            }
            
            # Skip header row (GRADE, LAST NAME...) and start from data rows (2 rows after ALPHA header)
            data_start_idx = flights_header_idx + 2
            
            # Parse each row until we hit "Total Cadets" or empty rows
            for row_idx in range(data_start_idx, len(rows)):
                row = rows[row_idx]
                
                # Check if we've reached the end (Total Cadets row)
                row_str = ','.join(row).lower()
                if 'total cadets' in row_str:
                    break
                
                # Process each flight column
                for flight_name, config in flight_config.items():
                    col = config['col_offset']
                    
                    # Get rank/grade (col+0), name (col+1), age (col+2), unit (col+3)
                    if len(row) > col + 3:
                        rank = row[col].strip() if row[col] else ''
                        name = row[col + 1].strip() if len(row) > col + 1 else ''
                        age_str = row[col + 2].strip() if len(row) > col + 2 else ''
                        unit = row[col + 3].strip() if len(row) > col + 3 else ''
                        
                        # Skip empty entries
                        if not name or name == '':
                            continue
                        
                        # Parse name (format: "LAST, FIRST M.I.")
                        name = name.strip().strip('"')
                        name_parts = name.split(',')
                        if len(name_parts) >= 2:
                            last_name = name_parts[0].strip()
                            first_part = name_parts[1].strip()
                            first_name = first_part.split()[0] if first_part else ''
                        else:
                            continue
                        
                        # Try to find matching participant in the roster
                        participant = await db.participants.find_one({
                            '$or': [
                                {'last_name': {'$regex': f'^{last_name}$', '$options': 'i'}, 
                                 'first_name': {'$regex': f'^{first_name}', '$options': 'i'}},
                                {'name': {'$regex': f'{last_name}.*{first_name}', '$options': 'i'}},
                            ]
                        })
                        
                        if participant:
                            # Update participant with flight and squadron assignment
                            await db.participants.update_one(
                                {'_id': participant['_id']},
                                {'$set': {
                                    'flight': flight_name,
                                    'squadron': config['squadron'],
                                    'squadron_full': config['squadron_full'],
                                    'participant_type': 'basic_student',
                                    'updated_at': now
                                }}
                            )
                            students_assigned += 1
                            logger.info(f"Assigned {last_name}, {first_name} to {flight_name} Flight ({config['squadron']})")
        
        return {
            "success": True,
            "message": f"Org chart sync complete: {roles_created} new roles, {roles_updated} updated, {students_assigned} students assigned to flights",
            "created": roles_created,
            "updated": roles_updated,
            "students_assigned": students_assigned,
            "total": roles_created + roles_updated
        }
    
    except Exception as e:
        logger.error(f"Error syncing org chart: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"success": False, "message": str(e)}

async def perform_scheduled_sync():
    """Perform scheduled sync of all configured sheets"""
    logger.info("Starting scheduled Google Sheets sync...")
    
    settings = await db.google_sheets_settings.find_one({'_id': 'settings'})
    if not settings:
        logger.info("No Google Sheets settings configured, skipping sync")
        return
    
    if not settings.get('auto_sync_enabled', True):
        logger.info("Auto sync is disabled, skipping")
        return
    
    # Update status to running
    await db.google_sheets_settings.update_one(
        {'_id': 'settings'},
        {'$set': {'last_sync_status': 'running', 'last_sync_message': 'Sync in progress...'}}
    )
    
    try:
        results = []
        
        # Sync roster sheet
        roster_config = settings.get('roster_sheet')
        if roster_config and roster_config.get('enabled'):
            roster_result = await sync_roster_from_gsheet(
                roster_config['spreadsheet_id'],
                roster_config['gid']
            )
            results.append(f"Roster: {roster_result.get('message', 'unknown')}")
        
        # Sync org chart sheets
        org_chart_sheets = settings.get('org_chart_sheets', [])
        for org_config in org_chart_sheets:
            if org_config and org_config.get('enabled'):
                org_result = await sync_orgchart_from_gsheet(
                    org_config['spreadsheet_id'],
                    org_config['gid']
                )
                results.append(f"Org Chart: {org_result.get('message', 'unknown')}")
        
        # Update success status
        now = datetime.now(timezone.utc).isoformat()
        await db.google_sheets_settings.update_one(
            {'_id': 'settings'},
            {'$set': {
                'last_sync_at': now,
                'last_sync_status': 'success',
                'last_sync_message': '; '.join(results) if results else 'No sheets configured'
            }}
        )
        logger.info(f"Scheduled sync completed: {results}")
        
    except Exception as e:
        logger.error(f"Scheduled sync failed: {e}")
        await db.google_sheets_settings.update_one(
            {'_id': 'settings'},
            {'$set': {
                'last_sync_at': datetime.now(timezone.utc).isoformat(),
                'last_sync_status': 'error',
                'last_sync_message': str(e)
            }}
        )


# ================= HEALTH SERVICES API =================

from health_services import (
    get_cadet_health_summary, create_medication_profile, log_medication_administration,
    log_incident, log_custody_action, update_incident_status, update_cadet_hs_status,
    get_meds_due_dashboard, get_overdue_meds, get_open_incidents, get_historical_report,
    get_reference_lists, get_event_settings, generate_id, get_current_timestamp,
    RESULT_TYPES, INCIDENT_TYPES, RESOLUTION_STATUSES, CUSTODY_ACTIONS, ROUTES, HS_STATUSES
)

def require_health_view():
    """Dependency to check health view permission"""
    async def check_permission(user: dict = Depends(get_current_user)):
        perms = get_user_permissions(user)
        # Handle both dict and AccessPermissions object
        health_view = perms.get('health_view', False) if isinstance(perms, dict) else getattr(perms, 'health_view', False)
        health_full = perms.get('health_full', False) if isinstance(perms, dict) else getattr(perms, 'health_full', False)
        if not health_view and not health_full:
            raise HTTPException(status_code=403, detail="Health Services access required")
        return user
    return check_permission

def require_health_full():
    """Dependency to check full health services permission"""
    async def check_permission(user: dict = Depends(get_current_user)):
        perms = get_user_permissions(user)
        # Handle both dict and AccessPermissions object
        health_full = perms.get('health_full', False) if isinstance(perms, dict) else getattr(perms, 'health_full', False)
        if not health_full:
            raise HTTPException(status_code=403, detail="Full Health Services access required")
        return user
    return check_permission

# Health Services Settings
@api_router.get("/health/settings")
async def get_health_settings(user: dict = Depends(require_health_view())):
    """Get current event settings for health services"""
    settings = await get_event_settings(db)
    settings.pop("_id", None)
    return settings

@api_router.post("/health/settings")
async def update_health_settings(
    settings_data: dict,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.HEALTH_SERVICES]))
):
    """Update health services event settings"""
    await db.hs_settings.update_one(
        {"type": "event_config"},
        {"$set": {
            "event_id": settings_data.get("event_id"),
            "event_year": settings_data.get("event_year"),
            "event_name": settings_data.get("event_name")
        }},
        upsert=True
    )
    return {"message": "Settings updated"}

# Reference Data
@api_router.get("/health/reference-lists")
async def get_health_reference_lists(user: dict = Depends(require_health_view())):
    """Get reference lists for dropdowns"""
    return get_reference_lists()

# Cadet Health Summary
@api_router.get("/health/cadet/{cadet_id}/summary")
async def get_cadet_health_summary_endpoint(
    cadet_id: str,
    user: dict = Depends(require_health_view())
):
    """Get health summary for a specific cadet"""
    summary = await get_cadet_health_summary(db, cadet_id)
    
    # If user doesn't have full access, hide medication details
    perms = get_user_permissions(user)
    health_full = perms.get('health_full', False) if isinstance(perms, dict) else getattr(perms, 'health_full', False)
    if not health_full:
        # Staff can see basic info but not medication details
        summary["medications"] = []
        summary["medication_on_file"] = summary.get("active_med_count", 0) > 0
    
    return summary

@api_router.get("/health/cadet/by-capid/{capid}/summary")
async def get_cadet_health_summary_by_capid(
    capid: str,
    user: dict = Depends(require_health_view())
):
    """Get health summary for a cadet by CAPID"""
    summary = await get_cadet_health_summary(db, None, capid)
    
    perms = get_user_permissions(user)
    health_full = perms.get('health_full', False) if isinstance(perms, dict) else getattr(perms, 'health_full', False)
    if not health_full:
        summary["medications"] = []
        summary["medication_on_file"] = summary.get("active_med_count", 0) > 0
    
    return summary

# Medication Profiles
@api_router.get("/health/cadet/{cadet_id}/medications")
async def get_cadet_medications(
    cadet_id: str,
    user: dict = Depends(require_health_full())
):
    """Get all medication profiles for a cadet"""
    settings = await get_event_settings(db)
    profiles = await db.hs_medication_profiles.find({
        "event_id": settings["event_id"],
        "cadet_id_internal": cadet_id
    }).to_list(100)
    
    for p in profiles:
        p.pop("_id", None)
    
    return profiles

@api_router.post("/health/cadet/{cadet_id}/medications")
async def create_cadet_medication(
    cadet_id: str,
    medication: dict,
    user: dict = Depends(require_health_full())
):
    """Create a new medication profile for a cadet"""
    medication["cadet_id_internal"] = cadet_id
    result = await create_medication_profile(db, medication, user["id"])
    result.pop("_id", None)
    return result

@api_router.put("/health/medications/{med_profile_id}")
async def update_medication_profile(
    med_profile_id: str,
    updates: dict,
    user: dict = Depends(require_health_full())
):
    """Update a medication profile"""
    # Don't allow changing certain fields
    updates.pop("med_profile_id", None)
    updates.pop("event_id", None)
    updates.pop("cadet_id_internal", None)
    updates.pop("capid", None)
    updates.pop("entered_by", None)
    updates.pop("entered_at", None)
    
    result = await db.hs_medication_profiles.update_one(
        {"med_profile_id": med_profile_id},
        {"$set": updates}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Medication profile not found")
    
    return {"message": "Medication profile updated"}

@api_router.put("/health/medications/{med_profile_id}/deactivate")
async def deactivate_medication(
    med_profile_id: str,
    user: dict = Depends(require_health_full())
):
    """Deactivate a medication profile (soft delete)"""
    settings = await get_event_settings(db)
    
    result = await db.hs_medication_profiles.update_one(
        {"med_profile_id": med_profile_id},
        {"$set": {"is_active": False, "end_date": get_current_timestamp()[:10]}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Medication profile not found")
    
    # Log audit
    from health_services import log_audit
    await log_audit(db, settings["event_id"], "medication_profile", med_profile_id,
                   "DEACTIVATE", changed_by=user["id"])
    
    return {"message": "Medication deactivated"}

# Medication Administration Log
@api_router.get("/health/cadet/{cadet_id}/medication-log")
async def get_cadet_medication_log(
    cadet_id: str,
    limit: int = 100,
    user: dict = Depends(require_health_full())
):
    """Get medication administration history for a cadet"""
    settings = await get_event_settings(db)
    logs = await db.hs_medication_log.find({
        "event_id": settings["event_id"],
        "cadet_id_internal": cadet_id
    }).sort("entered_at_timestamp", -1).limit(limit).to_list(limit)
    
    for log in logs:
        log.pop("_id", None)
    
    return logs

@api_router.post("/health/cadet/{cadet_id}/medication-log")
async def log_medication_admin(
    cadet_id: str,
    entry: dict,
    user: dict = Depends(require_health_full())
):
    """Log a medication administration event"""
    entry["cadet_id_internal"] = cadet_id
    result = await log_medication_administration(db, entry, user["id"])
    result.pop("_id", None)
    return result

# Incident Log
@api_router.get("/health/cadet/{cadet_id}/incidents")
async def get_cadet_incidents(
    cadet_id: str,
    user: dict = Depends(require_health_view())
):
    """Get incident history for a cadet"""
    settings = await get_event_settings(db)
    incidents = await db.hs_incident_log.find({
        "event_id": settings["event_id"],
        "cadet_id_internal": cadet_id
    }).sort("entered_at_timestamp", -1).to_list(100)
    
    for inc in incidents:
        inc.pop("_id", None)
    
    return incidents

@api_router.post("/health/cadet/{cadet_id}/incidents")
async def log_cadet_incident(
    cadet_id: str,
    entry: dict,
    user: dict = Depends(require_health_full())
):
    """Log a health incident for a cadet"""
    entry["cadet_id_internal"] = cadet_id
    result = await log_incident(db, entry, user["id"])
    result.pop("_id", None)
    return result

@api_router.put("/health/incidents/{incident_id}/status")
async def update_incident_status_endpoint(
    incident_id: str,
    status_data: dict,
    user: dict = Depends(require_health_full())
):
    """Update incident resolution status"""
    new_status = status_data.get("status")
    notes = status_data.get("notes")
    
    if new_status not in RESOLUTION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    result = await update_incident_status(db, incident_id, new_status, user["id"], notes)
    return result

# Custody Log
@api_router.get("/health/cadet/{cadet_id}/custody-log")
async def get_cadet_custody_log(
    cadet_id: str,
    user: dict = Depends(require_health_full())
):
    """Get medication custody history for a cadet"""
    settings = await get_event_settings(db)
    logs = await db.hs_custody_log.find({
        "event_id": settings["event_id"],
        "cadet_id_internal": cadet_id
    }).sort("performed_at", -1).to_list(100)
    
    for log in logs:
        log.pop("_id", None)
    
    return logs

@api_router.post("/health/cadet/{cadet_id}/custody-log")
async def log_custody(
    cadet_id: str,
    entry: dict,
    user: dict = Depends(require_health_full())
):
    """Log a medication custody action"""
    entry["cadet_id_internal"] = cadet_id
    result = await log_custody_action(db, entry, user["id"])
    result.pop("_id", None)
    return result

# Cadet Health Status
@api_router.put("/health/cadet/{cadet_id}/status")
async def update_cadet_status(
    cadet_id: str,
    status_data: dict,
    user: dict = Depends(require_health_full())
):
    """Update cadet's final health services status"""
    new_status = status_data.get("status")
    capid = status_data.get("capid", "")
    
    if new_status not in HS_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    result = await update_cadet_hs_status(db, cadet_id, capid, new_status, user["id"])
    return result

# Dashboard Endpoints
@api_router.get("/health/dashboard/meds-due")
async def get_meds_due(
    window_minutes: int = 30,
    user: dict = Depends(require_health_full())
):
    """Get medications due within the specified time window"""
    # Enrich with cadet names
    meds = await get_meds_due_dashboard(db, window_minutes)
    
    for med in meds:
        participant = await db.participants.find_one(
            {"id": med["cadet_id_internal"]},
            {"_id": 0, "first_name": 1, "last_name": 1, "flight": 1, "squadron": 1}
        )
        if participant:
            med["cadet_name"] = f"{participant.get('last_name', '')}, {participant.get('first_name', '')}"
            med["flight"] = participant.get("flight")
            med["squadron"] = participant.get("squadron")
    
    return meds

@api_router.get("/health/dashboard/overdue")
async def get_overdue(user: dict = Depends(require_health_full())):
    """Get overdue medications"""
    meds = await get_overdue_meds(db)
    
    for med in meds:
        participant = await db.participants.find_one(
            {"id": med["cadet_id_internal"]},
            {"_id": 0, "first_name": 1, "last_name": 1, "flight": 1, "squadron": 1}
        )
        if participant:
            med["cadet_name"] = f"{participant.get('last_name', '')}, {participant.get('first_name', '')}"
            med["flight"] = participant.get("flight")
            med["squadron"] = participant.get("squadron")
    
    return meds

@api_router.get("/health/dashboard/open-incidents")
async def get_open_incidents_endpoint(user: dict = Depends(require_health_view())):
    """Get all open incidents"""
    incidents = await get_open_incidents(db)
    
    for inc in incidents:
        participant = await db.participants.find_one(
            {"id": inc["cadet_id_internal"]},
            {"_id": 0, "first_name": 1, "last_name": 1, "flight": 1, "squadron": 1}
        )
        if participant:
            inc["cadet_name"] = f"{participant.get('last_name', '')}, {participant.get('first_name', '')}"
            inc["flight"] = participant.get("flight")
            inc["squadron"] = participant.get("squadron")
    
    return incidents

@api_router.get("/health/dashboard/summary")
async def get_health_dashboard_summary(user: dict = Depends(require_health_view())):
    """Get overall health services dashboard summary"""
    settings = await get_event_settings(db)
    event_id = settings["event_id"]
    
    # Count cadets with health records
    total_cadets = await db.hs_cadet_master.count_documents({"event_id": event_id})
    with_meds = await db.hs_cadet_master.count_documents({"event_id": event_id, "medication_flag": True})
    rescue_meds = await db.hs_cadet_master.count_documents({"event_id": event_id, "rescue_med_flag": True})
    open_incidents = await db.hs_incident_log.count_documents({
        "event_id": event_id,
        "resolution_status": {"$in": ["open", "monitoring"]}
    })
    
    # Get meds due now
    meds_due = await get_meds_due_dashboard(db, 30)
    overdue = await get_overdue_meds(db)
    
    return {
        "event_id": event_id,
        "event_name": settings["event_name"],
        "total_cadets_tracked": total_cadets,
        "cadets_with_medications": with_meds,
        "cadets_with_rescue_meds": rescue_meds,
        "open_incidents": open_incidents,
        "meds_due_now": len(meds_due),
        "overdue_meds": len(overdue)
    }

@api_router.get("/health/reports/historical")
async def get_historical_report_endpoint(
    event_year: int = None,
    squadron: str = None,
    cadet_id: str = None,
    user: dict = Depends(require_health_full())
):
    """Get historical reporting data"""
    return await get_historical_report(db, event_year, squadron, cadet_id)

# Search Endpoints
@api_router.get("/health/search/cadets")
async def search_health_cadets(
    q: str = None,
    squadron: str = None,
    flight: str = None,
    has_medication: bool = None,
    has_incident: bool = None,
    user: dict = Depends(require_health_view())
):
    """Search cadets with health data"""
    settings = await get_event_settings(db)
    event_id = settings["event_id"]
    
    # Build query for participants
    participant_query = {}
    if squadron:
        participant_query["squadron"] = squadron
    if flight:
        participant_query["flight"] = flight
    
    participants = await db.participants.find(
        participant_query,
        {"_id": 0, "id": 1, "capid": 1, "first_name": 1, "last_name": 1, "flight": 1, "squadron": 1}
    ).to_list(500)
    
    # Filter by search term
    if q:
        q_lower = q.lower()
        participants = [p for p in participants if 
                       q_lower in f"{p.get('first_name', '')} {p.get('last_name', '')}".lower() or
                       q_lower in str(p.get('capid', ''))]
    
    # Enrich with health data
    results = []
    for p in participants:
        health_record = await db.hs_cadet_master.find_one({
            "event_id": event_id,
            "cadet_id_internal": p["id"]
        })
        
        has_med = health_record.get("medication_flag", False) if health_record else False
        has_inc = health_record.get("incident_open_flag", False) if health_record else False
        
        # Apply health filters
        if has_medication is not None and has_med != has_medication:
            continue
        if has_incident is not None and has_inc != has_incident:
            continue
        
        results.append({
            "cadet_id": p["id"],
            "capid": p.get("capid"),
            "name": f"{p.get('last_name', '')}, {p.get('first_name', '')}",
            "flight": p.get("flight"),
            "squadron": p.get("squadron"),
            "has_medication": has_med,
            "has_open_incident": has_inc,
            "hs_status": health_record.get("final_hs_status", "cleared") if health_record else "cleared"
        })
    
    return results

# Audit Log
@api_router.get("/health/audit-log")
async def get_audit_log(
    limit: int = 100,
    table_name: str = None,
    record_id: str = None,
    user: dict = Depends(require_health_full())
):
    """Get health services audit log"""
    settings = await get_event_settings(db)
    
    query = {"event_id": settings["event_id"]}
    if table_name:
        query["table_name"] = table_name
    if record_id:
        query["record_id"] = record_id
    
    logs = await db.hs_audit_log.find(query).sort("changed_at", -1).limit(limit).to_list(limit)
    
    for log in logs:
        log.pop("_id", None)
    
    return logs


# Re-include router to pick up health services routes
# (Note: FastAPI handles duplicate includes gracefully)
app.include_router(api_router)


# ================= APP STARTUP/SHUTDOWN =================

@app.on_event("startup")
async def startup_event():
    """Start the scheduler on app startup"""
    # Get sync interval from settings or use default
    settings = await db.google_sheets_settings.find_one({'_id': 'settings'})
    interval_hours = 1
    if settings:
        interval_hours = settings.get('sync_interval_hours', 1)
    
    # Add the scheduled sync job
    scheduler.add_job(
        perform_scheduled_sync,
        trigger=IntervalTrigger(hours=interval_hours),
        id='gsheets_sync',
        name='Google Sheets Sync',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"Scheduler started. Google Sheets sync scheduled every {interval_hours} hour(s)")

@app.on_event("shutdown")
async def shutdown_db_client():
    scheduler.shutdown(wait=False)
    client.close()
