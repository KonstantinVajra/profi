"""
Pydantic schemas for the dialogue copilot pipeline.
"""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, model_validator


# ── Enums ─────────────────────────────────────────────────────────────────

DetectedIntent = Literal[
    "ask_price",
    "ask_deliverables",
    "ask_availability",
    "hesitation",
    "comparison",
    "booking_signal",
    "other",
]

FunnelStage = Literal[
    "new_lead", "replied", "opened", "engaged", "qualified", "booked", "lost"
]

SuggestionType = Literal["warm", "short", "expert"]

REQUIRED_SUGGESTION_TYPES: set[str] = {"warm", "short", "expert"}


# ── Sub-schemas ───────────────────────────────────────────────────────────

class DialogueReplySuggestionItem(BaseModel):
    type: SuggestionType
    text: str


# ── Request ───────────────────────────────────────────────────────────────

class DialogueReplyRequest(BaseModel):
    message_text: str
    source_channel: str = "profi"     # profi | telegram | whatsapp | other


# ── AI output (validated internally by service) ───────────────────────────

class DialogueAIOutput(BaseModel):
    """Direct shape expected from OpenAI response."""
    detected_intent: DetectedIntent
    detected_stage: FunnelStage
    suggestions: list[DialogueReplySuggestionItem]
    next_best_question: str

    @model_validator(mode="after")
    def validate_suggestions(self) -> "DialogueAIOutput":
        types = {s.type for s in self.suggestions}
        missing = REQUIRED_SUGGESTION_TYPES - types
        if missing:
            raise ValueError(f"Missing suggestion types: {missing}")
        return self


# ── Response ──────────────────────────────────────────────────────────────

class DialogueSuggestionResponse(BaseModel):
    """API response for POST /projects/{project_id}/dialogue/reply."""
    id: str
    project_id: str
    source_message_id: str
    detected_intent: str
    detected_stage: str
    suggestions: list[DialogueReplySuggestionItem]
    next_best_question: str
    created_at: datetime

    class Config:
        from_attributes = True
