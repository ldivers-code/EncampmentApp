"""
Strict 1:1 Org Chart Seed from TNWG ENC26 ORG CHART spreadsheet.
Every node maps directly to a position visible in the spreadsheet.
NO inferred roles. NO placeholders. NO guessing.
"""
import asyncio
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

NOW = datetime.now(timezone.utc).isoformat()


def node(role_id, position_title, assigned_name, parent_id, category, order, display_label=""):
    return {
        "id": role_id,
        "role_id": role_id,
        "position_title": position_title,
        "assigned_name": assigned_name.strip() if assigned_name else "",
        "reports_to": parent_id,
        "role_category": category,
        "order": order,
        "display_label": display_label,
        "job_description": "",
        "responsible_for": "",
        "supervises": "",
        "created_at": NOW,
        "updated_at": NOW,
    }


def build_orgchart():
    nodes = []

    # =====================================================
    # ROOT - Encampment Commander
    # =====================================================
    nodes.append(node("enc-commander", "Encampment Commander", "Maj Divers, L", None, "senior_member", 1))

    # =====================================================
    # LEVEL 1 - Direct Reports to Encampment Commander
    # =====================================================
    nodes.append(node("chaplains", "Chaplain(s)", "", "enc-commander", "executive_cadre", 1))
    nodes.append(node("safety", "Safety", "", "enc-commander", "executive_cadre", 2))
    nodes.append(node("commandant", "Commandant", "", "enc-commander", "executive_cadre", 3))
    nodes.append(node("dep-cmdr-support", "Deputy Commander of Support", "Capt Belli, S", "enc-commander", "senior_member", 4, "SM"))
    nodes.append(node("academics-supt", "Academics Superintendent", "", "enc-commander", "executive_cadre", 5))
    nodes.append(node("cadet-group-cmdr", "Cadet Group Commander", "C/Lt Col Yoder, L", "enc-commander", "out_of_tnwg", 6))
    nodes.append(node("superintendent", "Superintendent", "TSgt Breslin, D", "enc-commander", "senior_member", 7))
    nodes.append(node("plans-programs-sm", "Plans & Programs", "", "enc-commander", "support_cadre", 8, "SM Level"))
    nodes.append(node("communications-sm", "Communications", "", "enc-commander", "support_cadre", 9, "SM Level"))
    nodes.append(node("finance-sm", "Finance", "", "enc-commander", "support_cadre", 10, "SM Level"))
    nodes.append(node("chief-training-officer", "Chief Training Officer", "", "enc-commander", "executive_cadre", 11))
    nodes.append(node("health-services-word", "Health Services / WORD", "Lt Col Divers, K", "enc-commander", "support_cadre", 12))

    # =====================================================
    # Under Academics Superintendent
    # =====================================================
    nodes.append(node("dean-of-academics", "C/Dean Of Academics", "C/Maj Doran, G", "academics-supt", "executive_cadre", 1))

    # =====================================================
    # Under Cadet Group Commander
    # =====================================================
    nodes.append(node("c-deputy-cmdr", "C/Deputy Commander", "C/Lt Col Grammer, A", "cadet-group-cmdr", "out_of_tnwg", 1))
    # Squadrons report to Cadet Group Commander
    nodes.append(node("6th-sq-cmdr", "6th Squadron Commander", "C/Capt Nhan, V", "cadet-group-cmdr", "training_cadre", 2))
    nodes.append(node("21st-sq-cmdr", "21st Squadron Commander", "C/2nd Lt Nair, P", "cadet-group-cmdr", "training_cadre", 3))
    nodes.append(node("22nd-sq-cmdr", "22nd Squadron Commander", "C/1st Lt Breslin, D", "cadet-group-cmdr", "training_cadre", 4))
    nodes.append(node("16th-oss-cmdr", "16th Ops Spt Sq Commander", "C/Capt. Posta, A", "cadet-group-cmdr", "executive_cadre", 5))

    # =====================================================
    # Under Superintendent
    # =====================================================
    nodes.append(node("cadet-group-supt", "Cadet Group Superintendent", "C/CMSgt Railey, A", "superintendent", "out_of_tnwg", 1))

    # =====================================================
    # Under Cadet Group Superintendent - Departments
    # =====================================================
    nodes.append(node("logistics-dept", "Logistics", "Capt Reed, A", "cadet-group-supt", "support_cadre", 1, "SM: Capt Reed, A"))
    nodes.append(node("public-affairs-dept", "Public Affairs", "", "cadet-group-supt", "support_cadre", 2))
    nodes.append(node("dining-facility-dept", "Dining Facility", "", "cadet-group-supt", "support_cadre", 3))

    # --- Logistics members ---
    nodes.append(node("log-oic", "OIC", "C/Capt Parker, T", "logistics-dept", "out_of_tnwg", 1))
    nodes.append(node("log-aoic", "AOIC", "C/2nd Lt Langston, M", "logistics-dept", "out_of_tnwg", 2))
    nodes.append(node("log-member-1", "Cadre", "C/SrA Mudhireddy, V", "logistics-dept", "out_of_tnwg", 3))
    nodes.append(node("log-member-2", "Cadre", "C/2nd Lt Phillips, E", "logistics-dept", "training_cadre", 4))
    nodes.append(node("log-member-3", "Cadre", "C/SMSgt Nichols, A", "logistics-dept", "female_cadre", 5))

    # --- Public Affairs members ---
    nodes.append(node("pa-oic", "OIC", "C/Lt Col Bartlett, E", "public-affairs-dept", "out_of_tnwg", 1))
    nodes.append(node("pa-aoic", "AOIC", "C/2d Lt Boykin, N", "public-affairs-dept", "out_of_tnwg", 2))
    nodes.append(node("pa-member-1", "Cadre", "C/SMSgt Tran, T", "public-affairs-dept", "out_of_tnwg", 3))
    nodes.append(node("pa-member-2", "Cadre", "C/TSgt Zamudio, A", "public-affairs-dept", "out_of_tnwg", 4))
    nodes.append(node("pa-member-3", "Cadre", "C/MSgt Plucker, J", "public-affairs-dept", "out_of_tnwg", 5))
    nodes.append(node("pa-member-4", "Cadre", "C/2nd Lt Marfio, M", "public-affairs-dept", "out_of_tnwg", 6))

    # --- Dining Facility members ---
    nodes.append(node("df-oic", "OIC", "C/1st Lt Jackson, J", "dining-facility-dept", "out_of_tnwg", 1))
    nodes.append(node("df-aoic", "AOIC", "C/1st Lt Ciampa, B", "dining-facility-dept", "out_of_tnwg", 2))
    nodes.append(node("df-member-1", "Cadre", "C/SSgt Mulverhill, M", "dining-facility-dept", "out_of_tnwg", 3))
    nodes.append(node("df-member-2", "Cadre", "C/CMSgt Kover, M", "dining-facility-dept", "out_of_tnwg", 4))
    nodes.append(node("df-member-3", "Cadre", "C/SrA Sporin, L", "dining-facility-dept", "out_of_tnwg", 5))
    nodes.append(node("df-member-4", "Cadre", "C/SSgt Flippen, M", "dining-facility-dept", "out_of_tnwg", 6))

    # =====================================================
    # Under Plans & Programs (SM Level)
    # =====================================================
    nodes.append(node("pp-sm-oic", "OIC", "Lt Col Brian Hughes", "plans-programs-sm", "senior_member", 1))
    nodes.append(node("pp-sm-aoic", "AOIC", "Maj Randall Parker", "plans-programs-sm", "senior_member", 2))

    # =====================================================
    # Under Communications (SM Level)
    # =====================================================
    nodes.append(node("comms-sm-oic", "OIC", "1st Lt Reed, I", "communications-sm", "senior_member", 1))

    # =====================================================
    # Under Finance (SM Level)
    # =====================================================
    nodes.append(node("finance-sm-oic", "OIC", "1st Lt Reed, I", "finance-sm", "senior_member", 1))

    # =====================================================
    # Under Chief Training Officer
    # =====================================================
    nodes.append(node("pp-cadet", "Plans & Programs", "", "chief-training-officer", "operations_cadre", 1, "Cadet Level"))
    nodes.append(node("media-publishing", "Media & Publishing", "", "chief-training-officer", "support_cadre", 2))
    nodes.append(node("cto-sm", "SM", "C/Capt Plucker, D", "chief-training-officer", "out_of_tnwg", 3))
    nodes.append(node("cto-cadets-1", "Cadets", "C/SMSgt Breslin, T", "chief-training-officer", "out_of_tnwg", 4))
    nodes.append(node("cto-cadets-2", "Cadets", "C/SrA Gould, J", "chief-training-officer", "training_cadre", 5))
    nodes.append(node("cto-cadets-3", "Cadets", "C/SrA Cranford, N", "chief-training-officer", "training_cadre", 6))
    nodes.append(node("cto-cadets-4", "Cadets", "C/CMSgt Mueller, L", "chief-training-officer", "female_cadre", 7))

    # --- Plans & Programs (Cadet) members ---
    nodes.append(node("pp-cadet-oic", "OIC", "Lt Col Brian Hughes", "pp-cadet", "senior_member", 1))
    nodes.append(node("pp-cadet-aoic", "AOIC", "Maj Randall Parker", "pp-cadet", "senior_member", 2))
    nodes.append(node("pp-cadet-coic", "C/OIC", "C/Maj. Stacey, R", "pp-cadet", "out_of_tnwg", 3))
    nodes.append(node("pp-cadet-caoic", "C/AOIC", "C/Capt. Lawson, J", "pp-cadet", "out_of_tnwg", 4))
    nodes.append(node("pp-cadet-member-1", "Cadre", "C/Maj. Phillips, L", "pp-cadet", "out_of_tnwg", 5))
    nodes.append(node("pp-cadet-member-2", "Cadre", "C/Lt Col Santos, N", "pp-cadet", "out_of_tnwg", 6))

    # --- Media & Publishing member ---
    nodes.append(node("media-member-1", "Cadre", "C/TSgt Spurling, I", "media-publishing", "training_cadre", 1))

    # =====================================================
    # Under Health Services / WORD
    # =====================================================
    nodes.append(node("hs-oic", "OIC", "C/CMSgt Plummer, R", "health-services-word", "out_of_tnwg", 1))
    nodes.append(node("hs-ncoic", "NCOIC", "C/CMSgt Steele, L", "health-services-word", "out_of_tnwg", 2))
    nodes.append(node("hs-member-1", "Cadre", "C/SMSgt Nhan, D", "health-services-word", "out_of_tnwg", 3))

    # =====================================================
    # 6th SQUADRON
    # =====================================================
    nodes.append(node("6th-sq-to", "Squadron Training Officer", "Capt Brad Dozier", "6th-sq-cmdr", "senior_member", 1))
    nodes.append(node("6th-sq-1sgt", "First Sergeant", "C/SMSgt Thomasson, T", "6th-sq-cmdr", "training_cadre", 2))
    # Flight A
    nodes.append(node("6th-flt-a-cmdr", "Flight Commander - A", "C/CMSgt Anand, R", "6th-sq-cmdr", "out_of_tnwg", 3))
    nodes.append(node("6th-flt-a-sgt", "Flight Sergeant - A", "C/SSgt Mellott, P", "6th-flt-a-cmdr", "out_of_tnwg", 1))
    # Flight B
    nodes.append(node("6th-flt-b-cmdr", "Flight Commander - B", "", "6th-sq-cmdr", "training_cadre", 4))
    nodes.append(node("6th-flt-b-sgt", "Flight Sergeant - B", "C/MSgt DeJesus, R", "6th-flt-b-cmdr", "out_of_tnwg", 1))

    # =====================================================
    # 21st SQUADRON
    # =====================================================
    nodes.append(node("21st-sq-to", "Squadron Training Officer", "Capt Renee Cyr", "21st-sq-cmdr", "senior_member", 1))
    nodes.append(node("21st-sq-1sgt", "First Sergeant", "C/CMSgt Jackson, L", "21st-sq-cmdr", "training_cadre", 2))
    # Flight C
    nodes.append(node("21st-flt-c-cmdr", "Flight Commander - C", "C/1st Lt Madera, G", "21st-sq-cmdr", "female_cadre", 3))
    nodes.append(node("21st-flt-c-sgt", "Flight Sergeant - C", "C/SMSgt Wilson, T", "21st-flt-c-cmdr", "out_of_tnwg", 1))
    # Flight D
    nodes.append(node("21st-flt-d-cmdr", "Flight Commander - D", "C/MSgt Calvez, T", "21st-sq-cmdr", "out_of_tnwg", 4))
    nodes.append(node("21st-flt-d-sgt", "Flight Sergeant - D", "C/SrA Garcia, B", "21st-flt-d-cmdr", "out_of_tnwg", 1))

    # =====================================================
    # 22nd SQUADRON
    # =====================================================
    nodes.append(node("22nd-sq-to", "Squadron Training Officer", "1st Lt Max Hammond", "22nd-sq-cmdr", "senior_member", 1))
    nodes.append(node("22nd-sq-1sgt", "First Sergeant", "C/SMSgt Wainman, A", "22nd-sq-cmdr", "training_cadre", 2))
    # Flight E
    nodes.append(node("22nd-flt-e-cmdr", "Flight Commander - E", "C/2nd Lt Rizzo, H", "22nd-sq-cmdr", "out_of_tnwg", 3))
    nodes.append(node("22nd-flt-e-sgt", "Flight Sergeant - E", "C/MSgt Ambelis, I", "22nd-flt-e-cmdr", "out_of_tnwg", 1))
    # Flight F
    nodes.append(node("22nd-flt-f-cmdr", "Flight Commander - F", "C/2nd Lt Terbizan, S", "22nd-sq-cmdr", "out_of_tnwg", 4))
    nodes.append(node("22nd-flt-f-sgt", "Flight Sergeant - F", "C/MSgt Kyle, E", "22nd-flt-f-cmdr", "out_of_tnwg", 1))

    # =====================================================
    # 16th OPS SUPPORT SQUADRON
    # =====================================================
    nodes.append(node("16th-oss-to", "OSS Training Officer", "", "16th-oss-cmdr", "executive_cadre", 1))
    nodes.append(node("16th-oss-1sgt", "First Sergeant", "", "16th-oss-cmdr", "executive_cadre", 2))
    nodes.append(node("16th-oss-logistics", "Logistics", "C/Capt Parker, T", "16th-oss-cmdr", "out_of_tnwg", 3))
    nodes.append(node("16th-oss-pa", "Public Affairs", "C/Lt Col Bartlett, E", "16th-oss-cmdr", "out_of_tnwg", 4))
    nodes.append(node("16th-oss-comms", "Communications", "", "16th-oss-cmdr", "support_cadre", 5))
    nodes.append(node("16th-oss-dining", "Dining Facility", "C/1st Lt Jackson, J", "16th-oss-cmdr", "out_of_tnwg", 6))
    nodes.append(node("16th-oss-word", "WORD", "C/CMSgt Plummer, R", "16th-oss-cmdr", "out_of_tnwg", 7))

    return nodes


async def main():
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "test_database")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    nodes = build_orgchart()
    print(f"Total positions to seed: {len(nodes)}")

    # Wipe existing org chart
    deleted = await db.org_chart_roles.delete_many({})
    print(f"Deleted {deleted.deleted_count} existing positions")

    # Insert all
    if nodes:
        result = await db.org_chart_roles.insert_many(nodes)
        print(f"Inserted {len(result.inserted_ids)} positions")

    # Verify
    count = await db.org_chart_roles.count_documents({})
    print(f"Verified: {count} positions in DB")

    # Print tree
    by_parent = {}
    for n in nodes:
        p = n["reports_to"] or "__root__"
        by_parent.setdefault(p, []).append(n)

    def print_tree(parent_id, indent=0):
        children = by_parent.get(parent_id, [])
        for c in sorted(children, key=lambda x: x["order"]):
            name_str = f" - {c['assigned_name']}" if c['assigned_name'] else ""
            print(f"{'  ' * indent}{c['position_title']}{name_str} [{c['role_category']}]")
            print_tree(c["role_id"], indent + 1)

    print("\n=== ORG CHART TREE ===")
    print_tree("__root__")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
