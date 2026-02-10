# Chatty Foods

A minimal web app for browsing recipes and food tips extracted from AI cooking conversations.

## Tech Stack

- **Flask** - Python web framework
- **SQLite** - Local database (auto-synced from JSON files)
- **Tailwind CSS** - Styling via CDN (dark/light mode)

## Setup

```bash
git clone <repo-url>
cd chatty-foods
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Visit `http://localhost:5000`

## Adding Data

Drop JSON files into the appropriate folder:

- `data/recipe_cards/` - Recipe files
- `data/food_tips/` - Tip files

Restart the app and the new data will appear automatically. See `CLAUDE.md` for JSON schema details.
