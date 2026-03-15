"""
DialogueCopilotService
──────────────────────
Generates 3 reply suggestions from a client message + ParsedOrder context.

Pipeline:
  1. load prompt from packages/prompts/dialogue_reply_prompt.txt
  2. build user message from client message + ParsedOrder + recent history
  3. call OpenAI via openai_client.extract_json()
  4. validate response with DialogueAIOutput schema
     — enforces exactly one suggestion per type: warm, short, expert
  5. return DialogueAIOutput

No DB access. No HTTP.
Receives strings and ParsedOrder, returns DialogueAIOutput.
"""

import logging
from pathlib import Path

from app.schemas.order import ParsedOrder
from app.schemas.dialogue import DialogueAIOutput, REQUIRED_SUGGESTION_TYPES
from app.services.openai_client import openai_client

logger = logging.getLogger(__name__)

_PROMPT_PATH = (
    Path(__file__).resolve()
    .parent           # services/
    .parent           # app/
    .parent           # api/
    .parent           # apps/
    .parent           # landing-reply/
    / "packages" / "prompts" / "dialogue_reply_prompt.txt"
)


class DialogueCopilotService:
    def __init__(self) -> None:
        self._system_prompt = _PROMPT_PATH.read_text(encoding="utf-8")

    def generate(
        self,
        client_message: str,
        parsed_order: ParsedOrder,
        recent_history: list[dict] | None = None,
    ) -> DialogueAIOutput:
        """
        Generate dialogue suggestions for a client message.

        Args:
            client_message:  the message the client just sent
            parsed_order:    order context for personalisation
            recent_history:  optional list of {"sender": "client"|"photographer", "text": "..."}
                             for the last N messages (for context)

        Returns:
            Validated DialogueAIOutput with exactly 3 suggestions.

        Raises:
            ValueError: if AI output fails schema validation.
        """
        user_message = self._build_user_message(
            client_message, parsed_order, recent_history or []
        )

        raw = openai_client.extract_json(
            system_prompt=self._system_prompt,
            user_message=user_message,
            temperature=0.6,
            max_tokens=1000,
        )

        try:
            result = DialogueAIOutput.model_validate(raw)
        except Exception as exc:
            logger.error("DialogueAIOutput validation failed: %s | raw: %s", exc, raw)
            raise ValueError(f"AI output did not match DialogueAIOutput schema: {exc}") from exc

        logger.info(
            "Dialogue suggestions generated | intent=%s | stage=%s",
            result.detected_intent, result.detected_stage,
        )
        return result

    # ── private ───────────────────────────────────────────────────────────

    def _build_user_message(
        self,
        client_message: str,
        o: ParsedOrder,
        history: list[dict],
    ) -> str:
        lines = [
            "=== Order context ===",
            f"event_type: {o.event_type or ''}",
            f"event_subtype: {o.event_subtype or ''}",
            f"date_text: {o.date_text or ''}",
            f"city: {o.city or ''}",
            f"budget_max: {o.budget_max or ''}",
            f"requirements: {', '.join(o.requirements) if o.requirements else ''}",
            "",
        ]

        if history:
            lines.append("=== Recent conversation (oldest first) ===")
            for msg in history:
                sender = "Клиент" if msg.get("sender") == "client" else "Фотограф"
                lines.append(f"{sender}: {msg.get('text', '')}")
            lines.append("")

        lines += [
            "=== Client message to analyse ===",
            client_message,
        ]

        return "\n".join(lines)


dialogue_copilot_service = DialogueCopilotService()
