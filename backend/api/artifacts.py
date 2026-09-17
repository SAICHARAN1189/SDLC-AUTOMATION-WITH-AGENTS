from flask import Blueprint, g

from backend.api.auth import require_auth
from backend.api.responses import fail, ok
from backend.persistence import repositories

artifacts_bp = Blueprint("artifacts", __name__)


@artifacts_bp.get("/api/runs/<run_id>/artifacts")
@require_auth
def list_artifacts(run_id: str):
    run = repositories.get_run(run_id, g.user["id"])
    if not run:
        return fail("NOT_FOUND", "Run not found", status=404)
    return ok(repositories.list_artifacts(run_id))
