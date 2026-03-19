"""
LandingGeneratorService
───────────────────────
Generates a LandingPageModel JSON from a ParsedOrder.

RULE: AI generates JSON only. Never HTML.

Pipeline (two-step):
  STEP 1 — semantic draft
    _generate_semantic_draft(parsed_order) → _SemanticDraft
    AI returns free-form text with labelled blocks [HERO]..[NEXT].
    Deterministic Python parser extracts blocks into _SemanticDraft.
    Block positions are fixed: TIP→0, NUANCE→1, TRUST→2.
    Falls back to empty draft on any failure so step 2 can still proceed.

  STEP 2 — JSON packaging (technical layer)
    _generate_landing_json(parsed_order, draft, ...) → LandingPageModel
    Generates structural fields only: slug, template_key, hero.title,
    price_card, style_grid, quick_questions, cta, badges, photographer.
    Semantic fields are stripped from Step 2 output before injection.
    Step 1 parser is the sole author of semantic text.

Source priority:
  Step 1 parser output > Step 2 AI output > _post_process defaults

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
Ты — AI-ассистент фотографа.

Твоя задача — написать короткий, точный, живой отклик на заказ клиента.

Ты НЕ пишешь JSON.  
Ты НЕ думаешь о фронтенде.  
Ты НЕ думаешь о структуре сайта.  

Ты пишешь человеческий отклик, который потом будет разобран системой.

---

## ФОРМАТ ВЫХОДА (СТРОГО ОБЯЗАТЕЛЕН)

Ты ОБЯЗАН вернуть текст строго в таком формате:

[HERO]
...

[NUANCE]
...

[TIP]
...

[TRUST]
...

[HOOK_KEY]
...

[NEXT]
...

---

### ЖЁСТКИЕ ПРАВИЛА ФОРМАТА

- Нельзя менять названия блоков  
- Нельзя менять порядок блоков  
- Нельзя пропускать блоки  
- Нельзя добавлять новые блоки  
- Нельзя писать текст вне блоков  

Если формат нарушен — ответ считается неправильным.

---

## ГЛАВНЫЙ ПРИНЦИП

Ты не пишешь "отклик фотографа".

Ты объясняешь ОДНУ конкретную ситуацию.

Весь текст должен идти по одной линии:

- что происходит у клиента  
- где в этом формате обычно проблема  
- что лучше сделать  
- почему это важно  
- чем можно помочь  

Если появляются лишние темы — это ошибка.

---

## ПРАВИЛО ОДНОЙ МЫСЛИ

В отклике должен быть ОДИН основной нюанс ситуации.

Не несколько.  
Не список.  
Один.

---

## HERO (ПОПАДАНИЕ В ЗАКАЗ)

Ты обязан начать с обращения.

ЕСЛИ есть имя:
используй имя в первой строке

Пример:
Анна, посмотрел ваш запрос...

ЕСЛИ имени нет:
Посмотрел ваш запрос...

---

### В HERO ОБЯЗАТЕЛЬНО:

- 1–2 конкретные детали заказа  
- живая формулировка ситуации  

---

### ЗАПРЕЩЕНО:

- пересказывать заказ списком  
- писать обобщённо  
- игнорировать имя  

---

## NUANCE

Один конкретный момент, где обычно возникает проблема.

Плохо:
- важно учитывать детали  

Хорошо:
- в коротких съёмках время уходит на перемещения  

---

## TIP (САМОЕ ВАЖНОЕ)

Одна практическая рекомендация.

Обязательно:

- что делать  
- когда делать  
- как это выглядит  

---

### ПЛОХО:

- лучше всё продумать  

### ХОРОШО:

- лучше выбрать 1–2 точки рядом и не ездить между локациями  

---

## TRUST

Одна короткая фраза из опыта.

Без самопрезентации.

Примеры:

- в коротких съёмках ритм решает почти всё  
- чаще всего проблема не во времени, а в суете  

---

## HOOK_KEY

Ты НЕ пишешь текст.

Ты выбираешь ОДИН ключ из списка:

timing  
movement  
restrictions  
lighting  
emotion_flow  
location_spot  
preparation  

Верни только ключ.  
Без пояснений.  

---

## NEXT

Мягкое продолжение.

Без давления.

Примеры:

- могу подсказать маршрут  
- могу накидать точки рядом  
- могу показать похожую съёмку  

---

## ЗАПРЕЩЕНО

Никогда не использовать:

- индивидуальный подход  
- сохраняю эмоции  
- важные моменты  
- работаю с душой  
- учту все пожелания  
- качественная съёмка  

Если фраза подходит к любому заказу — она плохая.

---

## СТИЛЬ

Пиши:

- спокойно  
- коротко  
- по-человечески  
- без пафоса  

Не пытайся "улучшать" текст.  
Если можно сказать проще — говори проще.

---

## САМОПРОВЕРКА

Перед ответом проверь:

- есть ли все 6 блоков  
- есть ли имя (если было)  
- есть ли конкретика  
- есть ли один нюанс  
- есть ли одна практическая фишка  
- нет ли банальщины  

Если нет — перепиши.

---

## ГЛАВНОЕ

Это должен быть не "красивый текст".

Это должно выглядеть как:

человек понял ситуацию  
и спокойно объяснил, что делать\
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

_VALID_HOOK_KEYS = frozenset({
    "timing", "movement", "restrictions",
    "lighting", "emotion_flow", "location_spot", "preparation",
})

_TEMPLATE_MAP: dict[str, str] = {
    "registry":  "registry_small",
    "wedding":   "wedding_full",
    "family":    "family_session",
    "event":     "event_general",
    "portrait":  "family_session",
    "other":     "registry_small",
}

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
    hero_subtitle: str = ""
    work_steps: list[str] = field(default_factory=lambda: ["", "", ""])
    case_title: str = ""
    case_description: str = ""
    hook_key: str = ""


class LandingGeneratorService:

    def _load_packaging_prompt(self) -> str:
        if not _PACKAGING_PROMPT_PATH.exists():
            raise FileNotFoundError(
                f"Landing packaging prompt not found: {_PACKAGING_PROMPT_PATH}"
            )
        return _PACKAGING_PROMPT_PATH.read_text(encoding="utf-8")

    def generate(
        self,
        parsed_order: ParsedOrder,
        photographer_name: str = "Константин",
        price: str | None = None,
        photo_set_id: str | None = None,
        case_series_id: str | None = None,
    ) -> LandingPageModel:
        draft = self._generate_semantic_draft(parsed_order)
        return self._generate_landing_json(
            parsed_order, draft, photographer_name, price, photo_set_id, case_series_id
        )

    def _generate_semantic_draft(self, parsed_order: ParsedOrder) -> _SemanticDraft:
        user_message = self._build_order_context(parsed_order)

        try:
            text = openai_client.extract_text(
                system_prompt=_SEMANTIC_DRAFT_PROMPT,
                user_message=user_message,
                temperature=0.7,
                max_tokens=900,
            )
        except Exception as exc:
            logger.error("STEP1 FAILED — returning empty draft: %s", exc)
            return _SemanticDraft()

        logger.info("STEP1 RAW OUTPUT:\n%s", text)
        draft = self._parse_semantic_draft(text)
        logger.info(
            "Semantic draft parsed | hero=%r | steps=%r | next=%r | hook=%r",
            draft.hero_subtitle,
            draft.work_steps,
            draft.case_description,
            draft.hook_key,
        )
        return draft

    def _parse_semantic_draft(self, text: str) -> _SemanticDraft:
        if not text or not text.strip():
            logger.warning("Semantic draft parser received empty text")
            return _SemanticDraft()

        pattern = re.compile(r"\[\s*([A-Z_]+)\s*\]", re.IGNORECASE)
        parts = pattern.split(text)

        blocks: dict[str, str] = {}
        it = iter(parts[1:])
        for key in it:
            content = next(it, "").strip()
            blocks[key.upper()] = content

        if not blocks:
            logger.warning("Semantic draft parser found no blocks in AI output")
            return _SemanticDraft()

        hook_key = blocks.get("HOOK_KEY", "").strip().lower()
        if hook_key:
            if hook_key in _VALID_HOOK_KEYS:
                logger.debug("Step 1 hook_key: %s", hook_key)
            else:
                logger.warning("Step 1 returned unknown hook_key value: %r", hook_key)

        work_steps = [
            blocks.get("TIP", ""),
            blocks.get("NUANCE", ""),
            blocks.get("TRUST", ""),
        ]

        return _SemanticDraft(
            hero_subtitle=blocks.get("HERO", ""),
            work_steps=work_steps,
            case_title="",
            case_description=blocks.get("NEXT", ""),
            hook_key=hook_key,
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
        packaging_prompt = self._load_packaging_prompt()
        user_message = self._build_packaging_message(
            parsed_order, photographer_name, price, photo_set_id, case_series_id
        )

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

        if isinstance(raw.get("hero"), dict):
            raw["hero"].pop("subtitle", None)
        elif "hero" not in raw:
            raw["hero"] = {}

        if isinstance(raw.get("work_block"), dict):
            raw["work_block"].pop("steps", None)

        if isinstance(raw.get("similar_case"), dict):
            raw["similar_case"].pop("description", None)
            raw["similar_case"].pop("title", None)

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

        if isinstance(raw2.get("hero"), dict):
            raw2["hero"].pop("subtitle", None)
        elif "hero" not in raw2:
            raw2["hero"] = {}

        if isinstance(raw2.get("work_block"), dict):
            raw2["work_block"].pop("steps", None)

        if isinstance(raw2.get("similar_case"), dict):
            raw2["similar_case"].pop("description", None)
            raw2["similar_case"].pop("title", None)

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
        result = dict(raw)

        if not isinstance(result.get("hero"), dict):
            result["hero"] = {}
        result["hero"]["subtitle"] = draft.hero_subtitle

        if not isinstance(result.get("work_block"), dict):
            result["work_block"] = {}
        result["work_block"]["steps"] = list(draft.work_steps)

        if draft.case_description:
            existing_similar_case = result.get("similar_case")
            if not isinstance(existing_similar_case, dict):
                existing_similar_case = {}
            existing_similar_case["description"] = draft.case_description
            if draft.case_title:
                existing_similar_case["title"] = draft.case_title
            result["similar_case"] = existing_similar_case

        return result

    def _build_order_context(self, o: ParsedOrder) -> str:
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
        result = dict(raw)

        result["slug"] = self._safe_slug(result.get("slug", ""), parsed_order)

        if not result.get("template_key"):
            event_type = (parsed_order.event_type or "other").lower()
            result["template_key"] = _TEMPLATE_MAP.get(event_type, "registry_small")

        if not isinstance(result.get("style_grid"), dict):
            result["style_grid"] = {}
        if photo_set_id_override:
            result["style_grid"]["photo_set_id"] = photo_set_id_override
        elif not result["style_grid"].get("photo_set_id"):
            event_type = (parsed_order.event_type or "registry").lower()
            result["style_grid"]["photo_set_id"] = _PHOTO_SET_MAP.get(event_type, "registry_light")

        for key in ("quick_questions", "reviews", "secondary_actions"):
            if not isinstance(result.get(key), list):
                result[key] = []

        if not isinstance(result.get("cta"), dict):
            result["cta"] = {}
        if not result["cta"].get("channels"):
            result["cta"]["channels"] = ["telegram", "whatsapp"]

        return result

    def _safe_slug(self, raw: str, parsed_order: ParsedOrder) -> str:
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
