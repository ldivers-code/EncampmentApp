"""Student Upload with Auto-Assignment and Budget Sync"""
from fastapi import Depends, HTTPException, UploadFile, File
from typing import List, Optional
from datetime import datetime, timezone
from io import BytesIO
import uuid
import logging
import re
import pandas as pd

from database import db, api_router
from models import UserRole
from permissions import get_current_user, require_role

logger = logging.getLogger(__name__)


# ================= SHARED IMPORT HELPERS =================

async def find_existing_participant(capid, email, first_name, last_name, include_removed=False):
    """Cascading match: CAPID → email → first+last name.
    Returns the existing participant doc or None.

    When `include_removed=True` (used by Sync Mode), soft-removed rows are
    also considered — so a previously-removed participant can be recovered
    rather than duplicated when they reappear in the upload.
    """
    removed_clause = {} if include_removed else {"is_removed": {"$ne": True}}
    # 1. Match by CAPID
    if capid and capid not in ('', 'nan'):
        existing = await db.participants.find_one(
            {"capid": str(capid), **removed_clause}, {"_id": 0}
        )
        if existing:
            return existing

    # 2. Match by email (case-insensitive)
    if email and email not in ('', 'nan'):
        existing = await db.participants.find_one(
            {"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"},
             **removed_clause}, {"_id": 0}
        )
        if existing:
            return existing

    # 3. Match by first + last name (case-insensitive)
    if first_name and last_name:
        existing = await db.participants.find_one(
            {"first_name": {"$regex": f"^{re.escape(first_name)}$", "$options": "i"},
             "last_name": {"$regex": f"^{re.escape(last_name)}$", "$options": "i"},
             **removed_clause}, {"_id": 0}
        )
        if existing:
            return existing

    return None


async def find_match_with_candidates(capid, email, first_name, last_name):
    """Like find_existing_participant but returns:
    {
      'match_type': 'capid' | 'email' | 'name' | 'none',
      'participant': matched doc or None,    # the chosen one (first match for capid/email; first for name)
      'candidates': list of docs                # all participants with the same first+last name (only populated when match_type='name' and >1 found, OR match_type='none' but name exists for awareness)
    }
    """
    # CAPID
    if capid and capid not in ('', 'nan'):
        existing = await db.participants.find_one(
            {"capid": str(capid), "is_removed": {"$ne": True}}, {"_id": 0}
        )
        if existing:
            return {"match_type": "capid", "participant": existing, "candidates": [existing]}

    # Email
    if email and email not in ('', 'nan'):
        existing = await db.participants.find_one(
            {"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"},
             "is_removed": {"$ne": True}}, {"_id": 0}
        )
        if existing:
            return {"match_type": "email", "participant": existing, "candidates": [existing]}

    # Name — return ALL candidates for ambiguity resolution
    if first_name and last_name:
        candidates = await db.participants.find(
            {"first_name": {"$regex": f"^{re.escape(first_name)}$", "$options": "i"},
             "last_name": {"$regex": f"^{re.escape(last_name)}$", "$options": "i"},
             "is_removed": {"$ne": True}}, {"_id": 0}
        ).to_list(20)
        if candidates:
            return {
                "match_type": "name",
                "participant": candidates[0],
                "candidates": candidates,
            }

    return {"match_type": "none", "participant": None, "candidates": []}


