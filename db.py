import hashlib
import json
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "chatty_foods.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


_RECIPE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS recipe_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT UNIQUE,
        file_hash TEXT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        prep_time INTEGER,
        cook_time INTEGER,
        portion_count TEXT,
        ingredients TEXT,
        directions TEXT,
        notes TEXT,
        source_conversation TEXT
    )
"""

_TIP_SCHEMA = """
    CREATE TABLE IF NOT EXISTS food_tips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT UNIQUE,
        file_hash TEXT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        items TEXT,
        notes TEXT,
        source_conversation TEXT
    )
"""


def _needs_migration(conn, table, column):
    """Check if a column has a NOT NULL constraint that needs relaxing."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    for row in rows:
        if row["name"] == column:
            return row["notnull"] == 1
    return False


def _migrate_table(conn, table, new_schema):
    """Recreate a table with a new schema, preserving all data."""
    conn.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
    conn.execute(new_schema)
    # Copy all columns that exist in both old and new tables
    old_cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table}_old)").fetchall()]
    new_cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    shared = [c for c in old_cols if c in new_cols]
    cols = ", ".join(shared)
    conn.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM {table}_old")
    conn.execute(f"DROP TABLE {table}_old")


def init_db():
    conn = get_db()
    # Check if migration is needed (existing DB with NOT NULL on file_path)
    tables = [r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]

    if "recipe_cards" in tables and _needs_migration(conn, "recipe_cards", "file_path"):
        _migrate_table(conn, "recipe_cards", _RECIPE_SCHEMA)
    else:
        conn.execute(_RECIPE_SCHEMA)

    if "food_tips" in tables and _needs_migration(conn, "food_tips", "file_path"):
        _migrate_table(conn, "food_tips", _TIP_SCHEMA)
    else:
        conn.execute(_TIP_SCHEMA)

    conn.commit()
    conn.close()


def _file_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def _sync_folder(conn, folder_name, table, parse_fn):
    folder = os.path.join(DATA_DIR, folder_name)
    if not os.path.isdir(folder):
        return

    disk_files = {}
    for fname in os.listdir(folder):
        if fname.endswith(".json"):
            full_path = os.path.join(folder, fname)
            rel_path = f"{folder_name}/{fname}"
            disk_files[rel_path] = full_path

    # Get existing records from DB
    rows = conn.execute(
        f"SELECT file_path, file_hash FROM {table}"
    ).fetchall()
    db_records = {row["file_path"]: row["file_hash"] for row in rows}

    # Delete removed files
    for db_path in db_records:
        if db_path not in disk_files:
            conn.execute(f"DELETE FROM {table} WHERE file_path = ?", (db_path,))

    # Insert or update
    for rel_path, full_path in disk_files.items():
        fhash = _file_hash(full_path)
        if rel_path not in db_records:
            _upsert(conn, table, full_path, rel_path, fhash, parse_fn)
        elif db_records[rel_path] != fhash:
            _upsert(conn, table, full_path, rel_path, fhash, parse_fn)

    conn.commit()


def _upsert(conn, table, full_path, rel_path, fhash, parse_fn):
    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    values = parse_fn(data, rel_path, fhash)
    columns = ", ".join(values.keys())
    placeholders = ", ".join("?" for _ in values)
    updates = ", ".join(f"{k} = ?" for k in values if k != "file_path")
    update_vals = [v for k, v in values.items() if k != "file_path"]

    conn.execute(
        f"""INSERT INTO {table} ({columns}) VALUES ({placeholders})
            ON CONFLICT(file_path) DO UPDATE SET {updates}""",
        list(values.values()) + update_vals,
    )


def _parse_recipe(data, rel_path, fhash):
    return {
        "file_path": rel_path,
        "file_hash": fhash,
        "title": data.get("title", ""),
        "category": data.get("category", ""),
        "prep_time": data.get("prep_time", 0),
        "cook_time": data.get("cook_time", 0),
        "portion_count": data.get("portion_count", ""),
        "ingredients": json.dumps(data.get("ingredients", [])),
        "directions": json.dumps(data.get("directions", [])),
        "notes": data.get("notes", ""),
        "source_conversation": data.get("source_conversation"),
    }


def _parse_tip(data, rel_path, fhash):
    return {
        "file_path": rel_path,
        "file_hash": fhash,
        "title": data.get("title", ""),
        "category": data.get("category", ""),
        "items": json.dumps(data.get("items", [])),
        "notes": data.get("notes", ""),
        "source_conversation": data.get("source_conversation"),
    }


def sync_all():
    conn = get_db()
    _sync_folder(conn, "recipe_cards", "recipe_cards", _parse_recipe)
    _sync_folder(conn, "food_tips", "food_tips", _parse_tip)
    conn.close()


