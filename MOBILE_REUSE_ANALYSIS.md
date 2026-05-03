# Mobile Reuse Analysis: What Stays, What Gets Rebuilt

## Summary

| Layer | Lines of Code | Reusable | Rebuild |
|-------|--------------|----------|---------|
| **Backend (API + DB)** | 13,918 | **100%** — zero changes | Nothing |
| **Business Logic** | ~3,000 (role checks, filters, type derivation) | **~80%** — extract to shared utils | Rewrite role guards for mobile navigation |
| **API Client Functions** | 1,570 (300 exports) | **~95%** — copy and adapt | Swap axios for fetch + change auth from cookies to Bearer |
| **UI Components** | 25,754 (pages + components) | **0%** — all React DOM | Rebuild every screen in React Native |
| **UI Library (Shadcn)** | 46 components | **0%** — web-only (Radix + Tailwind CSS) | Replace with RN equivalents (NativeWind + custom) |
| **Styling (Tailwind)** | All pages | **~60% of class names** — NativeWind supports most | Flex/grid layout, SVG, hover states need rework |
| **State Management** | AuthContext + local state | **~70%** — patterns transfer directly | Replace cookie auth with SecureStore tokens |
| **Navigation** | React Router (Sidebar.js) | **0%** — web routing | React Navigation (tab + stack) |

---

## REUSE AS-IS (Zero Modification)

### 1. Entire Backend — 13,918 lines, 282 endpoints, 38 route files

The mobile app connects to the exact same API. Nothing changes.

| What | Size | Why It Works |
|------|------|-------------|
| All 38 route files | 12,786 lines | REST endpoints are client-agnostic |
| Models + permissions | 896 lines | RBAC logic lives server-side |
| Database layer | 39 lines + 56 collections | MongoDB is shared |
| Auth endpoints | 583 lines | Already supports `Authorization: Bearer` header (not just cookies) |
| File storage | file_storage.py | Returns signed URLs that work on any client |
| SendGrid email | Integrated in routes | Server-side — mobile just triggers the API call |
| GPT-4o receipt OCR | budget.py | Server-side — mobile uploads the photo, API does the rest |
| Seed scripts | seed_orgchart.py | One-time data — no client dependency |

**Key detail:** The auth system (`routes/auth.py` lines 131-145) already checks for tokens in three places:
```python
# 1. Cookie (web)
# 2. Authorization: Bearer header (mobile)
# 3. Query param ?token= (fallback)
```
Mobile app uses #2. No backend changes.

### 2. MongoDB Schema — 56 collections, 176+ participants

All data models, indexes, and relationships are unchanged. The mobile app reads and writes the same documents.

### 3. SendGrid Integration

Email sending is entirely server-side. The mobile app calls the same endpoints (`POST /api/notifications/send`, assignment reminders, health alerts) and emails go out.

### 4. Object Storage (File Uploads/Downloads)

Photos, documents, receipts all go through `/api/profile/photo`, `/api/documents/upload`, `/api/budget/receipts/upload`. These return URLs. Mobile just needs `multipart/form-data` upload capability (standard).

---

## REUSE WITH MINOR ADAPTATION (~1 day of work each)

### 5. API Client Functions — 1,570 lines → ~1,400 reusable

**File:** `frontend/src/services/api.js` — 300 exported functions

**What transfers directly:** Every function signature, URL path, request/response shape. These are pure API calls.

**What changes:** Two things only.

```javascript
// WEB VERSION (current):
const getAuthHeaders = () => ({ withCredentials: true });
const API = process.env.REACT_APP_BACKEND_URL + '/api';

// MOBILE VERSION:
import * as SecureStore from 'expo-secure-store';
const token = await SecureStore.getItemAsync('access_token');
const getAuthHeaders = () => ({ Authorization: `Bearer ${token}` });
const API = 'https://cadre-hub.preview.emergentagent.com/api';
```

Everything else (300 functions calling GET/POST/PUT/DELETE with JSON bodies) copies verbatim. The adaptation is a single auth header wrapper at the top of the file.

### 6. AuthContext — 189 lines → ~160 reusable

**File:** `frontend/src/context/AuthContext.js`

**What transfers:** All role-checking logic, permission helpers, `canEdit()`, user state shape.

**What changes:**
- Cookie storage → `expo-secure-store` for token persistence
- `document.cookie` references → `SecureStore.setItemAsync/getItemAsync`
- `window.location` redirect → React Navigation `navigate()`

### 7. Business Logic / Role Checks — scattered across pages

These pure-JS patterns are framework-agnostic and copy directly:

