"""
DB models for landing_pages and landing_content tables.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class LandingPage(Base):
    """Metadata row — one per project in MVP."""
    __tablename__ = "landing_pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    template_key: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    content: Mapped[Optional["LandingContent"]] = relationship(
        back_populates="landing_page", cascade="all, delete-orphan", uselist=False
    )


class LandingContent(Base):
    """Full LandingPageModel stored as JSON."""
    __tablename__ = "landing_content"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    landing_page_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("landing_pages.id", ondelete="CASCADE"),
        nullable=False, unique=True
    )
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    landing_page: Mapped["LandingPage"] = relationship(back_populates="content")
