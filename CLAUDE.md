# Chatty Foods

This project stores recipe cards and food tips as JSON files. Conversations happen on Claude mobile while cooking, then get pasted here to be extracted into structured data.

## Ingesting a Conversation

When a conversation is pasted from Claude mobile/desktop:

1. Read through the entire conversation
2. Identify all recipes discussed (ingredients, directions, cook times, etc.)
3. Identify all food tips (pairings, storage advice, substitutions, techniques)
4. Create the appropriate JSON files in `data/recipe_cards/` and/or `data/food_tips/`
5. If a conversation has multiple recipes, create separate files for each
6. Skip general chit-chat - only extract actionable recipes and tips
7. Report what was created for review

## Adding a Recipe Card

Write to `data/recipe_cards/` using this format:

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
  "source_conversation": "Experimenting_with_chicken_glazes_2026-02-09"
}
```

- **File naming**: `lowercase_underscored_recipe_name.json` (based on the recipe title, not the conversation)
- **title**: Descriptive of the specific recipe, not the conversation topic
- **prep_time/cook_time**: integers in minutes
- **portion_count**: string (e.g., "4 servings", "24 cookies")
- **source_conversation**: `<Brief_conversation_summary>_<YYYY-MM-DD>` - multiple recipes from the same conversation share this value
- **Recipe categories**: chicken, seafood, sushi, dessert, coffee, sauce, breakfast, side, drink, beef, pork, pasta (add new categories if needed)

## Adding a Food Tip

Write to `data/food_tips/` using this format:

```json
{
  "title": "Hoisin Sauce Substitutes",
  "category": "substitution",
  "items": [
    {"name": "Soy sauce + peanut butter + honey", "details": "Mix equal parts for a quick substitute"},
    {"name": "Teriyaki sauce", "details": "Similar sweetness, slightly different flavor profile"}
  ],
  "notes": "Hoisin is thick and sweet - any substitute should match that consistency.",
  "source_conversation": "Experimenting_with_chicken_glazes_2026-02-09"
}
```

- **title**: Descriptive of the specific tip, not the conversation topic
- **source_conversation**: Same format as recipe cards
- **Tip categories**: pairing, storage, substitution, technique, tip

<!-- Reference for humans, not instructions for Claude -->
## Workflow Reference

1. **Cook** - Chat with Claude on mobile (Recipes project) while prepping/cooking
2. **Sync** - Open the same conversation on Claude desktop (it syncs automatically)
3. **Extract** - Copy the conversation, paste it into Claude Code in this repo, optionally add "extract recipes from this"
4. **Review** - Claude creates the JSON files and reports what was saved
