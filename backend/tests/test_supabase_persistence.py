"""Comprehensive persistence and database integration tests for SDLC Nexus.

Verifies:
TEST 1: Project creation persistence & return of persistent ID
TEST 2: Managed projects reading from persistent store
TEST 3: Survival of projects across backend restarts (app recreation)
TEST 4: Creating multiple projects and listing all
TEST 5: Pipeline run creation and status transitions
TEST 6: Agent execution metadata persistence
TEST 7: Artifact and results persistence across queries
TEST 8: Transaction rollback on failure (no phantom records, no false success)
TEST 9: Health check connectivity verification
TEST 10: Fail-fast 500 when DATABASE_URL is missing
TEST 11: Service unavailable 503 when connection fails
TEST 12: LangGraph PostgresCheckpointSaver persistence round-trip
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy.exc import OperationalError

from backend.app import create_app
from backend.config.settings import settings
from backend.models.database_models import (
    AgentExecution,
    Artifact,
    PipelineRun,
    Project,
    ReviewResult,
    SecurityFinding,
    TestResult as DBTestResult,
    WorkflowCheckpoint,
)
from backend.orchestration.checkpointing import PostgresCheckpointSaver
from backend.persistence import repositories
from backend.persistence.database import (
    DatabaseConfigurationError,
    DatabaseConnectionError,
    check_database_health,
    reset_engine,
    session_scope,
)


class PersistentDatabaseStore:
    """Simulates persistent PostgreSQL storage across backend instances without SQLite."""

    def __init__(self):
        self.tables = {
            "projects": {},
            "pipeline_runs": {},
            "agent_executions": {},
            "artifacts": {},
            "security_findings": {},
            "test_results": {},
            "review_results": {},
            "workflow_checkpoints": {},
        }
        self.rolled_back = False
        self.committed = False

    def get_table_name(self, obj):
        if isinstance(obj, Project):
            return "projects"
        if isinstance(obj, PipelineRun):
            return "pipeline_runs"
        if isinstance(obj, AgentExecution):
            return "agent_executions"
        if isinstance(obj, Artifact):
            return "artifacts"
        if isinstance(obj, SecurityFinding):
            return "security_findings"
        if isinstance(obj, DBTestResult):
            return "test_results"
        if isinstance(obj, ReviewResult):
            return "review_results"
        if isinstance(obj, WorkflowCheckpoint):
            return "workflow_checkpoints"
        return getattr(obj, "__tablename__", None)


class MockSession:
    """Mock SQLAlchemy Session maintaining transactions against PersistentDatabaseStore."""

    def __init__(self, store: PersistentDatabaseStore):
        self.store = store
        self.pending = []
        self.flushed = []

    def add(self, obj):
        self.pending.append(obj)

    def flush(self):
        for obj in self.pending:
            table = self.store.get_table_name(obj)
            if table:
                self.store.tables[table][obj.id] = obj
                self.flushed.append((table, obj.id))
        self.pending.clear()

    def commit(self):
        self.flush()
        self.flushed.clear()
        self.pending.clear()
        self.store.committed = True

    def rollback(self):
        for table, obj_id in self.flushed:
            if obj_id in self.store.tables.get(table, {}):
                del self.store.tables[table][obj_id]
        self.flushed.clear()
        self.pending.clear()
        self.store.rolled_back = True

    def close(self):
        self.pending.clear()

    def scalar(self, stmt):
        entity = stmt._raw_columns[0].entity_namespace
        table = getattr(entity, "__tablename__", None)
        rows = list(self.store.tables.get(table, {}).values())
        return rows[0] if rows else None

    def scalars(self, stmt):
        entity = stmt._raw_columns[0].entity_namespace
        table = getattr(entity, "__tablename__", None)
        rows = list(self.store.tables.get(table, {}).values())
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        mock_result.first.return_value = rows[0] if rows else None
        return mock_result

    def delete(self, obj):
        table = self.store.get_table_name(obj)
        if table and obj.id in self.store.tables[table]:
            del self.store.tables[table][obj.id]


@pytest.fixture
def persistent_db():
    """Provides a persistent database store that survives across sessions and apps."""
    store = PersistentDatabaseStore()

    @contextmanager
    def _session_scope():
        session = MockSession(store)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    with patch("backend.persistence.repositories.session_scope", _session_scope), \
         patch("backend.persistence.database.session_scope", _session_scope), \
         patch("backend.orchestration.checkpointing.session_scope", _session_scope):
        yield store


# ==============================================================================
# TEST 1 & TEST 2: Project Creation & Managed Projects Read
# ==============================================================================

def test_1_and_2_create_project_and_read(persistent_db):
    """TEST 1: Create project via API -> persists to database with persistent ID.
    TEST 2: List projects -> returns the persisted project.
    """
    app = create_app()
    client = app.test_client()
    headers = {"Authorization": "Bearer demo-token"}

    # TEST 1: Create project
    res = client.post(
        "/api/projects",
        json={"name": "Nexus Core Platform", "idea": "Autonomous SDLC orchestrator"},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.get_json()["data"]
    assert data["name"] == "Nexus Core Platform"
    project_id = data["id"]
    assert project_id is not None
    assert project_id in persistent_db.tables["projects"]
    assert persistent_db.committed is True

    # TEST 2: Read from Managed Projects
    res2 = client.get("/api/projects", headers=headers)
    assert res2.status_code == 200
    projects = res2.get_json()["data"]
    assert len(projects) == 1
    assert projects[0]["id"] == project_id
    assert projects[0]["name"] == "Nexus Core Platform"


# ==============================================================================
# TEST 3: Backend Restart Simulation
# ==============================================================================

def test_3_backend_restart_survives(persistent_db):
    """TEST 3: Restart Flask backend -> project remains persisted in Supabase database."""
    # App instance 1: Creates the project
    app1 = create_app()
    client1 = app1.test_client()
    headers = {"Authorization": "Bearer demo-token"}

    client1.post(
        "/api/projects",
        json={"name": "Restart Survival Project", "idea": "Must persist across restarts"},
        headers=headers,
    )
    assert len(persistent_db.tables["projects"]) == 1

    # App instance 1 destroyed, App instance 2 created (simulating server restart)
    del app1
    del client1

    app2 = create_app()
    client2 = app2.test_client()

    res = client2.get("/api/projects", headers=headers)
    assert res.status_code == 200
    projects = res.get_json()["data"]
    assert len(projects) == 1
    assert projects[0]["name"] == "Restart Survival Project"


# ==============================================================================
# TEST 4: Create Multiple Projects
# ==============================================================================

def test_4_create_multiple_projects(persistent_db):
    """TEST 4: Create a second project -> both appear in list."""
    p1 = repositories.create_project("demo-user", "Project 1", "Idea 1")
    p2 = repositories.create_project("demo-user", "Project 2", "Idea 2")

    listed = repositories.list_projects("demo-user")
    assert len(listed) == 2
    ids = [p["id"] for p in listed]
    assert p1["id"] in ids
    assert p2["id"] in ids


# ==============================================================================
# TEST 5: Pipeline Run Persistence
# ==============================================================================

def test_5_pipeline_run_persistence(persistent_db):
    """TEST 5: Launch an SDLC run -> pipeline_run row exists and status transitions are saved."""
    project = repositories.create_project("demo-user", "Pipeline Project", "Idea")
    run = repositories.create_run(project["id"], "demo-user", "FULL_AUTONOMOUS")

    run_id = run["id"]
    assert run_id in persistent_db.tables["pipeline_runs"]
    assert persistent_db.tables["pipeline_runs"][run_id].status == "QUEUED"
    assert persistent_db.tables["pipeline_runs"][run_id].current_stage == "START"

    # Status transitions
    repositories.update_run(run_id, status="RUNNING", current_stage="DEVELOPER")
    assert persistent_db.tables["pipeline_runs"][run_id].status == "RUNNING"
    assert persistent_db.tables["pipeline_runs"][run_id].current_stage == "DEVELOPER"

    repositories.update_run(run_id, status="COMPLETED", current_stage="FINALIZATION")
    assert persistent_db.tables["pipeline_runs"][run_id].status == "COMPLETED"


# ==============================================================================
# TEST 6: Agent Execution Persistence
# ==============================================================================

def test_6_agent_execution_persistence(persistent_db):
    """TEST 6: Individual agent executions/results are persisted."""
    project = repositories.create_project("demo-user", "Agent Project", "Idea")
    run = repositories.create_run(project["id"], "demo-user", "FULL_AUTONOMOUS")

    exec_id = repositories.add_agent_execution(
        {
            "run_id": run["id"],
            "agent_name": "developer_agent",
            "model": "gemini-3.8-flash",
            "status": "RUNNING",
            "retry_number": 0,
        }
    )
    assert exec_id in persistent_db.tables["agent_executions"]

    repositories.complete_agent_execution(exec_id, "COMPLETED", duration=3.45, token_usage={"prompt": 120, "completion": 450})
    execution = persistent_db.tables["agent_executions"][exec_id]
    assert execution.status == "COMPLETED"
    assert execution.duration == 3.45
    assert execution.token_usage_if_available["prompt"] == 120


# ==============================================================================
# TEST 7: Artifact and QA/Security Results Persistence
# ==============================================================================

def test_7_artifact_and_results_persistence(persistent_db):
    """TEST 7: Artifacts and QA/security results are persisted and reloadable."""
    project = repositories.create_project("demo-user", "Artifact Project", "Idea")
    run = repositories.create_run(project["id"], "demo-user", "FULL_AUTONOMOUS")

    # Artifact persistence
    art_id = repositories.add_artifact(
        run["id"],
        artifact_type="code",
        title="Source Code",
        content='{"files": []}',
        storage_path=f"{run['id']}/source.zip",
        metadata={"file_count": 5},
    )
    artifacts = repositories.list_artifacts(run["id"])
    assert len(artifacts) == 1
    assert artifacts[0]["id"] == art_id
    assert artifacts[0]["storage_path"] == f"{run['id']}/source.zip"

    # Test result persistence
    repositories.add_test_result(run["id"], {"total": 10, "passed": 10, "failed": 0})
    test_res = repositories.latest_test_result(run["id"])
    assert test_res is not None
    assert test_res["passed"] == 10

    # Security finding persistence
    repositories.replace_security_findings(run["id"], [{"category": "injection", "severity": "HIGH", "description": "SQLi vulnerability"}])
    findings = repositories.list_security_findings(run["id"])
    assert len(findings) == 1
    assert findings[0]["category"] == "injection"


# ==============================================================================
# TEST 8: Transaction Rollback on Failure
# ==============================================================================

def test_8_transaction_rollback_on_failure(persistent_db):
    """TEST 8: Forced database error rolls back transaction and caller does not receive false success."""
    project = Project(id="fail-proj", user_id="demo-user", name="Failed Project", idea="Will fail")

    # Simulate transaction failure
    with pytest.raises(ValueError, match="Forced DB write error"):
        with repositories.session_scope() as session:
            session.add(project)
            session.flush()
            raise ValueError("Forced DB write error")

    # Verify rollback was called and object is NOT committed
    assert persistent_db.rolled_back is True
    assert "fail-proj" not in persistent_db.tables["projects"]


# ==============================================================================
# TEST 9: Health Check Connectivity Verification
# ==============================================================================

def test_9_health_check_connectivity():
    """TEST 9: Health check returns healthy when DB connected, unavailable when disconnected."""
    # When DATABASE_URL is not set
    with patch.object(settings, "database_url", ""):
        is_healthy, msg = check_database_health()
        assert is_healthy is False
        assert "not configured" in msg

    # When DATABASE_URL is set and connect succeeds
    with patch.object(settings, "database_url", "postgresql://user:pass@db.supabase.co:5432/postgres"), \
         patch("backend.persistence.database.get_engine") as mock_engine:
        mock_conn = MagicMock()
        mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
        is_healthy, msg = check_database_health()
        assert is_healthy is True
        assert msg == "healthy"


# ==============================================================================
# TEST 10: Fail-Fast 500 when DATABASE_URL is Missing
# ==============================================================================

def test_10_missing_database_url_fail_fast():
    """TEST 10: Fails fast with 500 CONFIGURATION_ERROR if DATABASE_URL is missing."""
    reset_engine()
    with patch.object(settings, "database_url", ""):
        app = create_app()
        client = app.test_client()
        headers = {"Authorization": "Bearer demo-token"}
        res = client.post(
            "/api/projects",
            json={"name": "No DB Project", "idea": "Should fail fast"},
            headers=headers,
        )
        assert res.status_code == 500
        payload = res.get_json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "CONFIGURATION_ERROR"


# ==============================================================================
# TEST 11: 503 SERVICE_UNAVAILABLE on Connection Failure
# ==============================================================================

def test_11_database_connection_failure_returns_503():
    """TEST 11: Returns 503 SERVICE_UNAVAILABLE when database connection fails."""
    app = create_app()
    client = app.test_client()
    headers = {"Authorization": "Bearer demo-token"}

    with patch("backend.persistence.repositories.session_scope") as mock_scope:
        mock_scope.side_effect = OperationalError("connection refused", {}, Exception())
        res = client.post(
            "/api/projects",
            json={"name": "Down DB Project", "idea": "Should return 503"},
            headers=headers,
        )
        assert res.status_code == 503
        payload = res.get_json()
        assert payload["success"] is False
        assert payload["error"]["code"] == "SERVICE_UNAVAILABLE"


# ==============================================================================
# TEST 12: LangGraph PostgresCheckpointSaver Persistence
# ==============================================================================

def test_12_langgraph_postgres_checkpointer(persistent_db):
    """TEST 12: LangGraph PostgresCheckpointSaver persists and restores state via PostgreSQL."""
    saver = PostgresCheckpointSaver()

    config = {"configurable": {"thread_id": "test-thread-42", "checkpoint_ns": ""}}
    checkpoint = {
        "v": 1,
        "id": "chk-001",
        "ts": "2026-09-19T10:00:00Z",
        "channel_values": {"current_stage": "DEVELOPER", "files": [{"path": "app.py"}]},
        "channel_versions": {},
        "versions_seen": {},
    }
    metadata = {"source": "developer_node", "step": 1}

    # Save checkpoint to PostgreSQL
    saved_config = saver.put(config, checkpoint, metadata, {})
    assert any(c.thread_id == "test-thread-42" for c in persistent_db.tables["workflow_checkpoints"].values())

    # Retrieve checkpoint tuple from PostgreSQL
    retrieved = saver.get_tuple({"configurable": {"thread_id": "test-thread-42"}})
    assert retrieved is not None
    assert retrieved.checkpoint["channel_values"]["current_stage"] == "DEVELOPER"
    assert retrieved.metadata["step"] == 1
