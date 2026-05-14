"""Phase-2 one-shot migration: rewrite legacy participant_type values to the
canonical Phase-2 vocabulary, and lift the `exec_cadre` ptype into a
separate `is_exec_cadre` flag on cadre rows.

Rules applied (in evaluation order):

  ptype == "basic_student"  →  "student"
  ptype == "advanced_student" → "student"
  ptype == "senior_member"  →  "senior_staff"
  ptype == "exec_cadre"     →  "cadre"  (and set is_exec_cadre=true)
  ptype == "staff" AND member_type ∈ {SENIOR, CADET SPONSOR}  →  "senior_staff"
  ptype == "staff" AND member_type == "CADET"  →  "needs_review"
                       (cadets cannot be Senior Staff per Phase-2 spec)
  ptype already canonical ("senior_staff" / "cadre" / "student" / "needs_review")  →  untouched

Affected rows touch `is_removed: True` AND `is_removed: False` — both, so
historical/removed records also become consistent.

Run inside the backend container with the live DB. Does NOT create or remove
participants; only mutates `participant_type` and adds `is_exec_cadre`."""
import asyncio
import os
import sys

sys.path.insert(0, '/app/backend')
from database import db


async def migrate():
    counts = {
        "basic_student → student": 0,
        "advanced_student → student": 0,
        "senior_member → senior_staff": 0,
        "exec_cadre → cadre (+is_exec_cadre)": 0,
        "staff (SENIOR/CADET SPONSOR) → senior_staff": 0,
        "staff (CADET) → needs_review": 0,
        "staff (unknown member_type) → needs_review": 0,
        "already canonical (no change)": 0,
        "other / unknown value (no change)": 0,
        "total": 0,
    }

    cursor = db.participants.find({}, {"_id": 0, "id": 1, "participant_type": 1, "member_type": 1, "first_name": 1, "last_name": 1, "is_exec_cadre": 1})
    async for p in cursor:
        counts["total"] += 1
        pid = p["id"]
        ptype = (p.get("participant_type") or "").strip().lower()
        mtype = (p.get("member_type") or "").strip().upper()
        update = {}

        if ptype == "basic_student":
            update["participant_type"] = "student"
            counts["basic_student → student"] += 1
        elif ptype == "advanced_student":
            update["participant_type"] = "student"
            counts["advanced_student → student"] += 1
        elif ptype == "senior_member":
            update["participant_type"] = "senior_staff"
            counts["senior_member → senior_staff"] += 1
        elif ptype == "exec_cadre":
            update["participant_type"] = "cadre"
            update["is_exec_cadre"] = True
            counts["exec_cadre → cadre (+is_exec_cadre)"] += 1
        elif ptype == "staff":
            if mtype in ("SENIOR", "CADET SPONSOR"):
                update["participant_type"] = "senior_staff"
                counts["staff (SENIOR/CADET SPONSOR) → senior_staff"] += 1
            elif mtype == "CADET":
                update["participant_type"] = "needs_review"
                counts["staff (CADET) → needs_review"] += 1
            else:
                update["participant_type"] = "needs_review"
                counts["staff (unknown member_type) → needs_review"] += 1
        elif ptype in ("senior_staff", "cadre", "student", "needs_review"):
            counts["already canonical (no change)"] += 1
        else:
            counts["other / unknown value (no change)"] += 1

        # Ensure existing cadre rows have an explicit is_exec_cadre value
        if "is_exec_cadre" not in update and p.get("is_exec_cadre") is None:
            update["is_exec_cadre"] = False

        if update:
            await db.participants.update_one({"id": pid}, {"$set": update})

    print("Phase-2 migration complete.")
    print()
    print(f"{'Counts':<55}")
    print("-" * 70)
    for k, v in counts.items():
        print(f"  {k:<52}  {v:>5}")


if __name__ == "__main__":
    asyncio.run(migrate())
