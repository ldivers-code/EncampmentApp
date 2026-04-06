# CAP Encampment Management App — PRD

## Original Problem Statement
Build an interactive roster and management application for a Civil Air Patrol (CAP) encampment titled "Tennessee Wing Civil Air Patrol Encampment".

## Core Features (Implemented)
- **Roster Management**: Interactive roster with live filtering, search, RBAC inline editing, Kanban drag-and-drop, flight-grouped views, cadet contact info, cadet photo uploads
- **Student Upload System**: Excel upload with automatic flight assignment
- **Org Chart**: Hierarchical org chart with rich text, auto-syncing roles, rank-sorted assignment dropdowns (Senior Members vs Cadets)
- **Health Services**: Medical roster tracking allergies, OTC approvals, Parent OTC Medication Permission Form, Parent email notifications for incidents
- **Check-In & Barracks**: Multi-step in-processing, open-bay bunk assignments
- **Granular RBAC**: Complex role-based permissions, dual-assignments, Parent role with admin approval
- **Parent Portal**: "My Cadet" tab with schedule, points/awards, meal plans, OTC form submission, photo upload
- **Budget/Finance Tracker**: Daily payment report imports, smart receipt upload (OCR), Income vs Expenses charts
- **Notifications**: In-app bell notifications
- **Schedule**: Full event scheduling with date navigation, encampment date management, **Excel spreadsheet import** with 11 event categories
- **Analytics**: Participation analytics, flight distribution, age groups
- **Logistics**: Inventory, lost & found, radios, comms, callsigns, vehicles, facilities, supply requests
- **Status Board**: Live-updating display for encampment status

## Tech Stack
- **Frontend**: React 19, Tailwind CSS, Shadcn UI, DOMPurify, Recharts
- **Backend**: FastAPI, MongoDB, openpyxl for Excel parsing
- **Architecture**: Modular FastAPI routes (28+ modules in /backend/routes/)
- **Integrations**: Emergent Object Storage (cadet photos), SendGrid (mocked)

## Code Architecture
```
/app/
├── backend/
│   ├── server.py              # Startup/middleware only (~193 lines)
│   ├── database.py
│   ├── models.py
│   ├── permissions.py
│   ├── file_storage.py        # Emergent Object Storage
│   └── routes/                # 28+ modular route files
│       ├── auth.py, users.py, parent.py, participants.py
│       ├── health_services.py, schedule.py, budget.py
│       ├── photos.py, google_sheets.py
│       ├── otc_permissions.py, flights.py, ...
└── frontend/
    └── src/
        ├── App.js
        ├── components/
        │   ├── health/         # Extracted health dialog components
        │   ├── Sidebar.js, NotificationBell.js, RichTextEditor.js
        ├── pages/
        │   ├── budget/         # Extracted budget tabs
        │   ├── admin/          # Extracted admin tabs
        │   ├── SchedulePage.js # Excel import, 11 event categories
        │   ├── RosterPage.js   # Flight views, photo avatars
        │   ├── OrgChartPage.js # Rank-sorted dropdowns
        │   ├── MyCadetPage.js  # Parent portal
        │   └── ...
        └── services/
            └── api.js
```

## Schedule Event Categories (11 total)
General, Training, Ceremony, Meal, Recreation, PT, Admin, Leadership, Academics, **Aerospace**, **Character**

## Completed Excel Schedule Sync (April 6, 2026)
- Built real multi-sheet Excel parser using openpyxl (replaced hardcoded schedule)
- Parses sheets named by day ('Sat Jun 14' through 'Sat. June 21')
- Maps 2025 dates to 2026 encampment dates (Jun 14→Jul 17, Jun 15→Jul 18, etc.)
- Classifies events using CAP curriculum codes: F=PT, C=Character, A=Aerospace, L=Leadership, X=Admin/Meals
- Filters out task/notes rows, department headers, location sub-labels
- Added Aerospace (bg-sky-600) and Character (bg-rose-600) frontend categories
- 207 events imported across 8 days, re-upload replaces schedule (idempotent)
- Testing: Iteration 50 — 100% pass rate (12/12 backend, all frontend verified)

## Remaining Backlog
### P1 — Code Quality
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
- Emergent Object Storage — uses Emergent LLM Key (implemented for Photo Uploads)
- Smart Receipt OCR — currently MOCKED (simulated string-matching)

## DB Collections
users, participants, budget, receipts, otc_permissions, notifications, schedule, schedule_settings, barracks, health_profiles, org_chart, org_chart_roles, flights, logistics (inventory, lost_found, radios, comms, callsigns, vehicles, facilities, supply_requests), google_sheets_settings
