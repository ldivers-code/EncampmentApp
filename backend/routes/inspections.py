"""Inspections & Points — recreates the spreadsheet at
https://docs.google.com/spreadsheets/d/1el_Xsuv1PnmOqFkzSVLWag_KSTICR3wmyTf0v4Ei11E
inside the app.

Five inspection types (mirroring the workbook):
  * `dorm_uniform`         — per-cadet, 8 fields, /20 (Day 2 #1 initial)
  * `dorm_uniform_repeat`  — per-cadet, same 8 fields, /20 (Day 2 #2, Day 4, Day 6)
  * `drill`                — flight-level, 18 movements each scored 0–3, /(18*3)
  * `daily_sports`         — flight-level, single score, /20 (default max)
  * `knowledge`            — per-cadet, 9 Q's, /9

Per the spreadsheet:
  * Per-cadet inspections: flight % = AVERAGE(cadets' %) ignoring blanks/absent.
  * Drill / Sports are flight-level — their `percent` IS the flight %.
  * CTF Average (per flight per day) = AVERAGE of % across inspections that ran.
  * CTF Points  (per flight per day) = SUM(% * weight) across inspections.
  * CTS Average = AVERAGE of CTF Average for the two flights in the squadron.
  * CTS Points  = SUM of CTF Points for those flights.
  * Weekly Total per flight = SUM of CTF Points across days.
  * Weekly Change = CTF Points(day N) − CTF Points(day N−1); Day 1 baseline = 0.

The TOTALS U22:W26 weights live in `inspection_settings.weights` and are
editable from the UI. The Day-2 #1 hardcoded *20 quirk is preserved by
giving the `dorm_uniform` (initial) inspection type its own weight default
of 20, while `dorm_uniform_repeat` defaults to 100 (= TOTALS W22).
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from database import db, api_router
from models import UserRole
from permissions import get_current_user

logger_name = "inspections"
import logging
logger = logging.getLogger(logger_name)


# ── RBAC ─────────────────────────────────────────────────────────────
# Roles that can view & enter inspection data.
INSPECTION_ROLES: set[str] = {
    UserRole.EXEC_CADRE,
    UserRole.EXECUTIVE_STAFF,
    UserRole.PLANS_PROGRAMS,
    # Admin overrides — they can see everything anyway:
    UserRole.COMMANDER,
    UserRole.DCP,
}


async def require_inspection_role(user: dict = Depends(get_current_user)):
    if (user or {}).get("role") not in INSPECTION_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Inspections & Points is restricted to Exec Cadre, Exec Staff, "
                   "Plans & Programs (cadre or staff), and full admins.",
        )
    return user


# ── Constants ────────────────────────────────────────────────────────
INSPECTION_TYPES = (
    "dorm_uniform",
    "dorm_uniform_repeat",
    "drill",
    "daily_sports",
    "knowledge",
)
FLIGHTS = ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot")
FLIGHT_TO_SQUADRON = {
    "alpha": "6th_cts", "bravo": "6th_cts",
    "charlie": "21st_cts", "delta": "21st_cts",
    "echo": "22nd_cts", "foxtrot": "22nd_cts",
}
SQUADRON_FLIGHTS = {
    "6th_cts": ("alpha", "bravo"),
    "21st_cts": ("charlie", "delta"),
    "22nd_cts": ("echo", "foxtrot"),
}
DAYS = (1, 2, 3, 4, 5, 6)

# Category field definitions per inspection type — mirror the workbook.
DORM_FIELDS = [
    "personal_appearance", "garments", "accoutrements", "footwear",
    "shirt_fold", "socks_fold", "bunks", "barrack_cleanliness",
]
DORM_MAX_TOTAL = 20  # workbook divides by 20 → percent

DRILL_FIELDS = [
    "fall_in", "dress_right_dress", "ready_front", "at_ease",
    "flight_attention", "present_arms", "order_arms", "left_face",
    "right_face", "about_face", "parade_rest", "hand_salute",
    "forward_march", "incline_to_the_left", "incline_to_the_right",
    "flight_halt", "column_of_files", "fall_out",
]
DRILL_MAX_PER_FIELD = 3  # scored 0–3
DRILL_MAX_TOTAL = len(DRILL_FIELDS) * DRILL_MAX_PER_FIELD  # 54

KNOWLEDGE_FIELDS = [f"q{i}" for i in range(1, 10)]   # 9 questions
KNOWLEDGE_MAX_TOTAL = 9

SPORTS_FIELDS = ["sports_score"]
SPORTS_MAX_TOTAL = 20

PER_CADET_TYPES = {"dorm_uniform", "dorm_uniform_repeat", "knowledge"}
FLIGHT_LEVEL_TYPES = {"drill", "daily_sports"}

INSPECTION_FIELDS: dict[str, list[str]] = {
    "dorm_uniform":         DORM_FIELDS,
    "dorm_uniform_repeat":  DORM_FIELDS,
    "drill":                DRILL_FIELDS,
    "knowledge":            KNOWLEDGE_FIELDS,
    "daily_sports":         SPORTS_FIELDS,
}
INSPECTION_MAX_TOTAL: dict[str, int] = {
    "dorm_uniform":         DORM_MAX_TOTAL,
    "dorm_uniform_repeat":  DORM_MAX_TOTAL,
    "drill":                DRILL_MAX_TOTAL,
    "knowledge":            KNOWLEDGE_MAX_TOTAL,
    "daily_sports":         SPORTS_MAX_TOTAL,
}

# Workbook-default category weights — TOTALS U22:W26.
DEFAULT_WEIGHTS: dict[str, float] = {
    "dorm_uniform":         20.0,   # Day-2 #1 hardcoded *20 in workbook
    "dorm_uniform_repeat":  100.0,  # W22
    "drill":                100.0,  # W23
    "daily_sports":         20.0,   # W24
    "knowledge":            100.0,  # W25
    "app":                  10.0,   # W26 — "App" — not yet captured as an
                                    # inspection but kept for future use.
}

# Workbook-default Day → inspections mapping (matches TOTALS section
# headers). Day 1 is baseline (no inspections).
DEFAULT_DAY_INSPECTIONS: dict[str, list[str]] = {
    "1": [],
    "2": ["dorm_uniform", "dorm_uniform_repeat", "drill", "daily_sports", "knowledge"],
    "3": ["drill", "daily_sports", "knowledge"],
    "4": ["dorm_uniform_repeat", "daily_sports"],
    "5": ["drill", "daily_sports", "knowledge"],
    "6": ["dorm_uniform_repeat", "knowledge"],
}


# ── Pydantic models ──────────────────────────────────────────────────
class CadetScoreIn(BaseModel):
    cadet_participant_id: Optional[str] = None
    cadet_name: str = ""
    field_scores: dict[str, float] = Field(default_factory=dict)
    absent: bool = False


class ScoreUpsertBody(BaseModel):
    day: int
    flight: str
    inspection_type: str
    # For per-cadet types — full set of cadet rows (idempotent replace).
    cadet_scores: Optional[list[CadetScoreIn]] = None
    # For flight-level types — single set of field scores.
    field_scores: Optional[dict[str, float]] = None


class SettingsUpdateBody(BaseModel):
    day_inspections: Optional[dict[str, list[str]]] = None
    weights: Optional[dict[str, float]] = None
    include_merit_points: Optional[bool] = None


# ── Helpers ──────────────────────────────────────────────────────────
async def _get_settings() -> dict:
    doc = await db.inspection_settings.find_one({"_id": "default"}, {"_id": 0})
    if not doc:
        doc = {
            "day_inspections": dict(DEFAULT_DAY_INSPECTIONS),
            "weights": dict(DEFAULT_WEIGHTS),
            "include_merit_points": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.inspection_settings.replace_one(
            {"_id": "default"}, {"_id": "default", **doc}, upsert=True,
        )
    return doc


def _compute_total_percent(inspection_type: str, field_scores: dict) -> tuple[float, float]:
    """Sum the listed fields. Percent = total / type's max_total."""
    fields = INSPECTION_FIELDS[inspection_type]
    total = 0.0
    for f in fields:
        v = field_scores.get(f)
        if isinstance(v, (int, float)):
            total += float(v)
    max_total = INSPECTION_MAX_TOTAL[inspection_type] or 1
    return total, total / max_total


