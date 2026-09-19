from __future__ import annotations

from typing import Annotated, Any, Optional, TypedDict

def append_list(left: list | None, right: list | None) -> list:
    return (left or []) + (right or [])


class RetryCounts(TypedDict, total=False):
    security: int
    qa: int
    review: int


class ProjectState(TypedDict, total=False):
    project_id: str
    run_id: str
    user_id: str
    user_idea: str
    execution_mode: str
    current_stage: str
    current_agent: str
    demo_mode: bool
    stop_requested: bool
    developer_mode: str
    requested_stage: Optional[str]
    comparison_models: list[str]
    benchmark_prompt: Optional[str]
    primary_model: Optional[str]
    security_max_retries: int
    qa_max_retries: int
    review_max_retries: int
    requirements: Optional[dict[str, Any]]
    architecture: Optional[dict[str, Any]]
    visual_architecture: Optional[dict[str, Any]]
    code: Optional[dict[str, Any]]
    security_report: Optional[dict[str, Any]]
    test_report: Optional[dict[str, Any]]
    review_report: Optional[dict[str, Any]]
    model_comparison: Optional[dict[str, Any]]
    messages: Annotated[list[dict[str, Any]], append_list]
    workflow_events: Annotated[list[dict[str, Any]], append_list]
    retry_counts: RetryCounts
    security_status: str
    testing_status: str
    review_status: str
    developer_status: str
    validation_issues: list[dict[str, Any]]
    final_status: str
    errors: Annotated[list[dict[str, Any]], append_list]
    artifact_ids: Annotated[list[str], append_list]
    timestamps: dict[str, str]
    last_decision: Optional[str]


def initial_state(payload: dict[str, Any]) -> ProjectState:
    retries = payload.get("retry_counts") or {}
    return ProjectState(
        project_id=payload["project_id"],
        run_id=payload["run_id"],
        user_id=payload["user_id"],
        user_idea=payload["user_idea"],
        execution_mode=payload.get("execution_mode") or "FULL_AUTONOMOUS",
        current_stage="START",
        current_agent="",
        demo_mode=bool(payload.get("demo_mode", True)),
        stop_requested=False,
        developer_mode=payload.get("developer_mode") or "INITIAL_IMPLEMENTATION",
        requested_stage=payload.get("requested_stage"),
        comparison_models=payload.get("comparison_models") or [],
        benchmark_prompt=payload.get("benchmark_prompt"),
        primary_model=payload.get("primary_model"),
        security_max_retries=int(payload.get("security_max_retries", 2)),
        qa_max_retries=int(payload.get("qa_max_retries", 2)),
        review_max_retries=int(payload.get("review_max_retries", 2)),
        requirements=payload.get("requirements"),
        architecture=payload.get("architecture"),
        visual_architecture=payload.get("visual_architecture"),
        code=payload.get("code"),
        security_report=payload.get("security_report"),
        test_report=payload.get("test_report"),
        review_report=payload.get("review_report"),
        model_comparison=payload.get("model_comparison"),
        messages=[],
        workflow_events=[],
        retry_counts={"security": int(retries.get("security", 0)), "qa": int(retries.get("qa", 0)), "review": int(retries.get("review", 0))},
        security_status="PENDING",
        testing_status="PENDING",
        review_status="PENDING",
        developer_status="PENDING",
        validation_issues=[],
        final_status="PENDING",
        errors=[],
        artifact_ids=[],
        timestamps={},
        last_decision=None,
    )


_live_states: dict[str, dict[str, Any]] = {}


def get_live_state(run_id: str) -> dict[str, Any]:
    return _live_states.get(run_id) or {}


def update_live_state(run_id: str, updates: dict[str, Any]) -> None:
    if run_id not in _live_states:
        _live_states[run_id] = {}
    _live_states[run_id].update(updates)

