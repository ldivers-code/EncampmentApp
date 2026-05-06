"""Participant CRUD, Analytics, and PDF Export routes"""
from fastapi import Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from io import BytesIO
import uuid
import logging

logger = logging.getLogger(__name__)

import hashlib

try:
    import pandas as pd
except ImportError:
    pd = None

from database import db, api_router
from models import (
    UserRole, ParticipantCreate, ParticipantResponse, ParticipantRemoval
)
from permissions import get_current_user, require_role
from routes.students import auto_assign_single_student, is_valid_flight, sync_roster_to_budget, find_existing_participant, find_match_with_candidates, link_to_user_account, determine_participant_type

# ================= PARTICIPANT ROUTES =================

SQUADRON_FLIGHTS_MAP = {
    "6th_cts": ["alpha", "bravo"],
    "21st_cts": ["charlie", "delta"],
    "22nd_cts": ["echo", "foxtrot"]
}
FLIGHT_TO_SQUADRON_MAP = {
    "alpha": "6th_cts", "bravo": "6th_cts",
    "charlie": "21st_cts", "delta": "21st_cts",
    "echo": "22nd_cts", "foxtrot": "22nd_cts"
}

def _apply_visibility_filter(query: dict, user: dict):
    """Apply role-based visibility filter to participant queries.
    Squadron-level roles (Squadron Commander, Training Officer) see both flights in their squadron.
    Flight-level roles (Cadre, Exec Cadre) see only their assigned flight.
    """
    user_role = user.get('role')
    user_flight = (user.get('flight') or '').lower()
    user_squadron = (user.get('squadron') or '').lower()

    if user_role == UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Parents do not have roster access")

    # Squadron-level roles: see both flights in their squadron
    squadron_level_roles = [UserRole.SQUADRON_COMMANDER, UserRole.TRAINING_OFFICER]
    if user_role in squadron_level_roles:
        sq = user_squadron or FLIGHT_TO_SQUADRON_MAP.get(user_flight, '')
        if sq and sq in SQUADRON_FLIGHTS_MAP:
            query["flight"] = {"$in": SQUADRON_FLIGHTS_MAP[sq]}
        return

    # Flight-level cadre: see only their assigned flight
    flight_level_roles = [UserRole.CADRE, UserRole.EXEC_CADRE]
    if user_role in flight_level_roles and user_flight:
        query["flight"] = user_flight


@api_router.get("/participants", response_model=List[ParticipantResponse])
async def get_participants(user: dict = Depends(get_current_user)):
    query = {"is_removed": {"$ne": True}}
    
    user_role = user.get('role')
    
    _apply_visibility_filter(query, user)
    
    participants = await db.participants.find(query, {"_id": 0}).to_list(1000)
    
    privileged_roles = [
        UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.DCP,
        UserRole.EXEC_CADRE, UserRole.PLANS_PROGRAMS,
        UserRole.FINANCE, UserRole.STAFF, UserRole.HEALTH_SERVICES
    ]
    
    if user_role not in privileged_roles:
        sensitive_fields = [
            'address', 'city', 'state', 'zip_code',
            'amount_paid', 'registration_status', 'notes', 'comments', 
            'religious_preference', 'shirt_size', 'unit_cc_name', 'unit_cc_email'
        ]
        filtered_participants = []
        for p in participants:
            filtered_p = dict(p)
            for field in sensitive_fields:
                if field in filtered_p:
                    filtered_p[field] = None
            filtered_p['paid'] = False
            filtered_p['paid_in_full'] = False
            filtered_p['amount_paid'] = None
            filtered_p['unit_approved'] = False
            filtered_p['wing_approved'] = False
            filtered_participants.append(filtered_p)
        return [ParticipantResponse(**p) for p in filtered_participants]
    
    return [ParticipantResponse(**p) for p in participants]


@api_router.get("/participants/by-flight")
async def get_participants_by_flight(user: dict = Depends(get_current_user)):
    """Get participants grouped by flight for easy identification"""
    query = {"is_removed": {"$ne": True}}
    
    _apply_visibility_filter(query, user)
    
    participants = await db.participants.find(
        query,
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "rank": 1,
         "capid": 1, "flight": 1, "squadron": 1, "participant_type": 1,
         "gender": 1, "age": 1, "wing": 1, "unit": 1,
         "email": 1, "phone": 1, "cell_phone": 1,
         "cadet_parent_email": 1, "cadet_parent_phone": 1, "cadet_parent_name": 1,
         "member_type": 1, "photo_path": 1}
    ).to_list(1000)
    
    flights_map = {}
    unassigned = []
    
    for p in participants:
        flight = (p.get("flight") or "").lower()
        entry = {
            "id": p.get("id"),
            "name": f"{p.get('rank', '')} {p.get('last_name', '')}, {p.get('first_name', '')}".strip(", "),
            "first_name": p.get("first_name", ""),
            "last_name": p.get("last_name", ""),
            "rank": p.get("rank", ""),
            "capid": p.get("capid", ""),
            "flight": flight,
            "squadron": p.get("squadron", ""),
            "participant_type": p.get("participant_type", ""),
            "gender": p.get("gender", ""),
            "age": p.get("age"),
            "wing": p.get("wing", ""),
            "unit": p.get("unit", ""),
            "email": p.get("email", ""),
            "phone": p.get("phone", "") or p.get("cell_phone", ""),
            "parent_email": p.get("cadet_parent_email", ""),
            "parent_phone": p.get("cadet_parent_phone", ""),
            "parent_name": p.get("cadet_parent_name", ""),
            "photo_path": p.get("photo_path", ""),
        }
        
        if not flight:
            unassigned.append(entry)
        else:
            if flight not in flights_map:
                flights_map[flight] = []
            flights_map[flight].append(entry)
    
    flight_order = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
    result = []
    for f in flight_order:
        if f in flights_map:
            members = sorted(flights_map[f], key=lambda x: x["last_name"])
            result.append({
                "flight": f,
                "flight_label": f.capitalize(),
                "count": len(members),
                "members": members
            })
    
    for f in sorted(flights_map.keys()):
        if f not in flight_order:
            members = sorted(flights_map[f], key=lambda x: x["last_name"])
            result.append({
                "flight": f,
                "flight_label": f.capitalize() if f else "Unknown",
                "count": len(members),
                "members": members
            })
    
    if unassigned:
        result.append({
            "flight": "unassigned",
            "flight_label": "Unassigned",
            "count": len(unassigned),
            "members": sorted(unassigned, key=lambda x: x["last_name"])
        })
    
    return result


@api_router.get("/participants/stats")
async def get_participant_stats(user: dict = Depends(get_current_user)):
    """Get participant statistics for dashboard"""
    participants = await db.participants.find({"is_removed": {"$ne": True}}, {"_id": 0}).to_list(1000)
    
    stats = {
        'total': len(participants),
        'seniors': 0,
        'cadets': 0,
        'staff': 0,
        'cadre': 0,
        'students': 0,
        'paid': 0,
        'unpaid': 0,
        'total_collected': 0.0,
        'unit_approved': 0,
        'wing_approved': 0,
        'slotted': 0,
        'by_wing': {},
        'by_unit': {}
    }
    
    for p in participants:
        # Member type counts
        member_type = (p.get('member_type') or '').upper()
        if member_type == 'SENIOR':
            stats['seniors'] += 1
        elif member_type == 'CADET':
            stats['cadets'] += 1
        
        # Role counts
        ptype = p.get('participant_type', '')
        if ptype == 'staff':
            stats['staff'] += 1
        elif ptype == 'cadre':
            stats['cadre'] += 1
        elif ptype in ['basic_student', 'advanced_student']:
            stats['students'] += 1
        
        # Payment
        if p.get('paid') or p.get('paid_in_full'):
            stats['paid'] += 1
        else:
            stats['unpaid'] += 1
        
        if p.get('amount_paid'):
            stats['total_collected'] += float(p.get('amount_paid', 0))
        
        # Approvals
        if p.get('unit_approved'):
            stats['unit_approved'] += 1
        if p.get('wing_approved'):
            stats['wing_approved'] += 1
        if p.get('slotted'):
            stats['slotted'] += 1
        
        # By wing
        wing = p.get('wing', 'Unknown')
        if wing:
            stats['by_wing'][wing] = stats['by_wing'].get(wing, 0) + 1
        
        # By unit
        unit = p.get('unit', 'Unknown')
        if unit:
            stats['by_unit'][unit] = stats['by_unit'].get(unit, 0) + 1
    
    return stats


