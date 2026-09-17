from __future__ import annotations

import re
from dataclasses import dataclass

ALLOWED_DIAGRAMS = {"flowchart", "graph", "sequencediagram", "erdiagram", "classdiagram", "statediagram", "mindmap"}


@dataclass
class MermaidValidation:
    valid: bool
    error: str | None = None


def validate_mermaid(code: str) -> MermaidValidation:
    stripped = code.strip()
    if not stripped:
        return MermaidValidation(False, "Empty diagram")
    first = stripped.splitlines()[0].strip().lower().replace(" ", "")
    if not any(first.startswith(kind) for kind in ALLOWED_DIAGRAMS):
        return MermaidValidation(False, f"Unsupported or missing diagram header: {stripped.splitlines()[0]}")
    if stripped.count("```") >= 1:
        return MermaidValidation(False, "Mermaid code should not include markdown fences")
    if re.search(r"[<>]{3,}", stripped):
        return MermaidValidation(False, "Suspicious syntax")
    return MermaidValidation(True)
