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
    models_to_test = body.get("models") or [
        "gemini-3.8-flash",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
    ]
    agent = MultiModelAgent()
    result = agent.run(
        {
            "user_id": g.user["id"],
            "run_id": "benchmark",
            "benchmark_prompt": body.get("prompt") or "Design a resilient backend order processing pipeline with payment tokenization and SQL injection protections.",
            "comparison_models": models_to_test,
            "demo_mode": body.get("demo_mode", False),
            "user_idea": body.get("idea") or "order processing",
        }
    )
    return ok(result)
