import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Flask, jsonify, redirect, render_template, request,
    send_from_directory, session, url_for,
)

import db
import discord

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "")
app.permanent_session_lifetime = timedelta(days=30)

API_TOKEN = os.environ.get("API_TOKEN", "")

SOURCE_TYPES = [("ai", "AI"), ("personal", "Personal"), ("cookbook", "Cookbook")]

NEW_DAYS = 7


def _is_new(created_at):
    if not created_at:
        return False
    try:
        dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).days < NEW_DAYS
    except ValueError:
        return False


app.jinja_env.globals["is_new"] = _is_new


# --- Auth decorators ---


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


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def check_csrf(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == "POST":
            if request.form.get("csrf_token") != session.get("csrf_token"):
                return "Invalid request", 403
        return f(*args, **kwargs)
    return decorated


@app.before_request
def ensure_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)


@app.context_processor
def inject_globals():
    return {
        "is_admin": session.get("is_admin", False),
        "csrf_token": session.get("csrf_token", ""),
    }


# --- Auth routes ---


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("is_admin"):
        return redirect(url_for("index"))
    if request.method == "GET":
        return render_template("login.html")
    password = request.form.get("password", "")
    if not API_TOKEN:
        return render_template("login.html", error="Admin login not configured")
    if hmac.compare_digest(password, API_TOKEN):
        session.permanent = True
        session["is_admin"] = True
        return redirect(url_for("index"))
    return render_template("login.html", error="Incorrect password")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin")
@require_admin
def admin():
    return render_template("admin.html")


@app.route("/admin/upload", methods=["POST"])
@require_admin
@check_csrf
def admin_upload():
    raw = request.form.get("json_data", "").strip()
    if not raw:
        return render_template("admin.html", upload_error="No JSON provided")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return render_template("admin.html", upload_error=f"Invalid JSON: {e}")

    is_recipe = "ingredients" in data or "directions" in data
    is_tip = "items" in data

    valid_source_types = ("ai", "personal", "cookbook")
    if "source_type" in data and data["source_type"] not in valid_source_types:
        return render_template("admin.html", upload_error=f"Invalid source_type: must be one of {', '.join(valid_source_types)}")

    if is_recipe and is_tip:
        return render_template("admin.html", upload_error="Ambiguous: body has both recipe and tip fields")
    if not is_recipe and not is_tip:
        return render_template("admin.html", upload_error="Could not detect type: need 'ingredients'/'directions' for recipe or 'items' for tip")

    if is_recipe:
        missing = [f for f in ("title", "category", "ingredients", "directions") if f not in data]
        if missing:
            return render_template("admin.html", upload_error=f"Missing required fields: {', '.join(missing)}")
        row_id = db.insert_recipe(data)
        discord.notify_new_recipe(data, row_id)
        return render_template("admin.html", upload_success={
            "message": f"Recipe created: {data['title']}",
            "url": url_for("recipe", recipe_id=row_id),
        })
    else:
        missing = [f for f in ("title", "category", "items") if f not in data]
        if missing:
            return render_template("admin.html", upload_error=f"Missing required fields: {', '.join(missing)}")
        row_id = db.insert_tip(data)
        discord.notify_new_tip(data, row_id)
        return render_template("admin.html", upload_success={
            "message": f"Tip created: {data['title']}",
            "url": url_for("tip", tip_id=row_id),
        })


@app.route("/admin/export")
@require_admin
def admin_export():
    recipes, tips = db.export_all()
    data = json.dumps({"recipes": recipes, "tips": tips}, indent=2)
    return app.response_class(
        data,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=chatty-foods-export.json"},
    )


# --- Page routes ---


@app.route("/")
def index():
    recipe_count, tip_count = db.get_counts()
    recipe_categories = db.get_recipe_categories()
    tip_categories = db.get_tip_categories()
    highlighted_recipes = db.get_highlighted_recipes()
    highlighted_tips = db.get_highlighted_tips()
    recent_recipes = db.get_recent_recipes(NEW_DAYS)
    recent_tips = db.get_recent_tips(NEW_DAYS)
    return render_template(
        "index.html",
        recipe_count=recipe_count,
        tip_count=tip_count,
        recipe_categories=recipe_categories,
        tip_categories=tip_categories,
        highlighted_recipes=highlighted_recipes,
        highlighted_tips=highlighted_tips,
        recent_recipes=recent_recipes,
        recent_tips=recent_tips,
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


def _format_date(dt_string):
    if not dt_string:
        return None
    try:
        dt = datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%b %d, %Y").replace(" 0", " ")
    except ValueError:
        return None


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
        date_display=_format_date(row["created_at"]),
    )


