from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy import func, select

from backend.models.database_models import (
    AgentExecution,
    Artifact,
    ModelComparison,
    PipelineRun,
    Project,
    ReviewResult,
    SecurityFinding,
    TestResult,
    WorkflowCheckpoint,
    WorkflowEventRow,
)
from backend.models.schemas import new_id, utc_now
from backend.persistence.database import session_scope
from backend.utils.logging import logger


def create_project(user_id: str, name: str, idea: str) -> dict[str, Any]:
    logger.info(f"[PROJECT] Creating project: {name}")
    project = Project(id=new_id(), user_id=user_id, name=name, idea=idea, status="ACTIVE")
    with session_scope() as session:
        session.add(project)
        session.flush()
        res = serialize_project(project)
    logger.info(f"[PROJECT] Project persisted: {res['id']}")
    return res


def list_projects(user_id: str) -> list[dict[str, Any]]:
    with session_scope() as session:
        stmt = select(Project).where(Project.user_id == user_id).order_by(Project.created_at.desc())
        rows = session.scalars(stmt).all()
        return [serialize_project(row) for row in rows]


def get_project(project_id: str, user_id: str) -> Optional[dict[str, Any]]:
    with session_scope() as session:
        row = session.scalar(select(Project).where(Project.id == project_id, Project.user_id == user_id))
        return serialize_project(row) if row else None


def update_project(project_id: str, user_id: str, **fields: Any) -> Optional[dict[str, Any]]:
    with session_scope() as session:
        row = session.scalar(select(Project).where(Project.id == project_id, Project.user_id == user_id))
        if not row:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(row, key):
                setattr(row, key, value)
        session.flush()
        return serialize_project(row)


def delete_project(project_id: str, user_id: str) -> bool:
    with session_scope() as session:
        row = session.scalar(select(Project).where(Project.id == project_id, Project.user_id == user_id))
        if not row:
            return False
        session.delete(row)
        return True


