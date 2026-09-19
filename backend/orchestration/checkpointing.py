"""PostgreSQL-backed durable checkpointer for LangGraph and Supabase.

Persists LangGraph execution checkpoints and state tuples directly into
the Supabase PostgreSQL workflow_checkpoints table, ensuring SDLC runs
survive process restarts without loss of state.
"""

from __future__ import annotations

import base64
from collections import defaultdict
from typing import Any, Iterator, Optional, Sequence

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_metadata,
)
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.base import SerializerProtocol
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from sqlalchemy import select

from backend.config.settings import settings
from backend.models.database_models import WorkflowCheckpoint
from backend.models.schemas import new_id
from backend.persistence.database import database_available, session_scope
from backend.utils.logging import logger

memory_checkpointer = InMemorySaver()


class PostgresCheckpointSaver(BaseCheckpointSaver[str]):
    """Persistent checkpointer that persists LangGraph state to Supabase PostgreSQL."""

    def __init__(self, serde: Optional[SerializerProtocol] = None):
        super().__init__(serde=serde or JsonPlusSerializer())
        self.writes: dict[tuple[str, str, str], dict[tuple[str, int], tuple[str, str, tuple[str, bytes], str]]] = defaultdict(dict)

    def get_tuple(self, config: dict[str, Any]) -> Optional[CheckpointTuple]:
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        if not thread_id:
            return None
        checkpoint_id = configurable.get("checkpoint_id")
        checkpoint_ns = configurable.get("checkpoint_ns", "")

        try:
            with session_scope() as session:
                stmt = select(WorkflowCheckpoint).where(WorkflowCheckpoint.thread_id == str(thread_id))
                if checkpoint_id:
                    stmt = stmt.where(WorkflowCheckpoint.checkpoint_id == str(checkpoint_id))
                else:
                    stmt = stmt.order_by(WorkflowCheckpoint.created_at.desc())
                row = session.scalars(stmt).first()
                if not row:
                    return None

                state_json = row.state_json or {}
                if "_serde_data" in state_json and "_serde_type" in state_json:
                    raw_bytes = base64.b64decode(state_json["_serde_data"].encode("ascii"))
                    checkpoint = self.serde.loads_typed((state_json["_serde_type"], raw_bytes))
                else:
                    checkpoint = state_json

                if isinstance(checkpoint, dict) and "v" not in checkpoint:
                    channel_vals = {k: v for k, v in checkpoint.items() if not k.startswith("_serde_")}
                    checkpoint = {
                        "v": 1,
                        "id": str(row.checkpoint_id),
                        "ts": row.created_at.isoformat() if row.created_at else "",
                        "channel_values": channel_vals,
                        "channel_versions": {k: 1 for k in channel_vals},
                        "versions_seen": {},
                        "pending_sends": [],
                    }

                meta_json = row.metadata_json or {}
                if "_serde_data" in meta_json and "_serde_type" in meta_json:
                    meta_bytes = base64.b64decode(meta_json["_serde_data"].encode("ascii"))
                    metadata = self.serde.loads_typed((meta_json["_serde_type"], meta_bytes))
                else:
                    metadata = dict(meta_json)

                if isinstance(metadata, dict):
                    if "step" not in metadata:
                        metadata["step"] = 1
                    if "source" not in metadata:
                        metadata["source"] = "loop"
                    if "writes" not in metadata:
                        metadata["writes"] = {}
                    if "parents" not in metadata:
                        metadata["parents"] = {}

                parent_config = None
                if row.parent_checkpoint_id:
                    parent_config = {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": row.parent_checkpoint_id,
                        }
                    }

                outer_key = (str(thread_id), checkpoint_ns, row.checkpoint_id)
                pending_writes = [
                    (id_, c, self.serde.loads_typed((t, v)))
                    for id_, c, (t, v), _ in self.writes.get(outer_key, {}).values()
                ]

                return CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": row.checkpoint_id,
                        }
                    },
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config=parent_config,
                    pending_writes=pending_writes,
                )
        except Exception as exc:
            logger.warning(f"[CHECKPOINT] Failed to load checkpoint from PostgreSQL: {type(exc).__name__}")
            return None

    def list(
        self,
        config: Optional[dict[str, Any]],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        if not config:
            return
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return
        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")

        try:
            with session_scope() as session:
                stmt = (
                    select(WorkflowCheckpoint)
                    .where(WorkflowCheckpoint.thread_id == str(thread_id))
                    .order_by(WorkflowCheckpoint.created_at.desc())
                )
                if limit:
                    stmt = stmt.limit(limit)
                rows = session.scalars(stmt).all()
                for row in rows:
                    state_json = row.state_json or {}
                    if "_serde_data" in state_json and "_serde_type" in state_json:
                        raw_bytes = base64.b64decode(state_json["_serde_data"].encode("ascii"))
                        checkpoint = self.serde.loads_typed((state_json["_serde_type"], raw_bytes))
                    else:
                        checkpoint = state_json

                    if isinstance(checkpoint, dict) and "v" not in checkpoint:
                        channel_vals = {k: v for k, v in checkpoint.items() if not k.startswith("_serde_")}
                        checkpoint = {
                            "v": 1,
                            "id": str(row.checkpoint_id),
                            "ts": row.created_at.isoformat() if row.created_at else "",
                            "channel_values": channel_vals,
                            "channel_versions": {k: 1 for k in channel_vals},
                            "versions_seen": {},
                            "pending_sends": [],
                        }

                    meta_json = row.metadata_json or {}
                    if "_serde_data" in meta_json and "_serde_type" in meta_json:
                        meta_bytes = base64.b64decode(meta_json["_serde_data"].encode("ascii"))
                        metadata = self.serde.loads_typed((meta_json["_serde_type"], meta_bytes))
                    else:
                        metadata = dict(meta_json)

                    if isinstance(metadata, dict):
                        if "step" not in metadata:
                            metadata["step"] = 1
                        if "source" not in metadata:
                            metadata["source"] = "loop"
                        if "writes" not in metadata:
                            metadata["writes"] = {}
                        if "parents" not in metadata:
                            metadata["parents"] = {}

                    yield CheckpointTuple(
                        config={
                            "configurable": {
                                "thread_id": thread_id,
                                "checkpoint_ns": checkpoint_ns,
                                "checkpoint_id": row.checkpoint_id,
                            }
                        },
                        checkpoint=checkpoint,
                        metadata=metadata,
                        parent_config=(
                            {
                                "configurable": {
                                    "thread_id": thread_id,
                                    "checkpoint_ns": checkpoint_ns,
                                    "checkpoint_id": row.parent_checkpoint_id,
                                }
                            }
                            if row.parent_checkpoint_id
                            else None
                        ),
                    )
        except Exception as exc:
            logger.warning(f"[CHECKPOINT] Failed to list checkpoints from PostgreSQL: {type(exc).__name__}")

    def put(
        self,
        config: dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> dict[str, Any]:
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        parent_checkpoint_id = configurable.get("checkpoint_id")
        checkpoint_id = checkpoint["id"]

        type_str, raw_bytes = self.serde.dumps_typed(checkpoint)
        b64_data = base64.b64encode(raw_bytes).decode("ascii")
        meta_type, meta_bytes = self.serde.dumps_typed(get_checkpoint_metadata(config, metadata))
        meta_b64 = base64.b64encode(meta_bytes).decode("ascii")

        channel_values = checkpoint.get("channel_values", {})
        human_readable = {}
        for k, v in channel_values.items():
            if isinstance(v, (str, int, float, bool, list, dict)):
                human_readable[k] = v
            else:
                human_readable[k] = str(v)

        state_payload = {
            **human_readable,
            "_serde_type": type_str,
            "_serde_data": b64_data,
        }
        metadata_payload = {
            **metadata,
            "_serde_type": meta_type,
            "_serde_data": meta_b64,
        }

        try:
            with session_scope() as session:
                from backend.persistence.repositories import _ensure_run_exists

                _ensure_run_exists(session, str(thread_id))
                session.add(
                    WorkflowCheckpoint(
                        id=new_id(),
                        run_id=str(thread_id),
                        thread_id=str(thread_id),
                        checkpoint_id=str(checkpoint_id),
                        parent_checkpoint_id=str(parent_checkpoint_id) if parent_checkpoint_id else None,
                        state_json=state_payload,
                        metadata_json=metadata_payload,
                    )
                )
        except Exception as exc:
            logger.error(f"[CHECKPOINT] Failed to put checkpoint into PostgreSQL: {type(exc).__name__}")
            raise

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    def put_writes(
        self,
        config: dict[str, Any],
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = configurable.get("checkpoint_id")
        outer_key = (str(thread_id), checkpoint_ns, str(checkpoint_id))
        for idx, (c, v) in enumerate(writes):
            t, b = self.serde.dumps_typed(v)
            self.writes[outer_key][(task_id, idx)] = (task_id, c, (t, b), task_path)

    def delete_thread(self, thread_id: str) -> None:
        try:
            with session_scope() as session:
                stmt = select(WorkflowCheckpoint).where(WorkflowCheckpoint.thread_id == str(thread_id))
                rows = session.scalars(stmt).all()
                for row in rows:
                    session.delete(row)
        except Exception as exc:
            logger.warning(f"[CHECKPOINT] Failed to delete thread {thread_id} from PostgreSQL: {type(exc).__name__}")


postgres_checkpointer = PostgresCheckpointSaver()


def get_checkpoint_saver() -> BaseCheckpointSaver:
    """Return the appropriate checkpoint saver based on database availability."""
    if settings.normalized_database_url and database_available():
        return postgres_checkpointer
    return memory_checkpointer
