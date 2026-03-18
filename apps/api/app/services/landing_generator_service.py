"""
LandingGeneratorService
───────────────────────
Generates a LandingPageModel JSON from a ParsedOrder.

RULE: AI generates JSON only. Never HTML.

Pipeline:
  1. load main prompt from packages/prompts/landing_generate_prompt.txt
  2. build user message from ParsedOrder + overrides
  3. call OpenAI via openai_client.extract_json()
  4. validate raw output is dict
  5. post-process (structural repairs before validation)
  6. validate against LandingPageModel Pydantic schema
  7. on ValidationError: one repair retry with focused repair prompt
  8. return LandingPageModel or raise controlled ValueError
"""

import logging
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.schemas.order import ParsedOrder
from app.schemas.landing import LandingPageModel
from app.services.openai_client import openai_client

logger = logging.getLogger(__name__)

_PROMPT_PATH = (
    Path(__file__).resolve()
    .parent           # services/
    .parent           # app/
    .parent           # api/
    .parent           # apps/
    .parent           # landing-reply/
    / "packages" / "prompts" / "landing_generate_prompt.txt"
)

# Minimal repair prompt — only instructs correction, no schema duplication.
_REPAIR_PROMPT = """\
The previous JSON output failed schema validation.
Return a corrected complete LandingPageModel JSON object.

Required fields: slug, template_key, hero, price_card, style_grid,
quick_questions (non-empty), cta, personal_block.

Return ONLY the corrected JSON object. Nothing else.
"""

_TEMPLATE_MAP: dict[str, str] = {
    "registry": "registry_small",
    "wedding":  "wedding_full",
    "family":   "family_session",
    "event":    "event_general",
    "portrait": "family_session",
    "other":    "registry_small",
}

_PHOTO_SET_MAP: dict[str, str] = {
    "registry": "registry_light",
    "wedding":  "wedding_outdoor",
    "family":   "family_warm",
    "event":    "event_reportage",
    "portrait": "portrait_natural",
}


