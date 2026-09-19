from __future__ import annotations

from typing import Any, Literal, Optional

from backend.config.settings import settings
from backend.llm.gemini_client import (
    GeminiPermanentError,
    GeminiRetryExhaustedError,
    gemini_client,
)
from backend.llm.groq_client import LLMResult, groq_client
from backend.utils.logging import logger

ModelSlot = Literal["primary", "fast", "reasoning"]


class LLMProvider:
    def __init__(self) -> None:
        self.gemini = gemini_client
        self.groq = groq_client

    @property
    def current_provider(self) -> str:
        return settings.llm_provider.lower().strip()

    def resolve_provider_for_model(self, model: Optional[str] = None) -> str:
        if model:
            lowered = model.lower()
            if "gemini" in lowered:
                return "gemini"
            if any(k in lowered for k in ("openai/", "groq/", "qwen/", "llama", "compound")):
                return "groq"
        return self.current_provider

    def resolve_provider_and_model(
        self, slot: ModelSlot = "primary", override: Optional[str] = None
    ) -> tuple[str, str]:
        """Returns (provider_name, model_id)."""
        if override:
            if override in ("groq/llama-3.3-70b-versatile", "llama-3.3-70b-versatile", "llama-3.3-70b"):
                override = settings.groq_model
            provider = self.resolve_provider_for_model(override)
            return provider, override

        provider = self.current_provider
        if provider == "gemini":
            mapping = {
                "primary": settings.gemini_model,
                "fast": settings.gemini_fast_model,
                "reasoning": settings.gemini_model,
            }
        else:
            mapping = {
                "primary": settings.groq_model,
                "fast": settings.groq_fast_model,
                "reasoning": settings.groq_model,
            }
        return provider, mapping.get(slot, mapping["primary"])

    def resolve_model(self, slot: ModelSlot = "primary", override: Optional[str] = None) -> str:
        _, model = self.resolve_provider_and_model(slot, override)
        return model

    def complete(
        self,
        system: str,
        user: str,
        slot: ModelSlot = "primary",
        model: Optional[str] = None,
        json_mode: bool = True,
        temperature: float = 0.2,
        max_completion_tokens: int = 6144,
        agent_name: Optional[str] = None,
    ) -> LLMResult:
        provider_name, selected_model = self.resolve_provider_and_model(slot, model)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        agent_label = agent_name or "SDLC Agent"

        # Case 1: Primary provider is Gemini
        if provider_name == "gemini":
            try:
                result = self.gemini.chat(
                    messages=messages,
                    model=selected_model,
                    json_mode=json_mode,
                    temperature=temperature,
                    max_completion_tokens=max_completion_tokens,
                    agent_name=agent_name,
                )
                logger.info(
                    f"[{agent_label}]\nProvider: Gemini\nModel: {result.model}\nAttempt: {result.attempts}\nStatus: SUCCESS\nFallback: false"
                )
                return result

            except GeminiPermanentError as perm_err:
                # Permanent client error (400, 401, 403, 404) -> Fail immediately, do NOT retry or fallback
                logger.error(
                    f"[{agent_label}]\nProvider: Gemini\nModel: {selected_model}\nStatus: {perm_err.status_code or 400}\nAction: FAIL (Permanent Error)"
                )
                raise

            except (GeminiRetryExhaustedError, Exception) as exc:
                # Transient retries exhausted or network failure -> Check Groq automatic fallback
                status_code = getattr(exc, "status_code", 503) or 503
                attempts = getattr(exc, "attempts", 3)

                logger.warning(f"[GEMINI] retries exhausted -> switching to Groq")
                logger.warning(
                    f"[{agent_label}]\nProvider: Gemini\nModel: {selected_model}\nAttempt: {attempts}\nStatus: {status_code}\nAction: Fallback"
                )

                if settings.enable_llm_fallback and self.groq.available:
                    fallback_model = settings.groq_fallback_model  # "openai/gpt-oss-20b"
                    try:
                        fallback_result = self.groq.chat(
                            messages=messages,
                            model=fallback_model,
                            json_mode=json_mode,
                            temperature=temperature,
                            max_completion_tokens=max_completion_tokens,
                        )
                        fallback_result.fallback_used = True
                        fallback_result.attempts = attempts + 1
                        logger.info(
                            f"[{agent_label}]\nProvider: Groq\nModel: {fallback_model}\nStatus: SUCCESS\nFallback: true"
                        )
                        return fallback_result
                    except Exception as groq_exc:
                        logger.error(
                            f"[{agent_label}]\nProvider: Groq\nModel: {fallback_model}\nStatus: FAILED\nError: {groq_exc}"
                        )
                        raise RuntimeError(
                            f"LLM_ERROR: Primary (Gemini) exhausted retries ({exc}), and fallback (Groq) also failed: {groq_exc}"
                        ) from groq_exc
                else:
                    raise

        # Case 2: Provider is Groq (e.g. manual model selection or test)
        return self.groq.chat(
            messages=messages,
            model=selected_model,
            json_mode=json_mode,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
        )

    @property
    def available(self) -> bool:
        if self.current_provider == "gemini":
            return self.gemini.available
        return self.groq.available


provider = LLMProvider()
