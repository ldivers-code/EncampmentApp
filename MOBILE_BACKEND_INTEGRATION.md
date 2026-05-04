# TNWG Encampment Hub — Mobile Backend Integration Guide

> **This document is the single source of truth for connecting a mobile app to the existing backend.**
> The backend serves BOTH the web app and mobile app simultaneously. No backend changes required.

---

## 1. API Base URL

| Environment | URL |
|-------------|-----|
| **Production** | `https://tnwing-preview.emergent.host/api` |
| **Preview/Dev** | `https://cadre-hub.preview.emergentagent.com/api` |

All endpoints are prefixed with `/api`. Example: `POST https://tnwing-preview.emergent.host/api/auth/login`

---

## 2. Authentication Flow (Mobile)

The backend accepts JWT tokens via **three methods** (checked in this order):

1. `Cookie: access_token=<jwt>` — used by the web app
2. `Authorization: Bearer <jwt>` — **use this for mobile**
3. `?auth=<jwt>` — query param fallback (for image `src` tags)

### Login

```
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",    // or CAPID like "662519"
  "password": "userpassword"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "John Smith",
    "role": "cadre",
    "capid": "662519",
    "flight": "alpha",
    "squadron": null,
    "is_approved": true,
    "linked_participant_id": "uuid-or-null",
    "honor_agreement_signed": true,
    "permissions": { "dashboard": true, "roster_view": true, ... },
    "photo_url": "https://..." // or null
  }
}
```

**Mobile implementation:**
1. Call `POST /api/auth/login`
2. Store the `access_token` in secure storage (iOS Keychain / Android EncryptedSharedPrefs)
3. Attach to every subsequent request: `Authorization: Bearer <token>`
4. Check `user.is_approved` — if `false`, show "pending approval" screen
5. Check `user.honor_agreement_signed` — if `false`, show honor agreement modal

### Token Details

| Property | Value |
|----------|-------|
| Algorithm | HS256 |
| Expiry | 24 hours |
| Payload | `{ "sub": "<user_id>", "role": "<role>", "exp": <unix_ts> }` |

### Register

```
POST /api/auth/register
Content-Type: application/json

{
  "email": "newuser@cap.gov",
  "password": "Password123",
  "name": "Jane Doe",
  "role": "cadre",            // optional, default "staff"
  "capid": "789012"           // optional
}
```

New accounts require admin approval (`is_approved` starts as `false`).

### Logout

```
POST /api/auth/logout
Authorization: Bearer <token>
```

### Current User

```
GET /api/auth/me
Authorization: Bearer <token>
```

Returns the full user object (same shape as login response `.user`).

### Password Reset (no auth needed)

```
POST /api/auth/forgot-password     { "email": "user@cap.gov" }
POST /api/auth/verify-reset-token  { "token": "abc123" }
POST /api/auth/reset-password      { "token": "abc123", "new_password": "NewPass123" }
```

---

## 3. User Roles & Permissions (19 roles)

### Role Groups

| Group | Roles | Access Level |
|-------|-------|-------------|
| **Command** | `dcp`, `commander` | Full access to everything |
| **Senior Staff** | `executive_staff`, `training_officer`, `logistics`, `finance`, `plans_programs`, `health_services`, `dining_facility`, `staff` | Module-specific + general read |
| **Cadre** | `exec_cadre`, `cadre`, `squadron_commander` | Flight/squadron scope + cadre tools |
| **Support** | `support_logistics`, `support_comms`, `support_pa`, `support_dining`, `support_health` | Limited to their support area |
| **Parent** | `parent` | Read-only: own cadet's data only |

### Per-User Permission Overrides

Each user has a `permissions` object that can override role defaults:

```json
{
  "dashboard": true,
  "roster_view": true,
  "roster_edit": true,
  "schedule_view": true,
  "schedule_edit": true,
  "page_analytics": true,
  "page_health": false,
  "page_training": true,
  "page_check_in": true,
  "page_barracks": true,
  "page_logistics": true,
  "page_status_board": true,
  "page_parent_portal": false
}
```

Use these to gate mobile screen visibility.

---

## 4. Database (Read-Only Reference)

**Engine:** MongoDB
**Collections:** 56 active collections
**Key record counts:**

