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
