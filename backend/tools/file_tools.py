from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable

from backend.utils.validators import clean_code_content

SAFE_ROOT_NAME = "generated_workspace"


class UnsafePathError(ValueError):
    pass


def resolve_safe_path(root: Path, relative: str) -> Path:
    if os.path.isabs(relative) or ".." in Path(relative).parts:
        raise UnsafePathError(f"Unsafe path: {relative}")
    target = (root / relative).resolve()
    root_resolved = root.resolve()
    if root_resolved not in target.parents and target != root_resolved:
        raise UnsafePathError(f"Path escapes workspace: {relative}")
    return target


def list_structure(root: Path) -> list[str]:
    if not root.exists():
        return []
    items: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            items.append(str(path.relative_to(root)).replace("\\", "/"))
    return items


def read_file(root: Path, relative: str) -> str:
    path = resolve_safe_path(root, relative)
    return path.read_text(encoding="utf-8")


def write_file(root: Path, relative: str, content: str) -> str:
    path = resolve_safe_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = clean_code_content(content, relative)
    path.write_text(cleaned, encoding="utf-8")
    return str(path.relative_to(root)).replace("\\", "/")


def write_files(root: Path, files: Iterable[dict[str, str]]) -> list[str]:
    written: list[str] = []
    for item in files:
        written.append(write_file(root, item["path"], item["content"]))
    return written