| Collection | Records | Purpose |
|-----------|---------|---------|
| `users` | 21 | App accounts |
| `participants` | 176 | Full roster (students + cadre + staff) |
| `schedule` | 207 | Events |
| `assignments` | 28 | Google Classroom-style |
| `assignment_submissions` | 6 | Student work |
| `notifications` | 145 | Notification records |
| `user_notifications` | 293 | Per-user delivery |
| `budget` | 47 | Financial line items |
| `receipt_uploads` | 11 | OCR receipt data |
| `org_chart_roles` | 101 | Org chart positions |
| `hs_otc_approvals` | 96 | OTC med permissions |
| `hs_allergies` | 31 | Allergy records |
| `score_categories` | 11 | Point categories |
| `meal_plans` | 4 | Meal periods |
| `documents` | 5 | Uploaded docs |

**DO NOT** create, drop, or seed collections. The web app and mobile app share the same database.

---

## 5. Environment Variables (Mobile App)

The mobile app only needs:

```env
API_BASE_URL=https://tnwing-preview.emergent.host/api
```

All secrets (JWT_SECRET, MONGO_URL, SENDGRID, etc.) live server-side only. The mobile app never sees them.

### Backend env vars (for reference — DO NOT duplicate in mobile):

| Variable | Purpose | Mobile needs it? |
|----------|---------|------------------|
| `MONGO_URL` | Database connection | No (server only) |
| `DB_NAME` | Database name | No (server only) |
| `JWT_SECRET` | Token signing | No (server only) |
| `SENDGRID_API_KEY` | Email sending | No (server only) |
| `SENDGRID_SENDER_EMAIL` | From address | No (server only) |
| `EMERGENT_LLM_KEY` | GPT-4o OCR | No (server only) |
| `CORS_ORIGINS` | Allowed origins | **Yes — add mobile origin if needed** |
| `VAPID_PUBLIC_KEY` | Web push | Mobile uses FCM/APNS instead |
| `VAPID_PRIVATE_KEY` | Web push | No (server only) |
| `APP_URL` | Frontend URL | No (server only) |

---

## 6. Complete API Endpoint Reference (287 endpoints)

### Authentication (21 endpoints)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/auth/register` | No | Create new account (pending approval) |
| `POST` | `/api/auth/login` | No | Login → returns JWT + user |
| `POST` | `/api/auth/logout` | Yes | Invalidate session |
| `GET` | `/api/auth/me` | Yes | Get current user profile |
| `POST` | `/api/auth/sign-honor-agreement` | Yes | Sign the honor agreement |
| `POST` | `/api/auth/send-honor-agreement-reminders` | Yes | Send email reminders |
| `GET` | `/api/auth/honor-agreement-status` | Yes | Get agreement status for all users |
| `POST` | `/api/auth/forgot-password` | No | Request password reset email |
| `POST` | `/api/auth/reset-password` | No | Complete password reset |
| `POST` | `/api/auth/verify-reset-token` | No | Verify reset token validity |
| `POST` | `/api/users/{user_id}/reset-password` | Yes | Admin: reset user's password |
| `POST` | `/api/presence/heartbeat` | Yes | Update active/online status |
| `GET` | `/api/presence/active-users` | Yes | Get who's online |
| `POST` | `/api/presence/offline` | Yes | Set self as offline |
| `GET` | `/api/profile` | Yes | Get own profile |
| `PUT` | `/api/profile` | Yes | Update own profile |
| `POST` | `/api/profile/photo` | Yes | Upload profile photo |
| `DELETE` | `/api/profile/photo` | Yes | Remove profile photo |
| `POST` | `/api/profile/change-password` | Yes | Change own password |
| `GET` | `/api/profile/nav-order` | Yes | Get saved nav order |
| `PUT` | `/api/profile/nav-order` | Yes | Save custom nav order |

