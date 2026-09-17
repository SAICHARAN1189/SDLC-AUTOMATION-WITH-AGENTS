"""LangGraph in-process checkpointer plus PostgreSQL snapshots.

LangGraph state: live workflow context, routing, retries, agent messages.
PostgreSQL workflow_checkpoints: durable snapshots for resume after process restart.
"""

from langgraph.checkpoint.memory import InMemorySaver

memory_checkpointer = InMemorySaver()
