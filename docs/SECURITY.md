# Security Architecture & Safe Execution Sandbox

## 1. Safe Code Execution Sandbox

When executing tests or validating generated Python modules, untrusted AI-generated code must never run with system-level privileges or environment access.

SDLC Nexus implements a multi-layer **Safe Code Execution Sandbox** (`backend/tools/code_execution.py` & `test_execution.py`):

1. **Isolated Ephemeral Working Directory**: Each run operates within a sanitized temporary directory created via `tempfile.TemporaryDirectory`.
2. **Environment Sanitization**: Sensitive environment variables (`GROQ_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, `.env`) are scrubbed from the subprocess execution context.
3. **Execution Timeout**: Subprocesses are bounded by strict timeouts (default 15 seconds) to prevent infinite loops or denial-of-service hanging.
4. **Command Restrictions**: Shell execution (`shell=True`) is prohibited; commands are executed via parameterized arguments with stdout/stderr capture.
5. **Automatic Cleanup**: Temporary directories and transient artifacts are purged upon completion.

```python
# backend/tools/code_execution.py
def execute_code_safely(files: list[dict[str, str]], entrypoint: str) -> ExecutionResult:
    with tempfile.TemporaryDirectory(prefix="sdlc_sandbox_") as tmp_dir:
        # Write files into sandbox
        for f in files:
            safe_write(tmp_dir, f["path"], f["content"])
        
        # Scrub credentials from subprocess environment
        sanitized_env = {k: v for k, v in os.environ.items() if not is_sensitive(k)}
        
        # Execute with timeout
        proc = subprocess.run(
            [sys.executable, entrypoint],
            cwd=tmp_dir,
            env=sanitized_env,
            capture_output=True,
            timeout=settings.code_execution_timeout_seconds,
            text=True
        )
        return ExecutionResult(stdout=proc.stdout, stderr=proc.stderr, exit_code=proc.returncode)
```

## 2. Dual-Layer Security Scanner

Security analysis combines:
1. **Deterministic Static Analysis**: High-confidence regex patterns scanning for SQL injection sinks, hardcoded credentials, dangerous deserialization (`pickle.loads`), command injection (`eval`, `os.system`), and weak cryptographic hashing.
2. **LLM Semantic Threat Assessment**: Analyzes contextual data flow, authorization boundaries, and produces targeted developer remediation instructions.

## 3. Certified Security Product Disclaimer

> [!IMPORTANT]
> The security scanning utilities and LLM analysis in SDLC Nexus are designed for developmental feedback, iterative developer rework, and early defect prevention. They do not constitute a certified enterprise vulnerability assessment or replace accredited manual penetration testing.