### Roster / Participants (20 endpoints)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/participants` | Yes | Get all participants (filters: flight, type, squadron) |
| `GET` | `/api/participants/by-flight` | Yes | Participants grouped by flight |
| `GET` | `/api/participants/stats` | Yes | Roster statistics |
| `GET` | `/api/participants/analytics/detailed` | Yes | Detailed analytics |
| `GET` | `/api/participants/pending-payments` | Yes | Participants with unpaid fees |
| `GET` | `/api/participants/analytics/export` | Yes | Export analytics CSV |
| `GET` | `/api/participants/analytics/summary-export` | Yes | Summary export |
| `GET` | `/api/participants/export-pdf` | Yes | Export roster PDF |
| `GET` | `/api/participants/{id}` | Yes | Single participant detail |
| `POST` | `/api/participants` | Yes | Create participant |
| `PUT` | `/api/participants/{id}` | Yes | Update participant |
| `DELETE` | `/api/participants/{id}` | Yes | Delete participant |
| `PUT` | `/api/participants/{id}/assignment` | Yes | Assign flight/squadron/position |
| `POST` | `/api/participants/{id}/remove` | Yes | Soft remove |
| `POST` | `/api/participants/{id}/reinstate` | Yes | Reinstate removed |
| `POST` | `/api/participants/bulk-reset/preview` | Yes | Preview annual reset |
| `POST` | `/api/participants/bulk-reset/execute` | Yes | Execute annual reset (Commander/DCP) |
| `POST` | `/api/participants/bulk-reset/clear-all` | Yes | Clear all (Commander/DCP) |
| `POST` | `/api/participants/import` | Yes | Import from Excel |
| `POST` | `/api/participants/{id}/photo` | Yes | Upload cadet photo |

### Schedule (13 endpoints)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/schedule` | Yes | All events |
| `GET` | `/api/schedule/settings` | Yes | Schedule publish status |
| `POST` | `/api/schedule/publish` | Yes | Publish schedule |
| `POST` | `/api/schedule/unpublish` | Yes | Unpublish |
| `POST` | `/api/schedule` | Yes | Create event |
| `PUT` | `/api/schedule/{event_id}` | Yes | Update event |
| `DELETE` | `/api/schedule/{event_id}` | Yes | Delete event |
| `POST` | `/api/schedule/import` | Yes | Import from Excel |
| `DELETE` | `/api/schedule/clear` | Yes | Clear all events |
| `GET` | `/api/schedule-changes` | Yes | Get change requests |
| `POST` | `/api/schedule-changes` | Yes | Submit change request |
| `PUT` | `/api/schedule-changes/{id}/review` | Yes | Approve/deny change |
| `GET` | `/api/schedule-changes/pending-count` | Yes | Pending count |

### My Flight (7 endpoints)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/my-flight` | Yes | Current user's flight info |
| `GET` | `/api/flights` | Yes | List all flights |
| `GET` | `/api/squadrons` | Yes | List all squadrons |
| `GET` | `/api/flights/{flight}/roster` | Yes | Flight roster |
| `GET` | `/api/squadrons/{squadron}/roster` | Yes | Squadron roster |
| `GET` | `/api/flights/{flight}/leadership` | Yes | Chain of command (auto-populated from cadre positions) |
| `PUT` | `/api/flights/{flight}/leadership` | Yes | Manual leadership override |

### Health Services (41 endpoints)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/health/settings` | Yes | Health module config |
| `POST` | `/api/health/settings` | Yes | Update config |
| `GET` | `/api/health/reference-lists` | Yes | Medication/allergy reference data |
| `GET` | `/api/health/cadet/{id}/summary` | Yes | Cadet health summary |
| `GET` | `/api/health/cadet/by-capid/{capid}/summary` | Yes | Lookup by CAPID |
| `GET/POST` | `/api/health/cadet/{id}/medications` | Yes | Medication profiles |
| `PUT` | `/api/health/medications/{id}` | Yes | Update medication |
| `PUT` | `/api/health/medications/{id}/deactivate` | Yes | Deactivate medication |
| `GET/POST` | `/api/health/cadet/{id}/medication-log` | Yes | Medication log entries |
| `GET/POST` | `/api/health/cadet/{id}/incidents` | Yes | Health incidents |
| `PUT` | `/api/health/incidents/{id}/status` | Yes | Update incident status |
| `GET/POST` | `/api/health/cadet/{id}/custody-log` | Yes | Custody log |
| `PUT` | `/api/health/cadet/{id}/status` | Yes | Update cadet health status |
| `GET` | `/api/health/dashboard/meds-due` | Yes | Meds due now |
| `GET` | `/api/health/dashboard/overdue` | Yes | Overdue meds |
| `GET` | `/api/health/dashboard/open-incidents` | Yes | Open incidents |
| `GET` | `/api/health/dashboard/summary` | Yes | Dashboard summary |
| `GET` | `/api/health/medical-roster` | Yes | Full medical roster |
| `GET` | `/api/health/cadet/{id}/full-profile` | Yes | Complete health profile |
| `GET/POST` | `/api/health/cadet/{id}/allergies` | Yes | Allergy records |
| `PUT/DELETE` | `/api/health/allergies/{id}` | Yes | Manage allergy |
| `GET/PUT` | `/api/health/cadet/{id}/otc-approvals` | Yes | OTC permissions |
| `GET/POST` | `/api/health/cadet/{id}/med-diary` | Yes | Daily medication diary |
| `GET` | `/api/health/med-diary` | Yes | All diary entries (filter by date) |
| `PUT/DELETE` | `/api/health/med-diary/{id}` | Yes | Manage diary entry |
| `GET/POST` | `/api/health/cadet/{id}/supplements` | Yes | Non-Rx supplements |
| `PUT/DELETE` | `/api/health/supplements/{id}` | Yes | Manage supplement |

