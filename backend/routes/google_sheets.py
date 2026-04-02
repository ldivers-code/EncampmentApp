"""Google Sheets Sync Endpoints and Service"""
from fastapi import Depends, HTTPException, BackgroundTasks
from typing import Optional
from datetime import datetime, timezone
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import db, api_router
from models import UserRole, GoogleSheetsSyncRequest, GoogleSheetsSettings
from permissions import get_current_user, require_role

# ================= GOOGLE SHEETS SYNC ENDPOINTS =================

@api_router.get("/google-sheets/settings")
async def get_google_sheets_settings(user: dict = Depends(get_current_user)):
    """Get Google Sheets sync settings"""
    if user.get('role') not in ['commander', 'executive_staff', 'plans_programs']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    settings = await db.google_sheets_settings.find_one({'_id': 'settings'})
    if not settings:
        return {
            "roster_sheet": None,
            "org_chart_sheets": [],
            "sync_interval_hours": 1,
            "last_sync_at": None,
            "last_sync_status": None,
            "last_sync_message": None,
            "auto_sync_enabled": True
        }
    
    # Remove MongoDB _id
    settings.pop('_id', None)
    return settings

@api_router.post("/google-sheets/settings")
async def update_google_sheets_settings(
    request: GoogleSheetsSyncRequest,
    user: dict = Depends(get_current_user)
):
    """Update Google Sheets sync settings"""
    if user.get('role') not in ['commander', 'executive_staff', 'plans_programs']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    settings = {
        '_id': 'settings',
        'sync_interval_hours': request.sync_interval_hours,
        'auto_sync_enabled': request.auto_sync_enabled,
    }
    
    if request.roster_spreadsheet_id and request.roster_gid:
        settings['roster_sheet'] = {
            'sheet_type': 'roster',
            'spreadsheet_id': request.roster_spreadsheet_id,
            'gid': request.roster_gid,
            'name': 'Roster',
            'enabled': True
        }
    
    if request.org_chart_spreadsheet_id and request.org_chart_gids:
        settings['org_chart_sheets'] = [
            {
                'sheet_type': 'org_chart',
                'spreadsheet_id': request.org_chart_spreadsheet_id,
                'gid': gid,
                'name': f'Org Chart Tab {i+1}',
                'enabled': True
            }
            for i, gid in enumerate(request.org_chart_gids)
        ]
    
    await db.google_sheets_settings.replace_one(
        {'_id': 'settings'},
        settings,
        upsert=True
    )
    
    return {"message": "Settings updated successfully", "settings": settings}

