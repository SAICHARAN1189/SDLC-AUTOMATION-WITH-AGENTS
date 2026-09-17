from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from backend.config.settings import settings
from backend.tools.file_tools import write_files


@dataclass
class TestRunResult:
    executed: bool
    total: int
    passed: int
    failed: int
    skipped: int
    duration: float
    stdout: str
    stderr: str
    failures: list[dict[str, str]]
    blocked: bool = False


def run_pytest(files: list[dict[str, str]], extra_files: list[dict[str, str]] | None = None) -> TestRunResult:
    with tempfile.TemporaryDirectory(prefix="sdlc-nexus-qa-") as tmp:
        root = Path(tmp)
        write_files(root, (extra_files or []) + files)
        env = os.environ.copy()
        for key in ("GROQ_API_KEY", "SUPABASE_SERVICE_ROLE_KEY", "DATABASE_URL", "SUPABASE_ANON_KEY"):
            env.pop(key, None)
        env["PYTHONPATH"] = str(root)
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "--tb=short"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=settings.code_execution_timeout_seconds,
                env=env,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return TestRunResult(
                executed=False,
                total=0,
                passed=0,
                failed=0,
                skipped=0,
                duration=float(settings.code_execution_timeout_seconds),
                stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
                stderr="TIMEOUT_ERROR",
                failures=[{"test_name": "suite", "stack_trace": "timed out"}],
            )
        return parse_pytest_output(completed.stdout, completed.stderr, completed.returncode)


def parse_pytest_output(stdout: str, stderr: str, returncode: int) -> TestRunResult:
    total = passed = failed = skipped = 0
    failures: list[dict[str, str]] = []
    summary_line = ""
    for line in (stdout + "\n" + stderr).splitlines():
        if "failed" in line or "passed" in line or "skipped" in line:
            if "passed" in line or "failed" in line:
                summary_line = line
        if line.startswith("FAILED "):
            failures.append({"test_name": line.replace("FAILED ", "").strip(), "stack_trace": line})
    import re

    passed_m = re.search(r"(\d+) passed", summary_line)
    failed_m = re.search(r"(\d+) failed", summary_line)
    skipped_m = re.search(r"(\d+) skipped", summary_line)
    passed = int(passed_m.group(1)) if passed_m else 0
    failed = int(failed_m.group(1)) if failed_m else 0
    skipped = int(skipped_m.group(1)) if skipped_m else 0
    total = passed + failed + skipped
    duration_m = re.search(r"in ([0-9.]+)s", summary_line)
    duration = float(duration_m.group(1)) if duration_m else 0.0
    if total == 0 and returncode != 0:
        failed = 1
        total = 1
        failures.append({"test_name": "collection", "stack_trace": stderr or stdout})
    return TestRunResult(
        executed=True,
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        duration=duration,
        stdout=stdout[-8000:],
        stderr=stderr[-8000:],
        failures=failures,
    )
