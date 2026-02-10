import json
import os
import sqlite3

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
        source_conversation TEXT
    )
"""

_TIP_SCHEMA = """
    CREATE TABLE IF NOT EXISTS food_tips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        items TEXT,
        notes TEXT,
        source_conversation TEXT
    )
"""


def init_db():
    conn = get_db()
    conn.execute(_RECIPE_SCHEMA)
    conn.execute(_TIP_SCHEMA)
    conn.commit()
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
