from flask import Blueprint, g

from backend.api.auth import require_auth
from backend.api.responses import ok
from backend.config.settings import settings
from backend.llm.groq_client import groq_client
from backend.persistence.database import database_available
from backend.persistence import repositories

health_bp = Blueprint("health", __name__)


@health_bp.get("/api/health")
def health():
    db = "ok" if database_available() else ("demo-memory" if settings.demo_mode else "error")
    llm = "ok" if groq_client.available else ("demo" if settings.demo_mode else "error")
    status = "ok" if db != "error" else "degraded"
    return ok({"status": status, "database": db, "llm": llm, "demo_mode": settings.demo_mode})


@health_bp.get("/api/metrics")
@require_auth
def metrics():
    return ok(repositories.dashboard_metrics(g.user["id"]))


@health_bp.get("/api/status")
def service_status():
    return ok(
        {
            "backend": "ok",
            "database": "ok" if database_available() else "demo-memory",
            "groq": "ok" if groq_client.available else "demo",
            "workflow": "ok",
            "demo_mode": settings.demo_mode,
        }
    )
