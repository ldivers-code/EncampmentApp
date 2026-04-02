"""Daily Settings routes - Uniform of the Day & Weather Flag"""
from fastapi import Depends, HTTPException
from datetime import datetime, timezone

from database import db, api_router
from models import UserRole, UniformOfTheDay, WeatherFlagUpdate, DailySettingsUpdate
from permissions import get_current_user, require_role

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
                'uniform_code_2': None,
                'description_2': None,
                'cadet_uniform_code': 'BDU',
                'cadet_description': 'Battle Dress Uniform',
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
    if user.get('role') not in ['commander', 'executive_staff', 'plans_programs', 'staff', 'executive_cadre']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.daily_settings.update_one(
        {'_id': 'current'},
        {'$set': {
            'uniform': {
                'uniform_code': uniform.uniform_code,
                'description': uniform.description,
                'uniform_code_2': uniform.uniform_code_2,
                'description_2': uniform.description_2,
                'cadet_uniform_code': uniform.cadet_uniform_code or uniform.uniform_code,
                'cadet_description': uniform.cadet_description or uniform.description,
                'special_instructions': uniform.special_instructions,
                'updated_at': now,
                'updated_by': user.get('name', user.get('email'))
            }
        }},
        upsert=True
    )
    
    return {"message": "Uniform updated", "uniform_code": uniform.uniform_code}

@api_router.post("/daily-settings/weather-flag")
async def update_weather_flag(
    weather: WeatherFlagUpdate,
    user: dict = Depends(get_current_user)
):
    """Update the Weather Flag status (Admin only)"""
    if user.get('role') not in ['commander', 'executive_staff', 'plans_programs', 'staff', 'executive_cadre']:
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


