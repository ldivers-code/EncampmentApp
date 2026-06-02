# Mobile App Sync — Backend Changes (May 28 – Jun 2, 2026)

> **Audience**: TN Wing Encampment mobile-app team.
> **Backend base URL**: live at production. Use whichever environment URL your build is targeted at.
> **Auth**: unchanged — Bearer JWT from `/api/auth/login` works for every new endpoint below.

This is a focused changelog covering only the things that **break wire compatibility, add new endpoints, or shift response shapes**. Cosmetic / web-UI-only changes are excluded.

---

## 🚨 Breaking — Legacy Point Tracking REMOVED

Everything under `/api/points/*` was deleted on **2026-06-02**. The mobile app must drop those calls or it will hit 404s.

| OLD endpoint (404 now)                       | Replacement                                                                                          |
|----------------------------------------------|------------------------------------------------------------------------------------------------------|
| `GET  /api/points/categories`                 | n/a — categories are baked into the new system (5 inspection types).                                  |
| `POST /api/points/scores`                     | `PUT  /api/inspections/scores`                                                                       |
| `GET  /api/points/scores`                     | `GET  /api/inspections/scores`                                                                       |
| `POST /api/points/merits`                     | `PUT  /api/inspections/merit-points` (now flight-day-level, not per-cadet)                            |
| `GET  /api/points/leaderboard/{flights,squadrons,individuals}` | `GET  /api/inspections/dashboard` returns the same data via `weekly_totals` + `by_day`.   |
| `GET  /api/points/cumulative-standings`       | `GET  /api/inspections/dashboard` (`weekly_totals`)                                                  |
| `GET  /api/points/awards/*`                   | **Not yet replaced** — Honor Awards subsystem deferred. Hide those screens until parity is reinstated. |

Parent app endpoints kept the same path + response shape but are now backed by the new collection:
- `GET /api/parent/my-cadet/points` — still returns `{total_points, total_merits, total_demerits, entries, merits, awards}`. The `total_merits`, `total_demerits`, `merits`, and `awards` fields are now always `0`/`[]`. Mobile clients can keep parsing them safely; just don't expect non-zero values until awards is rebuilt.
- `GET /api/parent/admin-preview/{pid}/points` — same path; payload is now `inspection_scores[]`.

---

## 🆕 New Module — Inspections & Points (`/api/inspections/*`)

### Access control (HARD requirement)
Allowed `user.role` values: **`exec_cadre`, `executive_staff`, `plans_programs`, `commander`, `dcp`**. Anything else → `403` with `{"detail": "Inspections & Points is restricted to Exec Cadre, Exec Staff, Plans & Programs (cadre or staff), and full admins."}`.

Mobile UX recommendation: hide the entire Inspections tab in the nav when `user.role` is not in that set, and surface a friendly empty-state if a deep-link tries to open it.

### Endpoints

| Method | Path | Notes |
|--------|------|-------|
| `GET`    | `/api/inspections/types` | Read-only metadata: field lists per inspection type, max totals, days, flights, squadron mapping, default weights. **Fetch once on app start and cache.** Drives form rendering. |
| `GET`    | `/api/inspections/settings` | The active config singleton: `{day_inspections, weights, include_merit_points}`. Auto-creates defaults on first call. |
| `PUT`    | `/api/inspections/settings` | Body fields are all optional: `{day_inspections?, weights?, include_merit_points?}`. Bad keys silently dropped. |
| `GET`    | `/api/inspections/scores?day=&flight=&inspection_type=` | Filter any combination. |
| `PUT`    | `/api/inspections/scores` | Idempotent replace for `(day, flight, inspection_type)`. See payload shapes below. |
| `DELETE` | `/api/inspections/scores?day=&flight=&inspection_type=` | Wipes one bucket. |
| `PUT`    | `/api/inspections/merit-points` | Body: `{day:int, flight:str, points:float}`. Per-flight-per-day. |
| `GET`    | `/api/inspections/merit-points` | Returns all merit-point rows. |
| `GET`    | `/api/inspections/dashboard?include_merit_points=true` | The TOTALS view — see "Response shape" below. |
| `GET`    | `/api/inspections/student/{participant_id}` | Per-cadet roll-up — used on the participant profile. |

### Inspection types & field layouts
The five canonical types (drives the score-entry UI):

