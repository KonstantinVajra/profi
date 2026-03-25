"""
Pydantic schemas for photo sets.

photo_url is computed in the router/serving layer from storage_key.
storage_key never appears in public responses.
"""

from typing import Optional
from pydantic import BaseModel


# Canonical preset category keys
PRESET_CATEGORIES: list[str] = [
    "wedding",
    "love_story",
    "family",
    "kids",
    "portrait",
    "maternity",
    "business",
    "events",
    "catalog",
    "interior",
    "food",
    "art",
]


class PhotoSetItemResponse(BaseModel):
    id: str
    photo_url: str       # computed: /photos/{item_id} — not a DB field
    display_order: int

    class Config:
        from_attributes = True


class PhotoSetResponse(BaseModel):
    id: str
    name: Optional[str]
    category_key: Optional[str] = None
    items: list[PhotoSetItemResponse] = []

    class Config:
        from_attributes = True


class PhotoUploadResponse(BaseModel):
    """Returned after manual upload. Frontend passes photo_set_id to landing/generate."""
    photo_set_id: str


class PresetCreateResponse(BaseModel):
    """Returned after preset album creation."""
    photo_set_id: str
    name: str


class PresetAlbumSummary(BaseModel):
    """Lightweight preset album summary for category listings."""
    id: str
    name: Optional[str]

    class Config:
        from_attributes = True