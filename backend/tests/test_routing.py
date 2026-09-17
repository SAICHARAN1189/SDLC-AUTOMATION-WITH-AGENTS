from __future__ import annotations

from backend.orchestration.routing import after_qa, after_review, after_security
from backend.orchestration.state import ProjectState


def _state(**kwargs) -> ProjectState:
    base: ProjectState = {
        "run_id": "t",
        "project_id": "p",
        "user_id": "u",
        "user_idea": "food delivery",
        "execution_mode": "FULL_AUTONOMOUS",
        "security_max_retries": 2,
        "qa_max_retries": 2,
        "review_max_retries": 2,
        "retry_counts": {"security": 0, "qa": 0, "review": 0},
        "stop_requested": False,
    }
    base.update(kwargs)
    return base


def test_security_failure_routes_to_developer():
    state = _state(security_report={"blocking": True, "overall_status": "FAIL"}, retry_counts={"security": 0})
    assert after_security(state) == "developer_node"


def test_security_pass_routes_to_qa():
    state = _state(security_report={"blocking": False, "overall_status": "PASS"})
    assert after_security(state) == "qa_node"


def test_security_retry_limit_routes_to_finalization():
    state = _state(
        security_report={"blocking": True, "overall_status": "FAIL"},
        retry_counts={"security": 2},
        security_max_retries=2,
    )
    assert after_security(state) == "finalization_node"


def test_qa_failure_routes_to_developer():
    state = _state(test_report={"overall_status": "FAIL", "failed": 1}, retry_counts={"qa": 0})
    assert after_qa(state) == "developer_node"


def test_qa_pass_routes_to_review():
    state = _state(test_report={"overall_status": "PASS", "failed": 0})
    assert after_qa(state) == "review_node"


def test_review_failure_routes_to_developer():
    state = _state(review_report={"rework_required": True, "review_status": "FAIL"}, retry_counts={"review": 0})
    assert after_review(state) == "developer_node"


def test_review_pass_routes_to_finalization():
    state = _state(review_report={"rework_required": False, "review_status": "PASS"})
    assert after_review(state) == "finalization_node"