### Check-In (12 endpoints)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/check-in/roster` | Yes | Check-in roster with step status |
| `GET` | `/api/check-in/summary` | Yes | Check-in summary stats |
| `POST` | `/api/check-in/{id}/step` | Yes | Complete a check-in step |
| `DELETE` | `/api/check-in/{id}/step/{step}` | Yes | Undo a step |
| `POST` | `/api/check-in/{id}/check-all` | Yes | Complete all steps |
| `DELETE` | `/api/check-in/{id}/undo-all` | Yes | Undo all steps |
| `GET` | `/api/check-in/{id}/contraband` | Yes | Get cadet's contraband |
| `POST` | `/api/check-in/{id}/contraband` | Yes | Log contraband item |
| `PUT` | `/api/check-in/contraband/{id}` | Yes | Update contraband |
| `PUT` | `/api/check-in/contraband/{id}/return` | Yes | Mark contraband returned |
| `DELETE` | `/api/check-in/contraband/{id}` | Yes | Delete contraband record |
| `GET` | `/api/logistics/contraband` | Yes | All contraband (logistics view) |

### Assignments (13 endpoints)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/assignments` | Yes | Create assignment |
| `GET` | `/api/assignments` | Yes | List assignments |
| `GET` | `/api/assignments/{id}` | Yes | Assignment detail |
| `PUT` | `/api/assignments/{id}` | Yes | Update assignment |
| `DELETE` | `/api/assignments/{id}` | Yes | Delete assignment |
| `POST` | `/api/assignments/{id}/materials` | Yes | Upload material file |
| `GET` | `/api/assignments/{id}/materials/{mid}` | Yes | Download material |
| `DELETE` | `/api/assignments/{id}/materials/{mid}` | Yes | Delete material |
| `POST` | `/api/assignments/{id}/submit` | Yes | Submit student work |
| `GET` | `/api/assignments/{id}/submissions/{sid}/file` | Yes | Download submission file |
| `POST` | `/api/assignments/{id}/grade/{sid}` | Yes | Grade submission |
| `POST` | `/api/assignments/{id}/remind` | Yes | Send reminder emails |
| `GET` | `/api/assignments/stats/overview` | Yes | Assignment statistics |

### Budget / Finance (19 endpoints)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/budget` | Yes* | All budget items |
| `POST` | `/api/budget` | Yes* | Create budget item |
| `GET` | `/api/budget/summary` | Yes* | Income/expense summary |
| `PATCH` | `/api/budget/{id}/actual` | Yes* | Update actual amount |
| `POST` | `/api/budget/{id}/mark-paid` | Yes* | Mark as paid |
| `POST` | `/api/budget/{id}/receipt` | Yes* | Attach receipt to item |
| `DELETE` | `/api/budget/{id}/receipt` | Yes* | Remove receipt |
| `PUT` | `/api/budget/{id}` | Yes* | Update budget item |
| `DELETE` | `/api/budget/{id}` | Yes* | Delete budget item |
| `POST` | `/api/budget/receipt-upload` | Yes* | **Smart OCR receipt scan** (upload image → GPT-4o extracts items) |
| `POST` | `/api/budget/receipt-confirm` | Yes* | Confirm OCR results → add to budget |
| `GET` | `/api/budget/receipt-uploads` | Yes* | Receipt upload history |
| `POST` | `/api/budget/import` | Yes* | Import from Excel |
| `GET/PUT` | `/api/budget/food-settings` | Yes* | Food expense config |
| `POST` | `/api/participants/import-payments` | Yes* | Import payment data |
| `GET` | `/api/participants/payment-summary` | Yes* | Payment overview |
| `GET` | `/api/payment-imports` | Yes* | Import history |

