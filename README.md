# Landing Reply — Monorepo

AI-powered freelance reply generator with personalized micro landing pages.

## Quick Start

```bash
cp .env.example .env
docker-compose -f infrastructure/docker/docker-compose.yml up -d
cd apps/api && pip install -r requirements.txt && uvicorn app.main:app --reload
cd apps/web && npm install && npm run dev
```
