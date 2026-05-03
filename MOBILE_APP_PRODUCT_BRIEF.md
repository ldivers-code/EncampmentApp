# TNWG Encampment Hub — Mobile App Product Brief

## 1. Executive Summary

**Product Name:** TNWG Encampment Hub (working title: "Cadre Hub")
**Platform:** Cross-platform mobile app (iOS + Android) with existing responsive web companion
**Purpose:** End-to-end operational management for Civil Air Patrol (CAP) encampments — replacing paper rosters, spreadsheet schedules, manual check-in forms, and disconnected communication channels with a single mobile-first command tool.

**Current State:** Fully functional web application (React 19 + FastAPI + MongoDB) with 282 API endpoints, 56 database collections, 25 pages, 176 active participants, and live SendGrid email integration. The backend is production-ready and requires zero changes to support a mobile client — it exposes a complete REST API with httpOnly cookie authentication.

**Target Launch:** Tennessee Wing Encampment 2026, VTS Catoosa, GA (July 18–25, 2026)

---

## 2. Users & Personas

### 2.1 User Roles (19 distinct roles, 4 role groups)

| Group | Roles | Count | Primary Mobile Use |
|-------|-------|-------|--------------------|
| **Senior Staff** | DCP, Commander, Executive Staff, Training Officer, Health Services, Finance, Dining Facility, Logistics, Plans & Programs, Staff | ~15 | Full operational oversight, approvals, emergency alerts |
| **Cadre** | Executive Cadre, Cadre, Squadron Commander | ~95 | Flight roster management, point tracking, incident reports, daily check-ins |
| **Students** | Basic Student | ~60 | View schedule, assignments, flight info (read-only) |
| **Parents** | Parent/Guardian | Variable | Monitor cadet status, medication diary, sign OTC permissions |

### 2.2 Persona Snapshots

**Encampment Commander (Maj Divers)**
- Needs: Real-time headcount, budget status, emergency alerts, org chart at a glance
- Mobile context: Walking between buildings, reviewing status during formations

**Flight Commander (C/2dLt Marfio)**
- Needs: Flight roster with photos, point tracking, incident reports, Chain of Command
- Mobile context: In the field with cadets, needs offline-capable roster access

**Health Services Officer (Lt Col Divers, K)**
- Needs: Medication diary logging, allergy lookups, OTC approval tracking, supplement lists
- Mobile context: Administering medications at med call, needs quick cadet lookup

**Parent (remote)**
- Needs: See cadet's schedule, medication diary, health incidents, sign OTC forms
- Mobile context: Checking from home on phone, limited interaction

---

## 3. Feature Inventory (What Exists Today)

### 3.1 Core Modules — 25 Pages, Fully Implemented

| Module | Description | Key Endpoints | Mobile Priority |
|--------|-------------|---------------|-----------------|
| **Dashboard** | Today's schedule, participant count, budget snapshot, who's online | `/api/dashboard/*` | P0 — Home screen |
| **My Flight** | Flight roster, Chain of Command (auto-populated from cadre assignments), points, documents, incident reports, escalation chain | `/api/my-flight`, `/api/flights/*/leadership`, `/api/flights/*/roster` | P0 — Primary cadre view |
| **Roster** | 176 participants with live filtering (12 filter types), Excel import, flight assignment, Kanban drag-and-drop, print view, cadet photos | `/api/participants/*`, `/api/students/upload` | P0 — Core data |
| **Schedule** | 207 events across 11 categories, day/week/squadron view, Excel import, auto-publish, change requests, real-time sync | `/api/schedule/*` | P0 — Daily driver |
| **Check-In** | 6-step in-processing flow per cadet, contraband logging, bulk check-in/undo | `/api/check-in/*` | P0 — Day 1 critical |
| **Health Services** | Medical roster, allergy tracking (31 records), OTC approvals (96 records), daily medication diary, supplement list, health alerts | `/api/health/*` | P0 — Safety critical |
| **Assignments** | Google Classroom-style: create/submit/grade, instructor/mentor/student roles, Q&A, file upload, rubric grading, email reminders | `/api/assignments/*` | P1 |
| **Org Chart** | Interactive SVG node-link diagram, 85 positions, 5 color-coded categories, dual reporting lines, expand/collapse, detail panel | `/api/org-chart/*` | P1 |
| **Budget/Finance** | Income/expense tracking (46 entries), payment imports, receipt OCR (GPT-4o), daily reports, charts | `/api/budget/*` | P1 |
| **Barracks** | Bunk assignment grid, building/room/bed mapping | `/api/barracks/*` | P1 |
| **Points/Awards** | Point tracking per cadet, merit/demerit system, 11 score categories, leaderboard | `/api/points/*` | P1 |
| **Logistics** | Inventory, lost & found, radios, comms, vehicles, facilities, supply requests, callsigns, contraband (all logistics data) | `/api/logistics/*` | P2 |
| **Training Officer** | Blister checks, counseling logs, cadre issues, summary dashboard | `/api/training/*` | P2 |
| **Status Board** | Live display mode (auto-rotating), announcements, resources, flight status, emergency alerts | `/api/status-board/*` | P2 (display mode) |
| **Analytics** | Participation stats, flight distribution, age groups, payment tracking, wing/region breakdown | `/api/analytics/*` | P2 |
| **Notifications** | In-app bell notifications (293 sent), push-style alert system, read/unread tracking | `/api/notifications/*` | P0 — Push notifications |
| **Parent Portal** | "My Cadet" view: schedule, health incidents, medication diary, points, meals, OTC permission form, admin widget editor | `/api/parent/*` | P0 — Separate app flow |
| **Honor Agreements** | Digital signature agreements, role-specific content, blocking modal until signed, PDF download | `/api/honor-agreement/*` | P1 — Onboarding |
| **Admin** | User management, role assignment, permission overrides, Google Sheets sync, participant linking | `/api/users/*`, `/api/admin/*` | P2 |
| **Documents** | Official documents + handbooks, category-organized, upload/download | `/api/documents/*` | P2 |
| **Meal Plan** | Period-based meal planning, dietary notes | `/api/meal-plans/*` | P2 |

