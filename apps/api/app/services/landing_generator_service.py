"""
LandingGeneratorService
───────────────────────
Generates a LandingPageModel JSON from a ParsedOrder.

RULE: AI generates JSON only. Never HTML.

Pipeline (two-step):
  STEP 1 — semantic draft
    _generate_semantic_draft(parsed_order) → _SemanticDraft
    Focused on quality of thought: hero subtitle, work context, similar case.
    Private dataclass — not a public contract, not persisted.
    Falls back to empty draft on any failure so step 2 can still proceed.

  STEP 2 — JSON packaging
    _generate_landing_json(parsed_order, draft, ...) → LandingPageModel
    Focused on schema correctness.
    SemanticDraft fields are injected deterministically in code after AI output
    and before validation — not relying on prompt instructions alone.

No DB access. No HTTP. Receives ParsedOrder + overrides, returns LandingPageModel.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.schemas.order import ParsedOrder
from app.schemas.landing import LandingPageModel
from app.services.openai_client import openai_client

logger = logging.getLogger(__name__)

_PACKAGING_PROMPT_PATH = (
    Path(__file__).resolve()
    .parent           # services/
    .parent           # app/
    .parent           # api/
    .parent           # apps/
    .parent           # landing-reply/
    / "packages" / "prompts" / "landing_generate_prompt.txt"
)

# ── Step 1 prompt — semantic quality, not schema ──────────────────────────
_SEMANTIC_DRAFT_PROMPT = """\
You are an experienced photographer writing a personal reply to a client order.

Your task: produce a short structured semantic draft for a micro landing page
based on this specific order. Think like a practitioner, not a copywriter.

Rules:
- Be concrete. Generic statements that could apply to any order are invalid.
- Write in Russian.
- Do not mention price, links, or calls to action.
- Do not describe your services in general.

Return ONLY a JSON object with exactly these six fields:

hero_subtitle
  1 sentence. What is practically important or notable about this specific situation.
  Not about the photographer. About what matters in this shoot format.
  Good: "Регистрация в ЗАГСе обычно занимает 20–30 минут — момент после подписи самый живой."
  Bad: "Я постараюсь передать атмосферу вашего дня."

work_step_1
  1 sentence. First real thing that happens in this type of shoot (not "we discuss details").
  Specific to this event format.

work_step_2
  1 sentence. What usually matters most during this shoot and how to handle it.

work_step_3
  1 sentence. What happens after the shoot that is relevant to this order.

case_title
  Short title of a similar past situation. Include one concrete detail.
  Example: "Регистрация в небольшом зале — 8 гостей, потом короткая прогулка"

case_description
  1 sentence. What was interesting or notable about that situation.
  Not promotional. Relatable.
  Good: "Церемония заняла 15 минут, но после все вышли на улицу и получились лучшие кадры."
  Bad: "Съёмка прошла на высшем уровне."
"""

# ── Repair prompt for step 2 validation failure ───────────────────────────
_REPAIR_PROMPT = """\
The previous JSON output failed schema validation.
Return a corrected complete LandingPageModel JSON object.

Required fields: slug, template_key, hero, price_card, style_grid,
quick_questions (non-empty array of strings), cta.

hero must be an object: { "title": "..." }
price_card must be an object: { "price": "...", "description": "..." }
style_grid must be an object: { "photo_set_id": "..." }
cta must be an object: { "channels": ["telegram", "whatsapp"] }

