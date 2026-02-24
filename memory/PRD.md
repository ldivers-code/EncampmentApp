# CAP Encampment Roster - Product Requirements Document

## Original Problem Statement
Create an interactive roster for a Civil Air Patrol encampment using uploaded Excel template. Include pages for handbooks, schedule, official documents and financial trackers. Role-based access with Commander, Staff, Finance, and Cadet roles.

## User Personas
1. **Commander** - Full access to all features, user management, CRUD on all entities
2. **Staff** - Can edit roster, schedule, documents; assign users to units
3. **Finance** - Full budget access, manage expenses/income, upload receipts, food expense planning
4. **Cadet** - View-only access, sees only their unit's schedule, no budget access

## Core Requirements
- [x] Master Roster management with participant CRUD
- [x] Excel import for roster data
- [x] Schedule calendar with event management
- [x] Financial budget tracker with estimated vs actual
- [x] Handbooks document repository (placeholder)
- [x] Official documents section (placeholder)
- [x] Role-based access control (Commander/Staff/Finance/Cadet)
- [x] Civil Air Patrol branding (blue #00205B, white, red accents)
- [x] Org Chart with role descriptions and assignments
- [x] Schedule import from Excel with date correction (July 17-24, 2026)
- [x] Draft/Publish workflow for schedule
- [x] Real-time schedule sync (auto-refresh every 30 seconds)
- [x] Flight-specific schedules with target groups
- [x] User unit assignment (squadron/flight) in Admin page
- [x] Mobile-optimized schedule view with swipe navigation
- [x] Push notifications for schedule updates
- [x] Custom Tennessee Wing and 60th CTG branding
- [x] Enhanced Financial Tracker with Finance role restriction
- [x] Food expense planner (editable cost per person per day)
- [x] Receipt upload functionality
- [x] **Analytics Dashboard with detailed attendee metrics**
- [x] **Export functionality (CSV, Excel, Full Report)**
- [x] **Member Profiles with editable fields**
- [x] **Profile photo upload**
- [x] **User approval workflow for new accounts**
- [x] **Link users to roster participants by CAPID**
- [x] **Expanded role system (Commander, Finance, Plans & Programs, Executive Cadre, Staff, Cadre)**
- [x] **Updated unit structure (Staff, Support/Exec/Ops Cadre, Squadrons 1-3)**
- [x] **Granular permissions system (12 access types per user)**
- [x] **Admin inline permissions editor**
- [x] **SendGrid email notifications for account approval**
- [x] **Point Tracking System with flight-based permissions**
- [x] **Schedule filter dropdown for all users**
- [x] **Individual Awards Tracking System**
- [x] **My Flight Page with Flight Roster and Documents**

## What's Been Implemented

### Feb 24, 2026 - My Flight Page (Flight Roster & Documents)
- **My Flight Page** (`/my-flight`) with two main tabs:
  - **Roster Tab**: View flight members with name, rank, position (cadre only), and type badge
  - **Documents Tab**: Access TLPs, Pocket Classes, Handbooks, SOPs, and other documents
- **Flight/Squadron Access Control**:
  - Commanders & Exec Cadre: Full access to all flights and squadrons
  - Squadron-level staff: Access to all flights in their squadron
  - Flight staff: Access to their assigned flight only
  - Cadets: Can view documents for their flight
- **Document Management**:
  - Categories: TLPs, Pocket Classes, Handbooks, SOPs, Forms, Checklists, Reference Materials, Other
  - Scopes: Global (all flights), Squadron, Flight
  - Version control with history tracking
  - Upload restricted to Commanders only
- **UI Features**:
  - Flight selector dropdown for users with multi-flight access
  - Flight/Squadron view toggle
  - Category filter for documents
  - Document badges showing scope (Global, ALPHA, SQ1, etc.)
  - Upload Document modal with title, category, scope, description, and file URL

### Feb 24, 2026 - Individual Awards Tracking
- **Awards Tab** on Point Tracking page with comprehensive features:
  - **Daily Winners Display**: Flight of Day, Squadron of Day, Cadet of Day, Cadre of Day based on scores
  - **Assigned Awards Section**: Visual cards showing all awards for selected date with color-coded icons
  - **Awards History**: Filterable list of all awards with date, recipient, and type
  - **Top Award Recipients**: Leaderboard showing who has earned the most awards
- **Award Types** (13 total):
  - Auto-eligible (based on highest daily score): Cadet of the Day, Cadre of the Day
  - Manual assignment: Flight Honor Graduate, Commandant's Award, Honor Cadet, Honor Cadre, Leadership Award, PT Excellence, Academic Excellence, Drill Award, Spirit Award, Most Improved, Other
- **Award Features**:
  - Manual assignment via "Assign Award" modal (Award Type, Recipient, Date, Notes)
  - Auto-assign daily awards with "Auto-Assign Daily" button
  - Filter by award type and date range
  - Delete awards (Commander only)
  - Color-coded icons for each award type
  - Auto-generated indicator for automatic awards
  - Recipient name, flight, squadron, and notes displayed

### Feb 24, 2026 - Point Tracking System
- **Point Tracking Page** (`/points`): Full implementation with:
  - **Flight Standings**: Ranked display of all 6 flights by total points
  - **Squadron Standings**: Aggregated scores for Squadrons 1-3
  - **Top Cadets**: Individual cadet rankings with merits/demerits
  - **Top Cadre**: Individual cadre rankings
- **Score Recording**: Record scores for flights, squadrons, or individuals
  - Categories: Barracks Inspection, Uniform Inspection, Drill Competition, PT Score, Academic Test, Punctuality (flight-level)
  - Individual categories: Individual PT, Individual Academic, Leadership Evaluation (cadets), Cadre Performance, Cadre Leadership
- **Merit/Demerit System**: Award or deduct points with reasons
- **Daily Awards**: View Flight/Squadron/Cadet/Cadre of the Day for any date
- **Flight-Based Permissions**:
  - **Commanders & Executive Cadre**: Full access to all flights
  - **Other staff**: Can only edit scores for their assigned flight
  - Permission badge displays "Full Access - All Flights" or specific assigned flights
- **Score History**: View recent scores and merits/demerits with timestamps

### Feb 24, 2026 - Schedule Filter Enhancement
- **Schedule Filter for All Users**: Previously editors-only, now visible to ALL members
  - Filter by: All Events, Staff Only, Squadron 1/2/3, Alpha/Bravo/Charlie/Delta/Echo/Foxtrot flights
  - Mobile and desktop versions both support filtering

### Feb 21, 2026 - Roles, Units & Granular Permissions System
- **Expanded Role System** (6 roles):
  - **Commander**: Full access to all features
  - **Finance**: Budget view/edit, analytics
  - **Plans & Programs**: Schedule/admin, roster edit
  - **Executive Cadre**: View-only with analytics
  - **Staff**: Roster/schedule edit, no budget
  - **Cadre**: View-only permissions
- **Updated Unit Structure**:
  - Staff, Support Cadre, Exec Cadre, Ops Cadre
  - Squadron 1 (Alpha, Bravo), Squadron 2 (Charlie, Delta), Squadron 3 (Echo, Foxtrot)
- **Granular Permissions System** (12 access types):
  - Dashboard, Roster (View/Edit), Schedule (View/Edit), Budget (View/Edit)
  - Analytics, Org Chart, Handbooks, Documents, Admin Panel
- **Admin Permissions Editor**:
  - Inline checkbox editor for each user
  - "Save Permissions" and "Reset to Role Defaults" buttons
  - Role-based default permissions automatically assigned at registration
- **Email Notifications** (SendGrid integration):
  - Approval email sent when user account is approved
  - HTML email with CAP branding

### Feb 21, 2026 - Member Profiles & User Approval System
- **Profile Page** (`/profile`): New page with 4 editable sections:
  - **Basic Information**: Name, email, phone, cell phone, gender, shirt size
  - **CAP Information**: CAPID, rank, unit, wing, region (squadron/flight read-only, set by admin)
  - **Address**: Street address, city, state, ZIP code
  - **Emergency Contact**: Contact name, phone, parent/guardian info (for cadets)
- **Profile Photo**: Upload profile photo (5MB limit, base64 storage), displayed in sidebar
- **Registration Updates**: 
  - Users can select "Staff/Senior Member" or "Cadre/Cadet" role during registration
  - New accounts are created with `is_approved=false` and require Commander approval
- **User Approval Workflow** (Admin page):
  - New "Pending Approval" tab showing users awaiting approval
  - "Find Matches" button searches roster by CAPID/email/name with confidence levels
  - "Link & Approve" auto-populates profile from roster participant data
  - "Direct Approve" approves user without linking to roster
- **Admin Page Reorganization**: 3 tabs (Pending Approval, All Users, Settings)

### Feb 21, 2026 - Analytics Dashboard with Export
- **Comprehensive Analytics Dashboard**: New `/analytics` page with 4 tabs:
  - **Overview Tab**: Role counts (Seniors, Staff, Cadre, Students) with average ages, Age Statistics (avg, min, max, range), Gender Distribution by Role table
  - **Demographics Tab**: Overall Gender Distribution bars, Rank Distribution grid, Average Age by Squadron/Flight
  - **Distribution Tab**: Wing Distribution (with percentages), Region Distribution, Tennessee Group Distribution, Squadron/Flight Distribution bars
  - **Pending Payments Tab**: Table of unpaid participants with contact info (email, phone, parent contact)
- **Export Functionality**: Export dropdown with 3 options:
  - Export as CSV (participant list)
  - Export as Excel (single sheet)
  - Full Report (Multi-sheet Excel with summaries)
- **Access Control**: Analytics visible only to Commander, Staff, and Finance roles
- **API Endpoints**:
  - `GET /api/participants/analytics/detailed` - Comprehensive analytics data
  - `GET /api/participants/pending-payments` - Unpaid participants with contact info
  - `GET /api/participants/analytics/export?format=csv|excel` - Single-sheet export
  - `GET /api/participants/analytics/summary-export` - Multi-sheet Excel report

### Feb 21, 2026 - Auto-Sync Roster to Budget
- **Automatic Budget Sync on Import**: When a roster is imported, the budget income items are automatically updated:
  - Senior Members Staff: Actual = total collected from seniors
  - Cadet Cadre: Actual = total collected from cadre members
  - Basic Students: Actual = total collected from student members
- **Notes Auto-Update**: Each budget item notes field shows count (e.g., "33 Students @ $250")
- **Food Planner Sync**: Participant count auto-updates from roster total
- **Variance Tracking**: Income items show collection percentage (33%, 27%, 24%)
- **Manual Sync Available**: `/api/participants/sync-to-budget` endpoint for manual sync

### Feb 21, 2026 - CAP Event Admin Report Import
- **Smart Excel Import**: Automatically maps 60+ CAP Admin Report columns to participant data
  - CAPID, Rank, Name, Unit, Wing, Region
  - Payment info: PaidInFull, AmountPaid
  - Contact: Email, Phone, Cell Phone, Address
  - Emergency Contact, Parent Contact
  - Unit/Wing CC info
  - Approvals: Unit Approved, Wing Approved, Slotted
  - Training: CPPT Expiration, First Aid, IS100, IS700
  - Last Encampment history
- **Auto-detect Participant Type**: Senior vs Cadet, Staff vs Student based on MbrType & StaffMember fields
- **Upsert by CAPID**: Updates existing participants, creates new ones
- **Stats Dashboard on Roster Page**: Shows real-time counts:
  - Total participants, Seniors (+ staff count), Cadets (+ cadre + student counts)
  - Payment status (paid/unpaid), Total collected
  - Wing/Unit approval counts
- **Enhanced Roster Table**: New columns for Wing, Paid (with amount), Approved (Unit/Wing badges)
- **Payment Filter**: Filter roster by Paid/Unpaid status
- **Auto-update Food Planner**: Updates participant count in food expense settings after import

### Feb 21, 2026 - Live Budget Tracking
- **Real-Time Variance Tracking**: Dashboard shows 6 key metrics:
  - Estimated Income vs Actual Income with variance
  - Estimated Expenses vs Actual Expenses with under/over budget indicator
  - Current Balance (actual income - actual expenses)
  - Payment Status progress (X/Y items paid with progress bar)
- **Inline Actual Value Editing**: Click any actual value to edit in-place
  - Save with checkmark, cancel with X
  - Quick API: PATCH `/api/budget/{id}/actual`
- **Mark as Paid Quick Action**: Green checkmark button in Actions column
  - Sets status = paid, payment_date = today
  - If actual is 0, sets actual = estimated
  - API: POST `/api/budget/{id}/mark-paid`
- **Variance Column**: New column showing:
  - Income items: Collection percentage (e.g., "88%", "0%")
  - Expense items: Under/over budget amount (e.g., "+$11,000.00", "-$500.00")
  - Color-coded badges (green = good, amber = warning, red = over)
- **Status Filter**: Filter items by Pending, Paid, or Cancelled
- **Payment Date Tracking**: Shows "Paid: YYYY-MM-DD" below item name

### Feb 21, 2026 - Enhanced Financial Tracker
- **Finance Role**: New role with exclusive budget access (alongside Commander)
  - Added to role enum in backend
  - Added to Admin page role dropdown
  - Budget endpoints restricted to Commander/Finance only
- **Summary Dashboard**: 5 metric cards showing:
  - Total Income (green)
  - Total Expenses (red)
  - Current Balance
  - Estimated Expenses
  - Budget Left
- **Food Expense Planner**: 
  - Editable cost per person per day ($13.15 default from TNWG Budget)
  - Total participants (170 default: 42 SM + 38 Cadre + 90 Students)
  - Total days (default 8 for July 17-24)
  - Live calculated total food budget
- **Receipt Upload**:
  - Upload images/PDFs to budget items
  - Preview receipts in modal
  - Delete receipts
- **TNWG Budget Template**:
  - 40 pre-configured budget items from 2026 TNWG Encampment Budget
  - Categories: Participant Fees, NHQ Allocations, Donations, Facility, DFAC Budget, Graduation, Commandants, Deputy Commander, Advanced Training School, Public Affairs, Logistics, Health Services, T-Shirts, Refunds
  - "TNWG Template" button to seed budget (only shows when budget is empty)
- **Enhanced Budget Table**:
  - Income/Expense type indicator
  - Vendor column
  - Receipt upload icon
  - Payment status badge (pending/paid/cancelled)
- **Access Control**: Non-Commander/Finance users see "Access Restricted" page

### Feb 21, 2026 - Push Notifications & Branding
- **Push Notifications**: 
  - Enable/disable notifications in Admin page and Schedule header
  - Send notifications to specific groups (all, staff, squadrons, flights)
  - Notification history for admins
  - Service Worker for background push handling
  - Auto-notification on schedule publish
- **Custom Branding**:
  - Tennessee Wing patch as main logo in sidebar
  - 60th CTG patch in encampment info section
  - 2026 Encampment banner on dashboard
  - "VTS Catoosa, GA" location display

### Feb 21, 2026 - Mobile Optimization
- **Mobile-First Schedule View**: Compact card-based layout for phones
  - Large date navigator with day labels
  - Swipe left/right to change days
  - Tap date to show day picker grid
  - Color-coded event borders
  - Compact time display (start → end)
- **Touch-Friendly UI**: 
  - Larger touch targets
  - Responsive breakpoints at 768px
  - Simplified header controls on mobile
- **Day Summary**: Compact 4-column grid on mobile

### Feb 21, 2026 - Flight-Specific Schedules & Real-Time Sync
- **User Unit Assignment**: Admin page now allows assigning users to squadrons and flights
  - Squadron options: Staff/Cadre, Squadron 1, 2, 3
  - Flight options: Alpha/Bravo (SQ1), Charlie/Delta (SQ2), Echo/Foxtrot (SQ3)
- **Target Groups for Events**: Events can now target specific groups
  - All Participants, Staff/Cadre
  - Squadrons: sq1, sq2, sq3
  - Flights: alpha, bravo, charlie, delta, echo, foxtrot
- **Real-Time Sync**: Schedule page auto-refreshes every 30 seconds
  - Version tracking in schedule settings
  - "Auto-sync" indicator in header
- **Filter Toggle**: Editors can switch between viewing all events or filtered view
- **Cadet View**: Cadets see only events targeting their flight + squadron + all-hands

### Feb 21, 2026 - Schedule Import & Publish
- Imported 113 events from Excel template
- Corrected dates to July 17-24, 2026
- Events categorized by type (training, ceremony, meal, PT, etc.)
- Color-coded event display
- Draft/Publish workflow implemented

### Earlier Implementation
- JWT authentication with role-based permissions
- Users, Participants, Budget, Documents, Org Chart APIs
- Dashboard with statistics
- Master Roster with search, filter, pagination
- Org Chart page with hierarchical tree view

## Architecture

### Tech Stack
- **Frontend**: React 18, Tailwind CSS, Shadcn/UI, Axios, Recharts
- **Backend**: FastAPI (Python), Motor (async MongoDB)
- **Database**: MongoDB
- **Auth**: JWT tokens, bcrypt password hashing

### Key API Endpoints
- `/api/auth/register`, `/api/auth/login`, `/api/auth/me` - Authentication
- `/api/users`, `/api/users/{id}/role`, `/api/users/{id}/unit` - User management
- `/api/participants`, `/api/participants/import` - Roster management
- `/api/participants/analytics/detailed`, `/api/participants/analytics/export` - Analytics
- `/api/participants/pending-payments` - Unpaid participants
- `/api/profile`, `/api/profile/photo` - User profile management
- `/api/users/pending`, `/api/users/{id}/approve`, `/api/users/{id}/link-participant` - User approval
- `/api/users/{id}/match-participants` - Find roster matches for user
- `/api/schedule`, `/api/schedule/import`, `/api/schedule/publish`, `/api/schedule/settings` - Schedule
- `/api/budget`, `/api/budget/summary`, `/api/budget/food-settings` - Financial tracking
- `/api/budget/{id}/receipt` - Receipt upload/delete
- `/api/org-chart/roles`, `/api/org-chart/seed-defaults` - Org chart
- **Point Tracking Endpoints**:
  - `/api/points/categories` - CRUD for score categories
  - `/api/points/categories/seed-defaults` - Seed default categories
  - `/api/points/scores` - Record and retrieve scores
  - `/api/points/merits` - Record and retrieve merits/demerits
  - `/api/points/leaderboard/flights` - Flight rankings
  - `/api/points/leaderboard/squadrons` - Squadron rankings
  - `/api/points/leaderboard/individuals` - Individual rankings
  - `/api/points/daily-winners` - Daily winners by category
  - `/api/points/cumulative-standings` - Overall standings

### Database Collections
- `users` - User accounts with role, squadron, flight
- `participants` - Roster participants
- `schedule` - Schedule events with target_groups
- `schedule_settings` - Draft/publish status and version
- `budget` - Budget items with receipt_url, item_type
- `food_expense_settings` - Cost per person per day settings
- `org_chart_roles` - Org chart positions
- `documents` - Handbooks and official docs
- `push_subscriptions` - Push notification subscriptions
- `score_categories` - Point tracking score categories
- `score_entries` - Individual score records
- `merit_demerit_entries` - Merit and demerit records

### Unit Structure
```
Staff/Cadre
├── Squadron 1
│   ├── Alpha Flight
│   └── Bravo Flight
├── Squadron 2
│   ├── Charlie Flight
│   └── Delta Flight
└── Squadron 3
    ├── Echo Flight
    └── Foxtrot Flight
```

## Prioritized Backlog

### P0 (Critical) - COMPLETED
- [x] Schedule import with date correction
- [x] Draft/Publish workflow for schedule
- [x] Real-time schedule sync
- [x] Flight-specific schedules
- [x] User unit assignment
- [x] Enhanced Financial Tracker with Finance role
- [x] Food expense planner (cost per person per day)
- [x] Analytics Dashboard with detailed attendee metrics
- [x] Export functionality (CSV, Excel, Full Report)
- [x] Member Profiles (editable basic, CAP, address, emergency contact info)
- [x] Profile photo upload
- [x] User approval workflow with roster linking
- [x] **Point Tracking System** (flight standings, squadron standings, individual rankings)
- [x] **Schedule Filter for All Users** (all members can filter by flight/squadron)

### P1 (High Priority)
- [ ] Implement Handbooks page (upload/view PDF documents)
- [ ] Implement Official Documents page (upload/view files)
- [ ] PDF export for roster reports

### P2 (Medium Priority)
- [ ] Add Rich Text/Markdown support for Org Chart responsibilities
- [ ] Email notifications for schedule changes
- [ ] Attendance tracking per event
- [ ] Bulk participant import validation
- [ ] OCR integration for receipt scanning (auto-extract vendor/amount)

### P3 (Low Priority)
- [ ] Flight/Squadron assignment interface in Roster
- [ ] Print-friendly roster and org chart views
- [ ] Budget export to Excel

## Test Credentials
- **Commander**: commander@test.com / test123 (auto-created, full access)
- **Finance**: finance_test@test.com / financepass123
- New users can register and will be assigned Cadet role by default

## Notes
- First registered user automatically becomes Commander
- Schedule dates: July 17-24, 2026
  - July 17: Staff/Cadre Arrival
  - July 18: Student In-Processing  
  - July 19-23: Training Days 1-5
  - July 24: Graduation Day
- Assigning a flight automatically sets the correct squadron
- Cadets without unit assignment see all events
- Budget access restricted to Commander and Finance roles only
- Food expense calculation: cost × participants × days
