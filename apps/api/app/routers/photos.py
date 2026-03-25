"""
Photos router
─────────────
Workspace endpoints (authenticated zone in future — open for MVP):
  GET  /photo-sets                           — list preset albums
  GET  /photo-sets/{photo_set_id}            — one preset album with items
  POST /photo-sets/preset                    — create preset album (name + category + files)
  POST /projects/{project_id}/photos/upload  — manual upload → photo_set_id

Public serving endpoint:
  GET  /photos/{item_id}                     — serve photo bytes (public, no auth)

Public read paths for landing render:
  GET  /public/photo-sets?category={key}     — list preset albums by category
  GET  /public/photo-sets/{photo_set_id}     — items for landing_snapshot or preset
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.photo import PhotoSet, PhotoSetItem
from app.schemas.photo import (
    PhotoSetItemResponse,
    PhotoSetResponse,
    PhotoUploadResponse,
    PresetAlbumSummary,
    PresetCreateResponse,
    PRESET_CATEGORIES,
)
from app.services.landing_photo_service import STORAGE_ROOT, _photo_url

logger = logging.getLogger(__name__)
router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────

def _item_to_response(item: PhotoSetItem) -> PhotoSetItemResponse:
    return PhotoSetItemResponse(
        id=item.id,
        photo_url=_photo_url(item.id),
        display_order=item.display_order,
    )


def _save_upload(file: UploadFile, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f:
        f.write(file.file.read())


# ── workspace endpoints ───────────────────────────────────────────────────

@router.get(
    "/photo-sets",
    response_model=list[PhotoSetResponse],
    summary="List preset photo albums",
)
def list_photo_sets(
    category: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(PhotoSet).filter(PhotoSet.source_type == "preset")
    if category:
        q = q.filter(PhotoSet.category_key == category)
    sets = q.order_by(PhotoSet.created_at.desc()).all()
    return [
        PhotoSetResponse(
            id=s.id,
            name=s.name,
            category_key=s.category_key,
            items=[_item_to_response(i) for i in s.items],
        )
        for s in sets
    ]


@router.get(
    "/photo-sets/{photo_set_id}",
    response_model=PhotoSetResponse,
    summary="Get one preset photo album with items",
)
def get_photo_set(photo_set_id: str, db: Session = Depends(get_db)):
    ps = db.query(PhotoSet).filter(
        PhotoSet.id == photo_set_id,
        PhotoSet.source_type == "preset",
    ).first()
    if not ps:
        raise HTTPException(status_code=404, detail="Photo set not found")
    return PhotoSetResponse(
        id=ps.id,
        name=ps.name,
        category_key=ps.category_key,
        items=[_item_to_response(i) for i in ps.items],
    )


@router.post(
    "/photo-sets/preset",
    response_model=PresetCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a named preset photo album",
)
def create_preset_album(
    name: str = Form(...),
    category: str = Form(...),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    if category not in PRESET_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid category_key '{category}'. Allowed: {PRESET_CATEGORIES}",
        )
    ps = PhotoSet(source_type="preset", name=name, category_key=category)
    db.add(ps)
    db.flush()

    dest_dir = STORAGE_ROOT / "photos" / "sets" / ps.id
    items = []
    for order, upload in enumerate(files):
        filename = Path(upload.filename or f"photo_{order}").name
        dest = dest_dir / filename
        try:
            _save_upload(upload, dest)
        except OSError as exc:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save file '{filename}': {exc}",
            )
        storage_key = str(Path("photos") / "sets" / ps.id / filename)
        items.append(PhotoSetItem(
            photo_set_id=ps.id,
            storage_key=storage_key,
            display_order=order,
        ))

    db.add_all(items)
    db.commit()
    logger.info("Preset album created | id=%s | name=%s | category=%s | items=%d", ps.id, name, category, len(items))
    return PresetCreateResponse(photo_set_id=ps.id, name=name)


@router.post(
    "/projects/{project_id}/photos/upload",
    response_model=PhotoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload photos for landing generation (manual, not shown in UI lists)",
)
def upload_photos(
    project_id: str,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    ps = PhotoSet(source_type="manual_upload", name=None)
    db.add(ps)
    db.flush()

    dest_dir = STORAGE_ROOT / "photos" / "uploads" / project_id / ps.id
    items = []
    for order, upload in enumerate(files):
        filename = Path(upload.filename or f"photo_{order}").name
        dest = dest_dir / filename
        try:
            _save_upload(upload, dest)
        except OSError as exc:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save file '{filename}': {exc}",
            )
        storage_key = str(
            Path("photos") / "uploads" / project_id / ps.id / filename
        )
        items.append(PhotoSetItem(
            photo_set_id=ps.id,
            storage_key=storage_key,
            display_order=order,
        ))

    db.add_all(items)
    db.commit()
    logger.info(
        "Manual upload created | project=%s | photo_set=%s | items=%d",
        project_id, ps.id, len(items),
    )
    return PhotoUploadResponse(photo_set_id=ps.id)


# ── public serving ────────────────────────────────────────────────────────

@router.get(
    "/photos/{item_id}",
    summary="Serve photo bytes (public)",
    include_in_schema=True,
)
def serve_photo(item_id: str, db: Session = Depends(get_db)):
    item = (
        db.query(PhotoSetItem)
        .join(PhotoSet, PhotoSetItem.photo_set_id == PhotoSet.id)
        .filter(
            PhotoSetItem.id == item_id,
            PhotoSet.source_type.in_(["landing_snapshot", "preset"]),
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Photo not found")

    file_path = STORAGE_ROOT / item.storage_key
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Photo file not found on disk")

    return FileResponse(str(file_path))


# ── public photo-set endpoints (for landing render) ───────────────────────

@router.get(
    "/public/photo-sets",
    response_model=list[PresetAlbumSummary],
    summary="List preset albums by category (public, for landing page render)",
)
def list_public_photo_sets_by_category(
    category: str = Query(...),
    db: Session = Depends(get_db),
):
    if category not in PRESET_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid category_key '{category}'. Allowed: {PRESET_CATEGORIES}",
        )
    sets = (
        db.query(PhotoSet)
        .filter(
            PhotoSet.source_type == "preset",
            PhotoSet.category_key == category,
        )
        .order_by(PhotoSet.created_at.desc())
        .all()
    )
    return [
        PresetAlbumSummary(id=s.id, name=s.name)
        for s in sets
    ]


@router.get(
    "/public/photo-sets/{photo_set_id}",
    response_model=PhotoSetResponse,
    summary="Get photo items for a landing snapshot or preset album (public)",
)
def get_public_photo_set(photo_set_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Returns items for source_type=landing_snapshot OR source_type=preset.
    manual_upload is never publicly accessible.
    Used by the public /r/[slug] page to render style_grid and related albums.
    photo_url is built from the incoming request base URL.
    """
    ps = (
        db.query(PhotoSet)
        .filter(
            PhotoSet.id == photo_set_id,
            PhotoSet.source_type.in_(["landing_snapshot", "preset"]),
        )
        .first()
    )
    if not ps:
        raise HTTPException(status_code=404, detail="Photo set not found")

    items = (
        db.query(PhotoSetItem)
        .filter(PhotoSetItem.photo_set_id == photo_set_id)
        .order_by(PhotoSetItem.display_order)
        .all()
    )
    base = str(request.base_url).rstrip("/")
    return PhotoSetResponse(
        id=ps.id,
        name=ps.name,
        category_key=ps.category_key,
        items=[
            PhotoSetItemResponse(
                id=item.id,
                photo_url=f"{base}/photos/{item.id}",
                display_order=item.display_order,
            )
            for item in items
        ],
    )