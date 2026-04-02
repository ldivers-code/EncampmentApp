"""Org Chart routes"""
from fastapi import Depends, HTTPException
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from database import db, api_router
from models import UserRole, OrgChartRoleCreate, OrgChartRoleUpdate, OrgChartRoleResponse
from permissions import get_current_user, require_role

# ================= ORG CHART ROUTES =================

async def get_role_with_details(role: dict) -> dict:
    """Enrich org chart role with member details and subordinates"""
    # Get assigned member details
    if role.get("assigned_participant_id"):
        participant = await db.participants.find_one(
            {"id": role["assigned_participant_id"]}, 
            {"_id": 0, "first_name": 1, "last_name": 1, "rank": 1}
        )
        if participant:
            role["assigned_member_name"] = f"{participant.get('rank', '')} {participant.get('first_name', '')} {participant.get('last_name', '')}".strip()
            role["assigned_member_rank"] = participant.get("rank", "")
        else:
            role["assigned_member_name"] = None
            role["assigned_member_rank"] = None
    else:
        role["assigned_member_name"] = None
        role["assigned_member_rank"] = None
    
    # Get direct subordinates
    subordinates = await db.org_chart_roles.find(
        {"reports_to": role["role_id"]}, 
        {"_id": 0, "role_id": 1}
    ).to_list(100)
    role["direct_subordinates"] = [s["role_id"] for s in subordinates]
    
    return role

@api_router.get("/org-chart/roles", response_model=List[OrgChartRoleResponse])
async def get_org_chart_roles(user: dict = Depends(get_current_user)):
    """Get all org chart roles - accessible by all authenticated users"""
    roles = await db.org_chart_roles.find({}, {"_id": 0}).to_list(1000)
    enriched_roles = []
    for role in roles:
        enriched = await get_role_with_details(role)
        enriched_roles.append(OrgChartRoleResponse(**enriched))
    return enriched_roles

