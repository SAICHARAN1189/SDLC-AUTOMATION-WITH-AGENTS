# SDLC Nexus: SDLC Automation with Multi-Agent Systems

An enterprise-grade autonomous Software Development Lifecycle (SDLC) platform orchestrated by intelligent AI agents using **LangGraph**, **Flask**, and **React 19**.

---

## 🌟 Overview

SDLC Nexus automates end-to-end software development phases—from requirements analysis to deployment—through specialized, cooperative autonomous agents. Each agent handles a distinct phase of the SDLC, streaming real-time status and logs via Server-Sent Events (SSE) while persisting artifacts, audit logs, and metrics.

### Key Capabilities
- **Multi-Agent Orchestration**: Managed agent state workflows built on LangGraph.
- **Full SDLC Coverage**:
  - 📋 **Requirements Agent**: Generates PRDs, user stories, and acceptance criteria.
  - 🏗️ **Architecture Agent**: Designs system diagrams, API specs, and database schemas.
  - 💻 **Development Agent**: Generates production-ready code, modules, and project scaffolds.
  - 🔍 **Review Agent**: Conducts automated code quality and standards reviews.
  - 🛡️ **Security Agent**: Scans for vulnerabilities, OWASP compliance, and security postures.
  - 🧪 **QA Agent**: Builds automated test suites and reports test coverage.
  - 🚀 **DevOps / Deployment Agent**: Generates Dockerfiles, CI/CD pipelines, and infrastructure manifests.
- **Interactive Visual Canvas**: Interactive DAG and pipeline graph powered by `@xyflow/react`.
- **Real-Time Streaming**: Live agent token streaming and execution logs via Server-Sent Events (SSE).
- **Extensible LLM Providers**: Powered by Groq / LLM backends with resilience and retry policies.

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────┐
│               Frontend (React 19 + Vite)               │
│  - Pipeline Visualizer (React Flow / XYFlow)           │
│  - Real-Time Execution Logs (SSE)                      │
│  - Artifact Viewer & Markdown / Mermaid Rendering      │
└───────────────────────────▲────────────────────────────┘
                            │ REST / SSE
┌───────────────────────────▼────────────────────────────┐
│                  Backend (Flask API)                   │
│  - Blueprints: Agents, Runs, Artifacts, Security, QA   │
│  - LangGraph State Machine & Checkpointing             │
│  - SQLAlchemy ORM & Database Layer                     │
└───────────────────────────▲────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                    LLM Services                        │
│  - Groq API / Open-Source LLMs (Llama 3, Mixtral, etc.)│
└────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
SDLC-AUTOMATION-WITH-AGENTS/
├── backend/
│   ├── agents/            # Individual agent implementations (dev, qa, sec, etc.)
│   ├── api/               # Flask blueprints and endpoints
│   ├── config/            # Pydantic environment and app configuration
│   ├── llm/               # LLM client abstractions (Groq, etc.)
│   ├── migrations/        # Alembic database migration scripts
│   ├── models/            # SQLAlchemy database models
│   ├── orchestration/     # LangGraph workflows and state management
│   ├── persistence/       # DB session and persistence utilities
│   ├── tools/             # Agent tools and integrations
│   ├── utils/             # Helper utilities and validators
│   ├── app.py             # Flask application entrypoint
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── src/               # React components, pages, hooks, state
│   ├── index.html         # Web application entry point
│   ├── package.json       # Node.js dependencies
│   ├── tailwind.config.js # Tailwind CSS configuration
│   └── vite.config.ts     # Vite build and dev configuration
├── .env.example           # Example environment variables
├── .gitignore             # Git ignore configuration
└── README.md              # Project documentation
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Groq API Key (or supported LLM provider)

### 1. Environment Setup

Copy `.env.example` to `.env` in the root (and configure backend/frontend as required):
```bash
cp .env.example .env
```

Set your API keys:
```env
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=sqlite:///sdlc.db  # or postgresql://...
SECRET_KEY=your_secret_key
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
python app.py
```
Backend will be running at: `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```
Frontend will be running at: `http://localhost:5173`

---

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest -v
```

### Frontend End-to-End Tests
```bash
cd frontend
npm run test
```

---

## 📄 License
This project is licensed under the MIT License.
