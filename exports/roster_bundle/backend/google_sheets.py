"""Google Sheets Sync Endpoints and Service"""
from fastapi import Depends, HTTPException, BackgroundTasks
from typing import Optional
from datetime import datetime, timezone
from io import BytesIO
import csv
import logging
import os
import re
import uuid
import hashlib

import httpx
import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import db, api_router
from models import (
    UserRole,
    GoogleSheetsSyncRequest,
    GoogleSheetsSettings,
    ScheduleSheetConfig,
)
from permissions import get_current_user, require_role

logger = logging.getLogger(__name__)

# ================= GOOGLE SHEETS SYNC ENDPOINTS =================

# Phase 8: roles that can configure / trigger sheet sync.
_GSHEET_ADMIN_ROLES = ('commander', 'executive_staff', 'plans_programs', 'dcp', 'staff')


def _parse_spreadsheet_url(url_or_id: str) -> tuple[str, Optional[str]]:
    """Accept either a raw spreadsheet ID or a full Google Sheets URL.
    Returns (spreadsheet_id, gid_or_None)."""
    if not url_or_id:
        return "", None
    s = url_or_id.strip()
    # Raw id (no slashes)
    if "/" not in s:
        return s, None
    sid_match = re.search(r"/d/([a-zA-Z0-9_-]+)", s)
    gid_match = re.search(r"[?&#]gid=(\d+)", s)
    return (sid_match.group(1) if sid_match else s,
            gid_match.group(1) if gid_match else None)


def _slugify(name: str) -> str:
    """Stable id derived from a label."""
    s = (name or "schedule").lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "schedule"


@api_router.get("/google-sheets/settings")
async def get_google_sheets_settings(user: dict = Depends(get_current_user)):
    """Get Google Sheets sync settings"""
    if user.get('role') not in _GSHEET_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")

    settings = await db.google_sheets_settings.find_one({'_id': 'settings'})
    if not settings:
        return {
            "schedules": [],
            "org_chart_sheets": [],
            "sync_interval_hours": 1,
            "last_sync_at": None,
            "last_sync_status": None,
            "last_sync_message": None,
            "auto_sync_enabled": True,
        }

    settings.pop('_id', None)
    # Phase 8 migration: legacy docs may still carry roster_sheet —
    # strip it from the response and queue a quiet cleanup.
    if 'roster_sheet' in settings:
        settings.pop('roster_sheet', None)
        await db.google_sheets_settings.update_one(
            {'_id': 'settings'}, {'$unset': {'roster_sheet': ''}}
        )
    return settings


@api_router.post("/google-sheets/settings")
async def update_google_sheets_settings(
    request: GoogleSheetsSyncRequest,
    user: dict = Depends(get_current_user)
):
    """Update Google Sheets sync settings — schedules + org chart only."""
    if user.get('role') not in _GSHEET_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")

    settings: dict = {
        '_id': 'settings',
        'sync_interval_hours': request.sync_interval_hours,
        'auto_sync_enabled': request.auto_sync_enabled,
    }

    # Phase 8: schedules — preserve existing telemetry when the caller
    # only updates the URL/label/enabled flag.
    if request.schedules is not None:
        existing = await db.google_sheets_settings.find_one(
            {'_id': 'settings'}, {'schedules': 1}
        ) or {}
        existing_by_id = {s['id']: s for s in (existing.get('schedules') or [])}
        cleaned: list[dict] = []
        for s in request.schedules:
            # Accept a URL pasted into spreadsheet_id and split it apart.
            sid, gid_from_url = _parse_spreadsheet_url(s.spreadsheet_id)
            row = s.model_dump()
            row['spreadsheet_id'] = sid
            row['gid'] = s.gid or gid_from_url
            if not row.get('id'):
                row['id'] = _slugify(s.label)
            # Preserve telemetry from the prior doc if it exists.
            prior = existing_by_id.get(row['id'], {})
            for k in ('last_sync_at', 'last_sync_status',
                      'last_sync_message', 'last_event_count'):
                if row.get(k) is None and prior.get(k) is not None:
                    row[k] = prior[k]
            cleaned.append(row)
        settings['schedules'] = cleaned

    if request.org_chart_spreadsheet_id and request.org_chart_gids:
        settings['org_chart_sheets'] = [
            {
                'sheet_type': 'org_chart',
                'spreadsheet_id': request.org_chart_spreadsheet_id,
                'gid': gid,
                'name': f'Org Chart Tab {i+1}',
                'enabled': True
            }
            for i, gid in enumerate(request.org_chart_gids)
        ]

    # Phase 8 migration safety: never re-introduce roster_sheet.
    await db.google_sheets_settings.replace_one(
        {'_id': 'settings'},
        settings,
        upsert=True,
    )
    await db.google_sheets_settings.update_one(
        {'_id': 'settings'}, {'$unset': {'roster_sheet': ''}}
    )

    return {"message": "Settings updated successfully", "settings": settings}

