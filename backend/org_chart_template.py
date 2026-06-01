"""Canonical Org Chart position template (Feb 2026 — restructured).

This module is the **single source of truth** for the encampment org-chart
position hierarchy + per-position metadata. The seed script builds Mongo
nodes from this template, and the live `auto_sync_org_chart` logic in
`routes/users.py` looks up the right position id when a cadre user role
changes.

Notes on the Feb 2026 changes:
  * Public Affairs is now under the Deputy Commander for Support (DCS)
    branch — NOT under Chief Cadet Enlisted Advisor.
  * Squadron-level enlisted-leads keep the "First Sergeant" title
    (not "Squadron Superintendent").
  * Each position carries: `position_code`, `single_occupant`,
    `job_description`, `allowed_participant_types`, `secondary_reports_to`.
"""
from __future__ import annotations

from typing import Optional

# ── Branch / category slugs ──────────────────────────────────────────
CAT_STAFF = "staff"         # Emerald Green — Executive Cadre, Staff, Support
CAT_6TH = "6th_cts"         # Blue
CAT_21ST = "21st_cts"       # Yellow / Ginger
CAT_22ND = "22nd_cts"       # Maroon
CAT_CADET_SUPPORT = "cadet_support"  # Silver
CAT_SUPPORT = "support"     # Adult Senior Staff / Support — uses staff palette
# All allowed categories — used by validation in the orgchart route.
ALLOWED_CATEGORIES = {CAT_STAFF, CAT_6TH, CAT_21ST, CAT_22ND,
                      CAT_CADET_SUPPORT, CAT_SUPPORT}


# ── Allowed participant types per position ───────────────────────────
# Used to validate role assignments — e.g. you can't put a cadet under
# the "Encampment Commander" position which is senior_staff-only.
PT_SENIOR_STAFF = "senior_staff"
PT_CADET_CADRE = "cadre"
PT_SUPPORT_CADRE = "support_cadre"
PT_ANY = "any"


def _p(
    role_id: str,
    title: str,
    parent: Optional[str],
    cat: str,
    order: int,
    *,
    position_code: str = "",
    single_occupant: bool = True,
    allowed_types: tuple = (PT_ANY,),
    secondary_reports_to: Optional[str] = None,
    display_label: str = "",
    job_description: str = "",
) -> dict:
    """Build one canonical position record (template-only — no assignment).

    Records inserted into `db.org_chart_roles` carry the same fields plus
    runtime assignment data (`assigned_name`, `assigned_participant_id`,
    `updated_at`).
    """
    return {
        "role_id": role_id,
        "position_title": title,
        "reports_to": parent,
        "secondary_reports_to": secondary_reports_to,
        "role_category": cat,
        "order": order,
        "position_code": position_code,
        "single_occupant": single_occupant,
        "allowed_participant_types": list(allowed_types),
        "display_label": display_label,
        "job_description": job_description,
    }


# ── The hierarchy ────────────────────────────────────────────────────

