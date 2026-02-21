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

## What's Been Implemented

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
- `/api/schedule`, `/api/schedule/import`, `/api/schedule/publish`, `/api/schedule/settings` - Schedule
- `/api/budget`, `/api/budget/summary`, `/api/budget/food-settings` - Financial tracking
- `/api/budget/{id}/receipt` - Receipt upload/delete
- `/api/org-chart/roles`, `/api/org-chart/seed-defaults` - Org chart

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
