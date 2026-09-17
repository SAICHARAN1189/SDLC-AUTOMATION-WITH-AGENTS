from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from backend.config.settings import settings
from backend.tools.file_tools import write_files

DANGEROUS_TOKENS = (
    "rm -rf",
    "del /",
    "format ",
    "mkfs",
    "shutdown",
    ":(){",
    "os.system",
    "subprocess",
    "socket",
    "requests.",
    "http.client",
    "urllib",
    "open('/",
    "C:\\Windows",
    "/etc/passwd",
)


@dataclass
class ExecutionResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False
    blocked: bool = False


def is_dangerous(source: str) -> bool:
    lowered = source.lower()
    return any(token.lower() in lowered for token in DANGEROUS_TOKENS)


def run_python_files(files: list[dict[str, str]], entry: str | None = None, timeout: int | None = None) -> ExecutionResult:
    timeout = timeout or settings.code_execution_timeout_seconds
    with tempfile.TemporaryDirectory(prefix="sdlc-nexus-") as tmp:
        root = Path(tmp)
        write_files(root, files)
        if entry is None:
            py_files = [item["path"] for item in files if item["path"].endswith(".py") and "test" not in item["path"]]
            entry = py_files[0] if py_files else None
        if not entry:
            return ExecutionResult(False, "", "No entry file", 1)
        source = (root / entry).read_text(encoding="utf-8")
        if is_dangerous(source):
            return ExecutionResult(False, "", "Blocked potentially dangerous code", 1, blocked=True)
        env = os.environ.copy()
        for key in ("GROQ_API_KEY", "SUPABASE_SERVICE_ROLE_KEY", "DATABASE_URL", "SUPABASE_ANON_KEY"):
            env.pop(key, None)
        env["PYTHONPATH"] = str(root)
        try:
            completed = subprocess.run(
                [sys.executable, entry],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                check=False,
            )
            return ExecutionResult(
                ok=completed.returncode == 0,
                stdout=completed.stdout[-8000:],
                stderr=completed.stderr[-8000:],
                returncode=completed.returncode,
            )
        except subprocess.TimeoutExpired as exc:
            return ExecutionResult(
                False,
                (exc.stdout or "")[-8000:] if isinstance(exc.stdout, str) else "",
                "TIMEOUT_ERROR: execution exceeded limit",
                124,
                timed_out=True,
            )
