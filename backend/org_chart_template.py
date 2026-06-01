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
        # Flight role_ids drop the "-sq" infix to match the canonical
        # IDs referenced by tests + the live-sync mapper:
        #   `<prefix>-flt-<letter>-cmdr`   (e.g. 6th-flt-a-cmdr)
        sq_prefix = sq_id.replace("-sq", "")
        for i, flight_letter in enumerate(flights):
            cmd_id = f"{sq_prefix}-flt-{flight_letter.lower()}-cmdr"
            sgt_id = f"{sq_prefix}-flt-{flight_letter.lower()}-sgt"
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


# ── Initial assignments (used only on the very first seed; subsequent
# ── seeds preserve whatever assigned_name is already in the DB) ───────
INITIAL_ASSIGNMENTS: dict[str, str] = {
    "enc-commander":       "Maj Divers, L",
    "dcs":                 "Capt Belli, S",
    "sm-superintendent":   "TSgt Breslin, D",
    "ctg-cc":              "C/Lt Col Yoder, L",
    "ctg-cd":              "C/Lt Col Grammer, A",
    "ctg-df":              "C/Maj Doran, G",
    "ctg-ccea":            "C/CMSgt Railey, A",
    "css-cc":              "C/Capt. Posta, A",
    "6th-sq-cmdr":         "C/Capt Nhan, V",
    "21st-sq-cmdr":        "C/2nd Lt Nair, P",
    "22nd-sq-cmdr":        "C/1st Lt Breslin, D",
    "css-logistics":       "C/Capt Parker, T",
    "css-dining":          "C/1st Lt Jackson, J",
    "css-word":            "C/CMSgt Plummer, R",
    "6th-sq-to":           "Capt Brad Dozier",
    "21st-sq-to":          "Capt Renee Cyr",
    "22nd-sq-to":          "1st Lt Max Hammond",
    "lg-logistics":        "Capt Reed, A",
    "health-word":         "Lt Col Divers, K",
    "pp-cadet-oic":        "Lt Col Brian Hughes",
    "pp-cadet-aoic":       "Maj Randall Parker",
    "pp-cadet-coic":       "C/Maj. Stacey, R",
    "pp-cadet-caoic":      "C/Capt. Lawson, J",
    "pp-cadet-member-1":   "C/Maj. Phillips, L",
    "pp-cadet-member-2":   "C/Lt Col Santos, N",
    "media-member-1":      "C/TSgt Spurling, I",
    "xp-oic":              "Lt Col Brian Hughes",
    "xp-aoic":             "Maj Randall Parker",
    "lg-oic":              "C/Capt Parker, T",
    "lg-aoic":             "C/2nd Lt Langston, M",
    "lg-member-1":         "C/SrA Mudhireddy, V",
    "lg-member-2":         "C/2nd Lt Phillips, E",
    "lg-member-3":         "C/SMSgt Nichols, A",
    "comm-oic":            "1st Lt Reed, I",
    "finance-oic":         "1st Lt Reed, I",
    "hs-oic":              "C/CMSgt Plummer, R",
    "hs-ncoic":            "C/CMSgt Steele, L",
    "hs-member-1":         "C/SMSgt Nhan, D",
    "pa-oic":              "C/Lt Col Bartlett, E",
    "pa-aoic":             "C/2d Lt Boykin, N",
    "pa-member-1":         "C/SMSgt Tran, T",
    "pa-member-2":         "C/TSgt Zamudio, A",
    "pa-member-3":         "C/MSgt Plucker, J",
    "pa-member-4":         "C/2nd Lt Marfio, M",
    "df-oic":              "C/1st Lt Jackson, J",
    "df-aoic":             "C/1st Lt Ciampa, B",
    "df-member-1":         "C/SSgt Mulverhill, M",
    "df-member-2":         "C/CMSgt Kover, M",
    "df-member-3":         "C/SrA Sporin, L",
    "df-member-4":         "C/SSgt Flippen, M",
    "6th-sq-1sgt":         "C/SMSgt Thomasson, T",
    "6th-flt-a-cmdr":      "C/CMSgt Anand, R",
    "6th-flt-a-sgt":       "C/SSgt Mellott, P",
    "6th-flt-b-sgt":       "C/MSgt DeJesus, R",
    "21st-sq-1sgt":        "C/CMSgt Jackson, L",
    "21st-flt-c-cmdr":     "C/1st Lt Madera, G",
    "21st-flt-c-sgt":      "C/SMSgt Wilson, T",
    "21st-flt-d-cmdr":     "C/MSgt Calvez, T",
    "21st-flt-d-sgt":      "C/SrA Garcia, B",
    "22nd-sq-1sgt":        "C/SMSgt Wainman, A",
    "22nd-flt-e-cmdr":     "C/2nd Lt Rizzo, H",
    "22nd-flt-e-sgt":      "C/MSgt Ambelis, I",
    "22nd-flt-f-cmdr":     "C/2nd Lt Terbizan, S",
    "22nd-flt-f-sgt":      "C/MSgt Kyle, E",
}


# ── Live-sync mapping: figure out which canonical position a given user
# ── currently occupies, based on role + unit assignment fields. ────────

