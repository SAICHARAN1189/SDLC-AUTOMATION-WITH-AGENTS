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
        system = (
            f"{self.identity.instructions}\n\n"
            "You MUST return a valid JSON object matching ArchitectureOutput with the following fields:\n"
            "- architecture_style: (string, e.g. 'Modular Monolith' or 'Component-Based Client-Server')\n"
            "- frontend: (string, e.g. 'React with TypeScript and Tailwind CSS' or 'HTML5 / Modern Vanilla JS')\n"
            "- backend: (string, e.g. 'Python Flask REST API with blueprint modularity')\n"
            "- database: (string, e.g. 'PostgreSQL (Supabase) with SQLAlchemy ORM' or 'In-Memory / SQLite')\n"
            "- services: (list of strings representing service boundaries or functional components)\n"
            "- modules: (list of strings representing specific internal code modules)\n"
            "- apis: (list of strings, e.g. ['GET /api/v1/health', 'POST /api/v1/calculate', 'GET /api/v1/history'])\n"
            "- authentication: (string describing auth mechanism, e.g. 'Supabase Auth JWT' or 'Session cookies / None')\n"
            "- authorization: (string describing permissions, e.g. 'Role-based access control (RBAC)')\n"
            "- data_model: (list of strings representing primary entities or tables)\n"
            "- integrations: (list of strings representing external tools, APIs, or libraries)\n"
            "- deployment_architecture: (string describing target hosting, e.g. 'Containerized Docker / Cloud Run')\n"
            "- security_considerations: (list of strings with concrete threat mitigation measures)\n"
            "- scalability_considerations: (list of strings with caching, indexing, or scaling strategies)\n\n"
            "Ensure all string fields are populated with realistic, relevant technical choices and not left blank."
        )
        user = json.dumps(observed)
        return system, user
