# CAP Encampment Management App — PRD

## Original Problem Statement
Build an interactive roster and management application for a Civil Air Patrol (CAP) encampment titled "Tennessee Wing Civil Air Patrol Encampment".

## Core Features (Implemented)
- **Roster Management**: Interactive roster with live filtering, search, RBAC inline editing, Kanban drag-and-drop, flight-grouped views, cadet contact info, cadet photo uploads, auto-balance flight distribution, print-friendly layout
- **Assignments System**: Create assignments with rubric-based grading criteria, text+file submissions, rubric-based grading by Exec Cadre, in-app + email reminders for non-submitters, per-flight and individual targeting
- **Student Upload System**: Excel upload with automatic flight assignment
- **Org Chart**: Hierarchical org chart with rich text, auto-syncing roles, rank-sorted assignment dropdowns, print-friendly layout
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
- **Auth Security**: httpOnly cookie-based JWT authentication

## Tech Stack
- **Frontend**: React 19, Tailwind CSS, Shadcn UI, DOMPurify, Recharts
- **Backend**: FastAPI, MongoDB, openpyxl for Excel parsing
- **Architecture**: Modular FastAPI routes (29+ modules in /backend/routes/)
- **Auth**: httpOnly cookies (primary) + Bearer header (backward compat) + query param (?auth= for img tags)
- **Integrations**: Emergent Object Storage (cadet photos, assignment file uploads), SendGrid (mocked)

## Assignments System Details
- **Creators**: Exec Cadre, Executive Staff, Training Officers, Commander, DCP
- **Graders**: Exec Cadre, Executive Staff, Commander, DCP
- **Submissions**: Text responses + optional file uploads (stored via Emergent Object Storage)
- **Grading**: Rubric-based — multiple criteria with individual point values, total auto-calculated
- **Reminders**: In-app notifications + email (SendGrid, currently mocked)
- **Targeting**: All cadre, specific flights, or individual users
- **Collections**: `assignments`, `assignment_submissions`

## Code Architecture
```
/app/
├── backend/
│   ├── server.py
│   ├── database.py
│   ├── models.py
│   ├── permissions.py
│   ├── file_storage.py
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_*.py
│   └── routes/
│       ├── assignments.py     # NEW: Full CRUD, submissions, grading, reminders
│       ├── auth.py
│       ├── photos.py
│       ├── schedule.py
│       └── ...
└── frontend/
    └── src/
        ├── App.js
        ├── styles/print.css
        ├── context/AuthContext.js
        ├── services/api.js
        ├── components/Sidebar.js
        ├── pages/
        │   ├── AssignmentsPage.js  # NEW: Create, Submit, Detail, Grade dialogs
        │   ├── RosterPage.js
        │   ├── OrgChartPage.js
        │   └── ...
```

## Completed Work Log
- **Apr 6**: Excel Schedule Sync, Secure Token Storage, Test Secrets Cleanup, Auto-Balance Flights, Print-Friendly Views
- **Apr 7**: Assignments System (CRUD, rubric grading, submissions, reminders)

## Remaining Backlog
- SendGrid API key integration (currently mocked for emails/reminders)
- Any additional user-requested features

## 3rd Party Integrations
- SendGrid (Email) — requires user API key, currently MOCKED
- Emergent Object Storage — uses Emergent LLM Key (photos + assignment files)
