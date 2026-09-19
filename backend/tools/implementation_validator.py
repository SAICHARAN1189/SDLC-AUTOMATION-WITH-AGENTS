from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ValidationIssue:
    check: str
    severity: Literal["BLOCKING", "WARNING"]
    message: str
    affected_files: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "severity": self.severity,
            "message": self.message,
            "affected_files": self.affected_files,
            "details": self.details,
        }


@dataclass
class ImplementationValidationResult:
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    summary: str = ""
    checks_performed: list[str] = field(default_factory=list)

    @property
    def blocking_issues(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "BLOCKING"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "summary": self.summary,
            "issues": [i.to_dict() for i in self.issues],
            "checks_performed": self.checks_performed,
            "blocking_count": len(self.blocking_issues),
            "warning_count": len(self.issues) - len(self.blocking_issues),
        }


def _normalize_route_path(path: str) -> str:
    """Normalize route path variables across Flask and FastAPI syntax to a standard {param}."""
    path = path.strip()
    if not path.startswith("/"):
        path = "/" + path
    # Remove query parameters if present
    if "?" in path:
        path = path.split("?", 1)[0]
    # Remove trailing slash unless root
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    # Flask: <int:id>, <id>, <string:task_id> -> {param}
    path = re.sub(r"<(?:[a-zA-Z_][a-zA-Z0-9_]*:)?([a-zA-Z_][a-zA-Z0-9_]*)>", r"{\1}", path)
    # Express / regex: :id -> {id}
    path = re.sub(r":([a-zA-Z_][a-zA-Z0-9_]*)", r"{\1}", path)
    # Generic normalization for path param comparison
    path = re.sub(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}", "{param}", path)
    return path


