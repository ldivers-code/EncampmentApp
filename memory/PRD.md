# CAP Encampment Management App — PRD

## Original Problem Statement
Build an interactive roster and management application for a Civil Air Patrol (CAP) encampment titled "Tennessee Wing Civil Air Patrol Encampment".

## Core Features (Implemented)
- **Roster Management**: Interactive roster with live filtering, search, RBAC inline editing, Kanban drag-and-drop, flight-grouped views, cadet contact info, cadet photo uploads, **auto-balance flight distribution**, **print-friendly layout**
- **Student Upload System**: Excel upload with automatic flight assignment
- **Org Chart**: Hierarchical org chart with rich text, auto-syncing roles, rank-sorted assignment dropdowns, **print-friendly layout**
- **Health Services**: Medical roster tracking allergies, OTC approvals, Parent OTC Medication Permission Form, Parent email notifications for incidents
- **Check-In & Barracks**: Multi-step in-processing, open-bay bunk assignments
- **Granular RBAC**: Complex role-based permissions, dual-assignments, Parent role with admin approval
- **Parent Portal**: "My Cadet" tab with schedule, points/awards, meal plans, OTC form submission, photo upload
- **Budget/Finance Tracker**: Daily payment report imports, smart receipt upload (OCR), Income vs Expenses charts
- **Notifications**: In-app bell notifications
- **Schedule**: Full event scheduling with 11 categories (including Aerospace & Character), Excel multi-sheet import with date mapping
- **Analytics**: Participation analytics, flight distribution, age groups
- **Logistics**: Inventory, lost & found, radios, comms, callsigns, vehicles, facilities, supply requests
- **Status Board**: Live-updating display for encampment status
- **Auth Security**: **httpOnly cookie-based JWT authentication** (migrated from localStorage)

## Tech Stack
- **Frontend**: React 19, Tailwind CSS, Shadcn UI, DOMPurify, Recharts
- **Backend**: FastAPI, MongoDB, openpyxl for Excel parsing
- **Architecture**: Modular FastAPI routes (28+ modules in /backend/routes/)
- **Auth**: httpOnly cookies (primary) + Bearer header (backward compat) + query param (?auth= for img tags)
- **Integrations**: Emergent Object Storage (cadet photos), SendGrid (mocked)

## Code Architecture
```
/app/
├── backend/
│   ├── server.py              # Startup/middleware only (~193 lines)
│   ├── database.py            # HTTPBearer(auto_error=False)
│   ├── models.py
│   ├── permissions.py         # Cookie + header + query param auth
│   ├── file_storage.py
│   ├── tests/
│   │   ├── conftest.py        # Shared test credentials from env vars
│   │   └── test_*.py          # All using conftest imports
│   └── routes/                # 28+ modular route files
│       ├── auth.py            # Sets/clears httpOnly cookies
│       ├── photos.py          # Cookie-aware photo serving
│       ├── schedule.py        # Real Excel parser with openpyxl
│       └── ...
└── frontend/
    └── src/
        ├── App.js
        ├── styles/print.css   # Print-specific stylesheet
        ├── context/AuthContext.js  # Cookie-based, no localStorage
        ├── services/api.js        # withCredentials: true
        ├── pages/
        │   ├── RosterPage.js      # Auto-Balance + Print buttons
        │   ├── OrgChartPage.js    # Print button
        │   └── ...
```

## Schedule Event Categories (11 total)
General, Training, Ceremony, Meal, Recreation, PT, Admin, Leadership, Academics, Aerospace, Character

## Completed Work Log
- **Apr 6, 2026**: Excel Schedule Sync — real multi-sheet parser, Aerospace & Character categories (Test: Iteration 50 - 100%)
- **Apr 6, 2026**: Secure Token Storage — httpOnly cookie auth migration, removed all localStorage refs (Test: Iteration 51 - 100%)
- **Apr 6, 2026**: Test Secrets Cleanup — conftest.py with env-based credentials across all test files
- **Apr 6, 2026**: Auto-Balance Flights — button distributes unassigned students (Test: Iteration 51 - 100%)
- **Apr 6, 2026**: Print-Friendly Views — CSS print stylesheet, print buttons on Roster & Org Chart (Test: Iteration 51 - 100%)

## Remaining Backlog
- Attendance tracking per event (user said not needed)
- Senior Barracks individual room assignments (user said cadets only)
- Any other user-requested features

## 3rd Party Integrations
- SendGrid (Email) — requires user API key, currently MOCKED
- Emergent Object Storage — uses Emergent LLM Key (implemented for Photo Uploads)
