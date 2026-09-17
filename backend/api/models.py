from flask import Blueprint, g, request

from backend.api.auth import require_auth
from backend.api.responses import fail, ok
from backend.agents.multi_model_agent import MultiModelAgent
from backend.persistence import repositories

models_bp = Blueprint("models", __name__)


@models_bp.get("/api/models/<run_id>")
@require_auth
def get_models(run_id: str):
    run = repositories.get_run(run_id, g.user["id"])
    if not run:
        return fail("NOT_FOUND", "Run not found", status=404)
    return ok(repositories.list_model_comparisons(run_id))


@models_bp.post("/api/models/benchmark")
@require_auth
def benchmark():
    body = request.get_json(silent=True) or {}
    agent = MultiModelAgent()
    result = agent.run(
        {
            "user_id": g.user["id"],
            "run_id": "benchmark",
            "benchmark_prompt": body.get("prompt") or "Sketch a secure checkout service",
            "comparison_models": body.get("models"),
            "demo_mode": body.get("demo_mode", True),
            "user_idea": body.get("idea") or "secure checkout",
        }
    )
    return ok(result)