| Logic | Location | Lines | Reusable? |
|-------|----------|-------|-----------|
| `canAccessPage(pageKey, roles)` | Sidebar.js | ~10 | Yes — drives mobile tab visibility |
| `determine_participant_type()` | students.py (server) | ~35 | Already server-side |
| `ESCALATION_COLORS` map | MyFlightPage.js | ~5 | Yes |
| Flight-to-squadron mapping | Multiple files | ~10 | Yes |
| Category color maps | OrgChartPage.js, SchedulePage.js | ~30 | Yes (swap for RN StyleSheet) |
| Filter logic (roster) | RosterPage.js lines 236-296 | ~60 | Yes — pure array filtering |
| Score calculation | PointsPage.js | ~40 | Yes |
| Permission label maps | AdminPage.js | ~30 | Yes |
| Schedule filter logic | SchedulePage.js lines 271-309 | ~40 | Yes |

### 8. Tailwind Class Names — ~60% reusable via NativeWind

NativeWind (Tailwind CSS for React Native) supports most utility classes. What works:

| Works | Doesn't Work (needs rework) |
|-------|----------------------------|
| `bg-*`, `text-*`, `border-*` colors | `hover:*` states (no hover on mobile) |
| `p-*`, `m-*`, `px-*`, `py-*` spacing | `grid-cols-*` (Flexbox only in RN) |
| `rounded-*`, `shadow-*` | CSS `position: fixed/sticky` |
| `font-*`, `text-sm/lg/xl` | `overflow-x-auto` with scroll |
| `flex`, `flex-1`, `items-center`, `gap-*` | `::before/::after` pseudo-elements |
| `w-*`, `h-*`, `max-w-*` | `transition-*`, `animate-*` (use Reanimated) |
| `opacity-*`, `z-*` | `dangerouslySetInnerHTML` (no DOM) |

---

## MUST REBUILD (Mobile-Specific)

### 9. Every UI Screen — 25,754 lines (25 pages + 9 components)

React DOM (`<div>`, `<table>`, `<input>`) doesn't exist in React Native. Every visual component must be rewritten using `<View>`, `<Text>`, `<TextInput>`, `<FlatList>`, `<ScrollView>`, `<Pressable>`.

**However:** The screen structure, state variables, useEffect hooks, and API calls within each page are reusable patterns. You're rewriting the JSX template, not the logic.

Example of what changes vs. what stays in a typical page:

```
MyFlightPage.js (2,332 lines):
├── State declarations (lines 1-160)     → REUSE (copy useState/useEffect)
├── API calls (lines 160-690)            → REUSE (same functions)
├── Business logic (lines 690-850)       → REUSE (role checks, escalation)
├── JSX render (lines 850-2332)          → REBUILD (React DOM → React Native)
│   ├── Layout (<div> → <View>)
│   ├── Text (<p>/<span> → <Text>)
│   ├── Lists (<table> → <FlatList>)
│   ├── Inputs (<input> → <TextInput>)
│   ├── Buttons (<button> → <Pressable>)
│   └── Modals (Shadcn Sheet → RN Modal)
└── ~40% of the file is reusable logic, ~60% is JSX that must be rewritten
```

### 10. Navigation System — Sidebar.js (496 lines)

**Web:** Sidebar with 20+ nav items, drag-and-drop reorder, collapse toggle, role-based filtering.

**Mobile:** Bottom tab bar (5 tabs max) + stack navigation + "More" overflow menu. Completely different paradigm.

| Web | Mobile Equivalent |
|-----|-------------------|
| Sidebar with all 20 items | Bottom tabs (5) + "More" drawer |
| NavLink with active state | React Navigation Tab.Screen with icons |
| Drag-to-reorder | Settings screen to reorder tabs |
| Collapse sidebar | N/A (no sidebar on mobile) |
| Desktop/mobile toggle | N/A (always mobile) |

The **role-based nav item filtering logic** (which pages each role can see) is reusable.

### 11. Shadcn UI Components — 46 components, all web-only

Every Shadcn component (`Sheet`, `Dialog`, `Select`, `Tabs`, `Input`, etc.) is built on Radix UI primitives which are DOM-only. Mobile equivalents:

| Shadcn (Web) | Mobile Equivalent |
|--------------|-------------------|
| `Sheet` (slide-out panel) | React Native `Modal` or bottom sheet (`@gorhom/bottom-sheet`) |
| `Dialog` | `Modal` with overlay |
| `Select` / `SelectContent` | `@react-native-picker/picker` or custom bottom sheet picker |
| `Tabs` | React Navigation Material Top Tabs or custom |
| `Input` | `TextInput` |
| `Button` | `Pressable` with styles |
| `Toast / Sonner` | `react-native-toast-message` |
| `Table` | `FlatList` with row components |
| `Badge` | Custom `<View>` + `<Text>` |
| `Calendar` | `react-native-calendars` |
| `Textarea` | `TextInput multiline` |

### 12. SVG-Based Org Chart — OrgChartPage.js (entire page)

