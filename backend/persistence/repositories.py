from __future__ import annotations

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
from backend.persistence import memory_store
from backend.persistence.database import database_available, session_scope


def _require_db() -> None:
    if not database_available():
        raise RuntimeError("PostgreSQL is not available")


def create_project(user_id: str, name: str, idea: str) -> dict[str, Any]:
    if not database_available():
        return memory_store.create_project(user_id, name, idea)
    _require_db()
    project = Project(id=new_id(), user_id=user_id, name=name, idea=idea, status="ACTIVE")
    with session_scope() as session:
        session.add(project)
        session.flush()
        return serialize_project(project)


def list_projects(user_id: str) -> list[dict[str, Any]]:
    if not database_available():
        return memory_store.list_projects(user_id)
    with session_scope() as session:
        rows = session.scalars(select(Project).where(Project.user_id == user_id).order_by(Project.created_at.desc())).all()
        return [serialize_project(row) for row in rows]


def get_project(project_id: str, user_id: str) -> Optional[dict[str, Any]]:
    if not database_available():
        return memory_store.get_project(project_id, user_id)
    with session_scope() as session:
        row = session.scalar(select(Project).where(Project.id == project_id, Project.user_id == user_id))
        return serialize_project(row) if row else None


def update_project(project_id: str, user_id: str, **fields: Any) -> Optional[dict[str, Any]]:
    _require_db()
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
    _require_db()
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
    if not database_available():
        return memory_store.create_run(project_id, user_id, execution_mode, config_json)
    _require_db()
    run = PipelineRun(
        id=new_id(),
        project_id=project_id,
        user_id=user_id,
        execution_mode=execution_mode,
        status="QUEUED",
        current_stage="START",
        started_at=utc_now(),
        config_json=config_json or {},
    )
    with session_scope() as session:
        session.add(run)
        session.flush()
        return serialize_run(run)


def get_run(run_id: str, user_id: Optional[str] = None) -> Optional[dict[str, Any]]:
    if not database_available():
        return memory_store.get_run(run_id, user_id)
    with session_scope() as session:
        stmt = select(PipelineRun).where(PipelineRun.id == run_id)
        if user_id:
            stmt = stmt.where(PipelineRun.user_id == user_id)
        row = session.scalar(stmt)
        return serialize_run(row) if row else None


def list_runs(user_id: str, project_id: Optional[str] = None) -> list[dict[str, Any]]:
    if not database_available():
        return memory_store.list_runs(user_id, project_id)
    with session_scope() as session:
        stmt = select(PipelineRun).where(PipelineRun.user_id == user_id)
        if project_id:
            stmt = stmt.where(PipelineRun.project_id == project_id)
        rows = session.scalars(stmt.order_by(PipelineRun.started_at.desc())).all()
        return [serialize_run(row) for row in rows]


def update_run(run_id: str, **fields: Any) -> None:
    if not database_available():
        memory_store.update_run(run_id, **fields)
        return
    with session_scope() as session:
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
    if database_available():
        with session_scope() as session:
            session.add(WorkflowEventRow(**event))
    else:
        return memory_store.add_event(payload)
    return event


def list_events(run_id: str) -> list[dict[str, Any]]:
    if not database_available():
        return memory_store.list_events(run_id)
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
    if database_available():
        with session_scope() as session:
            session.add(
                AgentExecution(
                    id=execution_id,
                    run_id=payload["run_id"],
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
    if not database_available():
        return
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
    if not database_available():
        return []
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
    if not database_available():
        return memory_store.add_artifact(run_id, artifact_type, title, content, storage_path, metadata)
    artifact_id = new_id()
    if database_available():
        with session_scope() as session:
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
    if not database_available():
        return memory_store.list_artifacts(run_id)
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
    if not database_available():
        memory_store.replace_security_findings(run_id, findings)
        return
    with session_scope() as session:
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
    if not database_available():
        return memory_store.list_security_findings(run_id)
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


def add_test_result(run_id: str, payload: dict[str, Any]) -> None:
    if not database_available():
        memory_store.add_test_result(run_id, payload)
        return
    with session_scope() as session:
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
    if not database_available():
        return memory_store.latest_test_result(run_id)
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
    if not database_available():
        memory_store.add_review_result(run_id, payload)
        return
    with session_scope() as session:
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
    if not database_available():
        return memory_store.latest_review_result(run_id)
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
    if not database_available():
        memory_store.add_model_comparisons(run_id, results)
        return
    with session_scope() as session:
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
    if not database_available():
        return memory_store.list_model_comparisons(run_id)
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
    if not database_available():
        memory_store.save_checkpoint(run_id, thread_id, checkpoint_id, state, parent, metadata)
        return
    with session_scope() as session:
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
    if not database_available():
        return memory_store.latest_checkpoint(run_id)
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
    if not database_available():
        return memory_store.metrics(user_id)
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
        "config": row.config_json or {},
    }
