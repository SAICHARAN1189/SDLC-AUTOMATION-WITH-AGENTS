from __future__ import annotations

import random
import time
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Optional

from google import genai
from google.genai import types

from backend.config.settings import settings
from backend.llm.groq_client import LLMResult
from backend.models.schemas import ErrorCategory
from backend.utils.logging import logger


class GeminiPermanentError(RuntimeError):
    """Raised for non-retryable client errors (400, 401, 403, 404)."""
    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GeminiDailyQuotaExhaustedError(RuntimeError):
    """Raised when daily request quota (RPD) is exhausted, triggering immediate fallback without retrying."""
    def __init__(self, message: str, status_code: Optional[int] = 429) -> None:
        super().__init__(message)
        self.status_code = status_code


class GeminiRetryExhaustedError(RuntimeError):
    """Raised when transient retries (503, 429, 500, timeouts) have been exhausted."""
    def __init__(self, message: str, attempts: int, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.status_code = status_code


def classify_gemini_error(exc: Exception) -> tuple[str, Optional[int], str]:
    """
    Classifies an exception into TRANSIENT, DAILY_QUOTA, PERMANENT, or UNKNOWN.
    Returns (category, status_code, status_name).
    """
    status_code: Optional[int] = getattr(exc, "code", None)
    if status_code is None:
        status_code = getattr(exc, "status_code", None)

    status_str = str(getattr(exc, "status", "") or "").upper()
    message_str = str(exc).lower()

    # Check for daily request quota exhaustion first (e.g. Free Tier RPD)
    daily_quota_indicators = (
        "generaterequestsperday",
        "per day",
        "daily",
        "requests per day",
        "rpd",
        "free-tier",
        "freetier",
    )
    if (status_code == 429 or "RESOURCE_EXHAUSTED" in status_str or "quota" in message_str) and any(
        d in message_str for d in daily_quota_indicators
    ):
        return "DAILY_QUOTA", status_code or 429, "DAILY_QUOTA_EXHAUSTED"

    # 1. Direct HTTP status codes or status strings for transient errors
    if status_code in {503, 429, 500, 502, 504} or status_str in {"UNAVAILABLE", "RESOURCE_EXHAUSTED", "INTERNAL"}:
        code = status_code or (503 if "UNAVAILABLE" in status_str else 429 if "RESOURCE_EXHAUSTED" in status_str else 500)
        return "TRANSIENT", code, status_str or f"HTTP_{code}"

    # Transient error keywords in message or exception type
    transient_indicators = (
        "503", "unavailable",
        "429", "resource_exhausted", "rate limit", "quota",
        "500", "internal server error",
        "502", "bad gateway",
        "504", "gateway timeout",
        "timeout", "timed out", "connection error", "connection reset",
        "connection refused", "remoteprotocolerror", "network"
    )
    if any(ind in message_str for ind in transient_indicators):
        code = status_code or (503 if "503" in message_str or "unavailable" in message_str else 429 if "429" in message_str else 500)
        return "TRANSIENT", code, status_str or f"HTTP_{code}"

    # 2. Direct HTTP status codes or status strings for permanent errors
    if status_code in {400, 401, 403, 404, 422} or status_str in {"INVALID_ARGUMENT", "PERMISSION_DENIED", "UNAUTHENTICATED", "NOT_FOUND"}:
        return "PERMANENT", status_code, status_str or f"HTTP_{status_code}"

    permanent_indicators = (
        "400", "invalid_argument", "invalid argument",
        "401", "unauthenticated", "invalid api key", "api_key",
        "403", "permission_denied", "permission denied",
        "404", "not_found", "not found"
    )
    if any(ind in message_str for ind in permanent_indicators):
        return "PERMANENT", status_code or 400, status_str or "PERMANENT_CLIENT_ERROR"

    return "UNKNOWN", status_code, status_str or type(exc).__name__


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        if not self._client:
            key = self.api_key or settings.gemini_api_key
            if not key:
                raise RuntimeError("GEMINI_API_KEY is not configured")
            self._client = genai.Client(api_key=key)
        return self._client

    @property
    def available(self) -> bool:
        return bool(self.api_key or settings.gemini_api_key)

    def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_completion_tokens: int = 6144,
        json_mode: bool = True,
        agent_name: Optional[str] = None,
        thinking_level: Optional[str] = None,
    ) -> LLMResult:
        client = self._get_client()
        selected = model or settings.gemini_model

        # Extract system prompt and user contents
        system_instruction: Optional[str] = None
        user_parts: list[str] = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content") or ""
            if role == "system":
                system_instruction = content
            else:
                user_parts.append(content)

        user_content = "\n\n".join(user_parts) if user_parts else "Hello"

        # Apply conservative thinking configuration (e.g. low for 3.8 flash, None for flash-lite)
        thinking_cfg = None
        effective_thinking = thinking_level if thinking_level is not None else getattr(settings, "gemini_thinking_level", None)
        if hasattr(types, "ThinkingConfig") and effective_thinking and effective_thinking.lower() not in ("none", "off", "disabled"):
            try:
                thinking_cfg = types.ThinkingConfig(thinking_level=effective_thinking.lower())
            except Exception:
                thinking_cfg = None

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_completion_tokens,
            system_instruction=system_instruction,
            response_mime_type="application/json" if json_mode else "text/plain",
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            thinking_config=thinking_cfg,
        )

        max_retries = 2  # Bounded retry: attempt 1 + 2 retries = 3 attempts total
        max_attempts = max_retries + 1
        base_delay = 1.0

        for attempt in range(1, max_attempts + 1):
            started = perf_counter()
            try:
                response = client.models.generate_content(
                    model=selected,
                    contents=user_content,
                    config=config,
                )
                latency_ms = (perf_counter() - started) * 1000
                content = response.text or ""

                usage: dict[str, Any] = {}
                if getattr(response, "usage_metadata", None):
                    u = response.usage_metadata
                    usage = {
                        "prompt_tokens": getattr(u, "prompt_token_count", None),
                        "completion_tokens": getattr(u, "candidates_token_count", None),
                        "total_tokens": getattr(u, "total_token_count", None),
                    }

                logger.info(
                    f"[GEMINI] attempt={attempt} status=SUCCESS latency_ms={latency_ms:.0f}",
                    extra={"provider": "gemini", "model": selected, "attempt": attempt, "agent": agent_name},
                )

                return LLMResult(
                    content=content,
                    model=selected,
                    latency_ms=latency_ms,
                    usage=usage,
                    raw=response,
                    provider="gemini",
                    attempts=attempt,
                    fallback_used=False,
                )

            except Exception as exc:
                latency_ms = (perf_counter() - started) * 1000
                category, status_code, status_desc = classify_gemini_error(exc)
                status_display = status_code or status_desc

                # Permanent client error -> DO NOT RETRY, fail immediately
                if category == "PERMANENT":
                    logger.error(
                        f"[GEMINI] attempt={attempt} status={status_display} permanent error -> failing immediately",
                        extra={"provider": "gemini", "model": selected, "attempt": attempt, "error": str(exc)},
                    )
                    raise GeminiPermanentError(
                        f"Gemini permanent client error ({status_display}): {exc}",
                        status_code=status_code,
                    ) from exc

                # Daily request quota exhaustion -> DO NOT RETRY, fail immediately to trigger fallback
                if category == "DAILY_QUOTA":
                    logger.warning(
                        f"[GEMINI] attempt={attempt} status={status_display} daily quota exhausted -> immediate fallback",
                        extra={"provider": "gemini", "model": selected, "attempt": attempt, "error": str(exc)},
                    )
                    raise GeminiDailyQuotaExhaustedError(
                        f"Gemini daily quota exhausted ({status_display}): {exc}",
                        status_code=status_code,
                    ) from exc

                # Transient error -> Bounded exponential backoff + jitter
                if category == "TRANSIENT":
                    logger.warning(
                        f"[GEMINI] attempt={attempt} status={status_display}",
                        extra={"provider": "gemini", "model": selected, "attempt": attempt, "status": status_display},
                    )

                    if attempt < max_attempts:
                        delay = (base_delay * (2 ** (attempt - 1))) + random.uniform(0.1, 0.4)
                        logger.warning(
                            f"[GEMINI] transient error -> retrying in {delay:.1f}s",
                            extra={"provider": "gemini", "model": selected, "attempt": attempt, "next_delay": delay},
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"[GEMINI] attempt={attempt} status={status_display}",
                            extra={"provider": "gemini", "model": selected, "attempt": attempt},
                        )
                        logger.error(
                            "[GEMINI] retries exhausted",
                            extra={"provider": "gemini", "model": selected, "attempts": attempt},
                        )
                        raise GeminiRetryExhaustedError(
                            f"Gemini retries exhausted after {attempt} attempts: {exc}",
                            attempts=attempt,
                            status_code=status_code,
                        ) from exc

                # If JSON mode token cutoff or schema error on an unknown error, try text/plain once
                if json_mode and ("RESOURCE_EXHAUSTED" not in str(exc)):
                    logger.warning(
                        "Gemini json_mode request failed, retrying without strict json mime type",
                        extra={"model": selected},
                    )
                    config_retry = types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_completion_tokens,
                        system_instruction=system_instruction,
                        response_mime_type="text/plain",
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                        thinking_config=thinking_cfg,
                    )
                    try:
                        response = client.models.generate_content(
                            model=selected,
                            contents=user_content,
                            config=config_retry,
                        )
                        latency_ms = (perf_counter() - started) * 1000
                        content = response.text or ""
                        return LLMResult(
                            content=content,
                            model=selected,
                            latency_ms=latency_ms,
                            usage={},
                            raw=response,
                            provider="gemini",
                            attempts=attempt,
                            fallback_used=False,
                        )
                    except Exception as retry_exc:
                        sub_cat, sub_code, sub_desc = classify_gemini_error(retry_exc)
                        if sub_cat == "TRANSIENT" and attempt < max_attempts:
                            delay = (base_delay * (2 ** (attempt - 1))) + random.uniform(0.1, 0.4)
                            time.sleep(delay)
                            continue
                        raise GeminiRetryExhaustedError(
                            f"Gemini request failed: {retry_exc}",
                            attempts=attempt,
                            status_code=sub_code,
                        ) from retry_exc

                # Any other unexpected exception
                if attempt < max_attempts:
                    delay = (base_delay * (2 ** (attempt - 1))) + random.uniform(0.1, 0.4)
                    time.sleep(delay)
                    continue
                raise GeminiRetryExhaustedError(
                    f"Gemini request failed: {exc}",
                    attempts=attempt,
                    status_code=status_code,
                ) from exc

        raise GeminiRetryExhaustedError(
            f"Gemini retries exhausted after {max_attempts} attempts",
            attempts=max_attempts,
        )


gemini_client = GeminiClient()
