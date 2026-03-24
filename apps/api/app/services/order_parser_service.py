"""
OrderParserService
──────────────────
Converts a raw order (text or screenshot) into a validated ParsedOrder.

Two extraction modes:
  parse_text(raw_text, ...)  — text-based extraction via extract_json()
  parse_image(image_bytes, image_media_type, ...) — vision-based via extract_json_with_image()

Both modes:
  1. load system prompt from packages/prompts/order_parse_prompt.txt
  2. call OpenAI (text or vision mode respectively)
  3. post-process raw dict (date coercion, normalisation)
  4. validate via Pydantic ParsedOrder schema
  5. write PipelineTrace stage="extraction"
  6. return ParsedOrder

This service has NO knowledge of DB or HTTP.
It receives plain Python data (str or bytes), returns a ParsedOrder.
"""

import logging
import re
from datetime import date, datetime
from pathlib import Path

from app.schemas.order import ParsedOrder
from app.services.openai_client import openai_client

logger = logging.getLogger(__name__)

# Resolve prompt file relative to repo root regardless of working dir
_PROMPT_PATH = (
    Path(__file__).resolve()
    .parent           # services/
    .parent           # app/
    .parent           # api/
    .parent           # apps/
    .parent           # landing-reply/
    / "packages" / "prompts" / "order_parse_prompt.txt"
)


