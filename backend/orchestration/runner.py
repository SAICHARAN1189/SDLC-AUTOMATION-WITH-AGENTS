from __future__ import annotations

import threading
from typing import Any

from backend.config.settings import settings
from backend.models.schemas import EventType, utc_now
from backend.orchestration.events import emit
from backend.orchestration.graph import invoke_workflow, resume_workflow
from backend.orchestration.state import initial_state
from backend.persistence import memory_store, repositories
from backend.persistence.database import database_available
from backend.utils.logging import logger

_stop_flags: dict[str, bool] = {}
_latest_state: dict[str, dict[str, Any]] = {}


def db_or_memory():
    return repositories if database_available() else memory_store


def request_stop(run_id: str) -> None:
    _stop_flags[run_id] = True


def latest_state(run_id: str) -> dict[str, Any]:
    return _latest_state.get(run_id) or {}


def start_run_thread(run: dict[str, Any], project: dict[str, Any], options: dict[str, Any]) -> None:
    thread = threading.Thread(target=_execute, args=(run, project, options), daemon=True)
    thread.start()


def _execute(run: dict[str, Any], project: dict[str, Any], options: dict[str, Any]) -> None:
    store = db_or_memory()
    run_id = run["id"]
    store.update_run(run_id, status="RUNNING", current_stage="START")
    emit(run_id, EventType.PIPELINE_STARTED.value, "Pipeline started", "START", status="RUNNING", metadata={"demo_mode": options.get("demo_mode")})
    state = initial_state(
        {
            "project_id": project["id"],
            "run_id": run_id,
            "user_id": run["user_id"],
            "user_idea": project["idea"],
            "execution_mode": run["execution_mode"],
            "demo_mode": options.get("demo_mode", settings.demo_mode),
            "requested_stage": options.get("requested_stage"),
            "comparison_models": options.get("comparison_models") or settings.comparison_model_list,
            "benchmark_prompt": options.get("benchmark_prompt"),
            "primary_model": options.get("primary_model") or settings.primary_model,
            "security_max_retries": options.get("security_max_retries", settings.security_max_retries),
            "qa_max_retries": options.get("qa_max_retries", settings.qa_max_retries),
            "review_max_retries": options.get("review_max_retries", settings.review_max_retries),
        }
    )
    try:
        if _stop_flags.get(run_id):
            state["stop_requested"] = True
        result = invoke_workflow(dict(state))
        if _stop_flags.get(run_id):
            result["stop_requested"] = True
            store.update_run(run_id, status="STOPPED", current_stage=result.get("current_stage"))
            return
        _latest_state[run_id] = result
        status = result.get("final_status") or "RUNNING"
        if run["execution_mode"] == "STEP_BY_STEP" and result.get("current_stage") != "FINALIZATION":
            status = "WAITING"
        elif status not in {"COMPLETED", "MANUAL_INTERVENTION_REQUIRED"}:
            status = "RUNNING" if result.get("current_stage") != "FINALIZATION" else "COMPLETED"
        store.update_run(
            run_id,
            status=status,
            current_stage=result.get("current_stage"),
            completed_at=utc_now() if status in {"COMPLETED", "MANUAL_INTERVENTION_REQUIRED"} else None,
        )
    except Exception as exc:
        logger.error("workflow failed", extra={"run_id": run_id, "error_category": "WORKFLOW_ERROR"})
        emit(run_id, EventType.PIPELINE_FAILED.value, str(exc), "WORKFLOW", status="FAILED")
        store.update_run(run_id, status="FAILED", error_message=str(exc), completed_at=utc_now())


def continue_run(run_id: str, requested_stage: str | None = None) -> dict[str, Any]:
    result = resume_workflow(run_id, {"requested_stage": requested_stage, "stop_requested": False})
    _latest_state[run_id] = result
    store = db_or_memory()
    status = result.get("final_status") or "WAITING"
    store.update_run(run_id, status=status if status != "PENDING" else "WAITING", current_stage=result.get("current_stage"))
    return result
