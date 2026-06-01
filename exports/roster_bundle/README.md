# Roster ↔ User Sync — Code Bundle

Generated **automatically** by E1 — snapshot of every file involved in roster
display, flight/squadron assignment, the support-section taxonomy and the
roster↔user account sync. Use this to inspect the code yourself when the
preview shows correct counts but the deployed app shows incorrect ones.

---

## File map (organised by data flow)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  EXCEL / GOOGLE SHEETS ROSTER UPLOAD                                    │
│                                                                         │
│    /api/students/upload          ───┐                                   │
│    /api/google-sheets/.../sync   ───┴── parse roster → save participant │
└──────────────────────────────────────────┬──────────────────────────────┘
                                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PARTICIPANT STORAGE  (Mongo `participants` collection)                 │
│                                                                         │
│    { id, participant_type, flight, squadron, app_edit_data, ... }       │
└──────────────────────────────────────────┬──────────────────────────────┘
                                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ASSIGNMENT MUTATIONS                                                   │
│                                                                         │
│    /api/students/auto-assign         (batched balance, 15-cap)          │
│    /api/participants/{id}/assignment (single edit, no cap today)        │
│    /api/participants/bulk-assignment (multi edit, no cap today)         │
└──────────────────────────────────────────┬──────────────────────────────┘
                                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  READ + ENRICHMENT                                                      │
│                                                                         │
│    /api/participants            → joins to `users` to compute           │
│                                   linked_user_role, is_non_flight,      │
│                                   is_support, linked_support_section    │
│    /api/participants/by-flight  → groups for the drag-and-drop view     │
│    /api/taxonomy/support        → dropdown options for support cadre    │
└──────────────────────────────────────────┬──────────────────────────────┘
                                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  FRONTEND                                                               │
│                                                                         │
│    pages/RosterPage.js          (the table + filters + inline edit)     │
│    components/FlightManager.js  (the by-flight drag-and-drop view)      │
│    services/api.js              (axios wrappers)                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Backend files (`backend/`)

| File | Why it's in this bundle |
|------|--------------------------|
| `models.py` | Defines `ParticipantBase`, `ParticipantResponse`, `UserResponse`, `UserRole`, `ParticipantAssignmentUpdate`. The schema of every roster row + linked user. |
| `permissions.py` | `get_current_user`, `require_role`, RBAC guards used by every roster endpoint. |
| `role_groups.py` | The Seven-Concern model. Defines `FULL_ADMIN_ROLES`, `SENIOR_STAFF_ROLES`, `CADRE_LEAD_ROLES`. |
| `support_sections.py` | **NEW** Feb 2026. The Support/Senior Member taxonomy: which roles are non-flight, the 8 section slugs, the role ↔ section mapping used for sync. |
| `scope.py` | `apply_participant_visibility`, `redact_participant` — controls which rows/fields a given user sees in the roster. |
| `account_status.py` | Calculates the 6-field `/auth/status` payload that the frontend uses for routing. |
| `classifier.py` | RegZone SubEvents → participant_type classifier. |
| `routes/participants.py` | **`PUT /participants/{id}/assignment`** (single-row edit + user sync — line ~1200), `GET /participants` (enriches with linked user), `POST /participants/bulk-assignment`. |
| `routes/students.py` | **`POST /students/upload`** (Sync Mode + waitlist promotion), `POST /students/auto-assign` (balanced flight assignment with 15-cap), `auto_assign_flights()`, `_app_edit_sort_key()`. |
| `routes/auth.py` | Login, registration, password reset, `/auth/status`. |
| `routes/users.py` | User CRUD, role updates, `linked_participant_id` linking. |
| `routes/flights.py` | Flight grouping helpers, `/flights/distribution`. |
| `routes/taxonomy.py` | **NEW** Feb 2026. `GET /taxonomy/support` — exposes the 8 sections + 3 squadron buckets to the frontend. |
| `routes/google_sheets.py` | Roster sync from Google Sheets, schedule grid parser, tab auto-discovery, `AppEditDate` column mapping. |

---

## Frontend files (`frontend/`)

| File | Why it's in this bundle |
|------|--------------------------|
| `RosterPage.js` | The Roster page — table with inline editing, filters, Waitlist chip, auto-balance button. The Flight + Squadron `<Select>` dropdowns at line ~2118 / ~2163 are the ones that drive `PUT /assignment` calls. |
| `FlightManager.js` | The **By-Flight** view (the screenshot you sent). Renders one column per flight + an "Unassigned" column, supports drag-and-drop reassignment via `dnd-kit`. Uses `updateParticipantAssignment` from `api.js`. |
| `api.js` | Axios clients. The roster-relevant ones: `getParticipants`, `updateParticipantAssignment`, `autoAssignUnassignedStudents`, `uploadStudents`. |
| `AuthContext.js` | Stores the logged-in user, exposes `user.role` used for RBAC gating in the Roster UI. |

