# CAP Encampment Management App — PRD

## Original Problem Statement
Build an interactive roster and management application for a Civil Air Patrol (CAP) encampment titled "Tennessee Wing Civil Air Patrol Encampment".

## Core Features (Implemented)
- **Roster Management**: Interactive roster with live filtering, search, RBAC inline editing, Kanban drag-and-drop, flight-grouped views, cadet contact info, cadet photo uploads, auto-balance flight distribution, print-friendly layout
- **Assignments System (Google Classroom-style)**: Create assignments with instructor/mentor/student roles, squadron and flight targeting, Q&A questions with text answers, material document uploads, rubric-based grading, text+file submissions, in-app + email reminders, full-page detail view with Instructions/Submissions/People tabs
- **Student Upload System**: Excel upload with automatic flight assignment
- **Org Chart**: Strict 1:1 dataset-driven interactive mind-map tree from TNWG ENC26 spreadsheet. 86 positions with expand/collapse, 7 color-coded categories (Senior Member, Executive Cadre, Training Cadre, Support Cadre, Operations Cadre, Female Cadre, Out of TNWG Cadre), detail side panel on click, search, edit/delete, add position, reseed functionality
- **Health Services**: Medical roster tracking allergies, OTC approvals, Parent OTC Medication Permission Form, Parent email notifications for incidents
- **Check-In & Barracks**: Multi-step in-processing, open-bay bunk assignments
- **Granular RBAC**: Senior Staff roles (DCP, Commander, Exec Staff, Training Officer, Health Services, Finance, Dining Facility) separate from Cadre roles (Cadre, Exec Cadre). Cadre assign to Ops or Support sections. Parent role with admin approval.
- **Parent Portal**: "My Cadet" tab for parents. Admin preview mode for senior staff with widget editor.
- **Honor Agreement System**: Role-based digital honor agreements. Blocking modal on login until signed.
- **Budget/Finance Tracker**: Daily payment report imports, smart receipt upload (OCR via GPT-4o), Income vs Expenses charts
- **Meal Plan Schedule**: Period-based meal planning
- **Notifications**: In-app bell notifications
- **Schedule**: Full event scheduling with 11 categories, Excel import, Squadron View grid
- **Analytics**: Participation analytics, flight distribution, age groups
- **Logistics**: Inventory, lost & found, radios, comms, callsigns, vehicles, facilities, supply requests
- **Status Board**: Live-updating display
- **Auth Security**: httpOnly cookie-based JWT authentication
- **Admin Page**: User management with role/unit assignment

## Tech Stack
- **Frontend**: React 19, Tailwind CSS, Shadcn UI, DOMPurify, Recharts
- **Backend**: FastAPI, MongoDB, openpyxl for Excel parsing
- **Architecture**: Modular FastAPI routes (29+ modules in /backend/routes/)
- **Auth**: httpOnly cookies (primary) + Bearer header + query param
- **Integrations**: Emergent Object Storage, SendGrid (LIVE), GPT-4o (receipt OCR)

## Code Architecture
```
/app/
├── backend/
│   ├── server.py
│   ├── database.py
│   ├── models.py           # OrgChartRoleBase with position_title, assigned_name, role_category, etc.
│   ├── permissions.py
│   ├── file_storage.py
│   ├── seed_orgchart.py    # 86 positions from TNWG ENC26 spreadsheet
│   ├── tests/
│   │   ├── test_orgchart.py
│   │   └── ...
│   └── routes/
│       ├── orgchart.py     # CRUD + seed/reseed endpoints
│       ├── assignments.py
│       ├── auth.py
│       ├── budget.py
│       ├── participants.py
│       └── ...
└── frontend/
    └── src/
        ├── pages/
        │   ├── OrgChartPage.js  # Interactive mind-map tree with TreeNode recursive component
        │   └── ...
        └── services/api.js
```

## Completed Work Log
- **Apr 6**: Excel Schedule Sync, Secure Token Storage, Test Secrets Cleanup, Auto-Balance Flights, Print-Friendly Views
- **Apr 7**: Assignments System (CRUD, rubric grading, submissions, reminders)
- **Apr 9**: Admin RBAC, Meal Plan periods, Honor Agreement System, Squadron Schedule View
- **Apr 10**: Google Classroom-style Assignments overhaul. 100% test pass rate.
- **Apr 11**: SendGrid API key integration (live emails). Lillian Yoder account synced.
- **Apr 14**: Mobile responsiveness audit & fixes across all pages.
- **Apr 14**: Org Chart complete rebuild — strict 1:1 spreadsheet data mapping, 86 positions, interactive mind-map tree with expand/collapse, detail panel, color-coded categories, search, CRUD. 100% test pass rate (iteration 59).

## Remaining Backlog
- P1: Senior Barracks (TR-106, TR-107, TR-105) individual room assignments
- P2: Receipt Scanning (OCR) for the financial module (uses Emergent LLM Key)
- P3: Bulk auto-balance button for flight distribution

## 3rd Party Integrations
- SendGrid (Email) — LIVE with user API key (tnwgencampment@tncap.us)
- Emergent Object Storage — uses Emergent LLM Key (photos + assignment files)
- GPT-4o via Emergent Integrations — receipt OCR (uses EMERGENT_LLM_KEY)
