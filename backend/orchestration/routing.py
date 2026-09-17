from __future__ import annotations

from typing import Literal

from backend.orchestration.state import ProjectState

Route = Literal[
    "requirements_node",
    "architecture_node",
    "visual_architecture_node",
    "developer_node",
    "security_node",
    "qa_node",
    "review_node",
    "model_comparison_node",
    "finalization_node",
    "__end__",
]


def _stopped(state: ProjectState) -> bool:
    return bool(state.get("stop_requested"))


def after_requirements(state: ProjectState) -> Route:
    if _stopped(state):
        return "__end__"
    if state.get("execution_mode") == "STEP_BY_STEP":
        return "__end__"
    return "architecture_node"


def after_architecture(state: ProjectState) -> Route:
    if _stopped(state) or state.get("execution_mode") == "STEP_BY_STEP":
        return "__end__"
    return "visual_architecture_node"


def after_visual(state: ProjectState) -> Route:
    if _stopped(state) or state.get("execution_mode") == "STEP_BY_STEP":
        return "__end__"
    return "developer_node"


def after_developer(state: ProjectState) -> Route:
    if _stopped(state) or state.get("execution_mode") == "STEP_BY_STEP":
        return "__end__"
    return "security_node"


def after_security(state: ProjectState) -> Route:
    if _stopped(state):
        return "__end__"
    report = state.get("security_report") or {}
    blocking = bool(report.get("blocking")) or report.get("overall_status") == "FAIL"
    retries = (state.get("retry_counts") or {}).get("security", 0)
    max_retries = int(state.get("security_max_retries") or 2)
    if blocking and retries >= max_retries:
        return "finalization_node"
    if blocking:
        return "developer_node"
    if state.get("execution_mode") == "STEP_BY_STEP":
        return "__end__"
    return "qa_node"


def after_qa(state: ProjectState) -> Route:
    if _stopped(state):
        return "__end__"
    report = state.get("test_report") or {}
    failed = report.get("overall_status") == "FAIL" or int(report.get("failed") or 0) > 0
    retries = (state.get("retry_counts") or {}).get("qa", 0)
    max_retries = int(state.get("qa_max_retries") or 2)
    if failed and retries >= max_retries:
        return "finalization_node"
    if failed:
        return "developer_node"
    if state.get("execution_mode") == "STEP_BY_STEP":
        return "__end__"
    return "review_node"


def after_review(state: ProjectState) -> Route:
    if _stopped(state):
        return "__end__"
    report = state.get("review_report") or {}
    rework = bool(report.get("rework_required")) or report.get("review_status") == "FAIL"
    retries = (state.get("retry_counts") or {}).get("review", 0)
    max_retries = int(state.get("review_max_retries") or 2)
    if rework and retries >= max_retries:
        return "finalization_node"
    if rework:
        return "developer_node"
    return "finalization_node"


def after_start(state: ProjectState) -> Route:
    if _stopped(state):
        return "__end__"
    if state.get("execution_mode") == "MODEL_COMPARISON":
        return "model_comparison_node"
    requested = state.get("requested_stage")
    mapping = {
        "REQUIREMENTS": "requirements_node",
        "ARCHITECTURE": "architecture_node",
        "VISUAL_ARCHITECTURE": "visual_architecture_node",
        "DEVELOPER": "developer_node",
        "SECURITY": "security_node",
        "QA": "qa_node",
        "REVIEW": "review_node",
        "MODEL_COMPARISON": "model_comparison_node",
        "FINALIZATION": "finalization_node",
    }
    if requested and requested in mapping:
        return mapping[requested]  # type: ignore[return-value]
    decision = state.get("last_decision")
    if decision in {"SECURITY_REWORK", "QA_REWORK", "REVIEW_REWORK"}:
        return "developer_node"
    if not state.get("requirements"):
        return "requirements_node"
    if not state.get("architecture"):
        return "architecture_node"
    if not state.get("visual_architecture"):
        return "visual_architecture_node"
    if not state.get("code"):
        return "developer_node"
    if (state.get("security_status") or "PENDING") in {"PENDING", "REWORK"}:
        return "security_node"
    if (state.get("testing_status") or "PENDING") in {"PENDING", "FAIL"} and state.get("security_status") == "PASS":
        return "qa_node"
    if (state.get("review_status") or "PENDING") == "PENDING" and state.get("testing_status") == "PASS":
        return "review_node"
    return "finalization_node"
