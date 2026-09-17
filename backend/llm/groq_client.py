from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Optional

from groq import Groq

from backend.config.settings import settings
from backend.models.schemas import ErrorCategory
from backend.utils.logging import logger


@dataclass
class LLMResult:
    content: str
    model: str
    latency_ms: float
    usage: dict[str, Any]
    raw: Any = None


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
        max_completion_tokens: int = 4096,
        json_mode: bool = True,
    ) -> LLMResult:
        if not self._client:
            raise RuntimeError("GROQ_API_KEY is not configured")
        selected = model or settings.primary_model
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
        return LLMResult(content=content, model=selected, latency_ms=latency_ms, usage=usage, raw=completion)


groq_client = GroqClient()
