"""Flight Reporting API"""
from fastapi import Depends, HTTPException, BackgroundTasks
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import logging

from database import db, api_router
from models import (
    UserRole, FlightReportCreate, FlightReportResponse,
    EscalateReportRequest, ReportDeadlineSettings
)
from permissions import get_current_user, require_role

# ================= FLIGHT REPORTING API =================

@api_router.get("/reports/settings")
async def get_report_settings(user: dict = Depends(get_current_user)):
    """Get report deadline settings"""
    settings = await db.report_settings.find_one({'_id': 'settings'})
    if not settings:
        # Return defaults
        return {
            "deadline_time": "21:00",
            "reminder_minutes_before": 60,
            "is_enabled": True
        }
    return {
        "deadline_time": settings.get("deadline_time", "21:00"),
        "reminder_minutes_before": settings.get("reminder_minutes_before", 60),
        "is_enabled": settings.get("is_enabled", True)
    }

@api_router.post("/reports/settings")
async def update_report_settings(
    settings: ReportDeadlineSettings,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.PLANS_PROGRAMS]))
):
    """Update report deadline settings (admin only)"""
    await db.report_settings.update_one(
        {'_id': 'settings'},
        {'$set': {
            'deadline_time': settings.deadline_time,
            'reminder_minutes_before': settings.reminder_minutes_before,
            'is_enabled': settings.is_enabled,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'updated_by': user['id']
        }},
        upsert=True
    )
    return {"message": "Settings updated successfully"}

