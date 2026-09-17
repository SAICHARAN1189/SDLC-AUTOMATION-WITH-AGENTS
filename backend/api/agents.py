from __future__ import annotations

from flask import Blueprint, g, request

from backend.agents import AGENT_REGISTRY, serialize_agents
from backend.api.auth import require_auth
from backend.api.responses import fail, ok

agents_bp = Blueprint("agents", __name__)


@agents_bp.get("/api/agents")
@require_auth
def list_agents():
    return ok(serialize_agents())


@agents_bp.get("/api/agents/<agent>")
@require_auth
def get_agent(agent: str):
    instance = AGENT_REGISTRY.get(agent)
    if not instance:
        return fail("NOT_FOUND", "Unknown agent", status=404)
    return ok(instance.identity.model_dump(mode="json"))


@agents_bp.post("/api/agents/<agent>/run")
@require_auth
def run_agent(agent: str):
    instance = AGENT_REGISTRY.get(agent)
    if not instance:
        return fail("NOT_FOUND", "Unknown agent", status=404)
    body = request.get_json(silent=True) or {}
    body.setdefault("user_id", g.user["id"])
    body.setdefault("run_id", body.get("run_id") or "ad-hoc")
    body.setdefault("project_id", body.get("project_id") or "ad-hoc")
    try:
        result = instance.run(body)
        return ok(result)
    except Exception as exc:
        return fail("AGENT_ERROR", str(exc), status=500)