### 3.2 Cross-Cutting Features

- **Granular RBAC:** 19 roles with page-level and action-level permissions. Individual page visibility overrides per user.
- **Real-time:** Active user tracking, 30s badge refresh, 15s status board auto-refresh, schedule version polling
- **Email Integration:** Live SendGrid from `tnwgencampment@tncap.us` — assignment notifications, approval emails, health alerts
- **File Storage:** Emergent Object Storage for photos, assignment materials, receipts, documents
- **Excel Import/Export:** Roster import (CAP Event Admin Report format), schedule import, budget import, print-friendly exports
- **Sidebar Nav Customization:** Per-user drag-and-drop reorder, persisted to database

---

## 4. Technical Architecture

### 4.1 Existing Backend (No Changes Required for Mobile)

```
┌─────────────────────────────────────────┐
│            FastAPI Backend               │
│  282 REST endpoints, httpOnly JWT auth   │
│  MongoDB (56 collections)                │
│  SendGrid, Object Storage, GPT-4o       │
├─────────────────────────────────────────┤
│  Current Clients:                        │
│  ├── React 19 Web App (responsive)       │
│  └── [NEW] Mobile App (iOS/Android)      │
└─────────────────────────────────────────┘
```

### 4.2 API Authentication
- **Method:** httpOnly cookie-based JWT tokens
- **Login:** `POST /api/auth/login` → sets `access_token` cookie
- **Session:** `GET /api/auth/me` → returns current user + role + permissions
- **Mobile consideration:** The API also accepts `Authorization: Bearer <token>` header and `?token=<token>` query param as fallbacks. Mobile app should use the Bearer header approach.

### 4.3 Key API Patterns
- All endpoints prefixed with `/api/`
- Responses exclude MongoDB `_id` (clean JSON)
- File uploads via multipart form data
- Pagination not yet implemented (all lists return full arrays — fine for encampment scale of ~200 people)
- Error responses: `{"detail": "error message"}` with appropriate HTTP status codes

### 4.4 Database Schema Highlights

| Collection | Records | Purpose |
|-----------|---------|---------|
| `users` | 21 | App accounts (login credentials, role, flight, permissions) |
| `participants` | 176 | Full roster (imported from CAP reports — name, rank, CAPID, flight, squadron, position, contact info, payment status) |
| `schedule` | 207 | All encampment events (date, time, type, location, target groups) |
| `assignments` | 28 | Google Classroom-style assignments with submissions |
| `notifications` | 145 | Push notification records |
| `user_notifications` | 293 | Per-user notification delivery + read status |
| `hs_otc_approvals` | 96 | OTC medication permission forms |
| `org_chart_roles` | 101 | Org chart positions + hierarchy |
| `budget` | 46 | Income/expense line items |

---

## 5. Mobile App Screens (Recommended)

### 5.1 Navigation Structure

```
Bottom Tab Bar (role-dependent):
├── Home (Dashboard)
├── My Flight / My Cadet (role-dependent)
├── Schedule
├── Notifications
└── More (Roster, Health, Budget, Org Chart, etc.)
```

