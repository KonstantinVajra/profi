# Local Development Setup

No Docker required. SQLite is used by default.

## Prerequisites

- Python 3.11+
- Node.js 20+
- An OpenAI API key

## Backend

```bash
cd apps/api

# Create and activate virtualenv
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure env
cp .env.example .env
# Open .env and set:
#   OPENAI_API_KEY=sk-your-real-key
# DATABASE_URL defaults to sqlite:///./app.db — no changes needed locally

# Start backend (tables are created automatically on first start)
uvicorn app.main:app --reload --port 8000
```

Verify:
- `http://localhost:8000/health` → `{"status":"ok"}`
- `http://localhost:8000/docs` → Swagger UI

## Frontend

```bash
cd apps/web
npm install

# .env.local already exists with correct local defaults:
#   NEXT_PUBLIC_API_URL=http://localhost:8000
#   NEXT_PUBLIC_SITE_URL=http://localhost:3000

npm run dev
```

Verify:
- `http://localhost:3000/workspace` → workspace UI
- `http://localhost:3000/r/some-slug` → public landing (404 until data exists)

## Manual smoke test

Using the Swagger UI at `http://localhost:8000/docs`:

```
1. POST /projects              → copy project_id
2. POST /orders/extract        → { "project_id": "...", "raw_text": "Фотограф на регистрацию 11 июня в СПб, бюджет 15000" }
3. POST /projects/{id}/landing/generate   → copy slug from response
4. POST /projects/{id}/replies/generate   → { "landing_url": "http://localhost:3000/r/{slug}" }
5. GET  /public/landings/{slug}           → verify landing JSON returned
6. Browser: http://localhost:3000/r/{slug} → landing page renders
7. POST /projects/{id}/dialogue/reply     → { "message_text": "Сколько фото будет?", "source_channel": "profi" }
```

## Notes

- SQLite DB file is created at `apps/api/app.db` on first start
- To reset: delete `app.db` and restart the backend
- Redis is not required — it's not used in the current MVP
- Alembic migrations are in the repo but not used locally — `create_all()` handles table creation
