"""
Strict 1:1 Org Chart Seed — TNWG ENC26 restructured hierarchy.
Colors by unit: Blue (6th CTS), Maroon (22nd CTS), Yellow (21st CTS),
Emerald Green (Staff/Executive/Support), Silver (Cadet Support).
"""
import asyncio
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

NOW = datetime.now(timezone.utc).isoformat()


def n(role_id, title, name, parent, cat, order, label="", secondary=None):
    return {
        "id": role_id,
        "role_id": role_id,
        "position_title": title,
        "assigned_name": name.strip() if name else "",
        "reports_to": parent,
        "secondary_reports_to": secondary,
        "role_category": cat,
        "order": order,
        "display_label": label,
        "job_description": "",
        "responsible_for": "",
        "supervises": "",
        "created_at": NOW,
        "updated_at": NOW,
    }


STF = "staff"            # Emerald Green — Executive Cadre, Staff, Support
S6  = "6th_cts"          # Blue
S21 = "21st_cts"         # Yellow / Ginger
S22 = "22nd_cts"         # Maroon
CSS = "cadet_support"    # Silver


def build_orgchart():
    nodes = []

    # ═══════════════════════════════════════════════
    # LEVEL 0 — ENCAMPMENT COMMANDER
    # ═══════════════════════════════════════════════
    nodes.append(n("enc-commander", "Encampment Commander", "Maj Divers, L", None, STF, 1))

    # ═══════════════════════════════════════════════
    # LEVEL 1 — DIRECT REPORTS
    # ═══════════════════════════════════════════════
    nodes.append(n("commandant", "Commandant of Cadets", "", "enc-commander", STF, 1))
    nodes.append(n("dcs", "Deputy Commander for Support", "Capt Belli, S", "enc-commander", STF, 2, "DCS"))
    nodes.append(n("sm-superintendent", "SM Superintendent", "TSgt Breslin, D", "enc-commander", STF, 3))
    nodes.append(n("chaplains", "Chaplain(s)", "", "enc-commander", STF, 4))
    nodes.append(n("safety", "Safety", "", "enc-commander", STF, 5))

    # ═══════════════════════════════════════════════
    # LEVEL 2 — UNDER COMMANDANT
    # ═══════════════════════════════════════════════
    nodes.append(n("ctg-cc", "Cadet Training Group Commander", "C/Lt Col Yoder, L", "commandant", STF, 1, "CTG/CC"))

    # ═══════════════════════════════════════════════
    # LEVEL 3 — UNDER CTG/CC
    # ═══════════════════════════════════════════════
    nodes.append(n("ctg-cd", "Operations", "C/Lt Col Grammer, A", "ctg-cc", STF, 1, "CTG/CD"))
    nodes.append(n("ctg-df", "Academics", "C/Maj Doran, G", "ctg-cc", STF, 2, "CTG/DF"))
    nodes.append(n("ctg-ccea", "Chief Cadet Enlisted Advisor", "C/CMSgt Railey, A", "ctg-cc", STF, 3, "CTG/CCEA"))
    nodes.append(n("css-cc", "Cadet Support Squadron Commander", "C/Capt. Posta, A", "ctg-cc", CSS, 4, "CSS/CC", secondary="ctg-df"))
    nodes.append(n("chief-training-officer", "Chief Training Officer", "", "ctg-cc", STF, 5, "CTO"))
    # Squadron Commanders — colored by their squadron
    nodes.append(n("6th-sq-cmdr", "6th CTS Commander", "C/Capt Nhan, V", "ctg-cc", S6, 6, "6th CTS", secondary="ctg-df"))
    nodes.append(n("21st-sq-cmdr", "21st CTS Commander", "C/2nd Lt Nair, P", "ctg-cc", S21, 7, "21st CTS", secondary="ctg-df"))
    nodes.append(n("22nd-sq-cmdr", "22nd CTS Commander", "C/1st Lt Breslin, D", "ctg-cc", S22, 8, "22nd CTS", secondary="ctg-df"))

    # ═══════════════════════════════════════════════
    # UNDER CTG/CCEA — Enlisted departments
    # ═══════════════════════════════════════════════
    nodes.append(n("public-affairs-dept", "Public Affairs", "", "ctg-ccea", STF, 1))
    nodes.append(n("dining-facility-dept", "Dining Facility", "", "ctg-ccea", STF, 2))

    nodes.append(n("pa-oic", "OIC", "C/Lt Col Bartlett, E", "public-affairs-dept", STF, 1))
    nodes.append(n("pa-aoic", "AOIC", "C/2d Lt Boykin, N", "public-affairs-dept", STF, 2))
    nodes.append(n("pa-member-1", "Cadre", "C/SMSgt Tran, T", "public-affairs-dept", STF, 3))
    nodes.append(n("pa-member-2", "Cadre", "C/TSgt Zamudio, A", "public-affairs-dept", STF, 4))
    nodes.append(n("pa-member-3", "Cadre", "C/MSgt Plucker, J", "public-affairs-dept", STF, 5))
    nodes.append(n("pa-member-4", "Cadre", "C/2nd Lt Marfio, M", "public-affairs-dept", STF, 6))

    nodes.append(n("df-oic", "OIC", "C/1st Lt Jackson, J", "dining-facility-dept", STF, 1))
    nodes.append(n("df-aoic", "AOIC", "C/1st Lt Ciampa, B", "dining-facility-dept", STF, 2))
    nodes.append(n("df-member-1", "Cadre", "C/SSgt Mulverhill, M", "dining-facility-dept", STF, 3))
    nodes.append(n("df-member-2", "Cadre", "C/CMSgt Kover, M", "dining-facility-dept", STF, 4))
    nodes.append(n("df-member-3", "Cadre", "C/SrA Sporin, L", "dining-facility-dept", STF, 5))
    nodes.append(n("df-member-4", "Cadre", "C/SSgt Flippen, M", "dining-facility-dept", STF, 6))

    # ═══════════════════════════════════════════════
    # UNDER CSS/CC — Cadet Support Squadron
    # ═══════════════════════════════════════════════
    nodes.append(n("css-to", "OSS Training Officer", "", "css-cc", CSS, 1))
    nodes.append(n("css-1sgt", "First Sergeant", "", "css-cc", CSS, 2))
    nodes.append(n("css-logistics", "Logistics", "C/Capt Parker, T", "css-cc", CSS, 3))
    nodes.append(n("css-pa", "Public Affairs", "C/Lt Col Bartlett, E", "css-cc", CSS, 4))
    nodes.append(n("css-comms", "Communications", "", "css-cc", CSS, 5))
    nodes.append(n("css-dining", "Dining Facility", "C/1st Lt Jackson, J", "css-cc", CSS, 6))
    nodes.append(n("css-word", "WORD", "C/CMSgt Plummer, R", "css-cc", CSS, 7))

    # ═══════════════════════════════════════════════
    # UNDER CTO — Chief Training Officer
    # Squadron TOs colored by their squadron
    # ═══════════════════════════════════════════════
    nodes.append(n("6th-sq-to", "Squadron Training Officer - 6th CTS", "Capt Brad Dozier", "chief-training-officer", S6, 1, "6th CTS"))
    nodes.append(n("21st-sq-to", "Squadron Training Officer - 21st CTS", "Capt Renee Cyr", "chief-training-officer", S21, 2, "21st CTS"))
    nodes.append(n("22nd-sq-to", "Squadron Training Officer - 22nd CTS", "1st Lt Max Hammond", "chief-training-officer", S22, 3, "22nd CTS"))
    nodes.append(n("pp-cadet", "Plans & Programs", "", "chief-training-officer", STF, 4, "Cadet Level"))
    nodes.append(n("media-publishing", "Media & Publishing", "", "chief-training-officer", STF, 5))
    nodes.append(n("cto-sm", "SM", "C/Capt Plucker, D", "chief-training-officer", STF, 6))
    nodes.append(n("cto-cadets-1", "Cadets", "C/SMSgt Breslin, T", "chief-training-officer", STF, 7))
    nodes.append(n("cto-cadets-2", "Cadets", "C/SrA Gould, J", "chief-training-officer", STF, 8))
    nodes.append(n("cto-cadets-3", "Cadets", "C/SrA Cranford, N", "chief-training-officer", STF, 9))
    nodes.append(n("cto-cadets-4", "Cadets", "C/CMSgt Mueller, L", "chief-training-officer", STF, 10))

    nodes.append(n("pp-cadet-oic", "OIC", "Lt Col Brian Hughes", "pp-cadet", STF, 1))
    nodes.append(n("pp-cadet-aoic", "AOIC", "Maj Randall Parker", "pp-cadet", STF, 2))
    nodes.append(n("pp-cadet-coic", "C/OIC", "C/Maj. Stacey, R", "pp-cadet", STF, 3))
    nodes.append(n("pp-cadet-caoic", "C/AOIC", "C/Capt. Lawson, J", "pp-cadet", STF, 4))
    nodes.append(n("pp-cadet-member-1", "Cadre", "C/Maj. Phillips, L", "pp-cadet", STF, 5))
    nodes.append(n("pp-cadet-member-2", "Cadre", "C/Lt Col Santos, N", "pp-cadet", STF, 6))
    nodes.append(n("media-member-1", "Cadre", "C/TSgt Spurling, I", "media-publishing", STF, 1))

    # ═══════════════════════════════════════════════
    # UNDER DCS — Support departments
    # ═══════════════════════════════════════════════
    nodes.append(n("xp-plans", "Plans & Programs", "", "dcs", STF, 1, "XP"))
    nodes.append(n("lg-logistics", "Logistics", "Capt Reed, A", "dcs", STF, 2, "LG"))
    nodes.append(n("comm", "Communications", "", "dcs", STF, 3, "Comm"))
    nodes.append(n("finance", "Finance", "", "dcs", STF, 4))
    nodes.append(n("health-word", "Health Services / WORD", "Lt Col Divers, K", "dcs", STF, 5))

    nodes.append(n("xp-oic", "OIC", "Lt Col Brian Hughes", "xp-plans", STF, 1))
    nodes.append(n("xp-aoic", "AOIC", "Maj Randall Parker", "xp-plans", STF, 2))
    nodes.append(n("lg-oic", "OIC", "C/Capt Parker, T", "lg-logistics", STF, 1))
    nodes.append(n("lg-aoic", "AOIC", "C/2nd Lt Langston, M", "lg-logistics", STF, 2))
    nodes.append(n("lg-member-1", "Cadre", "C/SrA Mudhireddy, V", "lg-logistics", STF, 3))
    nodes.append(n("lg-member-2", "Cadre", "C/2nd Lt Phillips, E", "lg-logistics", STF, 4))
    nodes.append(n("lg-member-3", "Cadre", "C/SMSgt Nichols, A", "lg-logistics", STF, 5))
    nodes.append(n("comm-oic", "OIC", "1st Lt Reed, I", "comm", STF, 1))
    nodes.append(n("finance-oic", "OIC", "1st Lt Reed, I", "finance", STF, 1))
    nodes.append(n("hs-oic", "OIC", "C/CMSgt Plummer, R", "health-word", STF, 1))
    nodes.append(n("hs-ncoic", "NCOIC", "C/CMSgt Steele, L", "health-word", STF, 2))
    nodes.append(n("hs-member-1", "Cadre", "C/SMSgt Nhan, D", "health-word", STF, 3))

    # ═══════════════════════════════════════════════
    # 6th CTS — BLUE
    # ═══════════════════════════════════════════════
    nodes.append(n("6th-sq-1sgt", "First Sergeant", "C/SMSgt Thomasson, T", "6th-sq-cmdr", S6, 1, "", secondary="ctg-df"))
    nodes.append(n("6th-flt-a-cmdr", "Flight Commander - A", "C/CMSgt Anand, R", "6th-sq-cmdr", S6, 2, "", secondary="ctg-df"))
    nodes.append(n("6th-flt-a-sgt", "Flight Sergeant - A", "C/SSgt Mellott, P", "6th-flt-a-cmdr", S6, 1, "", secondary="ctg-df"))
    nodes.append(n("6th-flt-b-cmdr", "Flight Commander - B", "", "6th-sq-cmdr", S6, 3, "", secondary="ctg-df"))
    nodes.append(n("6th-flt-b-sgt", "Flight Sergeant - B", "C/MSgt DeJesus, R", "6th-flt-b-cmdr", S6, 1, "", secondary="ctg-df"))

    # ═══════════════════════════════════════════════
    # 21st CTS — YELLOW / GINGER
    # ═══════════════════════════════════════════════
    nodes.append(n("21st-sq-1sgt", "First Sergeant", "C/CMSgt Jackson, L", "21st-sq-cmdr", S21, 1, "", secondary="ctg-df"))
    nodes.append(n("21st-flt-c-cmdr", "Flight Commander - C", "C/1st Lt Madera, G", "21st-sq-cmdr", S21, 2, "", secondary="ctg-df"))
    nodes.append(n("21st-flt-c-sgt", "Flight Sergeant - C", "C/SMSgt Wilson, T", "21st-flt-c-cmdr", S21, 1, "", secondary="ctg-df"))
    nodes.append(n("21st-flt-d-cmdr", "Flight Commander - D", "C/MSgt Calvez, T", "21st-sq-cmdr", S21, 3, "", secondary="ctg-df"))
    nodes.append(n("21st-flt-d-sgt", "Flight Sergeant - D", "C/SrA Garcia, B", "21st-flt-d-cmdr", S21, 1, "", secondary="ctg-df"))

    # ═══════════════════════════════════════════════
    # 22nd CTS — MAROON
    # ═══════════════════════════════════════════════
    nodes.append(n("22nd-sq-1sgt", "First Sergeant", "C/SMSgt Wainman, A", "22nd-sq-cmdr", S22, 1, "", secondary="ctg-df"))
    nodes.append(n("22nd-flt-e-cmdr", "Flight Commander - E", "C/2nd Lt Rizzo, H", "22nd-sq-cmdr", S22, 2, "", secondary="ctg-df"))
    nodes.append(n("22nd-flt-e-sgt", "Flight Sergeant - E", "C/MSgt Ambelis, I", "22nd-flt-e-cmdr", S22, 1, "", secondary="ctg-df"))
    nodes.append(n("22nd-flt-f-cmdr", "Flight Commander - F", "C/2nd Lt Terbizan, S", "22nd-sq-cmdr", S22, 2, "", secondary="ctg-df"))
    nodes.append(n("22nd-flt-f-sgt", "Flight Sergeant - F", "C/MSgt Kyle, E", "22nd-flt-f-cmdr", S22, 1, "", secondary="ctg-df"))

    return nodes


async def main():
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "test_database")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    nodes = build_orgchart()
    print(f"Total positions: {len(nodes)}")

    deleted = await db.org_chart_roles.delete_many({})
    print(f"Deleted {deleted.deleted_count} existing")

    if nodes:
        result = await db.org_chart_roles.insert_many(nodes)
        print(f"Inserted {len(result.inserted_ids)}")

    count = await db.org_chart_roles.count_documents({})
    print(f"Verified: {count}")

    cats = {}
    for nd in nodes:
        cats[nd["role_category"]] = cats.get(nd["role_category"], 0) + 1
    print(f"Categories: {cats}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
