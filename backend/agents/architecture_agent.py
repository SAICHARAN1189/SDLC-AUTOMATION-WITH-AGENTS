from __future__ import annotations

import json
from typing import Any

from backend.agents.base import BaseEngineeringAgent
from backend.agents.demo_data import demo_architecture
from backend.models.schemas import AgentIdentity, AgentName, ArchitectureOutput


class ArchitectureAgent(BaseEngineeringAgent):
    identity = AgentIdentity(
        name=AgentName.ARCHITECTURE,
        display_name="System Architect",
        role="Design an internally consistent system architecture from requirements",
        goal="Select style, components, APIs, data model, authn/authz, and deployment shape",
        instructions=(
            "Observe the idea and requirements. Design a coherent architecture. Keep frontend, "
            "backend, database, APIs, and security considerations aligned with requirements."
        ),
        tools=["none-deterministic"],
        default_model_slot="reasoning",
    )
    output_model = ArchitectureOutput

    def observe(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_idea": state.get("user_idea"),
            "requirements": state.get("requirements"),
        }

    def demo_output(self, observed: dict[str, Any]) -> ArchitectureOutput:
        return demo_architecture(observed.get("user_idea") or "")

    def build_prompt(self, observed: dict[str, Any]) -> tuple[str, str]:
        system = self.identity.instructions + " Return JSON matching ArchitectureOutput."
        user = json.dumps(observed)
        return system, user
