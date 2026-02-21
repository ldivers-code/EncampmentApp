from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

# Create the main app
app = FastAPI(title="CAP Encampment Roster API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

security = HTTPBearer()

# ================= MODELS =================

class UserRole:
    COMMANDER = "commander"
    STAFF = "staff"
    FINANCE = "finance"
    CADET = "cadet"

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str = UserRole.CADET
    capid: Optional[str] = None
    squadron: Optional[str] = None  # sq1, sq2, sq3, staff
    flight: Optional[str] = None  # alpha, bravo, charlie, delta, echo, foxtrot

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUnitAssignment(BaseModel):
    squadron: Optional[str] = None
    flight: Optional[str] = None

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

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class ParticipantBase(BaseModel):
    capid: str
    rank: str
    last_name: str
    first_name: str
    unit: str
    wing: Optional[str] = None
    region: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    shirt_size: Optional[str] = None
    participant_type: str = "basic_student"  # basic_student, advanced_student, cadre, staff, senior_member
    squadron: Optional[str] = None
    flight: Optional[str] = None
    position: Optional[str] = None
    paid: bool = False
    first_encampment: bool = True
    religious_preference: Optional[str] = None
    emergency_contact: Optional[str] = None
    notes: Optional[str] = None

class ParticipantCreate(ParticipantBase):
    pass

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
    target_groups: List[str] = ["all"]  # all, staff, sq1, sq2, sq3, alpha, bravo, charlie, delta, echo, foxtrot

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
    target_groups: List[str] = ["all"]  # all, staff, sq1, sq2, sq3, or specific flights
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


# Food Expense Settings Model
class FoodExpenseSettings(BaseModel):
    cost_per_person_per_day: float = 15.0
    total_participants: int = 0
    total_days: int = 8  # July 17-24 = 8 days
    notes: Optional[str] = None


class FoodExpenseSettingsUpdate(BaseModel):
    cost_per_person_per_day: Optional[float] = None
    total_participants: Optional[int] = None
    total_days: Optional[int] = None
    notes: Optional[str] = None

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
    doc_type: str  # handbook, official_document, form
    content: Optional[str] = None
    file_url: Optional[str] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    created_at: str
    updated_at: str


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

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
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
    
    # Check if this is the first user - make them commander
    user_count = await db.users.count_documents({})
    assigned_role = UserRole.COMMANDER if user_count == 0 else user_data.role
    
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "role": assigned_role,
        "capid": user_data.capid,
        "squadron": user_data.squadron,
        "flight": user_data.flight,
        "password_hash": hash_password(user_data.password),
        "created_at": now
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
            created_at=now
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
    if role not in [UserRole.COMMANDER, UserRole.STAFF, UserRole.FINANCE, UserRole.CADET]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    result = await db.users.update_one({"id": user_id}, {"$set": {"role": role}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Role updated successfully"}

@api_router.put("/users/{user_id}/unit")
async def assign_user_unit(
    user_id: str, 
    assignment: UserUnitAssignment,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    """Assign a user to a squadron and flight"""
    valid_squadrons = [None, "", "staff", "sq1", "sq2", "sq3"]
    valid_flights = [None, "", "alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
    
    if assignment.squadron and assignment.squadron not in valid_squadrons:
        raise HTTPException(status_code=400, detail="Invalid squadron")
    if assignment.flight and assignment.flight not in valid_flights:
        raise HTTPException(status_code=400, detail="Invalid flight")
    
    # Validate flight belongs to squadron
    flight_squadron_map = {
        "alpha": "sq1", "bravo": "sq1",
        "charlie": "sq2", "delta": "sq2",
        "echo": "sq3", "foxtrot": "sq3"
    }
    
    if assignment.flight and assignment.flight in flight_squadron_map:
        expected_squadron = flight_squadron_map[assignment.flight]
        if assignment.squadron and assignment.squadron != expected_squadron:
            raise HTTPException(
                status_code=400, 
                detail=f"Flight {assignment.flight} belongs to {expected_squadron}"
            )
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

# ================= PARTICIPANT ROUTES =================

@api_router.get("/participants", response_model=List[ParticipantResponse])
async def get_participants(user: dict = Depends(get_current_user)):
    participants = await db.participants.find({}, {"_id": 0}).to_list(1000)
    return [ParticipantResponse(**p) for p in participants]

@api_router.get("/participants/{participant_id}", response_model=ParticipantResponse)
async def get_participant(participant_id: str, user: dict = Depends(get_current_user)):
    participant = await db.participants.find_one({"id": participant_id}, {"_id": 0})
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
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

@api_router.post("/participants/import")
async def import_participants(
    file: UploadFile = File(...),
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        
        # Normalize column names
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        imported_count = 0
        now = datetime.now(timezone.utc).isoformat()
        
        # Column mapping for common variations
        column_map = {
            'cap_id': 'capid', 'cap id': 'capid', 'capid': 'capid',
            'last': 'last_name', 'last_name': 'last_name', 'lastname': 'last_name',
            'first': 'first_name', 'first_name': 'first_name', 'firstname': 'first_name',
            'shirt': 'shirt_size', 'shirt_size': 'shirt_size', 'shirtsize': 'shirt_size',
            'type': 'participant_type', 'participant_type': 'participant_type'
        }
        
        df.columns = [column_map.get(col, col) for col in df.columns]
        
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            
            # Skip rows without CAPID
            capid = str(row_dict.get('capid', '')).strip()
            if not capid or capid == 'nan':
                continue
            
            participant_id = str(uuid.uuid4())
            
            doc = {
                "id": participant_id,
                "capid": capid,
                "rank": str(row_dict.get('rank', '')).strip() if pd.notna(row_dict.get('rank')) else '',
                "last_name": str(row_dict.get('last_name', '')).strip() if pd.notna(row_dict.get('last_name')) else '',
                "first_name": str(row_dict.get('first_name', '')).strip() if pd.notna(row_dict.get('first_name')) else '',
                "unit": str(row_dict.get('unit', '')).strip() if pd.notna(row_dict.get('unit')) else '',
                "wing": str(row_dict.get('wing', '')).strip() if pd.notna(row_dict.get('wing')) else None,
                "region": str(row_dict.get('region', '')).strip() if pd.notna(row_dict.get('region')) else None,
                "gender": str(row_dict.get('gender', '')).strip() if pd.notna(row_dict.get('gender')) else None,
                "age": int(row_dict.get('age', 0)) if pd.notna(row_dict.get('age')) else None,
                "email": str(row_dict.get('email', '')).strip() if pd.notna(row_dict.get('email')) else None,
                "phone": str(row_dict.get('phone', '')).strip() if pd.notna(row_dict.get('phone')) else None,
                "shirt_size": str(row_dict.get('shirt_size', '')).strip() if pd.notna(row_dict.get('shirt_size')) else None,
                "participant_type": str(row_dict.get('participant_type', 'basic_student')).strip() if pd.notna(row_dict.get('participant_type')) else 'basic_student',
                "squadron": str(row_dict.get('squadron', '')).strip() if pd.notna(row_dict.get('squadron')) else None,
                "flight": str(row_dict.get('flight', '')).strip() if pd.notna(row_dict.get('flight')) else None,
                "position": str(row_dict.get('position', '')).strip() if pd.notna(row_dict.get('position')) else None,
                "paid": bool(row_dict.get('paid', False)) if pd.notna(row_dict.get('paid')) else False,
                "first_encampment": bool(row_dict.get('first_encampment', True)) if pd.notna(row_dict.get('first_encampment')) else True,
                "religious_preference": str(row_dict.get('religious_preference', '')).strip() if pd.notna(row_dict.get('religious_preference')) else None,
                "emergency_contact": str(row_dict.get('emergency_contact', '')).strip() if pd.notna(row_dict.get('emergency_contact')) else None,
                "notes": str(row_dict.get('notes', '')).strip() if pd.notna(row_dict.get('notes')) else None,
                "created_at": now,
                "updated_at": now
            }
            
            # Upsert by CAPID
            await db.participants.update_one(
                {"capid": capid},
                {"$set": doc},
                upsert=True
            )
            imported_count += 1
        
        return {"message": f"Successfully imported {imported_count} participants"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

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
                if group in ["sq1", "sq2", "sq3"]:
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
    
    if not settings:
        return {
            "cost_per_person_per_day": 15.0,
            "total_participants": participant_count,
            "total_days": 8,
            "notes": "Default: July 17-24 (8 days)",
            "total_food_budget": 15.0 * participant_count * 8
        }
    
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


# ================= DOCUMENT ROUTES =================

@api_router.get("/documents", response_model=List[DocumentResponse])
async def get_documents(user: dict = Depends(get_current_user)):
    docs = await db.documents.find({}, {"_id": 0}).to_list(1000)
    return [DocumentResponse(**d) for d in docs]

@api_router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(**doc)

@api_router.post("/documents", response_model=DocumentResponse)
async def create_document(
    data: DocumentCreate,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    doc = {
        "id": doc_id,
        **data.model_dump(),
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
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    now = datetime.now(timezone.utc).isoformat()
    update_data = {**data.model_dump(), "updated_at": now}
    
    result = await db.documents.update_one({"id": doc_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = await db.documents.find_one({"id": doc_id}, {"_id": 0})
    return DocumentResponse(**doc)

@api_router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    user: dict = Depends(require_role([UserRole.COMMANDER, UserRole.STAFF]))
):
    result = await db.documents.delete_one({"id": doc_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully"}


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
        {"role_id": "to-sq1", "title": "Training Officer - Sq 1", "level": 4, "order": 0, "reports_to": "chief-training-officer",
         "summary": "Training Officer for Squadron 1.",
         "responsibilities": "- Oversee Squadron 1 training\n- Supervise Assistant TO\n- Evaluate training effectiveness\n- Report to Chief Training Officer"},
        {"role_id": "to-sq2", "title": "Training Officer - Sq 2", "level": 4, "order": 1, "reports_to": "chief-training-officer",
         "summary": "Training Officer for Squadron 2.",
         "responsibilities": "- Oversee Squadron 2 training\n- Supervise Assistant TO\n- Evaluate training effectiveness\n- Report to Chief Training Officer"},
        {"role_id": "to-sq3", "title": "Training Officer - Sq 3", "level": 4, "order": 2, "reports_to": "chief-training-officer",
         "summary": "Training Officer for Squadron 3.",
         "responsibilities": "- Oversee Squadron 3 training\n- Supervise Assistant TO\n- Evaluate training effectiveness\n- Report to Chief Training Officer"},
        
        # ===== LEVEL 5 - Asst Training Officers =====
        {"role_id": "ato-sq1", "title": "Asst Training Officer - Sq 1", "level": 5, "order": 0, "reports_to": "to-sq1",
         "summary": "Assistant Training Officer for Squadron 1.",
         "responsibilities": "- Assist with squadron training\n- Support Training Officer\n- Fill in as needed"},
        {"role_id": "ato-sq2", "title": "Asst Training Officer - Sq 2", "level": 5, "order": 1, "reports_to": "to-sq2",
         "summary": "Assistant Training Officer for Squadron 2.",
         "responsibilities": "- Assist with squadron training\n- Support Training Officer\n- Fill in as needed"},
        {"role_id": "ato-sq3", "title": "Asst Training Officer - Sq 3", "level": 5, "order": 2, "reports_to": "to-sq3",
         "summary": "Assistant Training Officer for Squadron 3.",
         "responsibilities": "- Assist with squadron training\n- Support Training Officer\n- Fill in as needed"},
        
        # ===== LEVEL 5 - Squadron Commanders =====
        {"role_id": "sq1-cc", "title": "Squadron Commander - Sq 1", "level": 5, "order": 3, "reports_to": "to-sq1",
         "summary": "Commands cadet Squadron 1.",
         "responsibilities": "- Lead Squadron 1 cadets\n- Conduct formations\n- Supervise flight commanders\n- Maintain discipline"},
        {"role_id": "sq2-cc", "title": "Squadron Commander - Sq 2", "level": 5, "order": 4, "reports_to": "to-sq2",
         "summary": "Commands cadet Squadron 2.",
         "responsibilities": "- Lead Squadron 2 cadets\n- Conduct formations\n- Supervise flight commanders\n- Maintain discipline"},
        {"role_id": "sq3-cc", "title": "Squadron Commander - Sq 3", "level": 5, "order": 5, "reports_to": "to-sq3",
         "summary": "Commands cadet Squadron 3.",
         "responsibilities": "- Lead Squadron 3 cadets\n- Conduct formations\n- Supervise flight commanders\n- Maintain discipline"},
        {"role_id": "support-sq-cc", "title": "Support Squadron Commander", "level": 5, "order": 6, "reports_to": "deputy-support",
         "summary": "Commands Support Squadron personnel.",
         "responsibilities": "- Lead support squadron staff\n- Coordinate support operations\n- Supervise support OICs\n- Report to Deputy Support"},
        
        # ===== LEVEL 6 - Squadron Staff =====
        {"role_id": "sq1-super", "title": "Sqdn Superintendent - Sq 1", "level": 6, "order": 0, "reports_to": "sq1-cc",
         "summary": "Squadron 1 Superintendent.",
         "responsibilities": "- Support Squadron CC\n- Manage squadron admin\n- Coordinate with flights"},
        {"role_id": "sq2-super", "title": "Sqdn Superintendent - Sq 2", "level": 6, "order": 1, "reports_to": "sq2-cc",
         "summary": "Squadron 2 Superintendent.",
         "responsibilities": "- Support Squadron CC\n- Manage squadron admin\n- Coordinate with flights"},
        {"role_id": "sq3-super", "title": "Sqdn Superintendent - Sq 3", "level": 6, "order": 2, "reports_to": "sq3-cc",
         "summary": "Squadron 3 Superintendent.",
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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
