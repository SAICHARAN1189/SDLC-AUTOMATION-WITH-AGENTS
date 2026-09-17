# SDLC Nexus System Architecture

## 1. High-Level Overview

SDLC Nexus is an enterprise-grade autonomous Software Development Life Cycle (SDLC) platform that transforms natural-language software requirements into production-ready software deliverables.

```
                         USER / STAKEHOLDER
                                 |
                                 v
                     REACT 19 FRONTEND (SPA)
             [XYFlow DAG, SSE Timeline, Inspector]
                                 |
                                 v REST / SSE (/api)
                         FLASK API GATEWAY
           [Authentication, Endpoints, Streaming SSE]
                                 |
                                 v
                     LANGGRAPH WORKFLOW ENGINE
           ┌───────────────────────────────────────────┐
           │   Shared Typed ProjectState               │
           │   Routing & Conditional Transitions       │
           │   Bounded Feedback & Rework Loops         │
           │   Memory & Persistent Checkpointing       │
           └─────────────────────┬─────────────────────┘
                                 |
        ┌────────────────────────┼────────────────────────┐
        v                        v                        v
Requirements Analyst       System Architect        Developer Agent
  [PRD & Stories]        [Tech Specs & APIs]     [Code Scaffolding]
        |                        |                        |
        |                        v                        v
        |                Visual Architect          ┌──────┴──────┐
        |               [Mermaid Diagrams]         v             v
        |                                       Security         QA
        |                                       Scanner       Engineer
        |                                          |             |
        |                                          └──────┬──────┘
        |                                                 v
        |                                            Code Reviewer
        |                                                 |
        |                                            PASS / FAIL
        |                                                 |
        |                                           Final Deliverables
        |
        └────────────── Multi-Model Comparison Branch
                                 |
                                 v
                           GROQ API INFERENCE
                   [Llama 3.3 70B, Mixtral 8x7B, 8B]
                                 |
                                 v
                       SUPABASE CLUSTER
             [PostgreSQL + Auth + Storage Buckets]
```

## 2. Core Architectural Pillars

### 2.1 Single Orchestration Framework: LangGraph Native
- **Zero CrewAI Principle**: LangGraph is the sole orchestration and workflow state machine framework. No secondary frameworks, redundant abstraction layers, or conflicting agent wrappers exist.
- **StateGraph Architecture**: Every agent corresponds to an explicit execution node in a LangGraph `StateGraph(ProjectState)`.
- **Checkpointing**: Every state update is persisted with `InMemorySaver` and optional database checkpoint snapshots for state recovery and resume.

### 2.2 Shared Typed ProjectState
Agents never call each other directly (e.g. `AgentA.call(AgentB)` is strictly prohibited). Instead, communication occurs via the strongly-typed `ProjectState` schema:
```python
class ProjectState(TypedDict, total=False):
    project_id: str
    run_id: str
    user_id: str
    user_idea: str
    execution_mode: str
    current_stage: str
    current_agent: str
    requirements: dict[str, Any]
    architecture: dict[str, Any]
    visual_architecture: dict[str, Any]
    code: dict[str, Any]
    security_report: dict[str, Any]
    test_report: dict[str, Any]
    review_report: dict[str, Any]
    model_comparison: dict[str, Any]
    messages: list[dict[str, Any]]
    workflow_events: list[dict[str, Any]]
    retry_counts: dict[str, int]
    security_status: str
    testing_status: str
    review_status: str
    final_status: str
    errors: list[dict[str, Any]]
    artifact_ids: list[str]
    timestamps: dict[str, str]
```

### 2.3 Bounded Feedback & Rework Loops
The platform supports three distinct iterative feedback loops:
1. **Security Feedback Loop**: Developer &rarr; Security Scanner. If high/critical findings exist, state is updated with remediation guidance and routed back to Developer Agent (bounded by `security_max_retries`).
2. **QA Feedback Loop**: QA executes tests in an isolated sandbox. If test assertions fail, failures are routed back to Developer Agent for code fixes (bounded by `qa_max_retries`).
3. **Review Feedback Loop**: Senior Code Reviewer compares implementation against requirements and architecture. If blocking discrepancies exist, a rework cycle is triggered (bounded by `review_max_retries`).

### 2.4 Separation of Concerns
- **LangGraph**: Workflow state, transitions, retry counters, and loop logic.
- **Agents**: Perception, engineering reasoning, tool invocation, and structured outputs.
- **Groq LLM**: High-speed, high-quality inference.
- **Python**: Deterministic security regexes, sandboxed pytest execution, Mermaid syntax verification, and file I/O.
- **Flask**: REST endpoints, Server-Sent Events (SSE) broadcasting, and authentication.
- **Supabase**: PostgreSQL database, user authentication, and large artifact storage.
