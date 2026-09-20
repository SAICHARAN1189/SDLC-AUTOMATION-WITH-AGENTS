from __future__ import annotations

import json
import logging
from flask import Blueprint, g, request

from backend.api.auth import require_auth
from backend.api.responses import fail, ok
from backend.persistence import repositories
from backend.tools.app_runner import get_app_status, start_app_runner, stop_app_runner

logger = logging.getLogger("sdlc_nexus.api.runner")

runner_bp = Blueprint("runner", __name__)


@runner_bp.post("/api/runs/<run_id>/app/start")
@require_auth
def start_run_app(run_id: str):
    # Support custom files provided in request or lookup from artifact
    body = request.get_json(silent=True) or {}
    files = body.get("files")

    if not files:
        # Load artifacts for run
        artifacts = repositories.list_artifacts(run_id)
        code_artifacts = [a for a in artifacts if a.get("artifact_type") == "code"]
        if not code_artifacts:
            return fail("NOT_FOUND", "No code artifact found for this run", status=404)

        raw_content = code_artifacts[-1].get("content")
        if isinstance(raw_content, str):
            try:
                data = json.loads(raw_content)
            except Exception:
                data = {}
        elif isinstance(raw_content, dict):
            data = raw_content
        else:
            data = {}

        files = data.get("files", [])

    if not files:
        return fail("NO_FILES", "No executable files found in code artifact", status=400)

    try:
        status_info = start_app_runner(run_id, files)
        return ok(status_info)
    except Exception as exc:
        logger.exception("Failed to start app runner: %s", exc)
        return fail("EXECUTION_ERROR", f"Could not start application: {exc}", status=500)


@runner_bp.post("/api/runs/<run_id>/app/stop")
@require_auth
def stop_run_app(run_id: str):
    try:
        result = stop_app_runner(run_id)
        return ok(result)
    except Exception as exc:
        logger.exception("Failed to stop app runner: %s", exc)
        return fail("STOP_ERROR", f"Could not stop application: {exc}", status=500)


@runner_bp.get("/api/runs/<run_id>/app/status")
@require_auth
def get_run_app_status(run_id: str):
    return ok(get_app_status(run_id))
