# PostgreSQL Database Schema & Migration Guide

## 1. Database Architecture & Alembic Migrations

SDLC Nexus uses SQLAlchemy 2.0 ORM backed by PostgreSQL on Supabase. Schema definitions reside in `backend/models/database_models.py`, managed by Alembic in `backend/migrations/`.

### Migration Commands
```bash
# Apply pending migrations
alembic upgrade head

# Generate a new migration revision after model updates
alembic revision --autogenerate -m "add_table_or_field"
```

## 2. Table Specifications

### `projects`
- `id` (VARCHAR primary key)
- `user_id` (VARCHAR, indexed)
- `name` (VARCHAR)
- `idea` (TEXT)
- `status` (VARCHAR: `ACTIVE`, `ARCHIVED`)
- `created_at` (TIMESTAMP UTC)
- `updated_at` (TIMESTAMP UTC)

### `pipeline_runs`
- `id` (VARCHAR primary key)
- `project_id` (VARCHAR foreign key &rarr; `projects.id`)
- `user_id` (VARCHAR)
- `execution_mode` (VARCHAR: `AUTONOMOUS`, `STEP_BY_STEP`)
- `status` (VARCHAR: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `MANUAL_INTERVENTION_REQUIRED`, `STOPPED`)
- `current_stage` (VARCHAR)
- `started_at` (TIMESTAMP UTC)
- `completed_at` (TIMESTAMP UTC)
- `error_message` (TEXT)

### `workflow_events`
- `id` (VARCHAR primary key)
- `run_id` (VARCHAR, indexed)
- `timestamp` (TIMESTAMP UTC)
- `stage` (VARCHAR)
- `agent` (VARCHAR)
- `event_type` (VARCHAR)
- `status` (VARCHAR)
- `message` (TEXT)
- `metadata_json` (JSONB)

### `agent_executions`
- `id` (VARCHAR primary key)
- `run_id` (VARCHAR)
- `agent_name` (VARCHAR)
- `model` (VARCHAR)
- `started_at` (TIMESTAMP UTC)
- `completed_at` (TIMESTAMP UTC)
- `duration` (FLOAT)
- `status` (VARCHAR)
- `retry_number` (INTEGER)
- `token_usage` (JSONB)

### `artifacts`
- `id` (VARCHAR primary key)
- `run_id` (VARCHAR, indexed)
- `artifact_type` (VARCHAR: `requirements`, `architecture`, `visual_architecture`, `code`, `security_report`, `test_report`, `review_report`, `model_comparison`)
- `title` (VARCHAR)
- `content` (TEXT)
- `storage_path` (VARCHAR)
- `metadata_json` (JSONB)
- `created_at` (TIMESTAMP UTC)

### `security_findings`
- `id` (VARCHAR primary key)
- `run_id` (VARCHAR, indexed)
- `category` (VARCHAR)
- `severity` (VARCHAR: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
- `description` (TEXT)
- `evidence` (TEXT)
- `remediation` (TEXT)
- `affected_file` (VARCHAR)
- `affected_line` (INTEGER)
- `status` (VARCHAR: `OPEN`, `RESOLVED`)

### `test_results`
- `id` (VARCHAR primary key)
- `run_id` (VARCHAR, indexed)
- `total` (INTEGER)
- `passed` (INTEGER)
- `failed` (INTEGER)
- `skipped` (INTEGER)
- `duration` (FLOAT)
- `output` (JSONB)

### `review_results`
- `id` (VARCHAR primary key)
- `run_id` (VARCHAR, indexed)
- `status` (VARCHAR: `APPROVED`, `REJECTED`, `NEEDS_REWORK`)
- `blocking_issues` (JSONB)
- `findings` (JSONB)
- `recommendations` (JSONB)

### `model_comparisons`
- `id` (VARCHAR primary key)
- `run_id` (VARCHAR, indexed)
- `model` (VARCHAR)
- `latency` (FLOAT)
- `output` (TEXT)
- `metrics_json` (JSONB)

## 3. Database vs. LangGraph State

| Property | LangGraph Shared State | Supabase PostgreSQL Database |
| :--- | :--- | :--- |
| **Lifecycle** | Transient execution run | Persistent long-term storage |
| **Purpose** | Inter-agent messaging, routing conditions, retry counters | Projects list, run history, security compliance audits |
| **Checkpointing**| In-memory & short-lived thread state | Versioned checkpoints and historical artifacts |
| **Access Pattern** | In-memory Python dictionary | Indexed SQL queries with foreign keys |
