"""
Pydantic schemas for order parsing pipeline.
"""
from datetime import date
from typing import Optional, Literal
from pydantic import BaseModel, Field


class ParsedOrder(BaseModel):
    """
    Structured data extracted from a raw freelance order by AI.
    Every field is optional — AI fills what it can find.
    """
    client_name: Optional[str] = Field(None, description="First name of the client if mentioned")
    client_label: Optional[str] = Field(None, description="How to address: 'Ксения', 'молодожёны', etc.")
    event_type: Optional[str] = Field(None, description="registry | wedding | family | event | portrait | other")
    event_subtype: Optional[str] = Field(None, description="small_registry | church_wedding | newborn | corporate | etc.")
    city: Optional[str] = Field(None, description="City of the event")
    location: Optional[str] = Field(None, description="Specific venue or address")
    event_date: Optional[date] = Field(None, description="Event date as ISO date")
    date_text: Optional[str] = Field(None, description="Date as written in order, e.g. '11 июня'")
    duration_text: Optional[str] = Field(None, description="Shoot duration as written, e.g. '2 часа'")
    guest_count_text: Optional[str] = Field(None, description="Guest count as written, e.g. 'до 10'")
    budget_max: Optional[int] = Field(None, description="Max budget as integer")
    currency: str = Field("RUB", description="Currency code")
    requirements: list[str] = Field(default_factory=list)
    priority_signals: list[str] = Field(default_factory=list)
    tone_signal: Optional[Literal["formal", "friendly", "neutral"]] = Field(None)
    extracted_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

    # ── semantic inference fields (additive, all optional) ────────────────
    client_intent_line: Optional[str] = Field(
        None,
        description=(
            "One clean sentence capturing what matters most to this client. "
            "AI-normalised, not a verbatim quote. Ready to use in landing copy. "
            "Example: 'Клиенту важны живые кадры без постановки — атмосфера, не режиссура.'"
        ),
    )
    situation_notes: Optional[str] = Field(
        None,
        description=(
            "1-2 sentences: AI inference about what makes this situation practically notable. "
            "Covers venue constraints, timing, format nuances — anything that affects how "
            "the shoot actually goes. Not a client quote. Not a service description. "
            "Example: 'Небольшой зал ЗАГСа, вероятно смешанный свет. "
            "Церемония короткая — важно не пропустить момент сразу после подписи.'"
        ),
    )
    shoot_feel: Optional[str] = Field(
        None,
        description=(
            "Short free-text phrase: expected atmosphere or style as inferred from the order. "
            "3-5 words. Contextual input for copy generation only — not for program logic. "
            "Examples: 'тихий документальный репортаж', 'лёгкая прогулочная съёмка'"
        ),
    )

    class Config:
        from_attributes = True


class OrderInputCreate(BaseModel):
    project_id: str
    raw_text: str


class ParsedOrderResponse(ParsedOrder):
    """ParsedOrder fields plus DB record identifiers."""
    id: str
    project_id: str
    order_input_id: str