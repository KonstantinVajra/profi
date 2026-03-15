"""
ReplyRepository
───────────────
Database access for reply_variants table.
No business logic — only DB reads and writes.

Methods:
  get_project         — verify project exists, return Project
  get_parsed_order    — return latest ParsedOrder for project, or None
  delete_reply_variants  — delete all variants for project (before regenerating)
  create_reply_variant   — insert one ReplyVariantModel
  list_reply_variants    — return all variants for project
"""

import logging

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.order import Project, ParsedOrderModel
from app.models.reply import ReplyVariantModel
from app.schemas.reply import ReplyVariant

logger = logging.getLogger(__name__)


class ReplyRepository:
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
        """Return the most recently created ParsedOrder for a project."""
        return (
            self.db.query(ParsedOrderModel)
            .filter(ParsedOrderModel.project_id == project_id)
            .order_by(ParsedOrderModel.created_at.desc())
            .first()
        )

    def delete_reply_variants(self, project_id: str) -> None:
        """Delete all existing variants for a project before writing new ones."""
        deleted = (
            self.db.query(ReplyVariantModel)
            .filter(ReplyVariantModel.project_id == project_id)
            .delete()
        )
        self.db.commit()
        logger.info("Deleted %d reply variants for project=%s", deleted, project_id)

    def create_reply_variant(
        self,
        project_id: str,
        variant: ReplyVariant,
    ) -> ReplyVariantModel:
        record = ReplyVariantModel(
            project_id=project_id,
            variant_type=variant.variant_type,
            message_text=variant.message_text,
            preview_text=variant.preview_text,
            includes_link=variant.includes_link,
            is_selected=variant.is_selected,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        logger.info(
            "ReplyVariant saved | id=%s | type=%s | project=%s",
            record.id, record.variant_type, project_id,
        )
        return record

    def list_reply_variants(self, project_id: str) -> list[ReplyVariantModel]:
        return (
            self.db.query(ReplyVariantModel)
            .filter(ReplyVariantModel.project_id == project_id)
            .order_by(ReplyVariantModel.created_at)
            .all()
        )
