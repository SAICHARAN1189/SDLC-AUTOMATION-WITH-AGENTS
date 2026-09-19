from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.agents.developer_agent import DeveloperAgent
from backend.agents.qa_agent import QAAgent
from backend.models.schemas import (
    CodeFile,
    CodeOutput,
    DeveloperMode,
    GateStatus,
    TestFailure as SchemaTestFailure,
    TestOutput as SchemaTestOutput,
)
from backend.orchestration.nodes import developer_node, qa_node
from backend.orchestration.state import initial_state
from backend.tools.test_execution import TestRunResult as ExecutionTestRunResult, parse_pytest_output


def test_developer_initial_implementation_contract():
    """Verify INITIAL_IMPLEMENTATION prompt instructs complete generation and use_tools treats all files as changed."""
    dev = DeveloperAgent()
    observed = {
        "developer_mode": DeveloperMode.INITIAL_IMPLEMENTATION.value,
        "user_idea": "Build a modern interactive calculator web app with clean UI.",
        "requirements": {
            "project_summary": "Modern interactive web calculator",
            "functional_requirements": ["Basic arithmetic", "Responsive UI", "Keyboard support"],
        },
        "architecture": {
            "architecture_style": "FullStack",
            "backend": "Flask",
            "database": "None",
        },
        "code": None,
    }
    system_prompt, user_prompt = dev.build_prompt(observed)
    assert "INITIAL_IMPLEMENTATION" in system_prompt
    assert "COMPLETE, RUNNABLE project" in system_prompt
    assert "HTML" in system_prompt
    assert "CSS" in system_prompt

    # Initial draft generation
    draft = CodeOutput(
        project_structure=["index.html", "style.css", "app.js", "app.py", "requirements.txt"],
        files=[
            CodeFile(path="index.html", content="<!DOCTYPE html><html><body><h1>Calc</h1></body></html>"),
            CodeFile(path="style.css", content="body { margin: 0; }"),
            CodeFile(path="app.js", content="console.log('calc ready');"),
            CodeFile(path="app.py", content="from flask import Flask\napp = Flask(__name__)"),
            CodeFile(path="requirements.txt", content="flask\n"),
        ],
        dependencies=["flask"],
        setup_instructions=["pip install -r requirements.txt", "python app.py"],
        mode=DeveloperMode.INITIAL_IMPLEMENTATION,
    )
    result = dev.use_tools(observed, draft)
    assert len(draft.files) == 5
    assert len(draft.changed_files) == 5
    assert "index.html" in draft.changed_files
    assert "style.css" in draft.changed_files
    assert result["total_files"] == 5


def test_developer_rework_merges_without_dropping_existing_files():
    """Verify that during rework, returning only a patch merges into existing files without dropping them."""
    dev = DeveloperAgent()
    existing_files = [
        {"path": "index.html", "content": "<html><body>Old HTML</body></html>"},
        {"path": "style.css", "content": "body { color: black; }"},
        {"path": "calculator.py", "content": "def add(a, b):\n    return a - b  # BUG\n"},
        {"path": "requirements.txt", "content": "flask\n"},
    ]
    observed = {
        "developer_mode": DeveloperMode.QA_REWORK.value,
        "code": {"files": existing_files},
        "test_report": {
            "failures": [
                {
                    "test": "tests/test_calculator.py::test_add",
                    "expected": "4",
                    "actual": "0",
                    "root_cause": "Assertion failed: expected '4', but got '0'",
                    "affected_files": ["calculator.py"],
                    "stack_trace": "assert add(2, 2) == 4",
                }
            ]
        },
    }

    # Prompt check
    system_prompt, user_prompt = dev.build_prompt(observed)
    assert "REWORK" in system_prompt
    assert "DO NOT blindly add dependencies" in system_prompt
    user_data = json.loads(user_prompt)
    assert len(user_data["existing_files"]) == 4
    assert len(user_data["qa_test_failures_to_fix"]) == 1
    failure = user_data["qa_test_failures_to_fix"][0]
    assert failure["expected"] == "4"
    assert failure["actual"] == "0"
    assert failure["affected_files"] == ["calculator.py"]

    # Developer LLM returns ONLY the single fixed file
    patch_draft = CodeOutput(
        project_structure=["calculator.py"],
        files=[
            CodeFile(path="calculator.py", content="def add(a, b):\n    return a + b  # FIXED\n"),
        ],
        changed_files=["calculator.py"],
        change_summary="Fixed addition operator in calculator.py",
        mode=DeveloperMode.QA_REWORK,
    )

    dev.use_tools(observed, patch_draft)

    # All 4 files must exist in patch_draft.files!
    paths_in_draft = {f.path for f in patch_draft.files}
    assert paths_in_draft == {"index.html", "style.css", "calculator.py", "requirements.txt"}
    assert len(patch_draft.files) == 4

    # The updated file has the new content
    fixed_calc = next(f for f in patch_draft.files if f.path == "calculator.py")
    assert "a + b  # FIXED" in fixed_calc.content

    # Unmodified files preserved
    html_file = next(f for f in patch_draft.files if f.path == "index.html")
    assert "Old HTML" in html_file.content

    # changed_files must distinguish ONLY the modified file
    assert patch_draft.changed_files == ["calculator.py"]