async def link_to_user_account(participant_id, capid, email):
    """If a user account exists for this person, link them.
    Sets linked_participant_id on the user doc."""
    user = None
    if capid and capid not in ('', 'nan'):
        user = await db.users.find_one({"capid": str(capid)})
    if not user and email and email not in ('', 'nan'):
        user = await db.users.find_one(
            {"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}}
        )
    if user and user.get("linked_participant_id") != participant_id:
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"linked_participant_id": participant_id,
                      "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        return True
    return False


def determine_participant_type(event_name, member_type, is_staff):
    """Determine participant_type from sub-event context and member data.

    DELEGATES to the canonical `classify_from_subevent` helper. The
    `is_staff` argument (generic RegZone "staff" boolean) is INTENTIONALLY
    IGNORED — per the Phase-2 rule:
      "Do not use the generic Registration Zone 'staff' selection as
       the source of truth."

    Returns one of: senior_staff / cadre / student / needs_review.
    """
    from classifier import classify_from_subevent
    return classify_from_subevent(member_type, event_name)

# ================= STUDENT UPLOAD WITH AUTO-ASSIGNMENT =================

# Flight assignment constants
STUDENT_FLIGHTS = {
    "6th_cts": ["alpha", "bravo"],
    "21st_cts": ["charlie", "delta"],
    "22nd_cts": ["echo", "foxtrot"]
}

FLIGHT_TO_SQUADRON = {
    "alpha": "6th_cts", "bravo": "6th_cts",
    "charlie": "21st_cts", "delta": "21st_cts",
    "echo": "22nd_cts", "foxtrot": "22nd_cts"
}

ALL_FLIGHTS = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
MAX_STUDENTS_PER_FLIGHT = 15

# Rank ordering for distribution (lower = junior)
RANK_ORDER = {
    "C/AB": 1, "C/Amn": 2, "C/A1C": 3, "C/SrA": 4,
    "C/SSgt": 5, "C/TSgt": 6, "C/MSgt": 7, "C/SMSgt": 8, "C/CMSgt": 9
}


def get_rank_tier(rank: str) -> int:
    """Get rank tier for distribution (1=junior, 2=mid, 3=senior)"""
    order = RANK_ORDER.get(rank, 0)
    if order <= 3:
        return 1  # Junior (AB, Amn, A1C)
    elif order <= 6:
        return 2  # Mid (SrA, SSgt, TSgt)
    else:
        return 3  # Senior (MSgt, SMSgt, CMSgt)


def get_age_tier(age) -> int:
    """Get age tier for distribution (1=young, 2=mid, 3=older)"""
    if age is None:
        return 2  # Default to mid
    try:
        age = int(age)
    except (ValueError, TypeError):
        return 2
    if age <= 13:
        return 1  # Young (12-13)
    elif age <= 15:
        return 2  # Mid (14-15)
    else:
        return 3  # Older (16+)


def is_valid_flight(flight: str) -> bool:
    """Check if a flight value is a valid assigned flight (not empty/null), case-insensitive"""
    if not flight:
        return False
    return flight.lower() in ALL_FLIGHTS


async def auto_assign_single_student(student_doc: dict) -> dict:
    """
    Auto-assign a single student to a flight if they don't already have one.
    Returns the updated document with flight/squadron assignment.
    
    PROTECTION: Only assigns if flight is empty/null. Does NOT change existing assignments.
    
    Distribution balanced by: Wing, Unit (home squadron), Age, Gender
    """
    # Only apply to students
    participant_type = student_doc.get("participant_type", "")
    if participant_type not in ["basic_student", "advanced_student"]:
        return student_doc  # Not a student, no auto-assignment
    
    # PROTECTION: Don't change students who already have a valid flight
    current_flight = student_doc.get("flight")
    if is_valid_flight(current_flight):
        return student_doc  # Already assigned, don't change
    
    # Get current flight distribution from database
    flight_counts = {f: {
        "total": 0, 
        "male": 0, 
        "female": 0, 
        "wings": {},      # Count per wing
        "units": {},      # Count per unit (home squadron)
        "age_tiers": {1: 0, 2: 0, 3: 0}
    } for f in ALL_FLIGHTS}
    
    # Build case-insensitive flight list for query
    valid_flights_query = ALL_FLIGHTS + [f.capitalize() for f in ALL_FLIGHTS] + [f.upper() for f in ALL_FLIGHTS]
    
    existing = await db.participants.find(
        {"participant_type": {"$in": ["basic_student", "advanced_student"]}, "is_removed": {"$ne": True}, "flight": {"$in": valid_flights_query}},
        {"flight": 1, "gender": 1, "wing": 1, "unit": 1, "age": 1, "age_at_event": 1}
    ).to_list(1000)
    
    for p in existing:
        f = (p.get("flight") or "").lower()
        if f in flight_counts:
            fc = flight_counts[f]
            fc["total"] += 1
            
            # Gender
            gender = (p.get("gender") or "").upper()
            if gender == "MALE" or gender == "M":
                fc["male"] += 1
            elif gender == "FEMALE" or gender == "F":
                fc["female"] += 1
            
            # Wing
            wing = (p.get("wing") or "").upper()
            if wing:
                fc["wings"][wing] = fc["wings"].get(wing, 0) + 1
            
            # Unit (home squadron)
            unit = str(p.get("unit") or "")
            if unit:
                fc["units"][unit] = fc["units"].get(unit, 0) + 1
            
            # Age tier
            age = p.get("age") or p.get("age_at_event")
            age_tier = get_age_tier(age)
            fc["age_tiers"][age_tier] += 1
    
    # Get this student's attributes for assignment
    gender = (student_doc.get("gender") or "").upper()
    if gender == "M":
        gender = "MALE"
    elif gender == "F":
        gender = "FEMALE"
    wing = (student_doc.get("wing") or "").upper()
    unit = str(student_doc.get("unit") or "")
    age = student_doc.get("age") or student_doc.get("age_at_event")
    age_tier = get_age_tier(age)
    
    # Find best flight using weighted scoring
    best_flight = None
    best_score = float('inf')
    
    for flight in ALL_FLIGHTS:
        fc = flight_counts[flight]
        
        # Skip if at capacity
        if fc["total"] >= MAX_STUDENTS_PER_FLIGHT:
            continue
        
        # Calculate score (lower is better)
        # Weight: total (10) > gender (5) > wing (3) > unit (3) > age (2)
        
        # Total balance - heavily weighted
        total_score = fc["total"] * 10
        
        # Gender balance
        if gender == "MALE":
            gender_score = (fc["male"] - fc["female"]) * 5
        elif gender == "FEMALE":
            gender_score = (fc["female"] - fc["male"]) * 5
        else:
            gender_score = 0
        
        # Wing distribution - spread students from same wing
        wing_score = fc["wings"].get(wing, 0) * 3 if wing else 0
        
        # Unit distribution - spread students from same home unit
        unit_score = fc["units"].get(unit, 0) * 3 if unit else 0
        
        # Age tier balance
        age_score = fc["age_tiers"].get(age_tier, 0) * 2
        
        score = total_score + gender_score + wing_score + unit_score + age_score
        
        if score < best_score:
            best_score = score
            best_flight = flight
    
    if best_flight:
        student_doc["flight"] = best_flight
        student_doc["squadron"] = FLIGHT_TO_SQUADRON[best_flight]
    
    return student_doc


async def auto_assign_flights(students: list) -> dict:
    """
    Automatically assign students to flights using balanced distribution.
    
    Distribution Rules:
    1. Evenly distribute total students across 6 flights (max 15 per flight)
    2. Balance male/female distribution (Gender)
    3. Spread students from same Wing across different flights
    4. Spread students from same Unit (home squadron) across different flights
    5. Balance age distribution across flights
    """
    # Get current flight distribution from database
    flight_counts = {f: {
        "total": 0, 
        "male": 0, 
        "female": 0, 
        "wings": {},      # Count per wing
        "units": {},      # Count per unit
        "age_tiers": {1: 0, 2: 0, 3: 0}
    } for f in ALL_FLIGHTS}
    
    # Build case-insensitive flight list for query
    valid_flights_query = ALL_FLIGHTS + [f.capitalize() for f in ALL_FLIGHTS] + [f.upper() for f in ALL_FLIGHTS]
    
    existing = await db.participants.find(
        {"participant_type": {"$in": ["basic_student", "advanced_student"]}, "is_removed": {"$ne": True}, "flight": {"$in": valid_flights_query}},
        {"flight": 1, "gender": 1, "wing": 1, "unit": 1, "age": 1, "age_at_event": 1}
    ).to_list(1000)
    
    for p in existing:
        f = (p.get("flight") or "").lower()
        if f in flight_counts:
            fc = flight_counts[f]
            fc["total"] += 1
            
            gender = (p.get("gender") or "").upper()
            if gender == "MALE" or gender == "M":
                fc["male"] += 1
            elif gender == "FEMALE" or gender == "F":
                fc["female"] += 1
            
            wing = (p.get("wing") or "").upper()
            if wing:
                fc["wings"][wing] = fc["wings"].get(wing, 0) + 1
            
            unit = str(p.get("unit") or "")
            if unit:
                fc["units"][unit] = fc["units"].get(unit, 0) + 1
            
            age = p.get("age") or p.get("age_at_event")
            age_tier = get_age_tier(age)
            fc["age_tiers"][age_tier] += 1
    
    # Prepare students to assign
    students_to_assign = []
    for s in students:
        current_flight = s.get("flight")
        if not current_flight or (isinstance(current_flight, str) and current_flight.lower() not in ALL_FLIGHTS):
            gender = (s.get("gender") or "").upper()
            if gender == "M":
                gender = "MALE"
            elif gender == "F":
                gender = "FEMALE"
            
            students_to_assign.append({
                **s,
                "gender": gender,
                "wing": (s.get("wing") or "").upper(),
                "unit": str(s.get("unit") or ""),
                "age_tier": get_age_tier(s.get("age") or s.get("age_at_event"))
            })
    
    # Sort to distribute diverse groups first (helps balance)
    # Sort by: wing, then unit, then age_tier, then gender
    students_to_assign.sort(key=lambda x: (x["wing"], x["unit"], x["age_tier"], x["gender"]))
    
    assignments = {}
    
    for student in students_to_assign:
        capid = student.get("capid")
        gender = student["gender"]
        wing = student["wing"]
        unit = student["unit"]
        age_tier = student["age_tier"]
        
        # Find best flight using weighted scoring
        best_flight = None
        best_score = float('inf')
        
        for flight in ALL_FLIGHTS:
            fc = flight_counts[flight]
            
            # Skip if at capacity
            if fc["total"] >= MAX_STUDENTS_PER_FLIGHT:
                continue
            
            # Calculate score (lower is better)
            # Weight: total (10) > gender (5) > wing (3) > unit (3) > age (2)
            
            total_score = fc["total"] * 10
            
            if gender == "MALE":
                gender_score = (fc["male"] - fc["female"]) * 5
            elif gender == "FEMALE":
                gender_score = (fc["female"] - fc["male"]) * 5
            else:
                gender_score = 0
            
            wing_score = fc["wings"].get(wing, 0) * 3 if wing else 0
            unit_score = fc["units"].get(unit, 0) * 3 if unit else 0
            age_score = fc["age_tiers"].get(age_tier, 0) * 2
            
            score = total_score + gender_score + wing_score + unit_score + age_score
            
            if score < best_score:
                best_score = score
                best_flight = flight
        
        if best_flight:
            assignments[capid] = {
                "flight": best_flight,
                "squadron": FLIGHT_TO_SQUADRON[best_flight]
            }
            # Update counts for next iteration
            fc = flight_counts[best_flight]
            fc["total"] += 1
            if gender == "MALE":
                fc["male"] += 1
            elif gender == "FEMALE":
                fc["female"] += 1
            if wing:
                fc["wings"][wing] = fc["wings"].get(wing, 0) + 1
            if unit:
                fc["units"][unit] = fc["units"].get(unit, 0) + 1
            fc["age_tiers"][age_tier] += 1
    
    return {
        "assignments": assignments,
        "flight_counts": {f: fc["total"] for f, fc in flight_counts.items()}
    }


@api_router.post("/students/upload/preview")
async def upload_students_preview(
    file: UploadFile = File(...),
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF, UserRole.PLANS_PROGRAMS]))
):
    """Phase 7 Sync Mode preview — analyse the file WITHOUT mutating the DB.

    Returns the counts the admin will see in their confirmation dialog:
      - file_rows: rows in the uploaded file (cleaned)
      - matches_existing: rows that will UPDATE an existing active row
      - recovers: rows that will RECOVER a soft-removed row
      - new_inserts: rows that will be inserted as net-new
      - soft_removes: existing active participants that will be soft-removed
                      because they're NOT in the uploaded file
      - soft_remove_sample: first 10 names that will be soft-removed (for UX)
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")

    contents = await file.read()
    try:
        df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read Excel file: {e}")
    df.columns = df.columns.str.strip()

    # Reuse the same column map as the upload endpoint.
    column_map = {
        'RegistrantsCAPID': 'capid', 'CAPID': 'capid',
        'EventName': 'event_name', 'SubEvents': 'event_name',
        'NameLast': 'last_name', 'NameFirst': 'first_name',
        'Email': 'email',
    }
    df = df.rename(columns=column_map)

    def get_str(row, key):
        v = row.get(key)
        if pd.isna(v) or v == '' or v == 'nan':
            return ''
        return str(v).strip()

    matches = recovers = new_inserts = 0
    seen_existing_ids: set[str] = set()

    for _, row in df.iterrows():
        rd = row.to_dict()
        capid = get_str(rd, 'capid')
        if capid.endswith('.0') and capid[:-2].isdigit():
            capid = capid[:-2]
        email = get_str(rd, 'email')
        fn = get_str(rd, 'first_name')
        ln = get_str(rd, 'last_name')
        if not capid and not (fn and ln):
            continue
        # Look in BOTH active and soft-removed rows so we can show the
        # recoverable count.
        existing = await find_existing_participant(capid, email, fn, ln, include_removed=True)
        if existing:
            seen_existing_ids.add(existing["id"])
            if existing.get("is_removed"):
                recovers += 1
            else:
                matches += 1
        else:
            new_inserts += 1

    # Stragglers that will be soft-removed (active rows not touched by file)
    stragglers = await db.participants.find(
        {"is_removed": {"$ne": True}, "id": {"$nin": list(seen_existing_ids)}},
        {"_id": 0, "id": 1, "capid": 1, "first_name": 1, "last_name": 1,
         "rank": 1, "participant_type": 1, "flight": 1}
    ).to_list(2000)

    sample = stragglers[:10]
    sample_payload = [
        {
            "capid": s.get("capid"),
            "name": f"{s.get('rank', '')} {s.get('last_name', '')}, {s.get('first_name', '')}".strip(", "),
            "participant_type": s.get("participant_type"),
            "flight": s.get("flight"),
        }
        for s in sample
    ]

    return {
        "mode": "sync",
        "file_rows": int(matches + recovers + new_inserts),
        "matches_existing": matches,
        "recovers": recovers,
        "new_inserts": new_inserts,
        "soft_removes": len(stragglers),
        "soft_remove_sample": sample_payload,
        "current_active_total": await db.participants.count_documents({"is_removed": {"$ne": True}}),
    }


@api_router.post("/students/upload")
async def upload_students(
    file: UploadFile = File(...),
    auto_assign: bool = True,
    sync: bool = True,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF, UserRole.PLANS_PROGRAMS]))
):
    """
    Upload student roster from Excel file.

    Default behavior is **SYNC MODE** (`sync=true`): the uploaded file is
    treated as the new source of truth.
      - Rows matching an existing participant by CAPID/email/name update it.
      - Rows whose CAPID is NOT in the file are SOFT-REMOVED
        (`is_removed=true`). Their participant `id` is preserved, so any
        linked user account keeps its `linked_participant_id` reference
        intact and the row can be recovered just by re-uploading them in
        a future file.
      - Previously soft-removed participants who reappear in the file are
        RECOVERED (un-soft-removed) rather than duplicated.

    Pass `sync=false` to use additive mode (no soft-removal of stragglers).

    All uploaded students are marked as "First-Time Student".
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        df.columns = df.columns.str.strip()
        
        # Column mapping for CAP Event Admin Report format
        # Supports both sub-event reports (have RegistrantsCAPID, EventName)
        # and master reports (have SubEvents at col BL, no CAPID column)
        column_map = {
            'RegistrantsCAPID': 'capid',
            'CAPID': 'capid',
            'EventName': 'event_name',
            'SubEvents': 'event_name',
            'Rank': 'rank',
            'NameLast': 'last_name',
            'NameFirst': 'first_name',
            'NameMiddle': 'middle_name',
            'Unit': 'unit',
            'Wing': 'wing',
            'Region': 'region',
            'Gender': 'gender',
            'Age': 'age',
            'DOB': 'dob',
            'AgeAtEventStart': 'age_at_event',
            'Email': 'email',
            'MbrType': 'member_type',
            'StaffMember': 'staff_member',
            'ShirtSize': 'shirt_size',
            'RegistrationStatus': 'registration_status',
            'Addr1': 'address',
            'Addr2': 'address2',
            'City': 'city',
            'State': 'state',
            'Zip': 'zip_code',
            'EmergencyContactName': 'emergency_contact',
            'EmergencyContactNumber': 'emergency_phone',
            'HomePhonePrimary': 'home_phone',
            'CellPhonePrimary': 'cell_phone',
            'CadetParentPhonePrimary': 'cadet_parent_phone',
            'CadetParentPhoneSecondary': 'cadet_parent_phone_secondary',
            'CadetParentPhoneEmergency': 'cadet_parent_phone_emergency',
            'CadetParentEmailPrimary': 'cadet_parent_email',
            'CadetParentEmailSecondary': 'cadet_parent_email_secondary',
            'CadetParentEmailEmergency': 'cadet_parent_email_emergency',
            'Comments': 'comments',
            'Conflicts': 'conflicts',
            'LastEncampment': 'last_encampment',
            'HighestORide': 'highest_oride',
            'AmountPaid': 'amount_paid',
            'PaidInFull': 'paid_in_full',
        }
        
        df = df.rename(columns=column_map)
        
        now = datetime.now(timezone.utc).isoformat()
        students_to_process = []
        
        # Helper functions
        def get_val(row_dict, key, default=None):
            val = row_dict.get(key)
            if pd.isna(val) or val == '' or val == 'nan':
                return default
            return val
        
        def get_str(row_dict, key, default=''):
            val = get_val(row_dict, key, default)
            return str(val).strip() if val is not None else default
        
        def get_int(row_dict, key, default=None):
            val = get_val(row_dict, key)
            if val is None:
                return default
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return default
        
        # Process each row
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            
            capid = get_str(row_dict, 'capid')
            if capid == 'nan':
                capid = ''
            first_name = get_str(row_dict, 'first_name')
            last_name = get_str(row_dict, 'last_name')
            
            # Skip rows with no identifying info
            if not capid and not (first_name and last_name):
                continue
            
            # Determine participant type from sub-event context
            event_name = get_str(row_dict, 'event_name')
            member_type_val = get_str(row_dict, 'member_type')
            staff_flag = get_str(row_dict, 'staff_member', 'No').lower() in ('yes', 'true', '1')
            p_type = determine_participant_type(event_name, member_type_val, staff_flag)
            # p_type is None when EventName/SubEvents is blank — will be resolved during upsert

            # member_type: use spreadsheet value
            m_type = member_type_val.upper() if member_type_val else ''

            students_to_process.append({
                "capid": capid,
                "rank": get_str(row_dict, 'rank'),
                "last_name": get_str(row_dict, 'last_name'),
                "first_name": get_str(row_dict, 'first_name'),
                "middle_name": get_str(row_dict, 'middle_name') or None,
                "unit": get_str(row_dict, 'unit'),
                "wing": get_str(row_dict, 'wing') or None,
                "region": get_str(row_dict, 'region') or None,
                "gender": get_str(row_dict, 'gender') or None,
                "age": get_int(row_dict, 'age'),
                "age_at_event": get_int(row_dict, 'age_at_event'),
                "email": get_str(row_dict, 'email') or None,
                "shirt_size": get_str(row_dict, 'shirt_size') or None,
                "registration_status": get_str(row_dict, 'registration_status') or None,
                "address": get_str(row_dict, 'address') or None,
                "address2": get_str(row_dict, 'address2') or None,
                "city": get_str(row_dict, 'city') or None,
                "state": get_str(row_dict, 'state') or None,
                "zip_code": get_str(row_dict, 'zip_code') or None,
                "emergency_contact": get_str(row_dict, 'emergency_contact') or None,
                "emergency_phone": get_str(row_dict, 'emergency_phone') or None,
                "cadet_parent_phone": get_str(row_dict, 'cadet_parent_phone') or None,
                "cadet_parent_phone_secondary": get_str(row_dict, 'cadet_parent_phone_secondary') or None,
                "cadet_parent_phone_emergency": get_str(row_dict, 'cadet_parent_phone_emergency') or None,
                "cadet_parent_email": get_str(row_dict, 'cadet_parent_email') or None,
                "cadet_parent_email_secondary": get_str(row_dict, 'cadet_parent_email_secondary') or None,
                "cadet_parent_email_emergency": get_str(row_dict, 'cadet_parent_email_emergency') or None,
                "comments": get_str(row_dict, 'comments') or None,
                "conflicts": get_str(row_dict, 'conflicts') or None,
                "last_encampment": get_str(row_dict, 'last_encampment') or None,
                "highest_oride": get_str(row_dict, 'highest_oride') or None,
                "participant_type": p_type,
                "student_type": "First-Time Student" if p_type == 'basic_student' else None,
                "member_type": m_type,
                "staff_member": staff_flag,
            })
        
        # Auto-assign flights if enabled
        flight_assignments = {}
        if auto_assign:
            result = await auto_assign_flights(students_to_process)
            flight_assignments = result["assignments"]
        
        # Insert/update students with cascading match + user linking
        imported_count = 0
        updated_count = 0
        recovered_count = 0
        linked_count = 0

        # Phase 7 Sync Mode: collect the participant ids touched by this
        # upload so we can soft-remove everyone else at the end.
        touched_ids: set[str] = set()

        for student in students_to_process:
            capid = student["capid"]
            email = student.get("email")
            first_name = student.get("first_name", "")
            last_name = student.get("last_name", "")

            # Apply flight assignment if available (only for students)
            if student.get("participant_type") == "basic_student" and capid in flight_assignments:
                student["flight"] = flight_assignments[capid]["flight"]
                student["squadron"] = flight_assignments[capid]["squadron"]

            student["updated_at"] = now

            # In sync mode, we ALSO look at soft-removed rows so we can
            # recover them instead of creating a duplicate.
            existing = await find_existing_participant(
                capid, email, first_name, last_name, include_removed=sync
            )

            if existing:
                # Don't override manual squadron/flight assignments
                if existing.get("flight") and existing["flight"] in ALL_FLIGHTS:
                    student["flight"] = existing["flight"]
                    student["squadron"] = existing.get("squadron")

                # If spreadsheet didn't specify a participant_type (blank SubEvents/EventName),
                # keep the existing type entirely — don't change what's already set
                if student.get("participant_type") is None:
                    student.pop("participant_type", None)
                    student.pop("student_type", None)
                # If spreadsheet DID specify a type, trust it (the SubEvents column is authoritative)

                # Only update fields that have actual values — don't wipe existing data with blanks
                update_doc = {k: v for k, v in student.items() if v is not None}
                update_doc["updated_at"] = now

                # If the existing row was soft-removed, recover it.
                was_removed = bool(existing.get("is_removed"))
                if was_removed:
                    update_doc["is_removed"] = False
                    update_doc["removed_at"] = None
                    update_doc["removed_by"] = None
                    recovered_count += 1
                else:
                    updated_count += 1

                await db.participants.update_one(
                    {"id": existing["id"]},
                    {"$set": update_doc}
                )
                pid = existing["id"]
            else:
                # New record — if no participant_type was determined, default to basic_student
                if student.get("participant_type") is None:
                    student["participant_type"] = "basic_student"
                    student["student_type"] = "First-Time Student"
                pid = str(uuid.uuid4())
                student["id"] = pid
                student["created_at"] = now
                await db.participants.insert_one(student)
                imported_count += 1

            touched_ids.add(pid)

            # Link to existing user account if one exists
            if await link_to_user_account(pid, capid, email):
                linked_count += 1

        # Phase 7 Sync Mode: soft-remove any active participant whose id was
        # NOT touched by this upload. Their user-account linkage is preserved
        # (we never null `linked_participant_id` on the user doc) so they can
        # be recovered automatically by a future upload that re-includes them.
        soft_removed_count = 0
        if sync and touched_ids:
            res = await db.participants.update_many(
                {"is_removed": {"$ne": True}, "id": {"$nin": list(touched_ids)}},
                {"$set": {
                    "is_removed": True,
                    "removed_at": now,
                    "removed_by": user.get("id"),
                    "removed_reason": "Not present in latest master roster upload",
                }}
            )
            soft_removed_count = res.modified_count
        
        # Get final counts
        total_students = await db.participants.count_documents({"participant_type": "basic_student", "is_removed": {"$ne": True}})
        
        # Get flight distribution
        flight_distribution = {}
        for flight in ALL_FLIGHTS:
            count = await db.participants.count_documents({
                "participant_type": "basic_student",
                "flight": flight,
                "is_removed": {"$ne": True}
            })
            flight_distribution[flight] = count
        
        return {
            "message": (
                f"Roster sync complete: {imported_count} new, {updated_count} updated, "
                f"{recovered_count} recovered, {soft_removed_count} removed (not in file), "
                f"{linked_count} linked to accounts"
                if sync else
                f"Student upload complete: {imported_count} new, {updated_count} updated, {linked_count} linked to accounts"
            ),
            "mode": "sync" if sync else "additive",
            "imported": imported_count,
            "updated": updated_count,
            "recovered": recovered_count,
            "soft_removed": soft_removed_count,
            "linked": linked_count,
            "total_students": total_students,
            "auto_assigned": len(flight_assignments),
            "flight_distribution": flight_distribution
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")


@api_router.get("/students/flight-distribution")
async def get_flight_distribution(user: dict = Depends(get_current_user)):
    """Get current student distribution across flights"""
    distribution = {}
    
    for flight in ALL_FLIGHTS:
        students = await db.participants.find(
            {
                "participant_type": "basic_student",
                "flight": flight,
                "is_removed": {"$ne": True}
            },
            {"gender": 1, "rank": 1}
        ).to_list(100)
        
        male_count = sum(1 for s in students if (s.get("gender") or "").upper() == "MALE")
        female_count = sum(1 for s in students if (s.get("gender") or "").upper() == "FEMALE")
        
        distribution[flight] = {
            "total": len(students),
            "male": male_count,
            "female": female_count,
            "squadron": FLIGHT_TO_SQUADRON.get(flight, ""),
            "capacity": MAX_STUDENTS_PER_FLIGHT
        }
    
    total_students = sum(d["total"] for d in distribution.values())
    total_capacity = MAX_STUDENTS_PER_FLIGHT * len(ALL_FLIGHTS)
    
    return {
        "flights": distribution,
        "total_students": total_students,
        "total_capacity": total_capacity,
        "utilization": round(total_students / total_capacity * 100, 1) if total_capacity > 0 else 0
    }


@api_router.post("/students/auto-assign")
async def auto_assign_unassigned_students(
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.PLANS_PROGRAMS, UserRole.STAFF]))
):
    """
    Auto-assign all students who don't have a flight.
    PROTECTION: Students with existing flight assignments are NOT changed.
    """
    # Valid flight values (both lowercase and capitalized for case-insensitive matching)
    valid_flights_all_cases = ALL_FLIGHTS + [f.capitalize() for f in ALL_FLIGHTS] + [f.upper() for f in ALL_FLIGHTS]
    
    # Find all students without a valid flight assignment
    unassigned = await db.participants.find(
        {
            "participant_type": {"$in": ["basic_student", "advanced_student"]},
            "is_removed": {"$ne": True},
            "$or": [
                {"flight": None},
                {"flight": ""},
                {"flight": {"$exists": False}},
                {"flight": {"$nin": valid_flights_all_cases}}
            ]
        },
        {"_id": 0}
    ).to_list(1000)
    
    if not unassigned:
        return {
            "message": "All students already have flight assignments",
            "assigned": 0,
            "total_unassigned": 0
        }
    
    # Use the batch assignment function
    result = await auto_assign_flights(unassigned)
    assignments = result.get("assignments", {})
    
    # Apply assignments to database
    assigned_count = 0
    for capid, assignment in assignments.items():
        await db.participants.update_one(
            {"capid": capid},
            {"$set": {
                "flight": assignment["flight"],
                "squadron": assignment["squadron"],
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        assigned_count += 1
    
    return {
        "message": f"Auto-assigned {assigned_count} students to flights",
        "assigned": assigned_count,
        "total_unassigned": len(unassigned),
        "flight_counts": result.get("flight_counts", {})
    }


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
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.FINANCE]))
):
    """Manually trigger sync of roster payment data to budget"""
    result = await sync_roster_to_budget()
    return result



