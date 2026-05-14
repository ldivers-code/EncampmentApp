# CAP Encampment App — PRD & Changelog

## Original Problem Statement
Build an interactive roster & management application for the **Tennessee Wing
Civil Air Patrol Encampment** with:
- Roster Management (live filtering, RBAC, flight-grouped views, contact info)
- Student Upload (Excel) with auto-flight assignment + sub-event handling
- Org Chart (strict 1:1 interactive mind-map)
- Health Services (allergies, OTC approvals, Daily Med Diary, Supplements, Contraband)
- Check-In & Barracks (multi-step in-processing)
- Granular RBAC with visibility / redaction / cascading assignments
- Parent Portal "My Cadet" + Admin widget editor
- Budget/Finance Tracker + Smart Receipt OCR
- Schedule Sync (Excel auto-publish)
- Honor Agreements (digital signature)
- Mobile App back-end ready

## Stack
- React 19, Tailwind, Shadcn UI, DOMPurify, lucide-react
- FastAPI, MongoDB, Python
- emergentintegrations (GPT-4o Vision OCR); SendGrid email
- JWT auth (httpOnly cookie + Bearer header); bcrypt

## Architecture (current)
```
/app/
├── backend/
│   ├── models.py              # Roles, Permissions, ParticipantTypes
│   ├── role_groups.py         # 7-concern separation, semantic groups (Phase 3)
│   ├── scope.py               # Visibility filtering & Redaction rules
│   ├── classifier.py          # Unified RegZone sub-event classifier
│   ├── permissions.py         # JWT, get_current_user, require_role, require_health_*
│   ├── database.py            # Centralized DB logic & participant counts
│   └── routes/                # auth, users, participants, …
└── frontend/src/{pages,components}
```

## Seven Separated Concerns (Phase 3)
1. **Account status** — `users.is_approved`; surfaced by `GET /api/auth/status`
2. **CAP member type** — `participants.member_type` (SENIOR / CADET / CADET SPONSOR)
3. **Encampment participant type** — `participants.participant_type` (`student | cadre | senior_staff | needs_review`)
4. **Cadre role type** — `participants.is_exec_cadre` + `users.cadre_position`
5. **Duty assignment** — `users.flight / squadron / cadre_unit / cadre_position / support_section`
6. **Permission role** — `users.role` (UserRole) grouped via `role_groups.py`
7. **Access scope** — `scope.py` (visibility filter + field redaction)

## Implementation Log
- **Phase 1**: Backend classification audit (canonical taxonomy proposal).
- **Phase 2** (Feb 2026): DB migration — all participants normalized to `student / cadre / senior_staff / needs_review`; added `is_exec_cadre` flag; centralized `get_active_participant_count`; created `scope.py` for visibility/redaction.
- **Phase 3** (Feb 2026): Separated the seven concerns; introduced `role_groups.py`; tightened EXEC_CADRE so it cannot leak into senior-staff capabilities by default; added `cadre_lead_can_target()` guard. 22 unit tests + 9 live RBAC tests passing.
- **Phase 4** (Feb 2026): Approval & participant linking hardened. New `account_status.py` (single source of truth for the six canonical fields). New `get_current_user_linked` dependency. Approve endpoint now tolerates id/email/capid identifiers, returns `matched_by`, structured 404 with `tried` array. Pending-users list now embeds the canonical status block. New `GET /api/users/{id}/status` (admin). 8 new unit tests passing.

## Backlog
- **P0**: Frontend taxonomy sync — replace `basic_student / staff / exec_cadre` literals across ~16 React files with `student / cadre / senior_staff / needs_review`.
- **P0**: Add `is_exec_cadre` toggle on Cadre participant edit UI.
- **P1**: `Needs Review` filter chip + admin resolution flow on Roster page.
- **P1**: Re-publish `MOBILE_BACKEND_INTEGRATION.md` with new ParticipantType vocabulary + the 7-concern model from `role_groups.py`.
- **P2**: Senior Barracks individual room assignments (TR-106, TR-107, TR-105).
- **P2**: Schedule Sync (Excel auto-publish), Honor Agreements digital signature flow.

## Test Credentials
See `/app/memory/test_credentials.md`.
