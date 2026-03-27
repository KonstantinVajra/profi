"""
dev_reset.py
────────────
DEV / ADMIN ONLY — do not run in production.

Fully resets runtime data for clean pre-production testing:
  1. TRUNCATE projects CASCADE — drops all project-owned rows via DB-level FK cascade
  2. TRUNCATE photo_set_items CASCADE + photo_sets CASCADE — standalone entities
  3. Removes filesystem photo and order-screenshot artifacts

Usage:
    cd apps/api
    python scripts/dev_reset.py

Environment guard:
    If APP_ENV=production is set in the environment, the script refuses to run.
    Set APP_ENV=development (or leave unset) to allow execution.

What is deleted:
    DB (cascade from projects):
      projects, order_inputs, parsed_orders, reply_variants,
      landing_pages, landing_content, dialogue_messages,
      dialogue_suggestions, pipeline_traces

    DB (standalone):
      photo_set_items, photo_sets

    Filesystem (STORAGE_ROOT):
      photos/sets/, photos/uploads/, photos/landings/
      storage/orders/

What is NOT deleted:
    DB schema, tables, indexes, alembic migration history,
    config files, source code.
"""

import os
import sys
import shutil
from pathlib import Path

# ── Environment guard ─────────────────────────────────────────────────────
# Reads APP_ENV directly from os.environ — does not depend on settings.
# Set APP_ENV=production in production deployments to block this script.

APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
if APP_ENV == "production":
    print("ERROR: Refusing to run dev_reset in production (APP_ENV=production).")
    sys.exit(1)

# ── Path setup ────────────────────────────────────────────────────────────
# Allow running from any working directory inside the project.

_SCRIPT_DIR = Path(__file__).resolve().parent
_API_ROOT = _SCRIPT_DIR.parent  # apps/api/
sys.path.insert(0, str(_API_ROOT))

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402

# ── Storage root ──────────────────────────────────────────────────────────

STORAGE_ROOT = Path(getattr(settings, "storage_root", "/var/storage/landing_reply"))

# Filesystem directories to wipe (relative to STORAGE_ROOT).
# Each directory is removed and recreated empty.
FS_DIRS_TO_CLEAR = [
    STORAGE_ROOT / "photos" / "sets",
    STORAGE_ROOT / "photos" / "uploads",
    STORAGE_ROOT / "photos" / "landings",
    STORAGE_ROOT / "storage" / "orders",
]

# ── Confirmation ──────────────────────────────────────────────────────────

def _confirm() -> bool:
    print()
    print("=" * 60)
    print("  DEV RESET — Landing Reply")
    print("=" * 60)
    print()
    print(f"  database : {settings.database_url}")
    print(f"  storage  : {STORAGE_ROOT}")
    print(f"  APP_ENV  : {APP_ENV}")
    print()
    print("  This will permanently delete:")
    print("    • ALL projects and all cascade-owned data")
    print("    • ALL photo sets and photo set items")
    print("    • ALL filesystem photos and order screenshots")
    print()
    answer = input("  Type YES to confirm: ").strip()
    return answer == "YES"

# ── Row counts ────────────────────────────────────────────────────────────

def _print_counts(db) -> None:
    tables = [
        "projects",
        "order_inputs",
        "parsed_orders",
        "reply_variants",
        "landing_pages",
        "landing_content",
        "dialogue_messages",
        "dialogue_suggestions",
        "pipeline_traces",
        "photo_sets",
        "photo_set_items",
    ]
    print()
    print("  Current row counts:")
    for table in tables:
        try:
            result = db.execute(__import__("sqlalchemy").text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
        except Exception:
            count = "?"
        print(f"    {table:30s} {count}")
    print()

# ── DB reset ──────────────────────────────────────────────────────────────

def _reset_db(db) -> None:
    import sqlalchemy

    print("  Truncating DB...")

    # TRUNCATE projects CASCADE covers all project-owned tables via FK ondelete=CASCADE:
    # order_inputs, parsed_orders, reply_variants, landing_pages → landing_content,
    # dialogue_messages → dialogue_suggestions, pipeline_traces
    db.execute(sqlalchemy.text("TRUNCATE TABLE projects CASCADE"))

    # photo_sets and photo_set_items are standalone (no FK to projects).
    # photo_set_items must be truncated before photo_sets, or CASCADE handles it.
    db.execute(sqlalchemy.text("TRUNCATE TABLE photo_set_items CASCADE"))
    db.execute(sqlalchemy.text("TRUNCATE TABLE photo_sets CASCADE"))

    db.commit()
    print("  DB truncated.")

# ── Filesystem reset ──────────────────────────────────────────────────────

def _reset_fs() -> None:
    print("  Clearing filesystem...")
    for directory in FS_DIRS_TO_CLEAR:
        if directory.exists():
            shutil.rmtree(directory)
            print(f"    removed : {directory}")
        else:
            print(f"    skipped : {directory} (does not exist)")
        # Recreate empty directory so the app can write immediately after reset.
        directory.mkdir(parents=True, exist_ok=True)
        print(f"    created : {directory}")
    print("  Filesystem cleared.")

# ── Entry point ───────────────────────────────────────────────────────────

def main() -> None:
    db = SessionLocal()
    try:
        _print_counts(db)

        if not _confirm():
            print()
            print("  Aborted.")
            return

        print()
        _reset_db(db)
        _reset_fs()

        print()
        print("  Verifying final counts:")
        _print_counts(db)

        print("  Done. System is clean.")
        print()

    except Exception as exc:
        db.rollback()
        print(f"\n  ERROR: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()