@api_router.get("/reports/my/submitted")
async def get_my_submitted_reports(
    user: dict = Depends(get_current_user)
):
    """Get reports submitted by the current user"""
    reports = await db.flight_reports.find(
        {"submitted_by": user['id']},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return reports

@api_router.get("/reports/commander-issues")
async def get_commander_issues(
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.EXEC_CADRE]))
):
    """Get all reports with commander issues (escalated status)"""
    reports = await db.flight_reports.find(
        {"status": "escalated"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return reports

@api_router.post("/reports")
async def create_flight_report(
    report: FlightReportCreate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Submit a new flight report"""
    now = datetime.now(timezone.utc).isoformat()
    report_id = str(uuid.uuid4())
    
    # Determine if there are commander issues that need escalation
    has_commander_issues = report.commander_issues.content.strip() != "" and report.commander_issues.has_issues
    
    report_doc = {
        "id": report_id,
        "report_date": report.report_date,
        "flight": report.flight,
        "squadron": report.squadron,
        "reporter_role": report.reporter_role,
        "morale": report.morale.model_dump(),
        "safety_concerns": report.safety_concerns.model_dump(),
        "discipline_issues": report.discipline_issues.model_dump(),
        "training_performance": report.training_performance.model_dump(),
        "significant_events": report.significant_events.model_dump(),
        "recommendations": report.recommendations.model_dump(),
        "commander_issues": report.commander_issues.model_dump(),
        "submitted_by": user['id'],
        "submitted_by_name": user['name'],
        "status": "escalated_flight_commander" if has_commander_issues else "submitted",
        "escalation_level": "flight_sergeant" if has_commander_issues else None,
        "escalation_history": [],
        "reviewed_by": None,
        "reviewed_at": None,
        "review_notes": None,
        "created_at": now,
        "updated_at": now
    }
    
    await db.flight_reports.insert_one(report_doc)
    
    # Send notification if there are commander issues
    if has_commander_issues:
        # Get flight label
        flight_labels = {
            "alpha": "Alpha", "bravo": "Bravo", "charlie": "Charlie",
            "delta": "Delta", "echo": "Echo", "foxtrot": "Foxtrot"
        }
        flight_label = flight_labels.get(report.flight, report.flight.title())
        
        # Store notification for squadron commanders and up
        notification_id = str(uuid.uuid4())
        await db.notifications.insert_one({
            "id": notification_id,
            "title": f"Commander Issue - {flight_label} Flight",
            "body": f"A flight report from {flight_label} Flight contains items requiring command attention.",
            "target_groups": ["commander", "exec_cadre", "staff", "plans_programs"],
            "report_id": report_id,
            "sent_by": user["id"],
            "sent_at": now,
            "notification_type": "commander_issue"
        })
    
    return {
        "message": "Report submitted successfully",
        "id": report_id,
        "status": report_doc["status"]
    }

@api_router.get("/reports")
async def get_flight_reports(
    flight: Optional[str] = None,
    squadron: Optional[str] = None,
    report_date: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get flight reports (filtered by user's access level)"""
    query = {}
    
    user_role = user.get('role')
    user_flight = user.get('flight', '').lower() if user.get('flight') else None
    user_squadron = user.get('squadron', '').lower() if user.get('squadron') else None
    
    # Roles with full access to all reports
    full_access_roles = [
        UserRole.COMMANDER, 
        UserRole.EXECUTIVE_STAFF,
        UserRole.EXEC_CADRE, 
        UserRole.STAFF,  # Includes Health Services
        UserRole.PLANS_PROGRAMS
    ]
    
    # Access control based on role
    if user_role in full_access_roles:
        # Full access - can see all reports
        pass
    elif user_squadron and user_squadron in ['6th_cts', '21st_cts', '22nd_cts']:
        # Squadron commander - can see their squadron's reports
        query['squadron'] = user_squadron
    elif user_flight:
        # Flight staff - can see their flight's reports only
        query['flight'] = user_flight
    else:
        # Limited access - only own reports
        query['submitted_by'] = user['id']
    
    # Apply additional filters
    if flight:
        query['flight'] = flight.lower()
    if squadron:
        query['squadron'] = squadron.lower()
    if report_date:
        query['report_date'] = report_date
    if status:
        query['status'] = status
    
    reports = await db.flight_reports.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return reports

@api_router.get("/reports/{report_id}")
async def get_flight_report(
    report_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific flight report"""
    report = await db.flight_reports.find_one({"id": report_id}, {"_id": 0})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Access control - same roles have full access
    user_role = user.get('role')
    user_flight = user.get('flight', '').lower() if user.get('flight') else None
    user_squadron = user.get('squadron', '').lower() if user.get('squadron') else None
    
    full_access_roles = [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.EXEC_CADRE, UserRole.STAFF, UserRole.PLANS_PROGRAMS]
    
    if user_role not in full_access_roles:
        if user_squadron and user_squadron in ['6th_cts', '21st_cts', '22nd_cts']:
            if report['squadron'] != user_squadron:
                raise HTTPException(status_code=403, detail="Access denied")
        elif user_flight:
            if report['flight'] != user_flight:
                raise HTTPException(status_code=403, detail="Access denied")
        elif report['submitted_by'] != user['id']:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return report

@api_router.put("/reports/{report_id}/review")
async def review_flight_report(
    report_id: str,
    review_notes: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Mark a report as reviewed (for commanders/supervisors)"""
    report = await db.flight_reports.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Only commanders, exec cadre, or squadron commanders can review
    user_role = user.get('role')
    user_squadron = user.get('squadron', '').lower() if user.get('squadron') else None
    
    can_review = False
    if user_role in [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.EXEC_CADRE]:
        can_review = True
    elif user_squadron and user_squadron == report['squadron']:
        # Squadron commander can review their squadron's reports
        can_review = True
    
    if not can_review:
        raise HTTPException(status_code=403, detail="You don't have permission to review this report")
    
    now = datetime.now(timezone.utc).isoformat()
    await db.flight_reports.update_one(
        {"id": report_id},
        {"$set": {
            "status": "reviewed",
            "reviewed_by": user['id'],
            "reviewed_at": now,
            "review_notes": review_notes,
            "updated_at": now
        }}
    )
    
    return {"message": "Report marked as reviewed"}

@api_router.put("/reports/{report_id}/escalate")
async def escalate_flight_report(
    report_id: str,
    request: EscalateReportRequest,
    user: dict = Depends(get_current_user)
):
    """Escalate a report up the chain of command
    
    Full chain: Flight Sergeant -> Flight Commander -> Squadron Commander -> 
                Exec Cadre -> DCS & Commandant -> Encampment Commander
    """
    report = await db.flight_reports.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    user_role = user.get('role')
    current_level = report.get('escalation_level', 'flight_sergeant')
    
    # Define the complete escalation chain with who can escalate at each level
    # Each level defines: who can escalate FROM this level, the next level, and the status name
    escalation_chain = {
        'flight_sergeant': {
            'can_escalate_roles': [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.EXEC_CADRE, UserRole.STAFF, UserRole.PLANS_PROGRAMS, UserRole.CADRE],
            'next_level': 'flight_commander',
            'status': 'escalated_flight_commander'
        },
        'flight_commander': {
            'can_escalate_roles': [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.EXEC_CADRE, UserRole.STAFF, UserRole.PLANS_PROGRAMS],
            'next_level': 'squadron_commander',
            'status': 'escalated_squadron'
        },
        'squadron_commander': {
            'can_escalate_roles': [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.EXEC_CADRE, UserRole.STAFF, UserRole.PLANS_PROGRAMS],
            'next_level': 'exec_cadre',
            'status': 'escalated_exec'
        },
        'exec_cadre': {
            'can_escalate_roles': [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.EXEC_CADRE],
            'next_level': 'dcs_commandant',
            'status': 'escalated_dcs'
        },
        'dcs_commandant': {
            'can_escalate_roles': [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF],
            'next_level': 'encampment_commander',
            'status': 'escalated_commander'
        },
        'encampment_commander': {
            'can_escalate_roles': [UserRole.COMMANDER],
            'next_level': None,  # Top of chain
            'status': 'at_commander'
        }
    }
    
    # Valid escalation targets
    valid_targets = ['flight_commander', 'squadron_commander', 'exec_cadre', 'dcs_commandant', 'encampment_commander']
    
    # Check if user can escalate from current level
    current_chain = escalation_chain.get(current_level, escalation_chain['flight_sergeant'])
    
    if user_role not in current_chain['can_escalate_roles']:
        raise HTTPException(
            status_code=403, 
            detail=f"You don't have permission to escalate from {current_level.replace('_', ' ')}"
        )
    
    # Determine target escalation level
    target_level = request.escalate_to
    if target_level not in valid_targets:
        raise HTTPException(status_code=400, detail="Invalid escalation target")
    
    # Validate escalation path - must go to the next level in chain
    if current_level == 'encampment_commander':
        raise HTTPException(status_code=400, detail="Report is already at the highest level")
    
    # Ensure we're escalating to the correct next level
    expected_next = current_chain['next_level']
    if target_level != expected_next:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot skip levels. Must escalate to {expected_next.replace('_', ' ').title()} next"
        )
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Create escalation history entry
    escalation_entry = {
        "from_level": current_level,
        "to_level": target_level,
        "escalated_by": user['id'],
        "escalated_by_name": user['name'],
        "escalated_at": now,
        "notes": request.notes or ""
    }
    
    # Determine new status from the chain
    new_status = current_chain['status']  # Use the status defined for escalating FROM the current level
    
    # Update the report
    await db.flight_reports.update_one(
        {"id": report_id},
        {
            "$set": {
                "status": new_status,
                "escalation_level": target_level,
                "updated_at": now
            },
            "$push": {
                "escalation_history": escalation_entry
            }
        }
    )
    
    # Create notification for the target level
    flight_labels = {
        "alpha": "Alpha", "bravo": "Bravo", "charlie": "Charlie",
        "delta": "Delta", "echo": "Echo", "foxtrot": "Foxtrot"
    }
    flight_label = flight_labels.get(report.get('flight', ''), report.get('flight', '').title())
    
    # Determine notification targets based on escalation level
    level_display_names = {
        'flight_commander': 'Flight Commander',
        'squadron_commander': 'Squadron Commander',
        'exec_cadre': 'Exec Cadre',
        'dcs_commandant': 'DCS & Commandant',
        'encampment_commander': 'Encampment Commander'
    }
    target_display = level_display_names.get(target_level, target_level.replace('_', ' ').title())
    
    # Notify relevant groups based on target level
    if target_level == 'encampment_commander':
        notification_targets = ['commander', 'executive_staff']
    elif target_level == 'dcs_commandant':
        notification_targets = ['commander', 'executive_staff']  # DCS and Commandant level
    elif target_level == 'exec_cadre':
        notification_targets = ['exec_cadre', 'commander', 'executive_staff']
    else:
        notification_targets = ['staff', 'exec_cadre', 'commander', 'executive_staff']
    
    notification_id = str(uuid.uuid4())
    await db.notifications.insert_one({
        "id": notification_id,
        "title": f"Commander Issue Escalated - {flight_label} Flight",
        "body": f"A commander issue has been escalated to {target_display} for review.",
        "target_groups": notification_targets,
        "report_id": report_id,
        "sent_by": user["id"],
        "sent_at": now,
        "notification_type": "escalation"
    })
    
    return {
        "message": f"Report escalated to {target_display}",
        "new_level": target_level,
        "status": new_status
    }

@api_router.put("/reports/{report_id}/resolve")
async def resolve_escalated_report(
    report_id: str,
    resolution_notes: Optional[str] = None,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.EXEC_CADRE]))
):
    """Mark an escalated report as resolved (Commander or Exec Cadre only)"""
    report = await db.flight_reports.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Add resolution to escalation history
    resolution_entry = {
        "action": "resolved",
        "resolved_by": user['id'],
        "resolved_by_name": user['name'],
        "resolved_at": now,
        "notes": resolution_notes or ""
    }
    
    await db.flight_reports.update_one(
        {"id": report_id},
        {
            "$set": {
                "status": "resolved",
                "reviewed_by": user['id'],
                "reviewed_at": now,
                "review_notes": resolution_notes,
                "updated_at": now
            },
            "$push": {
                "escalation_history": resolution_entry
            }
        }
    )
    
    return {"message": "Report marked as resolved"}

@api_router.delete("/reports/{report_id}")
async def delete_flight_report(
    report_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a flight report (only author or commander)"""
    report = await db.flight_reports.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Only the author or a commander can delete
    if report['submitted_by'] != user['id'] and user.get('role') not in [UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]:
        raise HTTPException(status_code=403, detail="You don't have permission to delete this report")
    
    await db.flight_reports.delete_one({"id": report_id})
    return {"message": "Report deleted successfully"}

logger = logging.getLogger(__name__)


