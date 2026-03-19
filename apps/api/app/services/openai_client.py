"""
OpenAIClient
────────────
Thin wrapper around the OpenAI SDK.

Responsibilities:
  - hold a single configured client instance
  - expose two methods:
    extract_json() — sends system + user message, expects JSON back, returns dict
    extract_text() — sends system + user message, returns raw text string

All prompts are passed in by callers — this module knows nothing
about business logic.
"""

import json
import logging
from typing import Any

from openai import OpenAI
from openai.types.chat import ChatCompletion

from app.config import settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    def extract_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.1,   # low temp = deterministic extraction
        max_tokens: int = 1000,
    ) -> dict[str, Any]:
        """
        Send a prompt pair to the model and parse the response as JSON.

        Args:
            system_prompt: instructions telling the model what to do
            user_message:  the actual content to process
            temperature:   0.1 default — extraction should be deterministic
            max_tokens:    budget for the response

        Returns:
            Parsed JSON dict.

        Raises:
            ValueError: if the response cannot be parsed as JSON.
            openai.APIError: on network / auth failures (let caller handle).
        """
        logger.debug("OpenAI request | model=%s | user_len=%d", self._model, len(user_message))

        response: ChatCompletion = self._client.chat.completions.create(
            model=self._model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},   # forces JSON mode
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
        )

        raw = response.choices[0].message.content or ""
        logger.debug("OpenAI response | tokens=%d | raw_len=%d",
                     response.usage.total_tokens if response.usage else 0, len(raw))

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse OpenAI response as JSON: %s", raw[:300])
            raise ValueError(f"OpenAI returned non-JSON response: {raw[:200]}") from exc

    def extract_text(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        """
        Send a prompt pair to the model and return the raw text response.
        Used when the model is expected to return free-form text, not JSON.

        Same call semantics as extract_json() — same model, same message
        structure — but without response_format JSON mode constraint.

        Args:
            system_prompt: instructions telling the model what to do
            user_message:  the actual content to process
            temperature:   0.7 default — text generation benefits from variety
            max_tokens:    budget for the response

        Returns:
            Raw text string from the model. Never None — empty string on empty response.

        Raises:
            openai.APIError: on network / auth failures (let caller handle).
        """
        logger.debug("OpenAI text request | model=%s | user_len=%d", self._model, len(user_message))

        response: ChatCompletion = self._client.chat.completions.create(
            model=self._model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
        )

        text = response.choices[0].message.content or ""
        logger.debug("OpenAI text response | tokens=%d | raw_len=%d",
                     response.usage.total_tokens if response.usage else 0, len(text))

        return text


# Module-level singleton — imported by services
openai_client = OpenAIClient()