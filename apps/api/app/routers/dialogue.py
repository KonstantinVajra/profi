"""
Dialogue router
───────────────
POST /projects/{project_id}/dialogue/reply

Flow:
  1. verify project exists
  2. verify parsed_order exists — 400 if missing
  3. load recent message history for context
  4. save client message (sender_type="client")
  5. generate suggestions via DialogueCopilotService
  6. save dialogue_suggestion
  7. return DialogueSuggestionResponse
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dialogue import (
    DialogueReplyRequest,
    DialogueSuggestionResponse,
    DialogueReplySuggestionItem,
)
from app.schemas.order import ParsedOrder
from app.repositories.dialogue_repo import DialogueRepository
from app.services.dialogue_copilot_service import dialogue_copilot_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/{project_id}/dialogue/reply",
    response_model=DialogueSuggestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate dialogue suggestions for a client message",
)
def suggest_dialogue_reply(
    project_id: str,
    body: DialogueReplyRequest,
    db: Session = Depends(get_db),
):
    repo = DialogueRepository(db)

    # 1. verify project
    repo.get_project(project_id)

    # 2. verify parsed_order
    parsed_order_record = repo.get_parsed_order(project_id)
    if not parsed_order_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No parsed order found for this project. Run POST /orders/extract first.",
        )

    # 3. load recent history for context (up to 6 messages)
    recent = repo.list_recent_messages(project_id, limit=6)
    history = [
        {"sender": m.sender_type, "text": m.message_text}
        for m in recent
    ]

    # 4. save client message
    message = repo.create_dialogue_message(
        project_id=project_id,
        sender_type="client",
        message_text=body.message_text,
        source_channel=body.source_channel,
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
    )

    # 5. generate
    try:
        result = dialogue_copilot_service.generate(
            client_message=body.message_text,
            parsed_order=parsed_order,
            recent_history=history,
        )
    except ValueError as exc:
        logger.error("Dialogue generation failed | project=%s | error=%s", project_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Dialogue suggestion failed: {exc}",
        )

    # 6. save suggestion
    suggestion = repo.create_dialogue_suggestion(
        project_id=project_id,
        source_message_id=message.id,
        result=result,
    )

    # 7. return
    return DialogueSuggestionResponse(
        id=suggestion.id,
        project_id=project_id,
        source_message_id=message.id,
        detected_intent=suggestion.detected_intent,
        detected_stage=suggestion.detected_stage,
        suggestions=[
            DialogueReplySuggestionItem(**s) for s in suggestion.suggestions_json
        ],
        next_best_question=suggestion.next_best_question,
        created_at=suggestion.created_at,
    )