class OrderParserService:
    """
    Usage:
        service = OrderParserService()
        parsed = service.parse("Нужен фотограф на регистрацию 11 июня...")
    """

    def __init__(self) -> None:
        self._system_prompt = self._load_prompt()

    # ── public ────────────────────────────────────────────────────────────

    def parse_text(self, raw_text: str, project_id: str | None = None, db=None) -> ParsedOrder:
        """
        Extract structured order fields from raw text using OpenAI (JSON mode).

        Args:
            raw_text:   order text as provided by the user
            project_id: optional — if provided along with db, trace is written
            db:         optional SQLAlchemy session for trace persistence

        Returns:
            Validated ParsedOrder instance.

        Raises:
            ValueError: if AI response cannot be parsed or validated.
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("raw_text must not be empty")

        logger.info("Parsing order | text_len=%d", len(raw_text))

        user_message = raw_text.strip()
        prompt_text = self._system_prompt + "\n\n---USER---\n\n" + user_message

        # 1. call AI
        import json as _json
        try:
            raw_dict = openai_client.extract_json(
                system_prompt=self._system_prompt,
                user_message=user_message,
                temperature=0.1,
                max_tokens=800,
            )
        except Exception as exc:
            logger.error("OpenAI call failed during extraction: %s", exc)
            self._write_trace(
                project_id=project_id,
                db=db,
                input_payload={"raw_text": raw_text},
                prompt_text=prompt_text,
                raw_ai_output=None,
                parsed_output=None,
            )
            raise ValueError(f"AI call failed: {exc}") from exc

        logger.error("DEBUG raw extract_json output: %s", raw_dict)

        # capture raw AI output before any processing
        raw_ai_str = _json.dumps(raw_dict, ensure_ascii=False) if isinstance(raw_dict, dict) else str(raw_dict)

        # 2. post-process
        cleaned = self._post_process(raw_dict)

        # 3. validate via Pydantic
        try:
            parsed = ParsedOrder.model_validate(cleaned)
        except Exception as exc:
            logger.error("ParsedOrder validation failed: %s | raw: %s", exc, cleaned)
            self._write_trace(
                project_id=project_id,
                db=db,
                input_payload={"raw_text": raw_text},
                prompt_text=prompt_text,
                raw_ai_output=raw_ai_str,
                parsed_output=None,
            )
            raise ValueError(f"AI output did not match ParsedOrder schema: {exc}") from exc

        self._write_trace(
            project_id=project_id,
            db=db,
            input_payload={"raw_text": raw_text},
            prompt_text=prompt_text,
            raw_ai_output=raw_ai_str,
            parsed_output=parsed.model_dump(mode="json"),
        )

        logger.info(
            "Order parsed | event_type=%s | city=%s | budget=%s | confidence=%s",
            parsed.event_type, parsed.city, parsed.budget_max, parsed.extracted_confidence
        )
        return parsed

    def parse_image(
        self,
        image_bytes: bytes,
        image_media_type: str = "image/jpeg",
        project_id: str | None = None,
        db=None,
    ) -> ParsedOrder:
        """
        Extract structured order fields from a screenshot using OpenAI vision mode.

        The caller (router) reads the file and passes raw bytes.
        This method has no knowledge of UploadFile or file storage.

        Args:
            image_bytes:       raw image bytes
            image_media_type:  MIME type, e.g. "image/jpeg" or "image/png"
            project_id:        optional — if provided along with db, trace is written
            db:                optional SQLAlchemy session for trace persistence

        Returns:
            Validated ParsedOrder instance.

        Raises:
            ValueError: if image is unreadable, AI response is empty, or validation fails.
                        Never silently degrades — caller must handle the error.
        """
        import json as _json

        if not image_bytes:
            raise ValueError("image_bytes must not be empty")

        logger.info("Parsing order from screenshot | media_type=%s | size=%d", image_media_type, len(image_bytes))

        prompt_text = self._system_prompt + "\n\n[input: screenshot]"
        input_payload = {"input_type": "screenshot", "image_media_type": image_media_type}

        try:
            raw_dict = openai_client.extract_json_with_image(
                system_prompt=self._system_prompt,
                image_bytes=image_bytes,
                image_media_type=image_media_type,
                temperature=0.1,
                max_tokens=800,
            )
        except Exception as exc:
            logger.error("OpenAI vision call failed during extraction: %s", exc)
            self._write_trace(
                project_id=project_id,
                db=db,
                input_payload=input_payload,
                prompt_text=prompt_text,
                raw_ai_output=None,
                parsed_output=None,
            )
            raise ValueError(f"AI vision call failed: {exc}") from exc

        # Explicit check — empty dict means unreadable screenshot, not a parse error
        if not raw_dict:
            self._write_trace(
                project_id=project_id,
                db=db,
                input_payload=input_payload,
                prompt_text=prompt_text,
                raw_ai_output="{}",
                parsed_output=None,
            )
            raise ValueError(
                "Screenshot could not be read: AI returned an empty result. "
                "Please provide a clearer image or enter the order text manually."
            )

        raw_ai_str = _json.dumps(raw_dict, ensure_ascii=False)

        cleaned = self._post_process(raw_dict)

        try:
            parsed = ParsedOrder.model_validate(cleaned)
        except Exception as exc:
            logger.error("ParsedOrder validation failed (vision): %s | raw: %s", exc, cleaned)
            self._write_trace(
                project_id=project_id,
                db=db,
                input_payload=input_payload,
                prompt_text=prompt_text,
                raw_ai_output=raw_ai_str,
                parsed_output=None,
            )
            raise ValueError(f"AI vision output did not match ParsedOrder schema: {exc}") from exc

        self._write_trace(
            project_id=project_id,
            db=db,
            input_payload=input_payload,
            prompt_text=prompt_text,
            raw_ai_output=raw_ai_str,
            parsed_output=parsed.model_dump(mode="json"),
        )

        logger.info(
            "Order parsed from screenshot | event_type=%s | city=%s | confidence=%s",
            parsed.event_type, parsed.city, parsed.extracted_confidence,
        )
        return parsed

    def _write_trace(
        self,
        project_id: str | None,
        db,
        input_payload: dict | None,
        prompt_text: str | None,
        raw_ai_output: str | None,
        parsed_output: dict | None,
    ) -> None:
        """Write trace record. Silently skips if project_id or db is not provided."""
        if not project_id or db is None:
            return
        try:
            from app.repositories.debug_trace_repo import DebugTraceRepository
            DebugTraceRepository(db).create_trace(
                project_id=project_id,
                stage="extraction",
                input_payload=input_payload,
                prompt_text=prompt_text,
                raw_ai_output=raw_ai_output,
                parsed_output=parsed_output,
            )
        except Exception as exc:
            logger.warning("Trace write failed (extraction) | project=%s | error=%s", project_id, exc)

    # ── private ───────────────────────────────────────────────────────────

    def _load_prompt(self) -> str:
        """Load and prepare the system prompt, injecting current year."""
        if not _PROMPT_PATH.exists():
            raise FileNotFoundError(f"Prompt file not found: {_PROMPT_PATH}")
        template = _PROMPT_PATH.read_text(encoding="utf-8")
        current_year = datetime.now().year
        return template.replace("{current_year}", str(current_year))

    def _post_process(self, raw: dict) -> dict:
        """
        Clean and normalise the raw AI dict before Pydantic validation.

        - coerce event_date string → date if needed
        - strip whitespace from string fields
        - ensure lists are lists
        - clamp extracted_confidence to [0, 1]
        """
        result = dict(raw)

        # string fields — strip whitespace, convert empty string to None
        for key in (
            "client_name", "client_label", "event_type", "event_subtype",
            "city", "location", "date_text", "duration_text",
            "guest_count_text", "tone_signal",
            "client_intent_line", "situation_notes", "shoot_feel",
        ):
            val = result.get(key)
            if isinstance(val, str):
                val = val.strip()
                result[key] = val if val else None

        # event_date — accept "YYYY-MM-DD" string or already a date
        raw_date = result.get("event_date")
        if isinstance(raw_date, str) and raw_date:
            try:
                result["event_date"] = date.fromisoformat(raw_date)
            except ValueError:
                logger.warning("Could not parse event_date: %s", raw_date)
                result["event_date"] = None

        # budget_max — ensure int, strip non-digits if string
        budget = result.get("budget_max")
        if isinstance(budget, str):
            digits = re.sub(r"\D", "", budget)
            result["budget_max"] = int(digits) if digits else None

        # lists
        for key in ("requirements", "priority_signals"):
            val = result.get(key)
            if not isinstance(val, list):
                result[key] = []

        # confidence clamp
        conf = result.get("extracted_confidence")
        if conf is not None:
            try:
                result["extracted_confidence"] = max(0.0, min(1.0, float(conf)))
            except (TypeError, ValueError):
                result["extracted_confidence"] = None

        # currency default
        if not result.get("currency"):
            result["currency"] = "RUB"

        return result

    def parse_images(
        self,
        image_list: list[tuple[bytes, str]],
        project_id: str | None = None,
        db=None,
    ) -> ParsedOrder:
        """
        Extract structured order fields from multiple screenshots using OpenAI vision mode.

        All images are sent in a single AI call. The model is expected to synthesise
        information across all provided screenshots into one ParsedOrder.

        Args:
            image_list:   list of (image_bytes, media_type) tuples; 1–5 items
            project_id:   optional — if provided along with db, trace is written
            db:           optional SQLAlchemy session for trace persistence

        Returns:
            Validated ParsedOrder instance.

        Raises:
            ValueError: if image_list is empty, AI response is unreadable, or validation fails.
        """
        import json as _json

        if not image_list:
            raise ValueError("image_list must not be empty")

        logger.info(
            "Parsing order from %d screenshot(s) | sizes=%s",
            len(image_list),
            [len(b) for b, _ in image_list],
        )

        prompt_text = self._system_prompt + "\n\n[input: multi-screenshot]"
        input_payload = {
            "input_type": "multi-screenshot",
            "count": len(image_list),
            "media_types": [mt for _, mt in image_list],
        }

        try:
            raw_dict = openai_client.extract_json_with_images(
                system_prompt=self._system_prompt,
                image_list=image_list,
                temperature=0.1,
                max_tokens=800,
            )
        except Exception as exc:
            logger.error("OpenAI multi-image vision call failed: %s", exc)
            self._write_trace(
                project_id=project_id,
                db=db,
                input_payload=input_payload,
                prompt_text=prompt_text,
                raw_ai_output=None,
                parsed_output=None,
            )
            raise ValueError(f"AI vision call failed: {exc}") from exc

        if not raw_dict:
            self._write_trace(
                project_id=project_id,
                db=db,
                input_payload=input_payload,
                prompt_text=prompt_text,
                raw_ai_output="{}",
                parsed_output=None,
            )
            raise ValueError("AI could not extract order fields from the provided screenshots.")

        raw_ai_output = _json.dumps(raw_dict, ensure_ascii=False)
        cleaned = self._clean(raw_dict)

        try:
            parsed = ParsedOrder.model_validate(cleaned)
        except Exception as exc:
            logger.error("ParsedOrder validation failed (multi-image): %s", exc)
            self._write_trace(
                project_id=project_id,
                db=db,
                input_payload=input_payload,
                prompt_text=prompt_text,
                raw_ai_output=raw_ai_output,
                parsed_output=None,
            )
            raise ValueError(f"Parsed order validation failed: {exc}") from exc

        self._write_trace(
            project_id=project_id,
            db=db,
            input_payload=input_payload,
            prompt_text=prompt_text,
            raw_ai_output=raw_ai_output,
            parsed_output=_json.dumps(parsed.model_dump(mode="json"), ensure_ascii=False),
        )

        return parsed


# Module-level singleton — imported by the orders router
order_parser_service = OrderParserService()