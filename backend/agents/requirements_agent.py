from __future__ import annotations

import json
from typing import Any

from backend.agents.base import BaseEngineeringAgent
from backend.agents.demo_data import demo_requirements
from backend.models.schemas import AgentIdentity, AgentName, RequirementsOutput


class RequirementsAgent(BaseEngineeringAgent):
    identity = AgentIdentity(
        name=AgentName.REQUIREMENTS,
        display_name="Requirements Analyst",
        role="Translate a software idea into a structured requirements package",
        goal="Produce complete, testable requirements that downstream engineering agents can use",
        instructions=(
            "Observe the user idea. Identify users, stakeholders, functional and non-functional "
            "requirements, stories, acceptance criteria, assumptions, constraints, dependencies, "
            "edge cases, and risks. Return JSON only matching RequirementsOutput."
        ),
        tools=["none-deterministic"],
        default_model_slot="primary",
    )
    output_model = RequirementsOutput

    def observe(self, state: dict[str, Any]) -> dict[str, Any]:
        return {"user_idea": state.get("user_idea") or ""}

    def demo_output(self, observed: dict[str, Any]) -> RequirementsOutput:
        return demo_requirements(observed["user_idea"])

    def build_prompt(self, observed: dict[str, Any]) -> tuple[str, str]:
        system = (
            self.identity.instructions + " Return a JSON object with keys: "
            "project_summary (string), stakeholders (list of strings), target_users (list of strings), "
            "functional_requirements (list of strings), non_functional_requirements (list of strings), "
            "user_stories (list of strings), acceptance_criteria (list of strings), "
            "assumptions (list of strings), constraints (list of strings), dependencies (list of strings), "
            "edge_cases (list of strings), risks (list of strings)."
        )
        user = json.dumps({"user_idea": observed["user_idea"]})
        return system, user
