"""Schedule routes - CRUD, import, publish/draft workflow"""
from fastapi import Depends, HTTPException, UploadFile, File
from typing import List
from datetime import datetime, timezone
from io import BytesIO
import uuid
import logging
import re

import openpyxl

from database import db, api_router
from models import UserRole, ScheduleEventCreate, ScheduleEventResponse
from permissions import get_current_user, require_role
from routes.notifications import create_notification
from routes.push_notifications import send_schedule_update_notification

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
    is_editor = user["role"] in [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]
    
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
                (user["role"] in [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF] and "staff" in target_groups)
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
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
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
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
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
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
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

    # Send notification for new schedule event
    try:
        await create_notification(
            db, title="New Schedule Event",
            message=f"{data.title} on {data.date} ({data.start_time}-{data.end_time})",
            notification_type="schedule",
            target_roles=["all"],
            link="/schedule",
            created_by=user.get("id")
        )
    except Exception as e:
        logging.warning(f"Failed to send schedule notification: {e}")

    return ScheduleEventResponse(**doc)

@api_router.put("/schedule/{event_id}", response_model=ScheduleEventResponse)
async def update_schedule_event(
    event_id: str,
    data: ScheduleEventCreate,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
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

    # Send notification for updated schedule event
    try:
        await create_notification(
            db, title="Schedule Updated",
            message=f"{data.title} on {data.date} has been modified",
            notification_type="schedule",
            target_roles=["all"],
            link="/schedule",
            created_by=user.get("id")
        )
    except Exception as e:
        logging.warning(f"Failed to send schedule notification: {e}")

    return ScheduleEventResponse(**event)

@api_router.delete("/schedule/{event_id}")
async def delete_schedule_event(
    event_id: str,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    result = await db.schedule.delete_one({"id": event_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Update version for real-time sync
    await increment_schedule_version()

    # Send notification for deleted schedule event
    try:
        await create_notification(
            db, title="Schedule Event Cancelled",
            message="A schedule event has been removed",
            notification_type="schedule",
            target_roles=["all"],
            link="/schedule",
            created_by=user.get("id")
        )
    except Exception as e:
        logging.warning(f"Failed to send schedule notification: {e}")
    
    return {"message": "Event deleted successfully"}

def _parse_time_value(val) -> str | None:
    """Convert Excel time cell to HH:MM string. Handles '0600', 1345.0, datetime, etc."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None

    # datetime object (e.g. header row date) — skip
    if hasattr(val, 'strftime'):
        return None

    # Strip trailing .0 from floats like '1345.0'
    if s.endswith('.0'):
        s = s[:-2]

    # Must be 3 or 4 digit military time (e.g. '600' or '1345')
    if not re.match(r'^\d{3,4}$', s):
        return None

    s = s.zfill(4)          # '600' -> '0600'
    hh, mm = int(s[:2]), int(s[2:])
    if hh > 23 or mm > 59:
        return None
    return f"{hh:02d}:{mm:02d}"


def _classify_event(code: str, title: str) -> str:
    """Determine event_type from the CAP curriculum code and title keywords."""
    code = code.strip().split('/')[0].strip().upper()  # handle 'X8 / L6'
    title_lower = title.lower()

    # --- Code‑prefix mapping (most reliable) ---
    if code.startswith('F'):                   # F1-F4 = fitness
        return 'pt'
    if code.startswith('C'):                   # C1-C9 = character / core values
        # C9 is graduation ceremony
        if code == 'C9':
            return 'ceremony'
        return 'character'
    if code.startswith('A'):                   # A-codes = aerospace field trips
        return 'aerospace'
    if code.startswith('L'):
        num_part = code[1:]
        if num_part in ('1', '4', '5'):        # Report/Reveille/Retreat formations
            return 'ceremony'
        if num_part in ('6', '7', '22'):       # Drill, Parade, Flt CC time
            return 'training'
        if num_part.startswith('2'):            # L20-L25 = inspections/dorm prep
            return 'admin'
        if num_part.startswith('3'):            # L30-L32 = TLPs
            return 'leadership'
        # L10-L13 = leadership modules
        return 'leadership'
    if code.startswith('X'):
        num_part = code[1:]
        if num_part in ('7', '8', '9'):        # Meals
            return 'meal'
        if num_part == '5':                    # First Call
            return 'ceremony'
        if num_part in ('6', '13'):            # Shower / personal time
            return 'recreation'
        if num_part == '18':                   # Awards social
            return 'ceremony'
        return 'admin'
    if code == 'PRE':
        return 'admin'

    # --- Keyword fallback when no code ---
    if any(k in title_lower for k in ['calisthenics', 'fitness', 'obstacle', 'sports', 'guidon run', 'daily sport']):
        return 'pt'
    if any(k in title_lower for k in ['breakfast', 'lunch', 'dinner', 'meal', 'dfac', 'dishes', 'dining', 'pastries']):
        return 'meal'
    if any(k in title_lower for k in ['formation', 'retreat', 'reveille', 'parade', 'graduation', 'ceremony', 'first call']):
        return 'ceremony'
    if any(k in title_lower for k in ['core values', 'honor agreement', 'chaplain', 'character development', 'drug-free']):
        return 'character'
    if any(k in title_lower for k in ['drone', 'rocket', 'astronomy', 'cyber', 'mobile lab', 'military power',
                                       'simulator', 'fit to fly', 'parachute', 'maintenance hangar',
                                       'chattanooga']):
        return 'aerospace'
    if any(k in title_lower for k in ['leadership', 'wingmen', 'warrior', 'tlp', 'team leadership', 'discipline']):
        return 'leadership'
    if any(k in title_lower for k in ['quiz', 'academics', 'handbook', 'assessment']):
        return 'academics'
    if any(k in title_lower for k in ['personal time', 'shower', 'break', 'recreation', 'trivia', 'game room',
                                       'flex time', 'honor flight']):
        return 'recreation'
    if any(k in title_lower for k in ['sign in', 'pack', 'room', 'setup', 'inspection', 'uniform', 'nametag',
                                       'clean', 'critique', 'thank you', 'check', 'packing', 'lights out',
                                       'schedule review', 'operations', 'barracks', 'transit', 'arrive',
                                       'set up', 'headshot', 'organized for next day', 'parent orient']):
        return 'admin'
    return 'training'


def _extract_location(title: str, notes: str) -> str:
    """Pull location hints from title/notes."""
    combined = f"{title} {notes}".lower()
    if 'dfac' in combined or 'dining' in combined:
        return 'DFAC'
    if 'pt field' in combined:
        return 'PT Field'
    if 'rifle range' in combined:
        return 'Field (Rifle Range)'
    if 'chattanooga' in combined:
        return 'Chattanooga'
    loc_match = re.search(r'\b(TR[\-\s]?\d+[A-Z]?|F\d+|Conex)\b', f"{title} {notes}", re.IGNORECASE)
    if loc_match:
        return loc_match.group(0).upper()
    return ''


def _clean_title(raw_title: str) -> tuple[str, str]:
    """Split a raw spreadsheet title into (clean_title, extra_notes).

    Strips parenthetical planning notes (closed or unclosed), inline
    comments, and long trailing descriptions.
    """
    title = raw_title.strip()
    extra = ''

    # 1. Closed parenthetical notes — e.g. "(On Your Own, Not Paid for by ENC)"
    paren_match = re.search(r'\s*\(([^)]{15,})\)', title)
    if paren_match:
        extra = paren_match.group(1).strip()
        title = title[:paren_match.start()].strip()
        # Grab any text AFTER the closing paren too
        after = title[paren_match.end():].strip() if paren_match.end() < len(raw_title) else ''
        remainder = raw_title[paren_match.end():].strip()
        if remainder:
            extra += ' — ' + remainder
            title = title  # already set above

    # 2. Unclosed parenthetical — e.g. "(cut check in down to..."
    if not extra:
        unclosed = re.search(r'\s*\([^)]{15,}$', title)
        if unclosed:
            extra = title[unclosed.start():].strip().lstrip('(').strip()
            title = title[:unclosed.start()].strip()

    # 2b. Strip short parenthetical abbreviations like (Ops), (Sppt), (HQ)
    title = re.sub(r'\s*\([^)]{1,6}\)', '', title).strip()

    # 3. If still very long (>55 chars), split at a natural boundary
    if len(title) > 55:
        for sep in [' - ', ' / ', ', ', '/ ', '//']:
            idx = title.find(sep, 20)
            if 0 < idx < 55:
                extra = title[idx + len(sep):].strip() + (' — ' + extra if extra else '')
                title = title[:idx].strip()
                break
        # Last resort: truncate at last space before 55 chars
        if len(title) > 55:
            idx = title.rfind(' ', 0, 55)
            if idx > 20:
                extra = title[idx + 1:].strip() + (' — ' + extra if extra else '')
                title = title[:idx].strip()

    # Remove trailing slashes / whitespace
    title = title.rstrip(' /')
    return title, extra


@api_router.post("/schedule/import")
async def import_schedule(
    file: UploadFile = File(...),
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    """Import schedule from the multi-sheet CAP Encampment Excel file.

    Each sheet represents one day (e.g. 'Sat Jun 14').  Column A = military
    time, B = activity, C = curriculum code, D = hours, I/J = notes.
    Dates in the spreadsheet (Jun 14‑21 2025) are re‑mapped to the 2026
    encampment window (Jul 17‑24).
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")

    try:
        contents = await file.read()
        wb = openpyxl.load_workbook(BytesIO(contents), data_only=True)

        # Ordered mapping: sheet name -> target 2026 date
        # The spreadsheet days correspond 1-to-1 with Jul 17-24.
        SHEET_DATE_MAP = {
            'Sat Jun 14':  '2026-07-17',   # Staff/Cadre arrival
            'Sun Jun 15':  '2026-07-18',   # I-Day
            'Mon. Jun 16': '2026-07-19',
            'Tues Jun 17': '2026-07-20',
            'Wed. Jun 18': '2026-07-21',
            'Thurs Jun 19':'2026-07-22',
            'Fri Jun 20':  '2026-07-23',
            'Sat. June 21':'2026-07-24',   # Graduation
        }

        parsed_events = []

        for sheet_name, target_date in SHEET_DATE_MAP.items():
            if sheet_name not in wb.sheetnames:
                continue
            ws = wb[sheet_name]

            # Collect raw rows: (time_str, activity, code, hours, notes)
            raw_rows = []
            current_time = None
            for row_idx in range(1, ws.max_row + 1):
                time_cell = ws.cell(row_idx, 1).value
                activity_cell = ws.cell(row_idx, 2).value
                code_cell = ws.cell(row_idx, 3).value
                hours_cell = ws.cell(row_idx, 4).value
                notes_cell = None
                for col in range(9, min(ws.max_column + 1, 12)):
                    v = ws.cell(row_idx, col).value
                    if v and str(v).strip():
                        notes_cell = str(v).strip()
                        break

                parsed_time = _parse_time_value(time_cell)
                if parsed_time:
                    current_time = parsed_time

                if not activity_cell:
                    continue
                activity = str(activity_cell).strip()
                # Skip header row, task rows, uniform rows, empty labels
                if activity.lower() in ('activity', 'code', 'hrs', ''):
                    continue
                if activity.lower().startswith(('tasks:', 'uniform', 'senior staff uniform', 'officer of the day')):
                    continue
                # Skip department task entries (Logistics, Public Affairs, etc.)
                skip_keywords = [
                    'vehicle inspection', 'get supplies', 'issuing of radios',
                    'shirts counted', 'fuel cov', 'gather up sports',
                    'close up shop', 'start inventory', 'check on comms',
                    'gather hand receipts', 'comm radio support', 'cov inspection',
                    'determine cov', 'support comm', 'brief encampment staff',
                    'publish last staff', 'set up administrative',
                    'confirm chaplain', 'senior member led', 'cadet flight cadre led',
                    'cadet cadre', 'mix of sm/cadet', 'plans and programs',
                    'public affairs',
                ]
                if any(kw in activity.lower() for kw in skip_keywords):
                    continue
                # Skip pure sub-labels without their own time (like department headers)
                if activity.lower() in ('logistics', 'finance', 'communications', 'health services'):
                    continue
                # Skip location-only sub-labels and task-tracker entries
                if any(kw in activity.lower() for kw in [
                    'field accross from rifle range', 'field across from rifle range',
                    'continue with pictures', 'continue the photos', 'awards tracking',
                    'encampment awards tracking', 'tracking for encampment',
                    'support activities for capturing',
                ]):
                    continue
                # Skip sub-labels like 'Field Across from Rifle range', 'Rain Alternative' without own time
                if not current_time:
                    continue

                code_str = str(code_cell).strip() if code_cell and str(code_cell).strip().lower() not in ('none', 'code', 'n/a', '') else ''
                hours_val = None
                if hours_cell:
                    try:
                        hours_val = float(hours_cell)
                    except (ValueError, TypeError):
                        pass

                raw_rows.append({
                    'time': current_time,
                    'activity': activity,
                    'code': code_str,
                    'hours': hours_val,
                    'notes': notes_cell or ''
                })

            # Compute end times: use explicit hours if available, else next event's start
            for i, row in enumerate(raw_rows):
                if row['hours'] and row['hours'] > 0:
                    # Compute end from start + hours
                    h, m = map(int, row['time'].split(':'))
                    total_min = h * 60 + m + int(row['hours'] * 60)
                    end_h, end_m = divmod(total_min, 60)
                    if end_h > 23:
                        end_h = 22
                        end_m = 0
                    end_time = f"{end_h:02d}:{end_m:02d}"
                elif i + 1 < len(raw_rows) and raw_rows[i + 1]['time'] != row['time']:
                    end_time = raw_rows[i + 1]['time']
                else:
                    # Default: 15 min block
                    h, m = map(int, row['time'].split(':'))
                    total_min = h * 60 + m + 15
                    end_h, end_m = divmod(total_min, 60)
                    end_time = f"{end_h:02d}:{end_m:02d}"

                event_type = _classify_event(row['code'], row['activity'])
                location = _extract_location(row['activity'], row['notes'])
                clean_title, extra_notes = _clean_title(row['activity'])

                # Combine extracted notes with spreadsheet notes column
                combined_notes = ' — '.join(filter(None, [extra_notes, row['notes']]))

                parsed_events.append({
                    'date': target_date,
                    'start_time': row['time'],
                    'end_time': end_time,
                    'title': clean_title,
                    'event_type': event_type,
                    'location': location,
                    'notes': combined_notes,
                })

        if not parsed_events:
            raise HTTPException(status_code=400, detail="No schedule events found in the Excel file. Expected sheets named by day (e.g. 'Sat Jun 14').")

        # Clear existing schedule and insert parsed events
        await db.schedule.delete_many({})

        now = datetime.now(timezone.utc).isoformat()
        imported_count = 0

        for ev in parsed_events:
            doc = {
                "id": str(uuid.uuid4()),
                "title": ev['title'],
                "description": ev['notes'],
                "date": ev['date'],
                "start_time": ev['start_time'],
                "end_time": ev['end_time'],
                "location": ev['location'],
                "event_type": ev['event_type'],
                "target_groups": ["all"],
                "created_at": now,
                "updated_at": now,
            }
            await db.schedule.insert_one(doc)
            imported_count += 1

        # Mark schedule as published and increment version
        now_pub = datetime.now(timezone.utc).isoformat()
        await db.schedule_settings.update_one(
            {"_id": "settings"},
            {"$set": {
                "is_published": True,
                "last_published_at": now_pub,
                "last_modified_at": now_pub,
            }, "$inc": {"version": 1}},
            upsert=True
        )

        # Count events by type for summary
        type_counts = {}
        for ev in parsed_events:
            t = ev['event_type']
            type_counts[t] = type_counts.get(t, 0) + 1
        type_summary = ', '.join(f"{v} {k}" for k, v in sorted(type_counts.items()))

        return {
            "message": f"Successfully imported {imported_count} events for Jul 17-24, 2026 from {len(SHEET_DATE_MAP)} day sheets. Breakdown: {type_summary}. Schedule is now published.",
            "imported_count": imported_count,
            "type_breakdown": type_counts,
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Schedule import error: {e}")
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

@api_router.delete("/schedule/clear")
async def clear_schedule(
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
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


