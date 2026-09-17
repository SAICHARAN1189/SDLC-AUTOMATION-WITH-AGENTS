from __future__ import annotations

from typing import Any, Optional

from backend.config.settings import settings
from backend.models.schemas import new_id, utc_now

_projects: dict[str, dict[str, Any]] = {}
_runs: dict[str, dict[str, Any]] = {}
_events: dict[str, list[dict[str, Any]]] = {}
_artifacts: dict[str, list[dict[str, Any]]] = {}
_security: dict[str, list[dict[str, Any]]] = {}
_tests: dict[str, dict[str, Any]] = {}
_reviews: dict[str, dict[str, Any]] = {}
_models: dict[str, list[dict[str, Any]]] = {}
_checkpoints: dict[str, dict[str, Any]] = {}


def enabled() -> bool:
    return settings.demo_mode


def create_project(user_id: str, name: str, idea: str) -> dict[str, Any]:
    row = {
        "id": new_id(),
        "user_id": user_id,
        "name": name,
        "idea": idea,
        "status": "ACTIVE",
        "created_at": utc_now().isoformat(),
        "updated_at": utc_now().isoformat(),
        "demo": True,
    }
    _projects[row["id"]] = row
    return row


def list_projects(user_id: str) -> list[dict[str, Any]]:
    return [row for row in _projects.values() if row["user_id"] == user_id]


def get_project(project_id: str, user_id: str) -> Optional[dict[str, Any]]:
    row = _projects.get(project_id)
    if row and row["user_id"] == user_id:
        return row
    return None


def create_run(project_id: str, user_id: str, execution_mode: str, config_json: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    row = {
        "id": new_id(),
        "project_id": project_id,
        "user_id": user_id,
        "execution_mode": execution_mode,
        "status": "QUEUED",
        "current_stage": "START",
        "started_at": utc_now().isoformat(),
        "completed_at": None,
        "error_message": None,
        "config": config_json or {},
        "demo": True,
    }
    _runs[row["id"]] = row
    return row


def get_run(run_id: str, user_id: Optional[str] = None) -> Optional[dict[str, Any]]:
    row = _runs.get(run_id)
    if not row:
        return None
    if user_id and row["user_id"] != user_id:
        return None
    return row


def list_runs(user_id: str, project_id: Optional[str] = None) -> list[dict[str, Any]]:
    rows = [row for row in _runs.values() if row["user_id"] == user_id]
    if project_id:
        rows = [row for row in rows if row["project_id"] == project_id]
    return rows


def update_run(run_id: str, **fields: Any) -> None:
    row = _runs.get(run_id)
    if not row:
        return
    for key, value in fields.items():
        if key == "config_json":
            row["config"] = value
        else:
            row[key] = value.isoformat() if hasattr(value, "isoformat") else value


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
    if hasattr(event["timestamp"], "isoformat"):
        event["timestamp"] = event["timestamp"].isoformat()
    _events.setdefault(event["run_id"], []).append(
        {
            "id": event["id"],
            "run_id": event["run_id"],
            "timestamp": event["timestamp"],
            "stage": event["stage"],
            "agent": event["agent"],
            "event_type": event["event_type"],
            "status": event["status"],
            "message": event["message"],
            "metadata": event["metadata_json"],
        }
    )
    return event


def list_events(run_id: str) -> list[dict[str, Any]]:
    return list(_events.get(run_id) or [])


def add_artifact(run_id: str, artifact_type: str, title: str, content: Optional[str] = None, storage_path: Optional[str] = None, metadata: Optional[dict] = None) -> str:
    artifact_id = new_id()
    _artifacts.setdefault(run_id, []).append(
        {
            "id": artifact_id,
            "run_id": run_id,
            "artifact_type": artifact_type,
            "title": title,
            "content": content,
            "storage_path": storage_path,
            "metadata": metadata or {},
            "created_at": utc_now().isoformat(),
        }
    )
    return artifact_id


def list_artifacts(run_id: str) -> list[dict[str, Any]]:
    return list(_artifacts.get(run_id) or [])


def replace_security_findings(run_id: str, findings: list[dict[str, Any]]) -> None:
    _security[run_id] = [
        {
            "id": finding.get("id") or new_id(),
            "run_id": run_id,
            **finding,
        }
        for finding in findings
    ]


def list_security_findings(run_id: str) -> list[dict[str, Any]]:
    return list(_security.get(run_id) or [])


def add_test_result(run_id: str, payload: dict[str, Any]) -> None:
    _tests[run_id] = {"id" : new_id(), "run_id": run_id, **payload}


def latest_test_result(run_id: str) -> Optional[dict[str, Any]]:
    return _tests.get(run_id)


def add_review_result(run_id: str, payload: dict[str, Any]) -> None:
    _reviews[run_id] = {"id": new_id(), "run_id": run_id, **payload}


def latest_review_result(run_id: str) -> Optional[dict[str, Any]]:
    return _reviews.get(run_id)


def add_model_comparisons(run_id: str, results: list[dict[str, Any]]) -> None:
    _models[run_id] = results


def list_model_comparisons(run_id: str) -> list[dict[str, Any]]:
    return list(_models.get(run_id) or [])


def save_checkpoint(run_id: str, thread_id: str, checkpoint_id: str, state: dict[str, Any], parent: Optional[str] = None, metadata: Optional[dict] = None) -> None:
    _checkpoints[run_id] = {
        "run_id": run_id,
        "thread_id": thread_id,
        "checkpoint_id": checkpoint_id,
        "state": state,
        "metadata": metadata or {},
    }


def latest_checkpoint(run_id: str) -> Optional[dict[str, Any]]:
    return _checkpoints.get(run_id)


def metrics(user_id: str) -> dict[str, int]:
    runs = list_runs(user_id)
    return {
        "projects": len(list_projects(user_id)),
        "active_runs": len([r for r in runs if r["status"] in {"QUEUED", "RUNNING", "WAITING", "REWORKING"}]),
        "completed_runs": len([r for r in runs if r["status"] == "COMPLETED"]),
        "artifacts": sum(len(_artifacts.get(r["id"], [])) for r in runs),
        "security_findings": sum(len(_security.get(r["id"], [])) for r in runs),
    }
