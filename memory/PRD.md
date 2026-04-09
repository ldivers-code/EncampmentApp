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
- **Granular RBAC**: Complex role-based permissions, dual-assignments, Parent role with admin approval, Exec Cadre delegated admin access (role assignment only)
- **Parent Portal**: "My Cadet" tab with schedule, points/awards, meal plans, OTC form submission, photo upload
- **Honor Agreement System**: Role-based digital honor agreements (Cadre Honor Agreement for cadre/exec_cadre, Senior Staff Honor Agreement for all staff roles). Blocking modal on login until signed. Scroll-to-unlock signature mechanism. Admin can send in-app reminders to unsigned members.
- **Budget/Finance Tracker**: Daily payment report imports, smart receipt upload (OCR via GPT-4o), Income vs Expenses charts
- **Meal Plan Schedule**: Period-based meal planning for Cadre & Staff Training Weekend (May 29-30, 2026) and Encampment (Jul 17-24, 2026)
- **Notifications**: In-app bell notifications
- **Schedule**: Full event scheduling with 11 categories (including Aerospace & Character), Excel multi-sheet import with date mapping, Squadron View (multi-column grid showing 6th/21st/22nd CTS flights and 16th OPS SUP side-by-side, color-coded)
- **Analytics**: Participation analytics, flight distribution, age groups
- **Logistics**: Inventory, lost & found, radios, comms, callsigns, vehicles, facilities, supply requests
- **Status Board**: Live-updating display for encampment status
- **Auth Security**: httpOnly cookie-based JWT authentication
- **Admin Page**: User management with role/unit assignment, grouped by Staff/Cadre/Parent with alphabetical sorting, Exec Cadre restricted view

## Tech Stack
- **Frontend**: React 19, Tailwind CSS, Shadcn UI, DOMPurify, Recharts
- **Backend**: FastAPI, MongoDB, openpyxl for Excel parsing
- **Architecture**: Modular FastAPI routes (29+ modules in /backend/routes/)
- **Auth**: httpOnly cookies (primary) + Bearer header (backward compat) + query param (?auth= for img tags)
- **Integrations**: Emergent Object Storage (cadet photos, assignment file uploads), SendGrid (mocked), GPT-4o (receipt OCR)

## Admin Page RBAC Rules
- **Full Admin** (DCP, Commander, Executive Staff): All 3 tabs (Pending Approval, All Users, Settings), all action buttons
- **Exec Cadre**: All Users tab only, can change roles and unit assignments, CANNOT: approve users, edit permissions, delete users, reset passwords, or access settings

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
│   │   └── test_admin_rbac.py
│   └── routes/
│       ├── assignments.py
│       ├── auth.py
│       ├── budget.py       # Receipt OCR uses EMERGENT_LLM_KEY
│       ├── participants.py
│       ├── photos.py
│       ├── schedule.py
│       ├── students.py     # Auto-balance flight distribution
│       ├── users.py        # Exec Cadre permissions added
│       └── ...
└── frontend/
    └── src/
        ├── App.js           # Route protection includes exec_cadre for /admin
        ├── styles/print.css
        ├── context/AuthContext.js
        ├── services/api.js
        ├── components/Sidebar.js  # Exec Cadre sees Admin link
        ├── pages/
        │   ├── AdminPage.js       # isFullAdmin conditional rendering
        │   ├── AssignmentsPage.js
        │   ├── RosterPage.js
        │   ├── OrgChartPage.js
        │   └── ...
```

## Completed Work Log
- **Apr 6**: Excel Schedule Sync, Secure Token Storage, Test Secrets Cleanup, Auto-Balance Flights, Print-Friendly Views
- **Apr 7**: Assignments System (CRUD, rubric grading, submissions, reminders)
- **Apr 9**: Admin RBAC, Meal Plan periods, Honor Agreement System, Squadron Schedule View (6th/21st/22nd CTS + 16th OPS SUP multi-column grid with color-coded A-F flights)

## Remaining Backlog
- SendGrid API key integration (currently mocked for emails/reminders)
- Any additional user-requested features

## 3rd Party Integrations
- SendGrid (Email) — requires user API key, currently MOCKED
- Emergent Object Storage — uses Emergent LLM Key (photos + assignment files)
- GPT-4o via Emergent Integrations — receipt OCR (uses EMERGENT_LLM_KEY)
