"""Budget and Quick Update routes"""
from fastapi import Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from io import BytesIO
import pandas as pd
from datetime import datetime, timezone
import uuid

from database import db, api_router
from models import (
    UserRole, BudgetItemCreate, BudgetItemResponse,
    FoodExpenseSettings, FoodExpenseSettingsUpdate
)
from permissions import get_current_user, require_role

# ================= BUDGET ROUTES =================

# Helper to check if user can access financials
def require_finance_access():
    """Require Commander or Finance role for budget access"""
    async def checker(user: dict = Depends(get_current_user)):
        if user["role"] not in [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.FINANCE]:
            raise HTTPException(status_code=403, detail="Access restricted to Commander and Finance roles")
        return user
    return checker


@api_router.get("/budget", response_model=List[BudgetItemResponse])
async def get_budget(user: dict = Depends(require_finance_access())):
    """Get all budget items - restricted to Commander and Finance roles"""
    items = await db.budget.find({}, {"_id": 0}).to_list(1000)
    return [BudgetItemResponse(**i) for i in items]


@api_router.post("/budget", response_model=BudgetItemResponse)
async def create_budget_item(
    data: BudgetItemCreate,
    user: dict = Depends(require_finance_access())
):
    item_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    doc = {
        "id": item_id,
        **data.model_dump(),
        "created_at": now,
        "updated_at": now
    }
    await db.budget.insert_one(doc)
    doc.pop("_id", None)
    return BudgetItemResponse(**doc)


@api_router.get("/budget/summary")
async def get_budget_summary(user: dict = Depends(require_finance_access())):
    """Get budget summary - restricted to Commander and Finance roles"""
    items = await db.budget.find({}, {"_id": 0}).to_list(1000)
    
    total_estimated = sum(i.get("estimated", 0) for i in items)
    total_actual = sum(i.get("actual", 0) for i in items)
    
    # Group by category
    categories = {}
    for item in items:
        cat = item.get("category", "General")
        if cat not in categories:
            categories[cat] = {"estimated": 0, "actual": 0}
        categories[cat]["estimated"] += item.get("estimated", 0)
        categories[cat]["actual"] += item.get("actual", 0)
    
    return {
        "total_estimated": total_estimated,
        "total_actual": total_actual,
        "variance": total_estimated - total_actual,
        "by_category": categories
    }


@api_router.get("/budget/food-settings")
async def get_food_expense_settings(user: dict = Depends(require_finance_access())):
    """Get food expense settings for cost-per-person-per-day calculation"""
    settings = await db.food_expense_settings.find_one({"_id": "settings"})
    
    # Get participant count from roster
    participant_count = await db.participants.count_documents({"is_removed": {"$ne": True}})
    
    # Default cost from 2026 TNWG Encampment Budget: $13.15 per person per day
    default_cost = 13.15
    
    if not settings:
        return {
            "cost_per_person_per_day": default_cost,
            "total_participants": participant_count,
            "total_days": 8,
            "notes": "Default: $13.15/day from TNWG Budget (July 17-24)",
            "total_food_budget": default_cost * participant_count * 8
        }
    
    cost = settings.get("cost_per_person_per_day", default_cost)
    participants = settings.get("total_participants") or participant_count
    days = settings.get("total_days", 8)
    
    return {
        "cost_per_person_per_day": cost,
        "total_participants": participants,
        "total_days": days,
        "notes": settings.get("notes", ""),
        "total_food_budget": cost * participants * days
    }


@api_router.put("/budget/food-settings")
async def update_food_expense_settings(
    data: FoodExpenseSettingsUpdate,
    user: dict = Depends(require_finance_access())
):
    """Update food expense settings"""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.food_expense_settings.update_one(
        {"_id": "settings"},
        {"$set": update_data},
        upsert=True
    )
    
    # Fetch and return updated settings
    settings = await db.food_expense_settings.find_one({"_id": "settings"})
    participant_count = await db.participants.count_documents({})
    
    cost = settings.get("cost_per_person_per_day", 15.0)
    participants = settings.get("total_participants") or participant_count
    days = settings.get("total_days", 8)
    
    return {
        "cost_per_person_per_day": cost,
        "total_participants": participants,
        "total_days": days,
        "notes": settings.get("notes", ""),
        "total_food_budget": cost * participants * days
    }


