from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import projects, orders, replies, landings, dialogue, public_landings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Bootstrap DB tables on startup (SQLite local dev)
    from app.database import init_db
    init_db()
    yield


app = FastAPI(
    title="Landing Reply API",
    description="AI-powered freelance reply generator with micro landing pages",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://213.176.16.155:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(projects.router,        prefix="/projects",        tags=["projects"])
app.include_router(orders.router,          prefix="/orders",          tags=["orders"])
app.include_router(replies.router,         prefix="/projects",        tags=["replies"])
app.include_router(landings.router,        prefix="/projects",        tags=["landings"])
app.include_router(dialogue.router,        prefix="/projects",        tags=["dialogue"])
app.include_router(public_landings.router, prefix="/public/landings", tags=["public"])


@app.get("/health")
def health_check():
    return {"status": "ok"}
