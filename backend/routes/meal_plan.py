"""Meal Plan Schedule routes"""
from fastapi import Depends, HTTPException
from datetime import datetime, timezone
import uuid

from database import db, api_router
from models import UserRole
from permissions import get_current_user, require_role

from pydantic import BaseModel
from typing import Optional

# ================= MEAL PLAN SCHEDULE =================

MEAL_PLAN_EDITOR_ROLES = [
    UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF,
    UserRole.PLANS_PROGRAMS, UserRole.DINING_FACILITY
]

class MealPlanBase(BaseModel):
    date: str  # ISO date string
    meal_type: str  # breakfast, lunch, dinner, snack
    menu_items: str  # Description of menu items
    location: Optional[str] = None
    time: Optional[str] = None  # e.g. "0700", "1200"
    notes: Optional[str] = None
    headcount: Optional[int] = None
    dietary_notes: Optional[str] = None

class MealPlanCreate(MealPlanBase):
    pass

class MealPlanResponse(MealPlanBase):
    id: str
    created_by: str
    updated_by: Optional[str] = None
    created_at: str
    updated_at: str


@api_router.get("/meal-plans")
async def get_meal_plans(user: dict = Depends(get_current_user)):
    """Get all meal plans"""
    plans = await db.meal_plans.find({}, {"_id": 0}).sort([("date", 1), ("meal_type", 1)]).to_list(1000)
    return plans


@api_router.post("/meal-plans", response_model=MealPlanResponse)
async def create_meal_plan(
    data: MealPlanCreate,
    user: dict = Depends(require_role(MEAL_PLAN_EDITOR_ROLES))
):
    """Create a new meal plan entry"""
    now = datetime.now(timezone.utc).isoformat()
    plan = {
        "id": str(uuid.uuid4()),
        **data.dict(),
        "created_by": user["name"],
        "updated_by": None,
        "created_at": now,
        "updated_at": now
    }
    await db.meal_plans.insert_one(plan)
    plan.pop("_id", None)
    return MealPlanResponse(**plan)


@api_router.put("/meal-plans/{plan_id}", response_model=MealPlanResponse)
async def update_meal_plan(
    plan_id: str,
    data: MealPlanCreate,
    user: dict = Depends(require_role(MEAL_PLAN_EDITOR_ROLES))
):
    """Update an existing meal plan entry"""
    existing = await db.meal_plans.find_one({"id": plan_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Meal plan not found")

    now = datetime.now(timezone.utc).isoformat()
    await db.meal_plans.update_one({"id": plan_id}, {"$set": {
        **data.dict(),
        "updated_by": user["name"],
        "updated_at": now
    }})
    updated = await db.meal_plans.find_one({"id": plan_id}, {"_id": 0})
    return MealPlanResponse(**updated)


@api_router.delete("/meal-plans/{plan_id}")
async def delete_meal_plan(
    plan_id: str,
    user: dict = Depends(require_role(MEAL_PLAN_EDITOR_ROLES))
):
    """Delete a meal plan entry"""
    result = await db.meal_plans.delete_one({"id": plan_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    return {"message": "Meal plan deleted"}



