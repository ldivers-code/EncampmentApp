# CAP Encampment Roster - Product Requirements Document

## Original Problem Statement
Create an interactive roster for a Civil Air Patrol encampment using uploaded Excel template. Include pages for handbooks, schedule, official documents and financial trackers. Role-based access with Commander, Staff, Finance, and Cadet roles.

## User Personas
1. **Commander** - Full access to all features, user management, CRUD on all entities
2. **Executive Staff** - Same permissions as Commander; for Commandant and Deputy Commander for Support positions (falls under Commander's authority)
3. **Staff** - Can edit roster, schedule, documents; assign users to units
4. **Finance** - Full budget access, manage expenses/income, upload receipts, food expense planning
5. **Cadet** - View-only access, sees only their unit's schedule, no budget access
6. **Health Services** - Full access to medication tracking, incident logging, custody management
7. **Dining Facility** - Meal plan management, view access to most pages

## System Structure (IMPORTANT)
**Two distinct types of records:**
1. **Users (Staff and Cadre)** - Created through account signup, have login access, NOT from spreadsheet
2. **Students** - Created ONLY from spreadsheet uploads, NO accounts, data records only

**Pre-defined Structure (DO NOT MODIFY):**
- Squadrons: 6th CTS, 21st CTS, 22nd CTS
- Flights: Alpha, Bravo (6th CTS), Charlie, Delta (21st CTS), Echo, Foxtrot (22nd CTS)
- Capacity: 15 students per flight, 90 total

## Core Requirements
- [x] Master Roster management with participant CRUD
- [x] Excel import for roster data
- [x] **Student Upload with Auto-Assignment** (NEW)
- [x] Schedule calendar with event management
- [x] Financial budget tracker with estimated vs actual
- [x] Handbooks document repository with file upload & object storage
- [x] Official documents section with file upload & object storage
- [x] Role-based access control (Commander/Executive Staff/Staff/Finance/Cadet/Health Services/Dining Facility)
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
- [x] Meal Plan Schedule (separate from Financial Tracker)
- [x] Receipt upload functionality
- [x] **Analytics Dashboard with detailed attendee metrics**
- [x] **Export functionality (CSV, Excel, Full Report)**
- [x] **Member Profiles with editable fields**
- [x] **Profile photo upload**
- [x] **User approval workflow for new accounts**
- [x] **Link users to roster participants by CAPID**
- [x] **Expanded role system (Commander, Finance, Plans & Programs, Executive Cadre, Staff, Cadre, Health Services, Dining Facility)**
- [x] **Updated unit structure (Staff, Support/Exec/Ops Cadre, Squadrons 1-3)**
- [x] **Granular permissions system (14 access types per user including health_view/health_full)**
- [x] **Admin inline permissions editor**
- [x] **SendGrid email notifications for account approval**
- [x] **Point Tracking System with flight-based permissions**
- [x] **Schedule filter dropdown for all users**
- [x] **Individual Awards Tracking System**
- [x] **My Flight Page with Flight Roster and Documents**
- [x] **Active Users / Who's Online Feature**
- [x] **Password Reset (Self-Service & Admin, 1-hour token expiry)**
- [x] **Profile Change Password**
- [x] **My Flight Points Tab (Flight-specific point tracking)**
- [x] **Receipt Repository (Finance Page)**
- [x] **Squadron Name Standardization (6th CTS, 21st CTS, 22nd CTS)**
- [x] **Daily Schedule on Dashboard (Today's Schedule quick view)**
- [x] **Flight Reporting System (Daily reports with 7 sections)**
- [x] **Role-Based Roster Visibility (Sensitive data restricted)**
- [x] **Logistics Module (10 sub-pages: Dashboard, Inventory, Lost & Found, Radios, Comms Log, Call Signs, Vehicles, Vehicle Log, Facilities, Supply Requests)**
- [x] **Training Officer Module (Blister checks, counseling logs, cadre issues)**

## What's Been Implemented

### Mar 26, 2026 - Auto-Assignment System
- **Automatic Flight Assignment Triggers**:
  - When student spreadsheet is uploaded
  - When new student records are created via API
  - When student records are updated (if no flight)
  - When `/api/students/auto-assign` endpoint is called
- **Assignment Protection**:
  - Students with existing valid flights are NEVER changed
  - Only assigns students where flight is empty/null
  - Case-insensitive flight validation (Alpha = alpha = ALPHA)
- **Distribution Algorithm** (weighted scoring, lower = better):
  - **Total Balance** (weight: 10): Even distribution across 6 flights
  - **Gender Balance** (weight: 5): Balance M/F ratio per flight
  - **Wing Distribution** (weight: 3): Spread students from same wing
  - **Unit Distribution** (weight: 3): Spread students from same home unit
  - **Age Balance** (weight: 2): Balance age tiers (young/mid/older)
- **Helper Functions**:
  - `get_age_tier()`: Categorizes ages into 3 tiers (12-13, 14-15, 16+)
  - `auto_assign_single_student()`: Assigns one student
  - `auto_assign_flights()`: Batch assigns multiple students
- **New Endpoint**: `/api/students/auto-assign`
  - POST to trigger assignment of all unassigned students

### Mar 26, 2026 - Role-Based Assignment Permissions
- **New Endpoint**: `/api/participants/{id}/assignment`
  - PUT endpoint for updating flight/squadron/position assignments
  - Role-based permission checks before any update
- **Permission Matrix**:
  - **Full Access** (Commander, Executive Staff, Plans & Programs, DCP, Staff): Can edit BOTH students AND cadre assignments
  - **Cadre Only** (Exec Cadre): Can ONLY edit cadre assignments, gets 403 for students with clear error message
- **Frontend UI Updates**:
  - Edit assignment button (pencil) only appears when user has permission
  - Exec Cadre sees edit button on Cadre tab only, not on Students tab
  - Commander/Staff see edit buttons on all tabs
- **Auto Squadron Assignment**: Setting a student flight automatically sets the matching squadron

### Mar 26, 2026 - Student Upload Feature with Auto-Assignment
- **Student Upload** (`/api/students/upload`):
  - Upload Excel files from CAP Event Admin Report
  - All uploaded records are marked as "First-Time Student"
  - Participant type set to "basic_student"
  - Creates student records, NOT user accounts
- **Auto-Flight Assignment**:
  - Balances students across 6 flights (max 15 per flight)
  - Considers gender balance (M/F distribution)
  - Spreads ranks to avoid grouping senior cadets
  - Manual assignments are preserved (not overridden)
- **Roster Page Tabs** (Staff | Cadre | Students):
  - Category tabs filter participants by type
  - Each tab shows count
  - Upload Students button only on Students tab
- **Flight Distribution Panel**:
  - Shows capacity per flight (e.g., "9/15")
  - Male/Female breakdown
  - Total utilization percentage
- **Student Detail View** (5 Sections):
  1. Basic Info: CAPID, Rank, Unit, Gender, Age, Wing
  2. Encampment Info: Squadron, Flight, Registration Status, Shirt Size, Conflicts, Comments
  3. Emergency Contact: Name, Phone
  4. Parent/Guardian Contact: Primary/Secondary/Emergency phones and emails
  5. Address: Full address with Addr2 support

### Mar 26, 2026 - Password Reset Feature (Updated)
- Token expiry changed from 24 hours to 1 hour per user request
- Profile page now has "Change Password" section
- Current password verification required for profile change

### Mar 9, 2026 - Role-Based Roster Data Visibility
- **Public Data (visible to everyone)**: Rank, Name, Flight, Squadron, Gender, Age, Type
- **Restricted Data (privileged roles only)**: Contact info (email, phone), Payment status, Approval status, Address, Emergency contacts, Notes
- **Privileged Roles**: Commander, Exec Cadre, Plans & Programs, Finance, Staff (includes Health Services)
- **Frontend Changes**: 
  - Table columns dynamically shown/hidden based on role
  - Payment filter hidden for non-privileged users
  - Participant detail modal shows "Restricted" placeholders for sensitive sections
- **Backend Changes**: API endpoints filter sensitive fields based on user role

### Mar 9, 2026 - Flight Reporting Role Auto-Detection
- **Auto-Detection**: System automatically detects reporter role based on user's position
  - Squadron Commander: Users with "squadron commander" or "sq cc" in position
  - Flight Commander: Users with "flight commander" or "flt cc" in position
  - Flight Sergeant: Default for cadre/staff without specific position
- **Role Restrictions**:
  - Cadre users can ONLY submit reports for their assigned flight
  - Warning message and disabled button when viewing other flights
  - Role selector is locked (non-editable) for cadre users
- **Exec Cadre Full Access**:
  - Can view reports from all flights
  - "Full Access - All Flights" header displayed
  - Can choose any reporter role when submitting
  - Can filter by specific flight or view all

### Mar 9, 2026 - Commander Issue Escalation Chain (UPDATED)
- **6-Level Escalation Chain Implementation**:
  - Flight Sergeant → Flight Commander → Squadron Commander → Exec Cadre → DCS & Commandant → Encampment Commander
  - Reports with commander issues now start at "flight_sergeant" level
  - Each level can escalate to the next level only (cannot skip levels)
  - Only "commander" role can escalate from DCS & Commandant to Encampment Commander
- **New Status Badges**: 
  - Flight Commander (yellow), Sq. Commander (amber), Exec Cadre (orange)
  - DCS & Commandant (rose), Encampment Cmdr (red), At Cmdr Level (dark red)
- **Escalation History**: Full audit trail showing all 5 escalation steps with timestamps
- **Dynamic Escalation Actions**:
  - Button text updates to show correct next level (e.g., "Escalate to Flight Commander")
  - Color intensity increases as escalation level rises
- **Permission Controls**:
  - Cadre can escalate from flight_sergeant level
  - Staff/Plans & Programs can escalate up to exec_cadre level
  - Exec Cadre can escalate to dcs_commandant level
  - Only Commander role can escalate to encampment_commander level
- **Notifications**: Automatic notifications sent to appropriate groups at each level
- **API Endpoints**:
  - `PUT /api/reports/{id}/escalate` - Validates chain progression, enforces permissions
  - `PUT /api/reports/{id}/resolve` - Mark any escalated report as resolved
  - `PUT /api/reports/{id}/resolve` - Mark escalated report as resolved

### Mar 9, 2026 - Flight Reporting System
- **Flight Reports Feature** under My Flight page:
  - **Submit Daily Report Modal**: Full form with all 7 required sections from the Encampment Reporting Guide
  - **7 Report Sections**: Morale, Safety Concerns, Discipline Issues, Training Performance, Significant Events, Recommendations, Commander Issue Items
  - **Reporter Roles**: Flight Sergeant, Flight Commander, Squadron Commander
  - **Status Tracking**: Submitted, Reviewed, Escalated
  - **Commander Issues Escalation**: Auto-flags reports with Commander Issue Items checked
  - **Notifications**: Creates notification for commanders when reports have escalation items
  - **Deadline Settings**: Editable daily report deadline (default 21:00), admin-configurable
  - **View Reports**: Click to view full report details in modal
  - **Mark as Reviewed**: Commanders can mark reports as reviewed
- **Backend API Endpoints**:
  - `GET/POST /api/reports/settings` - Deadline configuration
  - `POST /api/reports` - Submit new report
  - `GET /api/reports` - Get reports (filtered by access level)
  - `GET /api/reports/{id}` - Get specific report
  - `PUT /api/reports/{id}/review` - Mark as reviewed
  - `GET /api/reports/commander-issues` - Get escalated reports
  - `DELETE /api/reports/{id}` - Delete report
- **Access Control**: Reports visible based on user's flight/squadron assignment

### Mar 9, 2026 - Daily Schedule Dashboard Widget
- **Today's Schedule Widget** on Dashboard page:
  - **"Happening Now" highlight**: Shows currently active event with pulsing indicator
  - **Event List**: All events for today with times, titles, locations, and uniform info
  - **Event Type Color Coding**: Color-coded left borders (training=blue, meal=amber, pt=red, etc.)
  - **Quick Stats Footer**: Shows total events count and current date
  - **"View Full Schedule" Button**: Links to full schedule page
- **Smart Date Handling**: Shows encampment Day 1 (July 17) when outside encampment dates
- **Scrollable List**: Events list scrolls within fixed height container

### Mar 9, 2026 - Squadron Name Standardization
- **Replaced all "Squadron 1/2/3" references** with proper designations:
  - Squadron 1 → 6th CTS (6th Cadet Training Squadron)
  - Squadron 2 → 21st CTS (21st Cadet Training Squadron)
  - Squadron 3 → 22nd CTS (22nd Cadet Training Squadron)
- **Updated Files**:
  - `AdminPage.js`: Squadron dropdown and flight-to-squadron mappings
  - `NotificationManager.js`: Target group options for notifications
  - `SchedulePage.js`: Filter options and flight-to-squadron logic
  - `server.py`: API endpoints (/api/squadrons, /api/flights), org chart defaults, validation logic
- **API Changes**: `/api/squadrons` now returns `{value: "6th_cts", label: "6th CTS"}` format
- **Verified**: All UI components and API endpoints display correct squadron names

### Feb 24, 2026 - Receipt Repository
- **Receipt Repository Tab** on Finance/Budget page:
  - **Stats Dashboard**: Total Receipts, Documented Expenses, Missing Receipts counts
  - **Search Bar**: Filter receipts by item name, category, or vendor
  - **Receipt Gallery**: Grid display of receipt cards with:
    - Image preview (or PDF icon for documents)
    - Item name, category, actual amount
    - Vendor name
    - View, Download, Delete action buttons
  - **Receipt Preview Modal**: Full-size view with details (Category, Amount, Vendor, Filename)
  - **Missing Receipts Alert**: Shows expense items that don't have receipts uploaded
- **Tab Badge**: Shows count of uploaded receipts
- **Integrated**: Uses existing receipt upload functionality for budget items

### Feb 24, 2026 - My Flight Points Tab
- **Points Tab** added to My Flight page with:
  - **Flight Standing Card**: Shows flight's rank and total points (e.g., "#1 - 95 points")
  - **Flight Cadets List**: Only cadets assigned to the selected flight
  - **Ranking Display**: Gold/silver/bronze badges for top 3 cadets
  - **Quick Merit/Demerit**: +/- buttons on each cadet row
  - **Point Totals**: Current points shown for each cadet
- **Merit/Demerit Modal**:
  - Pre-filled cadet name
  - Type dropdown (Merit/Demerit)
  - Points input (default: 5)
  - Reason textarea (required)
  - Color-coded buttons (green for merit, red for demerit)
- **Recent Activity**: Shows recent merits/demerits for the flight's cadets
- **Integration**: Connected to main Point Tracker - all data syncs
- **Navigation**: "View Full Point Tracker & Leaderboards" link

### Feb 24, 2026 - Password Reset Feature
- **Self-Service Password Reset** (`/forgot-password`):
  - User enters email and CAPID for identity verification
  - Reset link sent via email (when SendGrid configured)
  - Token valid for 1 hour (updated from 24 hours)
  - Security: Same response message whether user exists or not (no info leakage)
- **Admin Password Reset** (Admin Panel > All Users):
  - Key icon button for each user
  - Modal with password + confirm password inputs
  - Minimum 6 character validation
- **Reset Password Page** (`/reset-password?token=xxx`):
  - Token verification on page load
  - Shows error for invalid/expired tokens
  - Password + confirm password form
  - Success message with redirect to login
- **Profile Page Change Password**:
  - Expandable "Change Password" section on Profile page
  - Requires current password verification
  - New password + confirm new password fields
  - Minimum 6 character validation
  - Show/hide password toggle
- **Security Features**:
  - CAPID verification prevents unauthorized reset requests
  - Tokens invalidated after use
  - 1-hour token expiry
  - Current password verification for profile change

### Feb 24, 2026 - Active Users / Who's Online
- **Real-time Presence System** with heartbeat tracking:
  - Heartbeat sent every 30 seconds while app is open
  - Users considered "active" if heartbeat within last 60 seconds
  - Automatic offline marking when tab closes or user logs out
- **Sidebar Indicator**: Shows "X online now" with green pulse animation
- **Dashboard Widget**: "Who's Online" card showing:
  - Active user count with green indicator
  - List of online users with name, role, and avatar
  - Green status dot for each active user
- **Backend Endpoints**:
  - `POST /api/presence/heartbeat` - Update user's active timestamp
  - `GET /api/presence/active-users` - Get list of currently active users
  - `POST /api/presence/offline` - Mark user as offline

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
  - Filter by: All Events, Staff Only, 6th CTS/21st CTS/22nd CTS, Alpha/Bravo/Charlie/Delta/Echo/Foxtrot flights
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
  - 6th CTS (Alpha, Bravo), 21st CTS (Charlie, Delta), 22nd CTS (Echo, Foxtrot)
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
  - Squadron options: Staff/Cadre, 6th CTS, 21st CTS, 22nd CTS
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
├── 6th CTS (6th Cadet Training Squadron)
│   ├── Alpha Flight
│   └── Bravo Flight
├── 21st CTS (21st Cadet Training Squadron)
│   ├── Charlie Flight
│   └── Delta Flight
└── 22nd CTS (22nd Cadet Training Squadron)
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
- [x] **Analytics Page Empty State Handling** (gracefully shows zeros and "No data" messages when roster is empty)
- [x] **Gender Analytics Fix** (handles MALE/FEMALE values in addition to M/F)

### P1 (High Priority) - COMPLETED
- [x] **Header buttons CSS fix** (dropdown visibility and z-index issue resolved)
- [x] **Roster Import Enhancement** (supports CAP Admin Reports without CAPID column by auto-generating unique identifiers)
- [x] **Google Sheets Live Sync** (automatic hourly sync from Google Sheets to update roster data)
- [x] **Org Chart Google Sheets Integration** (parses org chart spreadsheet and updates roles with assigned staff names)
- [x] **Flight Assignment Auto-Sync** (parses student flight assignments from spreadsheet rows 45+ and auto-assigns to flights/squadrons)
- [x] **Squadron Designations Updated** (6th CTS, 21st CTS, 22nd CTS with proper names, mascots, and patches)
- [x] **Uniform of the Day** (Dashboard widget for daily uniform updates with admin controls)
- [x] **Weather Flag System** (Heat condition flags with CAP-compliant guidelines, rest schedules, and activity restrictions)

### P1 (High Priority) - PENDING
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

## Health Services Module (Added Mar 10, 2026)

### Overview
Comprehensive health tracking system for managing cadet medications, incidents, and custody logs during encampment.

### User Roles & Permissions
- **Health Services**: Full read/write access to all health data (medications, incidents, custody)
- **Commander**: Full read/write access to all health data
- **Staff**: View-only access to basic health info (incidents, restrictions) - NO medication details

### Features Implemented
- [x] Health Services Dashboard with summary cards
- [x] Real-time medication due tracking (next hour / overdue)
- [x] Open incidents tracking and status management
- [x] Cadet search by name, CAPID, squadron, flight
- [x] Quick Actions for reports, audit log, settings
- [x] Auto-refresh capability (2-minute intervals)

### API Endpoints Created
- `/api/health/settings` - Event configuration
- `/api/health/reference-lists` - Dropdown values
- `/api/health/cadet/{id}/summary` - Health summary for cadet
- `/api/health/cadet/{id}/medications` - Medication profiles CRUD
- `/api/health/cadet/{id}/medication-log` - Administration history (append-only)
- `/api/health/cadet/{id}/incidents` - Incident history (append-only)
- `/api/health/cadet/{id}/custody-log` - Custody actions (append-only)
- `/api/health/dashboard/summary` - Dashboard metrics
- `/api/health/dashboard/meds-due` - Medications due now
- `/api/health/dashboard/overdue` - Overdue medications
- `/api/health/dashboard/open-incidents` - Active incidents
- `/api/health/search/cadets` - Search with filters
- `/api/health/audit-log` - Audit trail

### Database Collections (MongoDB)
- `hs_cadet_master` - Cadet health summary records
- `hs_medication_profiles` - Medication profiles per cadet
- `hs_medication_log` - Append-only administration log
- `hs_incident_log` - Append-only incident log
- `hs_custody_log` - Append-only custody actions
- `hs_audit_log` - All changes tracked
- `hs_settings` - Event configuration

### Still To Complete
- [ ] Google Sheets export/sync for historical reporting
- [ ] Historical reports page (/health/reports)
- [ ] Audit log viewer page (/health/audit)
- [ ] Health settings page (/health/settings)

### Completed (March 12, 2026) - Status Board System
- [x] **Status Board - Projected Display System (Full Implementation)**
  - **Control View** (`/status-control`): 7-tab management interface (Flights, Schedule, Issues, Announcements, Resources, Settings, Audit Log) with full CRUD, emergency banner controls, seed data, and "Open Display" link
  - **Display View** (`/status-display`): Dark-themed projector wallboard with 4 auto-rotating modes (Command Dashboard, Schedule, Logistics, Safety), live clock, Heat Category indicator, flight status cards, active issues, upcoming events, scrolling announcement ticker
  - Emergency banner system (commander/exec_staff only) with pulsing red alert
  - Auto-refresh every 15s, auto-rotate modes every 25s (configurable)
  - Keyboard navigation: ArrowRight/Left for modes, F for fullscreen
  - Role-based permissions for editing vs viewing
  - Audit trail for all changes
  - Sample data seed for testing
  - Backend: Factory pattern router in /app/backend/statusboard.py with 22+ API endpoints
  - MongoDB collections: sb_flights, sb_issues, sb_announcements, sb_resources, sb_schedule_events, sb_display_settings, sb_audit_log
  - Testing: 24 backend tests (100%), 17 frontend features verified (100%)

### Completed (March 12, 2026) - Sidebar & UI Fixes
- [x] **Logistics Module - Full Implementation (10 sub-pages)**
  - Dashboard: Real-time stats (11 metric cards), overdue alerts, quick actions
  - Inventory Management: CRUD with categories, quantity tracking, low stock alerts, search
  - Lost & Found: Item logging with claim workflow (unclaimed → claimed)
  - Radio Check Out/Check In: Full checkout/checkin lifecycle, overdue auto-detection, extend/reset
  - Communications Log: Time-stamped entries with call signs, operators, priority levels
  - Call Sign Directory: Assignment tracking with staff categories, alternates, status management
  - Vehicle Assignments: Assign/return workflow with fuel tracking, overdue detection
  - Vehicle Log: Trip logging with mileage calculation, fuel purchase tracking
  - Facilities & Equipment: Status management (ready/in_use/needs_attention/out_of_service)
  - Supply Requests: Full workflow (pending → approved → issued → completed), priority levels
  - Role-based access: commander, executive_staff, logistics can create/edit/delete; others view-only
  - Backend: Factory pattern router in /app/backend/logistics.py with 25+ API endpoints
  - Frontend: Tabbed UI with modals, status badges, search/filter in /app/frontend/src/pages/LogisticsPage.js
  - MongoDB collections: log_inventory, log_lost_found, log_radios, log_comms, log_callsigns, log_vehicles, log_vehicle_log, log_facilities, log_supply_requests
- [x] **Backend Dependency Injection Fix**: Resolved FastAPI module loading error using factory pattern (create_logistics_router)
- [x] **Login Case-Insensitivity Fix**: Email matching now case-insensitive with whitespace trimming
- [x] Comprehensive testing: 20 backend tests pass (100%), 14 frontend features verified (100%)

### Completed (March 10, 2026)
- [x] CadetHealthSection component integrated into cadet detail modal
- [x] Medical Data Import feature (Import button on Health Services Dashboard)
  - Supports AllergiesReport.xlsx (per-cadet allergy data)
  - Supports OTCMedicationApprovalsReport.xlsx (per-cadet OTC medication approvals)
  - Data matched to roster participants by CAPID
  - Duplicate detection for allergies; upsert for OTC approvals
- [x] Allergies tab in CadetHealthSection (displays allergy details, severity indicators)
- [x] OTC Approvals tab in CadetHealthSection (13 medication approval grid)
- [x] Import Summary cards on Health Services Dashboard
- [x] MongoDB collections: hs_allergies, hs_otc_approvals
- [x] Backend endpoints: POST /api/health/import/medical-data, GET /api/health/cadet/{capid}/allergies, GET /api/health/cadet/{capid}/otc-approvals, GET /api/health/import/summary

### Mar 13, 2026 - CSS Header Cutoff Bug Fix (P0)
- **Fixed recurring global CSS bug** where header action buttons and dropdowns were cut off or appeared behind other elements
- **Root causes identified and fixed**:
  1. `overflow-x-hidden` on SchedulePage.js was clipping custom dropdown menus - REMOVED
  2. Main content wrapper in Sidebar.js lacked `overflow-visible` - ADDED
  3. Custom dropdown z-index on SchedulePage was too low (z-20) - INCREASED to z-50
  4. Radix UI popper content had no guaranteed z-index - ADDED global CSS rule (z-index: 100)
  5. Roster page header buttons (Import CAP Report, Add Participant) overflowed at 1280px viewport - Changed responsive breakpoint from `sm:flex-row` to `2xl:flex-row`
- **Files modified**: Sidebar.js, SchedulePage.js, RosterPage.js, index.css
- **Testing results**: 11/12 tests passed initially, then remaining Roster header overflow fixed

### Mar 13, 2026 - Favicon Update
- Updated app favicon to 60th Cadet Training Group (60th CTG) patch
- Generated ICO format with multiple sizes (16x16, 32x32, 48x48, 64x64)
- Added apple-touch-icon link tag for mobile devices
- **Files modified**: public/favicon.ico, public/favicon-new.png, public/index.html


### Mar 13, 2026 - Handbooks & Documents Upload System
- **Full file upload system** with Emergent Object Storage integration
- **Handbooks Page**: Complete rewrite with drag-and-drop file upload, categories (SOPs, Training Guides, Cadet/Staff Handbook, Regulations, References), search, filter, download
- **Documents Page**: Complete rewrite with file upload, document types (Official Document, Form/CAPF, Reference, Checklist, Regulation/Policy), search, type filter, download
- **Backend endpoints**:
  - `POST /api/documents/upload` - Multipart file upload to object storage
  - `GET /api/documents/{id}/download` - Download file with auth
  - `POST /api/documents/{id}/replace-file` - Replace file attachment
- **Upload permissions**: Commander, Executive Staff, Staff, Exec Cadre, Training Officer, Health Services, Plans & Programs, Logistics, Finance (all roles except Cadre)
- **View/download**: All users including Cadre
- **File support**: All file types, no size limits
- **New files**: `backend/file_storage.py` (object storage module)
- **Modified files**: `server.py`, `api.js`, `AuthContext.js`, `HandbooksPage.js`, `DocumentsPage.js`
- **MongoDB**: Uses existing `documents` collection with new fields: `storage_path`, `file_name`, `file_size`, `file_type`
- **Testing**: 13/13 backend tests passed, 100% frontend tests passed

### Mar 13, 2026 - Document Preview Feature
- **In-browser document preview** for PDFs, images (PNG, JPG, GIF, SVG, WebP), and text files (TXT, CSV, JSON, XML, Markdown)
- **Backend**: `GET /api/documents/{id}/preview` - serves file inline (Content-Disposition: inline)
- **Frontend**: New `DocumentPreview.js` shared component with full-screen modal
- Preview/View buttons on both Handbooks and Documents pages
- Smart button logic: "Preview" for files with storage, "View" for text content-only docs, "Download" always available
- Bug fix: content-only docs infinite loading state resolved
- **Testing**: 19/19 backend tests passed, 100% frontend tests passed



## Notes
- First registered user automatically becomes Commander
- Schedule dates: July 17-24, 2026
  - July 17: Staff/Cadre Arrival
  - July 18: Student In-Processing  
  - July 19-23: Training Days 1-5
  - July 24: Graduation Day
- Assigning a flight automatically sets the correct squadron
- Cadets without unit assignment see all events
- Budget access restricted to Commander, Executive Staff, and Finance roles only
- Meal Plan editable by: Commander, Executive Staff (DCS), Plans & Programs, Dining Facility, DCP
- Health Services permissions: health_view (basic info) and health_full (all data)
- Dining Facility role: view all pages except Admin and Health Services, edit only Meal Plan

### Mar 13, 2026 - Meal Plan Schedule & Dining Facility Role
- **New Meal Plan Schedule page** with weekly calendar view, color-coded meal types (Breakfast, Lunch, Dinner, Snack)
- **Removed Food Planner** from Financial Tracker (kept all other budget features intact)
- **New "Dining Facility" role** with view access to all pages EXCEPT admin and health services, edit privileges ONLY for Meal Plan Schedule
- **Meal Plan CRUD**: Full create/edit/delete with date, meal type, menu items, time, headcount, location, dietary notes
- **Backend**: `MEAL_PLAN_EDITOR_ROLES`, `dining_facility` role in UserRole, `meal_plans` MongoDB collection
- **Frontend**: `MealPlanPage.js`, `canEditMealPlan()` in AuthContext, updated Sidebar navigation
- **Testing**: 15/15 backend tests passed, 100% frontend tests passed
