# CAP Encampment Management App — PRD

## Original Problem Statement
Build an interactive roster and management application for a Civil Air Patrol (CAP) encampment titled "Tennessee Wing Civil Air Patrol Encampment".

## Core Features (Implemented)
- **Roster Management**: Interactive roster with live filtering, search, RBAC, flight-grouped views, photo uploads, auto-balance, print-friendly
- **Assignments System (Google Classroom-style)**: Instructor/mentor/student roles, Q&A, document uploads, grading, email reminders
- **Student Upload System**: Excel upload with automatic flight assignment
- **Org Chart**: Interactive SVG node-link command map with horizontal branching, 85 positions. Hierarchy: Enc Commander → Commandant → CTG/CC → [CTG/CD, CTG/DF, CTG/CCEA, CSS/CC, CTO + 3 Squadrons]. Squadron TOs under CTO (not Squadron Commanders). 19 positions with secondary academic reporting to CTG/DF (dashed connectors). 5-color scheme: Blue (Command), Maroon (Cadet Training), Yellow (Squadron), Emerald Green (Support), Silver (Cadet Support). Collapsible depth, search, category filters, detail side panel.
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
- **Apr 14**: Mobile responsiveness. Org Chart V1 (list tree, 86 positions). Org Chart V2 (SVG node-link diagram, 85 positions, restructured hierarchy, dual reporting). Org Chart V3 (TOs moved under CTO, 19 secondary academic reports to CTG/DF, 5-color scheme: Blue/Maroon/Yellow/Green/Silver). 100% tests (iterations 59-61).

## Remaining Backlog
- P1: Senior Barracks (TR-106, TR-107, TR-105) individual room assignments
- P2: Receipt Scanning (OCR) for the financial module
- P3: Bulk auto-balance button for flight distribution
