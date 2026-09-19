from __future__ import annotations

from typing import Any


def prepare_agent_context(agent_name: str, state: dict[str, Any]) -> dict[str, Any]:
    """
    Selects only the task-relevant state for each specific agent, stripping duplicate
    logs, extraneous events, and unrelated stage artifacts while strictly preserving
    exact code, requirements, acceptance criteria, security evidence, and test failures.

    Priority order:
    Correctness > Completeness > Token efficiency.
    """
    key = (
        agent_name.lower()
        .replace("_agent", "")
        .replace("_node", "")
        .replace(" ", "_")
        .strip()
    )

    reqs = state.get("requirements") or {}
    arch = state.get("architecture") or {}
    code = state.get("code") or {}
    sec = state.get("security_report") or {}
    qa = state.get("test_report") or {}
    rev = state.get("review_report") or {}

    if key == "requirements":
        return {
            "user_idea": state.get("user_idea") or "",
            "constraints": reqs.get("constraints") or [],
        }

    if key == "architecture":
        return {
            "user_idea": state.get("user_idea") or "",
            "requirements": {
                "project_summary": reqs.get("project_summary") or "",
                "functional_requirements": reqs.get("functional_requirements") or [],
                "non_functional_requirements": reqs.get("non_functional_requirements") or [],
                "target_users": reqs.get("target_users") or [],
                "constraints": reqs.get("constraints") or [],
                "assumptions": reqs.get("assumptions") or [],
                "edge_cases": reqs.get("edge_cases") or [],
            },
        }

    if key == "visual_architecture":
        return {
            "style": arch.get("architecture_style") or "Modular",
            "frontend": arch.get("frontend") or "React",
            "backend": arch.get("backend") or "Flask",
            "database": arch.get("database") or "PostgreSQL",
            "services": (arch.get("services") or [])[:6],
            "modules": (arch.get("modules") or [])[:6],
            "apis": (arch.get("apis") or [])[:6],
            "project_summary": reqs.get("project_summary") or "",
        }

    if key == "developer":
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

        ctx: dict[str, Any] = {
            "developer_mode": state.get("developer_mode") or "INITIAL_IMPLEMENTATION",
            "user_idea": state.get("user_idea") or "",
            "requirements": {
                "project_summary": reqs.get("project_summary") or "",
                "functional_requirements": reqs.get("functional_requirements") or [],
                "acceptance_criteria": reqs.get("acceptance_criteria") or [],
            },
            "architecture": {
                "style": arch.get("architecture_style"),
                "backend": arch.get("backend"),
                "database": arch.get("database"),
                "services": arch.get("services") or [],
                "apis": arch.get("apis") or [],
            },
        }
        if code.get("files"):
            ctx["existing_files"] = [
                {
                    "path": f.path if hasattr(f, "path") else f.get("path"),
                    "content": f.content if hasattr(f, "content") else f.get("content", ""),
                }
                for f in code.get("files") or []
                if (hasattr(f, "path") or "path" in f)
            ]
        if sec_findings:
            ctx["security_feedback"] = sec_findings
        if qa_failures:
            ctx["qa_feedback"] = qa_failures
        if rev.get("blocking_issues") or rev.get("required_changes"):
            ctx["review_feedback"] = {
                "blocking_issues": rev.get("blocking_issues") or [],
                "required_changes": rev.get("required_changes") or [],
            }
        return ctx

    if key == "security":
        files = code.get("files") or []
        normalized_files = [
            {
                "path": f.path if hasattr(f, "path") else f.get("path"),
                "content": f.content if hasattr(f, "content") else f.get("content", ""),
            }
            for f in files
            if (hasattr(f, "path") or "path" in f)
        ]
        return {
            "architecture_context": {
                "style": arch.get("architecture_style"),
                "backend": arch.get("backend"),
                "database": arch.get("database"),
                "apis": arch.get("apis") or [],
            },
            "files": normalized_files,
        }

    if key == "qa":
        files = code.get("files") or []
        normalized_files = [
            {
                "path": f.path if hasattr(f, "path") else f.get("path"),
                "content": f.content if hasattr(f, "content") else f.get("content", ""),
            }
            for f in files
            if (hasattr(f, "path") or "path" in f)
        ]
        return {
            "requirements": {
                "project_summary": reqs.get("project_summary") or "",
                "functional_requirements": reqs.get("functional_requirements") or [],
                "user_stories": reqs.get("user_stories") or [],
                "acceptance_criteria": reqs.get("acceptance_criteria") or [],
                "edge_cases": reqs.get("edge_cases") or [],
            },
            "framework": arch.get("backend") or "Flask",
            "source_files": normalized_files,
        }

    if key == "review":
        files = code.get("files") or []
        normalized_files = [
            {
                "path": f.path if hasattr(f, "path") else f.get("path"),
                "content": f.content if hasattr(f, "content") else f.get("content", ""),
            }
            for f in files
            if (hasattr(f, "path") or "path" in f)
        ]
        return {
            "requirements": {
                "project_summary": reqs.get("project_summary") or "",
                "functional_requirements": reqs.get("functional_requirements") or [],
            },
            "architecture": {
                "style": arch.get("architecture_style"),
                "backend": arch.get("backend"),
                "database": arch.get("database"),
                "services": arch.get("services") or [],
                "apis": arch.get("apis") or [],
            },
            "files": normalized_files,
            "security_summary": {
                "status": sec.get("overall_status"),
                "blocking": sec.get("blocking"),
                "high_or_critical_issues": [
                    v.get("description")
                    for v in sec.get("vulnerabilities") or []
                    if v.get("severity") in ("CRITICAL", "HIGH")
                ],
            },
            "test_summary": {
                "status": qa.get("overall_status"),
                "total": qa.get("total"),
                "passed": qa.get("passed"),
                "failed": qa.get("failed"),
            },
        }

    # Default: return shallow clean copy of state without logs or raw events
    pruned = dict(state)
    pruned.pop("workflow_events", None)
    pruned.pop("messages", None)
    pruned.pop("errors", None)
    return pruned
