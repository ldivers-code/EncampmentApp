# CAP Encampment Management App — PRD

## Original Problem Statement
Build an interactive roster and management application for a Civil Air Patrol (CAP) encampment titled "Tennessee Wing Civil Air Patrol Encampment".

## Core Features (Implemented)
- **Roster Management**: Interactive roster with live filtering, search, RBAC, flight-grouped views, photo uploads, auto-balance, print-friendly. Bulk-select, bulk-change-type, bulk-delete, Excel export with shirt sizes.
- **Assignments System (Google Classroom-style)**: Instructor/mentor/student roles, Q&A, document uploads, grading, email reminders
- **Student Upload System**: Excel upload with automatic flight assignment. Supports CAP Master Reports (uses `SubEvents` column) and sub-event reports; falls back to Name matching when CAPID is missing.
- **Org Chart**: Interactive SVG node-link command map with horizontal branching, 85 positions. Hierarchy: Enc Commander → Commandant → CTG/CC → [CTG/CD, CTG/DF, CTG/CCEA, CSS/CC, CTO + 3 Squadrons]. Squadron TOs under CTO. 19 positions with secondary academic reporting to CTG/DF (dashed connectors). 5-color scheme: Blue/Maroon/Yellow/Emerald/Silver. Collapsible depth, search, category filters, detail side panel.
- **Health Services**: Medical roster, allergies, OTC approvals, parent email notifications, Daily Med Diary, Supplements, Contraband check-in
- **Check-In & Barracks**: Multi-step in-processing, bunk assignments
- **Granular RBAC**: Senior Staff + Cadre roles with permissions
- **Parent Portal**: "My Cadet" tab, Admin widget editor
- **Honor Agreement System**: Role-based digital agreements, blocking modal
- **Budget/Finance Tracker**: Payment imports, smart receipt OCR (GPT-4o Vision), charts
- **Schedule**: 11 categories, Excel import, Squadron View grid
- **Analytics, Logistics, Status Board, Notifications**
- **Annual Reset Tab**: bulk roster/org chart wipe in Admin settings
- **Auth**: httpOnly cookie-based JWT
- **Mobile App API Spec**: `/app/MOBILE_BACKEND_INTEGRATION.md` documents endpoints for companion mobile app

## Auto-Balance Flights Algorithm
`POST /api/students/auto-assign` distributes unassigned students using weighted scoring:
- Capacity (max 15/flight, weight 10)
- Male/Female parity (weight 5)
- Wing spread (weight 3)
- Home unit spread (weight 3)
- Age tier balance (weight 2)
Existing flight assignments are NEVER overwritten.

## Bulk Action Endpoints (Roster)
- `PUT /api/participants/bulk-type` — change participant_type for multiple IDs (basic_student / advanced_student / cadre / staff / senior_member). Roles: DCP, COMMANDER, EXECUTIVE_STAFF, STAFF.
- `POST /api/participants/bulk-delete` — permanently delete with `confirm:true`. Cleans related health/contraband/supplements records and unlinks user accounts. Roles: DCP, COMMANDER, EXECUTIVE_STAFF.
- `PUT /api/participants/bulk-assignment` — bulk update Flight and/or Squadron. Pass empty/None to clear, omit field to leave unchanged. Roles: DCP, COMMANDER, EXECUTIVE_STAFF, STAFF.
- These literal-path routes are registered BEFORE `PUT /participants/{participant_id}` to avoid FastAPI route shadowing.

## Tech Stack
- Frontend: React 19, Tailwind CSS, Shadcn UI, DOMPurify
- Backend: FastAPI, MongoDB, openpyxl, reportlab
- Integrations: SendGrid (LIVE), Emergent Object Storage, GPT-4o Vision (receipt OCR via emergentintegrations)

## Completed Work Log
- **Apr 6-9**: Core features, Excel sync, RBAC, Honor Agreements
- **Apr 10**: Google Classroom-style Assignments. 100% tests.
- **Apr 11**: SendGrid live. Lillian Yoder account synced.
- **Apr 14**: Mobile responsiveness. Org Chart V1/V2/V3 (TOs under CTO, 19 secondary academic reports, 5-color scheme).
- **May**: Smart Receipt OCR (GPT-4o Vision), Annual Reset, sidebar nav editing, code-quality fixes (XSS DOMPurify, removed hardcoded secrets across 11 files), My Flight chain-of-command.
- **Feb 6, 2026**: Roster Bulk Actions UI complete (checkbox column, select-all, bulk-type-change menu, bulk-delete, Excel-with-shirt-size export). Fixed FastAPI route ordering bug (bulk-type was shadowed by /{participant_id}). 100% backend + 100% frontend tests (iteration_63).
- **Feb 6, 2026 (later)**: Added **Bulk Edit Flight / Squadron** dialog (`PUT /api/participants/bulk-assignment`) and extended Change Type menu with **Senior Member** and **Advanced Student**. Backend validates flight/squadron values, supports clear-to-None and partial updates. 5/5 curl tests pass.

## Remaining Backlog
- P1: Senior Barracks (TR-106, TR-107, TR-105) individual room assignments
- P3 (Optional cleanup): Resolve React hydration warnings on roster `<table>` (ve-dynamic `<span>` wrappers around `<th>/<tr>/<td>/<tbody>`)
- P3 (Optional refactor): Split RosterPage.js (~2400 lines) into RosterTable, RosterFilters, RosterToolbar, RosterBulkActions sub-components
