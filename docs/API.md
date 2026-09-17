# SDLC Nexus REST & SSE API Reference

## Standard Response Structure

All endpoints return a standardized JSON envelope:

### Success:
```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

### Error:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Project name cannot be empty",
    "details": {}
  }
}
```

---

## 1. Projects API

### `POST /api/projects`
Create a new project specification.
- **Request Body**:
  ```json
  {
    "name": "Nexus Secure Food Delivery",
    "idea": "Build a secure food delivery platform with isolated payment processing..."
  }
  ```
- **Response**: `201 Created` with `Project` record.

### `GET /api/projects`
List all projects belonging to the authenticated user.

### `GET /api/projects/{id}`
Retrieve project details and previous execution runs.

---

## 2. Pipeline Runs API

### `POST /api/projects/{id}/runs`
Launch an autonomous or step-by-step SDLC run.
- **Request Body**:
  ```json
  {
    "execution_mode": "AUTONOMOUS",
    "stage": "REQUIREMENTS"
  }
  ```
- **Response**: `200 OK` with `PipelineRun` record.

### `GET /api/runs/{id}`
Retrieve live pipeline run status and current state snapshot.

### `POST /api/runs/{id}/stop`
Terminate an active pipeline run.

### `GET /api/runs/{id}/events`
List all historical workflow events for the run.

### `GET /api/runs/{id}/artifacts`
Retrieve all produced deliverables (PRD, architecture, diagrams, code, audits).

---

## 3. Real-Time Streaming (SSE)

### `GET /api/runs/{id}/stream`
Server-Sent Events endpoint streaming live state events as they are emitted by LangGraph nodes.
- **Event format**:
  ```
  event: message
  data: {"event_id": "ev-1", "run_id": "...", "stage": "SECURITY", "event_type": "SECURITY_FINDINGS_FOUND", "message": "High severity SQL injection sink detected"}
  ```

---

## 4. Specialized Centers API

### `GET /api/security/{run_id}`
Returns security audit findings, severity breakdown, and rework causation indicators.

### `GET /api/tests/{run_id}`
Returns pytest execution results, coverage metrics, and failure traces.

### `GET /api/review/{run_id}`
Returns code review assessment, blocking issues, and gate sign-off status.

### `GET /api/models/{run_id}`
Returns benchmark comparison results across Groq models.

---

## 5. Agents Registry API

### `GET /api/agents`
List all 8 specialized agents, roles, goals, and assigned tools.

### `POST /api/agents/{agent_name}/run`
Execute a single agent in an isolated test environment.

---

## 6. Health & Diagnostics

### `GET /api/health`
Return cluster status:
```json
{
  "status": "ok",
  "database": "ok",
  "llm": "ok",
  "workflow": "active"
}
```