def create_run(
    project_id: str,
    user_id: str,
    execution_mode: str,
    config_json: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    run_id = new_id()
    logger.info(f"[RUN] Creating pipeline run: {run_id} for project {project_id}")
    run = PipelineRun(
        id=run_id,
        project_id=project_id,
        user_id=user_id,
        execution_mode=execution_mode,
        status="QUEUED",
        current_stage="START",
        started_at=utc_now(),
        config_json=config_json or {},
        rework_count=0,
    )
    with session_scope() as session:
        session.add(run)
        session.flush()
        res = serialize_run(run)
    logger.info(f"[RUN] Run persisted: {run_id}")
    return res


def get_run(run_id: str, user_id: Optional[str] = None) -> Optional[dict[str, Any]]:
    with session_scope() as session:
        stmt = select(PipelineRun).where(PipelineRun.id == run_id)
        if user_id:
            stmt = stmt.where(PipelineRun.user_id == user_id)
        row = session.scalar(stmt)
        return serialize_run(row) if row else None


def list_runs(user_id: str, project_id: Optional[str] = None) -> list[dict[str, Any]]:
    with session_scope() as session:
        stmt = select(PipelineRun).where(PipelineRun.user_id == user_id)
        if project_id:
            stmt = stmt.where(PipelineRun.project_id == project_id)
        rows = session.scalars(stmt.order_by(PipelineRun.started_at.desc())).all()
        return [serialize_run(row) for row in rows]


def _ensure_run_exists(session: Any, run_id: str, project_id: Optional[str] = None, user_id: str = "demo-user") -> None:
    """Ensure parent Project and PipelineRun exist before inserting child records with foreign keys."""
    run = session.scalar(select(PipelineRun).where(PipelineRun.id == run_id))
    if not run:
        p_id = project_id or "default-project"
        proj = session.scalar(select(Project).where(Project.id == p_id))
        if not proj:
            session.add(Project(id=p_id, user_id=user_id, name="Default Project", idea="Automated or test project"))
            session.flush()
        session.add(
            PipelineRun(
                id=run_id,
                project_id=p_id,
                user_id=user_id,
                execution_mode="FULL_AUTONOMOUS",
                status="RUNNING",
                current_stage="START",
            )
        )
        session.flush()


def update_run(run_id: str, **fields: Any) -> None:
    with session_scope() as session:
        row = session.scalar(select(PipelineRun).where(PipelineRun.id == run_id))
        if not row:
            _ensure_run_exists(session, run_id)
            row = session.scalar(select(PipelineRun).where(PipelineRun.id == run_id))
        if not row:
            return
        for key, value in fields.items():
            if hasattr(row, key):
                setattr(row, key, value)


def add_event(payload: dict[str, Any]) -> dict[str, Any]:
    event = {
        "id": payload.get("event_id") or payload.get("id") or new_id(),
        "run_id": payload["run_id"],
        "timestamp": payload.get("timestamp") or utc_now(),
        "stage": payload.get("stage") or "UNKNOWN",
        "agent": payload.get("agent"),
        "event_type": payload["event_type"],
        "status": payload.get("status") or "INFO",
        "message": payload.get("message") or "",
        "metadata_json": payload.get("metadata") or payload.get("metadata_json") or {},
    }
    with session_scope() as session:
        _ensure_run_exists(session, event["run_id"])
        session.add(WorkflowEventRow(**event))
    return event


def list_events(run_id: str) -> list[dict[str, Any]]:
    with session_scope() as session:
        rows = session.scalars(
            select(WorkflowEventRow).where(WorkflowEventRow.run_id == run_id).order_by(WorkflowEventRow.timestamp.asc())
        ).all()
        return [
            {
                "id": row.id,
                "run_id": row.run_id,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "stage": row.stage,
                "agent": row.agent,
                "event_type": row.event_type,
                "status": row.status,
                "message": row.message,
                "metadata": row.metadata_json or {},
            }
            for row in rows
        ]


def add_agent_execution(payload: dict[str, Any]) -> str:
    execution_id = payload.get("id") or new_id()
    run_id = payload["run_id"]
    with session_scope() as session:
        _ensure_run_exists(session, run_id)
        session.add(
            AgentExecution(
                id=execution_id,
                run_id=run_id,
                agent_name=payload["agent_name"],
                model=payload.get("model"),
                started_at=payload.get("started_at") or utc_now(),
                completed_at=payload.get("completed_at"),
                duration=payload.get("duration"),
                status=payload.get("status") or "RUNNING",
                retry_number=payload.get("retry_number") or 0,
                token_usage_if_available=payload.get("token_usage_if_available"),
            )
        )
    return execution_id


def complete_agent_execution(execution_id: str, status: str, duration: float, token_usage: Optional[dict] = None) -> None:
    with session_scope() as session:
        row = session.scalar(select(AgentExecution).where(AgentExecution.id == execution_id))
        if not row:
            return
        row.status = status
        row.duration = duration
        row.completed_at = utc_now()
        if token_usage:
            row.token_usage_if_available = token_usage


def list_agent_executions(run_id: str) -> list[dict[str, Any]]:
    with session_scope() as session:
        rows = session.scalars(
            select(AgentExecution).where(AgentExecution.run_id == run_id).order_by(AgentExecution.started_at.asc())
        ).all()
        return [
            {
                "id": row.id,
                "run_id": row.run_id,
                "agent_name": row.agent_name,
                "model": row.model,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "duration": row.duration,
                "status": row.status,
                "retry_number": row.retry_number,
                "token_usage_if_available": row.token_usage_if_available,
            }
            for row in rows
        ]


def add_artifact(run_id: str, artifact_type: str, title: str, content: Optional[str] = None, storage_path: Optional[str] = None, metadata: Optional[dict] = None) -> str:
    artifact_id = new_id()
    with session_scope() as session:
        _ensure_run_exists(session, run_id)
        session.add(
            Artifact(
                id=artifact_id,
                run_id=run_id,
                artifact_type=artifact_type,
                title=title,
                content=content,
                storage_path=storage_path,
                metadata_json=metadata or {},
            )
        )
    return artifact_id


def list_artifacts(run_id: str) -> list[dict[str, Any]]:
    with session_scope() as session:
        rows = session.scalars(select(Artifact).where(Artifact.run_id == run_id).order_by(Artifact.created_at.asc())).all()
        return [
            {
                "id": row.id,
                "run_id": row.run_id,
                "artifact_type": row.artifact_type,
                "title": row.title,
                "content": row.content,
                "storage_path": row.storage_path,
                "metadata": row.metadata_json or {},
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]


def replace_security_findings(run_id: str, findings: list[dict[str, Any]]) -> None:
    with session_scope() as session:
        _ensure_run_exists(session, run_id)
        existing = session.scalars(select(SecurityFinding).where(SecurityFinding.run_id == run_id)).all()
        for row in existing:
            session.delete(row)
        for finding in findings:
            session.add(
                SecurityFinding(
                    id=finding.get("id") or new_id(),
                    run_id=run_id,
                    category=finding.get("category") or "unknown",
                    severity=finding.get("severity") or "LOW",
                    description=finding.get("description") or "",
                    evidence=finding.get("evidence") or "",
                    remediation=finding.get("remediation") or "",
                    affected_file=finding.get("affected_file"),
                    affected_line=finding.get("affected_line"),
                    status=finding.get("status") or "OPEN",
                    source=finding.get("source"),
                    caused_rework=finding.get("caused_rework") or False,
                )
            )


def list_security_findings(run_id: str) -> list[dict[str, Any]]:
    with session_scope() as session:
        rows = session.scalars(select(SecurityFinding).where(SecurityFinding.run_id == run_id)).all()
        return [
            {
                "id": row.id,
                "run_id": row.run_id,
                "category": row.category,
                "severity": row.severity,
                "description": row.description,
                "evidence": row.evidence,
                "remediation": row.remediation,
                "affected_file": row.affected_file,
                "affected_line": row.affected_line,
                "status": row.status,
                "source": row.source,
                "caused_rework": row.caused_rework,
            }
            for row in rows
        ]


def get_run_security_output(run_id: str) -> dict[str, Any]:
    with session_scope() as session:
        art = session.scalars(
            select(Artifact)
            .where(Artifact.run_id == run_id, Artifact.artifact_type == "security")
            .order_by(Artifact.created_at.desc())
        ).first()
        if art and art.content:
            try:
                parsed = json.loads(art.content)
                if isinstance(parsed, dict) and "vulnerabilities" in parsed:
                    return parsed
            except Exception:
                pass

        rows = session.scalars(select(SecurityFinding).where(SecurityFinding.run_id == run_id)).all()
        findings = [
            {
                "id": row.id,
                "run_id": row.run_id,
                "category": row.category,
                "severity": (row.severity or "LOW").upper(),
                "description": row.description,
                "evidence": row.evidence,
                "remediation": row.remediation,
                "affected_file": row.affected_file,
                "affected_line": row.affected_line,
                "status": row.status,
                "source": row.source,
                "caused_rework": row.caused_rework,
            }
            for row in rows
        ]
        critical = sum(1 for f in findings if f["severity"] == "CRITICAL")
        high = sum(1 for f in findings if f["severity"] == "HIGH")
        medium = sum(1 for f in findings if f["severity"] == "MEDIUM")
        low = sum(1 for f in findings if f["severity"] == "LOW")
        overall = "FAIL" if (critical > 0 or high > 0) else ("WARNING" if medium > 0 else "PASS")
        return {
            "overall_status": overall,
            "severity_summary": {"critical": critical, "high": high, "medium": medium, "low": low},
            "vulnerabilities": findings,
            "recommendations": [],
            "remediation_actions": [],
            "affected_files": list({f["affected_file"] for f in findings if f.get("affected_file")}),
            "scan_timestamp": utc_now().isoformat(),
            "disclaimer": "Dual-layer deterministic static analysis + LLM semantic threat assessment from Supabase audit repository.",
        }


def get_security_overview(user_id: str, project_id: Optional[str] = None) -> dict[str, Any]:
    with session_scope() as session:
        proj_query = select(Project).where(Project.user_id == user_id)
        if project_id:
            proj_query = proj_query.where(Project.id == project_id)
        projects = session.scalars(proj_query.order_by(Project.created_at.desc())).all()
        project_ids = [p.id for p in projects]

        if not project_ids:
            return {
                "summary": {"total_projects": 0, "total_scans": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "resolved": 0, "open": 0},
                "projects": [],
                "findings": [],
            }

        runs = session.scalars(
            select(PipelineRun)
            .where(PipelineRun.project_id.in_(project_ids))
            .order_by(PipelineRun.started_at.desc())
        ).all()
        run_ids = [r.id for r in runs]
        run_to_project = {r.id: r.project_id for r in runs}
        project_names = {p.id: p.name for p in projects}

        findings_rows = []
        if run_ids:
            findings_rows = session.scalars(
                select(SecurityFinding)
                .where(SecurityFinding.run_id.in_(run_ids))
            ).all()

        findings_list = []
        critical = high = medium = low = resolved = open_count = 0

        for f in findings_rows:
            p_id = run_to_project.get(f.run_id, "")
            p_name = project_names.get(p_id, "Unknown Project")
            sev = (f.severity or "LOW").upper()
            if sev == "CRITICAL":
                critical += 1
            elif sev == "HIGH":
                high += 1
            elif sev == "MEDIUM":
                medium += 1
            else:
                low += 1

            st = (f.status or "OPEN").upper()
            if st == "RESOLVED":
                resolved += 1
            else:
                open_count += 1

            findings_list.append({
                "id": f.id,
                "project_id": p_id,
                "project_name": p_name,
                "run_id": f.run_id,
                "category": f.category,
                "severity": sev,
                "description": f.description,
                "evidence": f.evidence,
                "remediation": f.remediation,
                "affected_file": f.affected_file,
                "affected_line": f.affected_line,
                "status": st,
                "source": f.source,
                "caused_rework": f.caused_rework,
            })

        project_summaries = []
        for p in projects:
            p_runs = [r for r in runs if r.project_id == p.id]
            p_findings = [f for f in findings_list if f["project_id"] == p.id]
            p_crit = sum(1 for f in p_findings if f["severity"] == "CRITICAL")
            p_high = sum(1 for f in p_findings if f["severity"] == "HIGH")
            p_med = sum(1 for f in p_findings if f["severity"] == "MEDIUM")
            p_low = sum(1 for f in p_findings if f["severity"] == "LOW")
            status = "FAIL" if (p_crit > 0 or p_high > 0) else ("WARNING" if p_med > 0 else "PASS")
            last_dt = (p_runs[0].completed_at or p_runs[0].started_at) if p_runs else None

            project_summaries.append({
                "project_id": p.id,
                "project_name": p.name,
                "description": getattr(p, "idea", "") or "",
                "total_runs": len(p_runs),
                "latest_run_id": p_runs[0].id if p_runs else None,
                "overall_status": status,
                "findings_count": len(p_findings),
                "severity_summary": {
                    "critical": p_crit,
                    "high": p_high,
                    "medium": p_med,
                    "low": p_low,
                },
                "last_scanned_at": last_dt.isoformat() if last_dt else None,
            })

        return {
            "summary": {
                "total_projects": len(projects),
                "total_scans": len(runs),
                "critical": critical,
                "high": high,
                "medium": medium,
                "low": low,
                "resolved": resolved,
                "open": open_count,
            },
            "projects": project_summaries,
            "findings": findings_list,
        }


def add_test_result(run_id: str, payload: dict[str, Any]) -> None:
    with session_scope() as session:
        _ensure_run_exists(session, run_id)
        session.add(
            TestResult(
                id=new_id(),
                run_id=run_id,
                total=payload.get("total") or 0,
                passed=payload.get("passed") or 0,
                failed=payload.get("failed") or 0,
                skipped=payload.get("skipped") or 0,
                duration=payload.get("duration") or 0.0,
                output=payload.get("output") or payload.get("summary"),
                details_json=payload,
            )
        )


def latest_test_result(run_id: str) -> Optional[dict[str, Any]]:
    with session_scope() as session:
        row = session.scalars(select(TestResult).where(TestResult.run_id == run_id)).first()
        if not row:
            return None
        return {
            "id": row.id,
            "run_id": row.run_id,
            "total": row.total,
            "passed": row.passed,
            "failed": row.failed,
            "skipped": row.skipped,
            "duration": row.duration,
            "output": row.output,
            "details": row.details_json,
        }


def add_review_result(run_id: str, payload: dict[str, Any]) -> None:
    with session_scope() as session:
        _ensure_run_exists(session, run_id)
        session.add(
            ReviewResult(
                id=new_id(),
                run_id=run_id,
                status=payload.get("review_status") or payload.get("status") or "PENDING",
                blocking_issues=payload.get("blocking_issues") or [],
                findings=payload.get("findings") or [],
                recommendations=payload.get("recommendations") or [],
            )
        )


def latest_review_result(run_id: str) -> Optional[dict[str, Any]]:
    with session_scope() as session:
        row = session.scalars(select(ReviewResult).where(ReviewResult.run_id == run_id)).first()
        if not row:
            return None
        return {
            "id": row.id,
            "run_id": row.run_id,
            "status": row.status,
            "blocking_issues": row.blocking_issues,
            "findings": row.findings,
            "recommendations": row.recommendations,
        }


def add_model_comparisons(run_id: str, results: list[dict[str, Any]]) -> None:
    with session_scope() as session:
        _ensure_run_exists(session, run_id)
        for result in results:
            session.add(
                ModelComparison(
                    id=new_id(),
                    run_id=run_id,
                    model=result.get("model") or "unknown",
                    latency=result.get("latency_ms") or result.get("latency") or 0,
                    output=result.get("output") or "",
                    metrics_json=result,
                )
            )


def list_model_comparisons(run_id: str) -> list[dict[str, Any]]:
    with session_scope() as session:
        rows = session.scalars(select(ModelComparison).where(ModelComparison.run_id == run_id)).all()
        return [
            {
                "id": row.id,
                "run_id": row.run_id,
                "model": row.model,
                "latency": row.latency,
                "output": row.output,
                "metrics": row.metrics_json or {},
            }
            for row in rows
        ]


def save_checkpoint(run_id: str, thread_id: str, checkpoint_id: str, state: dict[str, Any], parent: Optional[str] = None, metadata: Optional[dict] = None) -> None:
    with session_scope() as session:
        _ensure_run_exists(session, run_id)
        session.add(
            WorkflowCheckpoint(
                id=new_id(),
                run_id=run_id,
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                parent_checkpoint_id=parent,
                state_json=state,
                metadata_json=metadata or {},
            )
        )


def latest_checkpoint(run_id: str) -> Optional[dict[str, Any]]:
    with session_scope() as session:
        row = session.scalars(
            select(WorkflowCheckpoint)
            .where(WorkflowCheckpoint.run_id == run_id)
            .order_by(WorkflowCheckpoint.created_at.desc())
        ).first()
        if not row:
            return None
        return {
            "id": row.id,
            "run_id": row.run_id,
            "thread_id": row.thread_id,
            "checkpoint_id": row.checkpoint_id,
            "state": row.state_json,
            "metadata": row.metadata_json,
        }


def dashboard_metrics(user_id: str) -> dict[str, int]:
    with session_scope() as session:
        projects = session.scalar(select(func.count(Project.id)).where(Project.user_id == user_id)) or 0
        active = session.scalar(
            select(func.count(PipelineRun.id)).where(
                PipelineRun.user_id == user_id, PipelineRun.status.in_(["QUEUED", "RUNNING", "WAITING", "REWORKING"])
            )
        ) or 0
        completed = session.scalar(
            select(func.count(PipelineRun.id)).where(PipelineRun.user_id == user_id, PipelineRun.status == "COMPLETED")
        ) or 0
        artifacts = (
            session.scalar(
                select(func.count(Artifact.id))
                .join(PipelineRun, Artifact.run_id == PipelineRun.id)
                .where(PipelineRun.user_id == user_id)
            )
            or 0
        )
        findings = (
            session.scalar(
                select(func.count(SecurityFinding.id))
                .join(PipelineRun, SecurityFinding.run_id == PipelineRun.id)
                .where(PipelineRun.user_id == user_id)
            )
            or 0
        )
        return {
            "projects": int(projects),
            "active_runs": int(active),
            "completed_runs": int(completed),
            "artifacts": int(artifacts),
            "security_findings": int(findings),
        }


def serialize_project(row: Project) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "name": row.name,
        "idea": row.idea,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def serialize_run(row: PipelineRun) -> dict[str, Any]:
    return {
        "id": row.id,
        "project_id": row.project_id,
        "user_id": row.user_id,
        "execution_mode": row.execution_mode,
        "status": row.status,
        "current_stage": row.current_stage,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "error_message": row.error_message,
        "rework_count": getattr(row, "rework_count", 0),
        "config": row.config_json or {},
    }
