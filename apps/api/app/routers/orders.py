"""
Orders router
─────────────
POST /orders/extract       — parse raw order text, return ParsedOrderResponse
POST /orders/extract/image — parse order from screenshot, return ParsedOrderResponse

Both endpoints produce the same ParsedOrderResponse and feed the same downstream
pipeline (Generate Landing → Generate Replies → ...).

Text flow:
  1. get project (404 if not found)
  2. save raw text to order_inputs (source_type="text")
  3. call OrderParserService.parse_text()
  4. save result to parsed_orders
  5. return ParsedOrderResponse

Image flow:
  1. get project (404 if not found)
  2. read image bytes from UploadFile (router responsibility)
  3. save screenshot file to storage/orders/{order_input_id}/screenshot.{ext}
  4. save metadata to order_inputs (source_type="screenshot", screenshot_path)
  5. call OrderParserService.parse_image(image_bytes, media_type)
  6. save result to parsed_orders
  7. return ParsedOrderResponse
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.order import OrderInputCreate, ParsedOrderResponse
from app.repositories.order_repo import OrderRepository
from app.services.order_parser_service import order_parser_service
from app.config import settings

# Storage root for order screenshots — same base path used across storage layer.
# Defined locally to avoid coupling orders router to landing photo service.
_ORDERS_STORAGE_ROOT = Path(getattr(settings, "storage_root", "/var/storage/landing_reply"))

logger = logging.getLogger(__name__)
router = APIRouter()

# Allowed MIME types for screenshot upload
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_IMAGE_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


@router.post(
    "/extract",
    response_model=ParsedOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract structured order fields from raw text",
)
def extract_order(body: OrderInputCreate, db: Session = Depends(get_db)):
    repo = OrderRepository(db)

    # 1. get project — raises 404 if not found
    repo.get_project(body.project_id)

    # 2. save raw input
    order_input = repo.create_order_input(
        project_id=body.project_id,
        raw_text=body.raw_text,
    )

    # 3. LLM extraction + Pydantic validation
    try:
        parsed = order_parser_service.parse_text(body.raw_text, project_id=str(body.project_id), db=db)
    except ValueError as exc:
        logger.error("Order parsing failed | project=%s | error=%s", body.project_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not extract order fields: {exc}",
        )

    # 4. save to DB
    record = repo.create_parsed_order(
        project_id=body.project_id,
        order_input_id=order_input.id,
        parsed=parsed,
    )

    # 5. return
    return ParsedOrderResponse(
        id=record.id,
        project_id=record.project_id,
        order_input_id=record.order_input_id,
        **parsed.model_dump(),
    )


@router.post(
    "/extract/image",
    response_model=ParsedOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract structured order fields from a screenshot (vision mode)",
)
async def extract_order_from_image(
    project_id: str = Form(...),
    screenshot: UploadFile = File(...),
    db=Depends(get_db),
):
    """
    Accept a screenshot of a client order and extract structured fields using AI vision.

    Returns the same ParsedOrderResponse as POST /orders/extract.
    The downstream pipeline (landing, replies, dialogue) is identical for both modes.
    """
    # 1. validate project exists
    repo = OrderRepository(db)
    repo.get_project(project_id)

    # 2. validate content type
    media_type = screenshot.content_type or "image/jpeg"
    if media_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type: {media_type}. Allowed: {sorted(_ALLOWED_IMAGE_TYPES)}",
        )

    # 3. read bytes — router is responsible for reading UploadFile
    image_bytes = await screenshot.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # 4. compute storage path using a transient UUID, then save file and record together.
    #    This avoids a two-step DB write (create then update screenshot_path).
    import uuid as _uuid_mod
    transient_id = str(_uuid_mod.uuid4())
    ext = _IMAGE_EXT.get(media_type, "jpg")
    storage_key = f"orders/{transient_id}/screenshot.{ext}"

    # 5. save screenshot to storage/orders/{transient_id}/screenshot.{ext}
    dest = _ORDERS_STORAGE_ROOT / storage_key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(image_bytes)

    # 6. create OrderInput with screenshot_path already set
    order_input = repo.create_order_input(
        project_id=project_id,
        raw_text=None,
        screenshot_path=storage_key,
        source_type="screenshot",
    )

    # 7. AI vision extraction — service receives bytes only, not UploadFile
    try:
        parsed = order_parser_service.parse_image(
            image_bytes=image_bytes,
            image_media_type=media_type,
            project_id=project_id,
            db=db,
        )
    except ValueError as exc:
        logger.error(
            "Screenshot parsing failed | project=%s | error=%s", project_id, exc
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # 8. save parsed order to DB
    record = repo.create_parsed_order(
        project_id=project_id,
        order_input_id=order_input.id,
        parsed=parsed,
    )

    # 9. return same response shape as text extraction
    return ParsedOrderResponse(
        id=record.id,
        project_id=record.project_id,
        order_input_id=record.order_input_id,
        **parsed.model_dump(),
    )


@router.post(
    "/extract/images",
    response_model=ParsedOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract structured order fields from multiple screenshots (vision mode)",
)
async def extract_order_from_images(
    project_id: str = Form(...),
    screenshots: list[UploadFile] = File(...),
    db=Depends(get_db),
):
    """
    Accept 1–5 screenshots of a client order and extract structured fields using AI vision.
    All images are sent to the AI in a single call; the model synthesises them into one ParsedOrder.

    MVP limitation: screenshot_path in OrderInput stores only the first file path.
    Remaining files are used for AI extraction only and are not persisted individually.

    Returns the same ParsedOrderResponse as POST /orders/extract and /orders/extract/image.
    """
    repo = OrderRepository(db)

    # 1. validate project exists
    repo.get_project(project_id)

    # 2. count validation
    if len(screenshots) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one screenshot is required.",
        )
    if len(screenshots) > 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Too many screenshots: maximum 5 allowed, got {len(screenshots)}.",
        )

    # 3. validate MIME types and read bytes for all files
    image_list: list[tuple[bytes, str]] = []
    for upload in screenshots:
        media_type = upload.content_type or "image/jpeg"
        if media_type not in _ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported image type: {media_type}. Allowed: {sorted(_ALLOWED_IMAGE_TYPES)}",
            )
        img_bytes = await upload.read()
        if not img_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One of the uploaded files is empty.",
            )
        image_list.append((img_bytes, media_type))

    # 4. persist first screenshot to storage; remaining files used for AI only.
    #    MVP limitation: screenshot_path stores only the first file path.
    import uuid as _uuid_mod
    transient_id = str(_uuid_mod.uuid4())
    first_bytes, first_media_type = image_list[0]
    ext = _IMAGE_EXT.get(first_media_type, "jpg")
    storage_key = f"orders/{transient_id}/screenshot.{ext}"
    dest = _ORDERS_STORAGE_ROOT / storage_key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(first_bytes)

    # 5. save OrderInput with first screenshot path
    order_input = repo.create_order_input(
        project_id=project_id,
        raw_text=None,
        screenshot_path=storage_key,
        source_type="screenshot",
    )

    # 6. AI vision extraction across all screenshots in one call
    try:
        parsed = order_parser_service.parse_images(
            image_list=image_list,
            project_id=project_id,
            db=db,
        )
    except ValueError as exc:
        logger.error(
            "Multi-screenshot parsing failed | project=%s | error=%s", project_id, exc
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # 7. save parsed order to DB
    record = repo.create_parsed_order(
        project_id=project_id,
        order_input_id=order_input.id,
        parsed=parsed,
    )

    # 8. return same response shape as single-image extraction
    return ParsedOrderResponse(
        id=record.id,
        project_id=record.project_id,
        order_input_id=record.order_input_id,
        **parsed.model_dump(),
    )
