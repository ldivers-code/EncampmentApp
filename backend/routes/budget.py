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



# ================= PAYMENT REPORT ENDPOINTS =================

@api_router.post("/participants/import-payments")
async def import_payment_report(
    file: UploadFile = File(...),
    user: dict = Depends(require_finance_access())
):
    """Import payment reports - auto-detects format:
    1) Daily Payments report (CAPID, FullName, Amount, PaymentDate, PaymentType) - each row = a payment
    2) eCAP EventAdmin report (RegistrantsCAPID, PaidInFull, AmountPaid, etc.) - status-based
    Matches by CAPID, overwrites existing payment data.
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        df.columns = df.columns.str.strip()
        cols = set(df.columns)
        
        now = datetime.now(timezone.utc).isoformat()
        matched = 0
        updated = 0
        not_found = []
        report_format = "unknown"
        
        # Auto-detect format
        is_daily_payments = 'FullName' in cols and 'Amount' in cols and 'PaymentDate' in cols
        is_ecap_admin = 'PaidInFull' in cols or 'RegistrationStatus' in cols or 'AmountPaid' in cols
        
        if is_daily_payments:
            report_format = "daily_payments"
            matched, updated, not_found = await _import_daily_payments(df, now)
        elif is_ecap_admin:
            report_format = "ecap_admin"
            matched, updated, not_found = await _import_ecap_admin(df, now)
        else:
            raise HTTPException(status_code=400, detail=f"Unrecognized report format. Expected columns like 'FullName'+'Amount'+'PaymentDate' (Daily Payments) or 'PaidInFull'/'RegistrationStatus' (eCAP Admin). Found: {', '.join(sorted(cols)[:15])}")
        
        import_log = {
            "id": str(uuid.uuid4()),
            "type": "payment_report",
            "format": report_format,
            "filename": file.filename,
            "imported_by": user.get("name", user.get("email")),
            "imported_at": now,
            "total_rows": len(df),
            "matched": matched,
            "updated": updated,
            "not_found_count": len(not_found),
            "not_found_sample": not_found[:20],
        }
        await db.payment_imports.insert_one(import_log)
        import_log.pop("_id", None)
        
        try:
            from routes.students import sync_roster_to_budget
            budget_sync = await sync_roster_to_budget()
        except Exception:
            budget_sync = None
        
        return {
            "message": f"Payment report imported ({report_format}): {matched} matched, {updated} updated, {len(not_found)} not on roster",
            "format": report_format,
            "matched": matched,
            "updated": updated,
            "not_found": not_found[:20],
            "budget_sync": budget_sync,
            "import_id": import_log["id"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing payment report: {str(e)}")


async def _resolve_capid(raw_capid, full_name=None):
    """Resolve a CAPID to a participant, handling corrupted Excel serial numbers.
    Falls back to name matching if CAPID doesn't match."""
    capid = str(raw_capid).strip()
    if not capid or capid == 'nan':
        return None, capid
    
    # Handle Excel date serial number corruption (e.g. 46069.7049375347)
    if '.' in capid:
        try:
            capid = str(int(float(capid)))
        except (ValueError, TypeError):
            pass
    
    # Remove leading zeros but keep at least 1 digit
    capid = capid.lstrip('0') or '0'
    
    existing = await db.participants.find_one(
        {"capid": capid, "is_removed": {"$ne": True}},
        {"_id": 0, "id": 1, "last_name": 1, "first_name": 1, "capid": 1}
    )
    if existing:
        return existing, capid
    
    # Fallback: try name matching if we have a full name
    if full_name and full_name != 'nan':
        name_clean = full_name.strip()
        if ',' in name_clean:
            parts = name_clean.split(',', 1)
            last = parts[0].strip()
            first = parts[1].strip().split()[0] if parts[1].strip() else ""
        else:
            parts = name_clean.split()
            last = parts[-1] if parts else ""
            first = parts[0] if len(parts) > 1 else ""
        
        if last:
            import re
            existing = await db.participants.find_one(
                {
                    "last_name": {"$regex": f"^{re.escape(last)}$", "$options": "i"},
                    "first_name": {"$regex": f"^{re.escape(first)}", "$options": "i"},
                    "is_removed": {"$ne": True}
                },
                {"_id": 0, "id": 1, "last_name": 1, "first_name": 1, "capid": 1}
            )
            if existing:
                return existing, existing.get("capid", capid)
    
    return None, capid


