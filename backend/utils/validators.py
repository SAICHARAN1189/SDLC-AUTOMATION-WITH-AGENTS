from __future__ import annotations

import json
import re
from typing import Any, Type

from pydantic import BaseModel, ValidationError

from backend.models.schemas import ErrorCategory


JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> Any:
    text = text.strip()
    fenced = JSON_FENCE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def parse_model(text: str, model: Type[BaseModel]) -> BaseModel:
    data = extract_json(text)
    return model.model_validate(data)


def validation_error_payload(exc: ValidationError) -> dict[str, Any]:
    return {
        "category": ErrorCategory.VALIDATION_ERROR.value,
        "errors": exc.errors(),
    }
