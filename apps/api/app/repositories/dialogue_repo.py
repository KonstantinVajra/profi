"""
DialogueRepository
──────────────────
Database access for dialogue_messages and dialogue_suggestions.
No business logic — only DB reads and writes.

Methods:
  get_project               — verify project exists
  get_parsed_order          — load latest ParsedOrder for project
  create_dialogue_message   — insert one message row
  list_recent_messages      — return last N messages for context
  create_dialogue_suggestion — insert suggestion set
  get_latest_dialogue_suggestion — return most recent suggestion for project
"""

import logging

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.order import Project, ParsedOrderModel
from app.models.dialogue import DialogueMessage, DialogueSuggestion
from app.schemas.dialogue import DialogueAIOutput

logger = logging.getLogger(__name__)


class DialogueRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_project(self, project_id: str) -> Project:
        project = self.db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )
        return project

    def get_parsed_order(self, project_id: str) -> ParsedOrderModel | None:
        return (
            self.db.query(ParsedOrderModel)
            .filter(ParsedOrderModel.project_id == project_id)
            .order_by(ParsedOrderModel.created_at.desc())
            .first()
        )

    def create_dialogue_message(
        self,
        project_id: str,
        sender_type: str,
        message_text: str,
        source_channel: str = "profi",
    ) -> DialogueMessage:
        message = DialogueMessage(
            project_id=project_id,
            sender_type=sender_type,
            message_text=message_text,
            source_channel=source_channel,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        logger.info("DialogueMessage saved | id=%s | sender=%s | project=%s",
                    message.id, sender_type, project_id)
        return message

    def list_recent_messages(
        self,
        project_id: str,
        limit: int = 6,
    ) -> list[DialogueMessage]:
        """Return last `limit` messages ordered oldest-first for context window."""
        rows = (
            self.db.query(DialogueMessage)
            .filter(DialogueMessage.project_id == project_id)
            .order_by(DialogueMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(rows))

    def create_dialogue_suggestion(
        self,
        project_id: str,
        source_message_id: str,
        result: DialogueAIOutput,
    ) -> DialogueSuggestion:
        suggestion = DialogueSuggestion(
            project_id=project_id,
            source_message_id=source_message_id,
            detected_intent=result.detected_intent,
            detected_stage=result.detected_stage,
            suggestions_json=[s.model_dump() for s in result.suggestions],
            next_best_question=result.next_best_question,
        )
        self.db.add(suggestion)
        self.db.commit()
        self.db.refresh(suggestion)
        logger.info("DialogueSuggestion saved | id=%s | intent=%s | project=%s",
                    suggestion.id, result.detected_intent, project_id)
        return suggestion

    def get_latest_dialogue_suggestion(
        self, project_id: str
    ) -> DialogueSuggestion | None:
        return (
            self.db.query(DialogueSuggestion)
            .filter(DialogueSuggestion.project_id == project_id)
            .order_by(DialogueSuggestion.created_at.desc())
            .first()
        )
