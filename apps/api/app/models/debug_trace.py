"""
PipelineTrace
─────────────
DB model for debug trace records.

One record = one AI stage execution.
Multiple records per project/stage = multiple runs (history preserved).

Stages:
  extraction                — order_parser_service
  reply_generation          — reply_generator_service
  landing_generation_step1  — landing_generator_service (semantic draft, text output)
  landing_generation_step2  — landing_generator_service (JSON packaging, json output)
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class PipelineTrace(Base):
    __tablename__ = "pipeline_traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(60), nullable=False)
    input_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_ai_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    __table_args__ = (
        Index("ix_pipeline_traces_project_id", "project_id"),
    )
