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
