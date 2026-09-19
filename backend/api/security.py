from flask import Blueprint, g, request

from backend.api.auth import require_auth
from backend.api.responses import fail, ok
from backend.persistence import repositories

security_bp = Blueprint("security", __name__)


@security_bp.get("/api/security")
@require_auth
def get_security_overview():
    project_id = request.args.get("project_id")
    overview = repositories.get_security_overview(g.user["id"], project_id=project_id)
    return ok(overview)


@security_bp.get("/api/security/<run_id>")
@require_auth
def get_security(run_id: str):
    run = repositories.get_run(run_id, g.user["id"])
    if not run:
        return fail("NOT_FOUND", "Run not found", status=404)
    return ok(repositories.get_run_security_output(run_id))
