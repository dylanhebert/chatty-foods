"""One-time script to backfill created_at from original conversation files.

Reads source_conversation from each record, finds the matching JSON file in
zzexclude/original_food_conversations/, extracts create_time, and updates
the created_at column.

Usage:
    cd chatty-foods
    .venv/Scripts/python scripts/backfill_dates.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import db

CONV_DIR = os.path.join(os.path.dirname(__file__), "..", "zzexclude", "original_food_conversations")


def backfill():
    conn = db.get_db()

    # Build a cache of source_conversation -> create_time
    create_times = {}
    for filename in os.listdir(CONV_DIR):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(CONV_DIR, filename)
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        if "create_time" in data:
            create_times[filename] = data["create_time"]

    updated = 0
    skipped = 0

    for table in ("recipe_cards", "food_tips"):
        rows = conn.execute(
            f"SELECT id, source_conversation, created_at FROM {table}"
        ).fetchall()
        for row in rows:
            if row["created_at"]:
                skipped += 1
                continue
            src = row["source_conversation"]
            if src and src in create_times:
                conn.execute(
                    f"UPDATE {table} SET created_at = ? WHERE id = ?",
                    (create_times[src], row["id"]),
                )
                updated += 1
            else:
                print(f"  No match: {table} id={row['id']} src={src}")
                skipped += 1

    conn.commit()
    conn.close()
    print(f"Done. Updated: {updated}, Skipped: {skipped}")


if __name__ == "__main__":
    backfill()