```jsonc
{
  "dorm_uniform": {           // initial dorm inspection (Day 2 #1)
    "scope": "per_cadet",
    "fields": ["personal_appearance","garments","accoutrements","footwear",
               "shirt_fold","socks_fold","bunks","barrack_cleanliness"],
    "max_total": 20,
    "default_weight": 20
  },
  "dorm_uniform_repeat": {    // Day 2 #2, Day 4, Day 6
    "scope": "per_cadet",
    "fields": ["personal_appearance","garments","accoutrements","footwear",
               "shirt_fold","socks_fold","bunks","barrack_cleanliness"],
    "max_total": 20,
    "default_weight": 100
  },
  "drill": {                  // flight-level, no per-cadet rows
    "scope": "flight_level",
    "fields": ["fall_in","dress_right_dress","ready_front","at_ease",
               "flight_attention","present_arms","order_arms","left_face",
               "right_face","about_face","parade_rest","hand_salute",
               "forward_march","incline_to_the_left","incline_to_the_right",
               "flight_halt","column_of_files","fall_out"],
    "max_total": 54,           // 18 movements × 3 each
    "default_weight": 100
  },
  "daily_sports": {           // flight-level
    "scope": "flight_level",
    "fields": ["sports_score"],
    "max_total": 20,
    "default_weight": 20
  },
  "knowledge": {              // per-cadet
    "scope": "per_cadet",
    "fields": ["q1","q2","q3","q4","q5","q6","q7","q8","q9"],
    "max_total": 9,
    "default_weight": 100
  }
  // bonus row in default_weights — "app" weight = 10 — reserved for a future inspection type
}
```

### `PUT /api/inspections/scores` payload

**Per-cadet types (`dorm_uniform`, `dorm_uniform_repeat`, `knowledge`)**:
```json
{
  "day": 2,
  "flight": "alpha",
  "inspection_type": "knowledge",
  "cadet_scores": [
    {
      "cadet_participant_id": "uuid-of-cadet",
      "cadet_name": "Smith, J",
      "field_scores": { "q1": 1, "q2": 1, "q3": 0, "q4": 1, "q5": 1, "q6": 1, "q7": 1, "q8": 1, "q9": 1 },
      "absent": false
    },
    { "cadet_participant_id": "uuid-2", "cadet_name": "Doe, A", "field_scores": {}, "absent": true }
  ]
}
```

* **`absent: true`** — the row is stored but its `percent` is `null` and it is **excluded from the flight average**. This is the canonical way to record "cadet was excused" without polluting the math. Do NOT submit `0`s for absent cadets.
* **Blank rows** — if a cadet has `field_scores: {}` and `absent: false`, the row is also excluded from the flight average (no usable data). Use this for "we haven't graded them yet".
* The endpoint is **idempotent replace**: existing rows for the same `(day, flight, inspection_type)` are deleted and re-inserted on every PUT. Always send the full list.

**Flight-level types (`drill`, `daily_sports`)**:
```json
{
  "day": 2,
  "flight": "alpha",
  "inspection_type": "drill",
  "field_scores": { "fall_in": 3, "dress_right_dress": 3, "ready_front": 3, "at_ease": 3,
                    "flight_attention": 3, "present_arms": 2, "order_arms": 3,
                    "left_face": 3, "right_face": 3, "about_face": 3,
                    "parade_rest": 3, "hand_salute": 3, "forward_march": 3,
                    "incline_to_the_left": 2, "incline_to_the_right": 2,
                    "flight_halt": 3, "column_of_files": 3, "fall_out": 3 }
}
```

Response: `{ "inserted": 1, "percent": 0.9444, "total": 51 }`.

### `GET /api/inspections/dashboard` response shape

```json
{
  "settings": { "...": "..." },
  "include_merit_points": true,
  "by_day": {
    "1": { "flights": [...], "squadrons": [...] },
    "2": {
      "flights": [
        {
          "flight": "alpha",
          "day": 2,
          "per_inspection": {
            "dorm_uniform":         { "percent": null, "weight": 20,  "points": 0 },
            "dorm_uniform_repeat":  { "percent": 0.8,  "weight": 100, "points": 80 },
            "drill":                { "percent": 0.94, "weight": 100, "points": 94.44 },
            "daily_sports":         { "percent": 0.9,  "weight": 20,  "points": 18 },
            "knowledge":            { "percent": 0.89, "weight": 100, "points": 88.89 }
          },
          "ctf_average": 0.8825,
          "ctf_points":  281.33,
          "merit_points": 5
        }
      ],
      "squadrons": [
        { "squadron": "6th_cts", "cts_average": 0.62, "cts_points": 322 }
      ]
    },
    "3": { "...": "..." }
  },
  "per_day_points": {
    "1": { "alpha": 0, "bravo": 0, "...": 0 },
    "2": { "alpha": 281.33, "bravo": 100, "...": 0 }
  },
  "weekly_totals": { "alpha": 281.33, "bravo": 100, "charlie": 0, "delta": 0, "echo": 0, "foxtrot": 0 },
  "weekly_change": {
    "1": { "alpha": 0, "...": 0 },
    "2": { "alpha": 281.33, "bravo": 100, "...": 0 },
    "3": { "alpha": -150,   "bravo": 0,   "...": 0 }
  }
}
```