*Budget endpoints use role-based access internally but the decorator detection reads as public. They DO check authentication.

### Points / Awards (23 endpoints)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET/POST` | `/api/points/categories` | Yes | Score categories CRUD |
| `PUT/DELETE` | `/api/points/categories/{id}` | Yes | Manage category |
| `POST` | `/api/points/scores` | Yes | Award points |
| `GET` | `/api/points/scores` | Yes | All score entries |
| `POST` | `/api/points/merits` | Yes | Award merit/demerit |
| `GET` | `/api/points/merits` | Yes | All merits |
| `GET` | `/api/points/leaderboard/flights` | Yes | Flight rankings |
| `GET` | `/api/points/leaderboard/squadrons` | Yes | Squadron rankings |
| `GET` | `/api/points/leaderboard/individuals` | Yes | Individual rankings |
| `GET` | `/api/points/daily-winners` | Yes | Today's top performers |
| `GET` | `/api/points/cumulative-standings` | Yes | Overall standings |
| `GET` | `/api/points/summary` | Yes | Points summary |
| `POST` | `/api/points/awards` | Yes | Create honor award |
| `GET` | `/api/points/awards` | Yes | All awards |
| `POST` | `/api/points/awards/auto-assign/{date}` | Yes | Auto-assign daily awards |

### Org Chart (7 + 1 endpoints)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/org-chart/roles` | Yes | All positions (85 nodes) |
| `GET` | `/api/org-chart/roles/{id}` | Yes | Single position + children |
| `POST` | `/api/org-chart/roles` | Yes | Create position |
| `PUT` | `/api/org-chart/roles/{id}` | Yes | Update position |
| `DELETE` | `/api/org-chart/roles/{id}` | Yes | Delete position |
| `POST` | `/api/org-chart/seed` | Yes | Reseed from spreadsheet |
| `POST` | `/api/org-chart/seed-defaults` | Yes | Seed defaults |
| `POST` | `/api/org-chart/bulk-reset` | Yes | Clear all (annual reset) |

### Parent Portal (14 + 5 endpoints)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/parent/my-cadet` | Yes | Parent's cadet overview |
| `GET` | `/api/parent/my-cadet/schedule` | Yes | Cadet's schedule |
| `GET` | `/api/parent/my-cadet/health-incidents` | Yes | Health incidents |
| `GET` | `/api/parent/my-cadet/med-diary` | Yes | Medication diary |
| `GET` | `/api/parent/my-cadet/points` | Yes | Points/awards |
| `GET` | `/api/parent/my-cadet/meals` | Yes | Meal plans |
| `GET/POST` | `/api/parent/my-cadet/otc-permission` | Yes | OTC permission form |
| `GET/PUT` | `/api/parent/portal-config` | Yes | Widget config (admin) |
| `GET` | `/api/parent/admin-preview/participants` | Yes | Admin: preview as parent |
| `GET` | `/api/parent/admin-preview/{id}/*` | Yes | Admin: preview specific cadet |

### Remaining Modules

| Module | Endpoints | Key Routes |
|--------|-----------|------------|
| **Notifications** | 9 | `GET /api/notifications`, `POST /api/notifications/send`, `PUT /api/notifications/{id}/read` |
| **Push Notifications** | 6 | `POST /api/notifications/subscribe`, `GET /api/notifications/vapid-key` |
| **Documents** | 12 | `GET /api/documents`, `POST /api/documents/upload`, `GET /api/documents/{id}/download` |
| **Reports** | 11 | `POST /api/reports`, `PUT /api/reports/{id}/escalate`, `PUT /api/reports/{id}/resolve` |
| **Training** | 10 | `GET/POST /api/training/blister-checks`, counseling-logs, cadre-issues |
| **Status Board** | 4 | `GET /api/daily-settings`, uniform, weather-flag |
| **Barracks** | 6 | `GET /api/barracks`, `POST /api/barracks/{id}/assign` |
| **Meal Plans** | 4 | `GET/POST/PUT/DELETE /api/meal-plans` |
| **Logistics** | (via logistics.py inline) | inventory, radios, vehicles, facilities, supply requests |
| **Users/Admin** | 11 | `GET /api/users`, `PUT /api/users/{id}/role`, `POST /api/users/{id}/approve` |
| **Google Sheets** | 4 | `GET/POST /api/google-sheets/settings`, sync |
| **Stats** | 2 | `GET /api/stats/dashboard`, `GET /api/stats/dashboard-quickview` |
| **Students** | 4 | `POST /api/students/upload`, auto-assign, flight-distribution |