_FLIGHT_TO_SQ_PREFIX: dict[str, str] = {
    "alpha": "6th",   "bravo":   "6th",
    "charlie": "21st", "delta":  "21st",
    "echo": "22nd",    "foxtrot": "22nd",
}
_SQUADRON_TO_PREFIX: dict[str, str] = {
    "6th_cts": "6th", "21st_cts": "21st", "22nd_cts": "22nd",
}
_FLIGHT_LETTER: dict[str, str] = {
    "alpha": "a", "bravo": "b", "charlie": "c",
    "delta": "d", "echo": "e", "foxtrot": "f",
}
_SUPPORT_SECTION_TO_ROLE: dict[str, str] = {
    # css-* nodes live UNDER the cadet support squadron (CSS/CC)
    "logistics":      "css-logistics",
    "communications": "css-comms",
    "comms":          "css-comms",
    "dining":         "css-dining",
    "dining_facility": "css-dining",
    "health":         "css-word",
    "health_services": "css-word",
    "word":           "css-word",
    # public_affairs uses the DCS branch node
    "public_affairs": "public-affairs-dept",
    "pa":             "public-affairs-dept",
    "plans_programs": "xp-plans",
    "plans/programs": "xp-plans",
    "training":       "css-to",
    "finance":        "finance",
}
_SUPPORT_ROLE_TO_NODE: dict[str, str] = {
    "support_logistics": "css-logistics",
    "support_comms":     "css-comms",
    "support_pa":        "public-affairs-dept",
    "support_dining":    "css-dining",
    "support_health":    "css-word",
}


def find_role_id_for_user(user_data: dict) -> Optional[str]:
    """Return the canonical org_chart_template `role_id` this user currently
    occupies, or `None` if no mapping can be inferred.

    Resolution priority:
      1. Top-level roles that ARE positions in their own right
         (squadron_commander, training_officer, senior-staff roles,
         support_*) — these always win, regardless of any stale
         `cadre_position` field left over from a prior assignment.
      2. `cadre_position` combined with `flight` / `squadron` (only
         meaningful for `cadre` / `exec_cadre` role users).
      3. Fall-through senior-staff mapping for roles not covered above.
    """
    role = (user_data.get("role") or "").lower()
    flight = (user_data.get("flight") or "").lower()
    squadron = (user_data.get("squadron") or "").lower()
    cadre_position = (user_data.get("cadre_position") or "").lower()
    cadre_unit = (user_data.get("cadre_unit") or "").lower()
    support_section = (user_data.get("support_section") or "").lower()

    sq_prefix = _SQUADRON_TO_PREFIX.get(squadron) or _FLIGHT_TO_SQ_PREFIX.get(flight)
    flt_letter = _FLIGHT_LETTER.get(flight)

    # 1) Role-as-position (takes precedence over stale cadre_position)
    if role == "squadron_commander" and sq_prefix:
        return f"{sq_prefix}-sq-cmdr"
    if role == "training_officer" and sq_prefix:
        return f"{sq_prefix}-sq-to"

    if role in _SUPPORT_ROLE_TO_NODE:
        if support_section and support_section in _SUPPORT_SECTION_TO_ROLE:
            return _SUPPORT_SECTION_TO_ROLE[support_section]
        return _SUPPORT_ROLE_TO_NODE[role]

    senior_map = {
        "commander":              "enc-commander",
        "dcp":                    "dcs",
        "executive_staff":        "dcs",
        "superintendent":         "sm-superintendent",
        "chief_training_officer": "chief-training-officer",
        "logistics":              "lg-logistics",
        "finance":                "finance",
        "plans_programs":         "xp-plans",
        "health_services":        "health-word",
        "dining_facility":        "css-dining",
        "public_affairs":         "public-affairs-dept",
    }
    if role in senior_map:
        return senior_map[role]

    # 2) cadre_position-driven mapping (for cadre / exec_cadre users)
    if cadre_position == "flight_commander" and sq_prefix and flt_letter:
        return f"{sq_prefix}-flt-{flt_letter}-cmdr"
    if cadre_position == "flight_sergeant" and sq_prefix and flt_letter:
        return f"{sq_prefix}-flt-{flt_letter}-sgt"
    if cadre_position == "cadet_first_sergeant" and sq_prefix:
        return f"{sq_prefix}-sq-1sgt"
    if cadre_position == "cadet_squadron_commander" and sq_prefix:
        return f"{sq_prefix}-sq-cmdr"
    if cadre_position == "squadron_training_officer" and sq_prefix:
        return f"{sq_prefix}-sq-to"
    if cadre_position == "commandant_of_cadets":
        return "commandant"
    if cadre_position == "chief_training_officer":
        return "chief-training-officer"
    if cadre_position == "group_commander":
        return "ctg-cc"
    if cadre_position == "group_deputy_commander":
        return "ctg-cd"
    if cadre_position == "group_superintendent":
        return "ctg-ccea"
    if cadre_position == "cadet_dean_academics":
        return "ctg-df"

    # 3) cadre_unit hint (last-resort)
    if cadre_unit == "group" and role == "exec_cadre":
        return "ctg-ccea"

    return None
