"""
Pydantic schemas for reply generation pipeline.
"""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, field_validator


VariantType = Literal["short", "warm", "expert"]

REQUIRED_TYPES: set[str] = {"short", "warm", "expert"}


class ReplyVariant(BaseModel):
    """
    AI output shape. Validated strictly — message_text must contain
    {{landing_url}} placeholder exactly as produced by the LLM.
    """
    variant_type: VariantType
    message_text: str
    preview_text: str
    includes_link: bool = True
    is_selected: bool = False

    @field_validator("message_text")
    @classmethod
    def must_contain_placeholder(cls, v: str) -> str:
        if "{{landing_url}}" not in v:
            raise ValueError("message_text must contain {{landing_url}} placeholder")
        return v


class ReplyVariantRecord(BaseModel):
    """
    DB / API response shape. Does NOT validate the placeholder —
    message_text may contain a substituted real URL at this point.
    """
    variant_type: VariantType
    message_text: str
    preview_text: str
    includes_link: bool = True
    is_selected: bool = False
    id: str
    project_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# keep alias so existing imports don't break
ReplyVariantResponse = ReplyVariantRecord


class ReplyGenerateRequest(BaseModel):
    """Optional landing_url to substitute the {{landing_url}} placeholder in replies."""
    landing_url: Optional[str] = None


class ReplyGenerateResponse(BaseModel):
    """Response for POST /projects/{project_id}/replies/generate."""
    project_id: str
    reply_variants: list[ReplyVariantRecord]
