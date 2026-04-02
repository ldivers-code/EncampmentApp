"""Stats and Dashboard routes"""
from fastapi import Depends, HTTPException
from datetime import datetime, timezone

from database import db, api_router
from models import UserRole
from permissions import get_current_user, require_role, get_user_permissions

# ================= STATS ROUTES =================

@api_router.get("/stats/dashboard")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    participants = await db.participants.find({"is_removed": {"$ne": True}}, {"_id": 0}).to_list(1000)
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

@api_router.get("/stats/dashboard-quickview")
async def get_dashboard_quickview(user: dict = Depends(get_current_user)):
    """Return role-specific quick-view data for the dashboard"""
    role = user.get("role", "cadre")
    permissions = user.get("permissions", {})
    data = {}

    # --- Admin/Command quick-view: pending approvals ---
    admin_roles = ["dcp", "commander", "executive_staff", "plans_programs"]
    if role in admin_roles or permissions.get("admin_panel"):
        pending_count = await db.users.count_documents({"is_approved": {"$ne": True}})
        unlinked_count = await db.users.count_documents({
            "is_approved": True,
            "$or": [{"linked_participant_id": None}, {"linked_participant_id": {"$exists": False}}]
        })
        data["admin"] = {"pending_approvals": pending_count, "unlinked_users": unlinked_count}

    # --- Check-in quick-view ---
    checkin_roles = ["dcp", "commander", "executive_staff", "plans_programs", "logistics", "support_logistics"]
    if role in checkin_roles or permissions.get("check_in_view") or permissions.get("page_check_in"):
        base = {"is_removed": {"$ne": True}}
        total = await db.participants.count_documents(base)
        check_ins = await db.check_ins.find({}, {"_id": 0, "steps": 1}).to_list(1000)
        fully_checked = sum(1 for ci in check_ins if sum(1 for s in ["arrival", "paperwork", "bunk_assignment", "gear_issue"] if ci.get("steps", {}).get(s, {}).get("completed")) == 4)
        data["check_in"] = {"total": total, "checked_in": fully_checked, "remaining": total - fully_checked}

    # --- Health quick-view ---
    health_roles = ["dcp", "commander", "executive_staff", "health_services", "support_health"]
    if role in health_roles or permissions.get("health_full") or permissions.get("page_health"):
        open_incidents = await db.hs_incidents.count_documents({"status": {"$in": ["open", "monitoring"]}})
        # Count cadets with any active medication
        active_meds = await db.hs_medication_profiles.count_documents({"active": True})
        # Count critical flags from allergies
        critical = await db.hs_allergies.count_documents({
            "$or": [
                {"allergy_text": {"$regex": "epipen|anaphylaxis|inhaler", "$options": "i"}},
                {"reaction_type": "anaphylaxis"}
            ]
        })
        data["health"] = {"open_incidents": open_incidents, "active_medications": active_meds, "critical_flags": critical}

    # --- Budget/Finance quick-view ---
    finance_roles = ["dcp", "commander", "executive_staff", "finance"]
    if role in finance_roles or permissions.get("budget_view"):
        budget_items = await db.budget.find({}, {"_id": 0, "estimated": 1, "actual": 1, "payment_status": 1}).to_list(1000)
        total_est = sum(i.get("estimated", 0) for i in budget_items)
        total_act = sum(i.get("actual", 0) for i in budget_items)
        unpaid_items = sum(1 for i in budget_items if i.get("payment_status") != "paid" and i.get("actual", 0) > 0)
        data["budget"] = {"total_estimated": total_est, "total_actual": total_act, "variance": total_est - total_act, "unpaid_items": unpaid_items}

    # --- Logistics quick-view ---
    logistics_roles = ["dcp", "commander", "executive_staff", "logistics", "support_logistics"]
    if role in logistics_roles or permissions.get("page_logistics"):
        open_supply = await db.supply_requests.count_documents({"status": {"$in": ["pending", "approved"]}})
        radios_out = await db.radios.count_documents({"status": "checked_out"})
        lost_items = await db.lost_found.count_documents({"status": "lost"})
        data["logistics"] = {"open_supply_requests": open_supply, "radios_checked_out": radios_out, "lost_items": lost_items}

    # --- Training Officer quick-view ---
    training_roles = ["dcp", "commander", "executive_staff", "training_officer", "squadron_commander"]
    if role in training_roles or permissions.get("page_training"):
        open_issues = await db.cadre_issues.count_documents({"status": {"$in": ["open", "in_progress"]}})
        recent_counseling = await db.counseling_logs.count_documents({})
        data["training"] = {"open_cadre_issues": open_issues, "counseling_logs": recent_counseling}

    # --- Flight info quick-view (for cadre/support/squadron commanders) ---
    cadre_roles = ["cadre", "exec_cadre", "squadron_commander", "support_logistics", "support_comms", "support_pa", "support_dining", "support_health"]
    if role in cadre_roles:
        user_flight = user.get("flight", "")
        user_squadron = user.get("squadron", "")
        flight_data = {}
        if user_flight:
            flight_count = await db.participants.count_documents({"flight": {"$regex": f"^{user_flight}$", "$options": "i"}, "is_removed": {"$ne": True}})
            flight_data["flight"] = user_flight
            flight_data["flight_count"] = flight_count
        if user_squadron:
            flight_data["squadron"] = user_squadron
        data["my_unit"] = flight_data

    # --- Dining quick-view ---
    dining_roles = ["dcp", "commander", "executive_staff", "dining_facility", "support_dining"]
    if role in dining_roles or permissions.get("page_meal_plan"):
        total_pax = await db.participants.count_documents({"is_removed": {"$ne": True}})
        meal_plans = await db.meal_plans.count_documents({})
        data["dining"] = {"total_headcount": total_pax, "meal_plans_set": meal_plans}

    # --- Barracks quick-view ---
    barracks_roles = ["dcp", "commander", "executive_staff", "plans_programs", "logistics", "support_logistics"]
    if role in barracks_roles or permissions.get("page_barracks"):
        assigned_bunks = await db.bunk_assignments.count_documents({})
        total_capacity = 250  # 5 barracks x 25 bunks x 2 positions
        data["barracks"] = {"assigned": assigned_bunks, "total_capacity": total_capacity, "available": total_capacity - assigned_bunks}

    # --- Flight reports (for squadron/exec commanders) ---
    report_roles = ["dcp", "commander", "executive_staff", "squadron_commander", "exec_cadre"]
    if role in report_roles:
        pending_reports = await db.flight_reports.count_documents({"status": "submitted"})
        escalated = await db.flight_reports.count_documents({"status": "escalated"})
        data["reports"] = {"pending_review": pending_reports, "escalated": escalated}

    return data


