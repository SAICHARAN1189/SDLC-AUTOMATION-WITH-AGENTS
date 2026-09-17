from __future__ import annotations

import json
from collections import Counter
from typing import Any

from backend.agents.base import BaseEngineeringAgent
from backend.agents.demo_data import demo_security_fail, demo_security_pass
from backend.models.schemas import (
    AgentIdentity,
    AgentName,
    FindingSource,
    GateStatus,
    SecurityOutput,
    Vulnerability,
)
from backend.tools.security_scanner import scan_files


class SecurityAgent(BaseEngineeringAgent):
    identity = AgentIdentity(
        name=AgentName.SECURITY,
        display_name="Security Scanner Agent",
        role="Combine deterministic scanning with LLM interpretation of application source",
        goal="Classify findings, mark blocking issues, and produce remediation guidance",
        instructions=(
            "Inspect code with deterministic scanners first. Interpret results. "
            "Mark HIGH/CRITICAL as blocking. This is not a certified security product."
        ),
        tools=["deterministic_security_scanner", "secret_pattern_detector", "source_inspection"],
        default_model_slot="reasoning",
    )
    output_model = SecurityOutput

    def observe(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "code": state.get("code"),
            "architecture": state.get("architecture"),
            "requirements": state.get("requirements"),
            "retry_counts": state.get("retry_counts") or {},
        }

    def demo_output(self, observed: dict[str, Any]) -> SecurityOutput:
        files = (observed.get("code") or {}).get("files") or []
        joined = "\n".join(item.get("content") or "" for item in files)
        if "super-secret-db-password" in joined or "f\"INSERT INTO orders" in joined or "f'INSERT INTO orders" in joined:
            return demo_security_fail()
        return demo_security_pass()

    def build_prompt(self, observed: dict[str, Any]) -> tuple[str, str]:
        files = (observed.get("code") or {}).get("files") or []
        deterministic = [finding.__dict__ for finding in scan_files(files)]
        system = (
            self.identity.instructions
            + " Merge deterministic findings with additional LLM analysis. Return SecurityOutput JSON. "
            "Set overall_status to FAIL and blocking true if any HIGH or CRITICAL remains."
        )
        user = json.dumps(
            {
                "deterministic_findings": deterministic,
                "files": [{"path": f.get("path"), "content": (f.get("content") or "")[:4000]} for f in files],
            }
        )
        return system, user

    def use_tools(self, observed: dict[str, Any], draft: SecurityOutput | None = None) -> dict[str, Any]:
        files = (observed.get("code") or {}).get("files") or []
        deterministic = scan_files(files)
        return {"deterministic": [item.__dict__ for item in deterministic]}

    def apply_tools(self, output: SecurityOutput, tool_context: dict[str, Any]) -> SecurityOutput:
        existing_keys = {(v.affected_file, v.affected_line, v.category) for v in output.vulnerabilities}
        for raw in tool_context.get("deterministic") or []:
            key = (raw.get("affected_file"), raw.get("affected_line"), raw.get("category"))
            if key in existing_keys:
                continue
            output.vulnerabilities.append(
                Vulnerability(
                    category=raw["category"],
                    severity=raw["severity"],
                    description=raw["description"],
                    evidence=raw["evidence"],
                    affected_file=raw.get("affected_file"),
                    affected_line=raw.get("affected_line"),
                    remediation=raw["remediation"],
                    confidence=raw.get("confidence", 0.9),
                    source=FindingSource.DETERMINISTIC_FINDING,
                )
            )
        counts = Counter(v.severity for v in output.vulnerabilities)
        output.severity_summary = {level: counts.get(level, 0) for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW")}
        blocking = counts.get("CRITICAL", 0) > 0 or counts.get("HIGH", 0) > 0
        output.blocking = blocking
        output.overall_status = GateStatus.FAIL if blocking else GateStatus.PASS
        output.affected_files = sorted({v.affected_file for v in output.vulnerabilities if v.affected_file})
        if blocking:
            for vuln in output.vulnerabilities:
                if vuln.severity in {"HIGH", "CRITICAL"}:
                    vuln.caused_rework = True
        return output
