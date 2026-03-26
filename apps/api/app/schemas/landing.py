"""
Pydantic schemas for landing generation pipeline.

LandingPageModel — AI output contract. AI generates this JSON. Never HTML.
LandingGenerateRequest — optional overrides (price, photo_set_id, etc.)
LandingGenerateResponse — API response shape
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator
from app.schemas.photo import PRESET_CATEGORIES


# ── LandingPageModel sub-blocks ───────────────────────────────────────────

class HeroBlock(BaseModel):
    title: str
    subtitle: Optional[str] = None


class BadgesBlock(BaseModel):
    items: list[str] = []     # short trust signals e.g. ["100+ свадеб", "RAW включены"]


class PriceCard(BaseModel):
    price: str                # formatted: "15 000 ₽" or "от 12 000 ₽"
    description: str          # what's included: "1 час • обработанные фото • исходники"


class Photographer(BaseModel):
    name: str
    role: str


class StyleGrid(BaseModel):
    photo_set_id: str         # references a pre-uploaded set in DB


class SimilarCase(BaseModel):
    case_series_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class WorkBlock(BaseModel):
    steps: list[str] = []    # how the work goes: ["Созвон", "Съёмка", "Сдача фото"]


class ReviewItem(BaseModel):
    review_id: Optional[str] = None
    author: Optional[str] = None
    text: Optional[str] = None


class QuickQuestion(BaseModel):
    label: str               # button label shown to client: "Проверить дату"
    action: str = "contact"  # contact | scroll | link


class CtaBlock(BaseModel):
    channels: list[str] = ["telegram", "whatsapp"]


class PersonalBlock(BaseModel):
    """
    Editorial block: a reaction to this specific order.
    Sequence: request_match → key_feature → trust_line → hook_line.
    The block is optional on LandingPageModel.
    If present, all four fields are required — no partial states.
    AI must never generate HTML in these fields.
    """
    request_match: str
    key_feature: str
    trust_line: str
    hook_line: str


# ── LandingPageModel — full contract ─────────────────────────────────────

class RelatedBlock(BaseModel):
    """Optional related photo series block. Stores filter only — no embedded data."""
    category_key: str

    @model_validator(mode="after")
    def validate_category_key(self) -> "RelatedBlock":
        if self.category_key not in PRESET_CATEGORIES:
            raise ValueError(
                f"related_block.category_key '{self.category_key}' is not valid. "
                f"Allowed: {PRESET_CATEGORIES}"
            )
        return self


class LandingPageModel(BaseModel):
    """
    JSON model for a micro landing page.
    AI generates this. The frontend renders it via template.
    AI must NEVER generate HTML.
    """
    slug: str
    template_key: str

    # required MVP render fields
    hero: HeroBlock
    price_card: PriceCard
    style_grid: StyleGrid
    quick_questions: list[str]
    cta: CtaBlock

    # optional blocks
    badges: Optional[BadgesBlock] = None
    photographer: Optional[Photographer] = None
    similar_case: Optional[SimilarCase] = None
    work_block: Optional[WorkBlock] = None
    reviews: list[ReviewItem] = []
    secondary_actions: list[str] = []
    personal_block: Optional[PersonalBlock] = None
    # Primary landing content (MVP). Populated from Step 1 AI output only.
    # Semantic blocks (work_block, similar_case, etc.) are secondary / legacy.
    # AI must never generate HTML in this field.
    final_text: Optional[str] = None
    # Short messenger hook (2–4 lines) from Step 1. Sent to client before landing link.
    # AI must never generate HTML in this field.
    entry_message: Optional[str] = None
    # Optional related photo series block. Stores category_key filter only.
    # AI must never generate this field — injected from user input only.
    related_block: Optional[RelatedBlock] = None
    # Explicit user-edited title for MVP header rendering.
    # Distinct from hero.title (structural/AI-generated, used in legacy mode only).
    # None = not user-edited → renderer falls back to TEMPLATE_TITLE[template_key].
    # AI must never generate this field — injected from user input only.
    hero_title_override: Optional[str] = None

    @field_validator("quick_questions")
    @classmethod
    def must_have_questions(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("quick_questions must not be empty")
        return v

    @field_validator("slug")
    @classmethod
    def slug_is_safe(cls, v: str) -> str:
        import re
        if not re.match(r'^[a-z0-9\-]+$', v):
            raise ValueError(f"slug must be lowercase latin letters, digits and hyphens. Got: {v!r}")
        return v


# ── Request / Response ────────────────────────────────────────────────────

class LandingGenerateRequest(BaseModel):
    """Optional overrides for landing generation."""
    price: Optional[str] = None             # e.g. "15 000 ₽" — overrides AI suggestion
    photo_set_id: Optional[str] = None      # override photo set selection
    case_series_id: Optional[str] = None    # override similar case
    review_ids: list[str] = []              # review IDs to include
    related_block: Optional[RelatedBlock] = None  # optional related photo series filter
    # Explicit user-edited title. Stored as hero_title_override in LandingPageModel.
    # None = not provided → renderer uses TEMPLATE_TITLE[template_key].
    hero_title_override: Optional[str] = None


class LandingPageMetadata(BaseModel):
    """Metadata row from landing_pages table."""
    id: str
    project_id: str
    slug: str
    template_key: str
    status: str
    is_public: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LandingGenerateResponse(BaseModel):
    """Response for POST /projects/{project_id}/landing/generate."""
    landing_page: LandingPageMetadata
    landing_content: LandingPageModel


class LandingPublicResponse(BaseModel):
    """Response for GET /public/landings/{slug}."""
    landing_page: LandingPageMetadata
    landing_content: LandingPageModel