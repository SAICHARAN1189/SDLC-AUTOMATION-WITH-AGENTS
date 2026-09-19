from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ModelTarget:
    provider: str
    model: str
    thinking_level: Optional[str] = None

    def to_dict(self) -> dict[str, str]:
        data = {"provider": self.provider, "model": self.model}
        if self.thinking_level:
            data["thinking_level"] = self.thinking_level
        return data


@dataclass
class AgentModelConfig:
    primary: ModelTarget
    fallbacks: list[ModelTarget] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "primary": self.primary.to_dict(),
            "fallbacks": [fb.to_dict() for fb in self.fallbacks],
        }


# Standard model identifiers
GEMINI_3_5_FLASH_LITE = "gemini-3.5-flash-lite"
GEMINI_3_8_FLASH = "gemini-3.8-flash"
GEMINI_3_1_FLASH_LITE = "gemini-3.1-flash-lite"
GROQ_GPT_OSS_120B = "openai/gpt-oss-120b"
GROQ_GPT_OSS_20B = "openai/gpt-oss-20b"

# Centralized Agent-to-Model mappings with per-agent fallback chains
AGENT_MODEL_CONFIG: dict[str, AgentModelConfig] = {
    "requirements": AgentModelConfig(
        primary=ModelTarget(provider="gemini", model=GEMINI_3_5_FLASH_LITE),
        fallbacks=[
            ModelTarget(provider="gemini", model=GEMINI_3_1_FLASH_LITE),
            ModelTarget(provider="groq", model=GROQ_GPT_OSS_20B),
        ],
    ),
    "architecture": AgentModelConfig(
        primary=ModelTarget(provider="gemini", model=GEMINI_3_8_FLASH, thinking_level="low"),
        fallbacks=[
            ModelTarget(provider="gemini", model=GEMINI_3_5_FLASH_LITE),
            ModelTarget(provider="groq", model=GROQ_GPT_OSS_20B),
        ],
    ),
    "visual_architecture": AgentModelConfig(
        primary=ModelTarget(provider="gemini", model=GEMINI_3_1_FLASH_LITE),
        fallbacks=[
            ModelTarget(provider="gemini", model=GEMINI_3_5_FLASH_LITE),
            ModelTarget(provider="groq", model=GROQ_GPT_OSS_20B),
        ],
    ),
    "developer": AgentModelConfig(
        primary=ModelTarget(provider="groq", model=GROQ_GPT_OSS_120B),
        fallbacks=[
            ModelTarget(provider="gemini", model=GEMINI_3_5_FLASH_LITE),
            ModelTarget(provider="groq", model=GROQ_GPT_OSS_20B),
        ],
    ),
    "security": AgentModelConfig(
        primary=ModelTarget(provider="groq", model=GROQ_GPT_OSS_20B),
        fallbacks=[
            ModelTarget(provider="gemini", model=GEMINI_3_5_FLASH_LITE),
        ],
    ),
    "qa": AgentModelConfig(
        primary=ModelTarget(provider="groq", model=GROQ_GPT_OSS_120B),
        fallbacks=[
            ModelTarget(provider="gemini", model=GEMINI_3_5_FLASH_LITE),
            ModelTarget(provider="groq", model=GROQ_GPT_OSS_20B),
        ],
    ),
    "review": AgentModelConfig(
        primary=ModelTarget(provider="gemini", model=GEMINI_3_5_FLASH_LITE),
        fallbacks=[
            ModelTarget(provider="gemini", model=GEMINI_3_1_FLASH_LITE),
            ModelTarget(provider="groq", model=GROQ_GPT_OSS_20B),
        ],
    ),
}

# Aliases for different agent key naming conventions
for key, conf in list(AGENT_MODEL_CONFIG.items()):
    AGENT_MODEL_CONFIG[f"{key}_agent"] = conf
    AGENT_MODEL_CONFIG[f"{key}_node"] = conf


def get_agent_config(agent_name: str) -> AgentModelConfig:
    normalized = agent_name.lower().strip()
    if normalized in AGENT_MODEL_CONFIG:
        return AGENT_MODEL_CONFIG[normalized]
    stripped = normalized.replace("_agent", "").replace("_node", "").replace(" ", "_")
    if stripped in AGENT_MODEL_CONFIG:
        return AGENT_MODEL_CONFIG[stripped]
    # Default fallback mapping if unrecognized agent
    return AgentModelConfig(
        primary=ModelTarget(provider="gemini", model=GEMINI_3_5_FLASH_LITE),
        fallbacks=[ModelTarget(provider="groq", model=GROQ_GPT_OSS_20B)],
    )
