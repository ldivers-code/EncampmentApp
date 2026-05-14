"""Database connection and shared app configuration"""
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI, APIRouter
from fastapi.security import HTTPBearer
from dotenv import load_dotenv
from pathlib import Path
import os

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

# VAPID Keys for Push Notifications
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')

# SendGrid Configuration
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
SENDGRID_SENDER_EMAIL = os.environ.get('SENDGRID_SENDER_EMAIL', 'noreply@cap-encampment.org')

# Object Storage
APP_NAME = "tnwing-cap"

# Create the main app
app = FastAPI(title="CAP Encampment Roster API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

security = HTTPBearer(auto_error=False)


# ─────────────────────────────────────────────────────────────────────────────
# Active participant counter — single source of truth
# ─────────────────────────────────────────────────────────────────────────────
async def get_active_participant_count(extra_filter: dict | None = None) -> int:
    """Return the count of participants where `is_removed` is not True.

    This is the canonical helper. Use it for every dashboard, roster, analytics,
    check-in, barracks, My Flight, budget/food planning, and report tile that
    needs "how many people are at encampment right now".

    Pass `extra_filter` to scope to a subset (e.g. by participant_type, flight,
    squadron). The is_removed exclusion is always applied — callers do NOT
    have to repeat it.

    Do NOT hard-code participant totals (e.g. 170) and do NOT rely on the
    stored value in `food_expense_settings.total_participants` as a count —
    that field is only a *planning estimate* used by Finance when locking a
    food budget; it is no longer used as a live count.
    """
    query: dict = {"is_removed": {"$ne": True}}
    if extra_filter:
        for k, v in extra_filter.items():
            if k == "is_removed":
                continue  # ignore — the canonical exclusion always wins
            query[k] = v
    return await db.participants.count_documents(query)

