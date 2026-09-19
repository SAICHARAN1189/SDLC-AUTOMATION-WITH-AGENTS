from __future__ import annotations

import time
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Optional

from groq import Groq

from backend.config.settings import settings
from backend.models.schemas import ErrorCategory
from backend.utils.logging import logger


class GroqPermanentError(RuntimeError):
    """Raised for non-retryable client errors (400, 401, 403, 404)."""
    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GroqRateLimitExhaustedError(RuntimeError):
    """Raised when rate limits (TPM/RPM) are hit, prompting router fallback."""
    def __init__(self, message: str, status_code: Optional[int] = 429) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class LLMResult:
    content: str
    model: str
    latency_ms: float
    usage: dict[str, Any]
    raw: Any = None
    provider: str = "gemini"
    attempts: int = 1
    fallback_used: bool = False


class GroqClient:
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key if api_key is not None else settings.groq_api_key
        self._client: Optional[Groq] = Groq(api_key=self.api_key) if self.api_key else None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_completion_tokens: int = 6144,
        json_mode: bool = True,
        agent_name: Optional[str] = None,
    ) -> LLMResult:
        if not self._client:
            raise RuntimeError("GROQ_API_KEY is not configured")
        selected = model or settings.primary_model
        if selected in ("groq/llama-3.3-70b-versatile", "llama-3.3-70b-versatile", "llama-3.3-70b"):
            selected = settings.primary_model
        kwargs: dict[str, Any] = {
            "model": selected,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_completion_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        started = perf_counter()
        try:
            completion = self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            msg = str(exc).lower()
            status = getattr(exc, "status_code", None)

            # 1. JSON validate failed / token cutoff -> retry without strict response_format
            if json_mode and "json_validate_failed" in msg:
                logger.warning("Groq json_mode token cutoff, retrying without strict response_format", extra={"model": selected})
                kwargs_retry = dict(kwargs)
                kwargs_retry.pop("response_format", None)
                kwargs_retry["max_completion_tokens"] = max(max_completion_tokens, 4096)
                try:
                    completion = self._client.chat.completions.create(**kwargs_retry)
                except Exception as retry_exc:
                    logger.error("Groq json retry failed", extra={"model": selected, "error": str(retry_exc)})
                    raise RuntimeError(f"LLM_ERROR: {retry_exc}") from retry_exc

            # 2. Rate limits (TPM / RPM) -> bounded retry with safe context reduction
            elif status == 429 or "rate_limit" in msg or "rate limit" in msg or "tpm" in msg or "rpm" in msg:
                logger.warning("Groq rate limit encountered, applying bounded retry and safe reduction", extra={"model": selected})
                # Check for retry-after delay if present and brief
                retry_after = getattr(exc, "response", None)
                wait_sec = 1.0
                if retry_after and hasattr(retry_after, "headers"):
                    try:
                        wait_sec = min(float(retry_after.headers.get("retry-after", "1.0")), 2.0)
                    except Exception:
                        wait_sec = 1.0
                time.sleep(wait_sec)

                # Safe context reduction: reduce max_completion_tokens safely without modifying source content
                kwargs_reduced = dict(kwargs)
                kwargs_reduced["max_completion_tokens"] = min(max_completion_tokens, 4096)
                try:
                    completion = self._client.chat.completions.create(**kwargs_reduced)
                except Exception as retry_exc:
                    logger.warning("Groq rate limit exhausted after retry", extra={"model": selected, "error": str(retry_exc)})
                    raise GroqRateLimitExhaustedError(
                        f"Groq rate limit exhausted: {retry_exc}",
                        status_code=429,
                    ) from retry_exc

            # 3. Permanent client errors -> do not retry or blindly fallback
            elif status in {400, 401, 403, 404}:
                logger.error("Groq permanent error", extra={"model": selected, "error": str(exc)})
                raise GroqPermanentError(f"Groq permanent client error ({status}): {exc}", status_code=status) from exc

            else:
                logger.error("Groq request failed", extra={"model": selected, "error_category": ErrorCategory.LLM_ERROR.value})
                raise RuntimeError(f"LLM_ERROR: {exc}") from exc

        latency_ms = (perf_counter() - started) * 1000
        content = completion.choices[0].message.content or ""
        usage = {}
        if completion.usage:
            usage = {
                "prompt_tokens": getattr(completion.usage, "prompt_tokens", None),
                "completion_tokens": getattr(completion.usage, "completion_tokens", None),
                "total_tokens": getattr(completion.usage, "total_tokens", None),
            }
        return LLMResult(content=content, model=selected, latency_ms=latency_ms, usage=usage, raw=completion, provider="groq")


groq_client = GroqClient()
