"""
Replies router
──────────────
POST /projects/{project_id}/replies/generate

Flow:
  1. verify project exists
  2. load latest ParsedOrder — 400 if missing
  3. generate 3 variants via ReplyGeneratorService
     (AI output contains {{landing_url}} placeholder — validated by schema)
  4. if landing_url provided in request body, substitute placeholder in message_text
  5. delete previous variants for this project
  6. save new variants
  7. return ReplyGenerateResponse
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.reply import ReplyGenerateRequest, ReplyGenerateResponse, ReplyVariant, ReplyVariantResponse
from app.schemas.order import ParsedOrder
from app.repositories.reply_repo import ReplyRepository
from app.services.reply_generator_service import reply_generator_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _substitute_url(variants: list[ReplyVariant], landing_url: str) -> list[ReplyVariant]:
    """
    Replace {{landing_url}} placeholder with the real URL in each variant.
    Also strips any punctuation that AI placed immediately after the URL,
    since trailing periods/commas break the link when copy-pasted.
    """
    import re
    result = []
    for v in variants:
        substituted_text = v.message_text.replace("{{landing_url}}", landing_url)
        # Remove punctuation that immediately follows the URL (e.g. trailing period from a sentence)
        substituted_text = re.sub(
            r'(https?://[^\s]+)[.,;:!?]+',
            r'\1',
            substituted_text,
        )
        new_v = ReplyVariant.model_construct(
            variant_type=v.variant_type,
            message_text=substituted_text,
            preview_text=v.preview_text,
            includes_link=v.includes_link,
            is_selected=v.is_selected,
        )
        result.append(new_v)
    return result


@router.post(
    "/{project_id}/replies/generate",
    response_model=ReplyGenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate 3 reply variants from the project's ParsedOrder",
)
def generate_replies(
    project_id: str,
    body: ReplyGenerateRequest = None,
    db: Session = Depends(get_db),
):
    if body is None:
        body = ReplyGenerateRequest()

    repo = ReplyRepository(db)

    # 1. verify project exists
    repo.get_project(project_id)

    # 2. load parsed order
    parsed_order_record = repo.get_parsed_order(project_id)
    if not parsed_order_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No parsed order found for this project. Run POST /orders/extract first.",
        )

    # map ORM record → Pydantic ParsedOrder for the service
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
    )

    # 3. generate via LLM — variants contain {{landing_url}} placeholder
    try:
        variants = reply_generator_service.generate(parsed_order, project_id=project_id, db=db)
    except ValueError as exc:
        logger.error("Reply generation failed | project=%s | error=%s", project_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Reply generation failed: {exc}",
        )

    # 4. substitute placeholder if landing_url provided
    if body.landing_url:
        variants = _substitute_url(variants, body.landing_url)
        logger.info("Substituted landing_url | project=%s | url=%s", project_id, body.landing_url)

    # 5. replace previous variants
    repo.delete_reply_variants(project_id)

    # 6. save new variants
    saved = [repo.create_reply_variant(project_id, v) for v in variants]

    # 7. return
    return ReplyGenerateResponse(
        project_id=project_id,
        reply_variants=[ReplyVariantResponse.model_validate(r) for r in saved],
    )
