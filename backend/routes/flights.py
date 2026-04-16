"""Flight Roster and Flight Leadership routes"""
from fastapi import Depends, HTTPException
from typing import List
from datetime import datetime, timezone
import uuid

from database import db, api_router
from models import UserRole
from permissions import get_current_user, require_role

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

# ================= FLIGHT LEADERSHIP =================

# Map position field values to leadership role keys
POSITION_TO_ROLE = {
    "flight commander": "flight_commander",
    "flight sergeant": "flight_sergeant",
    "squadron commander": "squadron_commander",
    "first sergeant": "first_sergeant",
}

FLIGHT_TO_SQUADRON = {
    "alpha": "6th_cts", "bravo": "6th_cts",
    "charlie": "21st_cts", "delta": "21st_cts",
    "echo": "22nd_cts", "foxtrot": "22nd_cts",
}


async def _resolve_leadership(flight_lower: str) -> dict:
    """Build leadership for a flight by auto-detecting cadre with assigned positions,
    then overlaying any manual overrides from the flight_leadership collection."""
    result = {
        "flight": flight_lower,
        "flight_sergeant": {"name": "", "rank": "", "capid": "", "auto": False},
        "flight_commander": {"name": "", "rank": "", "capid": "", "auto": False},
        "squadron_commander": {"name": "", "rank": "", "capid": "", "auto": False},
    }

    # 1. Auto-detect from cadre assigned to this flight with a position
    cadre_in_flight = await db.participants.find(
        {
            "flight": flight_lower,
            "participant_type": {"$in": ["cadre", "staff", "senior_member"]},
            "position": {"$exists": True, "$ne": None, "$ne": ""},
            "is_removed": {"$ne": True},
        },
        {"_id": 0, "first_name": 1, "last_name": 1, "rank": 1, "capid": 1, "position": 1},
    ).to_list(50)

    for cadre in cadre_in_flight:
        pos_lower = (cadre.get("position") or "").lower().strip()
        role_key = POSITION_TO_ROLE.get(pos_lower)
        if role_key and role_key in result:
            result[role_key] = {
                "name": f"{cadre.get('last_name', '')}, {cadre.get('first_name', '')}",
                "rank": cadre.get("rank", ""),
                "capid": cadre.get("capid", ""),
                "auto": True,
            }

    # 2. Auto-detect squadron commander from cadre assigned to the parent squadron
    squadron = FLIGHT_TO_SQUADRON.get(flight_lower)
    if squadron and not result["squadron_commander"]["name"]:
        sq_flights = [f for f, s in FLIGHT_TO_SQUADRON.items() if s == squadron]
        sq_cmdr = await db.participants.find_one(
            {
                "position": {"$regex": "^squadron commander$", "$options": "i"},
                "participant_type": {"$in": ["cadre", "staff", "senior_member"]},
                "$or": [
                    {"squadron": squadron},
                    {"flight": {"$in": sq_flights}},
                ],
                "is_removed": {"$ne": True},
            },
            {"_id": 0, "first_name": 1, "last_name": 1, "rank": 1, "capid": 1},
        )
        if sq_cmdr:
            result["squadron_commander"] = {
                "name": f"{sq_cmdr.get('last_name', '')}, {sq_cmdr.get('first_name', '')}",
                "rank": sq_cmdr.get("rank", ""),
                "capid": sq_cmdr.get("capid", ""),
                "auto": True,
            }

    # 3. Overlay manual overrides (if someone typed in leadership manually)
    manual = await db.flight_leadership.find_one(
        {"flight": flight_lower}, {"_id": 0}
    )
    if manual:
        for key in ("flight_sergeant", "flight_commander", "squadron_commander"):
            manual_entry = manual.get(key, {})
            if manual_entry.get("name"):
                result[key] = {
                    "name": manual_entry["name"],
                    "rank": manual_entry.get("rank", ""),
                    "capid": manual_entry.get("capid", ""),
                    "auto": False,
                }

    return result


@api_router.get("/flights/{flight}/leadership")
async def get_flight_leadership(flight: str, user: dict = Depends(get_current_user)):
    """Get leadership assignments for a flight — auto-detected from cadre positions + manual overrides"""
    return await _resolve_leadership(flight.lower())

@api_router.put("/flights/{flight}/leadership")
async def update_flight_leadership(
    flight: str,
    leadership: dict,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF, UserRole.EXEC_CADRE]))
):
    """Update leadership assignments for a flight"""
    flight_lower = flight.lower()
    valid_flights = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
    if flight_lower not in valid_flights:
        raise HTTPException(status_code=400, detail="Invalid flight")
    
    doc = {
        "flight": flight_lower,
        "flight_sergeant": {
            "name": leadership.get("flight_sergeant", {}).get("name", ""),
            "rank": leadership.get("flight_sergeant", {}).get("rank", "")
        },
        "flight_commander": {
            "name": leadership.get("flight_commander", {}).get("name", ""),
            "rank": leadership.get("flight_commander", {}).get("rank", "")
        },
        "squadron_commander": {
            "name": leadership.get("squadron_commander", {}).get("name", ""),
            "rank": leadership.get("squadron_commander", {}).get("rank", "")
        },
        "updated_by": user.get("id"),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.flight_leadership.update_one(
        {"flight": flight_lower},
        {"$set": doc},
        upsert=True
    )
    return doc



@api_router.get("/my-flight")
async def get_my_flight_info(user: dict = Depends(get_current_user)):
    """Get current user's flight information and accessible flights"""
    user_flight = (user.get("flight") or "").lower()
    user_role = user.get("role")
    user_squadron = (user.get("squadron") or "").lower()
    
    flight_to_squadron = {
        "alpha": "6th_cts", "bravo": "6th_cts",
        "charlie": "21st_cts", "delta": "21st_cts",
        "echo": "22nd_cts", "foxtrot": "22nd_cts"
    }
    
    squadron_flights = {
        "6th_cts": ["alpha", "bravo"],
        "21st_cts": ["charlie", "delta"],
        "22nd_cts": ["echo", "foxtrot"]
    }
    
    all_flights = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
    all_squadrons = ["6th_cts", "21st_cts", "22nd_cts"]
    
    # Full access roles
    if user_role in [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.EXEC_CADRE, UserRole.DCP]:
        accessible_flights = all_flights
        accessible_squadrons = all_squadrons
    # Squadron-level roles: see both flights in their squadron
    elif user_role in [UserRole.SQUADRON_COMMANDER, UserRole.TRAINING_OFFICER]:
        sq = user_squadron if user_squadron in squadron_flights else flight_to_squadron.get(user_flight, "")
        if sq and sq in squadron_flights:
            accessible_flights = squadron_flights[sq]
            accessible_squadrons = [sq]
        else:
            accessible_flights = all_flights
            accessible_squadrons = all_squadrons
    elif user_squadron and user_squadron in squadron_flights:
        # Other squadron-assigned staff
        accessible_flights = squadron_flights[user_squadron]
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
        "has_full_access": user_role in [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.EXEC_CADRE, UserRole.DCP]
    }



