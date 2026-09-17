from __future__ import annotations

from typing import Literal, Optional

from backend.config.settings import settings
from backend.llm.groq_client import LLMResult, groq_client


ModelSlot = Literal["primary", "fast", "reasoning"]


class LLMProvider:
    def resolve_model(self, slot: ModelSlot = "primary", override: Optional[str] = None) -> str:
        if override:
            return override
        mapping = {
            "primary": settings.primary_model,
            "fast": settings.fast_model,
            "reasoning": settings.reasoning_model,
        }
        return mapping[slot]

    def complete(
        self,
        system: str,
        user: str,
        slot: ModelSlot = "primary",
        model: Optional[str] = None,
        json_mode: bool = True,
        temperature: float = 0.2,
        max_completion_tokens: int = 4096,
    ) -> LLMResult:
        selected = self.resolve_model(slot, model)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return groq_client.chat(
            messages=messages,
            model=selected,
            json_mode=json_mode,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
        )

    @property
    def available(self) -> bool:
        return groq_client.available


provider = LLMProvider()
