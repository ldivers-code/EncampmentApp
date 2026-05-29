"""Unit tests for the grid-format Google Sheets schedule parser.

These tests run pure-Python (no DB / no HTTP) against the helpers in
`routes.google_sheets` so they're cheap to run in CI.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from routes.google_sheets import (
    _detect_grid_header,
    _parse_grid_header,
    _extract_grid_date,
    _extract_footer_year,
    _grid_rows_to_events,
    _classify_grid_header_cell,
)


# ── Header detection ────────────────────────────────────────────────

def test_detect_grid_header_cast_layout():
    rows = [
        ["Friday | Day 1 CADRE Arrival | May 29th", "", ""],
        ["", "", "Training Cadre"],
        ["START", "END", "6th CTS", "21st CTS", "22nd CTS", "16th CTS",
         "START", "END", "Notes"],
        ["0600", "0615", "", "", "", "", "0600", "0615", ""],
    ]
    assert _detect_grid_header(rows) == 2


def test_detect_grid_header_returns_none_for_flat_table():
    rows = [
        ["Date", "Start Time", "End Time", "Title"],
        ["2026-06-17", "09:00", "10:00", "Drill"],
    ]
    assert _detect_grid_header(rows) is None


def test_classify_grid_header_cell():
    assert _classify_grid_header_cell("START") == ("start", "")
    assert _classify_grid_header_cell("end") == ("end", "")
    assert _classify_grid_header_cell("Notes") == ("notes", "")
    assert _classify_grid_header_cell("6th CTS") == ("group", "6th_cts")
    assert _classify_grid_header_cell("21st CTS") == ("group", "21st_cts")
    assert _classify_grid_header_cell("Alpha") == ("group", "alpha")
    assert _classify_grid_header_cell("Bravo Flight") == ("group", "bravo")
    assert _classify_grid_header_cell("Whatever") is None
    assert _classify_grid_header_cell("") is None


# ── Block parsing ───────────────────────────────────────────────────

def test_parse_grid_header_two_blocks():
    header = ["START", "END", "6th CTS", "21st CTS", "22nd CTS", "16th CTS",
              "START", "END", "Notes"]
    blocks = _parse_grid_header(header)
    assert len(blocks) == 2

    b0 = blocks[0]
    assert b0["start_col"] == 0
    assert b0["end_col"] == 1
    assert [g["label"] for g in b0["group_cols"]] == [
        "6th_cts", "21st_cts", "22nd_cts", "16th_cts"
    ]

    b1 = blocks[1]
    assert b1["start_col"] == 6
    assert b1["end_col"] == 7
    assert b1["group_cols"] == []
    assert b1["notes_col"] == 8


# ── Date extraction ─────────────────────────────────────────────────

def test_extract_grid_date_with_month_day_ordinal():
    assert _extract_grid_date(
        "Friday | Day 1 CADRE Arrival | May 29th", 2026
    ) == "2026-05-29"


def test_extract_grid_date_with_year_in_title():
    assert _extract_grid_date(
        "Monday June 17 2024", None
    ) == "2024-06-17"


def test_extract_grid_date_returns_none_when_no_month():
    assert _extract_grid_date("Day 1", 2026) is None


def test_extract_footer_year_from_last_updated_row():
    rows = [
        ["something"],
        ["LAST UPDATED: 05/09/2026", "", ""],
    ]
    assert _extract_footer_year(rows) == 2026


# ── Event emission ──────────────────────────────────────────────────

def _mk_header_rows():
    return [
        ["Sunday | Day 2 | June 1st", "", "", "", "", "", "", "", ""],
        ["", "", "Training Cadre", "", "", "Support", "", "", ""],
        ["START", "END", "6th CTS", "21st CTS", "22nd CTS", "16th CTS",
         "START", "END", "Notes"],
    ]


def test_grid_emits_merged_event_when_only_first_col_filled():
    rows = _mk_header_rows() + [
        ["0900", "0915", "Opening Ceremony", "", "", "",
         "0900", "0915", "All hands"],
    ]
    header_idx = _detect_grid_header(rows)
    blocks = _parse_grid_header(rows[header_idx])
    events, skipped = _grid_rows_to_events(rows, header_idx, blocks,
                                           "2026-06-01")
    assert len(events) == 1
    ev = events[0]
    assert ev["title"] == "Opening Ceremony"
    assert ev["start_time"] == "09:00"
    assert ev["end_time"] == "09:15"
    assert ev["target_groups"] == [
        "6th_cts", "21st_cts", "22nd_cts", "16th_cts"
    ]
    assert ev["description"] == "All hands"


def test_grid_emits_per_squadron_events_when_cells_differ():
    rows = _mk_header_rows() + [
        ["1000", "1100", "Drill A", "Drill B", "Drill C", "Drill D",
         "1000", "1100", ""],
    ]
    header_idx = _detect_grid_header(rows)
    blocks = _parse_grid_header(rows[header_idx])
    events, _ = _grid_rows_to_events(rows, header_idx, blocks, "2026-06-01")
    assert len(events) == 4
    titles = {e["title"]: e["target_groups"] for e in events}
    assert titles == {
        "Drill A": ["6th_cts"],
        "Drill B": ["21st_cts"],
        "Drill C": ["22nd_cts"],
        "Drill D": ["16th_cts"],
    }


def test_grid_merges_contiguous_rows_with_same_title():
    """Vertically merged cells in the source sheet appear as a single value
    in the first row only — the parser should extend the end_time."""
    rows = _mk_header_rows() + [
        ["0800", "0815", "PT", "", "", "", "0800", "0815", ""],
        ["0815", "0830", "",   "", "", "", "0815", "0830", ""],
        ["0830", "0845", "",   "", "", "", "0830", "0845", ""],
        ["0845", "0900", "Chow","", "", "", "0845", "0900", ""],
    ]
    header_idx = _detect_grid_header(rows)
    blocks = _parse_grid_header(rows[header_idx])
    events, _ = _grid_rows_to_events(rows, header_idx, blocks, "2026-06-01")
    assert len(events) == 2
    pt, chow = sorted(events, key=lambda e: e["start_time"])
    assert pt["title"] == "PT"
    assert pt["start_time"] == "08:00"
    assert pt["end_time"] == "08:45"   # extended across three empty slots
    assert chow["title"] == "Chow"
    assert chow["start_time"] == "08:45"
    assert chow["end_time"] == "09:00"


def test_grid_stops_at_footer_row():
    rows = _mk_header_rows() + [
        ["0900", "0915", "Activity", "", "", "", "0900", "0915", ""],
        ["LAST UPDATED: 05/09/2026", "", "", "", "", "", "", "", ""],
        ["1000", "1015", "Should not appear", "", "", "", "", "", ""],
    ]
    header_idx = _detect_grid_header(rows)
    blocks = _parse_grid_header(rows[header_idx])
    events, _ = _grid_rows_to_events(rows, header_idx, blocks, "2026-06-01")
    assert len(events) == 1
    assert events[0]["title"] == "Activity"