@api_router.post("/budget/import")
async def import_budget(
    file: UploadFile = File(...),
    user: dict = Depends(require_finance_access())
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        imported_count = 0
        now = datetime.now(timezone.utc).isoformat()
        
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            
            item_name = str(row_dict.get('item_name', row_dict.get('item', ''))).strip()
            if not item_name or item_name == 'nan':
                continue
            
            item_id = str(uuid.uuid4())
            
            doc = {
                "id": item_id,
                "category": str(row_dict.get('category', 'General')).strip() if pd.notna(row_dict.get('category')) else 'General',
                "subcategory": str(row_dict.get('subcategory', '')).strip() if pd.notna(row_dict.get('subcategory')) else None,
                "item_name": item_name,
                "estimated": float(row_dict.get('estimated', 0)) if pd.notna(row_dict.get('estimated')) else 0.0,
                "actual": float(row_dict.get('actual', 0)) if pd.notna(row_dict.get('actual')) else 0.0,
                "notes": str(row_dict.get('notes', '')).strip() if pd.notna(row_dict.get('notes')) else None,
                "created_at": now,
                "updated_at": now
            }
            
            await db.budget.insert_one(doc)
            imported_count += 1
        
        return {"message": f"Successfully imported {imported_count} budget items"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")


@api_router.post("/budget/seed-tnwg-template")
async def seed_tnwg_budget_template(
    user: dict = Depends(require_finance_access())
):
    """Seed budget with 2026 TNWG Encampment Budget template items"""
    
    # Check if budget already has items
    existing_count = await db.budget.count_documents({})
    if existing_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Budget already has {existing_count} items. Clear budget first or use import."
        )
    
    now = datetime.now(timezone.utc).isoformat()
    
    # 2026 TNWG Encampment Budget Template Items
    template_items = [
        # Income Sources
        {"category": "Participant Fees", "item_name": "Senior Members Staff", "estimated": 2400.0, "item_type": "income", "notes": "42 SM @ varies"},
        {"category": "Participant Fees", "item_name": "Cadet Cadre", "estimated": 9500.0, "item_type": "income", "notes": "38 Cadre @ $250"},
        {"category": "Participant Fees", "item_name": "Basic Students", "estimated": 22500.0, "item_type": "income", "notes": "90 Students @ $250"},
        {"category": "NHQ Allocations", "item_name": "CEAP Funds (Students)", "estimated": 0.0, "item_type": "income", "notes": "NHQ CEAP allocation for students"},
        {"category": "NHQ Allocations", "item_name": "CEAP Funds (Cadre)", "estimated": 0.0, "item_type": "income", "notes": "NHQ CEAP allocation for cadre"},
        {"category": "Donations", "item_name": "Heritage Wing Donations", "estimated": 560.0, "item_type": "income"},
        {"category": "Donations", "item_name": "Other Donations", "estimated": 0.0, "item_type": "income"},
        
        # Facility Expenses
        {"category": "Facility", "item_name": "VTS Catoosa Facility Rental", "estimated": 11000.0, "item_type": "expense", "vendor": "VTS Catoosa"},
        
        # DFAC Budget
        {"category": "DFAC Budget", "item_name": "Meals Contract", "estimated": 0.0, "item_type": "expense", "notes": "$13.15/person/day - see Food Planner"},
        {"category": "DFAC Budget", "item_name": "Hydration Supplies", "estimated": 200.0, "item_type": "expense"},
        {"category": "DFAC Budget", "item_name": "DFAC Supplies", "estimated": 150.0, "item_type": "expense"},
        {"category": "DFAC Budget", "item_name": "Bathroom/DFAC Supplies", "estimated": 100.0, "item_type": "expense"},
        
        # Graduation Budget
        {"category": "Graduation Budget", "item_name": "Awards / Challenge Coins", "estimated": 670.0, "item_type": "expense"},
        {"category": "Graduation Budget", "item_name": "Honors/Grad Packages", "estimated": 3500.0, "item_type": "expense"},
        {"category": "Graduation Budget", "item_name": "Honor Flight Streamers", "estimated": 20.0, "item_type": "expense"},
        
        # Commandants Budget
        {"category": "Commandants Budget", "item_name": "Miscellaneous", "estimated": 500.0, "item_type": "expense"},
        {"category": "Commandants Budget", "item_name": "Sport Event Equipment", "estimated": 0.0, "item_type": "expense"},
        {"category": "Commandants Budget", "item_name": "Esprit de Corps", "estimated": 100.0, "item_type": "expense"},
        
        # Deputy Commander Support
        {"category": "Deputy Commander Support", "item_name": "Support Budget", "estimated": 450.0, "item_type": "expense"},
        {"category": "Deputy Commander Support", "item_name": "Cleaning Equipment", "estimated": 100.0, "item_type": "expense"},
        {"category": "Deputy Commander Support", "item_name": "Laundry Materials", "estimated": 100.0, "item_type": "expense"},
        
        # Advanced Training School
        {"category": "Advanced Training School", "item_name": "Academic Materials", "estimated": 100.0, "item_type": "expense"},
        {"category": "Advanced Training School", "item_name": "AE Track", "estimated": 0.0, "item_type": "expense"},
        {"category": "Advanced Training School", "item_name": "CP Track", "estimated": 100.0, "item_type": "expense"},
        {"category": "Advanced Training School", "item_name": "ES Track", "estimated": 100.0, "item_type": "expense"},
        {"category": "Advanced Training School", "item_name": "Streamer Holder", "estimated": 0.0, "item_type": "expense"},
        
        # Public Affairs
        {"category": "Public Affairs", "item_name": "Computer Discs", "estimated": 0.0, "item_type": "expense"},
        {"category": "Public Affairs", "item_name": "Printer Materials", "estimated": 100.0, "item_type": "expense"},
        {"category": "Public Affairs", "item_name": "Office Supplies", "estimated": 0.0, "item_type": "expense"},
        {"category": "Public Affairs", "item_name": "Student Supplies", "estimated": 100.0, "item_type": "expense"},
        
        # Logistics
        {"category": "Logistics", "item_name": "Communications Budget", "estimated": 0.0, "item_type": "expense"},
        {"category": "Logistics", "item_name": "Activities", "estimated": 100.0, "item_type": "expense"},
        {"category": "Logistics", "item_name": "Equipment", "estimated": 0.0, "item_type": "expense"},
        {"category": "Logistics", "item_name": "In-Processing Materials", "estimated": 100.0, "item_type": "expense"},
        
        # Health Services
        {"category": "Health Services", "item_name": "Support Budget", "estimated": 0.0, "item_type": "expense"},
        {"category": "Health Services", "item_name": "Swim Fee", "estimated": 345.0, "item_type": "expense"},
        
        # T-Shirts & Merchandise
        {"category": "T-Shirts & Merchandise", "item_name": "Encampment T-Shirts", "estimated": 7000.0, "item_type": "expense"},
        {"category": "T-Shirts & Merchandise", "item_name": "Cadre Equipment", "estimated": 600.0, "item_type": "expense"},
        
        # Refunds
        {"category": "Refunds", "item_name": "CEAP Refunds", "estimated": 0.0, "item_type": "expense"},
        {"category": "Refunds", "item_name": "Registration Refunds", "estimated": 0.0, "item_type": "expense"},
    ]
    
    inserted_count = 0
    for item_data in template_items:
        item_id = str(uuid.uuid4())
        doc = {
            "id": item_id,
            "category": item_data["category"],
            "subcategory": item_data.get("subcategory"),
            "item_name": item_data["item_name"],
            "estimated": item_data.get("estimated", 0.0),
            "actual": item_data.get("actual", 0.0),
            "notes": item_data.get("notes"),
            "vendor": item_data.get("vendor"),
            "item_type": item_data.get("item_type", "expense"),
            "payment_status": "pending",
            "created_at": now,
            "updated_at": now
        }
        await db.budget.insert_one(doc)
        inserted_count += 1
    
    # Also update food settings with TNWG defaults
    await db.food_expense_settings.update_one(
        {"_id": "settings"},
        {"$set": {
            "cost_per_person_per_day": 13.15,
            "total_participants": 170,  # 42 SM + 38 Cadre + 90 Students
            "total_days": 8,
            "notes": "2026 TNWG Encampment: $13.15/day (Breakfast + Lunch + Dinner)",
            "updated_at": now
        }},
        upsert=True
    )
    
    return {
        "message": f"Successfully seeded {inserted_count} budget items from TNWG template",
        "items_created": inserted_count,
        "food_settings_updated": True
    }


# ================= QUICK UPDATE ENDPOINTS =================

class QuickActualUpdate(BaseModel):
    actual: float
    payment_status: Optional[str] = None
    payment_date: Optional[str] = None


@api_router.patch("/budget/{item_id}/actual")
async def quick_update_actual(
    item_id: str,
    data: QuickActualUpdate,
    user: dict = Depends(require_finance_access())
):
    """Quick update for actual value - for live budget tracking"""
    item = await db.budget.find_one({"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Budget item not found")
    
    update_data = {
        "actual": data.actual,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if data.payment_status:
        update_data["payment_status"] = data.payment_status
    if data.payment_date:
        update_data["payment_date"] = data.payment_date
    
    await db.budget.update_one({"id": item_id}, {"$set": update_data})
    
    updated_item = await db.budget.find_one({"id": item_id}, {"_id": 0})
    return BudgetItemResponse(**updated_item)


@api_router.post("/budget/{item_id}/mark-paid")
async def mark_budget_item_paid(
    item_id: str,
    user: dict = Depends(require_finance_access())
):
    """Mark a budget item as paid - sets actual=estimated if no actual, status=paid"""
    item = await db.budget.find_one({"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Budget item not found")
    
    # If no actual value set, use estimated
    actual = item.get("actual", 0) or item.get("estimated", 0)
    
    update_data = {
        "actual": actual,
        "payment_status": "paid",
        "payment_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.budget.update_one({"id": item_id}, {"$set": update_data})
    
    updated_item = await db.budget.find_one({"id": item_id}, {"_id": 0})
    return BudgetItemResponse(**updated_item)


# Receipt upload helper
import base64

@api_router.post("/budget/{item_id}/receipt")
async def upload_receipt(
    item_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(require_finance_access())
):
    """Upload a receipt image for a budget item"""
    # Verify budget item exists
    item = await db.budget.find_one({"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Budget item not found")
    
    # Check file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Allowed: JPEG, PNG, GIF, PDF"
        )
    
    # Read file and encode as base64
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum 5MB allowed.")
    
    # Store receipt as base64 data URL
    b64_content = base64.b64encode(contents).decode('utf-8')
    data_url = f"data:{file.content_type};base64,{b64_content}"
    
    # Update budget item with receipt
    await db.budget.update_one(
        {"id": item_id},
        {"$set": {
            "receipt_url": data_url,
            "receipt_filename": file.filename,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "Receipt uploaded successfully",
        "filename": file.filename,
        "item_id": item_id
    }


@api_router.delete("/budget/{item_id}/receipt")
async def delete_receipt(
    item_id: str,
    user: dict = Depends(require_finance_access())
):
    """Delete a receipt from a budget item"""
    item = await db.budget.find_one({"id": item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Budget item not found")
    
    await db.budget.update_one(
        {"id": item_id},
        {"$set": {
            "receipt_url": None,
            "receipt_filename": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Receipt deleted successfully"}


@api_router.put("/budget/{item_id}", response_model=BudgetItemResponse)
async def update_budget_item(
    item_id: str,
    data: BudgetItemCreate,
    user: dict = Depends(require_finance_access())
):
    now = datetime.now(timezone.utc).isoformat()
    update_data = {**data.model_dump(), "updated_at": now}
    
    result = await db.budget.update_one({"id": item_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Budget item not found")
    
    item = await db.budget.find_one({"id": item_id}, {"_id": 0})
    return BudgetItemResponse(**item)


@api_router.delete("/budget/{item_id}")
async def delete_budget_item(
    item_id: str,
    user: dict = Depends(require_finance_access())
):
    result = await db.budget.delete_one({"id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Budget item not found")
    return {"message": "Budget item deleted successfully"}