Return ONLY the corrected JSON object. Nothing else.
"""

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


@dataclass
class _SemanticDraft:
    """
    Private intermediate result of step 1.
    Fields map directly to real LandingPageModel placement targets.
    Local to this service only — not a public contract, not persisted.
    """
    hero_subtitle: str = ""       # → hero.subtitle
    work_steps: list[str] = field(default_factory=list)  # → work_block.steps
    case_title: str = ""          # → similar_case.title (only if both present)
    case_description: str = ""    # → similar_case.description (only if both present)


class LandingGeneratorService:

    def _load_packaging_prompt(self) -> str:
        """Load packaging prompt lazily at generation time."""
        if not _PACKAGING_PROMPT_PATH.exists():
            raise FileNotFoundError(
                f"Landing packaging prompt not found: {_PACKAGING_PROMPT_PATH}"
            )
        return _PACKAGING_PROMPT_PATH.read_text(encoding="utf-8")

    def generate(
        self,
        parsed_order: ParsedOrder,
        photographer_name: str = "Алексей",
        price: str | None = None,
        photo_set_id: str | None = None,
        case_series_id: str | None = None,
    ) -> LandingPageModel:
        """
        Generate LandingPageModel from ParsedOrder via two-step pipeline.

        Step 1: semantic draft — quality of thought.
        Step 2: JSON packaging — schema correctness + deterministic draft injection.

        Returns:
            Validated LandingPageModel.

        Raises:
            ValueError: if step 2 fails after repair retry.
        """
        # ── STEP 1: semantic draft ────────────────────────────────────────
        draft = self._generate_semantic_draft(parsed_order)

        # ── STEP 2: JSON packaging ────────────────────────────────────────
        return self._generate_landing_json(
            parsed_order, draft, photographer_name, price, photo_set_id, case_series_id
        )

    # ── private ───────────────────────────────────────────────────────────

    def _generate_semantic_draft(self, parsed_order: ParsedOrder) -> _SemanticDraft:
        """
        Step 1 — meaning generation.
        Returns _SemanticDraft. Falls back to empty draft on any failure
        so step 2 can still proceed (old single-step behaviour as fallback).
        """
        user_message = self._build_order_context(parsed_order)

        try:
            raw = openai_client.extract_json(
                system_prompt=_SEMANTIC_DRAFT_PROMPT,
                user_message=user_message,
                temperature=0.7,
                max_tokens=500,
            )
        except Exception as exc:
            logger.warning("Semantic draft step failed — proceeding without draft: %s", exc)
            return _SemanticDraft()

        if not isinstance(raw, dict):
            logger.warning("Semantic draft returned non-dict — proceeding without draft")
            return _SemanticDraft()

        # Collect work steps — only non-empty strings
        work_steps = [
            s for s in [
                raw.get("work_step_1") or "",
                raw.get("work_step_2") or "",
                raw.get("work_step_3") or "",
            ]
            if s.strip()
        ]

        return _SemanticDraft(
            hero_subtitle=raw.get("hero_subtitle") or "",
            work_steps=work_steps,
            case_title=raw.get("case_title") or "",
            case_description=raw.get("case_description") or "",
        )

    def _generate_landing_json(
        self,
        parsed_order: ParsedOrder,
        draft: _SemanticDraft,
        photographer_name: str,
        price: str | None,
        photo_set_id: str | None,
        case_series_id: str | None,
    ) -> LandingPageModel:
        """
        Step 2 — JSON packaging.
        AI generates structural fields. SemanticDraft fields are injected
        deterministically in code after AI output and before validation.
        """
        packaging_prompt = self._load_packaging_prompt()
        user_message = self._build_packaging_message(
            parsed_order, photographer_name, price, photo_set_id, case_series_id
        )

        # ── first attempt ─────────────────────────────────────────────────
        raw = openai_client.extract_json(
            system_prompt=packaging_prompt,
            user_message=user_message,
            temperature=0.2,
            max_tokens=1500,
        )

        if not isinstance(raw, dict):
            raise ValueError(
                f"Step 2 AI returned non-object response (type={type(raw).__name__})."
            )

        patched = self._inject_draft(raw, draft)
        cleaned = self._post_process(patched, parsed_order, photo_set_id)

        try:
            model = LandingPageModel.model_validate(cleaned)
            logger.info("Landing generated | slug=%s | template=%s", model.slug, model.template_key)
            return model
        except ValidationError as exc:
            logger.warning(
                "Landing validation failed on first attempt — retrying\n%s", str(exc)
            )

        # ── one repair retry ──────────────────────────────────────────────
        repair_user = (
            f"Original context:\n{user_message}\n\n"
            f"Previous output that failed validation:\n{cleaned}"
        )

        raw2 = openai_client.extract_json(
            system_prompt=_REPAIR_PROMPT,
            user_message=repair_user,
            temperature=0.1,
            max_tokens=1500,
        )

        if not isinstance(raw2, dict):
            raise ValueError(
                f"Repair attempt returned non-object response (type={type(raw2).__name__})."
            )

        patched2 = self._inject_draft(raw2, draft)
        cleaned2 = self._post_process(patched2, parsed_order, photo_set_id)

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

    def _inject_draft(
        self, raw: dict[str, Any], draft: _SemanticDraft
    ) -> dict[str, Any]:
        """
        Deterministically inject SemanticDraft fields into the raw AI dict
        before post-processing and validation.

        Only injects when draft field is non-empty.
        Never overwrites with empty values.
        """
        result = dict(raw)

        # hero.subtitle — inject if draft produced one
        if draft.hero_subtitle:
            if not isinstance(result.get("hero"), dict):
                result["hero"] = {}
            result["hero"]["subtitle"] = draft.hero_subtitle

        # work_block.steps — inject if draft produced steps
        # Safe fallback: if draft has fewer than 3 steps, pad with a neutral step
        if draft.work_steps:
            steps = list(draft.work_steps)
            while len(steps) < 3:
                steps.append("Финальная обработка и передача фото")
            result["work_block"] = {"steps": steps[:3]}

        # similar_case — inject only when both title AND description are present
        if draft.case_title and draft.case_description:
            result["similar_case"] = {
                "title": draft.case_title,
                "description": draft.case_description,
            }

        return result

    def _build_order_context(self, o: ParsedOrder) -> str:
        """Flat key-value block for step 1 semantic draft prompt."""
        return "\n".join([
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
            f"tone_signal: {o.tone_signal or ''}",
        ])

    def _build_packaging_message(
        self,
        o: ParsedOrder,
        photographer_name: str,
        price: str | None,
        photo_set_id: str | None,
        case_series_id: str | None,
    ) -> str:
        """User message for step 2 packaging prompt."""
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
        Minimal structural repairs before Pydantic validation.
        Only fixes missing or wrong-typed structural fields.
        Never generates copy or overwrites non-empty valid values.
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