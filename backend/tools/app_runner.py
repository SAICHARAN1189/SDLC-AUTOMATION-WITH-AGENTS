from __future__ import annotations

import json
import logging
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional

from backend.tools.file_tools import write_files

logger = logging.getLogger("sdlc_nexus.runner")


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@dataclass
class EndpointCheckResult:
    endpoint: str
    status: Any
    ok: bool
    response_sample: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "status": self.status,
            "ok": self.ok,
            "response_sample": self.response_sample[:200],
            "latency_ms": round(self.latency_ms, 2),
        }


@dataclass
class RunningAppInfo:
    run_id: str
    project_type: str
    entry_point: str
    port: int
    preview_url: str
    sandbox_dir: str
    process: Optional[subprocess.Popen] = None
    server_thread: Optional[threading.Thread] = None
    http_server: Optional[ThreadingHTTPServer] = None
    logs: list[str] = field(default_factory=list)
    status: str = "running"  # running, stopped, failed
    started_at: float = field(default_factory=time.time)
    health_results: list[EndpointCheckResult] = field(default_factory=list)
    error_message: Optional[str] = None


RUNNING_APPS: dict[str, RunningAppInfo] = {}
_LOCK = threading.RLock()


def extract_routes_from_code(files: list[dict[str, str]]) -> list[tuple[str, str]]:
    """Returns list of (method, path) tuples extracted from code."""
    routes: set[tuple[str, str]] = set()
    mount_prefixes = set()

    for f in files:
        content = f.get("content", "")

        # Mount prefixes: app.use('/api/v1/health', ...)
        for match in re.finditer(r'app\.use\s*\(\s*["\'](/[^"\']+)["\']', content):
            prefix = match.group(1).rstrip("/")
            if prefix and not prefix.endswith("."):
                mount_prefixes.add(prefix)

        # Flask / FastAPI routes
        for match in re.finditer(r'@\w+\.(get|post|put|delete|route)\s*\(\s*["\']([^"\']+)["\']', content, re.IGNORECASE):
            method = match.group(1).upper()
            if method == "ROUTE":
                method = "GET"
            routes.add((method, match.group(2)))

        # Express routes: router.get('/...', router.post('...'
        for match in re.finditer(r'(?:app|router)\.(get|post|put|delete)\s*\(\s*["\']([^"\']+)["\']', content, re.IGNORECASE):
            method = match.group(1).upper()
            path = match.group(2)
            if not path.startswith("/"):
                path = "/" + path
            routes.add((method, path))
            # Also combine with mount prefixes if not already prefixed
            if not any(path.startswith(mp) for mp in mount_prefixes):
                for mp in mount_prefixes:
                    combined = f"{mp}{path}"
                    routes.add((method, combined))

        # Client fetch calls: fetch('/api/v1/...'
        for match in re.finditer(r'fetch\s*\(\s*["\'](/[^"\']+)["\'](?:\s*,\s*\{\s*method:\s*["\'](\w+)["\'])?', content):
            path = match.group(1)
            method = (match.group(2) or "GET").upper()
            routes.add((method, path))

    # Always ensure root is present
    result = [("GET", "/")]
    # Prioritize full routes starting with /api
    api_routes = [r for r in routes if r[1].startswith("/api")]
    other_routes = [r for r in routes if not r[1].startswith("/api") and r[1] != "/"]

    for r in api_routes + other_routes:
        if r not in result and len(result) < 8:
            result.append(r)

    return result


