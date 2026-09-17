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
            self.identity.instructions
            + " Return TestOutput JSON including generated_tests files. Execution results will be filled by tools."
        )
        return system, json.dumps(
            {
                "requirements": observed.get("requirements"),
                "files": [f.get("path") for f in (observed.get("code") or {}).get("files") or []],
            }
        )

    def use_tools(self, observed: dict[str, Any], draft: TestOutput | None = None) -> dict[str, Any]:
        source_files = (observed.get("code") or {}).get("files") or []
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
            return output
        output.executed = execution.executed
        output.total = execution.total
        output.passed = execution.passed
        output.failed = execution.failed
        output.skipped = execution.skipped
        output.duration = execution.duration
        output.failures = [
            TestFailure(
                test_name=item.get("test_name") or "unknown",
                stack_trace=item.get("stack_trace"),
                affected_component="generated_tests",
            )
            for item in execution.failures
        ]
        output.summary = execution.stdout or output.summary
        output.overall_status = GateStatus.PASS if execution.failed == 0 and execution.executed else GateStatus.FAIL
        if not output.generated_tests:
            output.generated_tests = demo_tests()
        return output
