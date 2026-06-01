# CAP Encampment App — PRD & Changelog

## Original Problem Statement
Build an interactive roster & management application for the **Tennessee Wing
Civil Air Patrol Encampment** with:
- Roster Management (live filtering, RBAC, flight-grouped views, contact info)
- Student Upload (Excel) with auto-flight assignment + sub-event handling
- Org Chart (strict 1:1 interactive mind-map)
- Health Services (allergies, OTC approvals, Daily Med Diary, Supplements, Contraband)
- Check-In & Barracks (multi-step in-processing)
- Granular RBAC with visibility / redaction / cascading assignments
- Parent Portal "My Cadet" + Admin widget editor
- Budget/Finance Tracker + Smart Receipt OCR
- Schedule Sync (Excel auto-publish)
- Honor Agreements (digital signature)
- Mobile App back-end ready

## Stack
- React 19, Tailwind, Shadcn UI, DOMPurify, lucide-react
- FastAPI, MongoDB, Python
- emergentintegrations (GPT-4o Vision OCR); SendGrid email
- JWT auth (httpOnly cookie + Bearer header); bcrypt

## Architecture (current)
```
/app/
├── backend/
│   ├── models.py              # Roles, Permissions, ParticipantTypes
│   ├── role_groups.py         # 7-concern separation, semantic groups (Phase 3)
│   ├── scope.py               # Visibility filtering & Redaction rules
│   ├── classifier.py          # Unified RegZone sub-event classifier
│   ├── permissions.py         # JWT, get_current_user, require_role, require_health_*
│   ├── database.py            # Centralized DB logic & participant counts
│   └── routes/                # auth, users, participants, …
└── frontend/src/{pages,components}
```

## Seven Separated Concerns (Phase 3)
1. **Account status** — `users.is_approved`; surfaced by `GET /api/auth/status`
2. **CAP member type** — `participants.member_type` (SENIOR / CADET / CADET SPONSOR)
3. **Encampment participant type** — `participants.participant_type` (`student | cadre | senior_staff | needs_review`)
4. **Cadre role type** — `participants.is_exec_cadre` + `users.cadre_position`
5. **Duty assignment** — `users.flight / squadron / cadre_unit / cadre_position / support_section`
6. **Permission role** — `users.role` (UserRole) grouped via `role_groups.py`
7. **Access scope** — `scope.py` (visibility filter + field redaction)