---

## 7. Error Response Format

All error responses follow this shape:

```json
{
  "detail": "Human-readable error message"
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad request / validation error |
| 401 | Not authenticated / token expired |
| 403 | Forbidden (role doesn't have access) |
| 404 | Resource not found |
| 422 | Validation error (Pydantic) |
| 500 | Server error |

---

## 8. File Upload Pattern

All file uploads use `multipart/form-data`:

```
POST /api/budget/receipt-upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <binary>
```

Receipt OCR response:
```json
{
  "id": "uuid",
  "vendor": "Walmart",
  "date": "04/15/2026",
  "total": 39.19,
  "receipt_url": "data:image/jpeg;base64,...",
  "line_items": [
    {
      "description": "Paper Plates",
      "amount": 12.99,
      "suggested_category": "Logistics",
      "confidence": "high"
    }
  ],
  "available_categories": ["Logistics", "Health Services", ...]
}
```

---

## 9. Key Data Shapes

### Participant

```json
{
  "id": "uuid",
  "capid": "662519",
  "first_name": "Lillian",
  "last_name": "Yoder",
  "rank": "C/LtCol",
  "participant_type": "cadre",       // basic_student | cadre | staff | senior_member
  "flight": "alpha",                 // alpha-foxtrot or null
  "squadron": "6th_cts",             // or null
  "position": "Flight Commander",    // or null
  "email": "user@cap.gov",
  "unit": "TN-001",
  "wing": "TNWG",
  "gender": "Female",
  "age": 17,
  "member_type": "CADET",           // CADET | SENIOR | CADET SPONSOR
  "registration_status": "Confirmed",
  "emergency_contact": "Parent Name",
  "emergency_phone": "615-555-0123",
  "cadet_parent_email": "parent@email.com",
  "amount_paid": "100.00",
  "paid_in_full": "Yes"
}
```

### Schedule Event

```json
{
  "id": "uuid",
  "title": "PT Formation",
  "date": "2026-07-19",
  "start_time": "0600",
  "end_time": "0700",
  "location": "Parade Field",
  "type": "physical_training",
  "description": "Morning PT",
  "target_groups": ["all"],
  "is_published": true
}
```

### Org Chart Node

```json
{
  "role_id": "6th-sq-cmdr",
  "position_title": "6th CTS Commander",
  "assigned_name": "C/Capt Nhan, V",
  "reports_to": "ctg-cc",
  "secondary_reports_to": "ctg-df",
  "role_category": "6th_cts",
  "display_label": "6th CTS",
  "children": ["6th-sq-1sgt", "6th-flt-a-cmdr", "6th-flt-b-cmdr"]
}
```

---

## 10. Mobile-Specific Considerations

### Offline Support
The backend has no offline sync built in. The mobile app should cache these endpoints locally:
- `GET /api/participants` (roster)
- `GET /api/schedule` (schedule)
- `GET /api/flights/{flight}/roster` (flight roster)
- `GET /api/flights/{flight}/leadership` (chain of command)

### Push Notifications
The backend has VAPID web push support. For native mobile push (FCM/APNS), you would need to add:
- `POST /api/devices/register` — register a device token (new endpoint, ~20 lines)
- Background job to send push via FCM/APNS when notifications are created

### Image URLs
Some endpoints return image URLs (profile photos, receipt images). These are either:
- Emergent Object Storage signed URLs (direct HTTPS links)
- Base64 data URLs (receipt images)

Both work in mobile `<Image>` components without modification.

### CORS
The backend currently allows `CORS_ORIGINS=*`. If you need to restrict this for production, add the mobile app's origin (for web views) or leave `*` since mobile native apps don't send Origin headers.