@app.route("/tips")
def tips():
    category = request.args.get("category")
    rows = db.get_tips(category)
    categories = db.get_tip_categories()
    tips_with_counts = []
    for row in rows:
        items = json.loads(row["items"])
        tips_with_counts.append({
            "id": row["id"],
            "title": row["title"],
            "category": row["category"],
            "item_count": len(items),
            "source_type": row["source_type"] or "ai",
            "highlight": row["highlight"],
            "created_at": row["created_at"],
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
    return render_template(
        "tip.html", tip=row, items=items, date_display=_format_date(row["created_at"])
    )


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


@app.route("/api-docs")
def api_docs():
    return render_template("api.html")


# --- Create routes ---


@app.route("/recipes/new", methods=["GET", "POST"])
@require_admin
@check_csrf
def new_recipe():
    if request.method == "GET":
        all_categories = sorted(r["category"] for r in db.get_recipe_categories())
        return render_template(
            "edit_recipe.html",
            recipe={"title": "", "category": "", "prep_time": 0, "cook_time": 0, "portion_count": "", "notes": "", "source_type": "ai", "source_conversation": "", "highlight": 0},
            ingredients=[],
            directions=[],
            recipe_categories=all_categories,
            source_types=SOURCE_TYPES,
            mode="create",
        )

    data = {
        "title": request.form.get("title", "").strip(),
        "category": request.form.get("category", ""),
        "prep_time": int(request.form.get("prep_time") or 0),
        "cook_time": int(request.form.get("cook_time") or 0),
        "portion_count": request.form.get("portion_count", "").strip(),
        "notes": request.form.get("notes", "").strip(),
        "source_type": request.form.get("source_type", "ai"),
        "source_conversation": request.form.get("source_conversation", "").strip(),
        "highlight": 1 if request.form.get("highlight") else 0,
    }

    names = request.form.getlist("ingredient_name")
    amounts = request.form.getlist("ingredient_amount")
    data["ingredients"] = [
        {"name": n.strip(), "amount": a.strip()}
        for n, a in zip(names, amounts) if n.strip()
    ]
    data["directions"] = [
        s.strip() for s in request.form.getlist("direction") if s.strip()
    ]

    row_id = db.insert_recipe(data)
    discord.notify_new_recipe(data, row_id)
    return redirect(url_for("recipe", recipe_id=row_id))


@app.route("/tips/new", methods=["GET", "POST"])
@require_admin
@check_csrf
def new_tip():
    if request.method == "GET":
        all_categories = sorted(r["category"] for r in db.get_tip_categories())
        return render_template(
            "edit_tip.html",
            tip={"title": "", "category": "", "notes": "", "source_type": "ai", "source_conversation": "", "highlight": 0},
            items=[],
            tip_categories=all_categories,
            source_types=SOURCE_TYPES,
            mode="create",
        )

    data = {
        "title": request.form.get("title", "").strip(),
        "category": request.form.get("category", ""),
        "notes": request.form.get("notes", "").strip(),
        "source_type": request.form.get("source_type", "ai"),
        "source_conversation": request.form.get("source_conversation", "").strip(),
        "highlight": 1 if request.form.get("highlight") else 0,
    }

    names = request.form.getlist("item_name")
    details = request.form.getlist("item_details")
    data["items"] = [
        {"name": n.strip(), "details": d.strip()}
        for n, d in zip(names, details) if n.strip()
    ]

    row_id = db.insert_tip(data)
    discord.notify_new_tip(data, row_id)
    return redirect(url_for("tip", tip_id=row_id))


# --- Edit routes ---


@app.route("/recipes/<int:recipe_id>/edit", methods=["GET", "POST"])
@require_admin
@check_csrf
def edit_recipe(recipe_id):
    row = db.get_recipe(recipe_id)
    if not row:
        return "Recipe not found", 404

    if request.method == "GET":
        ingredients = json.loads(row["ingredients"]) if row["ingredients"] else []
        directions = json.loads(row["directions"]) if row["directions"] else []
        all_categories = sorted(r["category"] for r in db.get_recipe_categories())
        return render_template(
            "edit_recipe.html",
            recipe=row,
            ingredients=ingredients,
            directions=directions,
            recipe_categories=all_categories,
            source_types=SOURCE_TYPES,
        )

    # POST — collect form data
    data = {
        "title": request.form.get("title", "").strip(),
        "category": request.form.get("category", ""),
        "prep_time": int(request.form.get("prep_time") or 0),
        "cook_time": int(request.form.get("cook_time") or 0),
        "portion_count": request.form.get("portion_count", "").strip(),
        "notes": request.form.get("notes", "").strip(),
        "source_type": request.form.get("source_type", "ai"),
        "source_conversation": request.form.get("source_conversation", "").strip(),
        "highlight": 1 if request.form.get("highlight") else 0,
    }

    # Collect ingredient rows
    names = request.form.getlist("ingredient_name")
    amounts = request.form.getlist("ingredient_amount")
    data["ingredients"] = [
        {"name": n.strip(), "amount": a.strip()}
        for n, a in zip(names, amounts) if n.strip()
    ]

    # Collect direction steps
    data["directions"] = [
        s.strip() for s in request.form.getlist("direction") if s.strip()
    ]

    db.update_recipe(recipe_id, data)
    return redirect(url_for("recipe", recipe_id=recipe_id))


@app.route("/tips/<int:tip_id>/edit", methods=["GET", "POST"])
@require_admin
@check_csrf
def edit_tip(tip_id):
    row = db.get_tip(tip_id)
    if not row:
        return "Tip not found", 404

    if request.method == "GET":
        items = json.loads(row["items"]) if row["items"] else []
        all_categories = sorted(r["category"] for r in db.get_tip_categories())
        return render_template(
            "edit_tip.html",
            tip=row,
            items=items,
            tip_categories=all_categories,
            source_types=SOURCE_TYPES,
        )

    # POST — collect form data
    data = {
        "title": request.form.get("title", "").strip(),
        "category": request.form.get("category", ""),
        "notes": request.form.get("notes", "").strip(),
        "source_type": request.form.get("source_type", "ai"),
        "source_conversation": request.form.get("source_conversation", "").strip(),
        "highlight": 1 if request.form.get("highlight") else 0,
    }

    # Collect item rows
    names = request.form.getlist("item_name")
    details = request.form.getlist("item_details")
    data["items"] = [
        {"name": n.strip(), "details": d.strip()}
        for n, d in zip(names, details) if n.strip()
    ]

    db.update_tip(tip_id, data)
    return redirect(url_for("tip", tip_id=tip_id))


@app.route("/recipes/<int:recipe_id>/delete", methods=["POST"])
@require_admin
@check_csrf
def delete_recipe(recipe_id):
    db.delete_recipe(recipe_id)
    return redirect(url_for("recipes"))


@app.route("/tips/<int:tip_id>/delete", methods=["POST"])
@require_admin
@check_csrf
def delete_tip(tip_id):
    db.delete_tip(tip_id)
    return redirect(url_for("tips"))


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
        "created_at": row["created_at"],
        "source_type": row["source_type"] or "ai",
        "highlight": bool(row["highlight"]),
    }


def _clean_tip(row):
    return {
        "title": row["title"],
        "category": row["category"],
        "items": json.loads(row["items"]) if row["items"] else [],
        "notes": row["notes"],
        "source_conversation": row["source_conversation"],
        "created_at": row["created_at"],
        "source_type": row["source_type"] or "ai",
        "highlight": bool(row["highlight"]),
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

    # Validate source_type if provided
    valid_source_types = ("ai", "personal", "cookbook")
    if "source_type" in data and data["source_type"] not in valid_source_types:
        return jsonify({"error": f"Invalid source_type: must be one of {', '.join(valid_source_types)}"}), 400

    if is_recipe and is_tip:
        return jsonify({"error": "Ambiguous: body has both recipe and tip fields"}), 400
    if not is_recipe and not is_tip:
        return jsonify({"error": "Could not detect type: need 'ingredients'/'directions' for recipe or 'items' for tip"}), 400

    if is_recipe:
        missing = [f for f in ("title", "category", "ingredients", "directions") if f not in data]
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
        row_id = db.insert_recipe(data)
        discord.notify_new_recipe(data, row_id)
        return jsonify({"type": "recipe", "id": row_id}), 201
    else:
        missing = [f for f in ("title", "category", "items") if f not in data]
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
        row_id = db.insert_tip(data)
        discord.notify_new_tip(data, row_id)
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
    app.run(debug=True)
