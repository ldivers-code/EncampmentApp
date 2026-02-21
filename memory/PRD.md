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

## What's Been Implemented (Feb 21, 2026)

### Backend (FastAPI + MongoDB)
- JWT authentication with role-based permissions
- Users API (register, login, role management)
- Participants API (CRUD + Excel import)
- Schedule API (CRUD for events)
- Budget API (CRUD + Excel import + summary)
- Documents API (handbooks + official docs)
- Dashboard statistics endpoint

### Frontend (React + Tailwind + Shadcn)
- Login/Registration page with CAP branding
- Collapsible sidebar navigation
- Dashboard with statistics cards and charts
- Master Roster with search, filter, pagination
- Schedule calendar view with week navigation
- Financial Tracker with summary cards and table
- Handbooks page with document viewer
- Official Documents grid
- Admin page for user management

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
3. Implement print-friendly roster views