@api_router.post("/google-sheets/sync")
async def trigger_manual_sync(
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Manually trigger a Google Sheets sync"""
    if user.get('role') not in ['commander', 'executive_staff', 'plans_programs', 'staff']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    settings = await db.google_sheets_settings.find_one({'_id': 'settings'})
    if not settings:
        raise HTTPException(status_code=400, detail="No Google Sheets configured. Please configure sheets first.")
    
    # Run sync in background
    background_tasks.add_task(perform_scheduled_sync)
    
    return {"message": "Sync started. Check status for results."}

@api_router.get("/google-sheets/sync-status")
async def get_sync_status(user: dict = Depends(get_current_user)):
    """Get the current sync status"""
    settings = await db.google_sheets_settings.find_one({'_id': 'settings'})
    if not settings:
        return {
            "configured": False,
            "last_sync_at": None,
            "last_sync_status": None,
            "last_sync_message": None,
            "auto_sync_enabled": False
        }
    
    return {
        "configured": True,
        "last_sync_at": settings.get('last_sync_at'),
        "last_sync_status": settings.get('last_sync_status'),
        "last_sync_message": settings.get('last_sync_message'),
        "auto_sync_enabled": settings.get('auto_sync_enabled', True),
        "sync_interval_hours": settings.get('sync_interval_hours', 1)
    }



# ================= GOOGLE SHEETS SYNC SERVICE =================

# Global scheduler instance
scheduler = AsyncIOScheduler()

async def fetch_google_sheet_csv(spreadsheet_id: str, gid: str) -> Optional[str]:
    """Fetch a Google Sheet as CSV data"""
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                content = response.text
                # Check if it's an error page
                if "Page Not Found" in content or "<!DOCTYPE html>" in content[:100]:
                    logger.error(f"Sheet not accessible: {spreadsheet_id}/{gid}")
                    return None
                return content
            else:
                logger.error(f"Failed to fetch sheet: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Error fetching Google Sheet: {e}")
        return None

async def sync_roster_from_gsheet(spreadsheet_id: str, gid: str) -> dict:
    """Sync roster data from Google Sheet"""
    csv_data = await fetch_google_sheet_csv(spreadsheet_id, gid)
    if not csv_data:
        return {"success": False, "message": "Failed to fetch sheet data"}
    
    try:
        df = pd.read_csv(BytesIO(csv_data.encode('utf-8')))
        df.columns = df.columns.str.strip()
        
        # Column mapping (same as Excel import)
        column_map = {
            'RegistrantsCAPID': 'capid', 'CAPID': 'capid',
            'Rank': 'rank', 'NameLast': 'last_name', 'NameFirst': 'first_name',
            'NameMiddle': 'middle_name', 'Unit': 'unit', 'Wing': 'wing',
            'Region': 'region', 'Gender': 'gender', 'Age': 'age',
            'AgeAtEventStart': 'age_at_event', 'Email': 'email',
            'HomePhonePrimary': 'phone', 'CellPhonePrimary': 'cell_phone',
            'ShirtSize': 'shirt_size', 'MbrType': 'member_type',
            'StaffMember': 'staff_member', 'PaidInFull': 'paid_in_full',
            'AmountPaid': 'amount_paid', 'RegistrationStatus': 'registration_status',
            'UnitApproved': 'unit_approved', 'WingApproved': 'wing_approved',
            'Addr1': 'address', 'City': 'city', 'State': 'state', 'Zip': 'zip_code',
            'EmergencyContactName': 'emergency_contact', 'EmergencyContactNumber': 'emergency_phone',
            'CadetParentPhonePrimary': 'cadet_parent_phone', 'CadetParentEmailPrimary': 'cadet_parent_email',
            'UnitCCName': 'unit_cc_name', 'UnitCCEmail': 'unit_cc_email',
            'LastEncampment': 'last_encampment', 'CPPTExpiration': 'cppt_expiration',
            'FirstAid': 'first_aid', 'SubEvents': 'sub_events',
        }
        
        df = df.rename(columns=column_map)
        
        imported_count = 0
        updated_count = 0
        now = datetime.now(timezone.utc).isoformat()
        
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            
            def get_val(key, default=None):
                val = row_dict.get(key)
                if pd.isna(val) or val == '' or val == 'nan':
                    return default
                return val
            
            def get_str(key, default=''):
                val = get_val(key, default)
                return str(val).strip() if val is not None else default
            
            def get_unit(key, default=''):
                """Get unit value and clean up float formatting (e.g., '96.0' -> '96')"""
                val = get_val(key, default)
                if val is None:
                    return default
                val_str = str(val).strip()
                # Remove .0 suffix if present (from float conversion)
                if val_str.endswith('.0'):
                    val_str = val_str[:-2]
                return val_str
            
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
                except:
                    return default
            
            def get_int(key, default=None):
                val = get_val(key)
                if val is None:
                    return default
                try:
                    return int(float(val))
                except:
                    return default
            
            # Generate CAPID if not present
            capid = get_str('capid', '')
            if not capid:
                email = get_str('email', '')
                if email:
                    email_prefix = email.split('@')[0] if '@' in email else ''
                    numeric_parts = ''.join(filter(str.isdigit, email_prefix))
                    if len(numeric_parts) >= 5:
                        capid = numeric_parts[:6]
                
                if not capid:
                    last_name = get_str('last_name', '')
                    first_name = get_str('first_name', '')
                    wing = get_str('wing', 'XX')
                    unit = get_str('unit', '000')
                    if last_name and first_name:
                        import hashlib
                        composite = f"{last_name}_{first_name}_{wing}_{unit}".upper()
                        hash_digest = hashlib.md5(composite.encode()).hexdigest()[:6]
                        capid = f"GEN{hash_digest.upper()}"
                    else:
                        continue
            
            # Determine participant type
            member_type = get_str('member_type', '').upper()
            is_staff = get_bool('staff_member')
            sub_events = get_str('sub_events', '').lower()
            
            if member_type == 'SENIOR':
                participant_type = 'staff'
            elif 'cadre' in sub_events:
                participant_type = 'cadre'
            else:
                participant_type = 'basic_student'
            
            participant_data = {
                'capid': capid,
                'rank': get_str('rank'),
                'last_name': get_str('last_name'),
                'first_name': get_str('first_name'),
                'middle_name': get_str('middle_name'),
                'name': f"{get_str('last_name')}, {get_str('first_name')}",
                'unit': get_unit('unit'),
                'wing': get_str('wing'),
                'region': get_str('region'),
                'gender': get_str('gender'),
                'age': get_int('age'),
                'age_at_event': get_int('age_at_event'),
                'email': get_str('email'),
                'phone': get_str('phone'),
                'cell_phone': get_str('cell_phone'),
                'shirt_size': get_str('shirt_size'),
                'member_type': member_type,
                'participant_type': participant_type,
                'paid_in_full': get_bool('paid_in_full'),
                'amount_paid': get_float('amount_paid'),
                'paid': get_bool('paid_in_full') or get_float('amount_paid') > 0,
                'registration_status': get_str('registration_status'),
                'staff_member': is_staff,
                'unit_approved': get_bool('unit_approved'),
                'wing_approved': get_bool('wing_approved'),
                'address': get_str('address'),
                'city': get_str('city'),
                'state': get_str('state'),
                'zip_code': get_str('zip_code'),
                'emergency_contact': get_str('emergency_contact'),
                'emergency_phone': get_str('emergency_phone'),
                'cadet_parent_phone': get_str('cadet_parent_phone'),
                'cadet_parent_email': get_str('cadet_parent_email'),
                'unit_cc_name': get_str('unit_cc_name'),
                'unit_cc_email': get_str('unit_cc_email'),
                'last_encampment': get_str('last_encampment'),
                'cppt_expiration': get_str('cppt_expiration'),
                'first_aid': get_str('first_aid'),
                'updated_at': now,
            }
            
            # Upsert by CAPID
            existing = await db.participants.find_one({'capid': capid})
            if existing:
                await db.participants.update_one(
                    {'capid': capid},
                    {'$set': participant_data}
                )
                updated_count += 1
            else:
                participant_data['id'] = str(uuid.uuid4())
                participant_data['created_at'] = now
                participant_data['is_removed'] = False
                await db.participants.insert_one(participant_data)
                imported_count += 1
        
        return {
            "success": True,
            "message": f"Roster sync complete: {imported_count} new, {updated_count} updated",
            "imported": imported_count,
            "updated": updated_count,
            "total": imported_count + updated_count
        }
    
    except Exception as e:
        logger.error(f"Error syncing roster: {e}")
        return {"success": False, "message": str(e)}

async def sync_orgchart_from_gsheet(spreadsheet_id: str, gid: str) -> dict:
    """Sync org chart data from Google Sheet"""
    csv_data = await fetch_google_sheet_csv(spreadsheet_id, gid)
    if not csv_data:
        return {"success": False, "message": "Failed to fetch org chart sheet data"}
    
    try:
        # Parse CSV into rows
        lines = csv_data.strip().split('\n')
        rows = []
        for line in lines:
            # Simple CSV parsing (handles basic cases)
            row = []
            current = ''
            in_quotes = False
            for char in line:
                if char == '"':
                    in_quotes = not in_quotes
                elif char == ',' and not in_quotes:
                    row.append(current.strip())
                    current = ''
                else:
                    current += char
            row.append(current.strip())
            rows.append(row)
        
        now = datetime.now(timezone.utc).isoformat()
        roles_created = 0
        roles_updated = 0
        
        # Define the org chart structure we're looking for
        # Parse key positions from the spreadsheet layout
        org_roles = []
        
        # Helper to parse name and find matching participant
        async def parse_and_match_member(name_str, rank_str=None):
            """Parse name string and try to find matching participant"""
            if not name_str or name_str.strip() == '':
                return None, None, None
            
            # Clean the name string - remove quotes and extra spaces
            name_str = name_str.strip().strip('"').strip()
            if not name_str:
                return None, None, None
                
            # Parse "Last, First" or "Last, First M.I." format
            parts = name_str.split(',')
            if len(parts) >= 2:
                last_name = parts[0].strip()
                first_name = parts[1].strip().split()[0] if parts[1].strip() else ''
            else:
                # Try "First Last" format
                name_parts = name_str.split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = name_parts[-1]
                else:
                    last_name = name_str
                    first_name = ''
            
            # Try to find matching participant
            participant = await db.participants.find_one({
                '$or': [
                    {'last_name': {'$regex': f'^{last_name}', '$options': 'i'}, 'first_name': {'$regex': f'^{first_name}', '$options': 'i'}},
                    {'name': {'$regex': f'{last_name}.*{first_name}', '$options': 'i'}},
                    {'name': {'$regex': f'{first_name}.*{last_name}', '$options': 'i'}}
                ]
            }, {'_id': 0, 'id': 1, 'capid': 1, 'name': 1, 'rank': 1})
            
            participant_id = participant.get('id') if participant else None
            return last_name, first_name, participant_id
        
        # Parse specific positions from known cell locations
        # Row 19 (index 18) has main command staff
        if len(rows) > 19:
            row = rows[18]  # 0-indexed, so row 19 is index 18
            
            # Commandant of Cadets - columns around index 6-10
            if len(row) > 13:
                commandant_rank = row[12] if len(row) > 12 else ''
                commandant_name = row[13] if len(row) > 13 else ''
                if commandant_name:
                    last, first, pid = await parse_and_match_member(commandant_name, commandant_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'commandant',
                            'title': 'Commandant of Cadets',
                            'abbreviation': 'ENC/CW',
                            'category': 'Command',
                            'level': 1,
                            'parent_role_id': 'commander',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': commandant_rank.strip() if commandant_rank else None,
                            'assigned_participant_id': pid
                        })
            
            # Encampment Commander - columns around index 18-22
            if len(row) > 19:
                enc_cc_rank = row[18] if len(row) > 18 else ''
                enc_cc_name = row[19] if len(row) > 19 else ''
                if enc_cc_name:
                    last, first, pid = await parse_and_match_member(enc_cc_name, enc_cc_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'commander',
                            'title': 'Encampment Commander',
                            'abbreviation': 'ENC/CC',
                            'category': 'Command',
                            'level': 0,
                            'parent_role_id': None,
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': enc_cc_rank.strip() if enc_cc_rank else None,
                            'assigned_participant_id': pid
                        })
            
            # Deputy CC for Support - columns around index 24-28
            if len(row) > 25:
                dep_rank = row[24] if len(row) > 24 else ''
                dep_name = row[25] if len(row) > 25 else ''
                if dep_name:
                    last, first, pid = await parse_and_match_member(dep_name, dep_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'deputy_support',
                            'title': 'Deputy CC for Support',
                            'abbreviation': 'ENC/DCS',
                            'category': 'Command',
                            'level': 1,
                            'parent_role_id': 'commander',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': dep_rank.strip() if dep_rank else None,
                            'assigned_participant_id': pid
                        })
        
        # Row 20 has more staff positions
        if len(rows) > 20:
            row = rows[19]
            # 60th CTG/CD
            if len(row) > 13:
                cd_rank = row[12] if len(row) > 12 else ''
                cd_name = row[13] if len(row) > 13 else ''
                if cd_name:
                    last, first, pid = await parse_and_match_member(cd_name, cd_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'ctg_cd',
                            'title': '60th CTG Deputy Commander',
                            'abbreviation': '60th CTG/CD',
                            'category': 'Cadet Training',
                            'level': 2,
                            'parent_role_id': 'commandant',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': cd_rank.strip() if cd_rank else None,
                            'assigned_participant_id': pid
                        })
        
        # Row 21 - ENC Superintendent
        if len(rows) > 21:
            row = rows[20]
            if len(row) > 19:
                sup_rank = row[18] if len(row) > 18 else ''
                sup_name = row[19] if len(row) > 19 else ''
                if sup_name:
                    last, first, pid = await parse_and_match_member(sup_name, sup_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'superintendent',
                            'title': 'Encampment Superintendent',
                            'abbreviation': 'ENC/CCEA',
                            'category': 'Operations',
                            'level': 2,
                            'parent_role_id': 'commander',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': sup_rank.strip() if sup_rank else None,
                            'assigned_participant_id': pid
                        })
        
        # Row 22 - 60th CTG/DOA
        if len(rows) > 22:
            row = rows[21]
            if len(row) > 13:
                doa_rank = row[12] if len(row) > 12 else ''
                doa_name = row[13] if len(row) > 13 else ''
                if doa_name:
                    last, first, pid = await parse_and_match_member(doa_name, doa_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'ctg_doa',
                            'title': '60th CTG Director of Academics',
                            'abbreviation': '60th CTG/DOA',
                            'category': 'Cadet Training',
                            'level': 2,
                            'parent_role_id': 'commandant',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': doa_rank.strip() if doa_rank else None,
                            'assigned_participant_id': pid
                        })
        
        # Row 27 - Health Services Officer
        if len(rows) > 27:
            row = rows[26]
            if len(row) > 19:
                hso_rank = row[18] if len(row) > 18 else ''
                hso_name = row[19] if len(row) > 19 else ''
                if hso_name:
                    last, first, pid = await parse_and_match_member(hso_name, hso_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'health_services',
                            'title': 'Health Services Officer',
                            'abbreviation': 'ENC/HS',
                            'category': 'Support',
                            'level': 2,
                            'parent_role_id': 'deputy_support',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': hso_rank.strip() if hso_rank else None,
                            'assigned_participant_id': pid
                        })
        
        # Parse support staff from column around 24-28 (rows 21-28)
        support_positions = [
            (21, 'support_staff_1', 'Support Staff'),
            (22, 'plans_programs', 'Plans and Programs Officer'),
            (23, 'logistics_1', 'Logistics Officer'),
            (24, 'logistics_2', 'Logistics Officer'),
            (25, 'word_emeritus', 'WORD Officer / HS Emeritus'),
            (26, 'communications', 'Communications Director'),
            (27, 'public_affairs', 'Public Affairs Officer'),
            (28, 'dining_facility', 'Dining Facility Officer'),
            (29, 'finance', 'Finance Officer'),
        ]
        
        for row_idx, role_id, title in support_positions:
            if len(rows) > row_idx:
                row = rows[row_idx - 1]  # Convert to 0-indexed
                if len(row) > 28:
                    supp_rank = row[24] if len(row) > 24 else ''
                    supp_name = row[25] if len(row) > 25 else ''
                    if supp_name and supp_name.strip():
                        last, first, pid = await parse_and_match_member(supp_name, supp_rank)
                        if last:
                            org_roles.append({
                                'role_id': role_id,
                                'title': title,
                                'abbreviation': role_id.upper().replace('_', '/'),
                                'category': 'Support',
                                'level': 3,
                                'parent_role_id': 'deputy_support',
                                'assigned_member_name': f"{last}, {first}" if first else last,
                                'assigned_member_rank': supp_rank.strip() if supp_rank else None,
                                'assigned_participant_id': pid
                            })
        
        # Parse Squadron Commanders from row 35 area
        squadrons = [
            (35, 0, '6th_cts_cc', '6th CTS Commander', '6th CTS/CC', 'commandant'),
            (35, 12, '21st_cts_cc', '21st CTS Commander', '21st CTS/CC', 'commandant'),
            (35, 24, '22nd_cts_cc', '22nd CTS Commander', '22nd CTS/CC', 'commandant'),
        ]
        
        # Parse Flight Sergeants and Commanders from flights row (around row 41)
        flights_row_idx = None
        for idx, row in enumerate(rows):
            if len(row) > 0 and 'ALPHA' in str(row[0]).upper():
                flights_row_idx = idx
                break
        
        if flights_row_idx:
            # Flight names are in this row
            flight_cols = {
                'ALPHA': (0, '6th_cts_cc'),
                'BRAVO': (6, '6th_cts_cc'),
                'CHARLIE': (12, '21st_cts_cc'),
                'DELTA': (18, '21st_cts_cc'),
                'ECHO': (24, '22nd_cts_cc'),
                'FOXTROT': (30, '22nd_cts_cc')
            }
            
            for flight_name, (col_offset, parent_id) in flight_cols.items():
                org_roles.append({
                    'role_id': f'flight_{flight_name.lower()}_commander',
                    'title': f'{flight_name} Flight Commander',
                    'abbreviation': f'{flight_name[:1]}FLT/CC',
                    'category': 'Flight',
                    'level': 4,
                    'parent_role_id': parent_id,
                    'assigned_member_name': None,
                    'assigned_member_rank': None,
                    'assigned_participant_id': None
                })
                org_roles.append({
                    'role_id': f'flight_{flight_name.lower()}_sergeant',
                    'title': f'{flight_name} Flight Sergeant',
                    'abbreviation': f'{flight_name[:1]}FLT/FS',
                    'category': 'Flight',
                    'level': 4,
                    'parent_role_id': f'flight_{flight_name.lower()}_commander',
                    'assigned_member_name': None,
                    'assigned_member_rank': None,
                    'assigned_participant_id': None
                })
        
        # Now upsert all roles to the database
        for role_data in org_roles:
            role_id = role_data['role_id']
            existing = await db.org_chart_roles.find_one({'role_id': role_id})
            
            if existing:
                await db.org_chart_roles.update_one(
                    {'role_id': role_id},
                    {'$set': {
                        'assigned_member_name': role_data.get('assigned_member_name'),
                        'assigned_member_rank': role_data.get('assigned_member_rank'),
                        'assigned_participant_id': role_data.get('assigned_participant_id'),
                        'updated_at': now
                    }}
                )
                roles_updated += 1
            else:
                role_data['id'] = str(uuid.uuid4())
                role_data['responsibilities'] = ''
                role_data['created_at'] = now
                role_data['updated_at'] = now
                await db.org_chart_roles.insert_one(role_data)
                roles_created += 1
        
        # ================= PARSE FLIGHT ASSIGNMENTS =================
        # Find the row with flight headers (ALPHA, BRAVO, etc.)
        flights_header_idx = None
        for idx, row in enumerate(rows):
            if len(row) > 0 and 'ALPHA' in str(row[0]).upper():
                flights_header_idx = idx
                break
        
        students_assigned = 0
        if flights_header_idx is not None:
            # Flight column positions (each flight spans ~6 columns)
            # Based on the spreadsheet: ALPHA(0-5), BRAVO(6-11), CHARLIE(12-17), DELTA(18-23), ECHO(24-29), FOXTROT(30-35)
            flight_config = {
                'Alpha': {'col_offset': 0, 'squadron': '6th CTS', 'squadron_full': '6th Cadet Training Squadron'},
                'Bravo': {'col_offset': 6, 'squadron': '6th CTS', 'squadron_full': '6th Cadet Training Squadron'},
                'Charlie': {'col_offset': 12, 'squadron': '21st CTS', 'squadron_full': '21st Cadet Training Squadron'},
                'Delta': {'col_offset': 18, 'squadron': '21st CTS', 'squadron_full': '21st Cadet Training Squadron'},
                'Echo': {'col_offset': 24, 'squadron': '22nd CTS', 'squadron_full': '22nd Cadet Training Squadron'},
                'Foxtrot': {'col_offset': 30, 'squadron': '22nd CTS', 'squadron_full': '22nd Cadet Training Squadron'},
            }
            
            # Skip header row (GRADE, LAST NAME...) and start from data rows (2 rows after ALPHA header)
            data_start_idx = flights_header_idx + 2
            
            # Parse each row until we hit "Total Cadets" or empty rows
            for row_idx in range(data_start_idx, len(rows)):
                row = rows[row_idx]
                
                # Check if we've reached the end (Total Cadets row)
                row_str = ','.join(row).lower()
                if 'total cadets' in row_str:
                    break
                
                # Process each flight column
                for flight_name, config in flight_config.items():
                    col = config['col_offset']
                    
                    # Get rank/grade (col+0), name (col+1), age (col+2), unit (col+3)
                    if len(row) > col + 3:
                        rank = row[col].strip() if row[col] else ''
                        name = row[col + 1].strip() if len(row) > col + 1 else ''
                        age_str = row[col + 2].strip() if len(row) > col + 2 else ''
                        unit = row[col + 3].strip() if len(row) > col + 3 else ''
                        
                        # Skip empty entries
                        if not name or name == '':
                            continue
                        
                        # Parse name (format: "LAST, FIRST M.I.")
                        name = name.strip().strip('"')
                        name_parts = name.split(',')
                        if len(name_parts) >= 2:
                            last_name = name_parts[0].strip()
                            first_part = name_parts[1].strip()
                            first_name = first_part.split()[0] if first_part else ''
                        else:
                            continue
                        
                        # Try to find matching participant in the roster
                        participant = await db.participants.find_one({
                            '$or': [
                                {'last_name': {'$regex': f'^{last_name}$', '$options': 'i'}, 
                                 'first_name': {'$regex': f'^{first_name}', '$options': 'i'}},
                                {'name': {'$regex': f'{last_name}.*{first_name}', '$options': 'i'}},
                            ]
                        })
                        
                        if participant:
                            # Update participant with flight and squadron assignment
                            await db.participants.update_one(
                                {'_id': participant['_id']},
                                {'$set': {
                                    'flight': flight_name,
                                    'squadron': config['squadron'],
                                    'squadron_full': config['squadron_full'],
                                    'participant_type': 'basic_student',
                                    'updated_at': now
                                }}
                            )
                            students_assigned += 1
                            logger.info(f"Assigned {last_name}, {first_name} to {flight_name} Flight ({config['squadron']})")
        
        return {
            "success": True,
            "message": f"Org chart sync complete: {roles_created} new roles, {roles_updated} updated, {students_assigned} students assigned to flights",
            "created": roles_created,
            "updated": roles_updated,
            "students_assigned": students_assigned,
            "total": roles_created + roles_updated
        }
    
    except Exception as e:
        logger.error(f"Error syncing org chart: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"success": False, "message": str(e)}

async def perform_scheduled_sync():
    """Perform scheduled sync of all configured sheets"""
    logger.info("Starting scheduled Google Sheets sync...")
    
    settings = await db.google_sheets_settings.find_one({'_id': 'settings'})
    if not settings:
        logger.info("No Google Sheets settings configured, skipping sync")
        return
    
    if not settings.get('auto_sync_enabled', True):
        logger.info("Auto sync is disabled, skipping")
        return
    
    # Update status to running
    await db.google_sheets_settings.update_one(
        {'_id': 'settings'},
        {'$set': {'last_sync_status': 'running', 'last_sync_message': 'Sync in progress...'}}
    )
    
    try:
        results = []
        
        # Sync roster sheet
        roster_config = settings.get('roster_sheet')
        if roster_config and roster_config.get('enabled'):
            roster_result = await sync_roster_from_gsheet(
                roster_config['spreadsheet_id'],
                roster_config['gid']
            )
            results.append(f"Roster: {roster_result.get('message', 'unknown')}")
        
        # Sync org chart sheets
        org_chart_sheets = settings.get('org_chart_sheets', [])
        for org_config in org_chart_sheets:
            if org_config and org_config.get('enabled'):
                org_result = await sync_orgchart_from_gsheet(
                    org_config['spreadsheet_id'],
                    org_config['gid']
                )
                results.append(f"Org Chart: {org_result.get('message', 'unknown')}")
        
        # Update success status
        now = datetime.now(timezone.utc).isoformat()
        await db.google_sheets_settings.update_one(
            {'_id': 'settings'},
            {'$set': {
                'last_sync_at': now,
                'last_sync_status': 'success',
                'last_sync_message': '; '.join(results) if results else 'No sheets configured'
            }}
        )
        logger.info(f"Scheduled sync completed: {results}")
        
    except Exception as e:
        logger.error(f"Scheduled sync failed: {e}")
        await db.google_sheets_settings.update_one(
            {'_id': 'settings'},
            {'$set': {
                'last_sync_at': datetime.now(timezone.utc).isoformat(),
                'last_sync_status': 'error',
                'last_sync_message': str(e)
            }}
        )



