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
- **source_type**: `ai` (from AI conversation, default), `personal` (own creation), `cookbook` (from a cookbook), `online` (from a website/online source)
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

## Extraction Prompt

Paste this at the end of a Claude cooking conversation to get copy-pasteable JSON for the admin upload page. This prompt is also available on the `/admin` page with a copy button.

```
Extract every recipe and food tip from this conversation as JSON. Output each as its own code block so I can copy them one at a time.

Recipe format:
{
  "title": "Descriptive recipe name",
  "category": "chicken|seafood|sushi|dessert|coffee|sauce|breakfast|side|drink|beef|pork|pasta",
  "prep_time": 5,
  "cook_time": 25,
  "portion_count": "4 servings",
  "ingredients": [
    {"name": "chicken thighs", "amount": "4"},
    {"name": "soy sauce", "amount": "2 tbsp"}
  ],
  "directions": ["Step 1.", "Step 2."],
  "notes": "Any extra tips or context.",
  "source_type": "ai",
  "source_conversation": "Brief_Conversation_Topic_YYYY-MM-DD"
}

Tip format:
{
  "title": "Descriptive tip name",
  "category": "pairing|storage|substitution|technique|tip",
  "items": [
    {"name": "Item or technique name", "details": "Explanation or details"}
  ],
  "notes": "Any extra context.",
  "source_type": "ai",
  "source_conversation": "Brief_Conversation_Topic_YYYY-MM-DD"
}

- prep_time/cook_time: integers in minutes
- portion_count: string — "4 servings", "12 cookies", "2 cups", etc.
- ingredients.amount: string with quantity and unit — "2 tbsp", "1 lb", "4", "to taste"
- source_conversation: short summary of conversation topic + today's date, shared across all items from the same conversation

Rules: skip chit-chat — only extract actionable recipes and tips. Create a new category if nothing fits.
```

<!-- Reference for humans, not instructions for Claude -->
## Workflow Reference

1. **Cook** - Chat with Claude on mobile while prepping/cooking
2. **Extract** - Paste the extraction prompt above at the end of the conversation
3. **Upload** - Copy each JSON block, go to `/admin`, paste into the upload textarea
4. **Review** - Edit from the detail page if anything needs tweaking
