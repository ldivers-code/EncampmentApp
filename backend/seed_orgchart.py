"""Rebuild the entire org chart from the TNWG ENC26 spreadsheet."""
import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

NOW = datetime.now(timezone.utc).isoformat()


def role(role_id, title, level, order, reports_to, summary="", is_sm=False):
    tag = " [SM]" if is_sm else ""
    return {
        "id": role_id,
        "role_id": role_id,
        "title": title,
        "level": level,
        "order": order,
        "reports_to": reports_to,
        "summary": f"{title}{tag}",
        "responsibilities": "",
        "assigned_participant_id": None,
        "created_at": NOW,
        "updated_at": NOW,
    }


def build_roles():
    roles = []
    o = [0]  # mutable order counter

    def add(role_id, title, level, reports_to, is_sm=False):
        o[0] += 1
        roles.append(role(role_id, title, level, o[0], reports_to, is_sm=is_sm))

    # ──── Level 0: Commander ─────────────────────────────────
    add("enc-commander", "Encampment Commander", 0, None, is_sm=True)

    # ──── Level 1: Direct reports ────────────────────────────
    add("dep-commander", "Deputy Commander", 1, "enc-commander", is_sm=True)
    add("cadet-commander", "Cadet Commander", 1, "enc-commander")
    add("chaplain", "Chaplain(s)", 1, "enc-commander", is_sm=True)
    add("safety-cadre", "Safety Cadre", 1, "enc-commander", is_sm=True)
    add("female-cadre", "Female Cadre", 1, "enc-commander")

    # ──── Level 2: Under Cadet Commander ─────────────────────
    add("group-superintendent", "Cadet Group Superintendent", 2, "cadet-commander")

    # ──── Level 2: Under Commander — Major staff branches ────
    add("chief-training-officer", "Chief Training Officer", 2, "enc-commander", is_sm=True)
    add("dep-commander-support", "Dep Commander of Support", 2, "enc-commander", is_sm=True)
    add("academics-superintendent", "Academics Superintendent", 2, "enc-commander", is_sm=True)

    # ──── Under Academics Superintendent ─────────────────────
    add("dean-academics", "Dean of Academics", 3, "academics-superintendent")
    add("dep-commander-cadets", "Deputy Commander Cadets", 4, "dean-academics")

    # ────────────────────────────────────────────────────────
    # CHIEF TRAINING OFFICER BRANCH
    # ────────────────────────────────────────────────────────

    # Training Staff OIC
    add("training-oic", "Training Staff OIC", 3, "chief-training-officer")
    add("training-oic-member-1", "Training OIC Team Member", 4, "training-oic")
    add("training-oic-member-2", "Training OIC Team Member", 4, "training-oic")
    add("training-oic-member-3", "Training OIC Team Member", 4, "training-oic")

    # Training Staff AOIC
    add("training-aoic", "Training Staff AOIC", 3, "chief-training-officer")
    add("training-aoic-member-1", "Training AOIC Team Member", 4, "training-aoic")
    add("training-aoic-member-2", "Training AOIC Team Member", 4, "training-aoic")
    add("training-aoic-member-3", "Training AOIC Team Member", 4, "training-aoic")

    # Training Staff Cadets/SM
    add("training-cadets-lead", "Training Cadets/SM Lead", 3, "chief-training-officer")
    add("training-cadets-member-1", "Training Cadets Member", 4, "training-cadets-lead")
    add("training-cadets-member-2", "Training Cadets Member", 4, "training-cadets-lead")
    add("training-cadets-member-3", "Training Cadets Member", 4, "training-cadets-lead")
    add("training-sm-1", "Training SM", 4, "training-cadets-lead", is_sm=True)
    add("training-sm-2", "Training SM", 4, "training-cadets-lead", is_sm=True)
    add("training-sm-3", "Training SM", 4, "training-cadets-lead", is_sm=True)

    # Media & Publishing
    add("media-publishing", "Media & Publishing", 3, "chief-training-officer")
    add("media-sm", "Media SM", 4, "media-publishing", is_sm=True)
    add("media-member-1", "Media Team Member", 4, "media-publishing")
    add("media-member-2", "Media Team Member", 4, "media-publishing")

    # Health Services / WORD
    add("health-services-word", "Health Services / WORD", 3, "chief-training-officer", is_sm=True)
    add("health-oic", "Health Services OIC", 4, "health-services-word")
    add("health-ncoic", "Health Services NCOIC", 4, "health-services-word")
    add("health-member-1", "Health Services Member", 4, "health-services-word")
    add("word-lead", "WORD Lead", 4, "health-services-word")

    # ────────────────────────────────────────────────────────
    # DEPUTY COMMANDER OF SUPPORT BRANCH
    # ────────────────────────────────────────────────────────

    add("support-ops-cadre", "Operations Cadre", 3, "dep-commander-support", is_sm=True)

    # Communications
    add("support-communications", "Communications", 3, "dep-commander-support")
    add("comms-lead", "Comms Lead", 4, "support-communications")
    add("comms-sm", "Comms SM", 4, "support-communications", is_sm=True)
    add("comms-member-1", "Comms Team Member", 5, "comms-lead")
    add("comms-member-2", "Comms Team Member", 5, "comms-lead")
    add("comms-member-3", "Comms Team Member", 5, "comms-lead")

    # Finance
    add("support-finance", "Finance", 3, "dep-commander-support")
    add("finance-oic", "Finance OIC", 4, "support-finance", is_sm=True)
    add("finance-aoic", "Finance AOIC", 4, "support-finance", is_sm=True)
    add("finance-member-1", "Finance Team Member", 5, "finance-oic")
    add("finance-member-2", "Finance Team Member", 5, "finance-oic")

    # Public Affairs
    add("support-public-affairs", "Public Affairs", 3, "dep-commander-support")
    add("pa-oic", "Public Affairs OIC", 4, "support-public-affairs")
    add("pa-aoic", "Public Affairs AOIC", 4, "support-public-affairs")
    add("pa-member-1", "PA Team Member", 5, "pa-oic")
    add("pa-member-2", "PA Team Member", 5, "pa-oic")
    add("pa-member-3", "PA Team Member", 5, "pa-oic")

    # Dining Facility
    add("support-dining-facility", "Dining Facility", 3, "dep-commander-support")
    add("dfac-oic", "DFAC OIC", 4, "support-dining-facility")
    add("dfac-aoic", "DFAC AOIC", 4, "support-dining-facility")
    add("dfac-member-1", "DFAC Team Member", 5, "dfac-oic")
    add("dfac-member-2", "DFAC Team Member", 5, "dfac-oic")
    add("dfac-member-3", "DFAC Team Member", 5, "dfac-oic")
    for i in range(1, 7):
        add(f"dfac-training-officer-{i}", "DFAC Training Officer", 5, "dfac-oic")

    # Logistics
    add("support-logistics", "Logistics", 3, "dep-commander-support")
    add("logistics-oic", "Logistics OIC", 4, "support-logistics")
    for i in range(1, 8):
        add(f"logistics-member-{i}", "Logistics Team Member", 5, "logistics-oic")

    # Plans & Programs
    add("support-plans-programs", "Plans & Programs", 3, "dep-commander-support")
    add("pp-oic", "Plans & Programs OIC", 4, "support-plans-programs", is_sm=True)
    add("pp-aoic-1", "Plans & Programs AOIC", 4, "support-plans-programs")
    add("pp-aoic-2", "Plans & Programs AOIC", 4, "support-plans-programs")

    # ────────────────────────────────────────────────────────
    # SQUADRONS  (6th CTS, 21st CTS, 22nd CTS, 16th OSS)
    # ────────────────────────────────────────────────────────

    squadron_defs = [
        ("6th-cts", "6th CTS", "enc-commander"),
        ("21st-cts", "21st CTS", "enc-commander"),
        ("22nd-cts", "22nd CTS", "enc-commander"),
        ("16th-oss", "16th OPS SUP SQ", "enc-commander"),
    ]

    flight_letters = ["A", "B", "C", "D", "E", "F"]

    for sq_id, sq_name, parent in squadron_defs:
        # Squadron Commander
        add(f"{sq_id}-commander", f"{sq_name} Commander", 2, parent)

        # Squadron Training Officer (SM)
        add(f"{sq_id}-training-officer", f"{sq_name} Training Officer", 3, f"{sq_id}-commander", is_sm=True)
        # Squadron Superintendent (reports to training officer)
        add(f"{sq_id}-superintendent", f"{sq_name} Superintendent", 4, f"{sq_id}-training-officer")

        # First Sergeant
        add(f"{sq_id}-first-sergeant", f"{sq_name} First Sergeant", 3, f"{sq_id}-commander")

        # Flights A-F
        for letter in flight_letters:
            flt_id = f"{sq_id}-flt-{letter.lower()}"
            add(f"{flt_id}-commander", f"Flight Commander {letter}", 3, f"{sq_id}-commander")
            add(f"{flt_id}-sergeant", f"Flight Sergeant {letter}", 4, f"{flt_id}-commander")

        # Squadron support roles
        support_roles = [
            ("logistics", "Logistics"),
            ("public-affairs", "Public Affairs"),
            ("communications", "Communications"),
            ("dining-facility", "Dining Facility"),
            ("training-officer-sq", "Training Officer"),
            ("word", "WORD"),
        ]
        for spt_id, spt_title in support_roles:
            add(f"{sq_id}-{spt_id}", f"{sq_name} {spt_title}", 3, f"{sq_id}-commander")

    return roles


async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["test_database"]

    roles = build_roles()
    print(f"Total roles to seed: {len(roles)}")

    # Delete all existing org chart roles
    deleted = await db.org_chart_roles.delete_many({})
    print(f"Deleted {deleted.deleted_count} existing roles")

    # Insert all new roles
    if roles:
        result = await db.org_chart_roles.insert_many(roles)
        print(f"Inserted {len(result.inserted_ids)} roles")

    # Verify
    count = await db.org_chart_roles.count_documents({})
    print(f"Verified: {count} roles in DB")

    # Print structure summary
    level_counts = {}
    for r in roles:
        lvl = r["level"]
        level_counts[lvl] = level_counts.get(lvl, 0) + 1
    for lvl in sorted(level_counts):
        print(f"  Level {lvl}: {level_counts[lvl]} roles")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
