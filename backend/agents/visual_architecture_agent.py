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
        arch = state.get("architecture") or {}
        reqs = state.get("requirements") or {}
        return {
            "style": arch.get("architecture_style") or "Modular",
            "frontend": arch.get("frontend") or "React",
            "backend": arch.get("backend") or "Flask",
            "database": arch.get("database") or "PostgreSQL",
            "services": (arch.get("services") or [])[:5],
            "modules": (arch.get("modules") or [])[:5],
            "apis": (arch.get("apis") or [])[:5],
            "project_summary": reqs.get("project_summary") or "",
        }

    def demo_output(self, observed: dict[str, Any]) -> VisualArchitectureOutput:
        return demo_visuals()

    def build_prompt(self, observed: dict[str, Any]) -> tuple[str, str]:
        system = (
            "You are a Software Visual Architect. "
            "Generate 2 concise Mermaid diagrams: 1 system architecture topology and 1 component flow. "
            "Keep Mermaid syntax clean and valid (use graph TD). Keep nodes/edges focused on 4 to 6 core components. "
            "Return JSON matching: {\"diagrams\": [{\"diagram_type\": \"architecture\", \"title\": \"System Architecture\", "
            "\"mermaid_code\": \"graph TD\\n  Client[Frontend] --> API[API Gateway]\\n  API --> DB[(Database)]\", "
            "\"nodes\": [{\"id\": \"Client\", \"label\": \"Frontend\", \"kind\": \"component\"}], "
            "\"edges\": [{\"source\": \"Client\", \"target\": \"API\", \"label\": \"HTTP\"}], \"metadata\": {}}]}"
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