def build_position_template() -> list[dict]:
    """Return the full position template as a list of dicts."""
    pos: list[dict] = []

    # Level 0 — Encampment Commander
    pos.append(_p("enc-commander", "Encampment Commander", None, CAT_STAFF, 1,
                  position_code="ENC/CC", single_occupant=True,
                  allowed_types=(PT_SENIOR_STAFF,),
                  job_description=(
                      "Overall command of the encampment. Responsible for "
                      "mission accomplishment, cadet safety, training "
                      "quality, and good order/discipline."
                  )))

    # Level 1 — Direct reports to the Encampment Commander
    pos.append(_p("commandant", "Commandant of Cadets", "enc-commander",
                  CAT_STAFF, 1, position_code="ENC/CW",
                  allowed_types=(PT_SENIOR_STAFF,),
                  job_description=(
                      "Primary advisor to the Encampment Commander on cadet "
                      "training and discipline. Supervises the Cadet "
                      "Training Group Commander."
                  )))
    pos.append(_p("dcs", "Deputy Commander for Support", "enc-commander",
                  CAT_STAFF, 2, position_code="ENC/SD", display_label="DCS",
                  allowed_types=(PT_SENIOR_STAFF,),
                  job_description=(
                      "Leads all adult support functions — Plans & Programs, "
                      "Logistics, Public Affairs, Communications, Finance, "
                      "and Health/WORD."
                  )))
    pos.append(_p("sm-superintendent", "SM Superintendent", "enc-commander",
                  CAT_STAFF, 3, position_code="ENC/CCS",
                  allowed_types=(PT_SENIOR_STAFF,),
                  job_description=(
                      "Senior enlisted advisor to the Encampment Commander. "
                      "Mentors all senior NCOs assigned to the encampment."
                  )))
    pos.append(_p("chaplains", "Chaplain(s)", "enc-commander", CAT_STAFF, 4,
                  position_code="ENC/HC", single_occupant=False,
                  allowed_types=(PT_SENIOR_STAFF,)))
    pos.append(_p("safety", "Safety", "enc-commander", CAT_STAFF, 5,
                  position_code="ENC/SE", single_occupant=False,
                  allowed_types=(PT_SENIOR_STAFF,)))

    # Level 2 — Under Commandant
    pos.append(_p("ctg-cc", "Cadet Training Group Commander", "commandant",
                  CAT_STAFF, 1, position_code="CTG/CC",
                  allowed_types=(PT_CADET_CADRE,),
                  job_description=(
                      "Commands all cadet training squadrons. Reports to the "
                      "Commandant of Cadets."
                  )))

    # Level 3 — Under CTG/CC
    pos.append(_p("ctg-cd", "Operations", "ctg-cc", CAT_STAFF, 1,
                  position_code="CTG/CD",
                  allowed_types=(PT_CADET_CADRE,)))
    pos.append(_p("ctg-df", "Academics", "ctg-cc", CAT_STAFF, 2,
                  position_code="CTG/DF",
                  allowed_types=(PT_CADET_CADRE,)))
    pos.append(_p("ctg-ccea", "Chief Cadet Enlisted Advisor", "ctg-cc",
                  CAT_STAFF, 3, position_code="CTG/CCEA",
                  allowed_types=(PT_CADET_CADRE,)))
    pos.append(_p("css-cc", "Cadet Support Squadron Commander", "ctg-cc",
                  CAT_CADET_SUPPORT, 4, position_code="CSS/CC",
                  secondary_reports_to="ctg-df",
                  allowed_types=(PT_CADET_CADRE,)))
    pos.append(_p("chief-training-officer", "Chief Training Officer", "ctg-cc",
                  CAT_STAFF, 5, position_code="CTO",
                  allowed_types=(PT_SENIOR_STAFF,)))
    # Squadron commanders
    pos.append(_p("6th-sq-cmdr", "6th CTS Commander", "ctg-cc", CAT_6TH, 6,
                  position_code="6th CTS/CC", display_label="6th CTS",
                  secondary_reports_to="ctg-df",
                  allowed_types=(PT_CADET_CADRE,)))
    pos.append(_p("21st-sq-cmdr", "21st CTS Commander", "ctg-cc", CAT_21ST, 7,
                  position_code="21st CTS/CC", display_label="21st CTS",
                  secondary_reports_to="ctg-df",
                  allowed_types=(PT_CADET_CADRE,)))
    pos.append(_p("22nd-sq-cmdr", "22nd CTS Commander", "ctg-cc", CAT_22ND, 8,
                  position_code="22nd CTS/CC", display_label="22nd CTS",
                  secondary_reports_to="ctg-df",
                  allowed_types=(PT_CADET_CADRE,)))

    # Dining Facility — stays under CTG/CCEA (enlisted department).
    pos.append(_p("dining-facility-dept", "Dining Facility", "ctg-ccea",
                  CAT_STAFF, 1, single_occupant=False,
                  allowed_types=(PT_CADET_CADRE,)))
    for i, t in enumerate([
        ("df-oic", "OIC"),
        ("df-aoic", "AOIC"),
        ("df-member-1", "Cadre"),
        ("df-member-2", "Cadre"),
        ("df-member-3", "Cadre"),
        ("df-member-4", "Cadre"),
    ]):
        pos.append(_p(t[0], t[1], "dining-facility-dept", CAT_STAFF, i + 1,
                      single_occupant=(t[0] in {"df-oic", "df-aoic"}),
                      allowed_types=(PT_CADET_CADRE,)))

    # Under CSS/CC — Cadet Support Squadron
    for i, t in enumerate([
        ("css-to", "OSS Training Officer"),
        ("css-1sgt", "First Sergeant"),
        ("css-logistics", "Logistics"),
        ("css-comms", "Communications"),
        ("css-dining", "Dining Facility"),
        ("css-word", "WORD"),
    ]):
        pos.append(_p(t[0], t[1], "css-cc", CAT_CADET_SUPPORT, i + 1,
                      single_occupant=False,
                      allowed_types=(PT_CADET_CADRE, PT_SUPPORT_CADRE)))

    # Under CTO
    pos.append(_p("6th-sq-to", "Squadron Training Officer - 6th CTS",
                  "chief-training-officer", CAT_6TH, 1,
                  display_label="6th CTS",
                  allowed_types=(PT_SENIOR_STAFF,)))
    pos.append(_p("21st-sq-to", "Squadron Training Officer - 21st CTS",
                  "chief-training-officer", CAT_21ST, 2,
                  display_label="21st CTS",
                  allowed_types=(PT_SENIOR_STAFF,)))
    pos.append(_p("22nd-sq-to", "Squadron Training Officer - 22nd CTS",
                  "chief-training-officer", CAT_22ND, 3,
                  display_label="22nd CTS",
                  allowed_types=(PT_SENIOR_STAFF,)))
    pos.append(_p("pp-cadet", "Plans & Programs", "chief-training-officer",
                  CAT_STAFF, 4, display_label="Cadet Level",
                  allowed_types=(PT_CADET_CADRE,)))
    pos.append(_p("media-publishing", "Media & Publishing",
                  "chief-training-officer", CAT_STAFF, 5,
                  single_occupant=False,
                  allowed_types=(PT_CADET_CADRE,)))

    # Under pp-cadet
    for i, t in enumerate([
        ("pp-cadet-oic", "OIC"),
        ("pp-cadet-aoic", "AOIC"),
        ("pp-cadet-coic", "C/OIC"),
        ("pp-cadet-caoic", "C/AOIC"),
        ("pp-cadet-member-1", "Cadre"),
        ("pp-cadet-member-2", "Cadre"),
    ]):
        pos.append(_p(t[0], t[1], "pp-cadet", CAT_STAFF, i + 1,
                      single_occupant=("oic" in t[0]),
                      allowed_types=(PT_CADET_CADRE, PT_SENIOR_STAFF)))
    pos.append(_p("media-member-1", "Cadre", "media-publishing", CAT_STAFF, 1,
                  single_occupant=False,
                  allowed_types=(PT_CADET_CADRE,)))

    # ── DCS branch (Feb 2026: Public Affairs lives here) ──────────────
    pos.append(_p("xp-plans", "Plans & Programs", "dcs", CAT_SUPPORT, 1,
                  position_code="XP", single_occupant=False,
                  allowed_types=(PT_SENIOR_STAFF,)))
    pos.append(_p("lg-logistics", "Logistics", "dcs", CAT_SUPPORT, 2,
                  position_code="LG", single_occupant=False,
                  allowed_types=(PT_SENIOR_STAFF,)))
    # PUBLIC AFFAIRS — Feb 2026: moved out of CTG/CCEA into the DCS support chain.
    pos.append(_p("public-affairs-dept", "Public Affairs", "dcs",
                  CAT_SUPPORT, 3, position_code="ENC/PA",
                  single_occupant=False,
                  allowed_types=(PT_SENIOR_STAFF, PT_SUPPORT_CADRE),
                  job_description=(
                      "Manages all external communications, photography, "
                      "press releases, and social media for the encampment. "
                      "Reports to the Deputy Commander for Support."
                  )))
    pos.append(_p("comm", "Communications", "dcs", CAT_SUPPORT, 4,
                  position_code="Comm", single_occupant=False,
                  allowed_types=(PT_SENIOR_STAFF,)))
    pos.append(_p("finance", "Finance", "dcs", CAT_SUPPORT, 5,
                  position_code="FIN", single_occupant=False,
                  allowed_types=(PT_SENIOR_STAFF,)))
    pos.append(_p("health-word", "Health Services / WORD", "dcs",
                  CAT_SUPPORT, 6, single_occupant=False,
                  position_code="HS",
                  allowed_types=(PT_SENIOR_STAFF,)))

    # Members under DCS departments
    for parent_id, members in [
        ("xp-plans",        [("xp-oic", "OIC"), ("xp-aoic", "AOIC")]),
        ("lg-logistics",    [("lg-oic", "OIC"), ("lg-aoic", "AOIC"),
                             ("lg-member-1", "Cadre"), ("lg-member-2", "Cadre"),
                             ("lg-member-3", "Cadre")]),
        ("public-affairs-dept", [
                             ("pa-oic", "OIC"), ("pa-aoic", "AOIC"),
                             ("pa-member-1", "Cadre"), ("pa-member-2", "Cadre"),
                             ("pa-member-3", "Cadre"), ("pa-member-4", "Cadre")]),
        ("comm",            [("comm-oic", "OIC")]),
        ("finance",         [("finance-oic", "OIC")]),
        ("health-word",     [("hs-oic", "OIC"), ("hs-ncoic", "NCOIC"),
                             ("hs-member-1", "Cadre")]),
    ]:
        for i, (mid, mtitle) in enumerate(members):
            parent_pos = next(p for p in pos if p["role_id"] == parent_id)
            pos.append(_p(mid, mtitle, parent_id, parent_pos["role_category"], i + 1,
                          single_occupant=mid.endswith("-oic") or mid.endswith("-aoic") or mid.endswith("-ncoic"),
                          allowed_types=(PT_SENIOR_STAFF, PT_SUPPORT_CADRE,
                                         PT_CADET_CADRE)))

    # ── Squadron sub-trees: 6th / 21st / 22nd CTS ────────────────────
    def _squadron(sq_id: str, cat: str, flights: tuple):
        # "Superintendent" rename — squadron enlisted lead is "First Sergeant".
        pos.append(_p(f"{sq_id}-1sgt", "First Sergeant", f"{sq_id}-cmdr",
                      cat, 1, secondary_reports_to="ctg-df",
                      allowed_types=(PT_CADET_CADRE,)))
        for i, flight_letter in enumerate(flights):
            cmd_id = f"{sq_id}-flt-{flight_letter.lower()}-cmdr"
            sgt_id = f"{sq_id}-flt-{flight_letter.lower()}-sgt"
            pos.append(_p(cmd_id, f"Flight Commander - {flight_letter}",
                          f"{sq_id}-cmdr", cat, i + 2,
                          secondary_reports_to="ctg-df",
                          allowed_types=(PT_CADET_CADRE,)))
            pos.append(_p(sgt_id, f"Flight Sergeant - {flight_letter}",
                          cmd_id, cat, 1, secondary_reports_to="ctg-df",
                          allowed_types=(PT_CADET_CADRE,)))

    _squadron("6th-sq", CAT_6TH, ("A", "B"))
    _squadron("21st-sq", CAT_21ST, ("C", "D"))
    _squadron("22nd-sq", CAT_22ND, ("E", "F"))

    return pos


# Build once at import — cheap & deterministic.
POSITION_TEMPLATE: list[dict] = build_position_template()
POSITION_BY_ID: dict[str, dict] = {p["role_id"]: p for p in POSITION_TEMPLATE}
