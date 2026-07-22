"""Text generation through Gemini with a Cloudflare fallback."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import requests

from config import (
    CLOUDFLARE_ACCOUNT_ID,
    CLOUDFLARE_API_TOKEN,
    CLOUDFLARE_TEXT_MODEL,
    GEMINI_API_KEY,
    GEMINI_TEXT_MODEL,
)

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_REQUEST_TIMEOUT_SECONDS = 120


class AITextError(RuntimeError):
    """Raised when every configured text provider fails."""


class ProviderConfigurationError(AITextError):
    """Raised when a provider is missing required credentials."""


class ProviderResponseError(AITextError):
    """Raised when a provider returns an invalid or unsuccessful response."""


def _retry_delay(response: requests.Response | None, attempt: int) -> float:
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), 60.0)
            except ValueError:
                pass
    return min(2.0**attempt, 15.0)


def _response_error(provider: str, response: requests.Response) -> ProviderResponseError:
    body = response.text[:500].replace("\n", " ")
    return ProviderResponseError(
        f"{provider} returned HTTP {response.status_code}: {body}"
    )


def _extract_gemini_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        feedback = payload.get("promptFeedback", {})
        raise ProviderResponseError(f"Gemini returned no candidates: {feedback}")
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        raise ProviderResponseError("Gemini returned an invalid candidate")
    content = candidate.get("content", {})
    if not isinstance(content, dict):
        raise ProviderResponseError("Gemini returned invalid candidate content")
    parts = content.get("parts", [])
    text = "".join(
        part.get("text", "") for part in parts if isinstance(part, dict)
    ).strip()
    if not text:
        raise ProviderResponseError("Gemini returned an empty text response")
    return text


def _extract_cloudflare_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderResponseError(f"Cloudflare returned no choices: {payload}")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise ProviderResponseError("Cloudflare returned an invalid choice")
    message = choice.get("message", {})
    if not isinstance(message, dict):
        raise ProviderResponseError("Cloudflare returned an invalid message")
    text = message.get("content", "")
    if not isinstance(text, str) or not text.strip():
        raise ProviderResponseError("Cloudflare returned an empty text response")
    return text.strip()


def _gemini_complete(
    prompt: str,
    system: str | None,
    temperature: float,
    json_mode: bool,
    max_retries: int,
) -> str:
    if not GEMINI_API_KEY:
        raise ProviderConfigurationError("GEMINI_API_KEY is not configured")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_TEXT_MODEL}:generateContent"
    )
    body: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 4096,
        },
    }
    if system:
        body["system_instruction"] = {"parts": [{"text": system}]}
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"

    last_error: Exception | None = None
    for attempt in range(max_retries):
        response: requests.Response | None = None
        try:
            response = requests.post(
                url,
                headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
                json=body,
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code == 200:
                return _extract_gemini_text(response.json())
            error = _response_error("Gemini", response)
            if response.status_code not in _RETRYABLE_STATUS_CODES:
                raise error
            last_error = error
            logger.warning("Gemini retry %s/%s after HTTP %s", attempt + 1, max_retries, response.status_code)
        except requests.RequestException as error:
            last_error = error
            logger.warning("Gemini network retry %s/%s: %s", attempt + 1, max_retries, error)
        except (ValueError, ProviderResponseError) as error:
            last_error = error
            if response is None or response.status_code not in _RETRYABLE_STATUS_CODES:
                raise
        if attempt < max_retries - 1:
            time.sleep(_retry_delay(response, attempt))
    raise AITextError(f"Gemini failed after {max_retries} attempts: {last_error}") from last_error


def _cloudflare_complete(
    prompt: str,
    system: str | None,
    temperature: float,
    json_mode: bool,
    max_retries: int,
) -> str:
    if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_TOKEN:
        raise ProviderConfigurationError(
            "CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required"
        )

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}"
        "/ai/v1/chat/completions"
    )
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body: dict[str, Any] = {
        "model": CLOUDFLARE_TEXT_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 4096,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    last_error: Exception | None = None
    for attempt in range(max_retries):
        response: requests.Response | None = None
        try:
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code == 200:
                return _extract_cloudflare_text(response.json())
            error = _response_error("Cloudflare Workers AI", response)
            if response.status_code not in _RETRYABLE_STATUS_CODES:
                raise error
            last_error = error
            logger.warning("Cloudflare retry %s/%s after HTTP %s", attempt + 1, max_retries, response.status_code)
        except requests.RequestException as error:
            last_error = error
            logger.warning("Cloudflare network retry %s/%s: %s", attempt + 1, max_retries, error)
        except (ValueError, ProviderResponseError) as error:
            last_error = error
            if response is None or response.status_code not in _RETRYABLE_STATUS_CODES:
                raise
        if attempt < max_retries - 1:
            time.sleep(_retry_delay(response, attempt))
    raise AITextError(
        f"Cloudflare Workers AI failed after {max_retries} attempts: {last_error}"
    ) from last_error


def chat_complete(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    temperature: float = 0.8,
    json_mode: bool = False,
    max_retries: int = 3,
) -> str:
    """Generate text with Gemini first and Cloudflare as an explicit fallback."""
    if max_retries < 1:
        raise ValueError("max_retries must be at least 1")
    if model:
        logger.warning("The model argument is ignored; provider models are configured in .env")

    gemini_error: Exception | None = None
    if GEMINI_API_KEY:
        try:
            return _gemini_complete(prompt, system, temperature, json_mode, max_retries)
        except AITextError as error:
            gemini_error = error
            logger.warning("Gemini failed; trying Cloudflare fallback: %s", error)

    if CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN:
        try:
            return _cloudflare_complete(prompt, system, temperature, json_mode, max_retries)
        except AITextError as error:
            if gemini_error is not None:
                raise AITextError(
                    f"Gemini and Cloudflare text providers failed. Gemini: {gemini_error}; Cloudflare: {error}"
                ) from error
            raise

    if gemini_error is not None:
        raise gemini_error
    raise ProviderConfigurationError(
        "Configure GEMINI_API_KEY or both CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN"
    )


def extract_json(text: str) -> dict[str, Any]:
    """Extract a JSON object from a provider response."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"```$", "", cleaned.strip()).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group()
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("AI response JSON must be an object")
    return value
