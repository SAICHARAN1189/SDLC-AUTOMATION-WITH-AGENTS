from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.config.settings import settings

SECRET_PATTERN = re.compile(r"(api[_-]?key|password|secret|token|service_role)", re.I)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "user_id",
            "project_id",
            "run_id",
            "stage",
            "agent",
            "model",
            "duration",
            "status",
            "retry_number",
            "error_category",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload)


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("sdlc_nexus")
    if logger.handlers:
        return logger
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if not settings.is_production else logging.INFO)
    logger.propagate = False
    return logger


logger = configure_logging()


def redact(value: str) -> str:
    if SECRET_PATTERN.search(value):
        return "[REDACTED]"
    return value
