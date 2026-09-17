from __future__ import annotations

from flask import Blueprint, request

from backend.api.auth import require_auth
from backend.api.responses import fail, ok
from backend.persistence import repositories
from flask import g

projects_bp = Blueprint("projects", __name__)


@projects_bp.post("/api/projects")
@require_auth
def create_project():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    idea = (body.get("idea") or "").strip()
    if not name or not idea:
        return fail("VALIDATION_ERROR", "name and idea are required")
    project = repositories.create_project(g.user["id"], name, idea)
    return ok(project, 201)


@projects_bp.get("/api/projects")
@require_auth
def list_projects():
    return ok(repositories.list_projects(g.user["id"]))


@projects_bp.get("/api/projects/<project_id>")
@require_auth
def get_project(project_id: str):
    project = repositories.get_project(project_id, g.user["id"])
    if not project:
        return fail("NOT_FOUND", "Project not found", status=404)
    runs = repositories.list_runs(g.user["id"], project_id)
    return ok({**project, "runs": runs})


@projects_bp.patch("/api/projects/<project_id>")
@require_auth
def rename_project(project_id: str):
    body = request.get_json(silent=True) or {}
    try:
        updated = repositories.update_project(project_id, g.user["id"], name=body.get("name"), idea=body.get("idea"), status=body.get("status"))
    except RuntimeError:
        project = repositories.get_project(project_id, g.user["id"])
        if not project:
            return fail("NOT_FOUND", "Project not found", status=404)
        if body.get("name"):
            project["name"] = body["name"]
        return ok(project)
    if not updated:
        return fail("NOT_FOUND", "Project not found", status=404)
    return ok(updated)


@projects_bp.delete("/api/projects/<project_id>")
@require_auth
def delete_project(project_id: str):
    try:
        deleted = repositories.delete_project(project_id, g.user["id"])
    except RuntimeError:
        return fail("DATABASE_ERROR", "Delete requires PostgreSQL", status=400)
    if not deleted:
        return fail("NOT_FOUND", "Project not found", status=404)
    return ok({"deleted": True})
