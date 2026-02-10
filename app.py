import json
import os
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory

import db

load_dotenv()

app = Flask(__name__)

API_TOKEN = os.environ.get("API_TOKEN", "")


def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not API_TOKEN:
            return jsonify({"error": "API token not configured"}), 503
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {API_TOKEN}":
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


@app.route("/")
def index():
    recipe_count, tip_count = db.get_counts()
    recipe_categories = db.get_recipe_categories()
    tip_categories = db.get_tip_categories()
    return render_template(
        "index.html",
        recipe_count=recipe_count,
        tip_count=tip_count,
        recipe_categories=recipe_categories,
        tip_categories=tip_categories,
    )


@app.route("/recipes")
def recipes():
    category = request.args.get("category")
    rows = db.get_recipes(category)
    categories = db.get_recipe_categories()
    return render_template(
        "recipes.html",
        recipes=rows,
        categories=categories,
        active_category=category,
    )


@app.route("/recipes/<int:recipe_id>")
def recipe(recipe_id):
    row = db.get_recipe(recipe_id)
    if not row:
        return "Recipe not found", 404
    ingredients = json.loads(row["ingredients"])
    directions = json.loads(row["directions"])
    return render_template(
        "recipe.html",
        recipe=row,
        ingredients=ingredients,
        directions=directions,
    )


@app.route("/tips")
def tips():
    category = request.args.get("category")
    rows = db.get_tips(category)
    categories = db.get_tip_categories()
    # Add item count to each row
    tips_with_counts = []
    for row in rows:
        items = json.loads(row["items"])
        tips_with_counts.append({
            "id": row["id"],
            "title": row["title"],
            "category": row["category"],
            "item_count": len(items),
        })
    return render_template(
        "tips.html",
        tips=tips_with_counts,
        categories=categories,
        active_category=category,
    )


@app.route("/tips/<int:tip_id>")
def tip(tip_id):
    row = db.get_tip(tip_id)
    if not row:
        return "Tip not found", 404
    items = json.loads(row["items"])
    return render_template("tip.html", tip=row, items=items)


@app.route("/search")
def search_results():
    query = request.args.get("q", "").strip()
    if not query:
        return render_template("search.html", query="", recipes=[], tips=[])
    recipes, tips = db.search(query)
    return render_template(
        "search.html", query=query, recipes=recipes, tips=tips
    )


@app.route("/about")
def about():
    return render_template("about.html")


# --- API routes ---


def _clean_recipe(row):
    return {
        "title": row["title"],
        "category": row["category"],
        "prep_time": row["prep_time"],
        "cook_time": row["cook_time"],
        "portion_count": row["portion_count"],
        "ingredients": json.loads(row["ingredients"]) if row["ingredients"] else [],
        "directions": json.loads(row["directions"]) if row["directions"] else [],
        "notes": row["notes"],
        "source_conversation": row["source_conversation"],
    }


def _clean_tip(row):
    return {
        "title": row["title"],
        "category": row["category"],
        "items": json.loads(row["items"]) if row["items"] else [],
        "notes": row["notes"],
        "source_conversation": row["source_conversation"],
    }


@app.route("/api/upload", methods=["POST"])
@require_token
def api_upload():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    # Auto-detect type
    is_recipe = "ingredients" in data or "directions" in data
    is_tip = "items" in data

    if is_recipe and is_tip:
        return jsonify({"error": "Ambiguous: body has both recipe and tip fields"}), 400
    if not is_recipe and not is_tip:
        return jsonify({"error": "Could not detect type: need 'ingredients'/'directions' for recipe or 'items' for tip"}), 400

    if is_recipe:
        missing = [f for f in ("title", "category", "ingredients", "directions") if f not in data]
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
        row_id = db.insert_recipe(data)
        return jsonify({"type": "recipe", "id": row_id}), 201
    else:
        missing = [f for f in ("title", "category", "items") if f not in data]
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
        row_id = db.insert_tip(data)
        return jsonify({"type": "tip", "id": row_id}), 201


@app.route("/api/recipes")
@require_token
def api_recipes():
    recipes, _ = db.export_all()
    return jsonify(recipes)


@app.route("/api/recipes/<int:recipe_id>")
@require_token
def api_recipe(recipe_id):
    row = db.get_recipe(recipe_id)
    if not row:
        return jsonify({"error": "Recipe not found"}), 404
    return jsonify(_clean_recipe(row))


@app.route("/api/tips")
@require_token
def api_tips():
    _, tips = db.export_all()
    return jsonify(tips)


@app.route("/api/tips/<int:tip_id>")
@require_token
def api_tip(tip_id):
    row = db.get_tip(tip_id)
    if not row:
        return jsonify({"error": "Tip not found"}), 404
    return jsonify(_clean_tip(row))


@app.route("/api/export")
@require_token
def api_export():
    recipes, tips = db.export_all()
    return jsonify({"recipes": recipes, "tips": tips})


@app.route("/robots.txt")
def robots():
    return send_from_directory(app.static_folder, "robots.txt")


if __name__ == "__main__":
    db.init_db()
    db.sync_all()
    app.run(debug=True)
