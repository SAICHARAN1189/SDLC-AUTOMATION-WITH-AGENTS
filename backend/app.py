from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import Flask
from flask_cors import CORS

from backend.api.agents import agents_bp
from backend.api.artifacts import artifacts_bp
from backend.api.health import health_bp
from backend.api.models import models_bp
from backend.api.projects import projects_bp
from backend.api.qa import qa_bp
from backend.api.review import review_bp
from backend.api.runs import runs_bp
from backend.api.security import security_bp
from backend.api.sse import sse_bp
from backend.config.settings import settings
from backend.persistence.database import init_db


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.secret_key
    origins = settings.cors_origin_list
    CORS(app, origins=origins, supports_credentials=True)
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

    @app.get("/")
    def index():
        return {
            "status": "online",
            "service": "SDLC Nexus Autonomous Multi-Agent Platform API",
            "version": "2.0.0",
            "frontend_url": "http://localhost:5173",
            "health_check": "/api/health",
        }

    from backend.api.responses import fail
    from backend.persistence.database import DatabaseConfigurationError, DatabaseConnectionError, check_database_health
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

    @app.get("/health")
    def root_health():
        db_healthy, _ = check_database_health()
        return {
            "backend": "healthy",
            "database": "healthy" if db_healthy else "unavailable",
        }

    init_db()
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=not settings.is_production, threaded=True)