@api_router.get("/participants/analytics/detailed")
async def get_detailed_analytics(user: dict = Depends(get_current_user)):
    """Get comprehensive analytics for encampment attendees"""
    participants = await db.participants.find({"is_removed": {"$ne": True}}, {"_id": 0}).to_list(1000)
    
    # Return empty analytics structure when no participants
    if not participants:
        return {
            'total_count': 0,
            'by_role': {
                'seniors': {'count': 0, 'male': 0, 'female': 0, 'male_pct': 0, 'female_pct': 0, 'avg_age': None},
                'staff': {'count': 0, 'male': 0, 'female': 0, 'male_pct': 0, 'female_pct': 0, 'avg_age': None},
                'cadre': {'count': 0, 'male': 0, 'female': 0, 'male_pct': 0, 'female_pct': 0, 'avg_age': None},
                'students': {'count': 0, 'male': 0, 'female': 0, 'male_pct': 0, 'female_pct': 0, 'avg_age': None},
            },
            'by_rank': {},
            'by_wing': {},
            'by_region': {},
            'by_gender': {'M': 0, 'F': 0, 'Unknown': 0},
            'by_group': {},
            'by_squadron': {},
            'by_flight': {},
            'age_stats': {
                'total': {'avg': None, 'min': None, 'max': None},
                'by_squadron': {},
                'by_flight': {}
            },
            'pending_payments': [],
        }
    
    # Initialize analytics structure
    analytics = {
        'total_count': len(participants),
        'by_role': {
            'seniors': {'count': 0, 'male': 0, 'female': 0, 'ages': []},
            'staff': {'count': 0, 'male': 0, 'female': 0, 'ages': []},
            'cadre': {'count': 0, 'male': 0, 'female': 0, 'ages': []},
            'students': {'count': 0, 'male': 0, 'female': 0, 'ages': []},
        },
        'by_rank': {},
        'by_wing': {},
        'by_region': {},
        'by_gender': {'M': 0, 'F': 0, 'Unknown': 0},
        'by_group': {},  # TN Groups
        'by_squadron': {},
        'by_flight': {},
        'age_stats': {
            'total': {'ages': [], 'avg': 0, 'min': 0, 'max': 0},  # Cadets only (students + cadre)
            'cadets_only': {'ages': []},  # Track cadet ages separately
            'by_squadron': {},
            'by_flight': {}
        },
        'pending_payments': [],
    }
    
    for p in participants:
        member_type = (p.get('member_type') or '').upper()
        ptype = p.get('participant_type', '')
        raw_gender = (p.get('gender') or 'Unknown').upper()
        # Normalize gender values (handle MALE/FEMALE or M/F)
        if raw_gender in ['M', 'MALE']:
            gender = 'M'
        elif raw_gender in ['F', 'FEMALE']:
            gender = 'F'
        else:
            gender = 'Unknown'
        age = p.get('age') or p.get('age_at_event')
        rank = p.get('rank', 'Unknown')
        wing = p.get('wing', 'Unknown')
        region = p.get('region', 'Unknown')
        unit = p.get('unit', '')
        squadron = p.get('squadron', 'Unassigned')
        flight = p.get('flight', 'Unassigned')
        
        # Gender counts
        analytics['by_gender'][gender] = analytics['by_gender'].get(gender, 0) + 1
        
        # Rank distribution
        if rank:
            analytics['by_rank'][rank] = analytics['by_rank'].get(rank, 0) + 1
        
        # Wing distribution
        if wing:
            analytics['by_wing'][wing] = analytics['by_wing'].get(wing, 0) + 1
        
        # Region distribution
        if region:
            analytics['by_region'][region] = analytics['by_region'].get(region, 0) + 1
        
        # TN Group extraction (for TN wing members)
        if wing == 'TN' and unit:
            # CAP unit format: Group/Squadron or just number
            # Try to extract group from unit
            group = 'Unknown'
            try:
                unit_num = int(str(unit).split('/')[0].strip())
                if unit_num < 100:
                    group = f"Group {unit_num}"
                elif unit_num < 200:
                    group = "Group 1"
                elif unit_num < 300:
                    group = "Group 2"
                elif unit_num < 400:
                    group = "Group 3"
                elif unit_num < 500:
                    group = "Group 4"
                else:
                    group = "Other"
            except (ValueError, IndexError):
                group = "Unknown"
            analytics['by_group'][group] = analytics['by_group'].get(group, 0) + 1
        
        # Role-based counts with gender and age
        if member_type == 'SENIOR':
            analytics['by_role']['seniors']['count'] += 1
            if gender == 'M':
                analytics['by_role']['seniors']['male'] += 1
            elif gender == 'F':
                analytics['by_role']['seniors']['female'] += 1
            if age:
                analytics['by_role']['seniors']['ages'].append(age)
            
            if ptype == 'staff':
                analytics['by_role']['staff']['count'] += 1
                if gender == 'M':
                    analytics['by_role']['staff']['male'] += 1
                elif gender == 'F':
                    analytics['by_role']['staff']['female'] += 1
                if age:
                    analytics['by_role']['staff']['ages'].append(age)
        else:
            if ptype == 'cadre':
                analytics['by_role']['cadre']['count'] += 1
                if gender == 'M':
                    analytics['by_role']['cadre']['male'] += 1
                elif gender == 'F':
                    analytics['by_role']['cadre']['female'] += 1
                if age:
                    analytics['by_role']['cadre']['ages'].append(age)
            else:
                analytics['by_role']['students']['count'] += 1
                if gender == 'M':
                    analytics['by_role']['students']['male'] += 1
                elif gender == 'F':
                    analytics['by_role']['students']['female'] += 1
                if age:
                    analytics['by_role']['students']['ages'].append(age)
        
        # Age tracking for averages - CADETS ONLY (exclude senior members)
        if age:
            # Only include cadets (not senior members) in ALL age stats
            is_cadet = member_type != 'SENIOR'
            if is_cadet:
                analytics['age_stats']['total']['ages'].append(age)
                
                # Squadron age averages - cadets only
                if squadron and squadron != 'Unassigned':
                    if squadron not in analytics['age_stats']['by_squadron']:
                        analytics['age_stats']['by_squadron'][squadron] = []
                    analytics['age_stats']['by_squadron'][squadron].append(age)
                
                # Flight age averages - cadets only
                if flight and flight != 'Unassigned':
                    if flight not in analytics['age_stats']['by_flight']:
                        analytics['age_stats']['by_flight'][flight] = []
                    analytics['age_stats']['by_flight'][flight].append(age)
        
        # Squadron/Flight distribution
        if squadron:
            analytics['by_squadron'][squadron] = analytics['by_squadron'].get(squadron, 0) + 1
        if flight:
            analytics['by_flight'][flight] = analytics['by_flight'].get(flight, 0) + 1
        
        # Pending payments
        is_paid = p.get('paid') or p.get('paid_in_full')
        if not is_paid:
            analytics['pending_payments'].append({
                'capid': p.get('capid'),
                'name': f"{p.get('last_name', '')}, {p.get('first_name', '')}",
                'rank': rank,
                'unit': unit,
                'wing': wing,
                'type': ptype,
                'email': p.get('email'),
                'phone': p.get('phone') or p.get('cell_phone'),
                'parent_email': p.get('cadet_parent_email'),
                'parent_phone': p.get('cadet_parent_phone'),
                'amount_paid': p.get('amount_paid', 0)
            })
    
    # Calculate percentages for gender by role
    for role in ['staff', 'cadre', 'students']:
        total = analytics['by_role'][role]['count']
        if total > 0:
            analytics['by_role'][role]['male_pct'] = round(analytics['by_role'][role]['male'] / total * 100, 1)
            analytics['by_role'][role]['female_pct'] = round(analytics['by_role'][role]['female'] / total * 100, 1)
            # Average age
            ages = analytics['by_role'][role]['ages']
            if ages:
                analytics['by_role'][role]['avg_age'] = round(sum(ages) / len(ages), 1)
        else:
            analytics['by_role'][role]['male_pct'] = 0
            analytics['by_role'][role]['female_pct'] = 0
            analytics['by_role'][role]['avg_age'] = 0
        # Remove raw ages list from response
        del analytics['by_role'][role]['ages']
    
    # Also calculate gender stats for seniors (but NOT age stats)
    if analytics['by_role']['seniors']['count'] > 0:
        total = analytics['by_role']['seniors']['count']
        analytics['by_role']['seniors']['male_pct'] = round(analytics['by_role']['seniors']['male'] / total * 100, 1)
        analytics['by_role']['seniors']['female_pct'] = round(analytics['by_role']['seniors']['female'] / total * 100, 1)
    # Remove seniors ages - we don't track/display senior age stats
    del analytics['by_role']['seniors']['ages']
    
    # Calculate age statistics - CADETS ONLY
    cadet_ages = analytics['age_stats']['total']['ages']
    if cadet_ages:
        analytics['age_stats']['total']['avg'] = round(sum(cadet_ages) / len(cadet_ages), 1)
        analytics['age_stats']['total']['min'] = min(cadet_ages)
        analytics['age_stats']['total']['max'] = max(cadet_ages)
        analytics['age_stats']['total']['count'] = len(cadet_ages)
    del analytics['age_stats']['total']['ages']
    # Remove the temp tracking field if it exists
    if 'cadets_only' in analytics['age_stats']:
        del analytics['age_stats']['cadets_only']
    
    # Squadron averages
    for sq, ages in analytics['age_stats']['by_squadron'].items():
        if ages:
            analytics['age_stats']['by_squadron'][sq] = round(sum(ages) / len(ages), 1)
    
    # Flight averages
    for fl, ages in analytics['age_stats']['by_flight'].items():
        if ages:
            analytics['age_stats']['by_flight'][fl] = round(sum(ages) / len(ages), 1)
    
    return analytics