* **`ctf_points`** already has merit added (when `include_merit_points=true`). The separate `merit_points` field is just informational.
* **`weekly_change`** uses Day 1 as a 0-baseline, then `Day N − Day N−1` for every subsequent day. Positive → flight gained, negative → flight lost.
* **`squadrons`** mapping: `6th_cts ⇒ alpha+bravo`, `21st_cts ⇒ charlie+delta`, `22nd_cts ⇒ echo+foxtrot`.

### Mobile UX guidance

1. **Cache `/api/inspections/types` and `/api/inspections/settings` on app launch**. Refresh on pull-to-refresh of the Inspections tab. Both rarely change mid-day.
2. **Score-entry screens** need a per-row "Absent" toggle that does NOT post a `0`. Treat blanks identically.
3. **Day → Inspections gating**: the active settings tell you which inspection types are valid for each day. Hide / disable irrelevant rows. If `settings.day_inspections["3"] === ["drill","knowledge"]`, Day 3's UI should expose drill + knowledge only.
4. **Dashboard rendering**: for each enabled day, render one card. Use the per-cadet UI for `per_cadet_types` and a single form for `flight_level_types`.
5. **Empty math**: if `percent` comes back as `null`, display "—" not "0%". Only show `0%` when the user genuinely entered all-zero scores.
6. **Merit toggle**: when the user flips it on the Weekly Totals screen, call `PUT /api/inspections/settings {include_merit_points: bool}` to persist, then refetch `/api/inspections/dashboard`. The dashboard recomputes server-side.

---

## 🆕 New Module — Org Chart Canonical Template + Live Sync

The org chart was overhauled across two phases (May 28 → Jun 2). For mobile clients this means **two new endpoints** and one **behavioral change** to be aware of.

### New endpoints

| Method | Path | Notes |
|--------|------|-------|
| `GET`  | `/api/org-chart/template` | **Read-only canonical template** (79 positions). Returns `{version, categories, positions, count}`. Mobile clients should fetch this on first load to render the chart skeleton; never assume the shape from `/roles` alone. `version` lets you cache-bust safely. |
| `PUT`  | `/api/org-chart/roles/{role_id}/assign-user` | **Smart-assign endpoint** — body `{user_id, propagate=true}`. With `propagate=true` (default), updates the target user's `role` + `flight` + `squadron` + `cadre_position` to match the position, then the live-sync helper writes the chart row. With `propagate=false` (full admins only) writes `assigned_name` directly. Honors the same Exec Cadre cadre-only scoping as `PUT /users/{id}/role`. |
| `PUT`  | `/api/org-chart/roles/{role_id}/clear-assignment` | Blanks `assigned_name` + `assigned_user_id` without touching the user. |
| `POST` | `/api/org-chart/resync-from-users` | Wipes every dynamic assignment then walks all approved users to rebuild the chart. Admin-only. |
| `POST` | `/api/org-chart/seed?reset=bool` | Was destructive-only; **default is now preserve-mode** (template metadata reconciled, assignments retained, orphans pruned). Mobile clients calling this in the background should set `reset=false` (the default) to avoid clobbering manual assignments. |

### Behavioural change — live sync

When an Exec Cadre / admin user changes a user's role via `PUT /api/users/{user_id}/role` **OR** unit via `PUT /api/users/{user_id}/unit` **OR** links a participant via `POST /users/{user_id}/link-participant`, the server immediately resolves the user's canonical position and writes the matching `org_chart_roles.assigned_name`. The previously-occupied slot (if any) is cleared so a person never appears in two places.

**Mobile implication**: after any role-management mutation, **refetch `/api/org-chart/roles`** to surface the change. Don't assume the cache is current.

### Hierarchy corrections (visible diffs)

* **Public Affairs** is now `public-affairs-dept` reporting to `dcs` (was under `ctg-ccea`). If your client hard-codes `reports_to`, fix this.
* **Squadron enlisted leads** are now "First Sergeant" with `role_id` of `6th-sq-1sgt`, `21st-sq-1sgt`, `22nd-sq-1sgt` (replaces the old "Superintendent" titles).
* **Flight position IDs** follow `<prefix>-flt-<letter>-cmdr|sgt` where `prefix ∈ {6th, 21st, 22nd}` and `letter ∈ {a, b, c, d, e, f}`. Example: `6th-flt-a-cmdr`.
* New top-level slot `sm-superintendent` (Senior Member Superintendent).

