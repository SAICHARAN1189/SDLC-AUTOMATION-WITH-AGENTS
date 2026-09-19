from __future__ import annotations

import json
from typing import Any

from backend.agents.base import BaseEngineeringAgent
from backend.agents.demo_data import demo_review_pass
from backend.models.schemas import AgentIdentity, AgentName, GateStatus, ReviewOutput


class ReviewAgent(BaseEngineeringAgent):
    identity = AgentIdentity(
        name=AgentName.REVIEW,
        display_name="Code Reviewer",
        role="Review implementation against requirements and architecture",
        goal="Decide whether blocking rework is required",
        instructions=(
            "Inspect correctness, architecture consistency, maintainability, tests, and security posture. "
            "Set rework_required if blocking issues exist."
        ),
        tools=["file_reader", "test_report_reader", "security_report_reader"],
        default_model_slot="reasoning",
    )
    output_model = ReviewOutput

    def observe(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "requirements": state.get("requirements"),
            "architecture": state.get("architecture"),
            "code": state.get("code"),
            "security_report": state.get("security_report"),
            "test_report": state.get("test_report"),
        }

    def demo_output(self, observed: dict[str, Any]) -> ReviewOutput:
        security = observed.get("security_report") or {}
        tests = observed.get("test_report") or {}
        if security.get("blocking") or tests.get("overall_status") == "FAIL":
            return ReviewOutput(
                review_status=GateStatus.FAIL,
                blocking_issues=["Downstream gates are not green"],
                findings=[],
                recommendations=["Resolve security/QA before final review"],
                required_changes=["Address failing gates"],
                summary="DEMO MODE: blocking because prior gates failed.",
                rework_required=True,
            )
        return demo_review_pass()

    def build_prompt(self, observed: dict[str, Any]) -> tuple[str, str]:
        system = (
            "You are a Principal Software Architect conducting Code Review. "
            "Review implementation against architecture, requirements, test reports, and security posture. "
            "Return ONLY a single valid JSON object strictly matching this schema with no markdown code fence:\n"
            "{\n"
            '  "review_status": "PASS",\n'
            '  "blocking_issues": [],\n'
            '  "findings": [\n'
            '    {"severity": "INFO", "category": "architecture", "description": "Clean modular implementation.", "recommendation": "Maintain test coverage."}\n'
            '  ],\n'
            '  "recommendations": ["Ready for deployment packaging."],\n'
            '  "required_changes": [],\n'
            '  "summary": "Code review passed with all quality gates satisfied.",\n'
            '  "rework_required": false\n'
            "}"
        )
        arch = observed.get("architecture") or {}
        reqs = observed.get("requirements") or {}
        sec = observed.get("security_report") or {}
        tests = observed.get("test_report") or {}
        code = observed.get("code") or {}

        compact = {
            "requirements": {
                "project_summary": reqs.get("project_summary"),
                "functional_requirements": reqs.get("functional_requirements") or [],
            },
            "architecture": {
                "style": arch.get("architecture_style"),
                "backend": arch.get("backend"),
                "database": arch.get("database"),
                "services": arch.get("services") or [],
                "apis": arch.get("apis") or [],
            },
            "files": [{"path": f.get("path"), "content": f.get("content")} for f in code.get("files") or []],
            "security_summary": {
                "status": sec.get("overall_status"),
                "blocking": sec.get("blocking"),
                "high_or_critical_issues": [
                    v.get("description")
                    for v in sec.get("vulnerabilities") or []
                    if v.get("severity") in ("CRITICAL", "HIGH")
                ],
            },
            "test_summary": {
                "status": tests.get("overall_status"),
                "total": tests.get("total"),
                "passed": tests.get("passed"),
                "failed": tests.get("failed"),
            },
        }
        return system, json.dumps(compact)

    def use_tools(self, observed: dict[str, Any], draft: ReviewOutput | None = None) -> dict[str, Any]:
        return {
            "file_count": len((observed.get("code") or {}).get("files") or []),
            "security_status": (observed.get("security_report") or {}).get("overall_status"),
            "qa_status": (observed.get("test_report") or {}).get("overall_status"),
        }