The current org chart uses absolutely-positioned `<div>` nodes + `<svg>` connectors with a custom recursive layout engine. This will not render in React Native.

**Mobile approach:** Use `react-native-svg` for connectors + `<ScrollView>` with zoom (`react-native-gesture-handler` pinch-to-zoom). The layout algorithm (`measureTree`, `positionTree`) is pure math and reuses directly — only the rendering layer changes.

### 13. Rich Text Editor — RichTextEditor.js

Uses `react-quill` which requires a browser DOM. Mobile options:
- `react-native-pell-rich-editor`
- `@10play/tentap-editor`
- Or simplify to plain text input for mobile (assignments may not need rich text on phone)

### 14. File Upload UX

Web uses `<input type="file">` and drag-and-drop. Mobile needs:
- `expo-image-picker` for camera/gallery photos
- `expo-document-picker` for documents
- Chunked upload for large files on cellular

The actual upload API call is identical — only the file selection UI changes.

### 15. Print Views

Web has print-friendly CSS layouts for roster and reports. Not applicable on mobile. Replace with:
- "Share as PDF" using `expo-print` → `expo-sharing`
- Or "Export to email" using existing SendGrid integration

---

## NEW MOBILE-ONLY FEATURES (Don't Exist in Web)

| Feature | Why | Effort |
|---------|-----|--------|
| **Native Push Notifications** | Web uses in-app bell only. Mobile needs FCM (Android) + APNS (iOS). | Backend: add `/api/devices/register` endpoint (~50 lines). Mobile: `expo-notifications` setup. |
| **Offline Roster Cache** | VTS Catoosa has unreliable WiFi. Cadre need roster access in the field. | Mobile: SQLite or AsyncStorage cache of `/api/participants` + `/api/schedule`. Sync on reconnect. |
| **Biometric Auth Gate** | Health/finance data on shared devices needs protection. | Mobile: `expo-local-authentication` (FaceID/TouchID) before displaying sensitive screens. |
| **QR/Barcode Check-In** | Scan CAPID barcode on CAP cards for instant check-in lookup. | Backend: trivial (`GET /api/check-in/lookup?capid=X`). Mobile: `expo-camera` barcode scanner. |
| **Camera Integration** | Direct photo capture for cadet headshots, receipts, contraband evidence. | Mobile: `expo-image-picker` → existing upload endpoints. |
| **Haptic Feedback** | Confirm check-in steps, point awards, escalation actions with tactile feedback. | Mobile: `expo-haptics` — trivial integration. |

---

## Effort Estimate by Component

| Component | Web Lines | Mobile Effort | Notes |
|-----------|-----------|---------------|-------|
| Auth + token management | 189 | 1 day | SecureStore swap |
| API client layer | 1,570 | 0.5 day | Header swap only |
| Navigation shell | 496 | 2 days | Bottom tabs + stacks + role gating |
| Dashboard | 882 | 2 days | Cards + schedule list |
| My Flight | 2,332 | 3 days | Largest page, many sub-features |
| Schedule | 1,749 | 2 days | Day view + swipe + filters |
| Roster | 2,188 | 2 days | FlatList + filters + search |
| Check-In | 669 | 1.5 days | Step flow + contraband |
| Health Services | 2,197 | 3 days | Med diary + allergy search + OTC |
| Parent Portal | 677 | 1.5 days | Read-mostly, OTC form |
| Assignments | 1,095 | 2 days | List + submit + grade |
| Org Chart | 555 | 2 days | SVG rebuild with zoom |
| Budget | 1,410 | 2 days | Camera OCR + charts |
| Points | 1,365 | 1.5 days | Leaderboard + quick entry |
| Notifications (push) | 430 + new | 2 days | FCM/APNS + backend endpoint |
| Remaining (Logistics, Admin, etc.) | ~4,000 | 4 days | Lower priority screens |
| Offline cache | New | 2 days | SQLite + sync logic |
| **Total** | **22,000+** | **~32 days** | ~6.5 weeks with one developer |

---

## Decision Framework

**If you want the fastest path to mobile:** Start with React Native + Expo. Port `api.js` on day 1 (0.5 day), auth on day 1 (0.5 day), and you have a working authenticated shell by end of day 1 that talks to your live backend. Then it's purely UI rebuilding — the hardest part (business logic, API, data) is already done.

**If budget is tight:** Ship a PWA first (1-2 weeks — add service worker + manifest to existing React app). You get "Add to Home Screen" on both platforms with the current responsive UI. No App Store review. Upgrade to native later.

**If you want the richest mobile experience:** React Native with these priorities:
1. Week 1: Auth + Dashboard + Schedule + My Flight + Push
2. Week 2: Check-In + Health Services + Roster
3. Week 3: Assignments + Points + Parent Portal
4. Week 4+: Everything else + offline + polish
