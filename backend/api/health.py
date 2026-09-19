from flask import Blueprint, g

from backend.api.auth import require_auth
from backend.api.responses import ok
from backend.config.settings import settings
from backend.llm import gemini_client, groq_client, provider
from backend.models.schemas import utc_now
from backend.persistence.database import check_database_health
from backend.persistence import repositories

health_bp = Blueprint("health", __name__)


@health_bp.get("/api/health")
@health_bp.get("/health")
def health():
    db_healthy, db_msg = check_database_health()
    db_status = "healthy" if db_healthy else "unavailable"
    llm_status = "healthy" if provider.available else "needs-api-key"
    backend_status = "healthy"
    return ok({
        "status": "healthy" if db_healthy else "degraded",
        "backend": backend_status,
        "database": db_status,
        "llm": llm_status,
        "workflow": "healthy",
        "timestamp": utc_now().isoformat(),
        "provider": settings.llm_provider,
        "gemini_available": gemini_client.available,
        "groq_available": groq_client.available,
        "demo_mode": settings.demo_mode,
    })


@health_bp.get("/api/metrics")
@require_auth
def metrics():
    return ok(repositories.dashboard_metrics(g.user["id"]))


@health_bp.get("/api/status")
def service_status():
    db_healthy, _ = check_database_health()
    return ok(
        {
            "backend": "healthy",
            "database": "healthy" if db_healthy else "unavailable",
            "provider": settings.llm_provider,
            "gemini": "healthy" if gemini_client.available else "not-configured",
            "groq": "healthy" if groq_client.available else "not-configured",
            "workflow": "healthy",
            "demo_mode": settings.demo_mode,
        }
    )

