"""
DB models for dialogue_messages and dialogue_suggestions tables.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class DialogueMessage(Base):
    __tablename__ = "dialogue_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_channel: Mapped[str] = mapped_column(String(50), nullable=False, default="profi")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class DialogueSuggestion(Base):
    __tablename__ = "dialogue_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    source_message_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("dialogue_messages.id", ondelete="CASCADE"), nullable=False
    )
    detected_intent: Mapped[str] = mapped_column(String(100), nullable=False)
    detected_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    suggestions_json: Mapped[list] = mapped_column(JSON, nullable=False)
    next_best_question: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