@api_router.get("/participants/pending-payments")
async def get_pending_payments(user: dict = Depends(get_current_user)):
    """Get list of participants with pending payments for follow-up"""
    participants = await db.participants.find(
        {"is_removed": {"$ne": True}, "$or": [{"paid": False}, {"paid": None}, {"paid_in_full": False}, {"paid_in_full": None}]},
        {"_id": 0}
    ).to_list(1000)
    
    # Filter to only truly unpaid
    unpaid = []
    for p in participants:
        if not p.get('paid') and not p.get('paid_in_full'):
            unpaid.append({
                'capid': p.get('capid'),
                'name': f"{p.get('last_name', '')}, {p.get('first_name', '')}",
                'rank': p.get('rank'),
                'unit': p.get('unit'),
                'wing': p.get('wing'),
                'participant_type': p.get('participant_type'),
                'member_type': p.get('member_type'),
                'email': p.get('email'),
                'phone': p.get('phone') or p.get('cell_phone'),
                'parent_email': p.get('cadet_parent_email'),
                'parent_phone': p.get('cadet_parent_phone'),
                'unit_cc_email': p.get('unit_cc_email'),
                'amount_paid': p.get('amount_paid', 0),
                'registration_status': p.get('registration_status')
            })
    
    return {
        'count': len(unpaid),
        'participants': unpaid
    }


