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


@runner_bp.route("/api/runs/<run_id>/app/proxy/", defaults={"subpath": ""}, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@runner_bp.route("/api/runs/<run_id>/app/proxy/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def proxy_run_app(run_id: str, subpath: str = ""):
    import mimetypes
    import urllib.error
    import urllib.request
    from flask import Response
    from backend.tools.app_runner import RUNNING_APPS

    # 1. Forward to running app process if active
    app_info = RUNNING_APPS.get(run_id)
    if app_info and app_info.status == "running" and app_info.port:
        target_url = f"http://127.0.0.1:{app_info.port}/{subpath}"
        if request.query_string:
            target_url += f"?{request.query_string.decode('utf-8')}"
        try:
            req = urllib.request.Request(
                target_url,
                data=request.get_data() if request.method in ("POST", "PUT", "PATCH") else None,
                headers={k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")},
                method=request.method,
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                resp_data = resp.read()
                content_type = resp.headers.get("Content-Type", "text/html; charset=utf-8")
                return Response(resp_data, status=resp.status, content_type=content_type)
        except urllib.error.HTTPError as he:
            return Response(he.read(), status=he.code, content_type=he.headers.get("Content-Type", "text/plain"))
        except Exception as e:
            logger.warning(f"[Proxy] Forwarding to {target_url} failed: {e}")

    # 2. Fallback: serve directly from code artifact files
    artifacts = repositories.list_artifacts(run_id)
    code_artifacts = [a for a in artifacts if a.get("artifact_type") == "code"]
    if not code_artifacts:
        return Response("<h1>404 Not Found</h1><p>No code artifact available for this run.</p>", status=404, mimetype="text/html")

    raw_content = code_artifacts[-1].get("content")
    data = json.loads(raw_content) if isinstance(raw_content, str) else (raw_content or {})
    files = data.get("files") or []
    files_map = {f.get("path", "").replace("\\", "/"): f.get("content", "") for f in files}

    # Normalize lookup path
    lookup_path = subpath.strip("/")
    if not lookup_path or lookup_path == "index.html":
        for cand in ("static/index.html", "index.html", "frontend/index.html", "public/index.html"):
            if cand in files_map:
                lookup_path = cand
                break

    target_content = files_map.get(lookup_path)
    if target_content is None:
        for prefix in ("static/", "frontend/", "public/"):
            if prefix + lookup_path in files_map:
                target_content = files_map[prefix + lookup_path]
                lookup_path = prefix + lookup_path
                break

    if target_content is not None:
        mime_type, _ = mimetypes.guess_type(lookup_path)
        if not mime_type:
            if lookup_path.endswith(".js"):
                mime_type = "application/javascript"
            elif lookup_path.endswith(".css"):
                mime_type = "text/css"
            elif lookup_path.endswith(".html"):
                mime_type = "text/html; charset=utf-8"
            else:
                mime_type = "text/plain; charset=utf-8"
        return Response(target_content, status=200, mimetype=mime_type)

    if lookup_path.startswith("api/"):
        return Response(json.dumps({"status": "healthy", "service": "sdlc-nexus-mock", "uptime": "ok"}), status=200, mimetype="application/json")

    return Response(f"<h1>404 Not Found</h1><p>Resource '{subpath}' not found in codebase artifact.</p>", status=404, mimetype="text/html")

