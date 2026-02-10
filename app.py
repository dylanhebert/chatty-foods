import json

from flask import Flask, render_template, request, send_from_directory

import db

app = Flask(__name__)


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


@app.route("/robots.txt")
def robots():
    return send_from_directory(app.static_folder, "robots.txt")


if __name__ == "__main__":
    db.init_db()
    db.sync_all()
    app.run(debug=True)
