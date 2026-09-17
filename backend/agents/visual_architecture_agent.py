from __future__ import annotations

import json
from typing import Any

from backend.agents.base import BaseEngineeringAgent
from backend.agents.demo_data import demo_visuals
from backend.models.schemas import AgentIdentity, AgentName, VisualArchitectureOutput
from backend.tools.mermaid_validator import validate_mermaid


class VisualArchitectureAgent(BaseEngineeringAgent):
    identity = AgentIdentity(
        name=AgentName.VISUAL_ARCHITECTURE,
        display_name="Visual Architecture Agent",
        role="Produce validated architecture diagrams",
        goal="Generate system, component, ER, sequence, and workflow diagrams",
        instructions="Create Mermaid diagrams plus node/edge data for React Flow. Keep diagrams consistent with architecture.",
        tools=["mermaid_validator"],
        default_model_slot="fast",
    )
    output_model = VisualArchitectureOutput

    def observe(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "requirements": state.get("requirements"),
            "architecture": state.get("architecture"),
        }

    def demo_output(self, observed: dict[str, Any]) -> VisualArchitectureOutput:
        return demo_visuals()

    def build_prompt(self, observed: dict[str, Any]) -> tuple[str, str]:
        system = (
            self.identity.instructions
            + " Return JSON {diagrams:[{diagram_type,title,mermaid_code,nodes,edges,metadata}]}."
        )
        return system, json.dumps(observed)

    def use_tools(self, observed: dict[str, Any], draft: VisualArchitectureOutput | None = None) -> dict[str, Any]:
        if not draft:
            return {}
        validations = []
        for diagram in draft.diagrams:
            result = validate_mermaid(diagram.mermaid_code)
            diagram.valid = result.valid
            diagram.validation_error = result.error
            validations.append(result.valid)
        return {"all_valid": all(validations)}