def _validate_inspection_type(t: str):
    if t not in INSPECTION_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid inspection_type '{t}'")


def _validate_day(d: int):
    if d not in DAYS:
        raise HTTPException(status_code=400, detail=f"Invalid day {d}")


def _validate_flight(f: str):
    if f not in FLIGHTS:
        raise HTTPException(status_code=400, detail=f"Invalid flight '{f}'")


async def _flight_percent(day: int, flight: str, inspection_type: str) -> Optional[float]:
    """Compute the flight's percent for one inspection on one day.

    Per-cadet types: AVERAGE of present cadets' percents (absent / blank
    field_scores rows are excluded).
    Flight-level types: returns the single stored percent.
    Returns None if no scoring data exists.
    """
    if inspection_type in FLIGHT_LEVEL_TYPES:
        doc = await db.inspection_scores.find_one(
            {"day": day, "flight": flight, "inspection_type": inspection_type,
             "cadet_participant_id": None},
            {"_id": 0, "percent": 1},
        )
        if not doc:
            return None
        return doc.get("percent")

    cur = db.inspection_scores.find(
        {"day": day, "flight": flight, "inspection_type": inspection_type,
         "cadet_participant_id": {"$ne": None}, "absent": {"$ne": True}},
        {"_id": 0, "percent": 1, "field_scores": 1},
    )
    percents: list[float] = []
    async for d in cur:
        # Skip rows with completely empty field_scores so a placeholder
        # row never counts as a 0 (matches spreadsheet rule).
        fs = d.get("field_scores") or {}
        if not any(isinstance(v, (int, float)) for v in fs.values()):
            continue
        p = d.get("percent")
        if isinstance(p, (int, float)):
            percents.append(p)
    if not percents:
        return None
    return sum(percents) / len(percents)


