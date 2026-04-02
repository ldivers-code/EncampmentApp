from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, status, BackgroundTasks, Body
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
from fastapi import Form, Query
from fastapi.responses import Response
from file_storage import init_storage, put_object, get_object

# Import shared modules
from database import db, app, api_router, security, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, SENDGRID_API_KEY, SENDGRID_SENDER_EMAIL, APP_NAME, ROOT_DIR, mongo_url, client
from models import (
    UserRole, UserUnit, AccessPermissions, DEFAULT_PERMISSIONS,
    UserBase, UserCreate, UserLogin, UserUnitAssignment, UserProfile, UserProfileUpdate, UserResponse, TokenResponse,
    ParticipantBase, ParticipantCreate, ParticipantRemoval, ParticipantResponse,
    ScheduleEventBase, ScheduleEventCreate, ScheduleEventResponse, ScheduleSettings,
    PushSubscription, PushNotificationRequest,
    BudgetItemBase, BudgetItemCreate, BudgetItemResponse, FoodExpenseSettings, FoodExpenseSettingsUpdate,
    ScoreCategoryBase, ScoreCategoryCreate, ScoreCategoryResponse,
    ScoreEntryBase, ScoreEntryCreate, ScoreEntryResponse,
    MeritDemeritEntry, MeritDemeritResponse, DailyAward,
    FlightReportSection, FlightReportBase, FlightReportCreate, FlightReportResponse,
    EscalateReportRequest, ReportDeadlineSettings,
    DocumentBase, DocumentCreate, DocumentResponse,
    OrgChartRoleBase, OrgChartRoleCreate, OrgChartRoleUpdate, OrgChartRoleResponse,
    GoogleSheetConfig, UniformOfTheDay, WeatherFlagUpdate, DailySettingsUpdate,
    GoogleSheetsSettings, GoogleSheetsSyncRequest, BunkAssignRequest, NotificationPreferences
)
from permissions import (
    hash_password, verify_password, create_token,
    get_default_permissions, get_user_permissions,
    send_approval_email, get_current_user, require_role,
    require_health_view, require_health_full, require_check_in_access, get_event_settings
)

logger = logging.getLogger("server")

# Import notification routes and helper
import routes.notifications
from routes.notifications import create_notification
import routes.training
import routes.checkin
import routes.barracks
import routes.schedule_changes
import routes.health_alerts
import routes.auth
import routes.users
import routes.schedule
import routes.push_notifications
import routes.budget
import routes.documents
import routes.meal_plan
import routes.flights
import routes.orgchart
import routes.stats
import routes.daily_settings
import routes.google_sheets
from routes.google_sheets import scheduler, perform_scheduled_sync
import routes.badges
import routes.reports
import routes.health_services
import routes.medical_roster
import routes.participants
import routes.students
import routes.points

# Auth routes extracted to routes/auth.py
# User management routes extracted to routes/users.py



# Participant routes extracted to routes/participants.py
# Student upload routes extracted to routes/students.py
# Points + Honor Awards routes extracted to routes/points.py


# Schedule routes extracted to routes/schedule.py
# Push Notification routes extracted to routes/push_notifications.py
# Budget + Quick Update routes extracted to routes/budget.py
# Document + File routes extracted to routes/documents.py
# Meal Plan routes extracted to routes/meal_plan.py
# Flight Roster + Leadership routes extracted to routes/flights.py
# Org Chart routes extracted to routes/orgchart.py
# Stats routes extracted to routes/stats.py
# ================= ROOT ROUTE =================

@api_router.get("/")
async def root():
    return {"message": "CAP Encampment Roster API", "version": "1.0.0"}

# Daily Settings routes extracted to routes/daily_settings.py
# Google Sheets Sync Endpoints extracted to routes/google_sheets.py
# Notification Badges extracted to routes/badges.py
# Flight Reporting API extracted to routes/reports.py
# Google Sheets Sync Service extracted to routes/google_sheets.py
# Health Services API extracted to routes/health_services.py
# Training Officer routes extracted to routes/training.py

# Health Services Medical Import extracted to routes/health_services.py
# Check-In routes extracted to routes/checkin.py

# Barracks routes extracted to routes/barracks.py




# Barracks routes extracted to routes/barracks.py


# Medical Roster routes extracted to routes/medical_roster.py

# ================= Include all routes ====================
app.include_router(api_router)

# Include logistics router using factory pattern
from logistics import create_logistics_router
logistics_router = create_logistics_router(db, get_current_user)
app.include_router(logistics_router)

# Include status board router using factory pattern
from statusboard import create_statusboard_router
statusboard_router = create_statusboard_router(db, get_current_user)
app.include_router(statusboard_router)

# CORS middleware
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

    # Initialize object storage
    try:
        init_storage()
        logger.info("Object storage initialized successfully")
    except Exception as e:
        logger.warning(f"Object storage init failed (uploads will retry): {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    scheduler.shutdown(wait=False)
    client.close()
