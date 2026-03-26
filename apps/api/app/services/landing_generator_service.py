"""
LandingGeneratorService
───────────────────────
Generates a LandingPageModel JSON from a ParsedOrder.

RULE: AI generates JSON only. Never HTML.

Pipeline (two-step):
  STEP 1 — reply draft (human-readable outreach text)
    _generate_semantic_draft(parsed_order) → _SemanticDraft
    AI returns free-form text with two labelled blocks:
      [final_text]    — complete ready-to-use reply; injected into LandingPageModel.
      [entry_message] — short messenger hook; parsed and injected into LandingPageModel.
    Deterministic Python parser extracts [final_text] into _SemanticDraft.final_text.
    Falls back to empty draft on any failure so step 2 can still proceed.

    Legacy _SemanticDraft fields (hero_subtitle, work_steps, case_*, hook_key):
      Retained for hybrid/fallback scenarios only.
      New Step 1 prompt does NOT generate old [HERO]..[NEXT] blocks.
      These fields will be empty in practice; _inject_draft() guards prevent
      empty values from entering LandingPageModel.

  STEP 2 — JSON packaging (structural layer)
    _generate_landing_json(parsed_order, draft, ...) → LandingPageModel
    Generates structural fields only: slug, template_key, hero.title,
    price_card, style_grid, quick_questions, cta, badges, photographer.
    final_text is stripped from Step 2 AI output and injected from _SemanticDraft.
    Step 1 parser is the sole author of final_text.

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

_SERVICE_VERSION = "diag-v1"

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
Ты — GPT-коуч по откликам для фотографа.

Твоя главная задача — НЕ написать отклик.

Твоя задача — научить писать отклик на конкретном примере.

Ты всегда работаешь через разбор:

ты показываешь, как думаешь,

и этим обучаешь повторять логику.

Ты не ведёшь диалог.

Ты не даёшь теорию отдельно.

Ты не пишешь «готовый текст и потом разбор».

Ты строишь обучение так:

👉 сначала настраиваешь мышление

👉 потом показываешь, как это превращается в текст

🧠 ROLE STACK (ОБЯЗАТЕЛЬНО)

Ты одновременно:

— психолог

— продажник

— арт-директор

— стратег

Ты работаешь на пересечении этих ролей.

🧠 КАК ТЫ ДУМАЕШЬ (ОБЯЗАТЕЛЬНО)

Перед каждым этапом ты определяешь:

— что человек ХОЧЕТ

— чего он БОИТСЯ

— где он СОМНЕВАЕТСЯ

— что заставит его ДВИНУТЬСЯ дальше

Без этого ты не имеешь права писать текст.

🧠 ПСИХОЛОГИЯ

Ты работаешь через состояние клиента.

Если текст не влияет на состояние — он слабый.

💰 ПРОДАЖА

Ты не информируешь.

Ты ведёшь к действию.

⚔️ АНТИ-ШАБЛОН

Если текст можно отправить 10 людям —

он плохой.

👉 Должно быть ощущение: "это написано под меня"

🧠 ПОВЕДЕНИЕ КОУЧА

Ты показываешь выбор:

— как обычно делают (и почему это слабо)

— какое решение выбираешь ты

— почему оно сильнее

— как это повторить

🆕 NEW REQUEST

Каждое обращение — новый заказ.

Анализ с нуля.

---

# СТРУКТУРА

Entry

Match

Interpretation

Proof

Price

Transition

---

# ФОРМАТ

[stage]

[reason_block]

⚠️ максимум 5 коротких фраз

⚠️ только до text_block

⚠️ никаких объяснений после текста

[text_block --- Entry]

[text_block --- Match]

[text_block --- Interpretation]

[text_block --- Proof]

[text_block --- Price]

[text_block --- Transition]

❌ Запрещено:

— добавлять общий разбор после всех блоков

— объяснять текст вне reason_block

— делать финальный анализ

⚠️ КОНТРОЛЬ ОБЪЁМА (ОБЯЗАТЕЛЬНО)

В каждом этапе ты обязан следить за длиной текста.

text_block должен быть:

— коротким

— плотным

— без лишних объяснений

Ориентир:

1—3 предложения на этап

Запрещено:

— длинные абзацы

— повторение одной мысли разными словами

— "разжёвывание"

Ты должен сам объяснять это в reason_block перед каждым этапом:

— где нужно сократить

— почему длинный текст хуже

— как оставить только суть

Если текст можно сократить — он обязан быть сокращён.

Короткий текст воспринимается как уверенность.

Длинный текст воспринимается как попытка убедить.

---

# 🔴 ОБРАЩЕНИЕ К КЛИЕНТУ (КРИТИЧЕСКИ ЖЁСТКО)

Во всём тексте:

👉 только "Вы / Вам / Ваш"

Любое "ты" = ошибка.

---

# 🔴 GREETING (КРИТИЧЕСКИ ЖЁСТКО)

ПЕРВАЯ СТРОКА Entry ОБЯЗАНА содержать приветствие.

Это обязательное правило.

Если есть имя:

👉 "Маша, здравствуйте ..."

Если нет:

👉 "Здравствуйте ..."

❌ Нельзя без приветствия

❌ Нельзя начинать с сути

Приветствие обязательно:

— в основном тексте

— в entry_message

---

# 🔗 ENTRY HOOK

Первый блок должен:

— зацепить

— дать ощущение "это про меня"

— намекнуть, что ниже уже есть решение

Запрещено использовать обезличенные формулировки:

— "для вас подготовлено"

— "собрали"

— "разобрали"

Всегда должен быть субъект:

✔ "я разобрал"

✔ "я собрал"

✔ "я посмотрел ваш запрос"

Если в тексте нет "я" — он воспринимается как реклама.

---

# 🖼 PHOTO CONTEXT

Обязательно встроить:

👉 под текстом есть фото

👉 они подобраны под запрос

Не как факт.

А как ценность.

Запрещено описывать точное содержимое кадров.

Ты не знаешь, что именно на фото.

Нельзя:

— "там вы вдвоём"

— "там видно регистрацию"

— "там такие же люди"

Можно только:

— описывать формат

— ощущение

— подачу

— ритм съёмки

Правильно:

"там видно, как это выглядит в таком формате съёмки"

---

# 💰 PRICE

Это отдельный этап.

Он всегда идёт после Proof и перед Transition.

Формат:

— 1—2 короткие строки

— без перегруза

— без объяснений

Тон:

— спокойный

— мягкий

— без давления

Примеры вектора:


Важно:

— не делать из этого продажу

— не расписывать цену

— не оправдываться

⚠️ СТРОГОЕ ПРАВИЛО

Цена может быть указана ТОЛЬКО если она явно присутствует во входных данных заказа.

Если цена / бюджет НЕ указаны:
— НЕ указывай цену
— НЕ делай оценок
— НЕ пиши "обычно выходит"
— НЕ придумывай стоимость

Если точная цена известна:
— можно мягко упомянуть её
— без давления
— без расчётов
— без "от" и "примерно"

Если цена неизвестна:
— пропусти этот блок
— переходи сразу к Transition

---

# ФОКУС

❌ я

✔ вы

---

# 🔴 TRANSITION (УСИЛЕН)

Финал — это крючок.

Он должен:

— усилить интерес

— создать ощущение "там уже есть ответ"

— подтолкнуть к просмотру

❌ нельзя нейтрально

❌ нельзя "напишите"

👉 только интерес и вовлечение

В конце отклика должен быть мягкий выход в диалог.

Не через давление ("напишите"),

а через помощь и продолжение:

— "могу подобрать"

— "могу предложить"

— "могу собрать"

Если в конце нет такого мостика — отклик считается незавершённым.

---

# FINAL_TEXT

Цельный отклик:

— с приветствием

— на "Вы"

— без разметки

Обязательно добавляй в конце отдельный блок:

[final_text]

Внутри него:

— полная версия текста

— без подзаголовков внутри

— без внутренних служебных пометок

— как готовый цельный отклик для клиента

---

# ENTRY MESSAGE

[entry_message]

2—4 строки

ПЕРВАЯ СТРОКА:

👉 приветствие

👉 подведение к открытию

Обязательно:

— имя (если есть)

— ощущение "я посмотрел / я собрал / я подобрал"

Запрещено:

— обезличенность

— пафос

— рекламные формулировки

Он должен ощущаться как:

👉 короткое человеческое сообщение

---

# ГЛАВНЫЙ КРИТЕРИЙ

После текста:

👉 "он понял мою ситуацию"

После entry_message:

👉 "надо открыть"

---

# СУТЬ

Ты не пишешь отклик.

Ты показываешь мышление,

из которого он собирается.
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
    "other":     "event_general",
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
    Private intermediate result of Step 1.
    Local to this service only — not a public contract, not persisted.

    Step 1 source of truth (new prompt):
      - final_text: the only field reliably produced. Primary landing content (MVP).

    Legacy fields (hero_subtitle, work_steps, case_title, case_description, hook_key):
      - Retained for backward compatibility only.
      - New Step 1 prompt does NOT generate the old HERO/TIP/TRUST/NEXT blocks.
      - These fields will be empty in practice and are NOT injected if empty
        (see _inject_draft guards — Vариант B decision).

    entry_message: short messenger hook (2–4 lines). Parsed from Step 1, injected into LandingPageModel.
    """
    # Legacy semantic fields — will be empty with new Step 1 prompt.
    # Kept in struct to avoid breaking any future hybrid prompt scenarios.
    hero_subtitle: str = ""
    work_steps: list[str] = field(default_factory=list)
    case_title: str = ""
    case_description: str = ""
    hook_key: str = ""
    # Primary landing content — sole output that new Step 1 prompt guarantees.
    final_text: str = ""
    # Short messenger hook — parsed from [entry_message] block in Step 1 output.
    entry_message: str = ""


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
        related_block: dict | None = None,
        hero_title_override: str | None = None,
        project_id: str | None = None,
        db=None,
    ) -> LandingPageModel:
        logger.warning("LandingGeneratorService.generate() | version=%s", _SERVICE_VERSION)
        draft = self._generate_semantic_draft(parsed_order, project_id=project_id, db=db)
        return self._generate_landing_json(
            parsed_order, draft, photographer_name, price, photo_set_id, case_series_id,
            related_block=related_block,
            hero_title_override=hero_title_override,
            project_id=project_id, db=db,
        )

    def _generate_semantic_draft(self, parsed_order: ParsedOrder, project_id: str | None = None, db=None) -> _SemanticDraft:
        import dataclasses
        import json as _json

        user_message = (
            self._build_order_context(parsed_order)
            + "\n\n"
            + (
                "Верни ответ строго в двух блоках:\n"
                "[final_text] — полный готовый отклик для клиента, без разметки внутри.\n"
                "[entry_message] — короткое сообщение-подводка (2–4 строки).\n"
                "Никакого текста вне блоков."
            )
        )
        prompt_text = _SEMANTIC_DRAFT_PROMPT + "\n\n---USER---\n\n" + user_message

        _step1_messages = [
            {"role": "system", "content": _SEMANTIC_DRAFT_PROMPT},
            {"role": "user",   "content": user_message},
        ]
        logger.warning(
            "STEP1 OUTBOUND | model=%s | system_len=%d | user_len=%d"
            "\n--- SYSTEM ---\n%s"
            "\n--- USER ---\n%s",
            openai_client._model,
            len(_step1_messages[0]["content"]),
            len(_step1_messages[1]["content"]),
            _step1_messages[0]["content"],
            _step1_messages[1]["content"],
        )

        input_payload = {"user_message": user_message}

        try:
            text = openai_client.extract_text(
                system_prompt=_SEMANTIC_DRAFT_PROMPT,
                user_message=user_message,
                temperature=0.7,
                max_tokens=900,
            )
        except Exception as exc:
            logger.error("STEP1 FAILED — returning empty draft: %s", exc)
            self._write_trace(
                project_id=project_id,
                db=db,
                stage="landing_generation_step1",
                input_payload=input_payload,
                prompt_text=prompt_text,
                raw_ai_output=None,
                parsed_output=None,
            )
            return _SemanticDraft()

        logger.warning("STEP1 RAW OUTPUT:\n%s", text)
        draft = self._parse_semantic_draft(text)
        logger.warning(
            "Semantic draft parsed"
            " | final_text_present=%s | final_text_len=%d"
            " | hero_subtitle_present=%s | work_steps_count=%d | hook=%r",
            bool(draft.final_text),
            len(draft.final_text),
            bool(draft.hero_subtitle),
            len(draft.work_steps),
            draft.hook_key or None,
        )

        self._write_trace(
            project_id=project_id,
            db=db,
            stage="landing_generation_step1",
            input_payload=input_payload,
            prompt_text=prompt_text,
            raw_ai_output=text,
            parsed_output=dataclasses.asdict(draft),
        )

        return draft

    def _parse_semantic_draft(self, text: str) -> _SemanticDraft:
        """
        Parse Step 1 AI output into _SemanticDraft.

        New Step 1 prompt format:
          [final_text]   — primary landing content (required, always present)
          [entry_message] — short messenger hook; parsed into _SemanticDraft.entry_message

        Legacy blocks ([HERO_SUBTITLE], [TIP], [NUANCE], [TRUST], [HOOK_KEY], [NEXT])
        are no longer generated by the new prompt. Parser attempts to read them for
        hybrid/fallback scenarios but will get empty strings in practice.
        _inject_draft() guards prevent empty values from entering the model.
        """
        if not text or not text.strip():
            logger.warning("Semantic draft parser received empty text")
            return _SemanticDraft()

        # ── Primary: parse [final_text] ──────────────────────────────────
        # Must be extracted before the generic block splitter, because
        # [final_text] content may contain lines that look like block headers.
        # Lookahead stops at any next [BLOCK] header or end of text.
        pattern_final_text = r"\[final_text\]\s*(.*?)\s*(?=\n\[|$)"
        match = re.search(pattern_final_text, text, re.DOTALL | re.IGNORECASE)
        if match:
            final_text = match.group(1).strip()
            logger.warning("Step 1 final_text parsed | len=%d", len(final_text))
        else:
            final_text = ""
            logger.warning("Step 1 [final_text] block not found in output")

        # ── Parse [entry_message] ─────────────────────────────────────────
        # Short messenger hook (2–4 lines). Same lookahead pattern as final_text.
        pattern_entry_message = r"\[entry_message\]\s*(.*?)\s*(?=\n\[|$)"
        match_em = re.search(pattern_entry_message, text, re.DOTALL | re.IGNORECASE)
        if match_em:
            entry_message = match_em.group(1).strip()
            logger.warning("Step 1 entry_message parsed | len=%d", len(entry_message))
        else:
            entry_message = ""

        # ── Legacy: parse old semantic blocks (may be absent with new prompt) ─
        pattern = re.compile(r"\[\s*([A-Z_]+)\s*\]", re.IGNORECASE)
        parts = pattern.split(text)

        blocks: dict[str, str] = {}
        it = iter(parts[1:])
        for key in it:
            val = next(it, "").strip()
            blocks[key.upper()] = val

        detected = list(blocks.keys())
        if detected:
            logger.warning("Step 1 detected legacy blocks: %s", detected)

        # Legacy hook_key — only valid if old prompt was used
        hook_key = blocks.get("HOOK_KEY", "").strip().lower()
        if hook_key and hook_key not in _VALID_HOOK_KEYS:
            logger.warning("Step 1 returned unknown hook_key value: %r — ignoring", hook_key)
            hook_key = ""

        # Legacy work_steps — only non-empty strings, empty list if absent
        work_steps = [s for s in [
            blocks.get("TIP", ""),
            blocks.get("NUANCE", ""),
            blocks.get("TRUST", ""),
        ] if s]

        return _SemanticDraft(
            hero_subtitle=blocks.get("HERO_SUBTITLE", ""),
            work_steps=work_steps,
            case_title="",
            case_description=blocks.get("NEXT", ""),
            hook_key=hook_key,
            final_text=final_text,
            entry_message=entry_message,
        )

    def _generate_landing_json(
        self,
        parsed_order: ParsedOrder,
        draft: _SemanticDraft,
        photographer_name: str,
        price: str | None,
        photo_set_id: str | None,
        case_series_id: str | None,
        related_block: dict | None = None,
        hero_title_override: str | None = None,
        project_id: str | None = None,
        db=None,
    ) -> LandingPageModel:
        import json as _json

        packaging_prompt = self._load_packaging_prompt()
        user_message = self._build_packaging_message(
            parsed_order, photographer_name, price, photo_set_id, case_series_id
        )
        prompt_text = packaging_prompt + "\n\n---USER---\n\n" + user_message
        input_payload = {"user_message": user_message}

        try:
            raw = openai_client.extract_json(
                system_prompt=packaging_prompt,
                user_message=user_message,
                temperature=0.2,
                max_tokens=1500,
            )
        except Exception as exc:
            logger.error("OpenAI call failed during landing step2: %s", exc)
            self._write_trace(
                project_id=project_id, db=db,
                stage="landing_generation_step2",
                input_payload=input_payload,
                prompt_text=prompt_text,
                raw_ai_output=None,
                parsed_output=None,
            )
            raise ValueError(f"AI call failed: {exc}") from exc

        # capture raw AI output before any processing
        raw_ai_str = _json.dumps(raw, ensure_ascii=False) if isinstance(raw, dict) else str(raw)

        if not isinstance(raw, dict):
            self._write_trace(
                project_id=project_id, db=db,
                stage="landing_generation_step2",
                input_payload=input_payload,
                prompt_text=prompt_text,
                raw_ai_output=raw_ai_str,
                parsed_output=None,
            )
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

        # Strip final_text and entry_message from Step 2 AI output — Step 1 is the sole author.
        raw.pop("final_text", None)
        raw.pop("entry_message", None)
        # AI must never generate related_block — injected from user input only.
        raw.pop("related_block", None)

        patched = self._inject_draft(raw, draft)
        cleaned = self._post_process(patched, parsed_order, photo_set_id)

        # Inject related_block from user input — never from AI output.
        if related_block is not None:
            cleaned["related_block"] = related_block

        # Inject hero_title_override from user input — never from AI output.
        # AI must never generate this field — raw.pop is not needed here because
        # hero_title_override is not a field AI knows about.
        if hero_title_override and hero_title_override.strip():
            cleaned["hero_title_override"] = hero_title_override.strip()

        try:
            model = LandingPageModel.model_validate(cleaned)
            logger.info("Landing generated | slug=%s | template=%s", model.slug, model.template_key)
            self._write_trace(
                project_id=project_id, db=db,
                stage="landing_generation_step2",
                input_payload=input_payload,
                prompt_text=prompt_text,
                raw_ai_output=raw_ai_str,
                parsed_output=model.model_dump(mode="json"),
            )
            return model
        except ValidationError as exc:
            logger.warning(
                "Landing validation failed on first attempt — retrying\n%s", str(exc)
            )

        # Preserve final_text before repair — it comes from Step 1 and must
        # never be lost or overwritten by the repair AI call.
        saved_final_text = cleaned.get("final_text")
        # Preserve related_block before repair — user input, must never be overwritten.
        saved_related_block = cleaned.get("related_block")
        # Preserve hero_title_override before repair — user input, must never be overwritten.
        saved_hero_title_override = cleaned.get("hero_title_override")

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

        # capture raw repair attempt output before any processing
        raw2_ai_str = _json.dumps(raw2, ensure_ascii=False) if isinstance(raw2, dict) else str(raw2)

        if not isinstance(raw2, dict):
            self._write_trace(
                project_id=project_id, db=db,
                stage="landing_generation_step2",
                input_payload=input_payload,
                prompt_text=prompt_text,
                raw_ai_output=raw2_ai_str,
                parsed_output=None,
            )
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

        # Strip final_text and entry_message from repair AI output — Step 1 is the sole author.
        raw2.pop("final_text", None)
        raw2.pop("entry_message", None)
        # AI must never generate related_block — injected from user input only.
        raw2.pop("related_block", None)

        patched2 = self._inject_draft(raw2, draft)
        cleaned2 = self._post_process(patched2, parsed_order, photo_set_id)

        # Restore final_text after repair — repair AI does not know about it.
        if saved_final_text is not None:
            cleaned2["final_text"] = saved_final_text

        # Restore related_block after repair — user input, repair AI must not affect it.
        if saved_related_block is not None:
            cleaned2["related_block"] = saved_related_block

        # Restore hero_title_override after repair — user input, repair AI must not affect it.
        if saved_hero_title_override is not None:
            cleaned2["hero_title_override"] = saved_hero_title_override

        try:
            model = LandingPageModel.model_validate(cleaned2)
            logger.info("Landing generated after repair | slug=%s", model.slug)
            self._write_trace(
                project_id=project_id, db=db,
                stage="landing_generation_step2",
                input_payload=input_payload,
                prompt_text=prompt_text,
                raw_ai_output=raw2_ai_str,
                parsed_output=model.model_dump(mode="json"),
            )
            return model
        except ValidationError as exc2:
            logger.error(
                "Landing validation failed after repair\n%s\nraw=%s", str(exc2), cleaned2
            )
            self._write_trace(
                project_id=project_id, db=db,
                stage="landing_generation_step2",
                input_payload=input_payload,
                prompt_text=prompt_text,
                raw_ai_output=raw2_ai_str,
                parsed_output=None,
            )
            raise ValueError(
                f"Landing generation failed after repair attempt: {exc2}"
            ) from exc2

    def _write_trace(
        self,
        project_id: str | None,
        db,
        stage: str,
        input_payload: dict | None,
        prompt_text: str | None,
        raw_ai_output: str | None,
        parsed_output: dict | list | None,
    ) -> None:
        """Write trace record. Silently skips if project_id or db is not provided."""
        if not project_id or db is None:
            return
        try:
            from app.repositories.debug_trace_repo import DebugTraceRepository
            DebugTraceRepository(db).create_trace(
                project_id=project_id,
                stage=stage,
                input_payload=input_payload,
                prompt_text=prompt_text,
                raw_ai_output=raw_ai_output,
                parsed_output=parsed_output,
            )
        except Exception as exc:
            logger.warning("Trace write failed (%s) | project=%s | error=%s", stage, project_id, exc)

    def _inject_draft(
        self, raw: dict[str, Any], draft: _SemanticDraft
    ) -> dict[str, Any]:
        """
        Merge _SemanticDraft values into Step 2 AI output dict.

        Guards (Variant B decision):
          - Each legacy field is injected ONLY if non-empty.
          - No empty strings or empty lists are written into the model.
          - New Step 1 prompt does not produce legacy blocks, so in practice
            hero_subtitle / work_steps / case_* will be empty and skipped.
          - final_text is always injected if present (primary content, MVP).
        """
        result = dict(raw)

        # ── hero.subtitle — inject only if non-empty ─────────────────────
        if draft.hero_subtitle:
            if not isinstance(result.get("hero"), dict):
                result["hero"] = {}
            result["hero"]["subtitle"] = draft.hero_subtitle

        # ── work_block.steps — inject only if there are non-empty steps ──
        if draft.work_steps:
            if not isinstance(result.get("work_block"), dict):
                result["work_block"] = {}
            result["work_block"]["steps"] = list(draft.work_steps)

        # ── similar_case — inject only if description or title is non-empty
        if draft.case_description or draft.case_title:
            existing = result.get("similar_case")
            if not isinstance(existing, dict):
                existing = {}
            if draft.case_description:
                existing["description"] = draft.case_description
            if draft.case_title:
                existing["title"] = draft.case_title
            result["similar_case"] = existing

        # ── final_text — primary landing content from Step 1 ─────────────
        # Step 1 is the sole author. Step 2 AI output is stripped before this.
        if draft.final_text is not None:
            result["final_text"] = draft.final_text

        # ── entry_message — short messenger hook from Step 1 ─────────────
        # Step 1 is the sole author. Step 2 AI output is stripped before this.
        if draft.entry_message:
            result["entry_message"] = draft.entry_message

        logger.warning(
            "Inject summary"
            " | hero.subtitle=%r"
            " | work_block.steps_count=%d"
            " | similar_case.description=%r"
            " | final_text_len=%d"
            " | entry_message_len=%d",
            result.get("hero", {}).get("subtitle") if isinstance(result.get("hero"), dict) else None,
            len(result.get("work_block", {}).get("steps") or []) if isinstance(result.get("work_block"), dict) else 0,
            result.get("similar_case", {}).get("description") if isinstance(result.get("similar_case"), dict) else None,
            len(result.get("final_text") or ""),
            len(result.get("entry_message") or ""),
        )

        return result

    def _build_order_context(self, o: ParsedOrder) -> str:
        return "\n".join([
            f"client_name: {o.client_name or ''}",
            f"client_label: {o.client_label or ''}",
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
            result["template_key"] = _TEMPLATE_MAP.get(event_type, "event_general")

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