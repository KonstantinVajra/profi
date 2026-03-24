"""
OpenAIClient
────────────
Thin wrapper around the OpenAI SDK.

Responsibilities:
  - hold a single configured client instance
  - expose three methods:
    extract_json()            — sends system + user message, expects JSON back, returns dict
    extract_text()            — sends system + user message, returns raw text string
    extract_json_with_image() — sends system prompt + image bytes, expects JSON back, returns dict

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


    def extract_json_with_image(
        self,
        system_prompt: str,
        image_bytes: bytes,
        image_media_type: str = "image/jpeg",
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> dict[str, Any]:
        """
        Send a system prompt and an image to the model and parse the response as JSON.
        Used for screenshot-based order extraction (vision mode).

        The image is base64-encoded and sent as a data URL.
        Response format is NOT set to json_object because vision mode does not
        support it in all model configurations — JSON is enforced via prompt instead.

        Args:
            system_prompt:     instructions telling the model what to extract
            image_bytes:       raw image bytes (read by the caller, not this method)
            image_media_type:  MIME type, e.g. "image/jpeg" or "image/png"
            temperature:       0.1 default — extraction should be deterministic
            max_tokens:        budget for the response

        Returns:
            Parsed JSON dict.

        Raises:
            ValueError: if the response cannot be parsed as JSON.
            openai.APIError: on network / auth failures (let caller handle).
        """
        import base64

        logger.debug(
            "OpenAI vision request | model=%s | image_len=%d",
            self._model, len(image_bytes),
        )

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{image_media_type};base64,{image_b64}"

        response: ChatCompletion = self._client.chat.completions.create(
            model=self._model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                        {
                            "type": "text",
                            "text": "Extract order fields from this screenshot. Return ONLY valid JSON.",
                        },
                    ],
                },
            ],
        )

        raw = response.choices[0].message.content or ""
        logger.debug(
            "OpenAI vision response | tokens=%d | raw_len=%d",
            response.usage.total_tokens if response.usage else 0, len(raw),
        )

        # Strip markdown code fences if model wraps JSON in ```json ... ```
        stripped = raw.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            stripped = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            ).strip()

        try:
            return json.loads(stripped)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse vision response as JSON: %s", raw[:300])
            raise ValueError(f"OpenAI vision returned non-JSON response: {raw[:200]}") from exc

    def extract_json_with_images(
        self,
        system_prompt: str,
        image_list: list[tuple[bytes, str]],
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> dict[str, Any]:
        """
        Send a system prompt and multiple images to the model and parse the response as JSON.
        Used for multi-screenshot order extraction (vision mode).

        Each (bytes, media_type) pair is sent as a separate image_url block in the user
        message content. OpenAI processes all images together in a single AI call.

        Args:
            system_prompt:  instructions telling the model what to extract
            image_list:     list of (image_bytes, media_type) tuples; max 5 enforced by caller
            temperature:    0.1 default — extraction should be deterministic
            max_tokens:     budget for the response

        Returns:
            Parsed JSON dict.

        Raises:
            ValueError: if image_list is empty, or response cannot be parsed as JSON.
            openai.APIError: on network / auth failures (let caller handle).
        """
        import base64

        if not image_list:
            raise ValueError("image_list must not be empty")

        logger.debug(
            "OpenAI multi-image vision request | model=%s | count=%d",
            self._model, len(image_list),
        )

        # Build content: one image_url block per screenshot, then the extraction prompt.
        content: list[dict[str, Any]] = []
        for img_bytes, media_type in image_list:
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            data_url = f"data:{media_type};base64,{b64}"
            content.append({"type": "image_url", "image_url": {"url": data_url}})
        content.append({
            "type": "text",
            "text": "Extract order fields from these screenshots. Return ONLY valid JSON.",
        })

        response: ChatCompletion = self._client.chat.completions.create(
            model=self._model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
        )

        raw = response.choices[0].message.content or ""
        logger.debug(
            "OpenAI multi-image vision response | tokens=%d | raw_len=%d",
            response.usage.total_tokens if response.usage else 0, len(raw),
        )

        stripped = raw.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            stripped = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            ).strip()

        try:
            return json.loads(stripped)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse multi-image vision response as JSON: %s", raw[:300])
            raise ValueError(f"OpenAI vision returned non-JSON response: {raw[:200]}") from exc


# Module-level singleton — imported by services
openai_client = OpenAIClient()