"""initial sdlc nexus schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", sa.String(128), index=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("idea", sa.Text(), nullable=False),
        sa.Column("status", sa.String(64), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("execution_mode", sa.String(64), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("current_stage", sa.String(64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        sa.Column("config_json", postgresql.JSONB()),
        sa.Column("rework_count", sa.Integer(), server_default="0"),
    )
    op.create_table(
        "workflow_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE")),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("stage", sa.String(64)),
        sa.Column("agent", sa.String(128)),
        sa.Column("event_type", sa.String(64)),
        sa.Column("status", sa.String(64)),
        sa.Column("message", sa.Text()),
        sa.Column("metadata_json", postgresql.JSONB()),
    )
    op.create_table(
        "agent_executions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE")),
        sa.Column("agent_name", sa.String(128)),
        sa.Column("model", sa.String(128)),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration", sa.Float()),
        sa.Column("status", sa.String(64)),
        sa.Column("retry_number", sa.Integer(), server_default="0"),
        sa.Column("token_usage_if_available", postgresql.JSONB()),
    )
    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE")),
        sa.Column("artifact_type", sa.String(64)),
        sa.Column("title", sa.String(255)),
        sa.Column("content", sa.Text()),
        sa.Column("storage_path", sa.String(512)),
        sa.Column("metadata_json", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "security_findings",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE")),
        sa.Column("category", sa.String(128)),
        sa.Column("severity", sa.String(32)),
        sa.Column("description", sa.Text()),
        sa.Column("evidence", sa.Text()),
        sa.Column("remediation", sa.Text()),
        sa.Column("affected_file", sa.String(512)),
        sa.Column("affected_line", sa.Integer()),
        sa.Column("status", sa.String(64)),
        sa.Column("source", sa.String(64)),
        sa.Column("caused_rework", sa.Boolean(), server_default=sa.false()),
    )
    op.create_table(
        "test_results",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE")),
        sa.Column("total", sa.Integer()),
        sa.Column("passed", sa.Integer()),
        sa.Column("failed", sa.Integer()),
        sa.Column("skipped", sa.Integer()),
        sa.Column("duration", sa.Float()),
        sa.Column("output", sa.Text()),
        sa.Column("details_json", postgresql.JSONB()),
    )
    op.create_table(
        "review_results",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE")),
        sa.Column("status", sa.String(64)),
        sa.Column("blocking_issues", postgresql.JSONB()),
        sa.Column("findings", postgresql.JSONB()),
        sa.Column("recommendations", postgresql.JSONB()),
    )
    op.create_table(
        "model_comparisons",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE")),
        sa.Column("model", sa.String(128)),
        sa.Column("latency", sa.Float()),
        sa.Column("output", sa.Text()),
        sa.Column("metrics_json", postgresql.JSONB()),
    )
    op.create_table(
        "workflow_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE")),
        sa.Column("thread_id", sa.String(128)),
        sa.Column("checkpoint_id", sa.String(128)),
        sa.Column("parent_checkpoint_id", sa.String(128)),
        sa.Column("state_json", postgresql.JSONB()),
        sa.Column("metadata_json", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in [
        "workflow_checkpoints",
        "model_comparisons",
        "review_results",
        "test_results",
        "security_findings",
        "artifacts",
        "agent_executions",
        "workflow_events",
        "pipeline_runs",
        "projects",
    ]:
        op.drop_table(table)