def test_parse_pytest_output_assertion_failure():
    """Verify parse_pytest_output extracts test, expected, actual, root_cause, and affected_files."""
    stdout = """
=================================== FAILURES ===================================
__________________________________ test_add ___________________________________
tests/test_calculator.py:10: in test_add
    assert add(2, 2) == 4
calculator.py:2: in add
    return 0
E   AssertionError: assert 0 == 4
=========================== short test summary info ============================
FAILED tests/test_calculator.py::test_add - AssertionError: assert 0 == 4
1 failed in 0.05s
"""
    result = parse_pytest_output(stdout, "", 1)
    assert result.total == 1
    assert result.failed == 1
    assert result.passed == 0
    assert len(result.failures) == 1

    failure = result.failures[0]
    assert failure["test"] == "tests/test_calculator.py::test_add"
    assert failure["actual"] == "0"
    assert failure["expected"] == "4"
    assert "Assertion failed: expected '4', but got '0'" in failure["root_cause"]
    assert "tests/test_calculator.py" in failure["affected_files"]
    assert "calculator.py" in failure["affected_files"]


def test_parse_pytest_output_exception_failure():
    """Verify parse_pytest_output extracts root_cause and affected files for unhandled exceptions."""
    stdout = """
=================================== FAILURES ===================================
__________________________________ test_divide _________________________________
tests/test_calculator.py:15: in test_divide
    divide(10, 0)
calculator.py:5: in divide
    return a / b
E   ZeroDivisionError: division by zero
=========================== short test summary info ============================
FAILED tests/test_calculator.py::test_divide - ZeroDivisionError: division by zero
1 failed, 1 passed in 0.03s
"""
    result = parse_pytest_output(stdout, "", 1)
    assert result.failed == 1
    failure = result.failures[0]
    assert failure["test"] == "tests/test_calculator.py::test_divide"
    assert "ZeroDivisionError" in failure["root_cause"]
    assert "division by zero" in failure["root_cause"]
    assert "tests/test_calculator.py" in failure["affected_files"]
    assert "calculator.py" in failure["affected_files"]


def test_qa_agent_populates_rich_failures_and_severity():
    """Verify QAAgent sets severity=HIGH and populates rich TestFailure objects."""
    qa = QAAgent()
    output = SchemaTestOutput(
        summary="Test execution",
        generated_tests=[],
        recommendations=[],
    )
    fake_execution = ExecutionTestRunResult(
        executed=True,
        total=2,
        passed=1,
        failed=1,
        skipped=0,
        duration=0.1,
        stdout="1 failed, 1 passed in 0.1s",
        stderr="",
        failures=[
            {
                "test": "tests/test_api.py::test_status",
                "test_name": "tests/test_api.py::test_status",
                "expected": "200",
                "actual": "500",
                "root_cause": "Assertion failed: expected '200', but got '500'",
                "affected_files": ["app.py", "tests/test_api.py"],
                "stack_trace": "assert 500 == 200",
            }
        ],
    )
    updated = qa.apply_tools(output, {"execution": fake_execution})
    assert updated.overall_status == GateStatus.FAIL
    assert updated.severity == "HIGH"
    assert len(updated.failures) == 1
    f = updated.failures[0]
    assert f.test == "tests/test_api.py::test_status"
    assert f.expected == "200"
    assert f.actual == "500"
    assert f.root_cause == "Assertion failed: expected '200', but got '500'"
    assert f.affected_files == ["app.py", "tests/test_api.py"]


def test_developer_node_safety_merging():
    """Verify developer_node preserves existing files in state during rework even if output had fewer files."""
    state = initial_state(
        {
            "project_id": "p-safety",
            "run_id": "test-run-safety",
            "user_id": "u-safety",
            "user_idea": "Safety test app",
            "developer_mode": DeveloperMode.QA_REWORK.value,
            "code": {
                "files": [
                    {"path": "index.html", "content": "<h1>App</h1>"},
                    {"path": "style.css", "content": "body { color: red; }"},
                    {"path": "main.py", "content": "print('bug')"},
                ]
            },
        }
    )

    # Mock agent run returning only main.py
    with patch("backend.orchestration.nodes._run_agent") as mock_run:
        mock_run.return_value = (
            {
                "project_structure": ["main.py"],
                "files": [{"path": "main.py", "content": "print('fixed')"}],
                "changed_files": ["main.py"],
                "dependencies": [],
                "setup_instructions": [],
            },
            {},
        )
        node_output = developer_node(state)

    files = node_output["code"]["files"]
    file_paths = {f["path"] for f in files}
    assert file_paths == {"index.html", "style.css", "main.py"}
    fixed_main = next(f for f in files if f["path"] == "main.py")
    assert fixed_main["content"] == "print('fixed')"


def test_qa_node_bounded_rework_termination():
    """Verify qa_node stops safely and routes to MANUAL_INTERVENTION_REQUIRED when max retries is reached."""
    state = initial_state(
        {
            "project_id": "p-bounded",
            "run_id": "test-run-bounded",
            "user_id": "u-bounded",
            "user_idea": "Bounded retry app",
            "qa_max_retries": 2,
            "retry_counts": {"qa": 1},  # Already tried once
        }
    )

    # First retry -> retries becomes 2 -> triggers MANUAL_INTERVENTION_REQUIRED
    with patch("backend.orchestration.nodes._run_agent") as mock_run:
        mock_run.return_value = (
            {
                "overall_status": "FAIL",
                "failed": 1,
                "passed": 0,
                "total": 1,
                "summary": "1 failed",
                "failures": [
                    {
                        "test": "test_unfixable",
                        "expected": "true",
                        "actual": "false",
                        "root_cause": "unresolvable failure",
                        "affected_files": ["app.py"],
                    }
                ],
            },
            {},
        )
        result = qa_node(state)

    assert result["testing_status"] == "FAIL"
    assert result["retry_counts"]["qa"] == 2
    assert result["last_decision"] == "MANUAL_INTERVENTION_REQUIRED"
    assert result["final_status"] == "MANUAL_INTERVENTION_REQUIRED"


def test_app_root_route():
    """Verify GET / returns 200 and service metadata."""
    from backend.app import create_app

    app = create_app()
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "online"
    assert data["frontend_url"] == "http://localhost:5173"
