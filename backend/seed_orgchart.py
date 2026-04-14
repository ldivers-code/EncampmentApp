"""
Strict 1:1 Org Chart Seed — TNWG ENC26 restructured hierarchy.
Categories: command, cadet_training, support, cadet_support
Dual reporting via secondary_reports_to.
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


CMD = "command"
CTR = "cadet_training"
SUP = "support"
CSS = "cadet_support"


def build_orgchart():
    nodes = []

    # ═══════════════════════════════════════════════
    # LEVEL 0 — ENCAMPMENT COMMANDER
    # ═══════════════════════════════════════════════
    nodes.append(n("enc-commander", "Encampment Commander", "Maj Divers, L", None, CMD, 1))

    # ═══════════════════════════════════════════════
    # LEVEL 1 — DIRECT REPORTS
    # ═══════════════════════════════════════════════
    nodes.append(n("commandant", "Commandant of Cadets", "", "enc-commander", CMD, 1))
    nodes.append(n("dcs", "Deputy Commander for Support", "Capt Belli, S", "enc-commander", SUP, 2, "DCS"))
    nodes.append(n("sm-superintendent", "SM Superintendent", "TSgt Breslin, D", "enc-commander", CMD, 3))
    nodes.append(n("chaplains", "Chaplain(s)", "", "enc-commander", CMD, 4))
    nodes.append(n("safety", "Safety", "", "enc-commander", CMD, 5))

    # ═══════════════════════════════════════════════
    # LEVEL 2 — UNDER COMMANDANT
    # ═══════════════════════════════════════════════
    nodes.append(n("ctg-cc", "Cadet Training Group Commander", "C/Lt Col Yoder, L", "commandant", CTR, 1, "CTG/CC"))

    # ═══════════════════════════════════════════════
    # LEVEL 3 — UNDER CTG/CC
    # ═══════════════════════════════════════════════
    nodes.append(n("ctg-cd", "Operations", "C/Lt Col Grammer, A", "ctg-cc", CTR, 1, "CTG/CD"))
    nodes.append(n("ctg-df", "Academics", "C/Maj Doran, G", "ctg-cc", CTR, 2, "CTG/DF"))
    nodes.append(n("ctg-ccea", "Chief Cadet Enlisted Advisor", "C/CMSgt Railey, A", "ctg-cc", CTR, 3, "CTG/CCEA"))
    nodes.append(n("css-cc", "Cadet Support Squadron Commander", "C/Capt. Posta, A", "ctg-cc", CSS, 4, "CSS/CC", secondary="ctg-df"))
    nodes.append(n("chief-training-officer", "Chief Training Officer", "", "ctg-cc", CTR, 5, "CTO"))
    nodes.append(n("6th-sq-cmdr", "6th CTS Commander", "C/Capt Nhan, V", "ctg-cc", CTR, 6, "6th CTS"))
    nodes.append(n("21st-sq-cmdr", "21st CTS Commander", "C/2nd Lt Nair, P", "ctg-cc", CTR, 7, "21st CTS"))
    nodes.append(n("22nd-sq-cmdr", "22nd CTS Commander", "C/1st Lt Breslin, D", "ctg-cc", CTR, 8, "22nd CTS"))

    # ═══════════════════════════════════════════════
    # UNDER CTG/CCEA — Enlisted departments
    # ═══════════════════════════════════════════════
    nodes.append(n("public-affairs-dept", "Public Affairs", "", "ctg-ccea", CTR, 1))
    nodes.append(n("dining-facility-dept", "Dining Facility", "", "ctg-ccea", CTR, 2))

    # — Public Affairs cadre —
    nodes.append(n("pa-oic", "OIC", "C/Lt Col Bartlett, E", "public-affairs-dept", CTR, 1))
    nodes.append(n("pa-aoic", "AOIC", "C/2d Lt Boykin, N", "public-affairs-dept", CTR, 2))
    nodes.append(n("pa-member-1", "Cadre", "C/SMSgt Tran, T", "public-affairs-dept", CTR, 3))
    nodes.append(n("pa-member-2", "Cadre", "C/TSgt Zamudio, A", "public-affairs-dept", CTR, 4))
    nodes.append(n("pa-member-3", "Cadre", "C/MSgt Plucker, J", "public-affairs-dept", CTR, 5))
    nodes.append(n("pa-member-4", "Cadre", "C/2nd Lt Marfio, M", "public-affairs-dept", CTR, 6))

    # — Dining Facility cadre —
    nodes.append(n("df-oic", "OIC", "C/1st Lt Jackson, J", "dining-facility-dept", CTR, 1))
    nodes.append(n("df-aoic", "AOIC", "C/1st Lt Ciampa, B", "dining-facility-dept", CTR, 2))
    nodes.append(n("df-member-1", "Cadre", "C/SSgt Mulverhill, M", "dining-facility-dept", CTR, 3))
    nodes.append(n("df-member-2", "Cadre", "C/CMSgt Kover, M", "dining-facility-dept", CTR, 4))
    nodes.append(n("df-member-3", "Cadre", "C/SrA Sporin, L", "dining-facility-dept", CTR, 5))
    nodes.append(n("df-member-4", "Cadre", "C/SSgt Flippen, M", "dining-facility-dept", CTR, 6))

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
    # ═══════════════════════════════════════════════
    nodes.append(n("pp-cadet", "Plans & Programs", "", "chief-training-officer", CTR, 1, "Cadet Level"))
    nodes.append(n("media-publishing", "Media & Publishing", "", "chief-training-officer", CTR, 2))
    nodes.append(n("cto-sm", "SM", "C/Capt Plucker, D", "chief-training-officer", CTR, 3))
    nodes.append(n("cto-cadets-1", "Cadets", "C/SMSgt Breslin, T", "chief-training-officer", CTR, 4))
    nodes.append(n("cto-cadets-2", "Cadets", "C/SrA Gould, J", "chief-training-officer", CTR, 5))
    nodes.append(n("cto-cadets-3", "Cadets", "C/SrA Cranford, N", "chief-training-officer", CTR, 6))
    nodes.append(n("cto-cadets-4", "Cadets", "C/CMSgt Mueller, L", "chief-training-officer", CTR, 7))

    # — PP Cadet members —
    nodes.append(n("pp-cadet-oic", "OIC", "Lt Col Brian Hughes", "pp-cadet", CTR, 1))
    nodes.append(n("pp-cadet-aoic", "AOIC", "Maj Randall Parker", "pp-cadet", CTR, 2))
    nodes.append(n("pp-cadet-coic", "C/OIC", "C/Maj. Stacey, R", "pp-cadet", CTR, 3))
    nodes.append(n("pp-cadet-caoic", "C/AOIC", "C/Capt. Lawson, J", "pp-cadet", CTR, 4))
    nodes.append(n("pp-cadet-member-1", "Cadre", "C/Maj. Phillips, L", "pp-cadet", CTR, 5))
    nodes.append(n("pp-cadet-member-2", "Cadre", "C/Lt Col Santos, N", "pp-cadet", CTR, 6))
    nodes.append(n("media-member-1", "Cadre", "C/TSgt Spurling, I", "media-publishing", CTR, 1))

    # ═══════════════════════════════════════════════
    # UNDER DCS — Support departments
    # ═══════════════════════════════════════════════
    nodes.append(n("xp-plans", "Plans & Programs", "", "dcs", SUP, 1, "XP"))
    nodes.append(n("lg-logistics", "Logistics", "Capt Reed, A", "dcs", SUP, 2, "LG"))
    nodes.append(n("comm", "Communications", "", "dcs", SUP, 3, "Comm"))
    nodes.append(n("finance", "Finance", "", "dcs", SUP, 4))
    nodes.append(n("health-word", "Health Services / WORD", "Lt Col Divers, K", "dcs", SUP, 5))

    # — XP members —
    nodes.append(n("xp-oic", "OIC", "Lt Col Brian Hughes", "xp-plans", SUP, 1))
    nodes.append(n("xp-aoic", "AOIC", "Maj Randall Parker", "xp-plans", SUP, 2))

    # — LG Logistics members —
    nodes.append(n("lg-oic", "OIC", "C/Capt Parker, T", "lg-logistics", SUP, 1))
    nodes.append(n("lg-aoic", "AOIC", "C/2nd Lt Langston, M", "lg-logistics", SUP, 2))
    nodes.append(n("lg-member-1", "Cadre", "C/SrA Mudhireddy, V", "lg-logistics", SUP, 3))
    nodes.append(n("lg-member-2", "Cadre", "C/2nd Lt Phillips, E", "lg-logistics", SUP, 4))
    nodes.append(n("lg-member-3", "Cadre", "C/SMSgt Nichols, A", "lg-logistics", SUP, 5))

    # — Comm member —
    nodes.append(n("comm-oic", "OIC", "1st Lt Reed, I", "comm", SUP, 1))

    # — Finance member —
    nodes.append(n("finance-oic", "OIC", "1st Lt Reed, I", "finance", SUP, 1))

    # — Health Services / WORD members —
    nodes.append(n("hs-oic", "OIC", "C/CMSgt Plummer, R", "health-word", SUP, 1))
    nodes.append(n("hs-ncoic", "NCOIC", "C/CMSgt Steele, L", "health-word", SUP, 2))
    nodes.append(n("hs-member-1", "Cadre", "C/SMSgt Nhan, D", "health-word", SUP, 3))

    # ═══════════════════════════════════════════════
    # 6th CTS SQUADRON
    # ═══════════════════════════════════════════════
    nodes.append(n("6th-sq-to", "Squadron Training Officer", "Capt Brad Dozier", "6th-sq-cmdr", CTR, 1))
    nodes.append(n("6th-sq-1sgt", "First Sergeant", "C/SMSgt Thomasson, T", "6th-sq-cmdr", CTR, 2))
    nodes.append(n("6th-flt-a-cmdr", "Flight Commander - A", "C/CMSgt Anand, R", "6th-sq-cmdr", CTR, 3))
    nodes.append(n("6th-flt-a-sgt", "Flight Sergeant - A", "C/SSgt Mellott, P", "6th-flt-a-cmdr", CTR, 1))
    nodes.append(n("6th-flt-b-cmdr", "Flight Commander - B", "", "6th-sq-cmdr", CTR, 4))
    nodes.append(n("6th-flt-b-sgt", "Flight Sergeant - B", "C/MSgt DeJesus, R", "6th-flt-b-cmdr", CTR, 1))

    # ═══════════════════════════════════════════════
    # 21st CTS SQUADRON
    # ═══════════════════════════════════════════════
    nodes.append(n("21st-sq-to", "Squadron Training Officer", "Capt Renee Cyr", "21st-sq-cmdr", CTR, 1))
    nodes.append(n("21st-sq-1sgt", "First Sergeant", "C/CMSgt Jackson, L", "21st-sq-cmdr", CTR, 2))
    nodes.append(n("21st-flt-c-cmdr", "Flight Commander - C", "C/1st Lt Madera, G", "21st-sq-cmdr", CTR, 3))
    nodes.append(n("21st-flt-c-sgt", "Flight Sergeant - C", "C/SMSgt Wilson, T", "21st-flt-c-cmdr", CTR, 1))
    nodes.append(n("21st-flt-d-cmdr", "Flight Commander - D", "C/MSgt Calvez, T", "21st-sq-cmdr", CTR, 4))
    nodes.append(n("21st-flt-d-sgt", "Flight Sergeant - D", "C/SrA Garcia, B", "21st-flt-d-cmdr", CTR, 1))

    # ═══════════════════════════════════════════════
    # 22nd CTS SQUADRON
    # ═══════════════════════════════════════════════
    nodes.append(n("22nd-sq-to", "Squadron Training Officer", "1st Lt Max Hammond", "22nd-sq-cmdr", CTR, 1))
    nodes.append(n("22nd-sq-1sgt", "First Sergeant", "C/SMSgt Wainman, A", "22nd-sq-cmdr", CTR, 2))
    nodes.append(n("22nd-flt-e-cmdr", "Flight Commander - E", "C/2nd Lt Rizzo, H", "22nd-sq-cmdr", CTR, 3))
    nodes.append(n("22nd-flt-e-sgt", "Flight Sergeant - E", "C/MSgt Ambelis, I", "22nd-flt-e-cmdr", CTR, 1))
    nodes.append(n("22nd-flt-f-cmdr", "Flight Commander - F", "C/2nd Lt Terbizan, S", "22nd-sq-cmdr", CTR, 4))
    nodes.append(n("22nd-flt-f-sgt", "Flight Sergeant - F", "C/MSgt Kyle, E", "22nd-flt-f-cmdr", CTR, 1))

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

    by_parent = {}
    for nd in nodes:
        p = nd["reports_to"] or "__root__"
        by_parent.setdefault(p, []).append(nd)

    def pt(pid, indent=0):
        for c in sorted(by_parent.get(pid, []), key=lambda x: x["order"]):
            lbl = f" ({c['display_label']})" if c["display_label"] else ""
            nm = f" - {c['assigned_name']}" if c["assigned_name"] else ""
            sec = f" [secondary→{c['secondary_reports_to']}]" if c.get("secondary_reports_to") else ""
            print(f"{'  ' * indent}{c['position_title']}{lbl}{nm} [{c['role_category']}]{sec}")
            pt(c["role_id"], indent + 1)

    print("\n=== HIERARCHY ===")
    pt("__root__")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