async def _ctf_for_day_flight(day: int, flight: str, settings: dict) -> dict:
    """Compute CTF Average + CTF Points for one (day, flight)."""
    enabled = settings["day_inspections"].get(str(day), [])
    weights = settings["weights"]
    per_inspection: dict[str, dict] = {}
    pcts = []
    total_points = 0.0
    for t in enabled:
        if t not in INSPECTION_TYPES:
            continue
        pct = await _flight_percent(day, flight, t)
        wt = float(weights.get(t, DEFAULT_WEIGHTS.get(t, 0)))
        if pct is not None:
            pcts.append(pct)
            pts = pct * wt
            total_points += pts
        else:
            pts = 0.0
        per_inspection[t] = {"percent": pct, "weight": wt, "points": pts}
    ctf_avg = sum(pcts) / len(pcts) if pcts else 0.0
    return {
        "flight": flight,
        "day": day,
        "per_inspection": per_inspection,
        "ctf_average": ctf_avg,
        "ctf_points": total_points,
    }


async def _merit_points_for_day_flight(day: int, flight: str) -> float:
    doc = await db.flight_merit_points.find_one(
        {"day": day, "flight": flight}, {"_id": 0, "points": 1},
    )
    if not doc:
        return 0.0
    v = doc.get("points")
    return float(v) if isinstance(v, (int, float)) else 0.0


# ── Settings endpoints ───────────────────────────────────────────────
@api_router.get("/inspections/settings")
async def get_inspection_settings(user: dict = Depends(require_inspection_role)):
    return await _get_settings()


@api_router.put("/inspections/settings")
async def update_inspection_settings(
    body: SettingsUpdateBody,
    user: dict = Depends(require_inspection_role),
):
    settings = await _get_settings()
    if body.day_inspections is not None:
        # Validate keys + values
        clean: dict[str, list[str]] = {}
        for k, lst in body.day_inspections.items():
            try:
                day = int(k)
            except (TypeError, ValueError):
                continue
            if day not in DAYS:
                continue
            clean[str(day)] = [t for t in (lst or []) if t in INSPECTION_TYPES]
        # Ensure all 6 days present
        for d in DAYS:
            clean.setdefault(str(d), settings["day_inspections"].get(str(d), []))
        settings["day_inspections"] = clean
    if body.weights is not None:
        merged = dict(settings.get("weights") or DEFAULT_WEIGHTS)
        for k, v in body.weights.items():
            if k in DEFAULT_WEIGHTS and isinstance(v, (int, float)):
                merged[k] = float(v)
        settings["weights"] = merged
    if body.include_merit_points is not None:
        settings["include_merit_points"] = bool(body.include_merit_points)
    settings["updated_at"] = datetime.now(timezone.utc).isoformat()
    settings["updated_by"] = user.get("id")
    await db.inspection_settings.replace_one(
        {"_id": "default"}, {"_id": "default", **settings}, upsert=True,
    )
    return settings


# ── Score CRUD ───────────────────────────────────────────────────────
@api_router.get("/inspections/scores")
async def list_scores(
    day: Optional[int] = None,
    flight: Optional[str] = None,
    inspection_type: Optional[str] = None,
    user: dict = Depends(require_inspection_role),
):
    q: dict = {}
    if day is not None:
        _validate_day(day); q["day"] = day
    if flight:
        _validate_flight(flight); q["flight"] = flight
    if inspection_type:
        _validate_inspection_type(inspection_type); q["inspection_type"] = inspection_type
    cur = db.inspection_scores.find(q, {"_id": 0}).sort([("day", 1), ("flight", 1)])
    return await cur.to_list(2000)


