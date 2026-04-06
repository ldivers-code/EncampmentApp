# CAP Encampment Management App — PRD

## Original Problem Statement
Build an interactive roster and management application for a Civil Air Patrol (CAP) encampment titled "Tennessee Wing Civil Air Patrol Encampment".

## Core Features (Implemented)
- **Roster Management**: Interactive roster with live filtering, search, RBAC inline editing, Kanban drag-and-drop, flight-grouped views, cadet contact info
- **Student Upload System**: Excel upload with automatic flight assignment
- **Org Chart**: Hierarchical org chart with rich text, auto-syncing roles for Squadron/Flight leadership
- **Health Services**: Medical roster tracking allergies, OTC approvals, Parent OTC Medication Permission Form, Parent email notifications for incidents
- **Check-In & Barracks**: Multi-step in-processing, open-bay bunk assignments
- **Granular RBAC**: Complex role-based permissions, dual-assignments, Parent role with admin approval
- **Parent Portal**: "My Cadet" tab with schedule, points/awards, meal plans, OTC form submission
- **Budget/Finance Tracker**: Daily payment report imports, smart receipt upload (OCR), Income vs Expenses charts
- **Notifications**: In-app bell notifications
- **Schedule**: Full event scheduling with date navigation and encampment date management
- **Analytics**: Participation analytics, flight distribution, age groups
- **Logistics**: Inventory, lost & found, radios, comms, callsigns, vehicles, facilities, supply requests
- **Status Board**: Live-updating display for encampment status

## Tech Stack
- **Frontend**: React 19, Tailwind CSS, Shadcn UI, DOMPurify, Recharts
- **Backend**: FastAPI, MongoDB, python-dateutil
- **Architecture**: Modular FastAPI routes (28 modules in /backend/routes/)

## Code Architecture (Updated April 2026)
```
/app/
├── backend/
│   ├── server.py              # Startup/middleware only (~193 lines)
│   ├── database.py
│   ├── models.py
│   ├── permissions.py
│   ├── logistics.py           # Fixed lint (27 issues resolved)
│   └── routes/                # 28 modular route files
│       ├── auth.py, users.py, parent.py, participants.py
│       ├── health_services.py, schedule.py, budget.py
│       ├── otc_permissions.py, flights.py, ...
└── frontend/
    └── src/
        ├── App.js
        ├── components/
        │   ├── CadetHealthSection.js    # 676 lines (was 1129)
        │   ├── health/                   # NEW: Extracted dialogs
        │   │   ├── MedicationFormDialog.js
        │   │   ├── AdminLogFormDialog.js
        │   │   ├── IncidentFormDialog.js
        │   │   └── CustodyFormDialog.js
        │   ├── Sidebar.js, NotificationBell.js, RichTextEditor.js
        ├── pages/
        │   ├── BudgetPage.js            # 1410 lines (was 1947)
        │   ├── budget/                   # NEW: Extracted tabs
        │   │   ├── PaymentReportsTab.js
        │   │   ├── SmartReceiptTab.js
        │   │   └── ReceiptRepositoryTab.js
        │   ├── AdminPage.js             # 1006 lines (was 1274)
        │   ├── admin/                    # NEW: Extracted tab
        │   │   └── AdminSettingsTab.js
        │   ├── HealthServicesDashboard.js, SchedulePage.js
        │   ├── RosterPage.js, MyCadetPage.js, MyFlightPage.js
        │   └── ...
        └── services/
            └── api.js
```

## Completed Code Quality Work (April 3, 2026)
- Fixed 11 array index keys across HealthServicesDashboard, SchedulePage, MyFlightPage
- Fixed hook dependencies in SchedulePage, TrainingOfficerPage
- Removed dead useEffect in SchedulePage
- Extracted BudgetPage into 3 sub-components (-537 lines)
- Extracted AdminPage Settings tab into AdminSettingsTab (-268 lines)
- Extracted CadetHealthSection into 4 dialog sub-components (-453 lines)
- Fixed 27 backend lint issues in logistics.py (one-liners, bare excepts)
- Fixed f-string without placeholders in budget.py
- Cleaned up unused imports in CadetHealthSection

## Completed Org Chart Rank Sorting (April 6, 2026)
- Assignment dropdown now groups participants into "Senior Members" and "Cadets" sections
- Each group sorted by CAP rank order (Maj > SMSgt > TSgt for seniors; C/Maj > C/Capt > C/1stLt for cadets)
- Within same rank, sorted alphabetically by last name
- Vacant option remains at top

## Completed Cadet Photo Feature (April 6, 2026)
- Parents, Commanders, Staff, and roster editors can upload cadet photos
- Photos stored via Emergent Object Storage (real, not mocked)
- Small avatar thumbnails in roster table view and By Flight grouped view
- Larger avatar in cadet detail modal with hover-to-upload overlay
- Parents upload from "My Cadet" header section
- Backend: POST/GET/DELETE /api/participants/{id}/photo
- GET supports ?auth=token query param for img src tags
- File validation: JPEG, PNG, WEBP, HEIC/HEIF, max 5MB

## Remaining Backlog
### P1 — Code Quality (Lower Priority)
- Insecure token storage (localStorage → httpOnly cookies or memory)
- Hardcoded test secrets in Python test files → use env vars/fixtures

### P2 — Features
- Attendance tracking per event
- Senior Barracks (TR-106, TR-107, TR-105) individual room assignments

### P3 — Future
- Bulk auto-balance flight distribution button
- Print-friendly roster and org chart views

## 3rd Party Integrations
- SendGrid (Email) — requires user API key, currently MOCKED
- Emergent Object Storage — uses Emergent LLM Key
- Smart Receipt OCR — currently MOCKED (simulated string-matching)

## DB Collections
users, participants, budget, receipts, otc_permissions, notifications, schedule, barracks, health_profiles, org_chart, flights, logistics (inventory, lost_found, radios, comms, callsigns, vehicles, facilities, supply_requests)
