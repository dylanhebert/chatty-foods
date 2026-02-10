# Chatty Foods

This project stores recipe cards and food tips in a SQLite database, served by a Flask web app. Conversations happen on Claude mobile while cooking, then get pasted here to be extracted and uploaded via the API.

## Ingesting a Conversation

When a conversation is pasted from Claude mobile/desktop:

1. Read through the entire conversation
2. Identify all recipes discussed (ingredients, directions, cook times, etc.)
3. Identify all food tips (pairings, storage advice, substitutions, techniques)
4. Upload each recipe and tip via `POST /api/upload` (see schemas below)
5. If a conversation has multiple recipes, upload each one separately
6. Skip general chit-chat - only extract actionable recipes and tips
7. Report what was uploaded for review

## Uploading a Recipe Card

`POST /api/upload` with this JSON body:

```json
{
  "title": "Crispy Cranberry-Balsamic Skillet Chicken Thighs",
  "category": "chicken",
  "prep_time": 5,
  "cook_time": 25,
  "portion_count": "4 servings",
  "ingredients": [
    {"name": "chicken thighs", "amount": "4"},
    {"name": "cranberry balsamic vinegar", "amount": "2 tbsp"}
  ],
  "directions": [
    "Pat chicken dry and season with salt and pepper.",
    "Place skin-side down in a cold cast iron skillet."
  ],
  "notes": "Start skin-side down in a cold pan for crispiest skin.",
  "source_conversation": "Experimenting_with_chicken_glazes_2026-02-09",
  "source_type": "ai"
}
```

- **title**: Descriptive of the specific recipe, not the conversation topic
- **prep_time/cook_time**: integers in minutes
- **portion_count**: string (e.g., "4 servings", "24 cookies")
- **source_conversation**: `<Brief_conversation_summary>_<YYYY-MM-DD>` - multiple recipes from the same conversation share this value
- **source_type**: `ai` (from AI conversation, default), `personal` (own creation), `cookbook` (from a cookbook)
- **Recipe categories**: chicken, seafood, sushi, dessert, coffee, sauce, breakfast, side, drink, beef, pork, pasta (add new categories if needed)

## Uploading a Food Tip

`POST /api/upload` with this JSON body:

```json
{
  "title": "Hoisin Sauce Substitutes",
  "category": "substitution",
  "items": [
    {"name": "Soy sauce + peanut butter + honey", "details": "Mix equal parts for a quick substitute"},
    {"name": "Teriyaki sauce", "details": "Similar sweetness, slightly different flavor profile"}
  ],
  "notes": "Hoisin is thick and sweet - any substitute should match that consistency.",
  "source_conversation": "Experimenting_with_chicken_glazes_2026-02-09",
  "source_type": "ai"
}
```

- **title**: Descriptive of the specific tip, not the conversation topic
- **source_conversation**: Same format as recipe cards
- **Tip categories**: pairing, storage, substitution, technique, tip

## Authentication

All API requests require a Bearer token:

```
Authorization: Bearer <API_TOKEN>
```

The token is set via the `API_TOKEN` environment variable (`.env` file locally, systemd service on the server).

<!-- Reference for humans, not instructions for Claude -->
## Workflow Reference

1. **Cook** - Chat with Claude on mobile (Recipes project) while prepping/cooking
2. **Sync** - Open the same conversation on Claude desktop (it syncs automatically)
3. **Extract** - Copy the conversation, paste it into Claude Code in this repo, optionally add "extract recipes from this"
4. **Review** - Claude uploads via the API and reports what was saved
