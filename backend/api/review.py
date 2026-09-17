from flask import Blueprint, g

from backend.api.auth import require_auth
from backend.api.responses import fail, ok
from backend.persistence import repositories

review_bp = Blueprint("review", __name__)


@review_bp.get("/api/review/<run_id>")
@require_auth
def get_review(run_id: str):
    run = repositories.get_run(run_id, g.user["id"])
    if not run:
        return fail("NOT_FOUND", "Run not found", status=404)
    return ok(repositories.latest_review_result(run_id))