@api_router.get("/participants/analytics/export")
async def export_analytics(
    format: str = "csv",
    user: dict = Depends(get_current_user)
):
    """Export analytics data as CSV or Excel"""
    participants = await db.participants.find({"is_removed": {"$ne": True}}, {"_id": 0}).to_list(1000)
    
    if not participants:
        raise HTTPException(status_code=404, detail="No participants found")
    
    # Create DataFrame with participant data
    df = pd.DataFrame(participants)
    
    # Select and reorder columns for export
    export_columns = [
        'capid', 'rank', 'last_name', 'first_name', 'unit', 'wing', 'region',
        'gender', 'age', 'age_at_event', 'member_type', 'participant_type',
        'squadron', 'flight', 'position', 'shirt_size', 'email', 'phone', 'cell_phone',
        'paid', 'paid_in_full', 'amount_paid', 'registration_status',
        'unit_approved', 'wing_approved', 'slotted'
    ]
    
    # Only include columns that exist
    available_columns = [col for col in export_columns if col in df.columns]
    df_export = df[available_columns]
    
    # Generate file
    output = BytesIO()
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    
    if format == "excel":
        df_export.to_excel(output, index=False, sheet_name='Participants')
        output.seek(0)
        filename = f"cap_encampment_analytics_{timestamp}.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        df_export.to_csv(output, index=False)
        output.seek(0)
        filename = f"cap_encampment_analytics_{timestamp}.csv"
        media_type = "text/csv"
    
    return StreamingResponse(
        output,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@api_router.get("/participants/analytics/summary-export")
async def export_analytics_summary(
    user: dict = Depends(get_current_user)
):
    """Export analytics summary report as Excel with multiple sheets"""
    participants = await db.participants.find({"is_removed": {"$ne": True}}, {"_id": 0}).to_list(1000)
    
    if not participants:
        raise HTTPException(status_code=404, detail="No participants found")
    
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Full participant list
        df_full = pd.DataFrame(participants)
        export_columns = [
            'capid', 'rank', 'last_name', 'first_name', 'unit', 'wing', 'region',
            'gender', 'age', 'member_type', 'participant_type', 'squadron', 'flight',
            'paid', 'amount_paid'
        ]
        available_columns = [col for col in export_columns if col in df_full.columns]
        df_full[available_columns].to_excel(writer, sheet_name='All Participants', index=False)
        
        # Sheet 2: Summary by Role
        role_summary = []
        for p in participants:
            member_type = (p.get('member_type') or '').upper()
            ptype = p.get('participant_type', '')
            gender = (p.get('gender') or 'Unknown').upper()
            age = p.get('age') or p.get('age_at_event')
            
            role = 'Unknown'
            if member_type == 'SENIOR':
                role = 'Senior/Staff'
            elif ptype == 'cadre':
                role = 'Cadre'
            else:
                role = 'Student'
            
            role_summary.append({
                'Role': role,
                'Gender': gender,
                'Age': age,
                'Paid': 'Yes' if p.get('paid') or p.get('paid_in_full') else 'No'
            })
        
        df_roles = pd.DataFrame(role_summary)
        role_counts = df_roles.groupby('Role').agg({
            'Gender': 'count',
            'Age': 'mean'
        }).reset_index()
        role_counts.columns = ['Role', 'Count', 'Average Age']
        role_counts.to_excel(writer, sheet_name='Summary by Role', index=False)
        
        # Sheet 3: Summary by Wing
        wing_counts = df_full.groupby('wing').size().reset_index(name='Count')
        wing_counts.to_excel(writer, sheet_name='By Wing', index=False)
        
        # Sheet 4: Summary by Unit
        if 'unit' in df_full.columns:
            unit_counts = df_full.groupby('unit').size().reset_index(name='Count')
            unit_counts.to_excel(writer, sheet_name='By Unit', index=False)
        
        # Sheet 5: Pending Payments
        unpaid = [p for p in participants if not p.get('paid') and not p.get('paid_in_full')]
        if unpaid:
            df_unpaid = pd.DataFrame(unpaid)
            unpaid_columns = ['capid', 'rank', 'last_name', 'first_name', 'unit', 'wing', 
                            'email', 'phone', 'cadet_parent_email', 'cadet_parent_phone']
            available_unpaid = [col for col in unpaid_columns if col in df_unpaid.columns]
            df_unpaid[available_unpaid].to_excel(writer, sheet_name='Pending Payments', index=False)
    
    output.seek(0)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    filename = f"cap_encampment_full_report_{timestamp}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@api_router.get("/participants/export-pdf")
async def export_roster_pdf(
    format: str = "simple",
    user: dict = Depends(get_current_user)
):
    """Export roster as PDF. format: simple, by_flight, by_type"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    from collections import Counter

    participants = await db.participants.find({"is_removed": {"$ne": True}}, {"_id": 0}).to_list(1000)
    if not participants:
        raise HTTPException(status_code=404, detail="No participants found")

    output = BytesIO()
    timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    doc = SimpleDocTemplate(output, pagesize=landscape(letter), topMargin=0.5*inch, bottomMargin=0.5*inch, leftMargin=0.5*inch, rightMargin=0.5*inch)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleCustom', parent=styles['Title'], fontSize=18, textColor=colors.HexColor('#00205B'), spaceAfter=6)
    subtitle_style = ParagraphStyle('SubtitleCustom', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#475569'), spaceAfter=12)
    section_style = ParagraphStyle('SectionCustom', parent=styles['Heading2'], fontSize=13, textColor=colors.HexColor('#00205B'), spaceBefore=16, spaceAfter=6)
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=7, leading=9)
    header_cell_style = ParagraphStyle('HeaderCell', parent=styles['Normal'], fontSize=7, leading=9, textColor=colors.white)

    CAP_BLUE = colors.HexColor('#00205B')
    CAP_RED = colors.HexColor('#BF0D3E')
    LIGHT_GRAY = colors.HexColor('#F1F5F9')
    BORDER_GRAY = colors.HexColor('#CBD5E1')

    elements = []

    # ─── Title ───
    elements.append(Paragraph("Tennessee Wing CAP Encampment — Roster Report", title_style))
    gen_date = datetime.now(timezone.utc).strftime('%B %d, %Y at %H:%M UTC')
    format_labels = {"simple": "Complete Roster", "by_flight": "Roster by Flight", "by_type": "Roster by Type"}
    elements.append(Paragraph(f"Format: {format_labels.get(format, format)} &bull; Generated: {gen_date}", subtitle_style))

    # ─── Summary Stats ───
    total = len(participants)
    students = [p for p in participants if p.get('participant_type') in ['basic_student', 'student']]
    cadre = [p for p in participants if p.get('participant_type') in ['cadre', 'exec_cadre']]
    staff = [p for p in participants if p.get('participant_type') == 'staff']
    paid = sum(1 for p in participants if p.get('paid') or p.get('paid_in_full'))
    males = sum(1 for p in participants if (p.get('gender') or '').upper() in ['M', 'MALE'])
    females = sum(1 for p in participants if (p.get('gender') or '').upper() in ['F', 'FEMALE'])

    flights = Counter(p.get('flight', 'Unassigned') or 'Unassigned' for p in participants if p.get('participant_type') in ['basic_student', 'student', 'cadre', 'exec_cadre'])
    wings = Counter(p.get('wing', 'Unknown') or 'Unknown' for p in participants)
    units = Counter(p.get('unit', 'Unknown') or 'Unknown' for p in participants)

    stats_data = [
        [Paragraph('<b>Total Participants</b>', cell_style), Paragraph(str(total), cell_style),
         Paragraph('<b>Students</b>', cell_style), Paragraph(str(len(students)), cell_style),
         Paragraph('<b>Cadre</b>', cell_style), Paragraph(str(len(cadre)), cell_style),
         Paragraph('<b>Staff</b>', cell_style), Paragraph(str(len(staff)), cell_style)],
        [Paragraph('<b>Paid</b>', cell_style), Paragraph(f"{paid}/{total}", cell_style),
         Paragraph('<b>Unpaid</b>', cell_style), Paragraph(str(total - paid), cell_style),
         Paragraph('<b>Male</b>', cell_style), Paragraph(str(males), cell_style),
         Paragraph('<b>Female</b>', cell_style), Paragraph(str(females), cell_style)],
    ]
    stats_table = Table(stats_data, colWidths=[1.1*inch, 0.6*inch]*4)
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, BORDER_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 8))

    # Flight distribution row
    flight_items = sorted(flights.items(), key=lambda x: x[0])
    if flight_items:
        flight_str = " &bull; ".join([f"<b>{f}</b>: {c}" for f, c in flight_items])
        elements.append(Paragraph(f"<b>Flights:</b> {flight_str}", ParagraphStyle('FlightStats', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#475569'))))
        elements.append(Spacer(1, 4))

    # Wing distribution row
    wing_items = sorted(wings.items(), key=lambda x: -x[1])[:8]
    if wing_items:
        wing_str = " &bull; ".join([f"<b>{w}</b>: {c}" for w, c in wing_items])
        elements.append(Paragraph(f"<b>Wings:</b> {wing_str}", ParagraphStyle('WingStats', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#475569'))))
        elements.append(Spacer(1, 4))

    # Unit count
    elements.append(Paragraph(f"<b>Units Represented:</b> {len(units)}", ParagraphStyle('UnitStats', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#475569'))))
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY))
    elements.append(Spacer(1, 8))

    def build_table(data_rows, title=None):
        """Build a styled participant table"""
        if title:
            elements.append(Paragraph(title, section_style))

        headers = ['#', 'CAPID', 'Rank', 'Last Name', 'First Name', 'Type', 'Flight', 'Unit', 'Wing', 'Gender', 'Age', 'Phone', 'Email', 'Paid']
        header_row = [Paragraph(f'<b>{h}</b>', header_cell_style) for h in headers]
        table_data = [header_row]

        for idx, p in enumerate(data_rows, 1):
            paid_status = 'Yes' if p.get('paid') or p.get('paid_in_full') else 'No'
            ptype = p.get('participant_type', '')
            if ptype in ['basic_student', 'student']:
                ptype_label = 'Student'
            elif ptype in ['cadre', 'exec_cadre']:
                ptype_label = 'Cadre'
            elif ptype == 'staff':
                ptype_label = 'Staff'
            else:
                ptype_label = ptype.title()

            row = [
                Paragraph(str(idx), cell_style),
                Paragraph(str(p.get('capid', '')), cell_style),
                Paragraph(str(p.get('rank', '')), cell_style),
                Paragraph(str(p.get('last_name', '')), cell_style),
                Paragraph(str(p.get('first_name', '')), cell_style),
                Paragraph(ptype_label, cell_style),
                Paragraph(str(p.get('flight', '') or ''), cell_style),
                Paragraph(str(p.get('unit', '')), cell_style),
                Paragraph(str(p.get('wing', '')), cell_style),
                Paragraph(str(p.get('gender', '')), cell_style),
                Paragraph(str(p.get('age', '') or ''), cell_style),
                Paragraph(str(p.get('cell_phone', '') or p.get('phone', '') or ''), cell_style),
                Paragraph(str(p.get('email', '') or ''), cell_style),
                Paragraph(paid_status, cell_style),
            ]
            table_data.append(row)

        col_widths = [0.3*inch, 0.55*inch, 0.5*inch, 0.9*inch, 0.8*inch, 0.5*inch, 0.55*inch, 0.65*inch, 0.6*inch, 0.45*inch, 0.3*inch, 0.85*inch, 1.4*inch, 0.35*inch]
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), CAP_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
            ('LINEBELOW', (0, 0), (-1, 0), 1, CAP_BLUE),
            ('INNERGRID', (0, 1), (-1, -1), 0.25, BORDER_GRAY),
        ]
        # Zebra stripe
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), LIGHT_GRAY))
        # Highlight unpaid
        for i in range(1, len(table_data)):
            if table_data[i][-1] and hasattr(table_data[i][-1], 'text') and 'No' in str(table_data[i][-1].text if hasattr(table_data[i][-1], 'text') else ''):
                style_cmds.append(('TEXTCOLOR', (-1, i), (-1, i), CAP_RED))

        t.setStyle(TableStyle(style_cmds))
        elements.append(t)
        elements.append(Spacer(1, 12))

    sorted_participants = sorted(participants, key=lambda p: (p.get('last_name', ''), p.get('first_name', '')))

    if format == "simple":
        build_table(sorted_participants, "Complete Roster")

    elif format == "by_flight":
        flight_groups = {}
        for p in sorted_participants:
            flight = p.get('flight', '') or 'Unassigned'
            flight_groups.setdefault(flight, []).append(p)
        for flight_name in sorted(flight_groups.keys()):
            members = flight_groups[flight_name]
            build_table(members, f"Flight: {flight_name} ({len(members)} members)")

    elif format == "by_type":
        for ptype, label in [('staff', 'Staff (Senior Members)'), ('cadre', 'Cadre'), ('basic_student', 'Basic Students')]:
            if ptype == 'cadre':
                group = [p for p in sorted_participants if p.get('participant_type') in ['cadre', 'exec_cadre']]
            elif ptype == 'basic_student':
                group = [p for p in sorted_participants if p.get('participant_type') in ['basic_student', 'student']]
            else:
                group = [p for p in sorted_participants if p.get('participant_type') == ptype]
            if group:
                build_table(group, f"{label} ({len(group)})")

    doc.build(elements)
    output.seek(0)
    filename = f"cap_roster_{format}_{timestamp_str}.pdf"
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@api_router.get("/participants/{participant_id}", response_model=ParticipantResponse)
async def get_participant(participant_id: str, user: dict = Depends(get_current_user)):
    participant = await db.participants.find_one({"id": participant_id}, {"_id": 0})
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Define roles that can see all data
    privileged_roles = [
        UserRole.COMMANDER,
        UserRole.EXECUTIVE_STAFF,
        UserRole.EXEC_CADRE,
        UserRole.PLANS_PROGRAMS,
        UserRole.FINANCE,
        UserRole.STAFF
    ]
    
    user_role = user.get('role')
    
    # If user doesn't have a privileged role, filter sensitive fields
    if user_role not in privileged_roles:
        sensitive_fields = [
            'email', 'phone', 'cell_phone', 'address', 'city', 'state', 'zip_code',
            'emergency_contact', 'emergency_phone', 'cadet_parent_name', 
            'cadet_parent_phone', 'cadet_parent_email', 'amount_paid',
            'registration_status', 'notes', 'comments', 'religious_preference',
            'shirt_size', 'unit_cc_name', 'unit_cc_email'
        ]
        filtered_p = dict(participant)
        for field in sensitive_fields:
            if field in filtered_p:
                filtered_p[field] = None
        # Hide payment/approval info
        filtered_p['paid'] = False
        filtered_p['paid_in_full'] = False
        filtered_p['amount_paid'] = None
        filtered_p['unit_approved'] = False
        filtered_p['wing_approved'] = False
        return ParticipantResponse(**filtered_p)
    
    return ParticipantResponse(**participant)

@api_router.post("/participants", response_model=ParticipantResponse)
async def create_participant(
    data: ParticipantCreate,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    participant_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    doc = {
        "id": participant_id,
        **data.model_dump(),
        "created_at": now,
        "updated_at": now
    }
    
    # AUTO-ASSIGNMENT: If this is a student without a flight, auto-assign
    doc = await auto_assign_single_student(doc)
    
    await db.participants.insert_one(doc)
    doc.pop("_id", None)
    return ParticipantResponse(**doc)


# ================= BULK OPERATIONS (registered BEFORE /{participant_id} routes) =================

class BulkTypeChangeRequest(BaseModel):
    participant_ids: List[str]
    new_type: str  # basic_student, cadre, staff, senior_member


class BulkDeleteRequest(BaseModel):
    participant_ids: List[str]
    confirm: bool = False


class BulkAssignmentRequest(BaseModel):
    participant_ids: List[str]
    flight: Optional[str] = None    # 'alpha'..'foxtrot' or 'None' or '' to clear
    squadron: Optional[str] = None  # '6th_cts' / '21st_cts' / '22nd_cts' or 'None' or '' to clear


VALID_FLIGHTS = {"alpha", "bravo", "charlie", "delta", "echo", "foxtrot"}
VALID_SQUADRONS = {"6th_cts", "21st_cts", "22nd_cts"}


@api_router.put("/participants/bulk-assignment")
async def bulk_change_assignment(
    data: BulkAssignmentRequest,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    """Bulk update flight and/or squadron for multiple participants.
    Pass empty string or 'None' to clear an assignment. Omit a field to leave it unchanged."""
    if not data.participant_ids:
        raise HTTPException(status_code=400, detail="No participants selected")

    update_doc = {}

    # Flight
    if data.flight is not None:
        f = (data.flight or "").strip()
        if f == "" or f.lower() == "none":
            update_doc["flight"] = None
        elif f.lower() in VALID_FLIGHTS:
            # Store capitalized for UI ("Alpha")
            update_doc["flight"] = f.capitalize()
        else:
            raise HTTPException(status_code=400, detail=f"flight must be one of: {sorted(VALID_FLIGHTS)} or empty/None")

    # Squadron
    if data.squadron is not None:
        s = (data.squadron or "").strip()
        if s == "" or s.lower() == "none":
            update_doc["squadron"] = None
        elif s in VALID_SQUADRONS:
            update_doc["squadron"] = s
        else:
            raise HTTPException(status_code=400, detail=f"squadron must be one of: {sorted(VALID_SQUADRONS)} or empty/None")

    if not update_doc:
        raise HTTPException(status_code=400, detail="At least one of flight or squadron must be provided")

    update_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.participants.update_many(
        {"id": {"$in": data.participant_ids}},
        {"$set": update_doc},
    )

    parts = []
    if "flight" in update_doc:
        parts.append(f"flight={update_doc['flight'] or 'None'}")
    if "squadron" in update_doc:
        parts.append(f"squadron={update_doc['squadron'] or 'None'}")
    return {
        "message": f"Updated {result.modified_count} participants ({', '.join(parts)})",
        "modified": result.modified_count,
        "flight": update_doc.get("flight"),
        "squadron": update_doc.get("squadron"),
    }


@api_router.put("/participants/bulk-type")
async def bulk_change_type(
    data: BulkTypeChangeRequest,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    """Bulk change participant_type for multiple participants"""
    valid_types = {"basic_student", "cadre", "staff", "senior_member"}
    if data.new_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"new_type must be one of: {sorted(valid_types)}")
    if not data.participant_ids:
        raise HTTPException(status_code=400, detail="No participants selected")

    now = datetime.now(timezone.utc).isoformat()
    result = await db.participants.update_many(
        {"id": {"$in": data.participant_ids}},
        {"$set": {
            "participant_type": data.new_type,
            "student_type": "First-Time Student" if data.new_type == "basic_student" else None,
            "updated_at": now,
        }}
    )
    return {
        "message": f"Changed {result.modified_count} participants to {data.new_type}",
        "modified": result.modified_count,
        "new_type": data.new_type,
    }


@api_router.post("/participants/bulk-delete")
async def bulk_delete_participants(
    data: BulkDeleteRequest,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
):
    """Permanently delete selected participants"""
    if not data.confirm:
        raise HTTPException(status_code=400, detail="Must set confirm=true")
    if not data.participant_ids:
        raise HTTPException(status_code=400, detail="No participants selected")

    now = datetime.now(timezone.utc).isoformat()

    # Unlink user accounts
    await db.users.update_many(
        {"linked_participant_id": {"$in": data.participant_ids}},
        {"$set": {"linked_participant_id": None, "updated_at": now}}
    )

    # Delete related data
    await db.hs_med_diary.delete_many({"participant_id": {"$in": data.participant_ids}})
    await db.hs_supplements.delete_many({"participant_id": {"$in": data.participant_ids}})
    await db.contraband.delete_many({"participant_id": {"$in": data.participant_ids}})

    # Delete the participants
    result = await db.participants.delete_many({"id": {"$in": data.participant_ids}})

    return {
        "message": f"Deleted {result.deleted_count} participants",
        "deleted": result.deleted_count,
    }


@api_router.put("/participants/{participant_id}", response_model=ParticipantResponse)
async def update_participant(
    participant_id: str,
    data: ParticipantCreate,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    now = datetime.now(timezone.utc).isoformat()
    update_data = {**data.model_dump(), "updated_at": now, "manually_edited_at": now, "manually_edited_by": user["id"]}
    
    # First get the existing participant to check current flight
    existing = await db.participants.find_one({"id": participant_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    # Merge update data with participant_id for auto-assignment check
    merged_doc = {**existing, **update_data, "id": participant_id}
    
    # AUTO-ASSIGNMENT: If this is a student and flight is being cleared or was never set
    # Only auto-assign if the incoming data doesn't have a valid flight
    incoming_flight = data.flight
    if not is_valid_flight(incoming_flight):
        # Check if participant is a student type
        participant_type = update_data.get("participant_type") or existing.get("participant_type", "")
        if participant_type in ["basic_student", "advanced_student"]:
            merged_doc = await auto_assign_single_student(merged_doc)
            update_data["flight"] = merged_doc.get("flight")
            update_data["squadron"] = merged_doc.get("squadron")
    
    await db.participants.update_one(
        {"id": participant_id},
        {"$set": update_data}
    )
    
    participant = await db.participants.find_one({"id": participant_id}, {"_id": 0})
    return ParticipantResponse(**participant)

@api_router.delete("/participants/{participant_id}")
async def delete_participant(
    participant_id: str,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    result = await db.participants.delete_one({"id": participant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Participant not found")
    return {"message": "Participant deleted successfully"}


class ParticipantAssignmentUpdate(BaseModel):
    """Model for updating participant flight/squadron assignment"""
    flight: Optional[str] = None
    squadron: Optional[str] = None
    position: Optional[str] = None


@api_router.put("/participants/{participant_id}/assignment")
async def update_participant_assignment(
    participant_id: str,
    assignment: ParticipantAssignmentUpdate,
    user: dict = Depends(get_current_user)
):
    """
    Update participant flight/squadron/position assignment with role-based restrictions:
    - Exec Cadre: Can ONLY assign Cadre to roles (not students)
    - Plans & Programs, Executive Staff, Commander, DCP: Can assign BOTH students and cadre
    """
    # Get the participant to check their type
    participant = await db.participants.find_one({"id": participant_id}, {"_id": 0})
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    user_role = user.get("role")
    participant_type = participant.get("participant_type", "")
    
    # Define roles that can edit ALL participant types (students + cadre)
    full_access_roles = [
        UserRole.DCP,
        UserRole.COMMANDER,
        UserRole.EXECUTIVE_STAFF,
        UserRole.PLANS_PROGRAMS,
        UserRole.STAFF
    ]
    
    # Define roles that can ONLY edit cadre
    cadre_only_roles = [UserRole.EXEC_CADRE]
    
    # Check permissions
    is_student = participant_type in ["basic_student", "advanced_student"]
    
    if user_role in full_access_roles:
        # Full access - can edit both students and cadre
        pass
    elif user_role in cadre_only_roles:
        # Exec Cadre can ONLY edit cadre assignments
        if is_student:
            raise HTTPException(
                status_code=403,
                detail="Exec Cadre can only assign Cadre members, not students. Contact Plans & Programs or Executive Staff for student assignments."
            )
    else:
        # No permission to edit assignments
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to modify participant assignments"
        )
    
    # Validate flight/squadron combinations
    valid_flights = [None, "", "alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
    valid_squadrons = [None, "", "staff", "support_cadre", "exec_cadre", "ops_cadre", "6th_cts", "21st_cts", "22nd_cts"]
    
    if assignment.flight and assignment.flight.lower() not in [f.lower() if f else f for f in valid_flights]:
        raise HTTPException(status_code=400, detail=f"Invalid flight: {assignment.flight}")
    
    if assignment.squadron and assignment.squadron.lower() not in [s.lower() if s else s for s in valid_squadrons]:
        raise HTTPException(status_code=400, detail=f"Invalid squadron: {assignment.squadron}")
    
    # Auto-set squadron based on flight if flight is provided
    flight_squadron_map = {
        "alpha": "6th_cts", "bravo": "6th_cts",
        "charlie": "21st_cts", "delta": "21st_cts",
        "echo": "22nd_cts", "foxtrot": "22nd_cts"
    }
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if assignment.flight is not None:
        flight_lower = assignment.flight.lower() if assignment.flight else None
        update_data["flight"] = flight_lower
        
        # Auto-assign squadron for student flights
        if flight_lower and flight_lower in flight_squadron_map:
            update_data["squadron"] = flight_squadron_map[flight_lower]
    
    if assignment.squadron is not None:
        update_data["squadron"] = assignment.squadron.lower() if assignment.squadron else None
    
    if assignment.position is not None:
        update_data["position"] = assignment.position
    
    await db.participants.update_one(
        {"id": participant_id},
        {"$set": update_data}
    )
    
    updated = await db.participants.find_one({"id": participant_id}, {"_id": 0})
    return ParticipantResponse(**updated)


@api_router.post("/participants/{participant_id}/remove")
async def remove_participant_from_encampment(
    participant_id: str,
    removal_data: ParticipantRemoval,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF, UserRole.PLANS_PROGRAMS]))
):
    """Mark a participant as removed from encampment (soft delete) with reason"""
    participant = await db.participants.find_one({"id": participant_id})
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.participants.update_one(
        {"id": participant_id},
        {"$set": {
            "is_removed": True,
            "removed_at": now,
            "removed_by": user.get("name", user.get("email")),
            "removal_reason": removal_data.removal_reason,
            "updated_at": now
        }}
    )
    
    updated = await db.participants.find_one({"id": participant_id}, {"_id": 0})
    return {"message": "Participant removed from encampment", "participant": updated}


@api_router.post("/participants/{participant_id}/reinstate")
async def reinstate_participant(
    participant_id: str,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF, UserRole.PLANS_PROGRAMS]))
):
    """Reinstate a previously removed participant"""
    participant = await db.participants.find_one({"id": participant_id})
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.participants.update_one(
        {"id": participant_id},
        {"$set": {
            "is_removed": False,
            "removed_at": None,
            "removed_by": None,
            "removal_reason": None,
            "updated_at": now
        }}
    )
    
    updated = await db.participants.find_one({"id": participant_id}, {"_id": 0})
    return {"message": "Participant reinstated", "participant": updated}


# ================= BULK OPERATIONS (defined earlier, before /{participant_id} routes) =================


# ================= ANNUAL RESET =================

class BulkResetRequest(BaseModel):
    participant_types: List[str]  # e.g. ["cadre", "staff", "basic_student"]
    confirm: bool = False


@api_router.post("/participants/bulk-reset/preview")
async def preview_bulk_reset(
    data: BulkResetRequest,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER]))
):
    """Preview what would be removed in a bulk reset — does NOT delete anything."""
    if not data.participant_types:
        raise HTTPException(status_code=400, detail="No participant types selected")

    query = {
        "participant_type": {"$in": data.participant_types},
        "is_removed": {"$ne": True},
    }
    count = await db.participants.count_documents(query)
    sample = await db.participants.find(query, {
        "_id": 0, "id": 1, "first_name": 1, "last_name": 1, "rank": 1,
        "participant_type": 1, "flight": 1, "position": 1,
    }).sort("last_name", 1).limit(20).to_list(20)

    # Count linked user accounts that would be affected
    participant_ids = [p["id"] for p in await db.participants.find(query, {"_id": 0, "id": 1}).to_list(5000)]
    linked_accounts = await db.users.count_documents({"linked_participant_id": {"$in": participant_ids}}) if participant_ids else 0

    return {
        "total_to_remove": count,
        "linked_accounts": linked_accounts,
        "types": data.participant_types,
        "sample": sample,
    }


@api_router.post("/participants/bulk-reset/execute")
async def execute_bulk_reset(
    data: BulkResetRequest,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER]))
):
    """Execute annual roster reset: permanently deletes all participants of the selected types.
    Also unlinks any user accounts tied to deleted participants.
    Commander or DCP only. Requires confirm=true."""
    if not data.confirm:
        raise HTTPException(status_code=400, detail="Must set confirm=true to execute reset")
    if not data.participant_types:
        raise HTTPException(status_code=400, detail="No participant types selected")

    now = datetime.now(timezone.utc).isoformat()

    query = {
        "participant_type": {"$in": data.participant_types},
    }

    # Collect IDs for unlinking user accounts
    to_delete = await db.participants.find(query, {"_id": 0, "id": 1}).to_list(5000)
    deleted_ids = [p["id"] for p in to_delete]

    # Delete the participants
    result = await db.participants.delete_many(query)

    # Unlink user accounts
    unlinked = 0
    if deleted_ids:
        ul = await db.users.update_many(
            {"linked_participant_id": {"$in": deleted_ids}},
            {"$set": {"linked_participant_id": None, "updated_at": now}}
        )
        unlinked = ul.modified_count

    # Clear related data
    if deleted_ids:
        await db.hs_med_diary.delete_many({"participant_id": {"$in": deleted_ids}})
        await db.hs_supplements.delete_many({"participant_id": {"$in": deleted_ids}})
        await db.contraband.delete_many({"participant_id": {"$in": deleted_ids}})
        await db.check_in_records.delete_many({"participant_id": {"$in": deleted_ids}})

    logger.info(f"Annual reset by {user.get('name')}: deleted {result.deleted_count} participants ({data.participant_types}), unlinked {unlinked} accounts")

    return {
        "message": f"Reset complete: {result.deleted_count} participants removed",
        "deleted": result.deleted_count,
        "unlinked_accounts": unlinked,
        "types": data.participant_types,
    }


@api_router.post("/participants/bulk-reset/clear-all")
async def clear_all_participants(
    data: BulkResetRequest,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER]))
):
    """Nuclear option: delete ALL participants and related data. Commander/DCP only."""
    if not data.confirm:
        raise HTTPException(status_code=400, detail="Must set confirm=true")

    now = datetime.now(timezone.utc).isoformat()
    count = await db.participants.count_documents({})
    await db.participants.delete_many({})
    await db.users.update_many(
        {"linked_participant_id": {"$ne": None}},
        {"$set": {"linked_participant_id": None, "updated_at": now}}
    )
    await db.hs_med_diary.delete_many({})
    await db.hs_supplements.delete_many({})
    await db.contraband.delete_many({})
    await db.check_in_records.delete_many({})
    await db.flight_leadership.delete_many({})

    logger.info(f"Full roster clear by {user.get('name')}: {count} participants deleted")

    return {"message": f"All {count} participants cleared", "deleted": count}


@api_router.post("/org-chart/bulk-reset")
async def reset_org_chart(
    data: BulkResetRequest,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER]))
):
    """Clear all org chart positions (annual reset). Commander/DCP only."""
    if not data.confirm:
        raise HTTPException(status_code=400, detail="Must set confirm=true")

    count = await db.org_chart_roles.count_documents({})
    await db.org_chart_roles.delete_many({})

    logger.info(f"Org chart reset by {user.get('name')}: {count} positions deleted")

    return {"message": f"Org chart cleared: {count} positions removed", "deleted": count}


CAP_IMPORT_COLUMN_MAP = {
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
    'AgeAtEventStart': 'age_at_event',
    'Email': 'email',
    'HomePhonePrimary': 'phone',
    'CellPhonePrimary': 'cell_phone',
    'ShirtSize': 'shirt_size',
    'MbrType': 'member_type',
    'StaffMember': 'staff_member',
    'PaidInFull': 'paid_in_full',
    'AmountPaid': 'amount_paid',
    'RegistrationStatus': 'registration_status',
    'UnitApproved': 'unit_approved',
    'UnitApprovalDate': 'unit_approval_date',
    'WingApproved': 'wing_approved',
    'WingApprovalDate': 'wing_approval_date',
    'Slotted': 'slotted',
    'Addr1': 'address',
    'City': 'city',
    'State': 'state',
    'Zip': 'zip_code',
    'EmergencyContactName': 'emergency_contact',
    'EmergencyContactNumber': 'emergency_phone',
    'CadetParentPhonePrimary': 'cadet_parent_phone',
    'CadetParentEmailPrimary': 'cadet_parent_email',
    'UnitCCName': 'unit_cc_name',
    'UnitCCEmail': 'unit_cc_email',
    'LastEncampment': 'last_encampment',
    'CPPTExpiration': 'cppt_expiration',
    'FirstAid': 'first_aid',
    'IS100': 'is100_date',
    'IS700': 'is700_date',
    'Comments': 'comments',
}


def _parse_import_dataframe(df: pd.DataFrame) -> tuple[list[dict], dict]:
    """Parse a CAP Event Admin Report dataframe into normalized participant docs.
    Returns (rows, stats). Each row has keys:
      capid, doc, participant_type, member_type, paid_in_full, amount_paid
    where doc is the field-only update dict (no id/created_at), and participant_type
    may be None when the SubEvents column was blank (so caller decides whether to skip / default)."""
    df = df.rename(columns=CAP_IMPORT_COLUMN_MAP)

    rows: list[dict] = []
    stats = {
        'seniors': 0, 'cadets': 0, 'staff': 0, 'cadre': 0,
        'paid': 0, 'unpaid': 0, 'total_collected': 0.0,
    }

    for _idx, row in df.iterrows():
        row_dict = row.to_dict()

        def get_val(key, default=None):
            val = row_dict.get(key)
            if pd.isna(val) or val == '' or val == 'nan':
                return default
            return val

        def get_str(key, default=''):
            val = get_val(key, default)
            return str(val).strip() if val is not None else default

        def get_bool(key):
            val = get_val(key)
            if val is None:
                return False
            if isinstance(val, bool):
                return val
            return str(val).lower() in ['yes', 'true', '1']

        def get_float(key, default=0.0):
            val = get_val(key)
            if val is None:
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        def get_int(key, default=None):
            val = get_val(key)
            if val is None:
                return default
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return default

        # CAPID resolution: explicit column → email prefix → name+unit hash
        capid = str(row_dict.get('capid', '')).strip()
        # Strip pandas float artifact: "538026.0" → "538026"
        if capid.endswith('.0') and capid[:-2].isdigit():
            capid = capid[:-2]
        if not capid or capid == 'nan':
            email = get_str('email', '')
            if email:
                email_prefix = email.split('@')[0] if '@' in email else ''
                numeric_parts = ''.join(filter(str.isdigit, email_prefix))
                if len(numeric_parts) >= 5:
                    capid = numeric_parts[:6]
            if not capid or capid == 'nan':
                last_name = get_str('last_name', '')
                first_name = get_str('first_name', '')
                wing = get_str('wing', 'XX')
                unit = get_str('unit', '000')
                if last_name and first_name:
                    import hashlib
                    composite = f"{last_name}_{first_name}_{wing}_{unit}".upper()
                    hash_digest = hashlib.sha256(composite.encode()).hexdigest()[:6]
                    capid = f"GEN{hash_digest.upper()}"
                else:
                    continue  # not enough info to identify

        # Type inference
        member_type = get_str('member_type', '').upper()
        is_staff = get_bool('staff_member')
        event_name = get_str('event_name', '')
        participant_type = determine_participant_type(event_name, member_type, is_staff)

        if member_type in ('SENIOR', 'CADET SPONSOR'):
            stats['seniors'] += 1
            if participant_type == 'staff':
                stats['staff'] += 1
        elif member_type == 'CADET':
            stats['cadets'] += 1
            if participant_type == 'cadre':
                stats['cadre'] += 1

        paid_in_full = get_bool('paid_in_full')
        amount_paid = get_float('amount_paid', 0.0)
        if paid_in_full or amount_paid > 0:
            stats['paid'] += 1
            stats['total_collected'] += amount_paid
        else:
            stats['unpaid'] += 1

        last_enc = get_str('last_encampment', '')
        first_encampment = last_enc.lower() == 'not complete' or last_enc == ''

        doc = {
            "capid": capid,
            "rank": get_str('rank'),
            "last_name": get_str('last_name'),
            "first_name": get_str('first_name'),
            "middle_name": get_str('middle_name') or None,
            "unit": get_str('unit'),
            "wing": get_str('wing') or None,
            "region": get_str('region') or None,
            "gender": get_str('gender') or None,
            "age": get_int('age'),
            "age_at_event": get_int('age_at_event'),
            "email": get_str('email') or None,
            "phone": get_str('phone') or None,
            "cell_phone": get_str('cell_phone') or None,
            "shirt_size": get_str('shirt_size') or None,
            "member_type": member_type or None,
            "participant_type": participant_type,
            "staff_member": is_staff,
            "paid": paid_in_full,
            "paid_in_full": paid_in_full,
            "amount_paid": amount_paid if amount_paid > 0 else None,
            "registration_status": get_str('registration_status') or None,
            "unit_approved": get_bool('unit_approved'),
            "unit_approval_date": get_str('unit_approval_date') or None,
            "wing_approved": get_bool('wing_approved'),
            "wing_approval_date": get_str('wing_approval_date') or None,
            "slotted": get_bool('slotted'),
            "address": get_str('address') or None,
            "city": get_str('city') or None,
            "state": get_str('state') or None,
            "zip_code": get_str('zip_code') or None,
            "emergency_contact": get_str('emergency_contact') or None,
            "emergency_phone": get_str('emergency_phone') or None,
            "cadet_parent_phone": get_str('cadet_parent_phone') or None,
            "cadet_parent_email": get_str('cadet_parent_email') or None,
            "unit_cc_name": get_str('unit_cc_name') or None,
            "unit_cc_email": get_str('unit_cc_email') or None,
            "last_encampment": get_str('last_encampment') or None,
            "cppt_expiration": get_str('cppt_expiration') or None,
            "first_aid": get_str('first_aid') or None,
            "is100_date": get_str('is100_date') or None,
            "is700_date": get_str('is700_date') or None,
            "first_encampment": first_encampment,
            "comments": get_str('comments') or None,
        }

        rows.append({
            "capid": capid,
            "doc": doc,
            "participant_type": participant_type,
            "member_type": member_type,
            "paid_in_full": paid_in_full,
            "amount_paid": amount_paid,
        })

    return rows, stats


# Fields that are user-facing and shown in the diff
DIFF_FIELDS = [
    "rank", "first_name", "last_name", "middle_name", "email", "phone", "cell_phone",
    "unit", "wing", "region", "gender", "age", "age_at_event", "shirt_size",
    "participant_type", "member_type", "paid_in_full", "amount_paid",
    "registration_status", "unit_approved", "wing_approved", "slotted",
]


@api_router.post("/participants/import")
async def import_participants(
    file: UploadFile = File(...),
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    """Import participants from CAP Event Admin Report Excel file (auto-apply, no preview).
    For interactive preview/conflict resolution, use POST /participants/import/preview followed by /import/apply."""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")

    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        df.columns = df.columns.str.strip()

        rows, stats = _parse_import_dataframe(df)
        now = datetime.now(timezone.utc).isoformat()
        imported_count = 0
        updated_count = 0

        for r in rows:
            doc = r["doc"]
            participant_type = r["participant_type"]
            capid = r["capid"]
            email_val = doc.get("email")
            first_name_val = doc.get("first_name", "")
            last_name_val = doc.get("last_name", "")

            existing = await find_existing_participant(capid, email_val, first_name_val, last_name_val)

            if existing:
                if participant_type is None:
                    doc.pop("participant_type", None)
                update_doc = {k: v for k, v in doc.items() if v is not None}
                update_doc["updated_at"] = now
                await db.participants.update_one({"id": existing["id"]}, {"$set": update_doc})
                updated_count += 1
                pid = existing["id"]
            else:
                if participant_type is None:
                    doc["participant_type"] = "basic_student"
                pid = str(uuid.uuid4())
                doc["id"] = pid
                doc["created_at"] = now
                doc["updated_at"] = now
                await db.participants.insert_one(doc)
                imported_count += 1

            await link_to_user_account(pid, capid, email_val)

        total_participant_count = await db.participants.count_documents({"is_removed": {"$ne": True}})
        await db.food_expense_settings.update_one(
            {"_id": "settings"},
            {"$set": {"total_participants": total_participant_count, "updated_at": now}},
            upsert=True,
        )
        sync_result = await sync_roster_to_budget()

        return {
            "message": f"Import complete: {imported_count} new, {updated_count} updated",
            "imported": imported_count,
            "updated": updated_count,
            "total": total_participant_count,
            "stats": stats,
            "budget_sync": sync_result,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")


@api_router.post("/participants/import/preview")
async def import_preview(
    file: UploadFile = File(...),
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    """Parse an upload, classify each row (create/update/conflict) and return a staging_id
    along with a preview the user can confirm/resolve before applying."""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")

    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
        df.columns = df.columns.str.strip()
        rows, stats = _parse_import_dataframe(df)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

    preview_rows = []
    summary = {"new": 0, "update": 0, "conflict": 0, "skipped": 0}

    for idx, r in enumerate(rows):
        doc = r["doc"]
        capid = r["capid"]
        first_name_val = doc.get("first_name", "")
        last_name_val = doc.get("last_name", "")
        email_val = doc.get("email")

        match = await find_match_with_candidates(capid, email_val, first_name_val, last_name_val)

        candidates_summary = [
            {
                "id": c["id"],
                "capid": c.get("capid"),
                "rank": c.get("rank"),
                "first_name": c.get("first_name"),
                "last_name": c.get("last_name"),
                "unit": c.get("unit"),
                "wing": c.get("wing"),
                "email": c.get("email"),
                "participant_type": c.get("participant_type"),
                "flight": c.get("flight"),
                "squadron": c.get("squadron"),
            }
            for c in match["candidates"]
        ]

        if match["match_type"] == "name" and len(match["candidates"]) > 1:
            action = "conflict"
            target_id = None
            summary["conflict"] += 1
        elif match["participant"]:
            action = "update"
            target_id = match["participant"]["id"]
            summary["update"] += 1
        else:
            action = "create"
            target_id = None
            summary["new"] += 1

        # Compute field-level diff for updates
        changes = {}
        if match["participant"] and match["match_type"] != "none":
            existing = match["participant"]
            for f in DIFF_FIELDS:
                new_val = doc.get(f)
                # Skip blanks: empty string / None / NaN — they won't overwrite
                if new_val is None or (isinstance(new_val, str) and new_val.strip() == ""):
                    continue
                old_val = existing.get(f)
                if str(old_val or "") != str(new_val or ""):
                    changes[f] = {"old": old_val, "new": new_val}

        preview_rows.append({
            "row_idx": idx,
            "capid": capid,
            "first_name": first_name_val,
            "last_name": last_name_val,
            "email": email_val,
            "unit": doc.get("unit"),
            "wing": doc.get("wing"),
            "incoming_type": r["participant_type"],
            "match_type": match["match_type"],
            "default_action": action,
            "default_target_id": target_id,
            "candidates": candidates_summary,
            "changes": changes,
        })

    # Persist staging
    staging_id = str(uuid.uuid4())
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    await db.import_staging.insert_one({
        "id": staging_id,
        "user_id": user.get("id") or user.get("sub"),
        "user_email": user.get("email"),
        "filename": file.filename,
        "rows": rows,
        "stats": stats,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at,
    })

    # Opportunistic cleanup of expired staging docs
    await db.import_staging.delete_many({"expires_at": {"$lt": datetime.now(timezone.utc).isoformat()}})

    return {
        "staging_id": staging_id,
        "filename": file.filename,
        "summary": summary,
        "stats": stats,
        "rows": preview_rows,
        "expires_at": expires_at,
    }


class ImportApplyRequest(BaseModel):
    staging_id: str
    resolutions: dict[str, dict] = {}  # row_idx (str) → {"action": "update"|"create"|"skip", "participant_id": str|None}


@api_router.post("/participants/import/apply")
async def import_apply(
    data: ImportApplyRequest,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    """Apply a previously-previewed import using the user's row-level resolutions."""
    staging = await db.import_staging.find_one({"id": data.staging_id}, {"_id": 0})
    if not staging:
        raise HTTPException(status_code=404, detail="Staging not found or expired. Re-upload the file.")

    rows = staging.get("rows") or []
    stats = staging.get("stats") or {}
    now = datetime.now(timezone.utc).isoformat()

    imported_count = 0
    updated_count = 0
    skipped_count = 0

    for idx, r in enumerate(rows):
        doc = dict(r["doc"])
        participant_type = r["participant_type"]
        capid = r["capid"]
        email_val = doc.get("email")
        first_name_val = doc.get("first_name", "")
        last_name_val = doc.get("last_name", "")

        resolution = data.resolutions.get(str(idx)) or {}
        action = resolution.get("action")
        target_id = resolution.get("participant_id")

        # If no resolution provided, fall back to auto-detection
        if not action:
            existing = await find_existing_participant(capid, email_val, first_name_val, last_name_val)
            if existing:
                action = "update"
                target_id = existing["id"]
            else:
                action = "create"

        if action == "skip":
            skipped_count += 1
            continue

        if action == "update":
            if not target_id:
                # Resolve via auto-match if not provided
                existing = await find_existing_participant(capid, email_val, first_name_val, last_name_val)
                if not existing:
                    # No match — fall through to create
                    action = "create"
                else:
                    target_id = existing["id"]

        if action == "update" and target_id:
            if participant_type is None:
                doc.pop("participant_type", None)
            update_doc = {k: v for k, v in doc.items() if v is not None}
            update_doc["updated_at"] = now
            await db.participants.update_one({"id": target_id}, {"$set": update_doc})
            updated_count += 1
            pid = target_id
        else:
            # create
            if participant_type is None:
                doc["participant_type"] = "basic_student"
            pid = str(uuid.uuid4())
            doc["id"] = pid
            doc["created_at"] = now
            doc["updated_at"] = now
            await db.participants.insert_one(doc)
            imported_count += 1

        await link_to_user_account(pid, capid, email_val)

    # Cleanup staging
    await db.import_staging.delete_one({"id": data.staging_id})

    total_participant_count = await db.participants.count_documents({"is_removed": {"$ne": True}})
    await db.food_expense_settings.update_one(
        {"_id": "settings"},
        {"$set": {"total_participants": total_participant_count, "updated_at": now}},
        upsert=True,
    )
    sync_result = await sync_roster_to_budget()

    return {
        "message": f"Import applied: {imported_count} new, {updated_count} updated, {skipped_count} skipped",
        "imported": imported_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "total": total_participant_count,
        "stats": stats,
        "budget_sync": sync_result,
    }