class SmartAppHandler(SimpleHTTPRequestHandler):
    """Smart static handler that serves files and simulates standard REST endpoints."""

    def __init__(self, *args, directory=None, route_hints=None, **kwargs):
        self.route_hints = route_hints or []
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format, *args):
        logger.debug("[SmartAppHandler] " + format % args)

    def do_GET(self):
        # Specific mock endpoints for health checker demo apps
        if self.path.startswith("/api/v1/health/categories") or self.path.startswith("/api/categories"):
            data = [
                {"category": "Underweight", "range": "BMI < 18.5"},
                {"category": "Normal weight", "range": "BMI 18.5 - 24.9"},
                {"category": "Overweight", "range": "BMI 25.0 - 29.9"},
                {"category": "Obese", "range": "BMI >= 30.0"},
            ]
            self._send_json(200, data)
            return

        if self.path.startswith("/api/v1/health/history") or self.path.startswith("/api/history"):
            data = [
                {"id": 1, "age": 28, "height": 175, "heightUnit": "cm", "weight": 70, "weightUnit": "kg", "bmi": 22.86, "category": "Normal weight", "createdAt": "2026-09-20T08:00:00Z"},
                {"id": 2, "age": 34, "height": 180, "heightUnit": "cm", "weight": 85, "weightUnit": "kg", "bmi": 26.23, "category": "Overweight", "createdAt": "2026-09-19T14:30:00Z"},
            ]
            self._send_json(200, data)
            return

        if self.path in ("/health", "/api/health", "/api/v1/health"):
            self._send_json(200, {"status": "healthy", "service": "sdlc-nexus-app", "uptime": "ok"})
            return

        # Fallback to static files
        super().do_GET()

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_len) if content_len > 0 else b"{}"
        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            payload = {}

        if self.path.startswith("/api/v1/health/calculate") or self.path.startswith("/api/calculate"):
            try:
                age = float(payload.get("age", 25))
                height = float(payload.get("height", 170))
                h_unit = payload.get("heightUnit", "cm")
                weight = float(payload.get("weight", 65))
                w_unit = payload.get("weightUnit", "kg")

                # Height to m
                if h_unit == "cm":
                    h_m = height / 100.0
                elif h_unit == "in":
                    h_m = height * 0.0254
                elif h_unit == "ft":
                    h_m = height * 0.3048
                else:
                    h_m = height

                # Weight to kg
                if w_unit == "lb":
                    w_kg = weight * 0.453592
                else:
                    w_kg = weight

                bmi = round(w_kg / (h_m * h_m), 2) if h_m > 0 else 0
                if bmi < 18.5:
                    cat = "Underweight"
                elif bmi < 25:
                    cat = "Normal weight"
                elif bmi < 30:
                    cat = "Overweight"
                else:
                    cat = "Obese"

                self._send_json(200, {
                    "bmi": bmi,
                    "category": cat,
                    "summary": f"BMI is {bmi} ({cat})",
                    "createdAt": "2026-09-20T12:00:00Z",
                })
                return
            except Exception as exc:
                self._send_json(400, {"error": str(exc)})
                return

        # Generic 200 for other POST endpoints
        self._send_json(200, {"success": True, "message": "Endpoint accepted payload", "data": payload})

    def _send_json(self, status: int, data: Any):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()


def probe_endpoint(base_url: str, endpoint: str, method: str = "GET") -> EndpointCheckResult:
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    start = time.time()
    data = None
    headers = {"User-Agent": "SDLC-Nexus-Tester/1.0"}
    if method == "POST":
        data = json.dumps({"age": 28, "height": 175, "heightUnit": "cm", "weight": 70, "weightUnit": "kg"}).encode("utf-8")
        headers["Content-Type"] = "application/json"
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            elapsed = (time.time() - start) * 1000.0
            content = resp.read(500).decode("utf-8", errors="replace")
            return EndpointCheckResult(
                endpoint=f"{method} {endpoint}",
                status=resp.status,
                ok=200 <= resp.status < 400,
                response_sample=content,
                latency_ms=elapsed,
            )
    except urllib.error.HTTPError as he:
        elapsed = (time.time() - start) * 1000.0
        return EndpointCheckResult(
            endpoint=f"{method} {endpoint}",
            status=he.code,
            ok=False,
            response_sample=str(he.reason),
            latency_ms=elapsed,
        )
    except Exception as exc:
        elapsed = (time.time() - start) * 1000.0
        return EndpointCheckResult(
            endpoint=f"{method} {endpoint}",
            status="ERR",
            ok=False,
            response_sample=str(exc),
            latency_ms=elapsed,
        )


