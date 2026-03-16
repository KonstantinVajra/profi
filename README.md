# Landing Reply

AI-powered freelance reply generator with personalized micro landing pages.

**Core flow:** order input → parsed order → 3 reply variants → landing page → public URL → dialogue suggestions

## Quick local start (no Docker required)

```bash
# 1. Backend
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then set OPENAI_API_KEY in .env
uvicorn app.main:app --reload
# → http://localhost:8000/docs

# 2. Frontend (new terminal)
cd apps/web
npm install
cp .env.local.example .env.local   # already has correct defaults
npm run dev
# → http://localhost:3000/workspace
```

SQLite is used by default locally — no database setup needed.

## Deploy to VPS (Stage A)

See `docs/deploy.md` for the full VPS + PostgreSQL deployment guide.

## Project structure

```
apps/
  api/          FastAPI backend
  web/          Next.js frontend
packages/
  prompts/      AI prompt templates (.txt)
infrastructure/
  nginx/        Nginx reverse proxy config (Stage B)
  systemd/      Systemd unit files (Stage B)
  scripts/      Deploy helper scripts (Stage B)
```
