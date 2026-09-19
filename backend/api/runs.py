from __future__ import annotations

from flask import Blueprint, g, request

from backend.api.auth import require_auth
from backend.api.responses import fail, ok
from backend.config.settings import settings
from backend.models.schemas import EventType, utc_now
from backend.orchestration.events import emit, event_bus
from backend.orchestration.runner import (
    continue_run,
    latest_state,
    request_stop,
    start_continue_thread,
    start_run_thread,
)
from backend.persistence import repositories

runs_bp = Blueprint("runs", __name__)


@runs_bp.post("/api/projects/<project_id>/runs")
@require_auth
def create_run(project_id: str):
    project = repositories.get_project(project_id, g.user["id"])
    if not project:
        return fail("NOT_FOUND", "Project not found", status=404)
    body = request.get_json(silent=True) or {}
    execution_mode = body.get("execution_mode") or "FULL_AUTONOMOUS"
    req_model = body.get("primary_model")
    effective_model = req_model if req_model and req_model.lower() not in ("auto", "router", "default", "none") else None
    options = {
        "demo_mode": body.get("demo_mode", settings.demo_mode),
        "requested_stage": body.get("requested_stage"),
        "comparison_models": body.get("comparison_models") or settings.comparison_model_list,
        "benchmark_prompt": body.get("benchmark_prompt"),
        "primary_model": effective_model,
        "security_max_retries": body.get("security_max_retries", settings.security_max_retries),
        "qa_max_retries": body.get("qa_max_retries", settings.qa_max_retries),
        "review_max_retries": body.get("review_max_retries", settings.review_max_retries),
    }
    run = repositories.create_run(project_id, g.user["id"], execution_mode, options)
    start_run_thread(run, project, options)
    return ok(run, 201)


@runs_bp.get("/api/runs/<run_id>")
@require_auth
def get_run(run_id: str):
    run = repositories.get_run(run_id, g.user["id"])
    if not run:
        run = repositories.get_run(run_id)
        if not run:
            return fail("NOT_FOUND", "Run not found", status=404)
    return ok({**run, "state": latest_state(run_id), "events": event_bus.history(run_id)})


@runs_bp.get("/api/runs")
@require_auth
def list_runs():
    return ok(repositories.list_runs(g.user["id"]))


@runs_bp.get("/api/runs/<run_id>/events")
@require_auth
def get_events(run_id: str):
    run = repositories.get_run(run_id, g.user["id"])
    if not run:
        run = repositories.get_run(run_id)
        if not run:
            return fail("NOT_FOUND", "Run not found", status=404)
    return ok(event_bus.history(run_id))


@runs_bp.post("/api/runs/<run_id>/stop")
@require_auth
def stop_run(run_id: str):
    run = repositories.get_run(run_id, g.user["id"]) or repositories.get_run(run_id)
    if not run:
        return fail("NOT_FOUND", "Run not found", status=404)
    request_stop(run_id)
    repositories.update_run(run_id, status="STOPPED")
    return ok({"stopped": True})


@runs_bp.post("/api/runs/<run_id>/continue")
@require_auth
def resume(run_id: str):
    run = repositories.get_run(run_id, g.user["id"]) or repositories.get_run(run_id)
    if not run:
        return fail("NOT_FOUND", "Run not found", status=404)
    body = request.get_json(silent=True) or {}
    result = continue_run(run_id, body.get("requested_stage"))
    return ok({"state": result})


@runs_bp.post("/api/runs/<run_id>/intervention")
@require_auth
def handle_intervention(run_id: str):
    run = repositories.get_run(run_id, g.user["id"]) or repositories.get_run(run_id)
    if not run:
        return fail("NOT_FOUND", "Run not found", status=404)
    body = request.get_json(silent=True) or {}
    action = (body.get("action") or "OVERRIDE").upper()
    feedback = (body.get("feedback") or "").strip()

    if action == "COMPLETE":
        repositories.update_run(run_id, status="COMPLETED", completed_at=utc_now())
        emit(run_id, EventType.PIPELINE_COMPLETED.value, "Manual intervention: Pipeline approved and completed by engineer", "FINALIZATION", None, "COMPLETED")
        return ok({"status": "COMPLETED", "message": "Pipeline marked as completed"})

    elif action == "OVERRIDE":
        target_stage = body.get("requested_stage") or "REVIEW"
        updates = {
            "testing_status": "PASS",
            "security_status": "PASS",
            "final_status": "PENDING",
            "last_decision": None,
            "requested_stage": target_stage,
        }
        state = latest_state(run_id) or {}
        retry_counts = dict(state.get("retry_counts") or {})
        retry_counts["qa"] = 0
        retry_counts["security"] = 0
        updates["retry_counts"] = retry_counts

        emit(run_id, EventType.AGENT_STARTED.value, f"Manual intervention: Overriding gate and advancing to {target_stage}", target_stage, None, "RUNNING")
        repositories.update_run(run_id, status="RUNNING", current_stage=target_stage)
        start_continue_thread(run_id, target_stage, updates)
        return ok({"status": "RUNNING", "message": f"Gate overridden. Advancing to {target_stage}"})

    elif action == "REWORK":
        target_stage = body.get("requested_stage") or "DEVELOPER"
        user_msg = feedback or "Fix implementation according to manual intervention feedback"
        updates = {
            "developer_mode": "QA_REWORK",
            "final_status": "PENDING",
            "last_decision": "QA_REWORK",
            "requested_stage": target_stage,
            "user_feedback": user_msg,
        }
        state = latest_state(run_id) or {}
        retry_counts = dict(state.get("retry_counts") or {})
        retry_counts["qa"] = 0
        updates["retry_counts"] = retry_counts

        emit(run_id, EventType.REWORK_STARTED.value, f"Manual intervention: Triggered rework with feedback: {user_msg}", "DEVELOPMENT", "developer_agent", "RUNNING")
        repositories.update_run(run_id, status="RUNNING", current_stage="DEVELOPMENT")
        start_continue_thread(run_id, target_stage, updates)
        return ok({"status": "RUNNING", "message": f"Rework triggered for {target_stage}"})

    return fail("INVALID_ACTION", f"Unknown intervention action: {action}")