async def _import_daily_payments(df, now):
    """Import Daily Payments report: each row = a payment transaction.
    Presence in report means person has paid."""
    matched = 0
    updated = 0
    not_found = []
    
    # Aggregate payments per person (they might have multiple rows)
    payments_by_person = {}
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        raw_capid = row_dict.get('CAPID', '')
        full_name = str(row_dict.get('FullName', '')).strip()
        amount = 0
        try:
            amount = float(row_dict.get('Amount', 0))
        except (ValueError, TypeError):
            pass
        
        payment_date_raw = row_dict.get('PaymentDate')
        payment_type = str(row_dict.get('PaymentType', '')).strip()
        if payment_type == 'nan':
            payment_type = ''
        
        # Parse payment date
        payment_date = None
        if payment_date_raw and str(payment_date_raw) != 'nan':
            if isinstance(payment_date_raw, datetime):
                payment_date = payment_date_raw.isoformat()
            else:
                try:
                    from dateutil import parser as dateparser
                    payment_date = dateparser.parse(str(payment_date_raw)).isoformat()
                except Exception:
                    payment_date = str(payment_date_raw)
        
        key = f"{raw_capid}|{full_name}"
        if key not in payments_by_person:
            payments_by_person[key] = {
                "raw_capid": raw_capid,
                "full_name": full_name,
                "total_amount": 0,
                "payments": [],
            }
        payments_by_person[key]["total_amount"] += amount
        payments_by_person[key]["payments"].append({
            "amount": amount,
            "date": payment_date,
            "type": payment_type,
        })
    
    for key, person in payments_by_person.items():
        existing, capid = await _resolve_capid(person["raw_capid"], person["full_name"])
        
        if not existing:
            not_found.append({"capid": capid, "name": person["full_name"]})
            continue
        
        matched += 1
        
        payment_update = {
            "paid": True,
            "paid_in_full": True,
            "amount_paid": person["total_amount"],
            "updated_at": now,
            "payment_last_synced": now,
            "payment_history": person["payments"],
        }
        
        if person["payments"]:
            last_payment = person["payments"][-1]
            if last_payment.get("date"):
                payment_update["last_payment_date"] = last_payment["date"]
            if last_payment.get("type"):
                payment_update["payment_type"] = last_payment["type"]
        
        result = await db.participants.update_one(
            {"id": existing["id"]},
            {"$set": payment_update}
        )
        if result.modified_count > 0:
            updated += 1
    
    return matched, updated, not_found


async def _import_ecap_admin(df, now):
    """Import eCAP EventAdmin report: status-based with PaidInFull, RegistrationStatus, etc."""
    column_map = {
        'RegistrantsCAPID': 'capid', 'CAPID': 'capid',
        'PaidInFull': 'paid_in_full', 'AmountPaid': 'amount_paid',
        'RegistrationStatus': 'registration_status',
        'InvoiceStatus': 'invoice_status', 'InvoiceID': 'invoice_id',
        'UnitApproved': 'unit_approved', 'WingApproved': 'wing_approved',
        'ParentApproved': 'parent_approved',
        'NameLast': 'last_name', 'NameFirst': 'first_name',
    }
    df = df.rename(columns=column_map)
    
    matched = 0
    updated = 0
    not_found = []
    
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        capid = str(row_dict.get('capid', '')).strip()
        if not capid or capid == 'nan':
            continue
        if '.' in capid:
            try:
                capid = str(int(float(capid)))
            except (ValueError, TypeError):
                pass
        
        existing = await db.participants.find_one({"capid": capid, "is_removed": {"$ne": True}}, {"_id": 0, "id": 1})
        if not existing:
            last = str(row_dict.get('last_name', '')).strip()
            first = str(row_dict.get('first_name', '')).strip()
            if last != 'nan' and first != 'nan':
                not_found.append({"capid": capid, "name": f"{last}, {first}"})
            continue
        
        matched += 1
        
        def get_val(key, vtype='str'):
            val = row_dict.get(key)
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return None
            if vtype == 'bool':
                if isinstance(val, bool):
                    return val
                return str(val).lower() in ['yes', 'true', '1']
            if vtype == 'float':
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None
            s = str(val).strip()
            return s if s and s != 'nan' else None
        
        paid_in_full = get_val('paid_in_full', 'bool')
        amount_paid = get_val('amount_paid', 'float')
        
        payment_update = {"updated_at": now, "payment_last_synced": now}
        
        if paid_in_full is not None:
            payment_update["paid_in_full"] = paid_in_full
            payment_update["paid"] = paid_in_full
        if amount_paid is not None:
            payment_update["amount_paid"] = amount_paid
            if amount_paid > 0 and paid_in_full is None:
                payment_update["paid"] = True
                payment_update["paid_in_full"] = True
        
        for field, key in [("registration_status", "registration_status"), ("invoice_status", "invoice_status"), ("invoice_id", "invoice_id")]:
            v = get_val(key)
            if v:
                payment_update[field] = v
        
        for field, key in [("unit_approved", "unit_approved"), ("wing_approved", "wing_approved"), ("parent_approved", "parent_approved")]:
            v = get_val(key, 'bool')
            if v is not None:
                payment_update[field] = v
        
        result = await db.participants.update_one({"id": existing["id"]}, {"$set": payment_update})
        if result.modified_count > 0:
            updated += 1
    
    return matched, updated, not_found


