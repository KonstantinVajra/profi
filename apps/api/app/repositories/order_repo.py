"""
OrderRepository
───────────────
Database access layer for the order parsing pipeline.
No business logic — only DB reads and writes.

Methods:
  get_project          — verify project exists
  create_project       — create new project
  create_order_input   — save raw user input
  create_parsed_order  — save AI-extracted ParsedOrder
"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.order import Project, OrderInput, ParsedOrderModel
from app.schemas.order import ParsedOrder

logger = logging.getLogger(__name__)


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Project ───────────────────────────────────────────────────────────

    def get_project(self, project_id: str) -> Project:
        """
        Return Project or raise 404.
        Used to validate project_id before writing order data.
        """
        project = self.db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )
        return project

    def create_project(self, title: str | None = None) -> Project:
        """Create a new bare project. Used by POST /projects."""
        project = Project(title=title)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        logger.info("Project created | id=%s", project.id)
        return project

    # ── OrderInput ────────────────────────────────────────────────────────

    def create_order_input(
        self,
        project_id: str,
        raw_text: str,
        source_type: str = "text",
    ) -> OrderInput:
        """Persist raw user input before parsing."""
        order_input = OrderInput(
            project_id=project_id,
            raw_text=raw_text,
            source_type=source_type,
        )
        self.db.add(order_input)
        self.db.commit()
        self.db.refresh(order_input)
        logger.info("OrderInput saved | id=%s | project=%s", order_input.id, project_id)
        return order_input

    # ── ParsedOrder ───────────────────────────────────────────────────────

    def create_parsed_order(
        self,
        project_id: str,
        order_input_id: str,
        parsed: ParsedOrder,
    ) -> ParsedOrderModel:
        """
        Save AI-extracted ParsedOrder to DB.
        Maps all Pydantic fields to the ORM model.
        """
        record = ParsedOrderModel(
            project_id=project_id,
            order_input_id=order_input_id,
            # who
            client_name=parsed.client_name,
            client_label=parsed.client_label,
            # what
            event_type=parsed.event_type,
            event_subtype=parsed.event_subtype,
            # where
            city=parsed.city,
            location=parsed.location,
            # when
            event_date=parsed.event_date,
            date_text=parsed.date_text,
            # how
            duration_text=parsed.duration_text,
            guest_count_text=parsed.guest_count_text,
            # money
            budget_max=parsed.budget_max,
            currency=parsed.currency,
            # details
            requirements=parsed.requirements,
            priority_signals=parsed.priority_signals,
            tone_signal=parsed.tone_signal,
            extracted_confidence=parsed.extracted_confidence,
            # ── semantic inference fields ────────────────────────────────
            client_intent_line=parsed.client_intent_line,
            situation_notes=parsed.situation_notes,
            shoot_feel=parsed.shoot_feel,
            # state
            user_confirmed=False,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        logger.info("ParsedOrder saved | id=%s | project=%s", record.id, project_id)
        return record