@api_router.post("/google-sheets/sync")
async def trigger_manual_sync(
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Manually trigger a Google Sheets sync"""
    if user.get('role') not in ['commander', 'executive_staff', 'plans_programs', 'staff']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    settings = await db.google_sheets_settings.find_one({'_id': 'settings'})
    if not settings:
        raise HTTPException(status_code=400, detail="No Google Sheets configured. Please configure sheets first.")
    
    # Run sync in background
    background_tasks.add_task(perform_scheduled_sync)
    
    return {"message": "Sync started. Check status for results."}

@api_router.get("/google-sheets/sync-status")
async def get_sync_status(user: dict = Depends(get_current_user)):
    """Get the current sync status"""
    settings = await db.google_sheets_settings.find_one({'_id': 'settings'})
    if not settings:
        return {
            "configured": False,
            "last_sync_at": None,
            "last_sync_status": None,
            "last_sync_message": None,
            "auto_sync_enabled": False
        }
    
    return {
        "configured": True,
        "last_sync_at": settings.get('last_sync_at'),
        "last_sync_status": settings.get('last_sync_status'),
        "last_sync_message": settings.get('last_sync_message'),
        "auto_sync_enabled": settings.get('auto_sync_enabled', True),
        "sync_interval_hours": settings.get('sync_interval_hours', 1)
    }



# ================= GOOGLE SHEETS SYNC SERVICE =================

# Global scheduler instance
scheduler = AsyncIOScheduler()

async def fetch_google_sheet_csv(spreadsheet_id: str,
                                 gid: Optional[str] = None,
                                 sheet_name: Optional[str] = None) -> Optional[str]:
    """Fetch a Google Sheet tab as CSV data.

    Tab resolution order:
      1. `gid` if provided → /export?format=csv&gid=<gid>
      2. `sheet_name` if provided → /gviz/tq?tqx=out:csv&sheet=<name>
      3. Neither → first tab via /export?format=csv
    """
    if gid:
        url = (
            f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
            f"/export?format=csv&gid={gid}"
        )
    elif sheet_name:
        from urllib.parse import quote
        url = (
            f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
            f"/gviz/tq?tqx=out:csv&sheet={quote(sheet_name)}"
        )
    else:
        url = (
            f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
            f"/export?format=csv"
        )
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                content = response.text
                # Check if it's an error page
                if "Page Not Found" in content or "<!DOCTYPE html>" in content[:100]:
                    logger.error(f"Sheet not accessible: {spreadsheet_id}/{gid or sheet_name}")
                    return None
                return content
            else:
                logger.error(f"Failed to fetch sheet: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Error fetching Google Sheet: {e}")
        return None


# ── Phase 8: schedule sync from Google Sheets ────────────────────────────

# Column header aliases — case-insensitive. The flat parser expects a sheet
# with these columns (in any order); extra columns are ignored.
SCHEDULE_COLUMN_ALIASES = {
    "date":         {"date", "day"},
    "start_time":   {"start", "start time", "begin", "begin time", "start_time"},
    "end_time":     {"end", "end time", "finish", "end_time"},
    "title":        {"title", "activity", "event", "name"},
    "location":     {"location", "place", "venue"},
    "event_type":   {"type", "event type", "category", "event_type"},
    "target_groups": {"target", "target groups", "audience", "group", "groups", "target_groups"},
    "uniform":      {"uniform", "uod", "uniform of the day"},
    "description":  {"description", "notes", "details"},
}


def _find_schedule_columns(header_row: list[str]) -> dict:
    """Map our canonical column keys to the indexes found in the sheet header.
    Returns a dict like {"date": 0, "start_time": 1, ...} for the columns
    that ARE present. Missing optional columns simply don't appear in the dict.
    """
    out: dict[str, int] = {}
    normalised = [(i, (h or "").strip().lower()) for i, h in enumerate(header_row)]
    for canonical, aliases in SCHEDULE_COLUMN_ALIASES.items():
        for i, h in normalised:
            if h in aliases:
                out[canonical] = i
                break
    return out


def _norm_time(value: str) -> Optional[str]:
    """Accept 'HHMM', 'HH:MM', 'H:MM AM/PM' → return 'HH:MM' (24h)."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    # HHMM (military)
    if re.fullmatch(r"\d{3,4}", s):
        s = s.zfill(4)
        return f"{s[:2]}:{s[2:]}"
    # HH:MM with optional AM/PM
    m = re.fullmatch(r"(\d{1,2}):(\d{2})\s*(AM|PM)?", s, re.IGNORECASE)
    if m:
        h = int(m.group(1))
        mm = int(m.group(2))
        ampm = (m.group(3) or "").upper()
        if ampm == "PM" and h < 12:
            h += 12
        elif ampm == "AM" and h == 12:
            h = 0
        return f"{h:02d}:{mm:02d}"
    return None


def _norm_date(value: str) -> Optional[str]:
    """Best-effort date normaliser. Returns 'YYYY-MM-DD' or None."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    # ISO already
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    # Common US formats — let pandas do the heavy lifting
    try:
        return pd.to_datetime(s).strftime("%Y-%m-%d")
    except Exception:
        return None


# ── Phase 8: GRID-FORMAT parser (CAST / Encampment day-tab schedules) ────
#
# Sheet layout expected:
#   Row 0: Day title in A1, e.g. "Friday | Day 1 CADRE Arrival | May 29th"
#   Row 1: optional banner ("Training Cadre", "Support", ...) — ignored.
#   Row N: column header row containing one or more START/END pairs
#          plus squadron/flight columns and (optionally) a Notes column.
#          Example: START, END, 6th CTS, 21st CTS, 22nd CTS, 16th CTS,
#                   START, END, Notes
#   Rows >N: one row per time slot. A cell under a squadron column is the
#          activity title for that squadron in that slot. A "merged"
#          activity that applies to all squadrons in a block typically
#          appears in only the FIRST squadron column (CSV merge artefact).

_SQUADRON_HEADER_RE = re.compile(
    r"^\s*(\d+(?:st|nd|rd|th))\s*CTS\s*$", re.IGNORECASE
)
_FLIGHT_HEADER_RE = re.compile(
    r"^\s*(alpha|bravo|charlie|delta|echo|foxtrot|golf|hotel)"
    r"(?:\s*(?:flt|flight))?\s*$",
    re.IGNORECASE,
)
_MONTH_DAY_RE = re.compile(
    r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?"
    r"(?:[,\s]+(\d{4}))?\b",
    re.IGNORECASE,
)
_FOOTER_YEAR_RE = re.compile(r"\b(20\d{2})\b")


def _classify_grid_header_cell(text: str) -> Optional[tuple[str, str]]:
    """Return (kind, label) for a grid header cell.

    kind ∈ {"start", "end", "notes", "group"}.
    For "group" the label is the canonical slug (e.g. "6th_cts", "alpha").
    Returns None if the cell is not recognised.
    """
    if not text:
        return None
    t = text.strip()
    if not t:
        return None
    tU = t.upper()
    if tU == "START":
        return ("start", "")
    if tU == "END":
        return ("end", "")
    if tU in ("NOTES", "NOTE"):
        return ("notes", "")
    sm = _SQUADRON_HEADER_RE.match(t)
    if sm:
        return ("group", f"{sm.group(1).lower()}_cts")
    fm = _FLIGHT_HEADER_RE.match(t)
    if fm:
        return ("group", fm.group(1).lower())
    return None


def _detect_grid_header(rows: list[list[str]]) -> Optional[int]:
    """Find the index of the column-header row that has START/END + at least
    one squadron/flight column. Scan the first 10 rows."""
    for i in range(min(10, len(rows))):
        row = rows[i]
        has_start = False
        has_group = False
        for cell in row:
            kind = _classify_grid_header_cell(cell or "")
            if not kind:
                continue
            if kind[0] == "start":
                has_start = True
            elif kind[0] == "group":
                has_group = True
        if has_start and has_group:
            return i
    return None


def _parse_grid_header(header_row: list[str]) -> list[dict]:
    """Walk the header row and return a list of column blocks.

    Each block is {start_col, end_col, group_cols: [{col, label}], notes_col}.
    A new block begins at each "START" header. The notes column attaches to
    whichever block it falls inside (the last open block).
    """
    blocks: list[dict] = []
    cur: Optional[dict] = None
    for i, cell in enumerate(header_row):
        kind = _classify_grid_header_cell(cell or "")
        if not kind:
            continue
        k, label = kind
        if k == "start":
            cur = {"start_col": i, "end_col": None,
                   "group_cols": [], "notes_col": None}
            blocks.append(cur)
        elif k == "end" and cur and cur["end_col"] is None:
            cur["end_col"] = i
        elif k == "group" and cur and cur["end_col"] is not None:
            cur["group_cols"].append({"col": i, "label": label})
        elif k == "notes" and cur:
            cur["notes_col"] = i
    # Keep only well-formed blocks (start+end present)
    return [b for b in blocks if b["start_col"] is not None
            and b["end_col"] is not None]


def _extract_grid_date(title_cell: str,
                       footer_year: Optional[int]) -> Optional[str]:
    """Pull a YYYY-MM-DD out of a title like
    'Friday | Day 1 CADRE Arrival | May 29th'."""
    if not title_cell:
        return None
    m = _MONTH_DAY_RE.search(title_cell)
    if not m:
        return None
    month_str = m.group(1)
    day = int(m.group(2))
    year_in_title = m.group(3)
    if year_in_title:
        year = int(year_in_title)
    elif footer_year:
        year = footer_year
    else:
        year = datetime.now(timezone.utc).year
    # Try full month, then abbreviated
    for fmt in ("%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(
                f"{month_str.title()} {day} {year}", fmt
            ).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _extract_footer_year(rows: list[list[str]]) -> Optional[int]:
    """Look at the last ~5 rows for 'LAST UPDATED: MM/DD/YYYY' or any year."""
    for row in rows[-5:]:
        for cell in row:
            if not cell:
                continue
            m = _FOOTER_YEAR_RE.search(str(cell))
            if m:
                return int(m.group(1))
    return None


def _grid_rows_to_events(rows: list[list[str]],
                         header_idx: int,
                         blocks: list[dict],
                         date: str) -> tuple[list[dict], int]:
    """Walk data rows under the header and emit events per block.

    Adjacent rows that carry the same (block, label, title) get merged into
    one longer event (handles vertically-merged cells lost in the CSV
    export). Returns (events, skipped_row_count).
    """
    events: list[dict] = []
    skipped = 0

    # Open events keyed by (block_index, group_label) → event dict that we
    # may still extend with subsequent rows.
    open_per_label: dict[tuple[int, str], dict] = {}

    for row in rows[header_idx + 1:]:
        # Footer rows like "LAST UPDATED: ..." → stop processing
        if row and row[0] and "LAST UPDATED" in str(row[0]).upper():
            break

        # Notes columns may live in any block, but their text applies to
        # the whole row visually. Collect them once per row.
        row_notes_parts: list[str] = []
        for block in blocks:
            nc = block.get("notes_col")
            if nc is not None and len(row) > nc:
                txt = (row[nc] or "").strip()
                if txt:
                    row_notes_parts.append(txt)
        row_notes = " | ".join(row_notes_parts) if row_notes_parts else ""

        any_emit_this_row = False
        for bi, block in enumerate(blocks):
            sc, ec = block["start_col"], block["end_col"]
            start_raw = row[sc] if len(row) > sc else ""
            end_raw = row[ec] if len(row) > ec else ""
            start = _norm_time(start_raw)
            end = _norm_time(end_raw)
            if not (start and end):
                # Close any open events for this block — time block ended.
                for key in list(open_per_label.keys()):
                    if key[0] == bi:
                        open_per_label.pop(key, None)
                continue

            group_cols = block["group_cols"]
            if not group_cols:
                continue

            # Gather cell values for each group column.
            cell_values: list[tuple[str, str]] = []  # [(label, text)]
            for gc in group_cols:
                txt = ""
                if len(row) > gc["col"]:
                    txt = (row[gc["col"]] or "").strip()
                cell_values.append((gc["label"], txt))

            filled = [(lbl, txt) for lbl, txt in cell_values if txt]
            notes = row_notes

            # Decide event shape for this row.
            if not filled:
                # Empty activity row — extend any currently-open events
                # within this block to this row's end_time.
                for key, ev in list(open_per_label.items()):
                    if key[0] == bi:
                        ev["end_time"] = end
                continue

            # Heuristic: if only the FIRST squadron-column has content, treat
            # it as a horizontally-merged cell that applies to every group
            # in the block.
            only_first_filled = (
                len(filled) == 1
                and filled[0][0] == cell_values[0][0]
                and len(cell_values) > 1
            )
            all_filled_same = (
                len(filled) == len(cell_values)
                and len({t for _, t in filled}) == 1
            )

            if only_first_filled or all_filled_same:
                title = filled[0][1]
                targets = [lbl for lbl, _ in cell_values]
                # Use a synthetic group key so all groups share one open ev.
                key = (bi, "__ALL__")
                open_ev = open_per_label.get(key)
                if open_ev and open_ev["title"] == title \
                        and open_ev["end_time"] == start:
                    # Extend
                    open_ev["end_time"] = end
                    any_emit_this_row = True
                else:
                    # Close any prior __ALL__ for this block
                    open_per_label.pop(key, None)
                    # Close any per-label opens for this block too (different shape)
                    for k2 in list(open_per_label.keys()):
                        if k2[0] == bi:
                            open_per_label.pop(k2, None)
                    ev = {
                        "date": date,
                        "start_time": start,
                        "end_time": end,
                        "title": title,
                        "description": notes or None,
                        "location": None,
                        "event_type": "general",
                        "target_groups": targets,
                        "uniform": None,
                    }
                    events.append(ev)
                    open_per_label[key] = ev
                    any_emit_this_row = True
            else:
                # Per-label events. Close __ALL__ if any.
                open_per_label.pop((bi, "__ALL__"), None)
                seen_labels_this_row = set()
                for lbl, txt in filled:
                    seen_labels_this_row.add(lbl)
                    key = (bi, lbl)
                    open_ev = open_per_label.get(key)
                    if open_ev and open_ev["title"] == txt \
                            and open_ev["end_time"] == start:
                        open_ev["end_time"] = end
                    else:
                        open_per_label.pop(key, None)
                        ev = {
                            "date": date,
                            "start_time": start,
                            "end_time": end,
                            "title": txt,
                            "description": notes or None,
                            "location": None,
                            "event_type": "general",
                            "target_groups": [lbl],
                            "uniform": None,
                        }
                        events.append(ev)
                        open_per_label[key] = ev
                # Close opens for labels that were not seen on this row.
                for key in list(open_per_label.keys()):
                    if key[0] == bi and key[1] != "__ALL__" \
                            and key[1] not in seen_labels_this_row:
                        open_per_label.pop(key, None)
                any_emit_this_row = True

        if not any_emit_this_row:
            skipped += 1

    return events, skipped


async def sync_schedule_from_gsheet(schedule_id: str, label: str,
                                    spreadsheet_id: str,
                                    gid: Optional[str],
                                    sheet_name: Optional[str] = None) -> dict:
    """Sync one configured schedule from Google Sheets.

    Events imported from this schedule are tagged with
    `source_schedule_id=schedule_id` so re-syncing one configured schedule
    DOES NOT delete events from another (CAST and Encampment stay
    independent). Manually-created events without `source_schedule_id` are
    never touched.

    Two sheet formats are supported:
      1. Flat table — one row per event with columns Date, Start Time,
         End Time, Title (+optional Location, Event Type, Target Groups,
         Uniform, Notes).
      2. Grid layout — A1 carries the day title (containing a Month + Day),
         then a row with START / END / <squadron columns> / Notes, and
         each subsequent row is a time slot with per-squadron activities.
         Used by the CAST and Encampment day-tab schedules.
    """
    csv_data = await fetch_google_sheet_csv(spreadsheet_id, gid, sheet_name)
    if not csv_data:
        return {"success": False, "message": "Could not fetch the sheet. Is it shared as 'Anyone with the link'?"}

    rows = list(csv.reader(csv_data.splitlines()))
    if not rows:
        return {"success": False, "message": "Sheet is empty."}

    # ── Try GRID format first (CAST / Encampment day tabs) ─────────────
    grid_header_idx = _detect_grid_header(rows)
    if grid_header_idx is not None:
        blocks = _parse_grid_header(rows[grid_header_idx])
        if blocks and any(b["group_cols"] for b in blocks):
            title_cell = rows[0][0] if rows and rows[0] else ""
            footer_year = _extract_footer_year(rows)
            date = _extract_grid_date(title_cell, footer_year)
            if not date:
                return {
                    "success": False,
                    "message": (
                        f"Detected grid format but could not parse a date "
                        f"from the title row: '{title_cell[:80]}'. "
                        f"Add a Month + Day (e.g. 'May 29th') to cell A1."
                    ),
                }
            parsed_events, skipped_rows = _grid_rows_to_events(
                rows, grid_header_idx, blocks, date
            )
            if not parsed_events:
                return {
                    "success": False,
                    "message": (
                        f"Grid parsed but no events found. Skipped "
                        f"{skipped_rows} empty rows."
                    ),
                }

            now = datetime.now(timezone.utc).isoformat()
            await db.schedule.delete_many({"source_schedule_id": schedule_id})
            docs = []
            for e in parsed_events:
                docs.append({
                    "id": str(uuid.uuid4()),
                    "source_schedule_id": schedule_id,
                    "source_schedule_label": label,
                    "is_published": False,
                    "created_at": now,
                    "updated_at": now,
                    **e,
                })
            await db.schedule.insert_many(docs)
            await db.schedule_settings.update_one(
                {"_id": "settings"},
                {"$inc": {"version": 1},
                 "$set": {"last_modified_at": now}},
                upsert=True,
            )
            return {
                "success": True,
                "message": (
                    f"{label}: synced {len(parsed_events)} events "
                    f"(grid format, date={date})."
                ),
                "event_count": len(parsed_events),
                "skipped": skipped_rows,
                "format": "grid",
                "date": date,
            }

    # ── Fall back to FLAT table parser ─────────────────────────────────
    header_idx = None
    header_cols: dict = {}
    for i in range(min(6, len(rows))):
        cols = _find_schedule_columns(rows[i])
        # Must have at least Date + Start Time + Title to be a usable header.
        if "date" in cols and "start_time" in cols and "title" in cols:
            header_idx = i
            header_cols = cols
            break

    if header_idx is None:
        return {
            "success": False,
            "message": (
                "Could not find a recognisable header row. Expected either a "
                "flat table (columns: Date, Start Time, End Time, Title, …) "
                "or a grid (cell A1 with a date like 'May 29th', then a row "
                "with START/END/<squadron columns>/Notes)."
            ),
        }

    parsed_events = []
    skipped_rows = 0
    for row in rows[header_idx + 1:]:
        date = _norm_date(row[header_cols["date"]] if len(row) > header_cols["date"] else "")
        start = _norm_time(row[header_cols["start_time"]] if len(row) > header_cols["start_time"] else "")
        title = (row[header_cols["title"]] if len(row) > header_cols["title"] else "").strip()
        if not (date and start and title):
            skipped_rows += 1
            continue
        end = None
        if "end_time" in header_cols and len(row) > header_cols["end_time"]:
            end = _norm_time(row[header_cols["end_time"]])
        # Default: 15-minute block if no end time given.
        if not end:
            h, m = map(int, start.split(":"))
            total = h * 60 + m + 15
            eh, em = divmod(total, 60)
            end = f"{eh:02d}:{em:02d}"

        def _cell(key):
            return (row[header_cols[key]].strip()
                    if (key in header_cols and len(row) > header_cols[key])
                    else "")

        target_groups_raw = _cell("target_groups")
        if target_groups_raw:
            target_groups = [t.strip().lower() for t in re.split(r"[,;|]", target_groups_raw) if t.strip()]
        else:
            target_groups = ["all"]

        parsed_events.append({
            "date": date,
            "start_time": start,
            "end_time": end,
            "title": title,
            "description": _cell("description") or None,
            "location": _cell("location") or None,
            "event_type": (_cell("event_type") or "general").lower() or "general",
            "target_groups": target_groups,
            "uniform": _cell("uniform") or None,
        })

    if not parsed_events:
        return {
            "success": False,
            "message": f"No valid rows found. Skipped {skipped_rows} rows missing Date/Start Time/Title.",
        }

    now = datetime.now(timezone.utc).isoformat()
    # Replace just the events tagged to THIS schedule — leave manual events
    # and OTHER schedule events alone.
    await db.schedule.delete_many({"source_schedule_id": schedule_id})
    docs = []
    for e in parsed_events:
        docs.append({
            "id": str(uuid.uuid4()),
            "source_schedule_id": schedule_id,
            "source_schedule_label": label,
            "is_published": False,
            "created_at": now,
            "updated_at": now,
            **e,
        })
    await db.schedule.insert_many(docs)

    # Bump the schedule version for any clients watching for changes.
    await db.schedule_settings.update_one(
        {"_id": "settings"},
        {"$inc": {"version": 1},
         "$set": {"last_modified_at": now}},
        upsert=True,
    )

    return {
        "success": True,
        "message": f"{label}: synced {len(parsed_events)} events ({skipped_rows} rows skipped).",
        "event_count": len(parsed_events),
        "skipped": skipped_rows,
    }


async def _persist_schedule_telemetry(schedule_id: str, result: dict) -> None:
    """Update the per-schedule sync status fields inside settings."""
    now = datetime.now(timezone.utc).isoformat()
    await db.google_sheets_settings.update_one(
        {"_id": "settings", "schedules.id": schedule_id},
        {"$set": {
            "schedules.$.last_sync_at": now,
            "schedules.$.last_sync_status": "success" if result.get("success") else "error",
            "schedules.$.last_sync_message": result.get("message"),
            "schedules.$.last_event_count": result.get("event_count"),
        }},
    )


@api_router.post("/google-sheets/schedules/{schedule_id}/sync")
async def sync_one_schedule(schedule_id: str,
                            user: dict = Depends(get_current_user)):
    """Phase 8: manually trigger sync of a single configured schedule."""
    if user.get("role") not in _GSHEET_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")
    settings = await db.google_sheets_settings.find_one({"_id": "settings"})
    if not settings:
        raise HTTPException(status_code=404, detail="No schedules configured.")
    schedules = settings.get("schedules") or []
    cfg = next((s for s in schedules if s.get("id") == schedule_id), None)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Schedule '{schedule_id}' not configured.")
    result = await sync_schedule_from_gsheet(
        cfg["id"], cfg.get("label") or cfg["id"],
        cfg["spreadsheet_id"], cfg.get("gid"),
        cfg.get("sheet_name"),
    )
    await _persist_schedule_telemetry(schedule_id, result)
    return result


# ── Tab auto-discovery (one URL → many day-tabs) ─────────────────────────

from pydantic import BaseModel as _BM


class DiscoverTabsRequest(_BM):
    spreadsheet_id: str   # raw id OR full Sheets URL


class BulkAddSchedulesRequest(_BM):
    spreadsheet_id: str
    tabs: list[dict]   # each: {sheet_name, label, enabled?}


async def _fetch_xlsx_workbook(spreadsheet_id: str):
    """Download a public Google Sheet as XLSX and return an openpyxl workbook.
    Returns None if the sheet is not shared publicly or the download fails.
    """
    from io import BytesIO
    url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        f"/export?format=xlsx"
    )
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            logger.error(f"XLSX export failed: HTTP {resp.status_code}")
            return None
        # Reject HTML error pages
        ctype = resp.headers.get("content-type", "")
        if ctype.startswith("text/html") or resp.content[:4] != b"PK\x03\x04":
            logger.error(f"XLSX export returned non-xlsx content-type: {ctype}")
            return None
        from openpyxl import load_workbook
        return load_workbook(BytesIO(resp.content), read_only=True, data_only=True)
    except Exception as e:
        logger.error(f"Error downloading XLSX: {e}")
        return None


@api_router.post("/google-sheets/discover-tabs")
async def discover_tabs(req: DiscoverTabsRequest,
                        user: dict = Depends(get_current_user)):
    """Download a public Google Sheet, enumerate all tabs and return their
    name + A1 title + a flag for whether the tab looks like a schedule
    (its A1 cell parses as a Month + Day)."""
    if user.get("role") not in _GSHEET_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")

    sid, _gid = _parse_spreadsheet_url(req.spreadsheet_id)
    if not sid:
        raise HTTPException(status_code=400, detail="Invalid spreadsheet id/URL.")

    wb = await _fetch_xlsx_workbook(sid)
    if wb is None:
        raise HTTPException(
            status_code=400,
            detail=("Could not download the spreadsheet. Make sure it is shared "
                    "as 'Anyone with the link – Viewer' and the URL/ID is correct."),
        )

    tabs = []
    for name in wb.sheetnames:
        ws = wb[name]
        a1 = ws["A1"].value
        a1_str = "" if a1 is None else str(a1).strip()
        parsed_date = _extract_grid_date(a1_str, None) if a1_str else None
        # Suggested label: prefer A1 (it's already the day title); else tab name.
        suggested_label = a1_str if (a1_str and parsed_date) else name
        tabs.append({
            "sheet_name": name,
            "a1": a1_str,
            "parsed_date": parsed_date,
            "looks_like_schedule": bool(parsed_date),
            "suggested_label": suggested_label,
        })

    return {
        "spreadsheet_id": sid,
        "tabs": tabs,
        "schedule_tab_count": sum(1 for t in tabs if t["looks_like_schedule"]),
    }


@api_router.post("/google-sheets/schedules/bulk-add")
async def bulk_add_schedules(req: BulkAddSchedulesRequest,
                             user: dict = Depends(get_current_user)):
    """Append a list of {sheet_name, label} entries to the saved schedules
    config — used by the "Discover & Add Tabs" workflow in the Admin UI."""
    if user.get("role") not in _GSHEET_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")
    if not req.tabs:
        raise HTTPException(status_code=400, detail="No tabs provided.")
    sid, _gid = _parse_spreadsheet_url(req.spreadsheet_id)
    if not sid:
        raise HTTPException(status_code=400, detail="Invalid spreadsheet id/URL.")

    settings = await db.google_sheets_settings.find_one(
        {"_id": "settings"}
    ) or {}
    existing = list(settings.get("schedules") or [])
    existing_ids = {s.get("id") for s in existing}
    # Deduplicate by (spreadsheet_id, sheet_name) — never add the same tab twice.
    existing_keys = {(s.get("spreadsheet_id"), s.get("sheet_name") or s.get("gid") or "")
                     for s in existing}

    added = 0
    skipped = 0
    for tab in req.tabs:
        sheet_name = (tab.get("sheet_name") or "").strip()
        label = (tab.get("label") or sheet_name).strip()
        if not sheet_name:
            skipped += 1
            continue
        key = (sid, sheet_name)
        if key in existing_keys:
            skipped += 1
            continue

        # Generate stable id from spreadsheet_id + sheet_name.
        base = _slugify(f"{label or sheet_name}")
        sched_id = base
        i = 1
        while sched_id in existing_ids:
            i += 1
            sched_id = f"{base}_{i}"
        existing_ids.add(sched_id)
        existing_keys.add(key)

        existing.append({
            "id": sched_id,
            "label": label,
            "spreadsheet_id": sid,
            "gid": None,
            "sheet_name": sheet_name,
            "enabled": bool(tab.get("enabled", True)),
            "last_sync_at": None,
            "last_sync_status": None,
            "last_sync_message": None,
            "last_event_count": None,
        })
        added += 1

    await db.google_sheets_settings.update_one(
        {"_id": "settings"},
        {"$set": {"schedules": existing}},
        upsert=True,
    )

    return {
        "added": added,
        "skipped": skipped,
        "total_schedules": len(existing),
    }


async def sync_roster_from_gsheet(spreadsheet_id: str, gid: str) -> dict:
    """Sync roster data from Google Sheet"""
    csv_data = await fetch_google_sheet_csv(spreadsheet_id, gid)
    if not csv_data:
        return {"success": False, "message": "Failed to fetch sheet data"}
    
    try:
        df = pd.read_csv(BytesIO(csv_data.encode('utf-8')))
        df.columns = df.columns.str.strip()
        
        # Column mapping (same as Excel import)
        column_map = {
            'RegistrantsCAPID': 'capid', 'CAPID': 'capid',
            'Rank': 'rank', 'NameLast': 'last_name', 'NameFirst': 'first_name',
            'NameMiddle': 'middle_name', 'Unit': 'unit', 'Wing': 'wing',
            'Region': 'region', 'Gender': 'gender', 'Age': 'age',
            'AgeAtEventStart': 'age_at_event', 'Email': 'email',
            'HomePhonePrimary': 'phone', 'CellPhonePrimary': 'cell_phone',
            'ShirtSize': 'shirt_size', 'MbrType': 'member_type',
            'StaffMember': 'staff_member', 'PaidInFull': 'paid_in_full',
            'AmountPaid': 'amount_paid', 'RegistrationStatus': 'registration_status',
            'UnitApproved': 'unit_approved', 'WingApproved': 'wing_approved',
            'Addr1': 'address', 'City': 'city', 'State': 'state', 'Zip': 'zip_code',
            'EmergencyContactName': 'emergency_contact', 'EmergencyContactNumber': 'emergency_phone',
            'CadetParentPhonePrimary': 'cadet_parent_phone', 'CadetParentEmailPrimary': 'cadet_parent_email',
            'UnitCCName': 'unit_cc_name', 'UnitCCEmail': 'unit_cc_email',
            'LastEncampment': 'last_encampment', 'CPPTExpiration': 'cppt_expiration',
            'FirstAid': 'first_aid', 'SubEvents': 'sub_events',
            # Application timestamp — used for waitlist sort. Accept both spellings.
            'AppEditDate': 'app_edit_data',
            'AppEditData': 'app_edit_data',
        }
        
        df = df.rename(columns=column_map)
        
        imported_count = 0
        updated_count = 0
        now = datetime.now(timezone.utc).isoformat()
        
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            
            def get_val(key, default=None):
                val = row_dict.get(key)
                if pd.isna(val) or val == '' or val == 'nan':
                    return default
                return val
            
            def get_str(key, default=''):
                val = get_val(key, default)
                return str(val).strip() if val is not None else default
            
            def get_unit(key, default=''):
                """Get unit value and clean up float formatting (e.g., '96.0' -> '96')"""
                val = get_val(key, default)
                if val is None:
                    return default
                val_str = str(val).strip()
                # Remove .0 suffix if present (from float conversion)
                if val_str.endswith('.0'):
                    val_str = val_str[:-2]
                return val_str
            
            def get_bool(key):
                val = get_val(key)
                if val is None:
                    return False
                if isinstance(val, bool):
                    return val
                return str(val).lower() in ['yes', 'true', '1']
            
            def get_float(key, default=0.0):
                val = get_val(key)
                if val is None:
                    return default
                try:
                    return float(val)
                except:
                    return default
            
            def get_int(key, default=None):
                val = get_val(key)
                if val is None:
                    return default
                try:
                    return int(float(val))
                except:
                    return default
            
            # Generate CAPID if not present
            capid = get_str('capid', '')
            if not capid:
                email = get_str('email', '')
                if email:
                    email_prefix = email.split('@')[0] if '@' in email else ''
                    numeric_parts = ''.join(filter(str.isdigit, email_prefix))
                    if len(numeric_parts) >= 5:
                        capid = numeric_parts[:6]
                
                if not capid:
                    last_name = get_str('last_name', '')
                    first_name = get_str('first_name', '')
                    wing = get_str('wing', 'XX')
                    unit = get_str('unit', '000')
                    if last_name and first_name:
                        import hashlib
                        composite = f"{last_name}_{first_name}_{wing}_{unit}".upper()
                        hash_digest = hashlib.sha256(composite.encode()).hexdigest()[:6]
                        capid = f"GEN{hash_digest.upper()}"
                    else:
                        continue
            
            # ── Canonical classification ──────────────────────────────
            # The Registration Zone SubEvents column is the single source of
            # truth. The generic `staff_member` boolean is NOT consulted.
            # Cadets in mismatched sub-events become `needs_review`.
            from classifier import classify_from_subevent
            member_type = get_str('member_type', '').upper()
            sub_events = get_str('sub_events', '')
            participant_type = classify_from_subevent(member_type, sub_events)
            
            participant_data = {
                'capid': capid,
                'rank': get_str('rank'),
                'last_name': get_str('last_name'),
                'first_name': get_str('first_name'),
                'middle_name': get_str('middle_name'),
                'name': f"{get_str('last_name')}, {get_str('first_name')}",
                'unit': get_unit('unit'),
                'wing': get_str('wing'),
                'region': get_str('region'),
                'gender': get_str('gender'),
                'age': get_int('age'),
                'age_at_event': get_int('age_at_event'),
                'email': get_str('email'),
                'phone': get_str('phone'),
                'cell_phone': get_str('cell_phone'),
                'shirt_size': get_str('shirt_size'),
                'member_type': member_type,
                'participant_type': participant_type,
                'paid_in_full': get_bool('paid_in_full'),
                'amount_paid': get_float('amount_paid'),
                'paid': get_bool('paid_in_full') or get_float('amount_paid') > 0,
                'registration_status': get_str('registration_status'),
                'staff_member': get_bool('staff_member'),
                'unit_approved': get_bool('unit_approved'),
                'wing_approved': get_bool('wing_approved'),
                'address': get_str('address'),
                'city': get_str('city'),
                'state': get_str('state'),
                'zip_code': get_str('zip_code'),
                'emergency_contact': get_str('emergency_contact'),
                'emergency_phone': get_str('emergency_phone'),
                'cadet_parent_phone': get_str('cadet_parent_phone'),
                'cadet_parent_email': get_str('cadet_parent_email'),
                'unit_cc_name': get_str('unit_cc_name'),
                'unit_cc_email': get_str('unit_cc_email'),
                'last_encampment': get_str('last_encampment'),
                'cppt_expiration': get_str('cppt_expiration'),
                'first_aid': get_str('first_aid'),
                'app_edit_data': get_str('app_edit_data') or None,
                'updated_at': now,
            }
            
            # Upsert by CAPID
            existing = await db.participants.find_one({'capid': capid})
            if existing:
                await db.participants.update_one(
                    {'capid': capid},
                    {'$set': participant_data}
                )
                updated_count += 1
            else:
                participant_data['id'] = str(uuid.uuid4())
                participant_data['created_at'] = now
                participant_data['is_removed'] = False
                await db.participants.insert_one(participant_data)
                imported_count += 1
        
        return {
            "success": True,
            "message": f"Roster sync complete: {imported_count} new, {updated_count} updated",
            "imported": imported_count,
            "updated": updated_count,
            "total": imported_count + updated_count
        }
    
    except Exception as e:
        logger.error(f"Error syncing roster: {e}")
        return {"success": False, "message": str(e)}

async def sync_orgchart_from_gsheet(spreadsheet_id: str, gid: str) -> dict:
    """Sync org chart data from Google Sheet"""
    csv_data = await fetch_google_sheet_csv(spreadsheet_id, gid)
    if not csv_data:
        return {"success": False, "message": "Failed to fetch org chart sheet data"}
    
    try:
        # Parse CSV into rows
        lines = csv_data.strip().split('\n')
        rows = []
        for line in lines:
            # Simple CSV parsing (handles basic cases)
            row = []
            current = ''
            in_quotes = False
            for char in line:
                if char == '"':
                    in_quotes = not in_quotes
                elif char == ',' and not in_quotes:
                    row.append(current.strip())
                    current = ''
                else:
                    current += char
            row.append(current.strip())
            rows.append(row)
        
        now = datetime.now(timezone.utc).isoformat()
        roles_created = 0
        roles_updated = 0
        
        # Define the org chart structure we're looking for
        # Parse key positions from the spreadsheet layout
        org_roles = []
        
        # Helper to parse name and find matching participant
        async def parse_and_match_member(name_str, rank_str=None):
            """Parse name string and try to find matching participant"""
            if not name_str or name_str.strip() == '':
                return None, None, None
            
            # Clean the name string - remove quotes and extra spaces
            name_str = name_str.strip().strip('"').strip()
            if not name_str:
                return None, None, None
                
            # Parse "Last, First" or "Last, First M.I." format
            parts = name_str.split(',')
            if len(parts) >= 2:
                last_name = parts[0].strip()
                first_name = parts[1].strip().split()[0] if parts[1].strip() else ''
            else:
                # Try "First Last" format
                name_parts = name_str.split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = name_parts[-1]
                else:
                    last_name = name_str
                    first_name = ''
            
            # Try to find matching participant
            participant = await db.participants.find_one({
                '$or': [
                    {'last_name': {'$regex': f'^{last_name}', '$options': 'i'}, 'first_name': {'$regex': f'^{first_name}', '$options': 'i'}},
                    {'name': {'$regex': f'{last_name}.*{first_name}', '$options': 'i'}},
                    {'name': {'$regex': f'{first_name}.*{last_name}', '$options': 'i'}}
                ]
            }, {'_id': 0, 'id': 1, 'capid': 1, 'name': 1, 'rank': 1})
            
            participant_id = participant.get('id') if participant else None
            return last_name, first_name, participant_id
        
        # Parse specific positions from known cell locations
        # Row 19 (index 18) has main command staff
        if len(rows) > 19:
            row = rows[18]  # 0-indexed, so row 19 is index 18
            
            # Commandant of Cadets - columns around index 6-10
            if len(row) > 13:
                commandant_rank = row[12] if len(row) > 12 else ''
                commandant_name = row[13] if len(row) > 13 else ''
                if commandant_name:
                    last, first, pid = await parse_and_match_member(commandant_name, commandant_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'commandant',
                            'title': 'Commandant of Cadets',
                            'abbreviation': 'ENC/CW',
                            'category': 'Command',
                            'level': 1,
                            'parent_role_id': 'commander',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': commandant_rank.strip() if commandant_rank else None,
                            'assigned_participant_id': pid
                        })
            
            # Encampment Commander - columns around index 18-22
            if len(row) > 19:
                enc_cc_rank = row[18] if len(row) > 18 else ''
                enc_cc_name = row[19] if len(row) > 19 else ''
                if enc_cc_name:
                    last, first, pid = await parse_and_match_member(enc_cc_name, enc_cc_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'commander',
                            'title': 'Encampment Commander',
                            'abbreviation': 'ENC/CC',
                            'category': 'Command',
                            'level': 0,
                            'parent_role_id': None,
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': enc_cc_rank.strip() if enc_cc_rank else None,
                            'assigned_participant_id': pid
                        })
            
            # Deputy CC for Support - columns around index 24-28
            if len(row) > 25:
                dep_rank = row[24] if len(row) > 24 else ''
                dep_name = row[25] if len(row) > 25 else ''
                if dep_name:
                    last, first, pid = await parse_and_match_member(dep_name, dep_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'deputy_support',
                            'title': 'Deputy CC for Support',
                            'abbreviation': 'ENC/DCS',
                            'category': 'Command',
                            'level': 1,
                            'parent_role_id': 'commander',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': dep_rank.strip() if dep_rank else None,
                            'assigned_participant_id': pid
                        })
        
        # Row 20 has more staff positions
        if len(rows) > 20:
            row = rows[19]
            # 60th CTG/CD
            if len(row) > 13:
                cd_rank = row[12] if len(row) > 12 else ''
                cd_name = row[13] if len(row) > 13 else ''
                if cd_name:
                    last, first, pid = await parse_and_match_member(cd_name, cd_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'ctg_cd',
                            'title': '60th CTG Deputy Commander',
                            'abbreviation': '60th CTG/CD',
                            'category': 'Cadet Training',
                            'level': 2,
                            'parent_role_id': 'commandant',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': cd_rank.strip() if cd_rank else None,
                            'assigned_participant_id': pid
                        })
        
        # Row 21 - ENC Superintendent
        if len(rows) > 21:
            row = rows[20]
            if len(row) > 19:
                sup_rank = row[18] if len(row) > 18 else ''
                sup_name = row[19] if len(row) > 19 else ''
                if sup_name:
                    last, first, pid = await parse_and_match_member(sup_name, sup_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'superintendent',
                            'title': 'Encampment Superintendent',
                            'abbreviation': 'ENC/CCEA',
                            'category': 'Operations',
                            'level': 2,
                            'parent_role_id': 'commander',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': sup_rank.strip() if sup_rank else None,
                            'assigned_participant_id': pid
                        })
        
        # Row 22 - 60th CTG/DOA
        if len(rows) > 22:
            row = rows[21]
            if len(row) > 13:
                doa_rank = row[12] if len(row) > 12 else ''
                doa_name = row[13] if len(row) > 13 else ''
                if doa_name:
                    last, first, pid = await parse_and_match_member(doa_name, doa_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'ctg_doa',
                            'title': '60th CTG Director of Academics',
                            'abbreviation': '60th CTG/DOA',
                            'category': 'Cadet Training',
                            'level': 2,
                            'parent_role_id': 'commandant',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': doa_rank.strip() if doa_rank else None,
                            'assigned_participant_id': pid
                        })
        
        # Row 27 - Health Services Officer
        if len(rows) > 27:
            row = rows[26]
            if len(row) > 19:
                hso_rank = row[18] if len(row) > 18 else ''
                hso_name = row[19] if len(row) > 19 else ''
                if hso_name:
                    last, first, pid = await parse_and_match_member(hso_name, hso_rank)
                    if last:
                        org_roles.append({
                            'role_id': 'health_services',
                            'title': 'Health Services Officer',
                            'abbreviation': 'ENC/HS',
                            'category': 'Support',
                            'level': 2,
                            'parent_role_id': 'deputy_support',
                            'assigned_member_name': f"{last}, {first}" if first else last,
                            'assigned_member_rank': hso_rank.strip() if hso_rank else None,
                            'assigned_participant_id': pid
                        })
        
        # Parse support staff from column around 24-28 (rows 21-28)
        support_positions = [
            (21, 'support_staff_1', 'Support Staff'),
            (22, 'plans_programs', 'Plans and Programs Officer'),
            (23, 'logistics_1', 'Logistics Officer'),
            (24, 'logistics_2', 'Logistics Officer'),
            (25, 'word_emeritus', 'WORD Officer / HS Emeritus'),
            (26, 'communications', 'Communications Director'),
            (27, 'public_affairs', 'Public Affairs Officer'),
            (28, 'dining_facility', 'Dining Facility Officer'),
            (29, 'finance', 'Finance Officer'),
        ]
        
        for row_idx, role_id, title in support_positions:
            if len(rows) > row_idx:
                row = rows[row_idx - 1]  # Convert to 0-indexed
                if len(row) > 28:
                    supp_rank = row[24] if len(row) > 24 else ''
                    supp_name = row[25] if len(row) > 25 else ''
                    if supp_name and supp_name.strip():
                        last, first, pid = await parse_and_match_member(supp_name, supp_rank)
                        if last:
                            org_roles.append({
                                'role_id': role_id,
                                'title': title,
                                'abbreviation': role_id.upper().replace('_', '/'),
                                'category': 'Support',
                                'level': 3,
                                'parent_role_id': 'deputy_support',
                                'assigned_member_name': f"{last}, {first}" if first else last,
                                'assigned_member_rank': supp_rank.strip() if supp_rank else None,
                                'assigned_participant_id': pid
                            })
        
        # Parse Squadron Commanders from row 35 area
        squadrons = [
            (35, 0, '6th_cts_cc', '6th CTS Commander', '6th CTS/CC', 'commandant'),
            (35, 12, '21st_cts_cc', '21st CTS Commander', '21st CTS/CC', 'commandant'),
            (35, 24, '22nd_cts_cc', '22nd CTS Commander', '22nd CTS/CC', 'commandant'),
        ]
        
        # Parse Flight Sergeants and Commanders from flights row (around row 41)
        flights_row_idx = None
        for idx, row in enumerate(rows):
            if len(row) > 0 and 'ALPHA' in str(row[0]).upper():
                flights_row_idx = idx
                break
        
        if flights_row_idx:
            # Flight names are in this row
            flight_cols = {
                'ALPHA': (0, '6th_cts_cc'),
                'BRAVO': (6, '6th_cts_cc'),
                'CHARLIE': (12, '21st_cts_cc'),
                'DELTA': (18, '21st_cts_cc'),
                'ECHO': (24, '22nd_cts_cc'),
                'FOXTROT': (30, '22nd_cts_cc')
            }
            
            for flight_name, (col_offset, parent_id) in flight_cols.items():
                org_roles.append({
                    'role_id': f'flight_{flight_name.lower()}_commander',
                    'title': f'{flight_name} Flight Commander',
                    'abbreviation': f'{flight_name[:1]}FLT/CC',
                    'category': 'Flight',
                    'level': 4,
                    'parent_role_id': parent_id,
                    'assigned_member_name': None,
                    'assigned_member_rank': None,
                    'assigned_participant_id': None
                })
                org_roles.append({
                    'role_id': f'flight_{flight_name.lower()}_sergeant',
                    'title': f'{flight_name} Flight Sergeant',
                    'abbreviation': f'{flight_name[:1]}FLT/FS',
                    'category': 'Flight',
                    'level': 4,
                    'parent_role_id': f'flight_{flight_name.lower()}_commander',
                    'assigned_member_name': None,
                    'assigned_member_rank': None,
                    'assigned_participant_id': None
                })
        
        # Now upsert all roles to the database
        for role_data in org_roles:
            role_id = role_data['role_id']
            existing = await db.org_chart_roles.find_one({'role_id': role_id})
            
            if existing:
                await db.org_chart_roles.update_one(
                    {'role_id': role_id},
                    {'$set': {
                        'assigned_member_name': role_data.get('assigned_member_name'),
                        'assigned_member_rank': role_data.get('assigned_member_rank'),
                        'assigned_participant_id': role_data.get('assigned_participant_id'),
                        'updated_at': now
                    }}
                )
                roles_updated += 1
            else:
                role_data['id'] = str(uuid.uuid4())
                role_data['responsibilities'] = ''
                role_data['created_at'] = now
                role_data['updated_at'] = now
                await db.org_chart_roles.insert_one(role_data)
                roles_created += 1
        
        # ================= PARSE FLIGHT ASSIGNMENTS =================
        # Find the row with flight headers (ALPHA, BRAVO, etc.)
        flights_header_idx = None
        for idx, row in enumerate(rows):
            if len(row) > 0 and 'ALPHA' in str(row[0]).upper():
                flights_header_idx = idx
                break
        
        students_assigned = 0
        if flights_header_idx is not None:
            # Flight column positions (each flight spans ~6 columns)
            # Based on the spreadsheet: ALPHA(0-5), BRAVO(6-11), CHARLIE(12-17), DELTA(18-23), ECHO(24-29), FOXTROT(30-35)
            flight_config = {
                'Alpha': {'col_offset': 0, 'squadron': '6th CTS', 'squadron_full': '6th Cadet Training Squadron'},
                'Bravo': {'col_offset': 6, 'squadron': '6th CTS', 'squadron_full': '6th Cadet Training Squadron'},
                'Charlie': {'col_offset': 12, 'squadron': '21st CTS', 'squadron_full': '21st Cadet Training Squadron'},
                'Delta': {'col_offset': 18, 'squadron': '21st CTS', 'squadron_full': '21st Cadet Training Squadron'},
                'Echo': {'col_offset': 24, 'squadron': '22nd CTS', 'squadron_full': '22nd Cadet Training Squadron'},
                'Foxtrot': {'col_offset': 30, 'squadron': '22nd CTS', 'squadron_full': '22nd Cadet Training Squadron'},
            }
            
            # Skip header row (GRADE, LAST NAME...) and start from data rows (2 rows after ALPHA header)
            data_start_idx = flights_header_idx + 2
            
            # Parse each row until we hit "Total Cadets" or empty rows
            for row_idx in range(data_start_idx, len(rows)):
                row = rows[row_idx]
                
                # Check if we've reached the end (Total Cadets row)
                row_str = ','.join(row).lower()
                if 'total cadets' in row_str:
                    break
                
                # Process each flight column
                for flight_name, config in flight_config.items():
                    col = config['col_offset']
                    
                    # Get rank/grade (col+0), name (col+1), age (col+2), unit (col+3)
                    if len(row) > col + 3:
                        rank = row[col].strip() if row[col] else ''
                        name = row[col + 1].strip() if len(row) > col + 1 else ''
                        age_str = row[col + 2].strip() if len(row) > col + 2 else ''
                        unit = row[col + 3].strip() if len(row) > col + 3 else ''
                        
                        # Skip empty entries
                        if not name or name == '':
                            continue
                        
                        # Parse name (format: "LAST, FIRST M.I.")
                        name = name.strip().strip('"')
                        name_parts = name.split(',')
                        if len(name_parts) >= 2:
                            last_name = name_parts[0].strip()
                            first_part = name_parts[1].strip()
                            first_name = first_part.split()[0] if first_part else ''
                        else:
                            continue
                        
                        # Try to find matching participant in the roster
                        participant = await db.participants.find_one({
                            '$or': [
                                {'last_name': {'$regex': f'^{last_name}$', '$options': 'i'}, 
                                 'first_name': {'$regex': f'^{first_name}', '$options': 'i'}},
                                {'name': {'$regex': f'{last_name}.*{first_name}', '$options': 'i'}},
                            ]
                        })
                        
                        if participant:
                            # Update participant with flight and squadron assignment
                            await db.participants.update_one(
                                {'_id': participant['_id']},
                                {'$set': {
                                    'flight': flight_name,
                                    'squadron': config['squadron'],
                                    'squadron_full': config['squadron_full'],
                                    # Do NOT rewrite participant_type here —
                                    # classification is owned by the import
                                    # classifier and the canonical migration.
                                    # This branch only assigns flight/squadron.
                                    'updated_at': now
                                }}
                            )
                            students_assigned += 1
                            logger.info(f"Assigned {last_name}, {first_name} to {flight_name} Flight ({config['squadron']})")
        
        return {
            "success": True,
            "message": f"Org chart sync complete: {roles_created} new roles, {roles_updated} updated, {students_assigned} students assigned to flights",
            "created": roles_created,
            "updated": roles_updated,
            "students_assigned": students_assigned,
            "total": roles_created + roles_updated
        }
    
    except Exception as e:
        logger.error(f"Error syncing org chart: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"success": False, "message": str(e)}

async def perform_scheduled_sync():
    """Perform scheduled sync of all configured sheets"""
    logger.info("Starting scheduled Google Sheets sync...")
    
    settings = await db.google_sheets_settings.find_one({'_id': 'settings'})
    if not settings:
        logger.info("No Google Sheets settings configured, skipping sync")
        return
    
    if not settings.get('auto_sync_enabled', True):
        logger.info("Auto sync is disabled, skipping")
        return
    
    # Update status to running
    await db.google_sheets_settings.update_one(
        {'_id': 'settings'},
        {'$set': {'last_sync_status': 'running', 'last_sync_message': 'Sync in progress...'}}
    )
    
    try:
        results = []

        # Phase 8: sync configured schedules (CAST, Encampment, etc.)
        for cfg in (settings.get("schedules") or []):
            if not cfg.get("enabled"):
                continue
            sched_result = await sync_schedule_from_gsheet(
                cfg["id"], cfg.get("label") or cfg["id"],
                cfg["spreadsheet_id"], cfg.get("gid"),
                cfg.get("sheet_name"),
            )
            await _persist_schedule_telemetry(cfg["id"], sched_result)
            results.append(sched_result.get("message", "unknown"))

        # Sync org chart sheets
        org_chart_sheets = settings.get('org_chart_sheets', [])
        for org_config in org_chart_sheets:
            if org_config and org_config.get('enabled'):
                org_result = await sync_orgchart_from_gsheet(
                    org_config['spreadsheet_id'],
                    org_config['gid']
                )
                results.append(f"Org Chart: {org_result.get('message', 'unknown')}")
        
        # Update success status
        now = datetime.now(timezone.utc).isoformat()
        await db.google_sheets_settings.update_one(
            {'_id': 'settings'},
            {'$set': {
                'last_sync_at': now,
                'last_sync_status': 'success',
                'last_sync_message': '; '.join(results) if results else 'No sheets configured'
            }}
        )
        logger.info(f"Scheduled sync completed: {results}")
        
    except Exception as e:
        logger.error(f"Scheduled sync failed: {e}")
        await db.google_sheets_settings.update_one(
            {'_id': 'settings'},
            {'$set': {
                'last_sync_at': datetime.now(timezone.utc).isoformat(),
                'last_sync_status': 'error',
                'last_sync_message': str(e)
            }}
        )



