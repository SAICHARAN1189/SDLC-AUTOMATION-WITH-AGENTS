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
            return output
        return demo_initial_code()

    def build_prompt(self, observed: dict[str, Any]) -> tuple[str, str]:
        mode = observed.get("developer_mode") or DeveloperMode.INITIAL_IMPLEMENTATION.value
        arch = observed.get("architecture") or {}
        reqs = observed.get("requirements") or {}
        sec = observed.get("security_report") or {}
        qa = observed.get("test_report") or {}
        rev = observed.get("review_report") or {}
        code_data = observed.get("code") or {}

        if mode == DeveloperMode.INITIAL_IMPLEMENTATION.value:
            system = (
                "You are an expert Full-Stack Software Engineer. "
                "CRITICAL IMPLEMENTATION CONTRACT:\n"
                "1. INITIAL_IMPLEMENTATION: You MUST generate ALL files required for a COMPLETE, RUNNABLE project.\n"
                "   Do NOT output only a partial file list or single patch.\n"
                "   For web applications, include all required: HTML, CSS, JavaScript/TypeScript, configuration, "
                "dependency files (requirements.txt, package.json), backend files (app.py, routes, models), and test support files.\n"
                "2. The output MUST represent a runnable project where all file references, imports, and script tags are consistent.\n"
                "Return ONLY a single valid JSON object strictly matching this schema with no conversational text or markdown code fence:\n"
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
                "1. Analyze the exact QA failures and/or Security vulnerabilities reported.\n"
                "   For QA failures, examine: failing test, expected behavior, actual behavior, affected file, and root cause.\n"
                "2. Fix the underlying application code / logic so it satisfies requirements and tests.\n"
                "3. DO NOT blindly add dependencies (e.g. do not add selenium unless genuinely required by the architecture).\n"
                "4. DO NOT merely patch or bypass tests without fixing the application.\n"
                "5. Preserve working functionality across all existing files.\n"
                "6. Return the updated files. Any files you provide will be merged into the existing project files "
                "to maintain the COMPLETE, CONSISTENT project.\n"
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

        # Preserve exact test failures with root cause and affected files
        qa_failures = [
            {
                "test": f.get("test") or f.get("test_name"),
                "test_name": f.get("test_name") or f.get("test"),
                "expected": f.get("expected"),
                "actual": f.get("actual"),
                "root_cause": f.get("root_cause"),
                "affected_files": f.get("affected_files") or [],
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
            draft.changed_files = sorted(changed)
        else:
            draft.changed_files = [item.path for item in draft.files]

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
        }

    def apply_tools(self, output: CodeOutput, tool_context: dict[str, Any]) -> CodeOutput:
        return output
