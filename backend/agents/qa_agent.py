from __future__ import annotations

import json
from typing import Any

from backend.agents.base import BaseEngineeringAgent
from backend.agents.demo_data import demo_qa_fail, demo_qa_pass, demo_tests
from backend.models.schemas import AgentIdentity, AgentName, CodeFile, GateStatus, TestFailure, TestOutput
from backend.tools.test_execution import run_pytest


class QAAgent(BaseEngineeringAgent):
    identity = AgentIdentity(
        name=AgentName.QA,
        display_name="QA / Test Engineer",
        role="Design tests from requirements and execute them against generated code",
        goal="Produce real execution results and structured failure feedback",
        instructions=(
            "Create unit/integration/edge/negative tests. Execute them. Never fabricate execution counts. "
            "If execution is blocked, report executed=false."
        ),
        tools=["test_file_runner", "failure_parser"],
        default_model_slot="primary",
    )
    output_model = TestOutput

    def observe(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "requirements": state.get("requirements"),
            "architecture": state.get("architecture"),
            "code": state.get("code"),
            "retry_counts": state.get("retry_counts") or {},
        }

    def demo_output(self, observed: dict[str, Any]) -> TestOutput:
        retries = (observed.get("retry_counts") or {}).get("qa", 0)
        code = observed.get("code") or {}
        files = code.get("files") or []
        joined = "\n".join(item.get("content") or "" for item in files)
        if retries == 0 and "qty < 0" not in joined and "if not items" not in joined:
            return demo_qa_fail()
        return demo_qa_pass()

    def build_prompt(self, observed: dict[str, Any]) -> tuple[str, str]:
        system = (
            "You are a Senior QA Test Automation Engineer. "
            "Write comprehensive pytest test cases validating requirements against generated code. "
            "CRITICAL: 'generated_tests' MUST be an array of JSON objects with 'path' (e.g. 'tests/test_api.py') and 'content' (the complete, valid python pytest code). "
            "Do NOT output a list of file path strings. Each item in 'generated_tests' MUST have both 'path' and 'content'.\n"
            "Return ONLY a single valid JSON object strictly matching this schema with no markdown wrapper:\n"
            "{\n"
            '  "summary": "Generated test suite.",\n'
            '  "generated_tests": [\n'
            '    {\n'
            '      "path": "tests/test_api.py",\n'
            '      "content": "import pytest\\n\\ndef test_sample():\\n    assert True\\n"\n'
            '    }\n'
            '  ],\n'
            '  "recommendations": ["Execute pytest suite."]\n'
            "}"
        )
        reqs = observed.get("requirements") or {}
        code = observed.get("code") or {}
        files = code.get("files") or []
        arch = observed.get("architecture") or {}

        test_reqs = {
            "project_summary": reqs.get("project_summary"),
            "functional_requirements": reqs.get("functional_requirements") or [],
            "user_stories": reqs.get("user_stories") or [],
            "acceptance_criteria": reqs.get("acceptance_criteria") or [],
            "edge_cases": reqs.get("edge_cases") or [],
        }

        source_files = [
            {
                "path": f.path if hasattr(f, "path") else f.get("path"),
                "content": f.content if hasattr(f, "content") else f.get("content", ""),
            }
            for f in files
            if (hasattr(f, "path") or "path" in f)
        ]

        user = json.dumps(
            {
                "requirements": test_reqs,
                "framework": arch.get("backend") or "Flask",
                "source_files": source_files,
            }
        )
        return system, user

    def use_tools(self, observed: dict[str, Any], draft: TestOutput | None = None) -> dict[str, Any]:
        raw_source = (observed.get("code") or {}).get("files") or []
        source_files = [
            {
                "path": f.path if hasattr(f, "path") else f.get("path"),
                "content": f.content if hasattr(f, "content") else f.get("content", ""),
            }
            for f in raw_source
            if (hasattr(f, "path") or "path" in f)
        ]
        generated = list(draft.generated_tests) if draft and draft.generated_tests else demo_tests()
        result = run_pytest(
            [item.model_dump() if isinstance(item, CodeFile) else item for item in generated],
            extra_files=source_files,
        )
        return {"execution": result}

    def apply_tools(self, output: TestOutput, tool_context: dict[str, Any]) -> TestOutput:
        execution = tool_context.get("execution")
        if not execution:
            output.executed = False
            output.overall_status = GateStatus.FAIL
            output.severity = "HIGH"
            return output
        output.executed = execution.executed
        output.total = execution.total
        output.passed = execution.passed
        output.failed = execution.failed
        output.skipped = execution.skipped
        output.duration = execution.duration
        output.failures = [
            TestFailure(
                test_name=item.get("test_name") or item.get("test") or "unknown",
                test=item.get("test") or item.get("test_name") or "unknown",
                expected=item.get("expected"),
                actual=item.get("actual"),
                root_cause=item.get("root_cause"),
                affected_files=item.get("affected_files") or [],
                recommended_fix=item.get("recommended_fix"),
                stack_trace=item.get("stack_trace"),
                affected_component=(item.get("affected_files") or [None])[0] or "generated_tests",
            )
            for item in execution.failures
        ]
        output.summary = execution.stdout or output.summary
        output.overall_status = GateStatus.PASS if execution.failed == 0 and execution.executed else GateStatus.FAIL
        output.status = "PASS" if execution.failed == 0 and execution.executed else "FAIL"
        output.severity = "HIGH" if (execution.failed > 0 or not execution.executed) else "LOW"
        if not output.generated_tests:
            output.generated_tests = demo_tests()
        return output
