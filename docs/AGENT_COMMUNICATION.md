# Inter-Agent Communication Architecture

## 1. The Core Principle: State-Mediated Communication

In SDLC Nexus, **agents never invoke each other directly**. Direct peer-to-peer coupling between agents causes unpredictable execution cycles, opaque side-effects, and untracked failure cascades.

Instead, SDLC Nexus enforces **State-Mediated Communication** via LangGraph:

```
┌─────────────────┐
│     Agent A     │
└────────┬────────┘
         │ 1. Produces Strongly-Typed Output
         v
┌─────────────────┐
│ LangGraph State │ <--- Single Source of Truth
└────────┬────────┘
         │ 2. Workflow Evaluates Conditions & Updates Route
         v
┌─────────────────┐
│ Conditional Edge│
└────────┬────────┘
         │ 3. Injects Filtered Context
         v
┌─────────────────┐
│     Agent B     │
└─────────────────┘
```

## 2. Structured Message Schema

Inter-agent events and communications are represented using explicit typed payloads appended to `ProjectState["messages"]` and `ProjectState["workflow_events"]`:

```json
{
  "sender": "security_agent",
  "receiver": "developer_agent",
  "message_type": "SECURITY_FEEDBACK",
  "severity": "HIGH",
  "content": "2 high-severity findings require immediate remediation before QA testing.",
  "affected_files": [
    "backend/api/orders.py"
  ],
  "recommended_action": "REWORK",
  "timestamp": "2026-09-17T18:22:15Z"
}
```

## 3. Communication Sequences

### 3.1 Specification Handoff Sequence
```
Requirements Analyst
       │ (RequirementsOutput)
       ▼
 LangGraph State
       │
       ▼
 System Architect Agent
       │ (ArchitectureOutput)
       ▼
 LangGraph State
       │
       ▼
 Visual Architecture Agent & Developer Agent
```

### 3.2 Security Rework Loop Sequence
When the Security Scanner discovers vulnerabilities:
1. **Security Scanner Agent** scans code with deterministic regex tools + LLM reasoning.
2. If vulnerabilities are classified as `CRITICAL` or `HIGH`, it writes `overall_status = "FAIL"` and remediation steps to state.
3. LangGraph conditional router `after_security` checks retry limit:
   - If `retry_count < security_max_retries`: Route &rarr; `developer_node`
   - If `retry_count >= security_max_retries`: Route &rarr; `finalization_node` with `MANUAL_INTERVENTION_REQUIRED`
4. **Developer Agent** observes `security_report` in its state input.
5. Developer Agent switches to `SECURITY_REWORK` mode, refactors the vulnerable code, increments the retry counter, and produces updated code.
6. LangGraph returns to `security_node` for re-scan.
7. Upon successful pass (`overall_status = "PASS"`), LangGraph transitions to `qa_node`.

### 3.3 QA Fix Loop Sequence
1. **QA Agent** executes pytest suites in a sandboxed temporary directory.
2. If assertions fail, `TestOutput` contains failing test names, expected vs. actual values, and stack traces.
3. LangGraph conditional router `after_qa` evaluates `testing_status`:
   - If `failed > 0` and retries remain: Route &rarr; `developer_node` (Mode: `QA_REWORK`)
   - If tests pass (`failed == 0`): Route &rarr; `review_node`
