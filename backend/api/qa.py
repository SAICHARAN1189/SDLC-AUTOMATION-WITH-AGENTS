import json
from flask import Blueprint, g

from backend.api.auth import require_auth
from backend.api.responses import fail, ok
from backend.persistence import repositories

qa_bp = Blueprint("qa", __name__)


@qa_bp.get("/api/tests/<run_id>")
@require_auth
def get_tests(run_id: str):
    run = repositories.get_run(run_id, g.user["id"])
    if not run:
        return fail("NOT_FOUND", "Run not found", status=404)
    artifacts = repositories.list_artifacts(run_id)
    test_art = next((a for a in reversed(artifacts) if a.get("artifact_type") == "tests"), None)
    if test_art and test_art.get("content"):
        try:
            return ok(json.loads(test_art["content"]))
        except Exception:
            pass
    res = repositories.latest_test_result(run_id)
    if res and res.get("details"):
        return ok(res["details"])
    return ok(res or {})