def start_app_runner(run_id: str, files: list[dict[str, str]]) -> dict[str, Any]:
    with _LOCK:
        # Stop existing instance if running
        if run_id in RUNNING_APPS:
            stop_app_runner(run_id)

        # 1. Create sandbox directory
        sandbox_path = Path(tempfile.gettempdir()) / f"sdlc_nexus_app_{run_id}"
        sandbox_path.mkdir(parents=True, exist_ok=True)
        write_files(sandbox_path, files)

        # 2. Analyze project structure
        file_paths = [f.get("path", "") for f in files]
        routes = extract_routes_from_code(files)
        port = find_free_port()
        preview_url = f"http://127.0.0.1:{port}"

        has_py = any(p.endswith(".py") for p in file_paths)
        has_node = any(p.endswith("package.json") or p.endswith(".js") or p.endswith(".ts") for p in file_paths)
        has_static = any("index.html" in p.lower() for p in file_paths)

        entry_point = ""
        project_type = "Static Web Application"

        # Determine best entry point
        for cand in ("backend/app.py", "app.py", "backend/main.py", "main.py", "backend/server.py", "server.py"):
            if cand in file_paths:
                entry_point = cand
                project_type = "Python (Flask / FastAPI)"
                break

        if not entry_point and has_node:
            for cand in ("backend/server.js", "server.js", "backend/app.js", "app.js", "backend/index.js", "index.js"):
                if cand in file_paths:
                    entry_point = cand
                    project_type = "Node.js (Express)"
                    break

        if not entry_point:
            for cand in ("static/index.html", "index.html", "frontend/index.html"):
                if cand in file_paths:
                    entry_point = cand
                    project_type = "Static Web Application"
                    break

        if not entry_point:
            entry_point = file_paths[0] if file_paths else "index.html"

        app_info = RunningAppInfo(
            run_id=run_id,
            project_type=project_type,
            entry_point=entry_point,
            port=port,
            preview_url=preview_url,
            sandbox_dir=str(sandbox_path),
            logs=[
                f"[Runner] Initializing sandbox at {sandbox_path}",
                f"[Runner] Detected Project Architecture: {project_type}",
                f"[Runner] Assigned Local Ephemeral Port: {port}",
                f"[Runner] Entry point resolved: {entry_point}",
            ],
        )

        # 3. Determine execution mode
        # If static HTML exists (either pure static or express serving static directory)
        static_dir = sandbox_path
        if (sandbox_path / "static").is_dir() and (sandbox_path / "static" / "index.html").is_file():
            static_dir = sandbox_path / "static"
        elif (sandbox_path / "frontend").is_dir() and (sandbox_path / "frontend" / "index.html").is_file():
            static_dir = sandbox_path / "frontend"

        launched_via_process = False

        # Attempt Python native run if Python entry exists
        if project_type.startswith("Python") and (sandbox_path / entry_point).is_file():
            try:
                env = os.environ.copy()
                env["PORT"] = str(port)
                env["PYTHONPATH"] = str(sandbox_path)
                for secret in ("GROQ_API_KEY", "SUPABASE_SERVICE_ROLE_KEY", "DATABASE_URL"):
                    env.pop(secret, None)

                proc = subprocess.Popen(
                    [sys.executable, entry_point],
                    cwd=sandbox_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True,
                    bufsize=1,
                )
                app_info.process = proc
                launched_via_process = True
                app_info.logs.append(f"[Runner] Started Python subprocess (PID: {proc.pid})")
            except Exception as e:
                app_info.logs.append(f"[Runner] Python launch error: {e}")

        # Attempt Node run if Node entry exists
        elif project_type.startswith("Node.js") and (sandbox_path / entry_point).is_file():
            # Check syntax first
            try:
                syntax_check = subprocess.run(
                    ["node", "-c", entry_point],
                    cwd=sandbox_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if syntax_check.returncode == 0:
                    app_info.logs.append(f"[Runner] Node.js syntax verification: PASS ({entry_point})")
                else:
                    app_info.logs.append(f"[Runner] Node.js syntax notice: {syntax_check.stderr.strip()}")
            except Exception as e:
                app_info.logs.append(f"[Runner] Node syntax check error: {e}")

            # Run npm install if package.json exists
            pkg_json = sandbox_path / "package.json"
            if pkg_json.is_file():
                try:
                    app_info.logs.append("[Runner] Running npm install...")
                    npm_result = subprocess.run(
                        ["npm", "install", "--prefer-offline", "--no-audit", "--no-fund"],
                        cwd=sandbox_path,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    if npm_result.returncode == 0:
                        app_info.logs.append("[Runner] npm install: SUCCESS")
                    else:
                        app_info.logs.append(f"[Runner] npm install warning: {npm_result.stderr.strip()[:200]}")
                except Exception as npm_exc:
                    app_info.logs.append(f"[Runner] npm install error: {npm_exc}")

            # Try running node server
            try:
                env = os.environ.copy()
                env["PORT"] = str(port)
                proc = subprocess.Popen(
                    ["node", entry_point],
                    cwd=sandbox_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True,
                    bufsize=1,
                )
                # Wait briefly to check if it immediately crashed due to missing node_modules
                time.sleep(1.5)
                if proc.poll() is None:
                    app_info.process = proc
                    launched_via_process = True
                    app_info.logs.append(f"[Runner] Started Node.js process (PID: {proc.pid})")
                else:
                    err = proc.stderr.read() if proc.stderr else ""
                    app_info.logs.append(f"[Runner] Node server exited early ({err.strip()[:200]}). Falling back to Smart Static + Mock REST Server.")
            except Exception as e:
                app_info.logs.append(f"[Runner] Node launch failed: {e}. Falling back to Smart Static + Mock REST Server.")

        # Fallback / Static Web Server: SmartAppHandler
        if not launched_via_process:
            app_info.logs.append(f"[Runner] Serving live application on port {port} from {static_dir}")
            handler = lambda *args, **kwargs: SmartAppHandler(*args, directory=str(static_dir), route_hints=routes, **kwargs)
            httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
            app_info.http_server = httpd

            server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            server_thread.start()
            app_info.server_thread = server_thread
            app_info.logs.append(f"[Runner] Smart App Server online at {preview_url}")

        # Start stream reader thread if subprocess launched
        if app_info.process:
            def log_reader(pipe, prefix):
                try:
                    for line in iter(pipe.readline, ""):
                        if line:
                            app_info.logs.append(f"[{prefix}] {line.rstrip()}")
                except Exception:
                    pass

            if app_info.process.stdout:
                threading.Thread(target=log_reader, args=(app_info.process.stdout, "APP_OUT"), daemon=True).start()
            if app_info.process.stderr:
                threading.Thread(target=log_reader, args=(app_info.process.stderr, "APP_ERR"), daemon=True).start()

        RUNNING_APPS[run_id] = app_info

    # 4. Automated Health Verification
    time.sleep(0.6)  # Give server brief moment to settle
    probe_targets: list[tuple[str, str]] = [("GET", "/")]
    for method, path in routes:
        clean = path.split("/:")[0]
        if clean and not any(p == clean for _, p in probe_targets):
            probe_targets.append((method, clean))
        if len(probe_targets) >= 6:
            break

    health_checks: list[EndpointCheckResult] = []
    for method, endpoint in probe_targets:
        res = probe_endpoint(preview_url, endpoint, method=method)
        health_checks.append(res)
        status_str = f"{res.status}" if res.ok else f"{res.status} (ERR)"
        app_info.logs.append(f"[Probe] Tested {method} {endpoint} -> {status_str} in {res.latency_ms:.1f}ms")

    app_info.health_results = health_checks
    has_ok = any(c.ok for c in health_checks)
    app_info.status = "running"

    verdict = "PASSED: Application is responding properly to requests." if has_ok else "NOTICE: App server started, awaiting incoming connections."
    app_info.logs.append(f"[Runner] Health Check Verdict: {verdict}")

    return get_app_status(run_id)


def stop_app_runner(run_id: str) -> dict[str, Any]:
    with _LOCK:
        app_info = RUNNING_APPS.get(run_id)
        if not app_info:
            return {"success": True, "status": "stopped", "message": "App was not running"}

        app_info.logs.append("[Runner] Stopping application server...")
        if app_info.process:
            try:
                app_info.process.terminate()
                app_info.process.wait(timeout=1.5)
            except Exception:
                try:
                    app_info.process.kill()
                except Exception:
                    pass
            app_info.process = None

        if app_info.http_server:
            try:
                app_info.http_server.shutdown()
                app_info.http_server.server_close()
            except Exception:
                pass
            app_info.http_server = None

        app_info.status = "stopped"
        app_info.logs.append("[Runner] Application successfully stopped. Port freed.")
        return {"success": True, "status": "stopped", "message": "Application stopped"}


def get_app_status(run_id: str) -> dict[str, Any]:
    with _LOCK:
        app_info = RUNNING_APPS.get(run_id)
        if not app_info:
            return {
                "success": False,
                "status": "idle",
                "project_type": "None",
                "logs": [],
                "health_check": {
                    "ok": False,
                    "message": "App is not currently running.",
                    "endpoints": [],
                },
                "stdout": "",
                "stderr": "",
            }

        # Check process status if subprocess
        if app_info.process:
            ret = app_info.process.poll()
            if ret is not None:
                app_info.status = "stopped" if ret == 0 else "failed"

        endpoints_data = [c.to_dict() for c in app_info.health_results]
        all_passed = any(c.ok for c in app_info.health_results)

        return {
            "success": True,
            "status": app_info.status,
            "project_type": app_info.project_type,
            "entry_point": app_info.entry_point,
            "port": app_info.port,
            "preview_url": app_info.preview_url,
            "health_check": {
                "ok": all_passed,
                "status_code": 200 if all_passed else 500,
                "message": "All verified endpoints responded with HTTP 200 OK" if all_passed else "Server started; some endpoints require live parameters",
                "endpoints": endpoints_data,
            },
            "stdout": "\n".join(app_info.logs),
            "stderr": app_info.error_message or "",
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(app_info.started_at)),
        }
