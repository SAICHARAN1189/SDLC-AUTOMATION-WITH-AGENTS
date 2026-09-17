# LangGraph Workflow Architecture

## 1. Graph Overview

The entire SDLC pipeline is modeled as a compiled LangGraph `StateGraph(ProjectState)`. The state graph coordinates deterministic and non-deterministic agent nodes, conditional edge routers, retry thresholds, and in-memory/persistent checkpointing.

```
                  ┌─────────┐
                  │  START  │
                  └────┬────┘
                       │ after_start
                       ▼
             ┌────────────────────┐
             │ requirements_node  │
             └─────────┬──────────┘
                       │ after_requirements
                       ▼
             ┌────────────────────┐
             │ architecture_node  │
             └─────────┬──────────┘
                       │ after_architecture
                       ▼
             ┌─────────────────────────┐
             │visual_architecture_node │
             └─────────┬───────────────┘
                       │ after_visual
                       ▼
        ┌──────────> ┌────────────────────┐ <──────────┐
        │            │   developer_node   │            │
        │            └─────────┬──────────┘            │
        │                      │ after_developer       │
        │                      ▼                       │
        │            ┌────────────────────┐            │
        │            │   security_node    │            │
        │            └─────────┬──────────┘            │
        │                      │ after_security        │
        │   Security Rework    ├──────────┐            │
        └─── (if FAIL & retries)          │ (if PASS)  │
                                          ▼            │
                             ┌────────────────────┐    │
                             │      qa_node       │    │
                             └─────────┬──────────┘    │
                                       │ after_qa      │
                    QA Fix Loop        ├──────────┐    │
                    (if FAIL & retries)│          │ (if PASS)
                                                  ▼    │
                                     ┌────────────────────┐
                                     │    review_node     │
                                     └─────────┬──────────┘
                                               │ after_review
                             Review Rework     ├──────────┐
                             (if REJECTED)     │          │ (if APPROVED)
                                               │          ▼
                                               │ ┌───────────────────┐
                                               │ │ finalization_node │
                                               │ └─────────┬─────────┘
                                               │           │
                                               ▼           ▼
                                            ┌─────────────────┐
                                            │       END       │
                                            └─────────────────┘
```

## 2. Graph Nodes

| Node Name | Associated Agent | Primary Responsibilities |
| :--- | :--- | :--- |
| `requirements_node` | `RequirementsAgent` | Derives user stories, functional requirements, and risk factors. |
| `architecture_node` | `ArchitectureAgent` | Selects architecture style, defines modules, and designs data models. |
| `visual_architecture_node` | `VisualArchitectureAgent` | Validates and generates Mermaid diagrams. |
| `developer_node` | `DeveloperAgent` | Generates source code files or applies rework fixes. |
| `security_node` | `SecurityAgent` | Performs dual-layer regex + semantic vulnerability scan. |
| `qa_node` | `QAAgent` | Generates and executes test suites in temporary directory sandbox. |
| `review_node` | `ReviewAgent` | Compares implementation with specifications to issue approval gates. |
| `finalization_node` | Internal orchestrator | Collects deliverables and marks pipeline run as COMPLETED. |
| `model_comparison_node` | `MultiModelAgent` | Measures latency and tokens across Groq models. |

## 3. Conditional Routers

### `after_security(state: ProjectState) -> str`
- If `security_status == "FAIL"` and `retry_count < max_retries`: returns `"developer_node"`
- If `security_status == "FAIL"` and `retry_count >= max_retries`: returns `"finalization_node"` (Status: `MANUAL_INTERVENTION_REQUIRED`)
- If `security_status == "PASS"`: returns `"qa_node"`

### `after_qa(state: ProjectState) -> str`
- If `testing_status == "FAILED"` and `retry_count < max_retries`: returns `"developer_node"`
- If `testing_status == "FAILED"` and `retry_count >= max_retries`: returns `"finalization_node"` (Status: `MANUAL_INTERVENTION_REQUIRED`)
- If `testing_status == "PASSED"`: returns `"review_node"`

### `after_review(state: ProjectState) -> str`
- If `review_status in {"REJECTED", "NEEDS_REWORK"}` and `retry_count < max_retries`: returns `"developer_node"`
- If `review_status == "APPROVED"`: returns `"finalization_node"`
