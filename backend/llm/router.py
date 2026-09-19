from __future__ import annotations

from typing import Any, Optional

from backend.llm.config import AgentModelConfig, ModelTarget, get_agent_config
from backend.llm.gemini_client import (
    GeminiDailyQuotaExhaustedError,
    GeminiPermanentError,
    GeminiRetryExhaustedError,
)
from backend.llm.groq_client import (
    GroqPermanentError,
    GroqRateLimitExhaustedError,
    LLMResult,
)
from backend.llm.providers import get_provider_adapter
from backend.utils.logging import logger


class ModelRouter:
    """
    Centralized, deterministic Model Router that maps an SDLC agent task to its
    preferred LLM and configured fallback chain.
    """

    def get_config(self, agent_name: str) -> AgentModelConfig:
        return get_agent_config(agent_name)

    def get_model(self, agent_name: str) -> str:
        """Returns the primary model string for the specified agent."""
        return self.get_config(agent_name).primary.model

    def get_provider(self, agent_name: str) -> str:
        """Returns the primary provider string for the specified agent."""
        return self.get_config(agent_name).primary.provider

    def resolve_provider_for_model(self, model: str) -> str:
        lowered = model.lower()
        if "gemini" in lowered:
            return "gemini"
        if any(k in lowered for k in ("openai/", "groq/", "qwen/", "llama", "compound")):
            return "groq"
        if "mistral" in lowered:
            return "mistral"
        return "gemini"

    def generate(
        self,
        agent_name: str,
        messages: list[dict[str, str]],
        model_override: Optional[str] = None,
        json_mode: bool = True,
        temperature: float = 0.2,
        max_completion_tokens: int = 6144,
        thinking_level: Optional[str] = None,
    ) -> LLMResult:
        agent_config = self.get_config(agent_name)
        display_name = agent_name.replace("_agent", "").replace("_node", "").replace("_", " ").title()

        # Build candidate chain
        # If an explicit model override was requested (and is not a placeholder), use it as primary
        if model_override and model_override.lower() not in ("auto", "router", "default", "none", ""):
            primary_target = ModelTarget(
                provider=self.resolve_provider_for_model(model_override),
                model=model_override,
                thinking_level=thinking_level,
            )
            candidates = [primary_target] + agent_config.fallbacks
        else:
            candidates = [agent_config.primary] + agent_config.fallbacks

        primary_model_name = candidates[0].model
        last_error: Optional[Exception] = None

        for idx, target in enumerate(candidates):
            is_fallback = idx > 0
            provider_adapter = get_provider_adapter(target.provider)

            if not provider_adapter.available:
                logger.warning(
                    f"[MODEL ROUTER] Provider '{target.provider}' not available for model '{target.model}'. Skipping to next candidate."
                )
                continue

            # Observability logging
            if not is_fallback:
                logger.info(
                    f"\n[MODEL ROUTER]\nAgent: {display_name}\nProvider: {target.provider.title()}\nModel: {target.model}"
                )
            else:
                logger.info(
                    f"\n[MODEL ROUTER]\nFallback Provider: {target.provider.title()}\nFallback Model: {target.model}"
                )

            # Determine thinking level: agent config or argument
            target_thinking = target.thinking_level if target.thinking_level is not None else thinking_level

            try:
                result = provider_adapter.generate(
                    messages=messages,
                    model=target.model,
                    json_mode=json_mode,
                    temperature=temperature,
                    max_completion_tokens=max_completion_tokens,
                    agent_name=display_name,
                    thinking_level=target_thinking,
                )
                if is_fallback:
                    result.fallback_used = True
                return result

            except (GeminiPermanentError, GroqPermanentError) as perm_exc:
                # Permanent non-retryable client error -> fail immediately without fallback
                logger.error(
                    f"\n[MODEL ROUTER]\nAgent: {display_name}\nProvider: {target.provider.title()}\nModel: {target.model}\nError: PERMANENT_CLIENT_ERROR ({perm_exc})\nAction: FAIL (Permanent)"
                )
                raise

            except GeminiDailyQuotaExhaustedError as quota_exc:
                # Daily request quota reached -> Immediately fallback without retrying
                last_error = quota_exc
                logger.warning(
                    f"\n[MODEL ROUTER]\nAgent: {display_name}\nPrimary: {target.model}\nError: 429 DAILY_QUOTA\nAction: FALLBACK"
                )
                continue

            except (GeminiRetryExhaustedError, GroqRateLimitExhaustedError, Exception) as exc:
                last_error = exc
                error_desc = getattr(exc, "status_code", None) or type(exc).__name__
                logger.warning(
                    f"\n[MODEL ROUTER]\nAgent: {display_name}\nPrimary: {target.model}\nError: {error_desc}\nAction: FALLBACK"
                )
                continue

        # All primary and fallback candidates failed
        err_msg = (
            f"All LLM candidates exhausted for agent '{display_name}'. "
            f"Primary: {primary_model_name}, Last Error: {last_error}"
        )
        logger.error(f"[MODEL ROUTER] {err_msg}")
        raise RuntimeError(f"LLM_ERROR: {err_msg}") from last_error


model_router = ModelRouter()