@api_router.put("/inspections/scores")
async def upsert_scores(
    body: ScoreUpsertBody,
    user: dict = Depends(require_inspection_role),
):
    """Idempotent replace for one (day, flight, inspection_type).

    * Per-cadet types — accepts `cadet_scores` list. Existing rows for
      this (day, flight, type) are deleted, then the new rows inserted.
    * Flight-level types — accepts `field_scores`. Upserts a single row
      with `cadet_participant_id=None`.
    """
    _validate_day(body.day)
    _validate_flight(body.flight)
    _validate_inspection_type(body.inspection_type)
    now = datetime.now(timezone.utc).isoformat()
    recorder = user.get("id")

    await db.inspection_scores.delete_many({
        "day": body.day, "flight": body.flight,
        "inspection_type": body.inspection_type,
    })

    if body.inspection_type in FLIGHT_LEVEL_TYPES:
        if body.field_scores is None:
            return {"inserted": 0}
        total, pct = _compute_total_percent(body.inspection_type, body.field_scores)
        doc = {
            "id": str(uuid.uuid4()),
            "day": body.day,
            "flight": body.flight,
            "inspection_type": body.inspection_type,
            "cadet_participant_id": None,
            "cadet_name": "",
            "field_scores": body.field_scores,
            "total": total,
            "percent": pct,
            "absent": False,
            "created_at": now,
            "updated_at": now,
            "recorded_by": recorder,
        }
        await db.inspection_scores.insert_one(doc)
        return {"inserted": 1, "percent": pct, "total": total}

    # Per-cadet
    rows = body.cadet_scores or []
    docs = []
    for row in rows:
        if row.absent:
            total, pct = 0.0, None  # absent → percent None so it's excluded from avg
        else:
            total, pct = _compute_total_percent(body.inspection_type, row.field_scores or {})
        docs.append({
            "id": str(uuid.uuid4()),
            "day": body.day,
            "flight": body.flight,
            "inspection_type": body.inspection_type,
            "cadet_participant_id": row.cadet_participant_id,
            "cadet_name": row.cadet_name,
            "field_scores": row.field_scores or {},
            "total": total,
            "percent": pct,
            "absent": bool(row.absent),
            "created_at": now,
            "updated_at": now,
            "recorded_by": recorder,
        })
    if docs:
        await db.inspection_scores.insert_many(docs)
    return {"inserted": len(docs)}


@api_router.delete("/inspections/scores")
async def delete_scores(
    day: int, flight: str, inspection_type: str,
    user: dict = Depends(require_inspection_role),
):
    _validate_day(day); _validate_flight(flight); _validate_inspection_type(inspection_type)
    res = await db.inspection_scores.delete_many({
        "day": day, "flight": flight, "inspection_type": inspection_type,
    })
    return {"deleted": res.deleted_count}


# ── Merit points (per day/flight) ────────────────────────────────────
@api_router.put("/inspections/merit-points")
async def set_merit_points(
    body: dict,
    user: dict = Depends(require_inspection_role),
):
    day = int(body.get("day", 0))
    flight = str(body.get("flight", "")).lower()
    pts = float(body.get("points", 0))
    _validate_day(day); _validate_flight(flight)
    now = datetime.now(timezone.utc).isoformat()
    await db.flight_merit_points.replace_one(
        {"day": day, "flight": flight},
        {"day": day, "flight": flight, "points": pts,
         "updated_at": now, "updated_by": user.get("id")},
        upsert=True,
    )
    return {"day": day, "flight": flight, "points": pts}


@api_router.get("/inspections/merit-points")
async def list_merit_points(user: dict = Depends(require_inspection_role)):
    cur = db.flight_merit_points.find({}, {"_id": 0})
    return await cur.to_list(1000)


