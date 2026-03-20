"""
Landings router
───────────────
POST /projects/{project_id}/landing/generate

Flow:
  1. verify project exists
  2. load latest ParsedOrder — 400 if missing
  3. generate LandingPageModel via LandingGeneratorService
  4. delete existing landing for this project (replace)
  5. save landing_pages row
  6. save landing_content row
  7. return LandingGenerateResponse
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.landing import (
    LandingGenerateRequest,
    LandingGenerateResponse,
    LandingPageMetadata,
)
from app.schemas.order import ParsedOrder
from app.repositories.landing_repo import LandingRepository
from app.services.landing_generator_service import landing_generator_service
from app.services.landing_photo_service import snapshot_photo_set

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/{project_id}/landing/generate",
    response_model=LandingGenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate LandingPageModel JSON from the project's ParsedOrder",
)
def generate_landing(
    project_id: str,
    request: Request,
    body: LandingGenerateRequest = None,
    db: Session = Depends(get_db),
):
    if body is None:
        body = LandingGenerateRequest()

    repo = LandingRepository(db)

    # 1. verify project
    repo.get_project(project_id)

    # 2. load parsed order
    parsed_order_record = repo.get_parsed_order(project_id)
    if not parsed_order_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No parsed order found for this project. Run POST /orders/extract first.",
        )

    # map ORM → Pydantic for service
    parsed_order = ParsedOrder(
        client_name=parsed_order_record.client_name,
        client_label=parsed_order_record.client_label,
        event_type=parsed_order_record.event_type,
        event_subtype=parsed_order_record.event_subtype,
        city=parsed_order_record.city,
        location=parsed_order_record.location,
        event_date=parsed_order_record.event_date,
        date_text=parsed_order_record.date_text,
        duration_text=parsed_order_record.duration_text,
        guest_count_text=parsed_order_record.guest_count_text,
        budget_max=parsed_order_record.budget_max,
        currency=parsed_order_record.currency,
        requirements=parsed_order_record.requirements or [],
        priority_signals=parsed_order_record.priority_signals or [],
        tone_signal=parsed_order_record.tone_signal,
        extracted_confidence=parsed_order_record.extracted_confidence,
        # ── semantic inference fields ────────────────────────────────────
        client_intent_line=parsed_order_record.client_intent_line,
        situation_notes=parsed_order_record.situation_notes,
        shoot_feel=parsed_order_record.shoot_feel,
    )

    # 3. generate — controlled error handling
    try:
        landing_model = landing_generator_service.generate(
            parsed_order=parsed_order,
            price=body.price,
            photo_set_id=body.photo_set_id,
            case_series_id=body.case_series_id,
            project_id=project_id,
            db=db,
        )
    except ValueError as exc:
        logger.error(
            "Landing generation failed | project=%s | error=%s", project_id, exc
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Landing generation failed: {exc}",
        )
    except Exception:
        logger.exception(
            "Landing generation unexpected error | project=%s", project_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Landing generation failed due to an internal error. Please retry.",
        )

    # 3b. snapshot photos if photo_set_id was provided — must happen before saving content
    if body.photo_set_id:
        try:
            snapshot_id = snapshot_photo_set(body.photo_set_id, db)
            # inject snapshot id so content_json carries the landing-owned set
            landing_model = landing_model.model_copy(
                update={"style_grid": landing_model.style_grid.model_copy(
                    update={"photo_set_id": snapshot_id}
                )}
            )
            logger.info(
                "Photo snapshot injected | project=%s | snapshot=%s",
                project_id, snapshot_id,
            )
        except (ValueError, RuntimeError) as exc:
            logger.error(
                "Photo snapshot failed | project=%s | error=%s", project_id, exc
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Photo snapshot failed: {exc}",
            )

    # 4-6. replace landing + save — wrapped together so DB stays consistent if save fails.
    # Note: if snapshot succeeded but save fails, snapshot photo_sets/items are rolled back
    # by db.rollback(), but files on disk are NOT cleaned up (filesystem is not transactional).
    # filesystem cleanup is intentionally not handled in MVP.
    try:
        repo.delete_existing_landing(project_id)

        page = repo.create_landing_page(
            project_id=project_id,
            slug=landing_model.slug,
            template_key=landing_model.template_key,
        )

        repo.create_landing_content(
            landing_page_id=page.id,
            model=landing_model,
        )
    except Exception:
        db.rollback()
        logger.exception("Landing save failed | project=%s", project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save landing after generation. Please retry.",
        )

    # 7. return
    base = str(request.base_url).rstrip("/")
    logger.warning("DEBUG TRACE: %s/debug/project/%s", base, project_id)
    return LandingGenerateResponse(
        landing_page=LandingPageMetadata(
            id=page.id,
            project_id=page.project_id,
            slug=page.slug,
            template_key=page.template_key,
            status=page.status,
            is_public=page.is_public,
            created_at=page.created_at,
        ),
        landing_content=landing_model,
    )