# SDLC Nexus: Faculty & Technical Demo Guide

This guide provides a structured 3–5 minute presentation flow to demonstrate the agentic capabilities, LangGraph orchestration, feedback loops, and architectural deliverables of **SDLC Nexus**.

---

## 🎯 Demonstration Objective
Show that SDLC Nexus is **not a simple chatbot** or a series of disconnected LLM calls, but a serious multi-agent engineering platform exhibiting **genuine agentic behavior**:
- Shared typed workflow state
- Goal-directed agent reasoning
- Deterministic tool invocations
- Bounded backward rework loops (`Security -> Developer`, `QA -> Developer`)
- Real-time visibility into inter-agent communication

---

## ⏱️ 3-Minute Walkthrough Script

### Minute 1: The Control Center & Configuration
1. Open the application at `http://localhost:5173`.
2. **Key Talking Point**:
   > *"Notice the AI Software Engineering Control Center design—inspired by Linear and modern engineering observability tools. The cluster status bar confirms Supabase, Groq, and LangGraph connectivity, with our Zero-CrewAI guarantee."*
3. Click **"Explore Faculty Demo Preset"** or **"Start New SDLC Run"**.
4. The preset *"Build a secure online food delivery platform"* will be pre-filled.
5. Click **"Launch SDLC Pipeline"**.

### Minute 2: Live Workflow & Security Rework Loop (The "Wow" Moment)
1. You are automatically routed to `/live?run_id=...`.
2. **Observe the Live Canvas**:
   - **Requirements Analyst** derives user stories and functional requirements.
   - **System Architect** creates the backend, database, and API specifications.
   - **Visual Architect** creates verified Mermaid diagrams.
   - **Developer Agent** scaffolds multi-file source code.
3. **The Agentic Feedback Loop in Action**:
   - **Security Scanner** inspects the code using deterministic regexes + LLM reasoning.
   - A `HIGH` severity SQL injection flaw is identified in `backend/api/orders.py`.
   - **Point to the Communication Timeline**:
     > *"Notice that the Security Agent did not simply print a message. It wrote a structured feedback payload to LangGraph state. LangGraph evaluated its conditional router `after_security` and autonomously routed the workflow backward to the Developer Agent for rework!"*
   - Observe the **Rework Edge** pulse on the React Flow canvas.
   - Developer Agent applies parameterized query remediation and resubmits.
   - Security Scanner rescans and awards `PASS`.

### Minute 3: QA Execution, Review, and Deliverables
1. **QA Test Execution**:
   - QA Agent generates pytest scenarios and executes them in an isolated sandbox.
   - All tests pass, transitioning to the **Code Reviewer Agent**.
2. **Approval Gate**:
   - Senior Code Reviewer evaluates architectural consistency and grants `APPROVED` sign-off.
   - Workflow finalizes deliverables.
3. **Artifact Explorer**:
   - Click **"Artifacts"** in the top navigation.
   - Show the interactive **Requirements PRD**, **Architecture Spec**, live **Mermaid Architecture Diagram**, and multi-file **Source Code Viewer**.
4. **Model Lab**:
   - Click **"Model Lab"** in the sidebar.
   - Show the empirical latency and radar chart comparing `Groq Llama-3.3-70B`, `Mixtral-8x7B`, and `Llama-3.1-8B`.

---

## 🎓 Faculty Q&A Reference Sheet

### Q1: "How do the agents communicate?"
> **Answer**:
> *"Agents never call each other directly. Direct agent-to-agent calls lead to unmanaged state explosions. Instead, Agent A produces structured typed output into the shared LangGraph state. LangGraph evaluates routing rules and passes filtered, relevant context to Agent B. All communications are transparently logged as workflow events."*

### Q2: "What makes this genuinely agentic rather than just an LLM wrapper?"
> **Answer**:
> *"Each agent follows an active autonomous control loop: Observe &rarr; Analyze &rarr; Reason &rarr; Use Deterministic Tools &rarr; Form a Decision &rarr; Produce Structured Output &rarr; Update State. Crucially, downstream agents can reject implementations and force upstream agents into bounded rework cycles until acceptance criteria are satisfied."*

### Q3: "Why use LangGraph instead of CrewAI or AutoGen?"
> **Answer**:
> *"CrewAI abstracts away state and control flow into opaque role-play prompts. LangGraph gives us deterministic state machines, explicit graph topologies, typed conditional routing, bounded retry limits, and persistent checkpointing—essential requirements for reliable enterprise software engineering."*

### Q4: "Is this safe to run on production code?"
> **Answer**:
> *"Yes. All code validations and test runners operate inside ephemeral temporary directories. Subprocesses run with stripped credentials (API keys and service role keys are excluded from the child environment) and strict execution timeouts to prevent infinite loops."*
