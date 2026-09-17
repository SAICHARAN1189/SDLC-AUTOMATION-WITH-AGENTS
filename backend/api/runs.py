from __future__ import annotations

from flask import Blueprint, g, request

from backend.api.auth import require_auth
from backend.api.responses import fail, ok
from backend.config.settings import settings
from backend.orchestration.events import event_bus
from backend.orchestration.runner import continue_run, latest_state, request_stop, start_run_thread
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
    options = {
        "demo_mode": body.get("demo_mode", settings.demo_mode),
        "requested_stage": body.get("requested_stage"),
        "comparison_models": body.get("comparison_models") or settings.comparison_model_list,
        "benchmark_prompt": body.get("benchmark_prompt"),
        "primary_model": body.get("primary_model") or settings.primary_model,
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
        return fail("NOT_FOUND", "Run not found", status=404)
    return ok(event_bus.history(run_id))


@runs_bp.post("/api/runs/<run_id>/stop")
@require_auth
def stop_run(run_id: str):
    run = repositories.get_run(run_id, g.user["id"])
    if not run:
        return fail("NOT_FOUND", "Run not found", status=404)
    request_stop(run_id)
    repositories.update_run(run_id, status="STOPPED")
    return ok({"stopped": True})


@runs_bp.post("/api/runs/<run_id>/continue")
@require_auth
def resume(run_id: str):
    run = repositories.get_run(run_id, g.user["id"])
    if not run:
        return fail("NOT_FOUND", "Run not found", status=404)
    body = request.get_json(silent=True) or {}
    result = continue_run(run_id, body.get("requested_stage"))
    return ok({"state": result})