---

## Tests (`backend/tests/`)

| File | What it asserts |
|------|------------------|
| `test_auto_balance.py` | The 15-cap is enforced when auto-assign runs; `app_edit_data` drives the sort order. |
| `test_support_taxonomy.py` | The new role groups + the `GET /taxonomy/support` endpoint + the assignment-endpoint user-sync. |
| `test_student_upload.py` | Roster upload Sync Mode, waitlist promotion after soft-removes. |
| `test_user_participant_sync.py` | Linked-participant ↔ user account integrity. |

---

## Where the bug you saw likely lives

You saw **Alpha with 30 students** and **52 unassigned cadre** in production.
Two probable root causes (based on a fresh code reading):

### 1. The 15-cap is only enforced inside `auto_assign_flights()`

It's enforced ONLY when someone clicks "Auto-Balance Flights". These three
write paths do **not** check the cap:

- `PUT /api/participants/{id}/assignment` → `routes/participants.py` (line ~1200)
- `PUT /api/participants/bulk-assignment` → `routes/participants.py` (line ~993)
- `POST /api/students/upload` (Excel re-upload pass-through of the Flight column)
  → `routes/students.py`, search for `"flight": ` in the document-build loop.

So if your eCAP export already has cadets pre-assigned to Alpha, the
upload writes them all to Alpha regardless of count. Same for drag-and-drop
in the By-Flight view (which calls the single-row assignment endpoint).

### 2. Cadre have no auto-assignment workflow

`auto_assign_flights()` (in `students.py`) filters by
`participant_type == "student"`. **Cadre are never auto-balanced.**

Cadre `flight` is intended to be set by:
- The Org Chart (when you designate someone "Alpha Flight Sergeant" their
  org-chart node should write `flight=alpha` to their participant).
- The Excel upload's Flight column (if your eCAP export has it).
- Manual drag in the FlightManager UI.

If none of those happen, cadre sit in the Unassigned column — which is
exactly what you saw (52 cadre in Unassigned).

---

## Quick diagnostic queries

Run these in a Mongo shell against the production DB to see what
the current state really is:

```js
// Per-flight student/cadre counts (active only)
db.participants.aggregate([
  { $match: { is_removed: { $ne: true } } },
  { $group: {
      _id: { flight: "$flight", type: "$participant_type" },
      n: { $sum: 1 } } },
  { $sort: { "_id.flight": 1 } }
])

// Cadre with no flight
db.participants.find(
  { participant_type: "cadre", is_removed: { $ne: true },
    $or: [ { flight: null }, { flight: "" } ] },
  { _id: 0, last_name: 1, first_name: 1, squadron: 1, position: 1 }
).limit(20)

// Students over-stuffed into one flight
db.participants.aggregate([
  { $match: { participant_type: "student", is_removed: { $ne: true } } },
  { $group: { _id: "$flight", count: { $sum: 1 } } },
  { $match: { count: { $gt: 15 } } }
])
```

---

## How to apply local fixes

If after reading you want to enforce the 15-cap on **all** write paths,
the smallest change is to wrap every write inside a helper:

```python
# routes/students.py — add near auto_assign_flights
async def _can_seat_in_flight(flight: str, exclude_id: str | None = None) -> bool:
    if not flight or flight.lower() not in ALL_FLIGHTS:
        return True  # null / unassigned / non-flight value — always OK
    q = {
        "participant_type": "student",
        "is_removed": {"$ne": True},
        "flight": flight.lower(),
    }
    if exclude_id:
        q["id"] = {"$ne": exclude_id}
    count = await db.participants.count_documents(q)
    return count < MAX_STUDENTS_PER_FLIGHT
```

Then call it at the top of `update_participant_assignment`,
`bulk_change_assignment`, and the upload's per-row save loop. Reject with
`HTTPException(409, "Flight {flight} is at capacity (15/15)")` if False.

For cadre auto-assignment, the cleanest pattern is to extend
`auto_assign_flights()` to optionally include cadre with their own cap
(e.g. 3-5 per flight: 1 commander + 1 sergeant + 1-3 ICs).

---

*Bundle generated: 2026-06-01T22:06:41Z*
*Source environment: PREVIEW (`cadre-hub.preview.emergentagent.com`)*