@api_router.get("/org-chart/roles/{role_id}", response_model=OrgChartRoleResponse)
async def get_org_chart_role(role_id: str, user: dict = Depends(get_current_user)):
    """Get single org chart role details - accessible by all authenticated users"""
    role = await db.org_chart_roles.find_one({"role_id": role_id}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    enriched = await get_role_with_details(role)
    return OrgChartRoleResponse(**enriched)

@api_router.post("/org-chart/roles", response_model=OrgChartRoleResponse)
async def create_org_chart_role(
    data: OrgChartRoleCreate,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    """Create new org chart role - editors only"""
    # Check if role_id already exists
    existing = await db.org_chart_roles.find_one({"role_id": data.role_id})
    if existing:
        raise HTTPException(status_code=400, detail="Role ID already exists")
    
    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    doc = {
        "id": doc_id,
        **data.model_dump(),
        "created_at": now,
        "updated_at": now
    }
    await db.org_chart_roles.insert_one(doc)
    doc.pop("_id", None)
    
    enriched = await get_role_with_details(doc)
    return OrgChartRoleResponse(**enriched)

@api_router.put("/org-chart/roles/{role_id}", response_model=OrgChartRoleResponse)
async def update_org_chart_role(
    role_id: str,
    data: OrgChartRoleUpdate,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    """Update org chart role - editors only"""
    now = datetime.now(timezone.utc).isoformat()
    
    # Only update fields that are provided
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now
    
    result = await db.org_chart_roles.update_one(
        {"role_id": role_id}, 
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Role not found")
    
    role = await db.org_chart_roles.find_one({"role_id": role_id}, {"_id": 0})
    enriched = await get_role_with_details(role)
    return OrgChartRoleResponse(**enriched)

@api_router.put("/org-chart/roles/{role_id}/assign", response_model=OrgChartRoleResponse)
async def assign_org_chart_role(
    role_id: str,
    participant_id: Optional[str] = None,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    """Assign or unassign a participant to a role - editors only"""
    now = datetime.now(timezone.utc).isoformat()
    
    # Verify participant exists if assigning
    if participant_id:
        participant = await db.participants.find_one({"id": participant_id})
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
    
    result = await db.org_chart_roles.update_one(
        {"role_id": role_id},
        {"$set": {"assigned_participant_id": participant_id, "updated_at": now}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Role not found")
    
    role = await db.org_chart_roles.find_one({"role_id": role_id}, {"_id": 0})
    enriched = await get_role_with_details(role)
    return OrgChartRoleResponse(**enriched)

@api_router.delete("/org-chart/roles/{role_id}")
async def delete_org_chart_role(
    role_id: str,
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF, UserRole.STAFF]))
):
    """Delete org chart role - editors only"""
    # Check if any roles report to this one
    subordinates = await db.org_chart_roles.count_documents({"reports_to": role_id})
    if subordinates > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete role with {subordinates} subordinate(s). Reassign them first."
        )
    
    result = await db.org_chart_roles.delete_one({"role_id": role_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Role not found")
    return {"message": "Role deleted successfully"}

@api_router.post("/org-chart/seed-defaults")
async def seed_default_org_chart(
    user: dict = Depends(require_role([UserRole.DCP, UserRole.COMMANDER, UserRole.EXECUTIVE_STAFF]))
):
    """Seed default encampment org chart structure - commander only"""
    # Check if roles already exist
    existing_count = await db.org_chart_roles.count_documents({})
    if existing_count > 0:
        raise HTTPException(status_code=400, detail="Org chart already has roles. Clear first if you want to reseed.")
    
    now = datetime.now(timezone.utc).isoformat()
    
    default_roles = [
        # ===== LEVEL 0 - Director of Cadet Programs (Advisory) =====
        {"role_id": "dcp", "title": "Director of Cadet Programs", "level": 0, "order": 0, "reports_to": None,
         "summary": "Wing-level advisory role overseeing the encampment. Above the Commander but serves in an advisory capacity for the activity.",
         "responsibilities": "- Provide Wing-level oversight and guidance\n- Advise Encampment Commander on program execution\n- Ensure alignment with CAP Cadet Programs standards\n- Observe and evaluate encampment operations\n- Liaison between encampment and Wing HQ\n- Final authority on program policy matters"},
        
        # ===== LEVEL 1 - Encampment Commander =====
        {"role_id": "enc-commander", "title": "Encampment Commander", "level": 1, "order": 0, "reports_to": "dcp",
         "summary": "Overall commander responsible for the entire encampment operation.",
         "responsibilities": "- Provide strategic leadership and vision for encampment\n- Ensure safety and welfare of all participants\n- Coordinate with Wing and Region leadership\n- Final authority on all encampment matters\n- Conduct commander's calls and briefings\n- Approve all major decisions"},
        
        # ===== LEVEL 2 - Direct Reports to EC =====
        {"role_id": "sm-superintendent", "title": "SM Superintendent", "level": 2, "order": 0, "reports_to": "enc-commander",
         "summary": "Senior Member Superintendent - supports commander with senior member coordination.",
         "responsibilities": "- Coordinate senior member staff activities\n- Serve as liaison between cadets and senior members\n- Assist with administrative functions\n- Support commander as needed"},
        {"role_id": "finance", "title": "Finance", "level": 2, "order": 1, "reports_to": "enc-commander",
         "summary": "Manages all financial operations for encampment.",
         "responsibilities": "- Track all income and expenses\n- Process registration payments\n- Manage budget allocations\n- Prepare financial reports\n- Handle vendor payments"},
        {"role_id": "chaplain-cdi", "title": "Chaplain/CDI", "level": 2, "order": 2, "reports_to": "enc-commander",
         "summary": "Provides spiritual support and character development instruction.",
         "responsibilities": "- Conduct religious services\n- Provide counseling support\n- Lead character development sessions\n- Support cadet welfare"},
        {"role_id": "health-services", "title": "Health Services", "level": 2, "order": 3, "reports_to": "enc-commander",
         "summary": "Oversees all medical support and health services.",
         "responsibilities": "- Manage medical staff and supplies\n- Coordinate emergency medical response\n- Track medications and health records\n- Conduct health screenings\n- Ensure AED and first aid readiness"},
        {"role_id": "safety", "title": "Safety", "level": 2, "order": 4, "reports_to": "enc-commander",
         "summary": "Ensures safety compliance throughout encampment operations.",
         "responsibilities": "- Conduct safety briefings and inspections\n- Monitor activity safety compliance\n- Investigate and report incidents\n- Maintain safety documentation\n- Coordinate with health services"},
        
        # ===== LEVEL 2 - Commandant & Deputy Support =====
        {"role_id": "commandant", "title": "Commandant", "level": 3, "order": 0, "reports_to": "enc-commander",
         "summary": "Senior Member overseeing all cadet training operations.",
         "responsibilities": "- Supervise Cadet Commander and training staff\n- Ensure training objectives are met\n- Coordinate training schedule execution\n- Evaluate cadet performance\n- Maintain discipline standards"},
        {"role_id": "cadet-commander", "title": "Cadet Commander", "level": 3, "order": 1, "reports_to": "enc-commander",
         "summary": "Senior cadet leader commanding the cadet corps.",
         "responsibilities": "- Lead cadet staff and corps\n- Execute training plan\n- Set example for all cadets\n- Conduct formations and inspections\n- Report to Commandant and EC"},
        {"role_id": "deputy-support", "title": "Deputy Comm for Support", "level": 3, "order": 2, "reports_to": "enc-commander",
         "summary": "Oversees all support and logistics functions.",
         "responsibilities": "- Supervise support staff sections\n- Manage facilities and resources\n- Coordinate transportation and logistics\n- Oversee communications and PA"},
        
        # ===== LEVEL 3 - Under Commandant =====
        {"role_id": "chief-instructor", "title": "Chief Instructor", "level": 4, "order": 0, "reports_to": "commandant",
         "summary": "Leads instructor cadre for training delivery.",
         "responsibilities": "- Train and supervise instructors\n- Ensure training quality\n- Develop lesson plans\n- Evaluate instruction effectiveness"},
        {"role_id": "chief-training-officer", "title": "Chief Training Officer", "level": 4, "order": 1, "reports_to": "commandant",
         "summary": "Manages training schedule and operations.",
         "responsibilities": "- Coordinate daily training schedule\n- Track training completion\n- Manage training resources\n- Support instructors"},
        
        # ===== LEVEL 3 - Under Cadet Commander =====
        {"role_id": "dean-academics", "title": "Dean of Academics", "level": 4, "order": 2, "reports_to": "cadet-commander",
         "summary": "Oversees academic and classroom instruction.",
         "responsibilities": "- Manage classroom training\n- Coordinate testing and evaluations\n- Track academic progress\n- Support instructor development"},
        {"role_id": "deputy-commander", "title": "Deputy Commander", "level": 4, "order": 3, "reports_to": "cadet-commander",
         "summary": "Assists Cadet Commander with corps leadership.",
         "responsibilities": "- Support Cadet Commander duties\n- Lead in CC's absence\n- Coordinate staff activities\n- Assist with formations"},
        
        # ===== LEVEL 3 - Under Deputy Support =====
        {"role_id": "word", "title": "Word", "level": 4, "order": 4, "reports_to": "deputy-support",
         "summary": "Manages administrative and word processing functions.",
         "responsibilities": "- Prepare documents and reports\n- Maintain records and files\n- Support administrative tasks\n- Coordinate information flow"},
        {"role_id": "public-affairs", "title": "Public Affairs", "level": 4, "order": 5, "reports_to": "deputy-support",
         "summary": "Manages public affairs and media documentation.",
         "responsibilities": "- Photography and videography\n- Social media updates\n- Prepare graduation program\n- Media coordination and releases"},
        {"role_id": "logistics", "title": "Logistics", "level": 4, "order": 6, "reports_to": "deputy-support",
         "summary": "Manages supply and logistics operations.",
         "responsibilities": "- Inventory management\n- Supply distribution\n- Equipment accountability\n- Facility coordination"},
        {"role_id": "plans-programs", "title": "Plans and Programs", "level": 4, "order": 7, "reports_to": "deputy-support",
         "summary": "Manages planning and program coordination.",
         "responsibilities": "- Develop activity plans\n- Coordinate special programs\n- Track milestones and objectives\n- Support scheduling"},
        {"role_id": "comms", "title": "Comms", "level": 4, "order": 8, "reports_to": "deputy-support",
         "summary": "Manages communications equipment and operations.",
         "responsibilities": "- Maintain radios and comm equipment\n- Coordinate communication channels\n- Support emergency communications\n- Train users on equipment"},
        
        # ===== LEVEL 5 - Training Officers (3 squadrons) =====
        {"role_id": "to-sq1", "title": "Training Officer - 6th CTS", "level": 5, "order": 0, "reports_to": "chief-training-officer",
         "summary": "Training Officer for 6th CTS.",
         "responsibilities": "- Oversee 6th CTS training\n- Supervise Assistant TO\n- Evaluate training effectiveness\n- Report to Chief Training Officer"},
        {"role_id": "to-sq2", "title": "Training Officer - 21st CTS", "level": 5, "order": 1, "reports_to": "chief-training-officer",
         "summary": "Training Officer for 21st CTS.",
         "responsibilities": "- Oversee 21st CTS training\n- Supervise Assistant TO\n- Evaluate training effectiveness\n- Report to Chief Training Officer"},
        {"role_id": "to-sq3", "title": "Training Officer - 22nd CTS", "level": 5, "order": 2, "reports_to": "chief-training-officer",
         "summary": "Training Officer for 22nd CTS.",
         "responsibilities": "- Oversee 22nd CTS training\n- Supervise Assistant TO\n- Evaluate training effectiveness\n- Report to Chief Training Officer"},
        
        # ===== LEVEL 6 - Asst Training Officers =====
        {"role_id": "ato-sq1", "title": "Asst Training Officer - 6th CTS", "level": 6, "order": 0, "reports_to": "to-sq1",
         "summary": "Assistant Training Officer for 6th CTS.",
         "responsibilities": "- Assist with squadron training\n- Support Training Officer\n- Fill in as needed"},
        {"role_id": "ato-sq2", "title": "Asst Training Officer - 21st CTS", "level": 6, "order": 1, "reports_to": "to-sq2",
         "summary": "Assistant Training Officer for 21st CTS.",
         "responsibilities": "- Assist with squadron training\n- Support Training Officer\n- Fill in as needed"},
        {"role_id": "ato-sq3", "title": "Asst Training Officer - 22nd CTS", "level": 6, "order": 2, "reports_to": "to-sq3",
         "summary": "Assistant Training Officer for 22nd CTS.",
         "responsibilities": "- Assist with squadron training\n- Support Training Officer\n- Fill in as needed"},
        
        # ===== LEVEL 6 - Squadron Commanders =====
        {"role_id": "sq1-cc", "title": "Squadron Commander - 6th CTS", "level": 6, "order": 3, "reports_to": "to-sq1",
         "summary": "Commands 6th CTS cadets.",
         "responsibilities": "- Lead 6th CTS cadets\n- Conduct formations\n- Supervise flight commanders\n- Maintain discipline"},
        {"role_id": "sq2-cc", "title": "Squadron Commander - 21st CTS", "level": 6, "order": 4, "reports_to": "to-sq2",
         "summary": "Commands 21st CTS cadets.",
         "responsibilities": "- Lead 21st CTS cadets\n- Conduct formations\n- Supervise flight commanders\n- Maintain discipline"},
        {"role_id": "sq3-cc", "title": "Squadron Commander - 22nd CTS", "level": 6, "order": 5, "reports_to": "to-sq3",
         "summary": "Commands 22nd CTS cadets.",
         "responsibilities": "- Lead 22nd CTS cadets\n- Conduct formations\n- Supervise flight commanders\n- Maintain discipline"},
        {"role_id": "support-sq-cc", "title": "Support Squadron Commander", "level": 5, "order": 6, "reports_to": "deputy-support",
         "summary": "Commands Support Squadron personnel.",
         "responsibilities": "- Lead support squadron staff\n- Coordinate support operations\n- Supervise support OICs\n- Report to Deputy Support"},
        
        # ===== LEVEL 6 - Squadron Staff =====
        {"role_id": "sq1-super", "title": "Sqdn Superintendent - 6th CTS", "level": 6, "order": 0, "reports_to": "sq1-cc",
         "summary": "6th CTS Superintendent.",
         "responsibilities": "- Support Squadron CC\n- Manage squadron admin\n- Coordinate with flights"},
        {"role_id": "sq2-super", "title": "Sqdn Superintendent - 21st CTS", "level": 6, "order": 1, "reports_to": "sq2-cc",
         "summary": "21st CTS Superintendent.",
         "responsibilities": "- Support Squadron CC\n- Manage squadron admin\n- Coordinate with flights"},
        {"role_id": "sq3-super", "title": "Sqdn Superintendent - 22nd CTS", "level": 6, "order": 2, "reports_to": "sq3-cc",
         "summary": "22nd CTS Superintendent.",
         "responsibilities": "- Support Squadron CC\n- Manage squadron admin\n- Coordinate with flights"},
        
        # ===== LEVEL 6 - Support Squadron Section OICs =====
        {"role_id": "support-logistics-oic", "title": "Logistics OIC", "level": 6, "order": 3, "reports_to": "support-sq-cc",
         "summary": "Officer in Charge of Logistics section.",
         "responsibilities": "- Manage logistics operations\n- Supervise logistics team\n- Track supplies and equipment\n- Report to Support Sq CC"},
        {"role_id": "support-comms-oic", "title": "Communications OIC", "level": 6, "order": 4, "reports_to": "support-sq-cc",
         "summary": "Officer in Charge of Communications section.",
         "responsibilities": "- Manage communications operations\n- Oversee radio and comms equipment\n- Coordinate with all squadrons"},
        {"role_id": "support-pa-oic", "title": "Public Affairs OIC", "level": 6, "order": 5, "reports_to": "support-sq-cc",
         "summary": "Officer in Charge of Public Affairs section.",
         "responsibilities": "- Lead PA team\n- Coordinate photography and media\n- Manage public communications"},
        {"role_id": "support-dining-oic", "title": "Dining Services OIC", "level": 6, "order": 6, "reports_to": "support-sq-cc",
         "summary": "Officer in Charge of Dining Services section.",
         "responsibilities": "- Coordinate meal operations\n- Manage dining facility\n- Oversee food service staff"},
        {"role_id": "support-health-oic", "title": "Health Services OIC", "level": 6, "order": 7, "reports_to": "support-sq-cc",
         "summary": "Officer in Charge of Health Services section.",
         "responsibilities": "- Manage health services operations\n- Coordinate medical support\n- Oversee health screenings"},
        
        # ===== LEVEL 7 - Support Squadron Section AOICs =====
        {"role_id": "support-logistics-aoic", "title": "Logistics AOIC", "level": 7, "order": 10, "reports_to": "support-logistics-oic",
         "summary": "Assistant OIC of Logistics.",
         "responsibilities": "- Assist Logistics OIC\n- Manage supply chain\n- Support equipment distribution"},
        {"role_id": "support-comms-aoic", "title": "Communications AOIC", "level": 7, "order": 11, "reports_to": "support-comms-oic",
         "summary": "Assistant OIC of Communications.",
         "responsibilities": "- Assist Communications OIC\n- Support radio operations\n- Maintain comms equipment"},
        {"role_id": "support-pa-aoic", "title": "Public Affairs AOIC", "level": 7, "order": 12, "reports_to": "support-pa-oic",
         "summary": "Assistant OIC of Public Affairs.",
         "responsibilities": "- Assist PA OIC\n- Support photography\n- Help manage media content"},
        {"role_id": "support-dining-aoic", "title": "Dining Services AOIC", "level": 7, "order": 13, "reports_to": "support-dining-oic",
         "summary": "Assistant OIC of Dining Services.",
         "responsibilities": "- Assist Dining OIC\n- Support meal preparation\n- Coordinate serving schedules"},
        {"role_id": "support-health-aoic", "title": "Health Services AOIC", "level": 7, "order": 14, "reports_to": "support-health-oic",
         "summary": "Assistant OIC of Health Services.",
         "responsibilities": "- Assist Health OIC\n- Support medical operations\n- Help with health screenings"},
        
        # ===== LEVEL 7 - Support Squadron Section NCOICs =====
        {"role_id": "support-logistics-ncoic", "title": "Logistics NCOIC", "level": 7, "order": 20, "reports_to": "support-logistics-oic",
         "summary": "NCOIC of Logistics.",
         "responsibilities": "- Lead logistics cadre\n- Supervise daily operations\n- Manage inventory"},
        {"role_id": "support-comms-ncoic", "title": "Communications NCOIC", "level": 7, "order": 21, "reports_to": "support-comms-oic",
         "summary": "NCOIC of Communications.",
         "responsibilities": "- Lead comms cadre\n- Supervise radio watch\n- Maintain signal equipment"},
        {"role_id": "support-pa-ncoic", "title": "Public Affairs NCOIC", "level": 7, "order": 22, "reports_to": "support-pa-oic",
         "summary": "NCOIC of Public Affairs.",
         "responsibilities": "- Lead PA cadre\n- Supervise photo/video team\n- Support media distribution"},
        {"role_id": "support-dining-ncoic", "title": "Dining Services NCOIC", "level": 7, "order": 23, "reports_to": "support-dining-oic",
         "summary": "NCOIC of Dining Services.",
         "responsibilities": "- Lead dining cadre\n- Supervise meal service\n- Maintain facility standards"},
        {"role_id": "support-health-ncoic", "title": "Health Services NCOIC", "level": 7, "order": 24, "reports_to": "support-health-oic",
         "summary": "NCOIC of Health Services.",
         "responsibilities": "- Lead health services cadre\n- Supervise first aid stations\n- Maintain medical supplies"},
        
        # ===== LEVEL 7 - Support Squadron Section Cadre =====
        {"role_id": "support-logistics-cadre", "title": "Logistics Cadre", "level": 7, "order": 30, "reports_to": "support-logistics-oic",
         "summary": "Cadre member for Logistics section.",
         "responsibilities": "- Execute logistics tasks\n- Support supply operations\n- Assist with equipment management"},
        {"role_id": "support-comms-cadre", "title": "Communications Cadre", "level": 7, "order": 31, "reports_to": "support-comms-oic",
         "summary": "Cadre member for Communications section.",
         "responsibilities": "- Execute comms tasks\n- Support radio operations\n- Assist with equipment setup"},
        {"role_id": "support-pa-cadre", "title": "Public Affairs Cadre", "level": 7, "order": 32, "reports_to": "support-pa-oic",
         "summary": "Cadre member for Public Affairs section.",
         "responsibilities": "- Execute PA tasks\n- Support photography\n- Assist with media operations"},
        {"role_id": "support-dining-cadre", "title": "Dining Services Cadre", "level": 7, "order": 33, "reports_to": "support-dining-oic",
         "summary": "Cadre member for Dining Services section.",
         "responsibilities": "- Execute dining tasks\n- Support meal service\n- Assist with facility maintenance"},
        {"role_id": "support-health-cadre", "title": "Health Services Cadre", "level": 7, "order": 34, "reports_to": "support-health-oic",
         "summary": "Cadre member for Health Services section.",
         "responsibilities": "- Execute health services tasks\n- Support medical operations\n- Assist with first aid"},
        
        # ===== LEVEL 7 - Flight Commanders =====
        {"role_id": "alpha-fc", "title": "Flight Commander - Alpha", "level": 7, "order": 0, "reports_to": "sq1-cc",
         "summary": "Commands Alpha Flight.",
         "responsibilities": "- Lead Alpha Flight\n- Conduct formations\n- Supervise Flight Sergeant\n- Evaluate cadets"},
        {"role_id": "bravo-fc", "title": "Flight Commander - Bravo", "level": 7, "order": 1, "reports_to": "sq1-cc",
         "summary": "Commands Bravo Flight.",
         "responsibilities": "- Lead Bravo Flight\n- Conduct formations\n- Supervise Flight Sergeant\n- Evaluate cadets"},
        {"role_id": "charlie-fc", "title": "Flight Commander - Charlie", "level": 7, "order": 2, "reports_to": "sq2-cc",
         "summary": "Commands Charlie Flight.",
         "responsibilities": "- Lead Charlie Flight\n- Conduct formations\n- Supervise Flight Sergeant\n- Evaluate cadets"},
        {"role_id": "delta-fc", "title": "Flight Commander - Delta", "level": 7, "order": 3, "reports_to": "sq2-cc",
         "summary": "Commands Delta Flight.",
         "responsibilities": "- Lead Delta Flight\n- Conduct formations\n- Supervise Flight Sergeant\n- Evaluate cadets"},
        {"role_id": "echo-fc", "title": "Flight Commander - Echo", "level": 7, "order": 4, "reports_to": "sq3-cc",
         "summary": "Commands Echo Flight.",
         "responsibilities": "- Lead Echo Flight\n- Conduct formations\n- Supervise Flight Sergeant\n- Evaluate cadets"},
        {"role_id": "foxtrot-fc", "title": "Flight Commander - Foxtrot", "level": 7, "order": 5, "reports_to": "sq3-cc",
         "summary": "Commands Foxtrot Flight.",
         "responsibilities": "- Lead Foxtrot Flight\n- Conduct formations\n- Supervise Flight Sergeant\n- Evaluate cadets"},
        
        # ===== LEVEL 8 - Flight Sergeants =====
        {"role_id": "alpha-fs", "title": "Flight Sergeant - Alpha", "level": 8, "order": 0, "reports_to": "alpha-fc",
         "summary": "Flight Sergeant for Alpha Flight.",
         "responsibilities": "- Support Flight Commander\n- Lead flight in FC's absence\n- Assist with cadet training"},
        {"role_id": "bravo-fs", "title": "Flight Sergeant - Bravo", "level": 8, "order": 1, "reports_to": "bravo-fc",
         "summary": "Flight Sergeant for Bravo Flight.",
         "responsibilities": "- Support Flight Commander\n- Lead flight in FC's absence\n- Assist with cadet training"},
        {"role_id": "charlie-fs", "title": "Flight Sergeant - Charlie", "level": 8, "order": 2, "reports_to": "charlie-fc",
         "summary": "Flight Sergeant for Charlie Flight.",
         "responsibilities": "- Support Flight Commander\n- Lead flight in FC's absence\n- Assist with cadet training"},
        {"role_id": "delta-fs", "title": "Flight Sergeant - Delta", "level": 8, "order": 3, "reports_to": "delta-fc",
         "summary": "Flight Sergeant for Delta Flight.",
         "responsibilities": "- Support Flight Commander\n- Lead flight in FC's absence\n- Assist with cadet training"},
        {"role_id": "echo-fs", "title": "Flight Sergeant - Echo", "level": 8, "order": 4, "reports_to": "echo-fc",
         "summary": "Flight Sergeant for Echo Flight.",
         "responsibilities": "- Support Flight Commander\n- Lead flight in FC's absence\n- Assist with cadet training"},
        {"role_id": "foxtrot-fs", "title": "Flight Sergeant - Foxtrot", "level": 8, "order": 5, "reports_to": "foxtrot-fc",
         "summary": "Flight Sergeant for Foxtrot Flight.",
         "responsibilities": "- Support Flight Commander\n- Lead flight in FC's absence\n- Assist with cadet training"},
    ]
    
    for role_data in default_roles:
        doc = {
            "id": str(uuid.uuid4()),
            **role_data,
            "assigned_participant_id": None,
            "created_at": now,
            "updated_at": now
        }
        await db.org_chart_roles.insert_one(doc)
    
    return {"message": f"Successfully created {len(default_roles)} default org chart roles"}