## Implementation Log
- **Phase 1**: Backend classification audit (canonical taxonomy proposal).
- **Phase 2** (Feb 2026): DB migration — all participants normalized to `student / cadre / senior_staff / needs_review`; added `is_exec_cadre` flag; centralized `get_active_participant_count`; created `scope.py` for visibility/redaction.
- **Phase 3** (Feb 2026): Separated the seven concerns; introduced `role_groups.py`; tightened EXEC_CADRE so it cannot leak into senior-staff capabilities by default; added `cadre_lead_can_target()` guard. 22 unit tests + 9 live RBAC tests passing.
- **Phase 4** (Feb 2026): Approval & participant linking hardened. New `account_status.py` (single source of truth for the six canonical fields). New `get_current_user_linked` dependency. Approve endpoint now tolerates id/email/capid identifiers, returns `matched_by`, structured 404 with `tried` array. Pending-users list now embeds the canonical status block. New `GET /api/users/{id}/status` (admin). 8 new unit tests passing.
- **Phase 5** (Feb 2026): Sensitive data & exports consolidation. Extended `scope.py` with `safe_roster_entry`, `redact_payment_only`, `visible_flights_for`, `can_view_payment`, `can_view_medical`. Fixed three concrete leaks: `/participants/pending-payments` (now finance/admin-only + scoped + redacted), `/flights/{flight}/roster` & `/squadrons/{squadron}/roster` (now visibility-scoped 403 + redacted via safe_roster_entry), summary-export "Pending Payments" sheet (only emitted for finance callers). Stats endpoint updated to canonical taxonomy. 29 new scope tests passing.
- **Phase 6** (Feb 2026): Participant-count consistency. Every surface now sources its encampment-wide count from `get_active_participant_count()`. Added `total_active` to `/participants/stats` and `/participants/analytics/detailed` (so cadre/scoped callers see both their visible count AND the canonical encampment total). Added new `/api/barracks/summary` endpoint. Replaced `len(participants)` total in `/participants/payment-summary` with the helper. Live verification: 9 surfaces, identical count.
- **Schedule Grid Parser** (Feb 2026): `sync_schedule_from_gsheet` now auto-detects and parses the per-squadron grid layout used by the CAST and Encampment day-tab sheets in addition to the flat-table format. Detection: header row with `START / END / <squadron columns> / Notes`. Date extracted from cell A1 (e.g. "Friday | Day 1 CADRE Arrival | May 29th"); year falls back to `LAST UPDATED:` footer then current year. Merged horizontal cells (only first squadron column filled) are emitted as one event targeting all squadrons in the block; per-squadron filled cells emit per-squadron events. Vertically-merged cells across time slots are stitched back into one longer event by extending `end_time`. Notes column is treated as row-wide and copied into every emitted event. 12 unit tests in `test_schedule_grid_parser.py`. Verified live against the CAST Day 1 sheet — 9 correctly-merged events synced.
- **Frontend Taxonomy Sweep** (Feb 2026): Replaced remaining legacy participant_type literals in `HealthServicesDashboard.js`, `BarracksPage.js`, `AdminPage.js` (Annual Reset options), `FlightManager.js`, `PaymentReportsTab.js`, and `AnalyticsPage.js`. The four canonical values (`student`, `cadre`, `senior_staff`, `needs_review`) are now used consistently across UI filters, drag-and-drop chips, dashboards, and bulk-reset selectors. `is_exec_cadre` is treated as a boolean flag rather than a participant_type. `RosterPage.js` keeps the legacy aliases ONLY as defensive read-time fallbacks (so un-migrated DB rows still render). Lint clean.
- **Admin Schedule Settings UI** (Feb 2026): Replaced the "grid not supported" warning with a structured two-format hint card explaining both flat-table and grid layouts, including the cell A1 date convention and merge-behaviour.
- **Mobile Backend Integration Doc** (Feb 2026): Rewrote `§3 User Roles & Permissions` to document the seven-concern model from `role_groups.py`, the canonical four-value `participant_type`, the six fields returned by `/api/auth/status`, and per-status mobile UX guidance. Updated the `Participant` data shape to reflect the new taxonomy and the new `is_exec_cadre` boolean.
- **Schedule Tab Auto-Discovery** (Feb 2026): One-paste workflow for bulk-importing every day-tab from a Google Sheets spreadsheet. New endpoints `POST /api/google-sheets/discover-tabs` (downloads XLSX export via openpyxl, lists every tab with A1 title + parsed schedule date) and `POST /api/google-sheets/schedules/bulk-add` (appends to `settings.schedules`, deduped by `(spreadsheet_id, sheet_name)`, auto-suffixes colliding ids). `ScheduleSheetConfig` gained an optional `sheet_name` field; `fetch_google_sheet_csv` now resolves tabs as `gid → sheet_name (via gviz/tq) → first tab`. Admin UI: new "Discover Tabs" button + modal listing each tab with parsed-date badge, A1 preview, editable label, and a checkbox pre-checked for schedule-like tabs. Verified live against the CAST sheet (4 tabs found, 3 imported, 54 events synced from "Sat May 30th"). 7 new backend tests + 12 regression tests pass.
- **Auto-Balance Fix + Waitlist by Application Order** (Feb 2026): `auto_assign_flights`, `auto_assign_single_student`, and `auto_assign_unassigned_students` were silently no-op'ing because they filtered by the deprecated `participant_type ∈ {basic_student, advanced_student}`. Replaced with canonical `student` everywhere; ditto the `total_students` count and `flight_distribution` loop in the upload endpoint. Added `AppEditData → app_edit_data` to both the Excel upload and Google Sheets roster column maps; the assigner now sorts `students_to_assign` by `app_edit_data` ascending so the **earliest applications get the seats** and late applicants stay on the **waitlist**. Each flight is enforced at 3 elements × 5 cadets = 15 (6 × 15 = 90 total). When Sync Mode soft-removes a student from the roster, an auto-promotion pass immediately fills the open seat from the highest-priority waitlisted cadet. Auto-assign also normalises mixed-case flight values (`Alpha` → `alpha`) on every run to keep flight-grouped counts consistent. Frontend toast now reports both `assigned` and `waitlisted` counts. 6 new unit tests + existing student-upload regression all pass. Verified live: 101 students → 90 seated, 11 on waitlist; dropping one student → 1 promoted from waitlist.
- **Waitlist UI** (Feb 2026): Added `app_edit_data` to the `ParticipantResponse` model so the field reaches the frontend. Added a one-click **"Waitlist: N"** amber chip next to the participant count header on `RosterPage.js` that toggles the flight filter to `unassigned` and auto-switches to "All" roster view (so waitlisted students — who have no flight — actually appear). Added an info banner above the table explaining the cap (3×5=15) and how to manually promote (click any flight cell — uses existing inline-edit, no new endpoint needed). The flight cell on waitlisted rows now shows a yellow `WAITLIST` badge with the application date below it. When the waitlist filter is active, rows sort by `app_edit_data` ascending so the longest-waiting cadet is first.
- **Mobile Backend Integration — Recent Changes Section** (Feb 2026): Added new `§1a. Recent Backend Changes (Mobile-Relevant)` to `MOBILE_BACKEND_INTEGRATION.md` covering: (1) canonical `participant_type` deprecation guidance with the four allowed values + `is_exec_cadre` boolean, (2) waitlist & application-order auto-assign rules including `app_edit_data`, the 3×5=15 cap, the new `promoted_from_waitlist` field in upload responses, and mobile UI guidance for waitlist rendering, (3) schedule grid-format parser semantics + the `target_groups` filtering pattern + the new `discover-tabs` and `bulk-add` admin endpoints, (4) finance-tracker sync + `/api/budget/finance/needs-review` endpoint, (5) Participant data-shape additions (`app_edit_data`, `is_exec_cadre`, numeric `amount_paid`, `is_removed`). Also updated the Participant/Schedule Event data shape examples and the Roster/Google Sheets endpoint tables with new endpoints + response shapes.

## Backlog
- **P0**: Frontend taxonomy sync — replace `basic_student / staff / exec_cadre` literals across ~16 React files with `student / cadre / senior_staff / needs_review`.
- **P0**: Add `is_exec_cadre` toggle on Cadre participant edit UI.
- **P1**: `Needs Review` filter chip + admin resolution flow on Roster page.
- **P1**: Re-publish `MOBILE_BACKEND_INTEGRATION.md` with new ParticipantType vocabulary + the 7-concern model from `role_groups.py`.
- **P2**: Senior Barracks individual room assignments (TR-106, TR-107, TR-105).
- **P2**: Schedule Sync (Excel auto-publish), Honor Agreements digital signature flow.

## Test Credentials
See `/app/memory/test_credentials.md`.
