from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import Flask, send_from_directory
from flask_cors import CORS

from backend.api.agents import agents_bp
from backend.api.artifacts import artifacts_bp
from backend.api.health import health_bp
from backend.api.models import models_bp
from backend.api.projects import projects_bp
from backend.api.qa import qa_bp
from backend.api.responses import fail
from backend.api.review import review_bp
from backend.api.runner import runner_bp
from backend.api.runs import runs_bp
from backend.api.security import security_bp
from backend.api.sse import sse_bp
from backend.config.settings import settings
from backend.persistence.database import (
    DatabaseConfigurationError,
    DatabaseConnectionError,
    check_database_health,
    init_db,
)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.secret_key
    origins = settings.cors_origin_list
    CORS(app, origins=origins, supports_credentials=True)

    # 1. API Blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(runs_bp)
    app.register_blueprint(sse_bp)
    app.register_blueprint(agents_bp)
    app.register_blueprint(artifacts_bp)
    app.register_blueprint(security_bp)
    app.register_blueprint(qa_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(runner_bp)

    # 2. Top-level Health Check (Render/Cloud Monitoring)
    @app.get("/health")
    def root_health():
        db_healthy, _ = check_database_health()
        return {
            "backend": "healthy",
            "database": "healthy" if db_healthy else "unavailable",
        }

    # 3. Database Exception Handlers
    from sqlalchemy.exc import IntegrityError, OperationalError

    @app.errorhandler(DatabaseConfigurationError)
    def handle_db_config_error(exc):
        return fail("CONFIGURATION_ERROR", str(exc), status=500)

    @app.errorhandler(DatabaseConnectionError)
    def handle_db_conn_error(exc):
        return fail("SERVICE_UNAVAILABLE", f"Database unavailable: {exc}", status=503)

    @app.errorhandler(OperationalError)
    def handle_db_operational_error(exc):
        return fail("SERVICE_UNAVAILABLE", "Database connection failed or timed out", status=503)

    @app.errorhandler(IntegrityError)
    def handle_db_integrity_error(exc):
        return fail("CONSTRAINT_VIOLATION", "Database constraint violation", status=400)

    # 4. Frontend Static & Client-Side SPA Routing
    FRONTEND_DIST = ROOT / "frontend" / "dist"

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path: str):
        # Never catch missing API routes or health endpoints with HTML
        if path.startswith("api") or path == "health" or path.startswith("health/"):
            return fail("NOT_FOUND", f"API route /{path} not found", status=404)

        if FRONTEND_DIST.is_dir():
            target_file = FRONTEND_DIST / path
            if path and target_file.is_file():
                return send_from_directory(str(FRONTEND_DIST), path)
            index_file = FRONTEND_DIST / "index.html"
            if index_file.is_file():
                return send_from_directory(str(FRONTEND_DIST), "index.html")

        # Fallback for standalone backend development
        return {
            "status": "online",
            "service": "SDLC Nexus Autonomous Multi-Agent Platform API",
            "version": "2.0.0",
            "health_check": "/api/health",
            "notice": "Frontend build not detected in frontend/dist. Run 'npm run build' in frontend/ to generate it.",
        }

    init_db()
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=not settings.is_production, threaded=True)
