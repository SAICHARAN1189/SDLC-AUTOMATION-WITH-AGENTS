from __future__ import annotations

import json
from typing import Any

from backend.agents.base import BaseEngineeringAgent
from backend.agents.demo_data import demo_initial_code, demo_secure_code
from backend.models.schemas import AgentIdentity, AgentName, CodeFile, CodeOutput, DeveloperMode
from backend.tools.file_tools import list_structure
from pathlib import Path
import tempfile


class DeveloperAgent(BaseEngineeringAgent):
    identity = AgentIdentity(
        name=AgentName.DEVELOPER,
        display_name="Developer Agent",
        role="Implement and revise application source from requirements, architecture, and feedback",
        goal="Produce a consistent file set and apply bounded rework from security, QA, and review",
        instructions=(
            "Plan implementation, generate files, and revise existing files using feedback. "
            "Honor architecture. Never embed live credentials."
        ),
        tools=["file_writer", "project_structure_reader"],
        default_model_slot="primary",
    )
    output_model = CodeOutput

    def observe(self, state: dict[str, Any]) -> dict[str, Any]:
        mode = state.get("developer_mode") or DeveloperMode.INITIAL_IMPLEMENTATION.value
        return {
            "user_idea": state.get("user_idea"),
            "requirements": state.get("requirements"),
            "architecture": state.get("architecture"),
            "code": state.get("code"),
            "security_report": state.get("security_report"),
            "test_report": state.get("test_report"),
            "review_report": state.get("review_report"),
            "validation_issues": state.get("validation_issues") or [],
            "developer_mode": mode,
        }

    def demo_output(self, observed: dict[str, Any]) -> CodeOutput:
        mode = observed.get("developer_mode")
        if mode in {
            DeveloperMode.SECURITY_REWORK.value,
            DeveloperMode.QA_REWORK.value,
            DeveloperMode.REVIEW_REWORK.value,
        }:
            output = demo_secure_code()
            output.mode = DeveloperMode(mode)
            output.complete_project_files = list(output.files)
            output.changed_files = [f.path for f in output.files]
            return output
        output = demo_initial_code()
        output.complete_project_files = list(output.files)
        output.changed_files = [f.path for f in output.files]
        return output

    def build_prompt(self, observed: dict[str, Any]) -> tuple[str, str]:
        mode = observed.get("developer_mode") or DeveloperMode.INITIAL_IMPLEMENTATION.value
        arch = observed.get("architecture") or {}
        reqs = observed.get("requirements") or {}
        sec = observed.get("security_report") or {}
        qa = observed.get("test_report") or {}
        rev = observed.get("review_report") or {}
        val_issues = observed.get("validation_issues") or []
        code_data = observed.get("code") or {}

        if mode == DeveloperMode.INITIAL_IMPLEMENTATION.value:
            system = (
                "You are an expert Full-Stack Software Engineer.\n"
                "CRITICAL IMPLEMENTATION CONTRACT:\n"
                "1. INITIAL_IMPLEMENTATION: You MUST generate ALL files required for a COMPLETE, RUNNABLE project.\n"
                "   Include backend files, frontend files (HTML/CSS/JS), package.json / requirements.txt, configuration, and database setup.\n"
                "2. FRONTEND/BACKEND CONTRACT — THIS IS MANDATORY AND WILL BE MACHINE-VALIDATED:\n"
                "   a. Before writing any code, enumerate EVERY fetch() / axios call in your frontend files.\n"
                "   b. For EACH call, ensure the backend has a matching route (same HTTP method, same path).\n"
                "   c. If frontend calls GET /api/v1/calculations — backend MUST have app.get('/api/v1/calculations', ...) or router.get('/calculations') mounted at /api/v1.\n"
                "   d. If frontend calls POST /api/v1/items — backend MUST have the POST route. NO EXCEPTIONS.\n"
                "   e. Missing routes = broken app. An automated validator will flag every unmatched frontend call as a BLOCKING error.\n"
                "3. NODE.JS / EXPRESS SPECIFIC RULES (when using Express):\n"
                "   a. Use express.Router() to group routes. Mount with app.use('/api/v1', router).\n"
                "   b. Every route the frontend calls must appear in the router: router.get('/path', handler), router.post('/path', handler), etc.\n"
                "   c. Always add app.use(express.json()) and CORS headers / cors() middleware before routes.\n"
                "   d. Serve static frontend files: app.use(express.static('static')) and app.get('*', ...) fallback for SPA routing.\n"
                "   e. Listen on process.env.PORT || 3000 and log the port on startup.\n"
                "   f. package.json must list all npm dependencies (express, cors, etc.). Do NOT forget 'start' script: 'node backend/app.js'.\n"
                "4. DATABASE CONSISTENCY & INITIALIZATION:\n"
                "   - If models/tables are defined (SQLModel/SQLAlchemy/Prisma), database initialization MUST be explicitly invoked during startup.\n"
                "   - In ORM relationships, back_populates MUST be symmetric. Never leave one-sided relationships.\n"
                "   - NO SILENT SQLITE FALLBACK: If architecture specifies PostgreSQL/Supabase, honor it via DATABASE_URL env var.\n"
                "5. STATIC FRONTEND SERVING: If a static frontend exists, backend MUST serve it (StaticFiles, send_from_directory, express.static).\n"
                "6. REAL FUNCTIONALITY, NOT FAKE MOCKS: Implement real features. No mock_*() stubs or TODO placeholders.\n"
                "7. SECURITY QUALITY: Avoid eval(), exec(), hardcoded secrets/API keys, SQL string concatenation, unsafe innerHTML.\n"
                "8. DEPENDENCIES & STARTUP: All imported packages must be in requirements.txt / package.json. Setup instructions must match actual file paths.\n"
                "Return ONLY a single valid JSON object strictly matching this schema with no markdown code fence:\n"
                "{\n"
                '  "project_structure": ["backend/app.py", "backend/routes.py", "requirements.txt", "static/index.html", "static/style.css"],\n'
                '  "files": [\n'
                '    {"path": "requirements.txt", "content": "flask\\npydantic\\n"},\n'
                '    {"path": "backend/app.py", "content": "from flask import Flask\\napp = Flask(__name__)\\n"}\n'
                "  ],\n"
                '  "dependencies": ["flask", "pydantic"],\n'
                '  "setup_instructions": ["pip install -r requirements.txt", "python backend/app.py"],\n'
                '  "implementation_notes": "Implemented complete modular architecture.",\n'
                '  "changed_files": ["requirements.txt", "backend/app.py"],\n'
                '  "change_summary": "Initial complete code scaffolding and endpoints"\n'
                "}"
            )
        else:
            system = (
                "You are an expert Full-Stack Software Engineer performing REWORK on an existing codebase.\n"
                "CRITICAL REWORK CONTRACT:\n"
                "1. Analyze the exact QA failures, Security vulnerabilities, and Implementation Validation issues reported.\n"
                "   For QA failures, examine: failing test, expected behavior, actual behavior, affected file, root cause, and recommended fix.\n"
                "2. Modify the EXISTING complete project. Never drop working files.\n"
                "   Any files you return will be merged into the existing project files to maintain the COMPLETE, CONSISTENT project.\n"
                "3. Ensure all frontend API calls match backend routes, database initialization executes, ORM back_populates is symmetric,\n"
                "   and no mock_* stubs or unsafe innerHTML exist.\n"
                "4. DO NOT blindly add dependencies (e.g. do not add selenium unless genuinely required by the architecture).\n"
                "5. Return the updated files. Distinguish 'changed_files' from the complete file set.\n"
                "Return ONLY a single valid JSON object strictly matching the CodeOutput schema."
            )

        # Preserve exact security findings needed for remediation
        sec_findings = [
            {
                "severity": v.get("severity"),
                "category": v.get("category"),
                "description": v.get("description"),
                "evidence": v.get("evidence"),
                "affected_file": v.get("affected_file"),
                "affected_line": v.get("affected_line"),
                "remediation": v.get("remediation"),
            }
            for v in sec.get("vulnerabilities") or []
            if v.get("severity") in ("CRITICAL", "HIGH", "MEDIUM")
        ] if sec else []

        # Preserve exact test failures with root cause, recommended fix, and affected files
        qa_failures = [
            {
                "test": f.get("test") or f.get("test_name"),
                "test_name": f.get("test_name") or f.get("test"),
                "expected": f.get("expected"),
                "actual": f.get("actual"),
                "root_cause": f.get("root_cause"),
                "affected_files": f.get("affected_files") or [],
                "recommended_fix": f.get("recommended_fix"),
                "stack_trace": f.get("stack_trace"),
            }
            for f in qa.get("failures") or []
        ] if qa else []

        compact: dict[str, Any] = {
            "mode": mode,
            "idea": observed.get("user_idea"),
            "project_summary": reqs.get("project_summary"),
            "functional_requirements": reqs.get("functional_requirements") or [],
            "architecture_style": arch.get("architecture_style"),
            "backend_framework": arch.get("backend"),
            "database": arch.get("database"),
            "services": arch.get("services") or [],
            "apis": arch.get("apis") or [],
        }

        # Include existing files if reworking
        raw_existing = code_data.get("files") or []
        existing_files_list = [
            {
                "path": f.path if hasattr(f, "path") else f.get("path"),
                "content": f.content if hasattr(f, "content") else f.get("content", ""),
            }
            for f in raw_existing
            if (hasattr(f, "path") or "path" in f)
        ]
        if existing_files_list:
            compact["existing_files"] = existing_files_list

        if sec_findings:
            compact["security_issues_to_fix"] = sec_findings
        if qa_failures:
            compact["qa_test_failures_to_fix"] = qa_failures
        if val_issues:
            compact["implementation_validation_issues_to_fix"] = val_issues
        if rev.get("blocking_issues") or rev.get("required_changes"):
            compact["review_required_changes"] = {
                "blocking_issues": rev.get("blocking_issues"),
                "required_changes": rev.get("required_changes"),
            }

        return system, json.dumps(compact)

    def use_tools(self, observed: dict[str, Any], draft: CodeOutput | None = None) -> dict[str, Any]:
        if not draft:
            return {}

        mode = observed.get("developer_mode") or DeveloperMode.INITIAL_IMPLEMENTATION.value
        existing_raw = (observed.get("code") or {}).get("files") or []
        existing_map: dict[str, str] = {
            (f.path if hasattr(f, "path") else f["path"]): (f.content if hasattr(f, "content") else f.get("content", ""))
            for f in existing_raw
            if (hasattr(f, "path") or "path" in f)
        }

        draft_files_map = {item.path: item.content for item in draft.files}

        # MERGING CONTRACT:
        # In rework mode, reliably merge changed files into existing project files.
        # Preserve working functionality and never delete existing files inadvertently.
        if mode != DeveloperMode.INITIAL_IMPLEMENTATION.value and existing_map:
            changed: list[str] = []
            for path, content in draft_files_map.items():
                if path not in existing_map or existing_map[path] != content:
                    changed.append(path)
            for path in (draft.changed_files or []):
                if path in draft_files_map and path not in changed:
                    changed.append(path)
            if not changed:
                changed = list(draft_files_map.keys())

            # Start with existing files and overlay modifications
            merged_files_map = dict(existing_map)
            merged_files_map.update(draft_files_map)

            draft.files = [CodeFile(path=p, content=c) for p, c in sorted(merged_files_map.items())]
            draft.complete_project_files = list(draft.files)
            draft.changed_files = sorted(changed)
        else:
            draft.complete_project_files = list(draft.files)
            draft.changed_files = [item.path for item in draft.files]

        # Run Implementation Validator on complete project files
        from backend.tools.implementation_validator import validate_implementation

        val_result = validate_implementation(
            files=draft.files,
            architecture=observed.get("architecture"),
            requirements=observed.get("requirements"),
            setup_instructions=draft.setup_instructions,
            existing_files=existing_raw,
            mode=mode,
        )
        draft.validation_passed = val_result.passed
        draft.validation_issues = [issue.to_dict() for issue in val_result.issues]

        # Write ALL complete project files to temporary root to validate structure
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for item in draft.files:
                path = root / item.path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(item.content, encoding="utf-8")
            structure = list_structure(root)

        draft.project_structure = structure
        return {
            "structure": structure,
            "total_files": len(draft.files),
            "changed_files": draft.changed_files,
            "mode": mode,
            "validation": val_result.to_dict(),
        }

    def apply_tools(self, output: CodeOutput, tool_context: dict[str, Any]) -> CodeOutput:
        return output
