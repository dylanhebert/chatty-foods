import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "chatty_foods.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


_RECIPE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS recipe_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        prep_time INTEGER,
        cook_time INTEGER,
        portion_count TEXT,
        ingredients TEXT,
        directions TEXT,
        notes TEXT,
        source_conversation TEXT,
        created_at TEXT,
        source_type TEXT DEFAULT 'ai',
        highlight INTEGER DEFAULT 0
    )
"""

_TIP_SCHEMA = """
    CREATE TABLE IF NOT EXISTS food_tips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        items TEXT,
        notes TEXT,
        source_conversation TEXT,
        created_at TEXT,
        source_type TEXT DEFAULT 'ai',
        highlight INTEGER DEFAULT 0
    )
"""


def _has_column(conn, table, column):
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(c["name"] == column for c in cols)


def init_db():
    conn = get_db()
    conn.execute(_RECIPE_SCHEMA)
    conn.execute(_TIP_SCHEMA)
    # Migrate existing tables
    for table in ("recipe_cards", "food_tips"):
        if not _has_column(conn, table, "created_at"):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN created_at TEXT")
        if not _has_column(conn, table, "source_type"):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN source_type TEXT DEFAULT 'ai'")
        if not _has_column(conn, table, "highlight"):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN highlight INTEGER DEFAULT 0")
    conn.commit()
    conn.close()


# Query helpers

def get_recipes(category=None):
    conn = get_db()
    if category:
        rows = conn.execute(
            "SELECT id, title, category, prep_time, cook_time, portion_count, source_type, highlight, created_at "
            "FROM recipe_cards WHERE category = ? ORDER BY highlight DESC, title",
            (category,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, category, prep_time, cook_time, portion_count, source_type, highlight, created_at "
            "FROM recipe_cards ORDER BY highlight DESC, title"
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
            "SELECT id, title, category, items, source_type, highlight, created_at FROM food_tips "
            "WHERE category = ? ORDER BY highlight DESC, title",
            (category,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, category, items, source_type, highlight, created_at FROM food_tips "
            "ORDER BY highlight DESC, title"
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


def get_highlighted_recipes():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, category, created_at FROM recipe_cards "
        "WHERE highlight = 1 ORDER BY title"
    ).fetchall()
    conn.close()
    return rows


def get_highlighted_tips():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, category, created_at FROM food_tips "
        "WHERE highlight = 1 ORDER BY title"
    ).fetchall()
    conn.close()
    return rows


def get_recent_recipes(days=7):
    conn = get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        "SELECT id, title, category, created_at FROM recipe_cards "
        "WHERE created_at >= ? ORDER BY created_at DESC",
        (cutoff,),
    ).fetchall()
    conn.close()
    return rows


def get_recent_tips(days=7):
    conn = get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        "SELECT id, title, category, created_at FROM food_tips "
        "WHERE created_at >= ? ORDER BY created_at DESC",
        (cutoff,),
    ).fetchall()
    conn.close()
    return rows


def get_by_conversation(source_conversation):
    conn = get_db()
    recipes = conn.execute(
        "SELECT id, title, category, prep_time, cook_time, portion_count, source_type, highlight, created_at "
        "FROM recipe_cards WHERE source_conversation = ? ORDER BY highlight DESC, title",
        (source_conversation,),
    ).fetchall()
    tips = conn.execute(
        "SELECT id, title, category, items, source_type, highlight, created_at "
        "FROM food_tips WHERE source_conversation = ? ORDER BY highlight DESC, title",
        (source_conversation,),
    ).fetchall()
    conn.close()
    return recipes, tips


def get_counts():
    conn = get_db()
    recipe_count = conn.execute("SELECT COUNT(*) FROM recipe_cards").fetchone()[0]
    tip_count = conn.execute("SELECT COUNT(*) FROM food_tips").fetchone()[0]
    conn.close()
    return recipe_count, tip_count


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def insert_recipe(data):
    conn = get_db()
    conn.execute(
        "INSERT INTO recipe_cards (title, category, prep_time, cook_time, "
        "portion_count, ingredients, directions, notes, source_conversation, "
        "created_at, source_type, highlight) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
            data.get("created_at") or _now(),
            data.get("source_type", "ai"),
            1 if data.get("highlight") else 0,
        ),
    )
    row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return row_id


def insert_tip(data):
    conn = get_db()
    conn.execute(
        "INSERT INTO food_tips (title, category, items, notes, source_conversation, "
        "created_at, source_type, highlight) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            data["title"],
            data["category"],
            json.dumps(data.get("items", [])),
            data.get("notes", ""),
            data.get("source_conversation"),
            data.get("created_at") or _now(),
            data.get("source_type", "ai"),
            1 if data.get("highlight") else 0,
        ),
    )
    row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return row_id


def update_recipe(recipe_id, data):
    conn = get_db()
    conn.execute(
        "UPDATE recipe_cards SET title=?, category=?, prep_time=?, cook_time=?, "
        "portion_count=?, ingredients=?, directions=?, notes=?, source_type=?, "
        "source_conversation=?, highlight=? WHERE id=?",
        (
            data["title"],
            data["category"],
            data.get("prep_time", 0),
            data.get("cook_time", 0),
            data.get("portion_count", ""),
            json.dumps(data.get("ingredients", [])),
            json.dumps(data.get("directions", [])),
            data.get("notes", ""),
            data.get("source_type", "ai"),
            data.get("source_conversation", ""),
            data.get("highlight", 0),
            recipe_id,
        ),
    )
    conn.commit()
    conn.close()


def update_tip(tip_id, data):
    conn = get_db()
    conn.execute(
        "UPDATE food_tips SET title=?, category=?, items=?, notes=?, source_type=?, "
        "source_conversation=?, highlight=? WHERE id=?",
        (
            data["title"],
            data["category"],
            json.dumps(data.get("items", [])),
            data.get("notes", ""),
            data.get("source_type", "ai"),
            data.get("source_conversation", ""),
            data.get("highlight", 0),
            tip_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_recipe(recipe_id):
    conn = get_db()
    conn.execute("DELETE FROM recipe_cards WHERE id=?", (recipe_id,))
    conn.commit()
    conn.close()


def delete_tip(tip_id):
    conn = get_db()
    conn.execute("DELETE FROM food_tips WHERE id=?", (tip_id,))
    conn.commit()
    conn.close()


def export_all():
    conn = get_db()
    recipes = conn.execute(
        "SELECT title, category, prep_time, cook_time, portion_count, "
        "ingredients, directions, notes, source_conversation, created_at, source_type, highlight "
        "FROM recipe_cards ORDER BY title"
    ).fetchall()
    tips = conn.execute(
        "SELECT title, category, items, notes, source_conversation, created_at, source_type, highlight "
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
            "created_at": r["created_at"],
            "source_type": r["source_type"] or "ai",
            "highlight": bool(r["highlight"]),
        })

    tip_list = []
    for t in tips:
        tip_list.append({
            "title": t["title"],
            "category": t["category"],
            "items": json.loads(t["items"]) if t["items"] else [],
            "notes": t["notes"],
            "source_conversation": t["source_conversation"],
            "created_at": t["created_at"],
            "source_type": t["source_type"] or "ai",
            "highlight": bool(t["highlight"]),
        })

    return recipe_list, tip_list


def search(query):
    conn = get_db()
    q = f"%{query}%"
    recipes = conn.execute(
        "SELECT id, title, category, prep_time, cook_time, portion_count, "
        "ingredients, notes, source_type, highlight, created_at FROM recipe_cards "
        "WHERE title LIKE ? OR ingredients LIKE ? OR notes LIKE ? "
        "ORDER BY highlight DESC, title",
        (q, q, q),
    ).fetchall()
    tips = conn.execute(
        "SELECT id, title, category, items, notes, source_type, highlight, created_at FROM food_tips "
        "WHERE title LIKE ? OR items LIKE ? OR notes LIKE ? "
        "ORDER BY highlight DESC, title",
        (q, q, q),
    ).fetchall()
    conn.close()
    return recipes, tips
