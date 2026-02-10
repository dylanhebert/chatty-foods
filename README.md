# Chatty Foods

A minimal web app for browsing recipes and food tips extracted from AI cooking conversations.

## Tech Stack

- **Flask** - Python web framework
- **SQLite** - Local database
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

Upload recipes and tips via the API:

```bash
curl -X POST http://localhost:5000/api/upload \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{"title": "Crispy Chicken", "category": "chicken", "ingredients": [...], "directions": [...]}'
```

Requires two environment variables. Create a `.env` file in the project root:

```
API_TOKEN=your-secret-token-here
SECRET_KEY=your-secret-key-here
```

- `API_TOKEN` — Bearer token for API requests, also the admin login password
- `SECRET_KEY` — Used by Flask to sign session cookies (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)

See `CLAUDE.md` for the full JSON schema.

## Admin Editing

Log in at `/login` with the admin password (`API_TOKEN`) to edit recipes and tips directly from their detail pages. Sessions persist for 30 days.

## API

Token-protected endpoints for uploading, reading, and exporting data:

- `POST /api/upload` — Add a recipe or tip (auto-detected from fields)
- `GET /api/recipes` — List all recipes
- `GET /api/recipes/<id>` — Get a single recipe
- `GET /api/tips` — List all tips
- `GET /api/tips/<id>` — Get a single tip
- `GET /api/export` — Export the full database as JSON
