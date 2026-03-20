"""
Orders router
─────────────
POST /orders/extract — parse raw order text, return ParsedOrderResponse

Flow:
  1. get project (404 if not found)
  2. save raw text to order_inputs
  3. call OrderParserService (LLM extraction + Pydantic validation)
  4. save result to parsed_orders
  5. return ParsedOrderResponse
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.order import OrderInputCreate, ParsedOrderResponse
from app.repositories.order_repo import OrderRepository
from app.services.order_parser_service import order_parser_service

logger = logging.getLogger(__name__)
router = APIRouter()


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
        parsed = order_parser_service.parse(body.raw_text, project_id=str(body.project_id), db=db)
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
