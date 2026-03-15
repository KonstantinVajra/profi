"""
DB models for the order parsing pipeline.

Tables:
  projects       — one project per order (workspace container)
  order_inputs   — raw text/screenshot as received from user
  parsed_orders  — structured data extracted by AI from order_input
"""

import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Date,
    ForeignKey, JSON, Float, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# Project
# ─────────────────────────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # relationships
    order_inputs: Mapped[list["OrderInput"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    parsed_orders: Mapped[list["ParsedOrderModel"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


# ─────────────────────────────────────────────────────────────────────────────
# OrderInput  — raw user input
# ─────────────────────────────────────────────────────────────────────────────

class OrderInput(Base):
    __tablename__ = "order_inputs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE")
    )
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), default="text")  # text | screenshot
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="order_inputs")


# ─────────────────────────────────────────────────────────────────────────────
# ParsedOrderModel  — AI-extracted structured fields
# ─────────────────────────────────────────────────────────────────────────────

class ParsedOrderModel(Base):
    """
    Stores the structured result of AI extraction.
    One ParsedOrder per OrderInput.
    user_confirmed=True after the user reviews and accepts the fields.
    """
    __tablename__ = "parsed_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE")
    )
    order_input_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("order_inputs.id", ondelete="CASCADE")
    )

    # ── extracted fields ──────────────────────────────────────────────────
    client_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    client_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_subtype: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    event_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    duration_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    guest_count_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    budget_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="RUB")
    requirements: Mapped[list] = mapped_column(JSON, default=list)
    priority_signals: Mapped[list] = mapped_column(JSON, default=list)
    tone_signal: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    extracted_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── meta ─────────────────────────────────────────────────────────────
    user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="parsed_orders")
