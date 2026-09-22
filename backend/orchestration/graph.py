from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from backend.orchestration import nodes
from backend.orchestration.checkpointing import get_checkpoint_saver
from backend.orchestration.routing import (
    after_architecture,
    after_developer,
    after_qa,
    after_requirements,
    after_review,
    after_security,
    after_start,
    after_visual,
)
from backend.orchestration.state import ProjectState
from backend.persistence import repositories
from backend.models.schemas import new_id
from backend.utils.logging import logger

_compiled = None


def build_graph():
    builder = StateGraph(ProjectState)
    builder.add_node("requirements_node", nodes.requirements_node)
    builder.add_node("architecture_node", nodes.architecture_node)
    builder.add_node("visual_architecture_node", nodes.visual_architecture_node)
    builder.add_node("developer_node", nodes.developer_node)
    builder.add_node("security_node", nodes.security_node)
    builder.add_node("qa_node", nodes.qa_node)
    builder.add_node("review_node", nodes.review_node)
    builder.add_node("model_comparison_node", nodes.model_comparison_node)
    builder.add_node("finalization_node", nodes.finalization_node)

    builder.add_conditional_edges(
        START,
        after_start,
        {
            "requirements_node": "requirements_node",
            "architecture_node": "architecture_node",
            "visual_architecture_node": "visual_architecture_node",
            "developer_node": "developer_node",
            "security_node": "security_node",
            "qa_node": "qa_node",
            "review_node": "review_node",
            "model_comparison_node": "model_comparison_node",
            "finalization_node": "finalization_node",
        },
    )
    builder.add_conditional_edges("requirements_node", after_requirements, {"architecture_node": "architecture_node", "__end__": END})
    builder.add_conditional_edges("architecture_node", after_architecture, {"visual_architecture_node": "visual_architecture_node", "__end__": END})
    builder.add_conditional_edges("visual_architecture_node", after_visual, {"developer_node": "developer_node", "__end__": END})
    builder.add_conditional_edges("developer_node", after_developer, {"security_node": "security_node", "__end__": END})
    builder.add_conditional_edges(
        "security_node",
        after_security,
        {"developer_node": "developer_node", "qa_node": "qa_node", "finalization_node": "finalization_node", "__end__": END},
    )
    builder.add_conditional_edges(
        "qa_node",
        after_qa,
        {"developer_node": "developer_node", "review_node": "review_node", "finalization_node": "finalization_node", "__end__": END},
    )
    builder.add_conditional_edges(
        "review_node",
        after_review,
        {"developer_node": "developer_node", "finalization_node": "finalization_node"},
    )
    builder.add_edge("model_comparison_node", END)
    builder.add_edge("finalization_node", END)
    return builder.compile(checkpointer=get_checkpoint_saver())


def get_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled


def persist_checkpoint(run_id: str, state: dict[str, Any]) -> None:
    repositories.save_checkpoint(run_id, run_id, new_id(), state)


def invoke_workflow(state: dict[str, Any]) -> dict[str, Any]:
    graph = get_graph()
    config = {"configurable": {"thread_id": state["run_id"]}}
    result = graph.invoke(state, config)
    persist_checkpoint(state["run_id"], dict(result))
    return dict(result)


def resume_workflow(run_id: str, updates: dict[str, Any] | None = None) -> dict[str, Any]:
    graph = get_graph()
    config = {"configurable": {"thread_id": run_id}}
    merged: dict[str, Any] = {}
    try:
        snapshot = graph.get_state(config)
        if snapshot and snapshot.values:
            merged = dict(snapshot.values)
    except Exception as exc:
        logger.warning(f"Could not load state snapshot from graph: {exc}")
    if not merged:
        stored = repositories.latest_checkpoint(run_id)
        if stored:
            merged = stored.get("state") or {}
    if updates:
        merged.update(updates)
    result = graph.invoke(merged, config)
    persist_checkpoint(run_id, dict(result))
    return dict(result)
