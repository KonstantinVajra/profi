"""
DB models for photo_sets and photo_set_items tables.

source_type values:
  preset          — predefined albums created by the photographer, visible in UI
  manual_upload   — temporary upload for one landing generation, not shown in UI lists
  landing_snapshot — copy made during landing generation, owned by that landing
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class PhotoSet(Base):
    __tablename__ = "photo_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # preset | manual_upload | landing_snapshot
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    items: Mapped[list["PhotoSetItem"]] = relationship(
        back_populates="photo_set",
        cascade="all, delete-orphan",
        order_by="PhotoSetItem.display_order",
    )


class PhotoSetItem(Base):
    __tablename__ = "photo_set_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    photo_set_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("photo_sets.id", ondelete="CASCADE"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    photo_set: Mapped["PhotoSet"] = relationship(back_populates="items")
