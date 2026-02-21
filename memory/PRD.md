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

## What's Been Implemented

### Backend (FastAPI + MongoDB)
- JWT authentication with role-based permissions
- Users API (register, login, role management)
- Participants API (CRUD + Excel import)
- Schedule API (CRUD for events)
- Budget API (CRUD + Excel import + summary)
- Documents API (handbooks + official docs)
- **Org Chart API (CRUD + seed defaults + assignments)**
- Dashboard statistics endpoint

### Frontend (React + Tailwind + Shadcn)
- Login/Registration page with CAP branding
- Collapsible sidebar navigation
- Dashboard with statistics cards and charts
- Master Roster with search, filter, pagination
- **Org Chart page with hierarchical tree view**
- **Role Details side panel with view/edit modes**
- Schedule calendar view with week navigation
- Financial Tracker with summary cards and table
- Handbooks page with document viewer
- Official Documents grid
- Admin page for user management

### Org Chart Feature (Feb 21, 2026)
- 48 default roles matching 2026 Encampment Structure
- Clickable nodes opening Role Details panel
- Role Details: Title, Assigned Member, Summary, Responsibilities, Reports To, Subordinates
- Editors can edit descriptions and assign members
- Cadets have view-only access
- API-level role-based access control

## Prioritized Backlog

### P0 (Critical)
- All core features implemented ✓

### P1 (High Priority)
- [ ] Actual Excel file upload from original templates
- [ ] PDF export for roster reports
- [ ] Attendance tracking per event

### P2 (Medium Priority)
- [ ] Email notifications for schedule changes
- [ ] Bulk participant import validation
- [ ] Flight/Squadron assignment interface

## Next Tasks
1. Test Excel import with actual encampment roster template
2. Add more detailed financial reports
3. Implement print-friendly roster and org chart views