class LandingGeneratorService:

    def _load_main_prompt(self) -> str:
        if not _PROMPT_PATH.exists():
            raise FileNotFoundError(
                f"Landing generation prompt not found: {_PROMPT_PATH}"
            )
        return _PROMPT_PATH.read_text(encoding="utf-8")

    def generate(
        self,
        parsed_order: ParsedOrder,
        photographer_name: str = "Алексей",
        price: str | None = None,
        photo_set_id: str | None = None,
        case_series_id: str | None = None,
    ) -> LandingPageModel:

        system_prompt = self._load_main_prompt()
        user_message = self._build_user_message(
            parsed_order, photographer_name, price, photo_set_id, case_series_id
        )

        # ── first attempt ─────────────────────────────────────────────────
        raw = openai_client.extract_json(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.5,
            max_tokens=1200,
        )

        if not isinstance(raw, dict):
            raise ValueError(
                f"AI returned non-object response (type={type(raw).__name__}). "
                "Expected a JSON object."
            )

        cleaned = self._post_process(raw, parsed_order, photo_set_id)

        try:
            model = LandingPageModel.model_validate(cleaned)
            logger.info("Landing generated | slug=%s", model.slug)
            return model
        except ValidationError as exc:
            logger.warning(
                "Landing validation failed on first attempt — retrying\n%s", str(exc)
            )

        # ── one repair retry ──────────────────────────────────────────────
        repair_user = (
            f"Original order context:\n{user_message}\n\n"
            f"Previous output that failed validation:\n{cleaned}"
        )

        raw2 = openai_client.extract_json(
            system_prompt=_REPAIR_PROMPT,
            user_message=repair_user,
            temperature=0.2,
            max_tokens=1200,
        )

        if not isinstance(raw2, dict):
            raise ValueError(
                f"Repair attempt returned non-object response (type={type(raw2).__name__})."
            )

        cleaned2 = self._post_process(raw2, parsed_order, photo_set_id)

        try:
            model = LandingPageModel.model_validate(cleaned2)
            logger.info("Landing generated after repair | slug=%s", model.slug)
            return model
        except ValidationError as exc2:
            logger.error(
                "Landing validation failed after repair\n%s\nraw=%s", str(exc2), cleaned2
            )
            raise ValueError(
                f"Landing generation failed after repair attempt: {exc2}"
            ) from exc2

    # ── private ───────────────────────────────────────────────────────────

    def _build_user_message(
        self,
        o: ParsedOrder,
        photographer_name: str,
        price: str | None,
        photo_set_id: str | None,
        case_series_id: str | None,
    ) -> str:
        proposed_price = price or (f"до {o.budget_max} ₽" if o.budget_max else "не указана")

        lines = [
            f"client_label: {o.client_label or o.client_name or 'клиент'}",
            f"event_type: {o.event_type or ''}",
            f"event_subtype: {o.event_subtype or ''}",
            f"date: {o.date_text or ''}",
            f"city: {o.city or ''}",
            f"location: {o.location or ''}",
            f"duration: {o.duration_text or ''}",
            f"guest_count: {o.guest_count_text or ''}",
            "",
            f"requirements: {', '.join(o.requirements) if o.requirements else ''}",
            f"priority_signals: {', '.join(o.priority_signals) if o.priority_signals else ''}",
            "",
            f"client_intent_line: {o.client_intent_line or ''}",
            f"situation_notes: {o.situation_notes or ''}",
            f"shoot_feel: {o.shoot_feel or ''}",
            "",
            f"photographer_name: {photographer_name}",
            f"price: {proposed_price}",
        ]
        if photo_set_id:
            lines.append(f"preferred_photo_set_id: {photo_set_id}")
        if case_series_id:
            lines.append(f"preferred_case_series_id: {case_series_id}")

        return "\n".join(lines)

    def _post_process(
        self,
        raw: dict[str, Any],
        parsed_order: ParsedOrder,
        photo_set_id_override: str | None = None,
    ) -> dict[str, Any]:
        """
        Minimal structural repairs before Pydantic validation.
        Only fixes missing or wrong-typed structural fields.
        Never generates copy or overwrites non-empty valid values.
        """
        result = dict(raw)

        # ── slug ──────────────────────────────────────────────────────────
        result["slug"] = self._safe_slug(result.get("slug", ""), parsed_order)

        # ── template_key ──────────────────────────────────────────────────
        if not result.get("template_key"):
            event_type = (parsed_order.event_type or "other").lower()
            result["template_key"] = _TEMPLATE_MAP.get(event_type, "registry_small")

        # ── style_grid ────────────────────────────────────────────────────
        if not isinstance(result.get("style_grid"), dict):
            result["style_grid"] = {}
        if photo_set_id_override:
            result["style_grid"]["photo_set_id"] = photo_set_id_override
        elif not result["style_grid"].get("photo_set_id"):
            event_type = (parsed_order.event_type or "registry").lower()
            result["style_grid"]["photo_set_id"] = _PHOTO_SET_MAP.get(
                event_type, "registry_light"
            )

        # ── cta.channels ──────────────────────────────────────────────────
        if not isinstance(result.get("cta"), dict):
            result["cta"] = {}
        if not result["cta"].get("channels"):
            result["cta"]["channels"] = ["telegram", "whatsapp"]

        # ── list field defaults ───────────────────────────────────────────
        for key in ("quick_questions", "reviews", "secondary_actions"):
            if not isinstance(result.get(key), list):
                result[key] = []

        # quick_questions must be non-empty (schema validator requires it)
        if not result["quick_questions"]:
            result["quick_questions"] = [
                "Уточнить детали",
                "Узнать стоимость",
                "Задать вопрос",
            ]

        # ── personal_block: remove if AI returned a string ────────────────
        # Validation will fail cleanly; retry can produce a correct object.
        if isinstance(result.get("personal_block"), str):
            logger.warning("personal_block was a string — removing before validation")
            del result["personal_block"]

        return result

    def _safe_slug(self, raw: str, parsed_order: ParsedOrder) -> str:
        if raw and re.match(r'^[a-z0-9\-]+$', raw):
            return raw[:60]

        parts = []

        if parsed_order.client_name:
            parts.append(parsed_order.client_name.lower())

        if parsed_order.event_type:
            parts.append(parsed_order.event_type)

        if parsed_order.date_text:
            parts.append(parsed_order.date_text)

        slug = "-".join(parts)
        slug = re.sub(r'[^a-z0-9\-]+', '-', slug.lower())
        slug = re.sub(r'-+', '-', slug).strip('-')

        return slug[:60] or "landing"


landing_generator_service = LandingGeneratorService()