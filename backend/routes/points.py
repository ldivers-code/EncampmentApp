"""Point Tracking and Honor Awards Routes"""
from fastapi import Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from database import db, api_router
from models import (
    UserRole, ScoreCategoryCreate, ScoreCategoryResponse,
    ScoreEntryCreate, ScoreEntryResponse,
    MeritDemeritEntry, MeritDemeritResponse
)
from permissions import get_current_user, require_role

# ================= POINT TRACKING ROUTES =================

# Roles that can enter scores
SCORE_ENTRY_ROLES = [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF, UserRole.PLANS_PROGRAMS, UserRole.EXEC_CADRE]

@api_router.get("/points/categories")
async def get_score_categories(user: dict = Depends(get_current_user)):
    """Get all score categories"""
    categories = await db.score_categories.find({"is_active": True}, {"_id": 0}).to_list(100)
    return categories

@api_router.post("/points/categories")
async def create_score_category(
    category: ScoreCategoryCreate,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.PLANS_PROGRAMS]))
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
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.PLANS_PROGRAMS]))
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
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
):
    """Delete (deactivate) a score category"""
    await db.score_categories.update_one(
        {"id": category_id},
        {"$set": {"is_active": False}}
    )
    return {"message": "Category deactivated"}

@api_router.post("/points/categories/seed-defaults")
async def seed_default_categories(
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.PLANS_PROGRAMS]))
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
        participant_query["participant_type"] = {"$in": ["cadre", "exec_cadre", "staff", "senior_staff", "senior_member"]}
    
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
    if user["role"] not in [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF, UserRole.PLANS_PROGRAMS, UserRole.EXEC_CADRE]:
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
    if user["role"] not in [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.PLANS_PROGRAMS]:
        raise HTTPException(status_code=403, detail="Not authorized to delete awards")
    
    result = await db.honor_awards.delete_one({"id": award_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Award not found")
    
    return {"message": "Award deleted"}

@api_router.post("/points/awards/auto-assign/{date}")
async def auto_assign_daily_awards(date: str, user: dict = Depends(get_current_user)):
    """Automatically assign daily awards based on highest points for a date"""
    if user["role"] not in [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF, UserRole.PLANS_PROGRAMS]:
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



