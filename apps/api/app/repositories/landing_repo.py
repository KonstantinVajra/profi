"""
LandingRepository
─────────────────
Database access for landing_pages and landing_content.
No business logic — only DB reads and writes.

Methods:
  get_project              — verify project exists
  get_parsed_order         — load latest ParsedOrder for project
  delete_existing_landing  — remove current landing (dev/admin only — not called on regenerate)
  create_landing_page      — insert landing_pages row (first generation only)
  create_landing_content   — insert landing_content row (first generation only)
  update_landing_content   — replace content_json in-place (regeneration — preserves slug)
  update_landing_page      — update template_key if changed (regeneration)
  get_landing_by_project   — return landing + content for a project
  get_landing_by_slug      — return landing + content by slug (public endpoint)

Slug immutability invariant:
  Once a LandingPage exists for a project, its slug NEVER changes.
  On regeneration, the existing slug is the sole source of truth.
  AI-generated slug is used ONLY on first creation and ignored thereafter.
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
        Physically delete the LandingPage (and cascade LandingContent) for a project.

        DEV / ADMIN USE ONLY — e.g. dev_reset.py.
        NOT called on regeneration. Regeneration uses update_landing_content()
        to preserve the slug. Calling this on a live project will permanently
        kill the public URL.
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

    def _unique_slug(self, base_slug: str) -> str:
        """
        Return a slug that does not yet exist in landing_pages.
        If base_slug is free, returns it as-is.
        Otherwise appends -2, -3, ... until a free slot is found.
        """
        candidate = base_slug
        counter = 2
        while (
            self.db.query(LandingPage)
            .filter(LandingPage.slug == candidate)
            .first()
        ):
            candidate = f"{base_slug}-{counter}"
            counter += 1
        return candidate

    def create_landing_page(
        self,
        project_id: str,
        slug: str,
        template_key: str,
    ) -> LandingPage:
        unique = self._unique_slug(slug)
        if unique != slug:
            logger.info("Slug collision resolved | original=%s | used=%s", slug, unique)
        page = LandingPage(
            project_id=project_id,
            slug=unique,
            template_key=template_key,
            status="draft",
            is_public=False,
        )
        self.db.add(page)
        self.db.commit()
        self.db.refresh(page)
        logger.info("LandingPage created | id=%s | slug=%s | project=%s",
                    page.id, unique, project_id)
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

    def update_landing(
        self,
        existing_page: LandingPage,
        model: LandingPageModel,
    ) -> LandingPage:
        """
        Atomically update LandingPage + LandingContent in one commit.

        Slug is NEVER changed — immutability invariant.
        model.slug must already be normalised to existing_page.slug by caller
        before this method is called.

        Updates:
          - LandingPage.template_key (only if changed)
          - LandingContent.content_json (always replaced)
          - LandingContent.version (incremented)

        If LandingContent is missing (should not happen in normal flow),
        creates it within the same transaction.

        Use this method for all regeneration. Do not call update_landing_page()
        and update_landing_content() separately — they commit independently.
        """
        if existing_page.template_key != model.template_key:
            logger.info(
                "LandingPage template_key updated | id=%s | %s → %s",
                existing_page.id, existing_page.template_key, model.template_key,
            )
            existing_page.template_key = model.template_key

        content = existing_page.content
        if content is None:
            # Defensive: create if somehow absent — within same transaction.
            logger.warning(
                "LandingContent missing for existing landing — creating | landing=%s",
                existing_page.id,
            )
            content = LandingContent(
                landing_page_id=existing_page.id,
                content_json=model.model_dump(mode="json"),
                version=1,
            )
            self.db.add(content)
        else:
            content.content_json = model.model_dump(mode="json")
            content.version = (content.version or 1) + 1

        # Single commit — both LandingPage and LandingContent in one transaction.
        self.db.commit()
        self.db.refresh(existing_page)
        self.db.refresh(content)

        logger.info(
            "Landing updated atomically | id=%s | slug=%s | version=%s",
            existing_page.id, existing_page.slug, content.version,
        )
        return existing_page

    def update_landing_content(
        self,
        existing_page: LandingPage,
        model: LandingPageModel,
    ) -> LandingContent:
        """
        Replace content_json in-place on regeneration.
        Slug on existing_page is NOT touched — immutability invariant.
        If LandingContent is missing (should not happen), creates it.
        """
        content = existing_page.content
        if content is None:
            # Defensive: create if somehow absent
            logger.warning(
                "LandingContent missing for existing landing — creating | landing=%s",
                existing_page.id,
            )
            return self.create_landing_content(existing_page.id, model)

        content.content_json = model.model_dump(mode="json")
        content.version = (content.version or 1) + 1
        self.db.commit()
        self.db.refresh(content)
        logger.info(
            "LandingContent updated in-place | id=%s | landing=%s | version=%s",
            content.id, existing_page.id, content.version,
        )
        return content

    def update_landing_page(
        self,
        existing_page: LandingPage,
        template_key: str,
    ) -> LandingPage:
        """
        Update template_key only if it changed.
        Slug is NEVER changed — immutability invariant.
        """
        if existing_page.template_key != template_key:
            logger.info(
                "LandingPage template_key updated | id=%s | %s → %s",
                existing_page.id, existing_page.template_key, template_key,
            )
            existing_page.template_key = template_key
            self.db.commit()
            self.db.refresh(existing_page)
        return existing_page

    def get_landing_by_project(self, project_id: str) -> LandingPage | None:
        """
        Return LandingPage with eagerly loaded content for a project.
        joinedload prevents DetachedInstanceError when accessing page.content.
        """
        return (
            self.db.query(LandingPage)
            .options(joinedload(LandingPage.content))
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