### 5.2 Screen Map

**Auth Flow:**
1. Login (email/CAPID + password)
2. Honor Agreement (blocking if unsigned)
3. Forgot Password / Reset Password

**Primary Screens (P0):**
1. **Dashboard Home** — Today's schedule (scrollable), participant count, budget snapshot, active users
2. **My Flight** — Chain of Command (auto-populated), flight roster with photos, quick-action buttons (points, report)
3. **Schedule** — Day view with swipe navigation, event detail sheet, filter by squadron/flight
4. **Check-In** — Scannable list, step-by-step check-in flow, contraband logging
5. **Health Services** — Cadet search → medication diary entry, allergy lookup, OTC status
6. **Notifications** — Push notification list with deep links
7. **Parent Portal** (separate flow) — My Cadet overview, medication diary (read-only), OTC form

**Secondary Screens (P1):**
8. **Roster** — Searchable participant list, detail cards, flight/squadron filter
9. **Assignments** — Assignment list, submission flow, grading
10. **Org Chart** — Zoomable/pannable node diagram, tap for details
11. **Budget** — Income/expense summary, receipt camera capture (OCR)
12. **Points** — Flight leaderboard, quick point entry
13. **Barracks** — Room assignment grid

**Tertiary Screens (P2):**
14. Logistics, Training Officer, Status Board, Analytics, Admin, Documents, Meal Plan

### 5.3 Mobile-Specific Features to Add

| Feature | Why | API Impact |
|---------|-----|------------|
| **Push Notifications** (FCM/APNS) | Replace in-app-only bell with native push | Add `POST /api/devices/register` for device tokens, background push sender |
| **Offline Roster Cache** | Field access with no WiFi (VTS Catoosa has spotty coverage) | None — client-side SQLite/AsyncStorage cache of `/api/participants` |
| **Camera → Receipt OCR** | Snap receipt photo directly to budget module | Existing `POST /api/budget/receipts/upload` already handles this |
| **Camera → Cadet Photo** | Snap headshot during check-in | Existing `POST /api/profile/photo` already handles this |
| **QR Check-In** | Scan cadet CAPID barcode for fast check-in lookup | Add `GET /api/check-in/lookup?capid=XXXXXX` (trivial) |
| **Biometric Lock** | Protect health/finance data on shared devices | Client-side only (FaceID/TouchID gating API calls) |

---

## 6. Recommended Tech Stack for Mobile

### Option A: React Native (Recommended)
- **Why:** Existing team knows React. 80%+ of business logic (API calls, state management, role checks) can be shared. Shadcn patterns translate to NativeWind/Tamagui.
- **Framework:** React Native + Expo (managed workflow)
- **UI:** NativeWind (Tailwind for RN) or Tamagui
- **Navigation:** React Navigation (bottom tabs + stack)
- **State:** React Query (TanStack Query) for API caching + offline
- **Push:** Expo Notifications (wraps FCM + APNS)
- **Storage:** AsyncStorage for prefs, SQLite (expo-sqlite) for offline roster cache
- **Timeline:** 6–8 weeks to MVP with existing API

### Option B: Flutter
- **Why:** Single codebase, excellent performance, rich widget library
- **Tradeoff:** Team needs to learn Dart, no code sharing with existing React web app
- **Timeline:** 8–10 weeks

### Option C: Progressive Web App (PWA)
- **Why:** Zero new codebase — add service worker + manifest to existing React app
- **Tradeoff:** No native push on iOS (limited), no App Store presence, limited offline
- **Timeline:** 1–2 weeks for basic PWA, but lacks native feel
- **Best for:** Quick MVP / interim solution before native app

---

## 7. Data & Privacy

- **PII Handled:** Names, DOBs, addresses, phone numbers, emails, medical information (allergies, medications, OTC approvals), emergency contacts, parent contact info
- **Compliance:** CAP data handling policies, COPPA considerations (cadets are minors ages 12–18)
- **Encryption:** All API traffic over HTTPS. JWT tokens in httpOnly cookies (web) or secure storage (mobile). MongoDB at rest encryption recommended for production.
- **Medical Data:** Health Services module contains allergy lists, medication schedules, OTC permissions signed by parents. Requires appropriate access controls (already implemented via RBAC — only Health Services role + command staff can access).
- **Photo Storage:** Cadet photos stored in Emergent Object Storage with signed URLs (not publicly accessible)

---

## 8. Deployment & Distribution

