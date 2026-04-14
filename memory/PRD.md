# CAP Encampment Management App — PRD

## Original Problem Statement
Build an interactive roster and management application for a Civil Air Patrol (CAP) encampment titled "Tennessee Wing Civil Air Patrol Encampment".

## Core Features (Implemented)
- **Roster Management**: Interactive roster with live filtering, search, RBAC, flight-grouped views, photo uploads, auto-balance, print-friendly
- **Assignments System (Google Classroom-style)**: Instructor/mentor/student roles, Q&A, document uploads, grading, email reminders
- **Student Upload System**: Excel upload with automatic flight assignment
- **Org Chart**: Interactive node-link command map with SVG connectors, 85 positions from TNWG ENC26 spreadsheet, 4 color-coded categories (Command, Cadet Training, Support, Cadet Support), dual reporting (CSS/CC → CTG/DF dashed line), horizontal branching, collapsible depth, detail side panel on click, search + category filters
- **Health Services**: Medical roster, allergies, OTC approvals, parent email notifications
- **Check-In & Barracks**: Multi-step in-processing, bunk assignments
- **Granular RBAC**: Senior Staff + Cadre roles with permissions
- **Parent Portal**: "My Cadet" tab, Admin widget editor
- **Honor Agreement System**: Role-based digital agreements, blocking modal
- **Budget/Finance Tracker**: Payment imports, receipt OCR, charts
- **Schedule**: 11 categories, Excel import, Squadron View grid
- **Analytics, Logistics, Status Board, Notifications**
- **Auth**: httpOnly cookie-based JWT

## Org Chart Hierarchy (Current)
```
Encampment Commander (Maj Divers, L) [Command]
├── Commandant of Cadets [Command]
│   └── CTG/CC (C/Lt Col Yoder, L) [Cadet Training]
│       ├── CTG/CD Operations (C/Lt Col Grammer, A)
│       ├── CTG/DF Academics (C/Maj Doran, G)
│       ├── CTG/CCEA Enlisted (C/CMSgt Railey, A)
│       ├── CSS/CC Cadet Support Sq (C/Capt. Posta, A) [Cadet Support] ←--- secondary→CTG/DF
│       ├── CTO Chief Training Officer
│       ├── 6th CTS, 21st CTS, 22nd CTS
│       └── (Flights under each CTS)
├── DCS Deputy Commander for Support (Capt Belli, S) [Support]
│   ├── XP Plans & Programs
│   ├── LG Logistics (Capt Reed, A)
│   ├── Comm Communications
│   ├── Finance
│   └── Health Services / WORD (Lt Col Divers, K)
├── SM Superintendent (TSgt Breslin, D) [Command]
├── Chaplain(s) [Command]
└── Safety [Command]
```

## Tech Stack
- Frontend: React 19, Tailwind CSS, Shadcn UI
- Backend: FastAPI, MongoDB, openpyxl
- Integrations: SendGrid (LIVE), Emergent Object Storage, GPT-4o (receipt OCR)

## Completed Work Log
- **Apr 6-9**: Core features, Excel sync, RBAC, Honor Agreements
- **Apr 10**: Google Classroom-style Assignments. 100% tests.
- **Apr 11**: SendGrid live. Lillian Yoder account synced.
- **Apr 14**: Mobile responsiveness. Org Chart V1 (list tree, 86 positions, iteration 59). Org Chart V2 (SVG node-link diagram, 85 positions, restructured hierarchy, dual reporting, 4 categories, iteration 60). 100% tests.

## Remaining Backlog
- P1: Senior Barracks (TR-106, TR-107, TR-105) individual room assignments
- P2: Receipt Scanning (OCR) for the financial module
- P3: Bulk auto-balance button for flight distribution
