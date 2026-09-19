from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    failures: list[dict[str, Any]]
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
                failures=[{
                    "test": "suite",
                    "test_name": "suite",
                    "expected": "Execution within timeout",
                    "actual": "Timed out",
                    "root_cause": f"Pytest execution timed out after {settings.code_execution_timeout_seconds}s",
                    "affected_files": [],
                    "stack_trace": "timed out",
                }],
            )
        return parse_pytest_output(completed.stdout, completed.stderr, completed.returncode)


def parse_pytest_output(stdout: str, stderr: str, returncode: int) -> TestRunResult:
    total = passed = failed = skipped = 0
    failures: list[dict[str, Any]] = []
    summary_line = ""
    all_output = (stdout + "\n" + stderr).strip()
    lines = all_output.splitlines()

    for line in lines:
        if "passed" in line or "failed" in line or "skipped" in line:
            summary_line = line

    passed_m = re.search(r"(\d+)\s+passed", summary_line)
    failed_m = re.search(r"(\d+)\s+failed", summary_line)
    skipped_m = re.search(r"(\d+)\s+skipped", summary_line)
    passed = int(passed_m.group(1)) if passed_m else 0
    failed = int(failed_m.group(1)) if failed_m else 0
    skipped = int(skipped_m.group(1)) if skipped_m else 0
    total = passed + failed + skipped
    duration_m = re.search(r"in\s+([0-9.]+)\s*s", summary_line)
    duration = float(duration_m.group(1)) if duration_m else 0.0

    # Extract failure/error sections
    failure_blocks: dict[str, list[str]] = {}
    current_section = None
    section_pattern = re.compile(r"^_{3,}\s+(.+?)\s+_{3,}$")

    for line in lines:
        sec_match = section_pattern.match(line)
        if sec_match:
            current_section = sec_match.group(1).strip()
            failure_blocks[current_section] = []
        elif current_section is not None:
            if line.startswith("===") and ("summary" in line or "failed" in line or "passed" in line):
                current_section = None
            else:
                failure_blocks[current_section].append(line)

    # Process FAILED / ERROR summary lines
    for line in lines:
        if line.startswith("FAILED ") or line.startswith("ERROR "):
            prefix = "FAILED " if line.startswith("FAILED ") else "ERROR "
            raw_target = line[len(prefix):].strip()
            test_id = raw_target
            short_msg = ""
            if " - " in raw_target:
                parts = raw_target.split(" - ", 1)
                test_id = parts[0].strip()
                short_msg = parts[1].strip()

            # Find matching block from failure_blocks
            matched_block: list[str] = []
            for sec_name, block_lines in failure_blocks.items():
                clean_sec = sec_name.replace("ERROR collecting ", "").strip()
                if clean_sec in test_id or test_id.endswith(clean_sec) or clean_sec == test_id:
                    matched_block = block_lines
                    break

            stack_trace = "\n".join(matched_block) if matched_block else line
            affected_files: list[str] = []

            # Extract test file from test_id
            test_file = test_id.split("::")[0].strip()
            if test_file and any(test_file.endswith(ext) for ext in (".py", ".js", ".ts", ".html", ".css")):
                affected_files.append(test_file)

            # Find any other file references in the stack trace
            file_ref_pattern = re.compile(r"([\w\./\\-]+\.(?:py|js|ts|html|css)):(\d+)")
            for ref_match in file_ref_pattern.finditer(stack_trace):
                f_path = ref_match.group(1).replace("\\", "/")
                if "sdlc-nexus-qa-" in f_path:
                    parts = f_path.split("sdlc-nexus-qa-", 1)
                    if len(parts) > 1 and "/" in parts[1]:
                        f_path = parts[1].split("/", 1)[1]
                if f_path not in affected_files and not f_path.startswith("venv/"):
                    affected_files.append(f_path)

            expected = None
            actual = None
            root_cause = short_msg or None

            # Parse lines starting with E in matched_block
            e_lines = [l.strip() for l in matched_block if l.strip().startswith("E ") or l.strip().startswith("E:")]
            assert_found = False
            for el in e_lines:
                m = re.search(r"assert\s+(.+?)\s*==\s*(.+)", el)
                if m:
                    actual = m.group(1).strip()
                    expected = m.group(2).strip()
                    root_cause = f"Assertion failed: expected '{expected}', but got '{actual}'"
                    assert_found = True
                    break

            if not assert_found:
                for el in e_lines:
                    exc_m = re.search(r"([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))(?::\s*(.*))?", el)
                    if exc_m:
                        err_type = exc_m.group(1)
                        err_detail = exc_m.group(2) or ""
                        root_cause = f"{err_type}: {err_detail}" if err_detail else err_type
                        expected = "Successful execution without exception"
                        actual = f"Raised {root_cause}"
                        break

            if not root_cause and short_msg:
                root_cause = short_msg
                if "assert" in short_msg:
                    m = re.search(r"assert\s+(.+?)\s*==\s*(.+)", short_msg)
                    if m:
                        actual = m.group(1).strip()
                        expected = m.group(2).strip()
                        root_cause = f"Assertion failed: expected '{expected}', but got '{actual}'"
                elif "Error" in short_msg:
                    expected = "Successful execution without error"
                    actual = short_msg

            # Derive actionable recommended_fix for developer
            rec_fix = None
            if "404" in str(root_cause) or "NotFound" in str(root_cause):
                rec_fix = "Register the requested endpoint route in the backend router with correct HTTP method."
            elif "AssertionError" in str(root_cause) or "Assertion failed" in str(root_cause):
                rec_fix = f"Update logic in {', '.join(affected_files) if affected_files else 'source code'} to satisfy assertion condition."
            elif "ImportError" in str(root_cause) or "ModuleNotFoundError" in str(root_cause):
                rec_fix = "Verify module exists in project files and is listed in requirements.txt."
            elif "ZeroDivisionError" in str(root_cause):
                rec_fix = "Add guard check to avoid division by zero."
            elif "KeyError" in str(root_cause) or "AttributeError" in str(root_cause):
                rec_fix = "Ensure required key/attribute exists or use safe retrieval with default."
            else:
                rec_fix = f"Fix underlying error in {', '.join(affected_files) if affected_files else 'implementation'}."

            failures.append({
                "test": test_id,
                "test_name": test_id,
                "expected": expected or "Expected test condition to be satisfied",
                "actual": actual or (root_cause or "Test failed"),
                "root_cause": root_cause or (short_msg or "Assertion failure or unhandled exception"),
                "affected_files": affected_files,
                "recommended_fix": rec_fix,
                "stack_trace": stack_trace,
            })

    if total == 0 and returncode != 0:
        failed = 1
        total = 1
        trace = stderr or stdout
        err_match = re.search(r"([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception):.+)", trace)
        rc = err_match.group(1) if err_match else "Test collection or execution failed"
        failures.append({
            "test": "collection",
            "test_name": "collection",
            "expected": "Test suite to collect and run without errors",
            "actual": rc,
            "root_cause": rc,
            "affected_files": [],
            "recommended_fix": "Fix syntax or collection errors in project files so pytest can execute tests.",
            "stack_trace": trace[-2000:],
        })

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
