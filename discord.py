import logging
import os

import requests

log = logging.getLogger(__name__)

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
SITE_URL = os.getenv("SITE_URL", "").rstrip("/")

EMBED_COLOR = 0x10B981  # emerald-500


def notify_new_recipe(data, row_id):
    if not DISCORD_WEBHOOK_URL:
        return
    url = f"{SITE_URL}/recipes/{row_id}"
    fields = [
        {"name": "Category", "value": data.get("category", "—").capitalize(), "inline": True},
    ]
    cook = data.get("cook_time")
    if cook:
        fields.append({"name": "Cook time", "value": f"{cook} min", "inline": True})
    portion = data.get("portion_count")
    if portion:
        fields.append({"name": "Serves", "value": str(portion), "inline": True})
    ingredients = data.get("ingredients", [])
    if ingredients:
        fields.append({"name": "Ingredients", "value": f"{len(ingredients)} items", "inline": True})
    _send({
        "embeds": [{
            "title": data.get("title", "Untitled"),
            "url": url,
            "description": "New recipe added",
            "color": EMBED_COLOR,
            "fields": fields,
        }],
    })


def notify_new_tip(data, row_id):
    if not DISCORD_WEBHOOK_URL:
        return
    url = f"{SITE_URL}/tips/{row_id}"
    fields = [
        {"name": "Category", "value": data.get("category", "—").capitalize(), "inline": True},
    ]
    items = data.get("items", [])
    if items:
        fields.append({"name": "Items", "value": str(len(items)), "inline": True})
    _send({
        "embeds": [{
            "title": data.get("title", "Untitled"),
            "url": url,
            "description": "New food tip added",
            "color": EMBED_COLOR,
            "fields": fields,
        }],
    })


def _send(payload):
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
    except Exception:
        log.exception("Discord webhook failed")