| Aspect | Recommendation |
|--------|---------------|
| **Backend** | Already deployed. No changes needed. Mobile app connects to same API. |
| **iOS** | TestFlight for beta → App Store (requires Apple Developer $99/yr) |
| **Android** | Google Play internal testing → production (requires Google Play $25 one-time) |
| **MDM** | Consider Apple Business Manager for managed distribution to CAP-issued devices |
| **Updates** | Expo OTA updates for JS bundle changes (no App Store review needed) |

---

## 9. Metrics & Success Criteria

| Metric | Target |
|--------|--------|
| Daily active users during encampment | 80%+ of staff/cadre (90+ users) |
| Check-in completion rate via app | 100% of cadets processed through mobile |
| Medication diary compliance | Every med call logged within 5 min |
| Schedule views per day | 3+ per user |
| Parent portal engagement | 50%+ of parents access at least once |
| Crash-free rate | 99.5%+ |
| API response time (P95) | <500ms |

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Poor WiFi at VTS Catoosa | Users can't load data | Offline roster/schedule cache, optimistic UI updates |
| 200+ concurrent users on single API | Slow responses | MongoDB indexing already in place; add API response caching if needed |
| Minors' data on personal devices | Privacy concern | Biometric lock, auto-logout after 30 min, no data persisted on device beyond cache |
| App Store review timeline | Delayed launch | Submit 4+ weeks before encampment; use TestFlight/internal track as fallback |
| Lost/stolen devices | Data exposure | Remote session invalidation via `/api/auth/logout-all` (to be added) |

---

## 11. API Endpoint Reference (Complete)

The existing backend exposes **282 endpoints** across these route modules:

| Module | File | Endpoints | Key Routes |
|--------|------|-----------|------------|
| Auth | `auth.py` | 21 | `POST /login`, `GET /me`, `POST /register`, `PUT /profile`, `GET /profile/nav-order` |
| Participants | `participants.py` | 16 | `GET /participants`, `PUT /{id}/assignment`, `POST /import` |
| Students | `students.py` | 10 | `POST /upload`, `GET /auto-assign` |
| Schedule | `schedule.py` | 9 | `GET /schedule`, `POST /events`, `POST /import` |
| Health | `health_services.py` | 41 | `GET /health/cadet/{id}/*`, `POST /med-diary`, `POST /supplements` |
| Assignments | `assignments.py` | 13 | `GET /assignments`, `POST /submit`, `POST /grade` |
| Budget | `budget.py` | 18 | `GET /budget/*`, `POST /receipts/upload` |
| Flights | `flights.py` | 7 | `GET /my-flight`, `GET /flights/{f}/leadership`, `GET /flights/{f}/roster` |
| Check-In | `checkin.py` | 12 | `POST /check-in/{id}/{step}`, `GET /contraband` |
| Points | `points.py` | 23 | `POST /points/award`, `GET /points/leaderboard` |
| Notifications | `notifications.py` | 9 | `GET /notifications`, `POST /send`, `PUT /{id}/read` |
| Org Chart | `orgchart.py` | 7 | `GET /org-chart/roles`, `POST /seed` |
| Status Board | `status_board.py` | 12 | `GET /display`, `POST /announcements` |
| Users/Admin | `users.py` | 11 | `GET /users`, `PUT /{id}/role`, `POST /approve` |
| Parent | `parent.py` | 14 | `GET /my-cadet`, `GET /my-cadet/med-diary`, `POST /otc-permission` |
| Logistics | `logistics.py` | 15 | `GET /inventory`, `POST /supply-requests` |
| Documents | `documents.py` | 12 | `GET /documents`, `POST /upload` |
| Reports | `reports.py` | 11 | `POST /flight-reports`, `PUT /escalate` |
| Training | `training.py` | 10 | `GET /blister-checks`, `POST /counseling-logs` |
| Other | Various | 11 | Meal plans, analytics, badges, awards, daily settings |

---

## 12. Timeline Estimate

| Phase | Duration | Deliverables |
|-------|----------|-------------|
| **Phase 1: Core Shell** | Week 1–2 | Auth flow, navigation skeleton, Dashboard, Schedule, My Flight, Notifications (push) |
| **Phase 2: Operations** | Week 3–4 | Check-In, Health Services (med diary), Roster (read + search), Parent Portal |
| **Phase 3: Cadre Tools** | Week 5–6 | Points, Assignments, Incident Reports, Org Chart |
| **Phase 4: Admin & Polish** | Week 7–8 | Budget, Logistics, Barracks, offline cache, performance tuning, App Store submission |
| **Phase 5: Field Testing** | Week 9 | Beta with cadre/staff at pre-encampment events |

---

*Document generated from live production codebase — all features, endpoints, and data counts reflect actual system state as of April 2026.*
