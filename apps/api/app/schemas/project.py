from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class ContactInfo(BaseModel):
    """
    Photographer contact values. Used by frontend to build CTA button hrefs.
    All fields optional — channels with no value produce no button.

    Storage convention (enforced by ProjectContactUpdate validator):
      - telegram / instagram: stored WITHOUT leading @
      - all values: stripped of surrounding whitespace
      - empty string after strip → stored as None
    """
    whatsapp: Optional[str] = None
    telegram: Optional[str] = None
    phone: Optional[str] = None
    instagram: Optional[str] = None
    vk: Optional[str] = None


class ProjectContactUpdate(BaseModel):
    """Request body for PATCH /projects/{id}/contacts."""
    contact_info: ContactInfo

    @field_validator("contact_info", mode="before")
    @classmethod
    def trim_and_normalise(cls, v: object) -> object:
        """
        Trim whitespace from all string values.
        Strip leading @ from telegram and instagram usernames.
        Empty string after processing → None.
        """
        if not isinstance(v, dict):
            return v
        result: dict[str, Optional[str]] = {}
        for key, val in v.items():
            if isinstance(val, str):
                val = val.strip()
                if key in ("telegram", "instagram") and val.startswith("@"):
                    val = val[1:]
                result[key] = val if val else None
            else:
                result[key] = val  # None passes through unchanged
        return result


class ProjectCreate(BaseModel):
    title: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    title: Optional[str]
    status: str
    created_at: datetime
    contact_info: Optional[ContactInfo] = None

    class Config:
        from_attributes = True