# ── Dashboard / TOTALS aggregation ───────────────────────────────────
@api_router.get("/inspections/dashboard")
async def dashboard(
    include_merit_points: Optional[bool] = None,
    user: dict = Depends(require_inspection_role),
):
    settings = await _get_settings()
    merit_on = (
        settings.get("include_merit_points", True)
        if include_merit_points is None else bool(include_merit_points)
    )

    # Per-day per-flight breakdown
    by_day: dict[int, list[dict]] = {}
    for day in DAYS:
        rows = []
        for flight in FLIGHTS:
            ctf = await _ctf_for_day_flight(day, flight, settings)
            if merit_on:
                merit = await _merit_points_for_day_flight(day, flight)
                ctf["merit_points"] = merit
                ctf["ctf_points"] = ctf["ctf_points"] + merit
            else:
                ctf["merit_points"] = 0.0
            rows.append(ctf)
        # CTS aggregation
        cts = []
        for sq, (a, b) in SQUADRON_FLIGHTS.items():
            ra = next(r for r in rows if r["flight"] == a)
            rb = next(r for r in rows if r["flight"] == b)
            cts.append({
                "squadron": sq,
                "cts_average": (ra["ctf_average"] + rb["ctf_average"]) / 2,
                "cts_points":  ra["ctf_points"] + rb["ctf_points"],
            })
        by_day[day] = {"flights": rows, "squadrons": cts}

    # Weekly point totals (per-flight, all days summed) + per-day matrix
    weekly_totals = {f: 0.0 for f in FLIGHTS}
    per_day_points: dict[int, dict[str, float]] = {}
    for day in DAYS:
        per_day_points[day] = {}
        for r in by_day[day]["flights"]:
            per_day_points[day][r["flight"]] = r["ctf_points"]
            weekly_totals[r["flight"]] += r["ctf_points"]

    # Weekly point change (Day 1 baseline = 0)
    weekly_change: dict[int, dict[str, float]] = {}
    for day in DAYS:
        weekly_change[day] = {}
        if day == 1:
            for f in FLIGHTS:
                weekly_change[day][f] = 0.0
            continue
        for f in FLIGHTS:
            curr = per_day_points[day].get(f, 0.0)
            prev = per_day_points[day - 1].get(f, 0.0)
            weekly_change[day][f] = curr - prev

    return {
        "settings": settings,
        "include_merit_points": merit_on,
        "by_day": by_day,
        "per_day_points": per_day_points,
        "weekly_totals": weekly_totals,
        "weekly_change": weekly_change,
    }


@api_router.get("/inspections/types")
async def list_inspection_types(user: dict = Depends(require_inspection_role)):
    """Return the canonical inspection-type metadata (field lists, max totals).

    Front-end uses this to render the score-entry grids without
    hard-coding the field lists.
    """
    return {
        "types": INSPECTION_TYPES,
        "per_cadet_types": sorted(PER_CADET_TYPES),
        "flight_level_types": sorted(FLIGHT_LEVEL_TYPES),
        "fields": INSPECTION_FIELDS,
        "max_total": INSPECTION_MAX_TOTAL,
        "flights": list(FLIGHTS),
        "days": list(DAYS),
        "flight_to_squadron": FLIGHT_TO_SQUADRON,
        "squadron_flights": {k: list(v) for k, v in SQUADRON_FLIGHTS.items()},
        "default_weights": DEFAULT_WEIGHTS,
    }


# ── Per-student inspection data (for participant profile) ────────────
@api_router.get("/inspections/student/{participant_id}")
async def student_inspection_summary(
    participant_id: str,
    user: dict = Depends(require_inspection_role),
):
    """Inspection data for one cadet — used on the participant profile.

    Returns a per-day, per-type breakdown of the cadet's own scores plus
    a summary (total score across all inspections, % correct average).
    Flight-level inspections (drill/sports) aren't tied to individual
    cadets so they aren't included here.
    """
    cur = db.inspection_scores.find(
        {"cadet_participant_id": participant_id},
        {"_id": 0},
    )
    rows = await cur.to_list(500)
    if not rows:
        return {
            "participant_id": participant_id,
            "scores": [],
            "summary": {"avg_percent": None, "total_points": 0, "inspections_taken": 0},
        }
    present = [r for r in rows if not r.get("absent")
               and any(isinstance(v, (int, float)) for v in (r.get("field_scores") or {}).values())]
    avg_pct = (
        sum(r["percent"] for r in present if isinstance(r.get("percent"), (int, float)))
        / len(present)
    ) if present else None
    total_pts = sum(float(r.get("total") or 0) for r in present)
    return {
        "participant_id": participant_id,
        "scores": sorted(rows, key=lambda r: (r.get("day", 0), r.get("inspection_type", ""))),
        "summary": {
            "avg_percent": avg_pct,
            "total_points": total_pts,
            "inspections_taken": len(present),
        },
    }
