"""
LandingPhotoService
───────────────────
Snapshots a photo_set into a landing-owned copy during landing generation.

snapshot_photo_set():
  - reads items from source photo_set
  - copies files to photos/landings/{new_set_id}/
  - creates new photo_set with source_type=landing_snapshot
  - returns new photo_set_id

Called by landings router BEFORE saving landing_content.
If snapshot fails, the exception propagates — caller must abort generation.
"""

import logging
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.photo import PhotoSet, PhotoSetItem
from app.config import settings

logger = logging.getLogger(__name__)

STORAGE_ROOT = Path(getattr(settings, "storage_root", "/var/storage/landing_reply"))


def _storage_path(storage_key: str) -> Path:
    return STORAGE_ROOT / storage_key


def _photo_url(item_id: str) -> str:
    base = getattr(settings, "api_url", "http://localhost:8000")
    return f"{base}/photos/{item_id}"


def snapshot_photo_set(source_photo_set_id: str, db: Session) -> str:
    """
    Copy source photo_set into a new landing_snapshot photo_set.
    Returns new photo_set_id.
    Raises ValueError if source not found or has no items.
    Raises RuntimeError on file copy failure.
    """
    source = db.query(PhotoSet).filter(PhotoSet.id == source_photo_set_id).first()
    if not source:
        raise ValueError(f"photo_set '{source_photo_set_id}' not found")

    source_items = (
        db.query(PhotoSetItem)
        .filter(PhotoSetItem.photo_set_id == source_photo_set_id)
        .order_by(PhotoSetItem.display_order)
        .all()
    )
    if not source_items:
        raise ValueError(f"photo_set '{source_photo_set_id}' has no items")

    # create new landing_snapshot photo_set
    new_set = PhotoSet(source_type="landing_snapshot", name=source.name)
    db.add(new_set)
    db.flush()  # get new_set.id before copying files

    dest_dir = STORAGE_ROOT / "photos" / "landings" / new_set.id
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        db.rollback()
        raise RuntimeError(f"Failed to create snapshot directory: {exc}") from exc

    new_items = []
    for item in source_items:
        src_path = _storage_path(item.storage_key)
        filename = src_path.name
        dst_path = dest_dir / filename

        try:
            shutil.copy2(src_path, dst_path)
        except OSError as exc:
            db.rollback()
            raise RuntimeError(
                f"Failed to copy photo '{item.storage_key}': {exc}"
            ) from exc

        new_storage_key = str(
            (Path("photos") / "landings" / new_set.id / filename)
        )
        new_item = PhotoSetItem(
            photo_set_id=new_set.id,
            storage_key=new_storage_key,
            display_order=item.display_order,
        )
        new_items.append(new_item)

    db.add_all(new_items)
    db.flush()

    logger.info(
        "Photo snapshot created | source=%s | snapshot=%s | items=%d",
        source_photo_set_id,
        new_set.id,
        len(new_items),
    )
    return new_set.id
