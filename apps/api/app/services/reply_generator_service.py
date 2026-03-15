"""
ReplyGeneratorService
─────────────────────
Generates 3 reply variants from a ParsedOrder.

Pipeline:
  1. load prompt from packages/prompts/reply_generate_prompt.txt
  2. build user message from ParsedOrder fields
  3. call OpenAI via openai_client.extract_json()
  4. parse response — handle list or wrapped dict
  5. validate each item with ReplyVariant Pydantic schema
  6. enforce exactly one variant per type: short, warm, expert
  7. return list[ReplyVariant]

No DB access. No HTTP. Receives ParsedOrder, returns list[ReplyVariant].
"""

import logging
from pathlib import Path
from typing import Any

from app.schemas.order import ParsedOrder
from app.schemas.reply import ReplyVariant, REQUIRED_TYPES
from app.services.openai_client import openai_client

logger = logging.getLogger(__name__)

_PROMPT_PATH = (
    Path(__file__).resolve()
    .parent           # services/
    .parent           # app/
    .parent           # api/
    .parent           # apps/
    .parent           # landing-reply/
    / "packages" / "prompts" / "reply_generate_prompt.txt"
)


class ReplyGeneratorService:
    def __init__(self) -> None:
        self._system_prompt = _PROMPT_PATH.read_text(encoding="utf-8")

    def generate(self, parsed_order: ParsedOrder) -> list[ReplyVariant]:
        """
        Generate exactly 3 reply variants from a ParsedOrder.

        Returns:
            list[ReplyVariant] with one item per type: short, warm, expert.

        Raises:
            ValueError: if AI output is missing types or fails validation.
        """
        user_message = self._build_user_message(parsed_order)

        raw = openai_client.extract_json(
            system_prompt=self._system_prompt,
            user_message=user_message,
            temperature=0.7,
            max_tokens=1500,
        )

        return self._parse_and_validate(raw)

    # ── private ───────────────────────────────────────────────────────────

    def _build_user_message(self, o: ParsedOrder) -> str:
        """Serialize ParsedOrder into a flat key-value block for the prompt."""
        lines = [
            f"client_label: {o.client_label or o.client_name or 'клиент'}",
            f"event_type: {o.event_type or ''}",
            f"event_subtype: {o.event_subtype or ''}",
            f"date_text: {o.date_text or ''}",
            f"city: {o.city or ''}",
            f"location: {o.location or ''}",
            f"duration_text: {o.duration_text or ''}",
            f"guest_count_text: {o.guest_count_text or ''}",
            f"requirements: {', '.join(o.requirements) if o.requirements else ''}",
            f"priority_signals: {', '.join(o.priority_signals) if o.priority_signals else ''}",
            f"tone_signal: {o.tone_signal or 'neutral'}",
        ]
        return "\n".join(lines)

    def _parse_and_validate(self, raw: Any) -> list[ReplyVariant]:
        """
        Extract list of variant dicts from raw AI response.
        Accepts: direct list, or dict with a single list value.
        Validates each item. Enforces exactly one of each required type.
        """
        # unwrap if AI returned {"variants": [...]} or {"replies": [...]}
        items: list[dict] = []
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            for val in raw.values():
                if isinstance(val, list):
                    items = val
                    break

        if not items:
            raise ValueError(f"AI did not return a list of variants. Got: {type(raw)}")

        # validate each item and collect by type
        by_type: dict[str, ReplyVariant] = {}
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping non-dict item: %s", item)
                continue
            try:
                variant = ReplyVariant.model_validate(item)
            except Exception as exc:
                logger.warning("Skipping invalid variant: %s | error: %s", item, exc)
                continue

            # keep first occurrence of each type — ignore extras
            if variant.variant_type not in by_type:
                by_type[variant.variant_type] = variant

        # enforce all 3 types present
        missing = REQUIRED_TYPES - set(by_type.keys())
        if missing:
            raise ValueError(
                f"AI response missing required variant types: {missing}. "
                f"Got types: {list(by_type.keys())}"
            )

        # return in fixed order
        return [by_type["short"], by_type["warm"], by_type["expert"]]


reply_generator_service = ReplyGeneratorService()
