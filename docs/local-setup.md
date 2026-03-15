# Local Development Setup

## Prerequisites
- Docker Desktop
- Python 3.12+
- Node.js 20+

## Start infrastructure
```bash
cd infrastructure/docker
docker-compose up -d
# postgres on :5432, redis on :6379
```

## Start backend
```bash
cd apps/api
cp ../../.env.example .env
# edit .env — add your OPENAI_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload
# API on http://localhost:8000
# Docs on http://localhost:8000/docs
```

## Start frontend
```bash
cd apps/web
npm install
npm run dev
# UI on http://localhost:3000
```

## Verify
- http://localhost:8000/health → {"status":"ok"}
- http://localhost:3000/workspace → workspace UI
- http://localhost:3000/r/test-slug → landing (404 until data exists)