# Query helpers

def get_recipes(category=None):
    conn = get_db()
    if category:
        rows = conn.execute(
            "SELECT id, title, category, prep_time, cook_time, portion_count "
            "FROM recipe_cards WHERE category = ? ORDER BY title",
            (category,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, category, prep_time, cook_time, portion_count "
            "FROM recipe_cards ORDER BY title"
        ).fetchall()
    conn.close()
    return rows


def get_recipe(recipe_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM recipe_cards WHERE id = ?", (recipe_id,)
    ).fetchone()
    conn.close()
    return row


def get_tips(category=None):
    conn = get_db()
    if category:
        rows = conn.execute(
            "SELECT id, title, category, items FROM food_tips "
            "WHERE category = ? ORDER BY title",
            (category,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, category, items FROM food_tips ORDER BY title"
        ).fetchall()
    conn.close()
    return rows


def get_tip(tip_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM food_tips WHERE id = ?", (tip_id,)
    ).fetchone()
    conn.close()
    return row


def get_recipe_categories():
    conn = get_db()
    rows = conn.execute(
        "SELECT category, COUNT(*) as count FROM recipe_cards "
        "GROUP BY category ORDER BY category"
    ).fetchall()
    conn.close()
    return rows


def get_tip_categories():
    conn = get_db()
    rows = conn.execute(
        "SELECT category, COUNT(*) as count FROM food_tips "
        "GROUP BY category ORDER BY category"
    ).fetchall()
    conn.close()
    return rows


def get_counts():
    conn = get_db()
    recipe_count = conn.execute("SELECT COUNT(*) FROM recipe_cards").fetchone()[0]
    tip_count = conn.execute("SELECT COUNT(*) FROM food_tips").fetchone()[0]
    conn.close()
    return recipe_count, tip_count


def insert_recipe(data):
    conn = get_db()
    conn.execute(
        "INSERT INTO recipe_cards (title, category, prep_time, cook_time, "
        "portion_count, ingredients, directions, notes, source_conversation) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            data["title"],
            data["category"],
            data.get("prep_time", 0),
            data.get("cook_time", 0),
            data.get("portion_count", ""),
            json.dumps(data.get("ingredients", [])),
            json.dumps(data.get("directions", [])),
            data.get("notes", ""),
            data.get("source_conversation"),
        ),
    )
    row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return row_id


def insert_tip(data):
    conn = get_db()
    conn.execute(
        "INSERT INTO food_tips (title, category, items, notes, source_conversation) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            data["title"],
            data["category"],
            json.dumps(data.get("items", [])),
            data.get("notes", ""),
            data.get("source_conversation"),
        ),
    )
    row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return row_id


def export_all():
    conn = get_db()
    recipes = conn.execute(
        "SELECT title, category, prep_time, cook_time, portion_count, "
        "ingredients, directions, notes, source_conversation "
        "FROM recipe_cards ORDER BY title"
    ).fetchall()
    tips = conn.execute(
        "SELECT title, category, items, notes, source_conversation "
        "FROM food_tips ORDER BY title"
    ).fetchall()
    conn.close()

    recipe_list = []
    for r in recipes:
        recipe_list.append({
            "title": r["title"],
            "category": r["category"],
            "prep_time": r["prep_time"],
            "cook_time": r["cook_time"],
            "portion_count": r["portion_count"],
            "ingredients": json.loads(r["ingredients"]) if r["ingredients"] else [],
            "directions": json.loads(r["directions"]) if r["directions"] else [],
            "notes": r["notes"],
            "source_conversation": r["source_conversation"],
        })

    tip_list = []
    for t in tips:
        tip_list.append({
            "title": t["title"],
            "category": t["category"],
            "items": json.loads(t["items"]) if t["items"] else [],
            "notes": t["notes"],
            "source_conversation": t["source_conversation"],
        })

    return recipe_list, tip_list


def search(query):
    conn = get_db()
    q = f"%{query}%"
    recipes = conn.execute(
        "SELECT id, title, category, prep_time, cook_time, portion_count, "
        "ingredients, notes FROM recipe_cards "
        "WHERE title LIKE ? OR ingredients LIKE ? OR notes LIKE ? "
        "ORDER BY title",
        (q, q, q),
    ).fetchall()
    tips = conn.execute(
        "SELECT id, title, category, items, notes FROM food_tips "
        "WHERE title LIKE ? OR items LIKE ? OR notes LIKE ? "
        "ORDER BY title",
        (q, q, q),
    ).fetchall()
    conn.close()
    return recipes, tips