def validate_implementation(
    files: list[dict[str, str] | Any],
    architecture: dict[str, Any] | None = None,
    requirements: dict[str, Any] | None = None,
    setup_instructions: list[str] | None = None,
    existing_files: list[dict[str, str] | Any] | None = None,
    mode: str = "INITIAL_IMPLEMENTATION",
) -> ImplementationValidationResult:
    """
    Sanity gate validator that checks the completeness, coherence, and safety of generated code
    before passing to Security and QA.
    """
    issues: list[ValidationIssue] = []
    checks_performed: list[str] = []

    # Map files
    files_map: dict[str, str] = {}
    for f in files:
        path = f.path if hasattr(f, "path") else f.get("path", "")
        content = f.content if hasattr(f, "content") else f.get("content", "")
        if path:
            # Normalize path separators
            norm_path = path.replace("\\", "/").lstrip("./")
            files_map[norm_path] = content

    all_paths = set(files_map.keys())
    arch = architecture or {}
    reqs = requirements or {}
    instructions = setup_instructions or []

    # -------------------------------------------------------------
    # 1. SYNTAX VALIDATION (Python files)
    # -------------------------------------------------------------
    checks_performed.append("syntax_validation")
    parsed_asts: dict[str, ast.AST] = {}
    for path, content in files_map.items():
        if path.endswith(".py"):
            try:
                tree = ast.parse(content, filename=path)
                parsed_asts[path] = tree
            except SyntaxError as e:
                issues.append(
                    ValidationIssue(
                        check="syntax_validation",
                        severity="BLOCKING",
                        message=f"Syntax error in {path} at line {e.lineno}: {e.msg}",
                        affected_files=[path],
                        details={"line": e.lineno, "offset": e.offset, "text": e.text},
                    )
                )

    # -------------------------------------------------------------
    # 2. REQUIRED FILES & PROJECT STRUCTURE
    # -------------------------------------------------------------
    checks_performed.append("required_files")
    has_python_backend = any(p.endswith(".py") for p in all_paths)
    if has_python_backend:
        has_entrypoint = any(
            p in all_paths or p.endswith("/app.py") or p.endswith("/main.py") or p.endswith("/server.py")
            for p in ["app.py", "main.py", "server.py", "backend/app.py", "backend/main.py", "backend/server.py"]
        )
        if not has_entrypoint:
            issues.append(
                ValidationIssue(
                    check="required_files",
                    severity="BLOCKING",
                    message="Missing backend entry point (e.g. app.py or main.py).",
                    affected_files=list(all_paths),
                )
            )

        if "requirements.txt" not in all_paths:
            issues.append(
                ValidationIssue(
                    check="required_files",
                    severity="BLOCKING",
                    message="Missing 'requirements.txt' dependency manifest for Python project.",
                    affected_files=list(all_paths),
                )
            )

    # Check for frontend if web app architecture is indicated
    arch_frontend = str(arch.get("frontend") or "").lower()
    arch_style = str(arch.get("architecture_style") or "").lower()
    is_web_app = (
        "web" in arch_style
        or "fullstack" in arch_style
        or "html" in arch_frontend
        or "react" in arch_frontend
        or "vue" in arch_frontend
        or "vanilla" in arch_frontend
        or any(p.endswith(".html") for p in all_paths)
    )
    if is_web_app and not any(p.endswith(".html") for p in all_paths):
        issues.append(
            ValidationIssue(
                check="required_files",
                severity="BLOCKING",
                message="Web application architecture requires frontend HTML files (e.g. index.html), but none were found.",
                affected_files=list(all_paths),
            )
        )

    # -------------------------------------------------------------
    # 3. REWORK PRESERVATION (Regression Check #8)
    # -------------------------------------------------------------
    checks_performed.append("rework_preservation")
    if mode != "INITIAL_IMPLEMENTATION" and existing_files:
        existing_paths = {
            (f.path if hasattr(f, "path") else f.get("path", "")).replace("\\", "/").lstrip("./")
            for f in existing_files
        }
        existing_paths.discard("")
        dropped_files = existing_paths - all_paths
        if dropped_files:
            issues.append(
                ValidationIssue(
                    check="rework_preservation",
                    severity="BLOCKING",
                    message=(
                        f"Rework dropped {len(dropped_files)} existing project files: {sorted(dropped_files)}. "
                        "Developer must return the complete project files including unchanged files."
                    ),
                    affected_files=sorted(dropped_files),
                )
            )

    # -------------------------------------------------------------
    # 4. INTERNAL IMPORTS & MODULE CONSISTENCY
    # -------------------------------------------------------------
    checks_performed.append("internal_imports")
    # Build known local module names
    local_modules: set[str] = set()
    for p in all_paths:
        if p.endswith(".py"):
            base_no_ext = p[:-3]
            local_modules.add(base_no_ext.replace("/", "."))
            local_modules.add(p.split("/")[-1][:-3])
            # Also package directories with __init__.py
            parts = p.split("/")
            if len(parts) > 1:
                local_modules.add(parts[0])

    for path, tree in parsed_asts.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    # Check relative or local package import
                    mod = node.module
                    first_part = mod.split(".")[0]
                    # If this looks like an internal import within the project
                    if first_part in ("backend", "app", "models", "routes", "database", "services", "api", "utils"):
                        # Verify the target exists
                        mod_as_path = mod.replace(".", "/")
                        matches = any(
                            p == f"{mod_as_path}.py"
                            or p == f"backend/{mod_as_path}.py"
                            or p.startswith(f"{mod_as_path}/")
                            or p.startswith(f"backend/{mod_as_path}/")
                            for p in all_paths
                        )
                        if not matches and first_part in ("models", "database", "routes", "services"):
                            issues.append(
                                ValidationIssue(
                                    check="internal_imports",
                                    severity="BLOCKING",
                                    message=f"{path} imports from '{node.module}', but module file was not found in project.",
                                    affected_files=[path],
                                )
                            )

    # -------------------------------------------------------------
    # 5. FRONTEND / BACKEND CONTRACT (Regression Check #1)
    # -------------------------------------------------------------
    checks_performed.append("frontend_backend_contract")
    backend_routes: dict[str, set[str]] = {}  # normalized_path -> set of HTTP methods

    for path, content in files_map.items():
        if not path.endswith(".py"):
            continue

        # Look for Flask routes: @app.route("/path", methods=["GET", "POST"])
        flask_matches = re.finditer(
            r'@(?:[a-zA-Z0-9_]+\.)?route\(\s*["\']([^"\']+)["\'](?:\s*,\s*methods\s*=\s*\[([^\]]+)\])?',
            content,
        )
        for m in flask_matches:
            r_path = _normalize_route_path(m.group(1))
            methods_raw = m.group(2)
            if methods_raw:
                methods = {x.strip(" '\"").upper() for x in methods_raw.split(",")}
            else:
                methods = {"GET"}
            backend_routes.setdefault(r_path, set()).update(methods)

        # Look for FastAPI / Express-like decorators: @app.get("/path"), @router.post("/path")
        method_decorators = re.finditer(
            r'@(?:[a-zA-Z0-9_]+\.)?(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']',
            content,
            re.IGNORECASE,
        )
        for m in method_decorators:
            method = m.group(1).upper()
            r_path = _normalize_route_path(m.group(2))
            backend_routes.setdefault(r_path, set()).update([method])

    # Extract frontend API calls from HTML, JS, TS files
    frontend_calls: list[tuple[str, str, str]] = []  # (frontend_path, method, path)
    for path, content in files_map.items():
        if path.endswith((".html", ".js", ".ts", ".jsx", ".tsx")):
            # 1. fetch("/api/...", { method: "POST" })
            fetch_matches = re.finditer(
                r'fetch\(\s*[`\'"]([/a-zA-Z0-9_\-?={}:]+)[`\'"](?:\s*,\s*\{([^}]+)\})?',
                content,
                re.DOTALL,
            )
            for m in fetch_matches:
                api_url = m.group(1)
                # Ignore external URLs
                if api_url.startswith("http://") or api_url.startswith("https://"):
                    continue
                options = m.group(2) or ""
                method_m = re.search(r'method\s*:\s*[`\'"](GET|POST|PUT|DELETE|PATCH)[`\'"]', options, re.IGNORECASE)
                method = method_m.group(1).upper() if method_m else "GET"
                frontend_calls.append((path, method, _normalize_route_path(api_url)))

            # 2. axios.get("/api/..."), axios.post(...)
            axios_matches = re.finditer(
                r'axios\.(get|post|put|delete|patch)\(\s*[`\'"]([/a-zA-Z0-9_\-?={}:]+)[`\'"]',
                content,
                re.IGNORECASE,
            )
            for m in axios_matches:
                method = m.group(1).upper()
                api_url = m.group(2)
                if not (api_url.startswith("http://") or api_url.startswith("https://")):
                    frontend_calls.append((path, method, _normalize_route_path(api_url)))

    # Cross-check frontend calls with backend routes if backend routes exist
    if backend_routes:
        for f_path, f_method, f_route in frontend_calls:
            # Skip static asset queries
            if f_route.startswith("/static/") or f_route.endswith((".css", ".js", ".png", ".jpg", ".svg")):
                continue

            # Check exact or normalized match
            matched = False
            for b_route, b_methods in backend_routes.items():
                if b_route == f_route and f_method in b_methods:
                    matched = True
                    break
                # Also handle route prefixes e.g. /api/v1/tasks matching /api/tasks or vice versa
                if b_route == f_route:
                    matched = True
                    if f_method not in b_methods:
                        issues.append(
                            ValidationIssue(
                                check="frontend_backend_contract",
                                severity="BLOCKING",
                                message=(
                                    f"Method mismatch: Frontend ({f_path}) calls {f_method} {f_route}, "
                                    f"but backend route only supports {sorted(b_methods)}."
                                ),
                                affected_files=[f_path],
                                details={"endpoint": f_route, "frontend_method": f_method, "backend_methods": list(b_methods)},
                            )
                        )
                    break

            if not matched:
                issues.append(
                    ValidationIssue(
                        check="frontend_backend_contract",
                        severity="BLOCKING",
                        message=(
                            f"Frontend calls non-existent endpoint: {f_method} {f_route} in {f_path}. "
                            f"Backend does not implement this route."
                        ),
                        affected_files=[f_path],
                        details={"endpoint": f_route, "method": f_method},
                    )
                )

    # -------------------------------------------------------------
    # 6. DATABASE CONSISTENCY & NO SILENT SQLITE (Regression Checks #2, #3, #9)
    # -------------------------------------------------------------
    checks_performed.append("database_consistency")
    arch_db = str(arch.get("database") or "").lower()
    expects_postgres = "postgres" in arch_db or "supabase" in arch_db

    all_py_content = "\n".join(c for p, c in files_map.items() if p.endswith(".py"))

    # Regression #9: Silent SQLite fallback when architecture expects PostgreSQL/Supabase
    if expects_postgres:
        has_sqlite_hardcoded = (
            "sqlite:///" in all_py_content
            and "os.environ" not in all_py_content
            and "os.getenv" not in all_py_content
        ) or re.search(r'sqlite:///(\./)?[a-zA-Z0-9_\-]+\.db', all_py_content)
        if has_sqlite_hardcoded:
            # Check if PostgreSQL connection is handled at all
            if "postgresql" not in all_py_content.lower() and "database_url" not in all_py_content.lower():
                issues.append(
                    ValidationIssue(
                        check="no_silent_sqlite_fallback",
                        severity="BLOCKING",
                        message=(
                            "Architecture specifies PostgreSQL/Supabase, but implementation silently hardcoded "
                            "SQLite ('sqlite:///./app.db') without honoring the architectural specification."
                        ),
                        affected_files=[p for p, c in files_map.items() if "sqlite:///" in c],
                    )
                )

    # Regression #2: Database initialization defined but never executed
    uses_orm = (
        "SQLModel" in all_py_content
        or "Base.metadata.create_all" in all_py_content
        or "db.create_all" in all_py_content
        or "create_all" in all_py_content
    )
    if uses_orm:
        # Check if create_all or init_db is actually called during app execution/startup
        init_db_called = (
            "create_all(" in all_py_content
            or "init_db(" in all_py_content
            or "lifespan" in all_py_content
            or "@app.on_event(\"startup\")" in all_py_content
            or "on_event('startup')" in all_py_content
        )
        if not init_db_called:
            issues.append(
                ValidationIssue(
                    check="database_initialization",
                    severity="BLOCKING",
                    message="Database tables/models are defined, but database initialization (e.g. create_all() / init_db()) is never invoked on application startup.",
                    affected_files=[p for p, c in files_map.items() if "SQLModel" in c or "Base" in c],
                )
            )

    # Regression #3: ORM back_populates relationship incomplete/one-sided
    # Example: Task has Relationship(back_populates="parent"), but SubTask has no parent relationship!
    for path, tree in parsed_asts.items():
        classes_in_file: dict[str, dict[str, str]] = {}  # class_name -> {rel_attr: back_populates_target}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                cls_name = node.name
                classes_in_file[cls_name] = {}
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        attr_name = item.target.id
                        # Check value for Relationship(back_populates="...")
                        if item.value and isinstance(item.value, ast.Call):
                            for kw in item.value.keywords:
                                if kw.arg == "back_populates" and isinstance(kw.value, ast.Constant):
                                    classes_in_file[cls_name][attr_name] = str(kw.value.value)

        # Cross check within all classes found across project
        for cls_name, rels in classes_in_file.items():
            for attr_name, bp_target in rels.items():
                # We need to find if any other class has back_populates=attr_name
                # Let's check across all parsed files
                found_symmetric = False
                for other_path, other_tree in parsed_asts.items():
                    for other_node in ast.walk(other_tree):
                        if isinstance(other_node, ast.ClassDef) and other_node.name != cls_name:
                            for item in other_node.body:
                                if isinstance(item, ast.AnnAssign):
                                    if item.value and isinstance(item.value, ast.Call):
                                        for kw in item.value.keywords:
                                            if kw.arg == "back_populates" and isinstance(kw.value, ast.Constant):
                                                if str(kw.value.value) == attr_name:
                                                    found_symmetric = True
                                                    break
                if not found_symmetric:
                    issues.append(
                        ValidationIssue(
                            check="orm_relationships",
                            severity="BLOCKING",
                            message=(
                                f"Incomplete ORM relationship in {path}: Class '{cls_name}' defines relationship "
                                f"'{attr_name}' with back_populates='{bp_target}', but no corresponding model "
                                f"defines back_populates='{attr_name}'."
                            ),
                            affected_files=[path],
                            details={"class": cls_name, "relationship": attr_name, "back_populates": bp_target},
                        )
                    )

    # -------------------------------------------------------------
    # 7. STATIC FRONTEND SERVED (Regression Check #4)
    # -------------------------------------------------------------
    checks_performed.append("static_frontend_serving")
    has_html = any(p.endswith(".html") for p in all_paths)
    if has_html and has_python_backend:
        serves_static = (
            "StaticFiles" in all_py_content
            or "app.mount(" in all_py_content
            or "render_template(" in all_py_content
            or "send_from_directory(" in all_py_content
            or "send_static_file(" in all_py_content
            or "FileResponse(" in all_py_content
            or "HTMLResponse(" in all_py_content
            or "static_folder" in all_py_content
        )
        if not serves_static:
            issues.append(
                ValidationIssue(
                    check="static_frontend_serving",
                    severity="BLOCKING",
                    message=(
                        "Static frontend (HTML) exists, but backend does not mount or serve static files "
                        "(missing StaticFiles mount, render_template, or send_from_directory)."
                    ),
                    affected_files=[p for p in all_paths if p.endswith(".html")],
                )
            )

    # -------------------------------------------------------------
    # 8. REAL FUNCTIONALITY, NOT FAKE/MOCK (Regression Check #5)
    # -------------------------------------------------------------
    checks_performed.append("real_functionality")
    for path, content in files_map.items():
        if path.endswith(".py"):
            # Check for mock_decompose or functions named mock_* replacing real functionality
            mock_funcs = re.findall(r"def\s+(mock_[a-zA-Z0-9_]+|dummy_[a-zA-Z0-9_]+)\s*\(", content)
            if mock_funcs:
                issues.append(
                    ValidationIssue(
                        check="real_functionality",
                        severity="BLOCKING",
                        message=(
                            f"Fake mock implementation detected in {path}: function(s) {mock_funcs}. "
                            "Required features must be genuinely implemented, not stubbed with mock_* or dummy_*."
                        ),
                        affected_files=[path],
                        details={"mock_functions": mock_funcs},
                    )
                )

            # Check for obvious TODO placeholders in endpoint handlers
            todo_placeholders = re.findall(r"(TODO:?\s*implement\w*|pass\s*#\s*TODO)", content, re.IGNORECASE)
            if todo_placeholders:
                issues.append(
                    ValidationIssue(
                        check="real_functionality",
                        severity="BLOCKING",
                        message=f"Unimplemented TODO placeholders found in {path}: {todo_placeholders}.",
                        affected_files=[path],
                    )
                )

    # -------------------------------------------------------------
    # 9. SECURITY QUALITY (Regression Check #6)
    # -------------------------------------------------------------
    checks_performed.append("security_quality")
    for path, content in files_map.items():
        # Unsafe innerHTML in JavaScript/HTML with user input
        if path.endswith((".js", ".ts", ".html")):
            unsafe_inner_html = re.search(
                r'\.innerHTML\s*=\s*[`\'"].*\$\{[^}]+\}.*[`\'"]|\.innerHTML\s*=\s*[a-zA-Z0-9_.]+(?:title|name|input|val|data|content|text|desc|item)',
                content,
                re.IGNORECASE,
            )
            if unsafe_inner_html:
                issues.append(
                    ValidationIssue(
                        check="security_quality",
                        severity="BLOCKING",
                        message=(
                            f"Unsafe dynamic user content rendered with innerHTML in {path} (XSS risk). "
                            "Use textContent or safe DOM node creation instead of direct innerHTML assignment."
                        ),
                        affected_files=[path],
                    )
                )

        if path.endswith(".py"):
            # Check for eval() or exec()
            if re.search(r'\b(eval|exec)\s*\(', content):
                issues.append(
                    ValidationIssue(
                        check="security_quality",
                        severity="BLOCKING",
                        message=f"Insecure code execution (eval/exec) detected in {path}.",
                        affected_files=[path],
                    )
                )

            # Check for hardcoded secrets
            hardcoded_secrets = re.findall(
                r'["\'](sk-[a-zA-Z0-9]{20,}|AIza[0-9A-Za-z-_]{35}|gsk_[a-zA-Z0-9]{20,})["\']',
                content,
            )
            if hardcoded_secrets:
                issues.append(
                    ValidationIssue(
                        check="security_quality",
                        severity="BLOCKING",
                        message=f"Hardcoded live API key / secret detected in {path}. Use environment variables.",
                        affected_files=[path],
                    )
                )

            # Check for raw SQL string concatenation
            raw_sql_concat = re.search(
                r'\bexecute\s*\(\s*f["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*(?:\{|\%s)',
                content,
                re.IGNORECASE,
            )
            if raw_sql_concat:
                issues.append(
                    ValidationIssue(
                        check="security_quality",
                        severity="BLOCKING",
                        message=f"SQL injection risk: SQL query constructed via string formatting in {path}.",
                        affected_files=[path],
                    )
                )

    # -------------------------------------------------------------
    # 10. DEPENDENCY VALIDATION (Regression Check #7)
    # -------------------------------------------------------------
    checks_performed.append("dependency_validation")
    reqs_content = files_map.get("requirements.txt", "")
    reqs_lower = reqs_content.lower()

    # Check for unjustified selenium
    arch_full_text = str(arch).lower() + " " + str(reqs).lower()
    needs_browser_automation = (
        "selenium" in arch_full_text
        or "browser automation" in arch_full_text
        or "web scraping" in arch_full_text
        or "crawler" in arch_full_text
    )
    if "selenium" in reqs_lower and not needs_browser_automation:
        issues.append(
            ValidationIssue(
                check="dependency_validation",
                severity="BLOCKING",
                message=(
                    "Unjustified 'selenium' dependency found in requirements.txt. "
                    "Do not add selenium unless browser automation is an explicit architectural requirement."
                ),
                affected_files=["requirements.txt"],
            )
        )

    # Check that imported packages are listed in requirements.txt
    py_imports = set()
    for tree in parsed_asts.values():
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    py_imports.add(n.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                py_imports.add(node.module.split(".")[0])

    # Filter out standard library
    stdlib = {
        "os", "sys", "json", "re", "math", "time", "datetime", "typing", "collections",
        "pathlib", "functools", "itertools", "dataclasses", "abc", "tempfile", "shutil",
        "subprocess", "unittest", "logging", "asyncio", "threading", "contextlib", "hashlib",
        "urllib", "uuid", "enum", "io", "csv", "sqlite3", "random", "copy", "traceback",
    }
    local_roots = {p.split("/")[0] for p in all_paths if "/" in p} | {p[:-3] for p in all_paths if p.endswith(".py")}
    third_party_needed = py_imports - stdlib - local_roots - {"backend"}

    common_mapping = {
        "flask": "flask",
        "fastapi": "fastapi",
        "sqlmodel": "sqlmodel",
        "sqlalchemy": "sqlalchemy",
        "pydantic": "pydantic",
        "requests": "requests",
        "uvicorn": "uvicorn",
        "pytest": "pytest",
        "psycopg2": "psycopg2-binary",
        "dotenv": "python-dotenv",
        "jose": "python-jose",
        "jwt": "pyjwt",
    }

    for mod in third_party_needed:
        mapped_pkg = common_mapping.get(mod, mod)
        if mapped_pkg in common_mapping.values():
            if mapped_pkg not in reqs_lower and mod not in reqs_lower:
                issues.append(
                    ValidationIssue(
                        check="dependency_validation",
                        severity="WARNING",
                        message=f"Module '{mod}' is imported in application code but missing from requirements.txt.",
                        affected_files=["requirements.txt"],
                    )
                )

    # -------------------------------------------------------------
    # 11. STARTUP PATH VALIDATION (Regression Check #10)
    # -------------------------------------------------------------
    checks_performed.append("startup_path_validation")
    if instructions:
        instr_joined = " ".join(instructions)
        # If app.py is in backend/app.py, verify instructions don't say 'python app.py'
        if "backend/app.py" in all_paths and "app.py" not in [p for p in all_paths if "/" not in p]:
            if re.search(r'\bpython\s+app\.py\b', instr_joined):
                issues.append(
                    ValidationIssue(
                        check="startup_path_validation",
                        severity="BLOCKING",
                        message=(
                            "Startup instructions specify 'python app.py', but the file is located at "
                            "'backend/app.py'. Use 'python backend/app.py' or provide correct directory navigation."
                        ),
                        affected_files=["backend/app.py"],
                    )
                )

    blocking_count = sum(1 for i in issues if i.severity == "BLOCKING")
    passed = (blocking_count == 0)
    summary = (
        "Implementation passed all sanity checks."
        if passed
        else f"Implementation validation failed with {blocking_count} blocking issue(s) and {len(issues) - blocking_count} warning(s)."
    )

    return ImplementationValidationResult(
        passed=passed,
        issues=issues,
        summary=summary,
        checks_performed=checks_performed,
    )
