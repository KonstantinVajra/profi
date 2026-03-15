"""
LandingRepository
─────────────────
Database access for landing_pages and landing_content.
No business logic — only DB reads and writes.

Methods:
  get_project              — verify project exists
  get_parsed_order         — load latest ParsedOrder for project
  delete_existing_landing  — remove current landing before replacing
  create_landing_page      — insert landing_pages row
  create_landing_content   — insert landing_content row
  get_landing_by_project   — return landing + content for a project
"""

import logging

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.order import Project, ParsedOrderModel
from app.models.landing import LandingPage, LandingContent
from app.schemas.landing import LandingPageModel

logger = logging.getLogger(__name__)


class LandingRepository:
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

    def delete_existing_landing(self, project_id: str) -> None:
        """
        Delete existing landing (page + content cascade) for a project.
        Called before creating a fresh generation — MVP has one landing per project.
        """
        existing = (
            self.db.query(LandingPage)
            .filter(LandingPage.project_id == project_id)
            .first()
        )
        if existing:
            self.db.delete(existing)
            self.db.commit()
            logger.info("Deleted existing landing | project=%s | slug=%s",
                        project_id, existing.slug)

    def create_landing_page(
        self,
        project_id: str,
        slug: str,
        template_key: str,
    ) -> LandingPage:
        page = LandingPage(
            project_id=project_id,
            slug=slug,
            template_key=template_key,
            status="draft",
            is_public=False,
        )
        self.db.add(page)
        self.db.commit()
        self.db.refresh(page)
        logger.info("LandingPage created | id=%s | slug=%s | project=%s",
                    page.id, slug, project_id)
        return page

    def create_landing_content(
        self,
        landing_page_id: str,
        model: LandingPageModel,
    ) -> LandingContent:
        content = LandingContent(
            landing_page_id=landing_page_id,
            content_json=model.model_dump(mode="json"),
            version=1,
        )
        self.db.add(content)
        self.db.commit()
        self.db.refresh(content)
        logger.info("LandingContent saved | id=%s | landing=%s",
                    content.id, landing_page_id)
        return content

    def get_landing_by_project(self, project_id: str) -> LandingPage | None:
        return (
            self.db.query(LandingPage)
            .filter(LandingPage.project_id == project_id)
            .first()
        )

    def get_landing_by_slug(self, slug: str) -> LandingPage | None:
        """
        Return LandingPage with eagerly loaded content by slug.
        joinedload prevents DetachedInstanceError when accessing page.content
        after the query returns.
        """
        return (
            self.db.query(LandingPage)
            .options(joinedload(LandingPage.content))
            .filter(LandingPage.slug == slug)
            .first()
        )
