# CAP Encampment Roster - Product Requirements Document

## Original Problem Statement
Create an interactive roster for a Civil Air Patrol encampment using uploaded Excel template. Include pages for handbooks, schedule, official documents and financial trackers. Role-based access with Commander, Staff, and Cadet roles.

## User Personas
1. **Commander** - Full access to all features, user management, CRUD on all entities
2. **Staff** - Can edit roster, schedule, budget, documents; cannot manage users
3. **Cadet** - View-only access to all pages

## Core Requirements
- [x] Master Roster management with participant CRUD
- [x] Excel import for roster data
- [x] Schedule calendar with event management
- [x] Financial budget tracker with estimated vs actual
- [x] Handbooks document repository
- [x] Official documents section
- [x] Role-based access control (Commander/Staff/Cadet)
- [x] Civil Air Patrol branding (blue #00205B, white, red accents)
- [x] Org Chart with role descriptions and assignments
- [x] Schedule import from Excel with date correction (July 17-24, 2026)
- [x] Draft/Publish workflow for schedule

## What's Been Implemented

### Backend (FastAPI + MongoDB)
- JWT authentication with role-based permissions
- Users API (register, login, role management)
- Participants API (CRUD + Excel import)
- Schedule API (CRUD + Excel import + publish/unpublish + settings)
- Budget API (CRUD + Excel import + summary)
- Documents API (handbooks + official docs)
- Org Chart API (CRUD + seed defaults + assignments)
- Dashboard statistics endpoint

### Frontend (React + Tailwind + Shadcn)
- Login/Registration page with CAP branding
- Collapsible sidebar navigation
- Dashboard with statistics cards and charts
- Master Roster with search, filter, pagination
- Org Chart page with hierarchical tree view
- Role Details side panel with view/edit modes
- Schedule page with day-by-day grid view (July 17-24)
  - Import button for Excel schedule import
  - Publish/Unpublish toggle for draft workflow
  - Published/Draft badge indicator
  - 8 day tabs: Staff Arrival, In-Processing, Day 1-5, Graduation
- Financial Tracker with summary cards and table
- Handbooks page with document viewer
- Official Documents grid
- Admin page for user management

### Schedule Import Feature (Feb 21, 2026)
- Imported 113 events from Excel template
- Corrected dates to July 17-24, 2026
- Events categorized by type (training, ceremony, meal, PT, etc.)
- Color-coded event display
- Draft/Publish workflow implemented
- Import button for admins to re-import schedule

## Architecture

### Tech Stack
- **Frontend**: React 18, Tailwind CSS, Shadcn/UI, Axios
- **Backend**: FastAPI (Python), Motor (async MongoDB)
- **Database**: MongoDB
- **Auth**: JWT tokens, bcrypt password hashing

### Key API Endpoints
- `/api/auth/register`, `/api/auth/login` - Authentication
- `/api/participants`, `/api/participants/import` - Roster management
- `/api/schedule`, `/api/schedule/import`, `/api/schedule/publish`, `/api/schedule/settings` - Schedule management
- `/api/budget`, `/api/budget/summary` - Financial tracking
- `/api/org-chart/roles`, `/api/org-chart/seed-defaults` - Org chart management
- `/api/users` - User management (Commander only)

### Database Collections
- `users` - User accounts and roles
- `participants` - Roster participants
- `schedule` - Schedule events
- `schedule_settings` - Draft/publish status
- `budget` - Budget items
- `org_chart_roles` - Org chart positions
- `documents` - Handbooks and official docs

## Prioritized Backlog

### P0 (Critical) - COMPLETED
- [x] Schedule import with date correction
- [x] Draft/Publish workflow for schedule

### P1 (High Priority)
- [ ] Implement Handbooks page (upload/view PDF documents)
- [ ] Implement Official Documents page (upload/view files)
- [ ] PDF export for roster reports

### P2 (Medium Priority)
- [ ] Add Rich Text/Markdown support for Org Chart responsibilities
- [ ] Email notifications for schedule changes
- [ ] Attendance tracking per event
- [ ] Bulk participant import validation

### P3 (Low Priority)
- [ ] Flight/Squadron assignment interface
- [ ] Print-friendly roster and org chart views
- [ ] Enhanced financial reports

## Next Tasks
1. Implement Handbooks page with document upload functionality
2. Implement Official Documents page
3. Add PDF export for roster

## Test Credentials
- **Commander**: commander@test.com / test123 (auto-created, full access)
- New users can register and will be assigned Cadet role by default

## Notes
- First registered user automatically becomes Commander
- Schedule dates: July 17-24, 2026
  - July 17: Staff/Cadre Arrival
  - July 18: Student In-Processing  
  - July 19-23: Training Days 1-5
  - July 24: Graduation Day
