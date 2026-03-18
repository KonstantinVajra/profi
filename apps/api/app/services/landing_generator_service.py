"""
LandingGeneratorService
───────────────────────
Generates a LandingPageModel JSON from a ParsedOrder.

RULE: AI generates JSON only. Never HTML.
"""

import logging
import re
import unicodedata
from typing import Any

from app.schemas.order import ParsedOrder
from app.schemas.landing import LandingPageModel
from app.services.openai_client import openai_client

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are writing a direct reply to a client request.

This is NOT a landing page.

The landing page is just a UI wrapper around your reply.

---

Your goal:

Show that you understand the client’s situation
and know what can go wrong and how to handle it.

---

CRITICAL RULE:

If your text can be reused for another order — it is invalid.

---

THINK BEFORE WRITING:

1. What will likely go wrong in this situation?
2. Why does it happen?
3. What would an experienced professional do differently?

If you cannot identify a concrete problem — output is invalid.

---

STYLE:

- Write like a human expert
- Write like you are replying personally
- Not like a website
- Not like marketing

---

DO:

- Refer to the exact situation
- Mention real risks or mistakes
- Give a practical way to handle it
- Be specific

---

DO NOT:

- Describe services
- Use generic phrases
- Write abstract text
- Write like a portfolio

---

FIELD DEFINITIONS:

request_match:
Show that you understood the exact situation

key_feature:
Explain what usually goes wrong AND what to do instead

trust_line:
Short insight from experience

hook_line:
Specific interesting detail (not a question)

---

SELF-CHECK:

Before finalizing:

- Is this generic?
- Can it apply to another order?
- Is there a real problem described?

If yes — rewrite.

---

Return ONLY valid JSON matching LandingPageModel.
"""


_TEMPLATE_MAP: dict[str, str] = {
    "registry": "registry_small",
    "wedding": "wedding_full",
    "family": "family_session",
    "event": "event_general",
    "portrait": "family_session",
    "other": "registry_small",
}


class LandingGeneratorService:
    def generate(
        self,
        parsed_order: ParsedOrder,
        photographer_name: str = "Алексей",
        price: str | None = None,
    ) -> LandingPageModel:

        user_message = self._build_user_message(parsed_order, photographer_name, price)

        raw = openai_client.extract_json(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.5,
            max_tokens=1200,
        )

        cleaned = self._post_process(raw, parsed_order)

        try:
            model = LandingPageModel.model_validate(cleaned)
        except Exception as exc:
            logger.error("Landing validation failed: %s | raw: %s", exc, cleaned)
            raise ValueError(f"Invalid LandingPageModel: {exc}") from exc

        return model

    # ─────────────────────────────────────────

    def _build_user_message(
        self,
        o: ParsedOrder,
        photographer_name: str,
        price: str | None,
    ) -> str:
        proposed_price = price or (f"до {o.budget_max} ₽" if o.budget_max else "не указана")

        return f"""
client_label: {o.client_label or o.client_name or 'клиент'}
event_type: {o.event_type or ''}
event_subtype: {o.event_subtype or ''}
date: {o.date_text or ''}
city: {o.city or ''}
location: {o.location or ''}
duration: {o.duration_text or ''}
guest_count: {o.guest_count_text or ''}

requirements: {', '.join(o.requirements) if o.requirements else ''}
priority_signals: {', '.join(o.priority_signals) if o.priority_signals else ''}

client_intent_line: {o.client_intent_line or ''}
situation_notes: {o.situation_notes or ''}
shoot_feel: {o.shoot_feel or ''}

photographer_name: {photographer_name}
price: {proposed_price}
"""

    # ─────────────────────────────────────────

    def _post_process(
        self,
        raw: dict[str, Any],
        parsed_order: ParsedOrder,
    ) -> dict[str, Any]:

        result = dict(raw)

        # slug
        result["slug"] = self._safe_slug(result.get("slug", ""), parsed_order)

        # template fallback
        if not result.get("template_key"):
            event_type = (parsed_order.event_type or "other").lower()
            result["template_key"] = _TEMPLATE_MAP.get(event_type, "registry_small")

        return result

    # ─────────────────────────────────────────

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