### Branch palette (must match web)

| Category        | Hex        | Branch                        |
|-----------------|-----------|-------------------------------|
| `staff`          | `#008651` | Staff / Executive             |
| `support`        | `#0F6B45` | Adult Support (DCS)           |
| `6th_cts`        | `#00205B` | 6th CTS (Blue)                |
| `21st_cts`       | `#D4A017` | 21st CTS (Yellow)             |
| `22nd_cts`       | `#9B2335` | 22nd CTS (Maroon)             |
| `cadet_support`  | `#8C9298` | Cadet Support (Silver)        |

### Mobile chart UX recommendations

* Implement a **branch filter** that, when active, only renders the matching category + its ancestors up to the root. The web client (`OrgChartPage.js`) does this and the result is a much tighter, screen-friendly subtree — perfect for phone screens.
* Auto-expand collapsed nodes within the filtered subtree.
* Tap a node → side-sheet showing `position_title`, `assigned_name`, `reports_to` (look up by `role_id`), `job_description` (markdown-safe), and the supervises list (children).
* For an assigner UI, surface the new `PUT /roles/{id}/assign-user` with an autocomplete user picker over `GET /api/users`. Picker should show name, role, CAPID, and current squadron/flight to disambiguate.

### Org Chart Node data shape (extended)

```jsonc
{
  "role_id": "6th-sq-cmdr",
  "position_title": "6th CTS Commander",
  "assigned_name": "C/Capt Nhan, V",
  "assigned_user_id": "user-uuid-or-null",      // NEW — populated by live-sync writes
  "reports_to": "ctg-cc",
  "secondary_reports_to": "ctg-df",             // NEW — dashed-line connector (e.g. squadron → CTG/DF)
  "role_category": "6th_cts",                   // staff | support | cadet_support | 6th_cts | 21st_cts | 22nd_cts
  "display_label": "6th CTS",
  "position_code": "6th CTS/CC",                // NEW — short identifier
  "single_occupant": true,                      // NEW — false for multi-occupant slots (use assigned_user_ids)
  "allowed_participant_types": ["cadre"],       // NEW — template-level guard
  "job_description": "Commands the 6th Cadet Training Squadron …",
  "children": ["6th-sq-1sgt", "6th-flt-a-cmdr", "6th-flt-b-cmdr"]
}
```

---

## 🔐 RichTextEditor / Markdown Display Hardening

Backend itself didn't change, but if the mobile app stores or displays user-authored HTML coming back from any endpoint that's authored via the web `RichTextEditor`:

* The web client now restricts DOMPurify to `{p, br, strong, em, u, ol, ul, li, s}` with **zero allowed attributes**.
* Mobile should mirror this allow-list (or use a Markdown-only render path) — any other tag returned by the backend is intentional content that pre-dates this change but the sanitizer policy is now the contract.

---

## 📋 What Mobile Probably Needs to Edit

A quick punchlist:

1. **Remove** any code referencing `/api/points/*`. Hide the legacy Points / Leaderboard / Awards screens (or repoint them at `/api/inspections/dashboard`).
2. **Add** an Inspections tab (Dashboard, Enter Scores, Weekly Totals, Student Points, Settings) — visible only when `user.role ∈ {exec_cadre, executive_staff, plans_programs, commander, dcp}`.
3. **Wire** the score-entry forms using `/api/inspections/types` for the field lists rather than hard-coding (so future field additions don't require an app update).
4. **Respect** the `absent` flag — never auto-submit `0` for missing cadets.
5. **Refetch** the org chart after any role-management mutation.
6. **Migrate** Org Chart cached schemas to include the new fields (`assigned_user_id`, `position_code`, `single_occupant`, `allowed_participant_types`, `job_description`, `secondary_reports_to`).
7. **Update** the parent app to gracefully show zero merits/awards (those will populate again when Honor Awards parity ships).
8. **Update** the branch palette to add the new `support` Emerald color and verify all six categories render distinctly on dark / light themes.

---

## 🛣️ Roadmap items the mobile team should be aware of

These aren't built yet but are next on deck — flag them now so designs don't paint into a corner:

* **Honor Awards subsystem rebuild** — will likely surface as `/api/inspections/awards/*` once spec-locked. Plan UI shells but don't ship until the API exists.
* **Per-cadet "Inspection Points" card on the participant profile** — backend endpoint `/api/inspections/student/{participant_id}` is already live; UI just needs wiring.
* **`Needs Review` filter chip on the Roster page** — additional filter param coming to `/api/students/roster`.

---

*Generated by the backend team — 2026-06-02. Questions? Ping the codebase maintainers or open an issue.*
