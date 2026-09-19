from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from backend.llm.gemini_client import (
    GeminiClient,
    GeminiDailyQuotaExhaustedError,
    GeminiPermanentError,
    GeminiRetryExhaustedError,
    gemini_client,
)
from backend.llm.groq_client import (
    GroqClient,
    GroqPermanentError,
    GroqRateLimitExhaustedError,
    LLMResult,
    groq_client,
)


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM provider adapters."""

    name: str

    @property
    @abstractmethod
    def available(self) -> bool:
        """Whether the provider is configured and available for inference."""
        pass

    @abstractmethod
    def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        json_mode: bool = True,
        temperature: float = 0.2,
        max_completion_tokens: int = 6144,
        agent_name: Optional[str] = None,
        thinking_level: Optional[str] = None,
    ) -> LLMResult:
        """Executes inference for the given prompt messages."""
        pass


class GeminiProviderAdapter(BaseLLMProvider):
    name = "gemini"

    def __init__(self, client: Optional[GeminiClient] = None) -> None:
        self.client = client or gemini_client

    @property
    def available(self) -> bool:
        return self.client.available

    def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        json_mode: bool = True,
        temperature: float = 0.2,
        max_completion_tokens: int = 6144,
        agent_name: Optional[str] = None,
        thinking_level: Optional[str] = None,
    ) -> LLMResult:
        return self.client.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            json_mode=json_mode,
            agent_name=agent_name,
            thinking_level=thinking_level,
        )


class GroqProviderAdapter(BaseLLMProvider):
    name = "groq"

    def __init__(self, client: Optional[GroqClient] = None) -> None:
        self.client = client or groq_client

    @property
    def available(self) -> bool:
        return self.client.available

    def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        json_mode: bool = True,
        temperature: float = 0.2,
        max_completion_tokens: int = 6144,
        agent_name: Optional[str] = None,
        thinking_level: Optional[str] = None,
    ) -> LLMResult:
        return self.client.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            json_mode=json_mode,
            agent_name=agent_name,
        )


class MistralProviderAdapter(BaseLLMProvider):
    """
    Extensible adapter for future Mistral provider support.
    Can be hooked up without altering agent logic when Mistral API key is added.
    """

    name = "mistral"

    @property
    def available(self) -> bool:
        return False

    def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        json_mode: bool = True,
        temperature: float = 0.2,
        max_completion_tokens: int = 6144,
        agent_name: Optional[str] = None,
        thinking_level: Optional[str] = None,
    ) -> LLMResult:
        raise NotImplementedError("Mistral provider adapter is registered for future extensibility but not yet configured.")


_PROVIDERS: dict[str, BaseLLMProvider] = {
    "gemini": GeminiProviderAdapter(),
    "groq": GroqProviderAdapter(),
    "mistral": MistralProviderAdapter(),
}


def get_provider_adapter(name: str) -> BaseLLMProvider:
    key = name.lower().strip()
    if key not in _PROVIDERS:
        raise ValueError(f"Unsupported LLM provider: '{name}'. Available: {list(_PROVIDERS.keys())}")
    return _PROVIDERS[key]


def register_provider_adapter(provider: BaseLLMProvider) -> None:
    _PROVIDERS[provider.name.lower().strip()] = provider
