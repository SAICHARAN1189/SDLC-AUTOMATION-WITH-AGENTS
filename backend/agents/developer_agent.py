from __future__ import annotations

import json
from typing import Any

from backend.agents.base import BaseEngineeringAgent
from backend.agents.demo_data import demo_initial_code, demo_secure_code
from backend.models.schemas import AgentIdentity, AgentName, CodeOutput, DeveloperMode
from backend.tools.file_tools import list_structure
from pathlib import Path
import tempfile


class DeveloperAgent(BaseEngineeringAgent):
    identity = AgentIdentity(
        name=AgentName.DEVELOPER,
        display_name="Developer Agent",
        role="Implement and revise application source from requirements, architecture, and feedback",
        goal="Produce a consistent file set and apply bounded rework from security, QA, and review",
        instructions=(
            "Plan implementation, generate files, and revise existing files using feedback. "
            "Honor architecture. Never embed live credentials."
        ),
        tools=["file_writer", "project_structure_reader"],
        default_model_slot="primary",
    )
    output_model = CodeOutput

    def observe(self, state: dict[str, Any]) -> dict[str, Any]:
        mode = state.get("developer_mode") or DeveloperMode.INITIAL_IMPLEMENTATION.value
        return {
            "user_idea": state.get("user_idea"),
            "requirements": state.get("requirements"),
            "architecture": state.get("architecture"),
            "code": state.get("code"),
            "security_report": state.get("security_report"),
            "test_report": state.get("test_report"),
            "review_report": state.get("review_report"),
            "developer_mode": mode,
        }

    def demo_output(self, observed: dict[str, Any]) -> CodeOutput:
        mode = observed.get("developer_mode")
        if mode in {
            DeveloperMode.SECURITY_REWORK.value,
            DeveloperMode.QA_REWORK.value,
            DeveloperMode.REVIEW_REWORK.value,
        }:
            output = demo_secure_code()
            output.mode = DeveloperMode(mode)
            return output
        return demo_initial_code()

    def build_prompt(self, observed: dict[str, Any]) -> tuple[str, str]:
        system = (
            self.identity.instructions
            + " Return JSON CodeOutput with files:[{path,content}]. Mode="
            + str(observed.get("developer_mode"))
        )
        compact = {
            "mode": observed.get("developer_mode"),
            "requirements": observed.get("requirements"),
            "architecture": observed.get("architecture"),
            "existing_files": [f.get("path") for f in (observed.get("code") or {}).get("files") or []],
            "security_feedback": observed.get("security_report"),
            "qa_feedback": observed.get("test_report"),
            "review_feedback": observed.get("review_report"),
        }
        return system, json.dumps(compact)

    def use_tools(self, observed: dict[str, Any], draft: CodeOutput | None = None) -> dict[str, Any]:
        if not draft:
            return {}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for item in draft.files:
                path = root / item.path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(item.content, encoding="utf-8")
            structure = list_structure(root)
        draft.project_structure = structure
        draft.changed_files = [item.path for item in draft.files]
        return {"structure": structure}
