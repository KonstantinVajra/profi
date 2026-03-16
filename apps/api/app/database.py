from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

# ── Engine ────────────────────────────────────────────────────────────────
# PostgreSQL: standard pool settings
# SQLite: no pool, check_same_thread=False for FastAPI threads
if _is_sqlite:
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
else:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

# SQLite-only: enable WAL mode and foreign key enforcement
if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Create all tables from ORM models.
    Works for both SQLite (local dev) and PostgreSQL (production).
    Alembic remains in the repo for future migrations — not used for initial bootstrap.
    """
    import app.models  # noqa: F401 — ensures all models are registered with Base
    Base.metadata.create_all(bind=engine)