@api_router.get("/participants/payment-summary")
async def get_payment_summary(user: dict = Depends(require_finance_access())):
    """Get detailed payment collection summary broken down by participant type"""
    participants = await db.participants.find(
        {"is_removed": {"$ne": True}},
        {"_id": 0, "capid": 1, "rank": 1, "last_name": 1, "first_name": 1,
         "participant_type": 1, "member_type": 1, "flight": 1, "squadron": 1,
         "paid": 1, "paid_in_full": 1, "amount_paid": 1, "registration_status": 1,
         "invoice_status": 1, "unit_approved": 1, "wing_approved": 1, "parent_approved": 1,
         "email": 1, "cadet_parent_email": 1, "unit_cc_email": 1, "wing": 1, "unit": 1,
         "payment_last_synced": 1}
    ).to_list(2000)
    
    summary = {
        "total": len(participants),
        "paid": 0,
        "unpaid": 0,
        "total_collected": 0.0,
        "by_type": {},
        "by_flight": {},
        "by_status": {"approved": 0, "pending": 0, "other": 0},
        "unit_approved": 0,
        "wing_approved": 0,
        "participants": [],
        "last_import": None,
    }
    
    for p in participants:
        is_paid = p.get('paid') or p.get('paid_in_full')
        ptype = p.get('participant_type', 'unknown')
        flight = (p.get('flight') or 'unassigned').lower()
        
        if is_paid:
            summary["paid"] += 1
        else:
            summary["unpaid"] += 1
        
        amt = float(p.get('amount_paid') or 0)
        summary["total_collected"] += amt
        
        if ptype not in summary["by_type"]:
            summary["by_type"][ptype] = {"total": 0, "paid": 0, "unpaid": 0, "collected": 0.0}
        summary["by_type"][ptype]["total"] += 1
        if is_paid:
            summary["by_type"][ptype]["paid"] += 1
        else:
            summary["by_type"][ptype]["unpaid"] += 1
        summary["by_type"][ptype]["collected"] += amt
        
        if flight not in summary["by_flight"]:
            summary["by_flight"][flight] = {"total": 0, "paid": 0, "unpaid": 0}
        summary["by_flight"][flight]["total"] += 1
        if is_paid:
            summary["by_flight"][flight]["paid"] += 1
        else:
            summary["by_flight"][flight]["unpaid"] += 1
        
        reg = (p.get('registration_status') or '').lower()
        if 'approved' in reg:
            summary["by_status"]["approved"] += 1
        elif 'pending' in reg or not reg:
            summary["by_status"]["pending"] += 1
        else:
            summary["by_status"]["other"] += 1
        
        if p.get('unit_approved'):
            summary["unit_approved"] += 1
        if p.get('wing_approved'):
            summary["wing_approved"] += 1
        
        summary["participants"].append({
            "capid": p.get("capid"),
            "name": f"{p.get('rank', '')} {p.get('last_name', '')}, {p.get('first_name', '')}".strip(),
            "participant_type": ptype,
            "flight": flight,
            "paid": bool(is_paid),
            "amount_paid": amt,
            "registration_status": p.get("registration_status"),
            "unit_approved": bool(p.get("unit_approved")),
            "wing_approved": bool(p.get("wing_approved")),
            "parent_approved": bool(p.get("parent_approved")),
            "email": p.get("email"),
            "parent_email": p.get("cadet_parent_email"),
            "unit_cc_email": p.get("unit_cc_email"),
            "wing": p.get("wing"),
            "unit": p.get("unit"),
            "last_synced": p.get("payment_last_synced"),
        })
    
    last_import = await db.payment_imports.find_one(
        {"type": "payment_report"},
        {"_id": 0},
        sort=[("imported_at", -1)]
    )
    summary["last_import"] = last_import
    
    return summary


@api_router.get("/payment-imports")
async def get_payment_import_history(user: dict = Depends(require_finance_access())):
    """Get history of payment report imports"""
    imports = await db.payment_imports.find(
        {"type": "payment_report"},
        {"_id": 0}
    ).sort("imported_at", -1).to_list(50)
    return imports



