"""
LandingGeneratorService
───────────────────────
Generates a LandingPageModel JSON from a ParsedOrder.

RULE: AI generates JSON only. Never HTML.

Pipeline:
  1. load prompt from packages/prompts/landing_generate_prompt.txt
  2. build user message from ParsedOrder + request overrides
  3. call OpenAI via openai_client.extract_json()
  4. post-process raw dict (slug safety, required field defaults)
  5. validate against LandingPageModel Pydantic schema
  6. return LandingPageModel

No DB access. No HTTP. Receives ParsedOrder + overrides, returns LandingPageModel.
"""

import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

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

# Normalised event_type → template_key
_TEMPLATE_MAP: dict[str, str] = {
    "registry":  "registry_small",
    "wedding":   "wedding_full",
    "family":    "family_session",
    "event":     "event_general",
    "portrait":  "family_session",
    "other":     "registry_small",
}

# Normalised event_type → default photo_set_id
_PHOTO_SET_MAP: dict[str, str] = {
    "registry":  "registry_light",
    "wedding":   "wedding_outdoor",
    "family":    "family_warm",
    "event":     "event_reportage",
    "portrait":  "portrait_natural",
}


class LandingGeneratorService:
    def __init__(self) -> None:
        self._system_prompt = _PROMPT_PATH.read_text(encoding="utf-8")

    def generate(
        self,
        parsed_order: ParsedOrder,
        photographer_name: str = "Алексей",
        price: str | None = None,
        photo_set_id: str | None = None,
        case_series_id: str | None = None,
    ) -> LandingPageModel:
        """
        Generate LandingPageModel from ParsedOrder.

        Args:
            parsed_order:     confirmed order fields
            photographer_name: freelancer name shown on landing
            price:            optional price override (formatted string)
            photo_set_id:     optional photo set override
            case_series_id:   optional similar case override

        Returns:
            Validated LandingPageModel.

        Raises:
            ValueError: if AI output fails validation.
        """
        user_message = self._build_user_message(
            parsed_order, photographer_name, price, photo_set_id, case_series_id
        )

        raw = openai_client.extract_json(
            system_prompt=self._system_prompt,
            user_message=user_message,
            temperature=0.4,   # lower than replies — structure matters more than variety
            max_tokens=1500,
        )

        cleaned = self._post_process(raw, parsed_order, photo_set_id)

        try:
            model = LandingPageModel.model_validate(cleaned)
        except Exception as exc:
            logger.error("LandingPageModel validation failed: %s | raw: %s", exc, cleaned)
            raise ValueError(f"AI output did not match LandingPageModel schema: {exc}") from exc

        logger.info("Landing generated | slug=%s | template=%s", model.slug, model.template_key)
        return model

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
            f"date_text: {o.date_text or ''}",
            f"event_date: {o.event_date.isoformat() if o.event_date else ''}",
            f"city: {o.city or ''}",
            f"location: {o.location or ''}",
            f"duration_text: {o.duration_text or ''}",
            f"guest_count_text: {o.guest_count_text or ''}",
            f"budget_max: {o.budget_max or ''}",
            f"requirements: {', '.join(o.requirements) if o.requirements else ''}",
            f"priority_signals: {', '.join(o.priority_signals) if o.priority_signals else ''}",
            f"client_intent_line: {o.client_intent_line or ''}",
            f"situation_notes: {o.situation_notes or ''}",
            f"shoot_feel: {o.shoot_feel or ''}",
            f"photographer_name: {photographer_name}",
            f"proposed_price: {proposed_price}",
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
        photo_set_id_override: str | None,
    ) -> dict[str, Any]:
        """
        Minimal structural fixes before Pydantic validation.

        Allowed:
          - slug safety + fallback build
          - template_key fallback from event_type
          - photo_set_id override or event_type fallback
          - empty list defaults for strict schema fields
          - cta.channels fallback

        Not allowed:
          - generating landing copy in code
          - substituting missing AI text with handcrafted strings
        """
        result = dict(raw)

        # ── slug ─────────────────────────────────────────────────────────
        result["slug"] = self._safe_slug(result.get("slug", ""), parsed_order)

        # ── template_key ─────────────────────────────────────────────────
        if not result.get("template_key"):
            event_type = (parsed_order.event_type or "other").lower()
            result["template_key"] = _TEMPLATE_MAP.get(event_type, "registry_small")

        # ── style_grid.photo_set_id ───────────────────────────────────────
        if not isinstance(result.get("style_grid"), dict):
            result["style_grid"] = {}
        if photo_set_id_override:
            result["style_grid"]["photo_set_id"] = photo_set_id_override
        elif not result["style_grid"].get("photo_set_id"):
            event_type = (parsed_order.event_type or "registry").lower()
            result["style_grid"]["photo_set_id"] = _PHOTO_SET_MAP.get(event_type, "registry_light")

        # ── list field defaults (schema requires list, never None) ────────
        for key in ("quick_questions", "reviews", "secondary_actions"):
            if not isinstance(result.get(key), list):
                result[key] = []

        # ── cta.channels ─────────────────────────────────────────────────
        if not isinstance(result.get("cta"), dict):
            result["cta"] = {}
        if not result["cta"].get("channels"):
            result["cta"]["channels"] = ["telegram", "whatsapp"]

        return result

    def _safe_slug(self, raw: str, parsed_order: ParsedOrder) -> str:
        """
        Ensure slug is URL-safe: lowercase, latin, hyphens only.
        If AI returned an invalid slug, build one from ParsedOrder fields.
        Falls back to a UUID-based slug if nothing is available.
        """
        if raw and re.match(r'^[a-z0-9\-]+$', raw):
            return raw[:60]

        # build from ParsedOrder
        parts: list[str] = []

        label = parsed_order.client_label or parsed_order.client_name
        if label:
            parts.append(self._to_latin(label.split()[0]))

        if parsed_order.event_type:
            type_map = {
                "registry": "registry", "wedding": "wedding",
                "family": "family", "event": "event", "portrait": "portrait",
            }
            parts.append(type_map.get(parsed_order.event_type, parsed_order.event_type))

        if parsed_order.date_text:
            parts.append(self._to_latin(parsed_order.date_text))
        elif parsed_order.event_date:
            parts.append(parsed_order.event_date.strftime("%d-%b").lower())

        if parts:
            slug = "-".join(p for p in parts if p)
            slug = re.sub(r'-+', '-', slug).strip('-')
            return slug[:60] or "landing"

        import uuid
        return f"landing-{str(uuid.uuid4())[:8]}"

    @staticmethod
    def _to_latin(text: str) -> str:
        """Transliterate Russian to latin, keep digits, replace spaces with hyphens."""
        RU_TO_LATIN = {
            'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh',
            'з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o',
            'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts',
            'ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu',
            'я':'ya',
        }
        result = []
        for ch in text.lower():
            if ch in RU_TO_LATIN:
                result.append(RU_TO_LATIN[ch])
            elif ch.isalnum():
                result.append(ch)
            elif ch in (' ', '-', '_'):
                result.append('-')
        slug = ''.join(result)
        return re.sub(r'-+', '-', slug).strip('-')


landing_generator_service = LandingGeneratorService()