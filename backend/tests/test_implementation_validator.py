from __future__ import annotations

import pytest

from backend.tools.implementation_validator import validate_implementation


def test_regression_1_frontend_calls_nonexistent_endpoint():
    """Regression 1: Frontend calls an endpoint that does not exist on backend."""
    files = [
        {
            "path": "backend/app.py",
            "content": """
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/tasks")
def get_tasks():
    return []
""",
        },
        {
            "path": "frontend/app.js",
            "content": """
async function decomposeTask(title) {
    const res = await fetch("/api/v1/tasks/decompose", {
        method: "POST",
        body: JSON.stringify({ title })
    });
    return res.json();
}
""",
        },
        {"path": "requirements.txt", "content": "fastapi\nuvicorn\n"},
    ]
    result = validate_implementation(files)
    assert not result.passed
    assert any(
        i.check == "frontend_backend_contract" and "POST /api/v1/tasks/decompose" in i.message
        for i in result.blocking_issues
    )


def test_regression_2_database_initialization_never_invoked():
    """Regression 2: Database models defined but create_all / init_db never invoked on startup."""
    files = [
        {
            "path": "app.py",
            "content": """
from fastapi import FastAPI
from sqlmodel import SQLModel, Field

app = FastAPI()

class Task(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    title: str

@app.get("/tasks")
def get_tasks():
    return []
""",
        },
        {"path": "requirements.txt", "content": "fastapi\nsqlmodel\n"},
    ]
    result = validate_implementation(files)
    assert not result.passed
    assert any(
        i.check == "database_initialization" and "never invoked" in i.message
        for i in result.blocking_issues
    )


def test_regression_3_orm_back_populates_incomplete():
    """Regression 3: ORM back_populates relationship is one-sided and incomplete."""
    files = [
        {
            "path": "app.py",
            "content": """
from fastapi import FastAPI
from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional

app = FastAPI()

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    sub_tasks: List["SubTask"] = Relationship(back_populates="parent")

class SubTask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id")
    # Missing symmetric: parent: Optional[Task] = Relationship(back_populates="sub_tasks")

def init_db():
    SQLModel.metadata.create_all(engine)
init_db()
""",
        },
        {"path": "requirements.txt", "content": "fastapi\nsqlmodel\n"},
    ]
    result = validate_implementation(files)
    assert not result.passed
    assert any(
        i.check == "orm_relationships" and "back_populates='parent'" in i.message
        for i in result.blocking_issues
    )


def test_regression_4_static_frontend_not_served():
    """Regression 4: Static frontend exists but backend does not mount or serve it."""
    files = [
        {
            "path": "app.py",
            "content": """
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/status")
def status():
    return {"status": "ok"}
""",
        },
        {
            "path": "static/index.html",
            "content": "<!DOCTYPE html><html><body><h1>To-Do</h1></body></html>",
        },
        {"path": "requirements.txt", "content": "fastapi\n"},
    ]
    result = validate_implementation(files)
    assert not result.passed
    assert any(
        i.check == "static_frontend_serving" and "backend does not mount or serve" in i.message
        for i in result.blocking_issues
    )


def test_regression_5_mock_decompose_fake_implementation():
    """Regression 5: Required AI feature is replaced by mock_decompose()."""
    files = [
        {
            "path": "app.py",
            "content": """
from fastapi import FastAPI
app = FastAPI()

def mock_decompose(task_title: str):
    return ["Step 1 dummy", "Step 2 dummy"]

@app.post("/api/decompose")
def decompose():
    return mock_decompose("dummy")
""",
        },
        {"path": "requirements.txt", "content": "fastapi\n"},
    ]
    result = validate_implementation(files)
    assert not result.passed
    assert any(
        i.check == "real_functionality" and "mock_decompose" in i.message
        for i in result.blocking_issues
    )


def test_regression_6_unsafe_inner_html():
    """Regression 6: Unsafe dynamic user content rendered with innerHTML."""
    files = [
        {
            "path": "app.py",
            "content": "from fastapi import FastAPI\napp = FastAPI()\n",
        },
        {
            "path": "static/app.js",
            "content": """
function renderTask(task) {
    const el = document.createElement("div");
    el.innerHTML = `<h3>${task.title}</h3>`; // XSS risk
    document.body.appendChild(el);
}
""",
        },
        {"path": "requirements.txt", "content": "fastapi\n"},
    ]
    result = validate_implementation(files)
    assert not result.passed
    assert any(
        i.check == "security_quality" and "innerHTML" in i.message
        for i in result.blocking_issues
    )


def test_regression_7_unjustified_selenium_dependency():
    """Regression 7: Unjustified selenium dependency added to requirements.txt."""
    files = [
        {
            "path": "app.py",
            "content": "from fastapi import FastAPI\napp = FastAPI()\n",
        },
        {
            "path": "requirements.txt",
            "content": "fastapi\nselenium\n",
        },
    ]
    arch = {"architecture_style": "Web API", "database": "SQLite"}
    result = validate_implementation(files, architecture=arch)
    assert not result.passed
    assert any(
        i.check == "dependency_validation" and "selenium" in i.message
        for i in result.blocking_issues
    )


def test_regression_8_rework_drops_existing_files():
    """Regression 8: Rework returns only changed files and drops existing files."""
    existing = [
        {"path": "index.html", "content": "<html></html>"},
        {"path": "style.css", "content": "body {}"},
        {"path": "app.py", "content": "print('old')"},
        {"path": "models.py", "content": "class M: pass"},
    ]
    rework_files = [
        {"path": "models.py", "content": "class M: pass # updated"},
    ]
    result = validate_implementation(rework_files, existing_files=existing, mode="QA_REWORK")
    assert not result.passed
    assert any(
        i.check == "rework_preservation" and "dropped 3 existing project files" in i.message
        for i in result.blocking_issues
    )


def test_regression_9_silent_sqlite_fallback():
    """Regression 9: Architecture specifies PostgreSQL/Supabase, but implementation silently hardcodes SQLite."""
    files = [
        {
            "path": "app.py",
            "content": """
from fastapi import FastAPI
from sqlmodel import create_engine
app = FastAPI()
engine = create_engine("sqlite:///./app.db")
""",
        },
        {"path": "requirements.txt", "content": "fastapi\nsqlmodel\n"},
    ]
    arch = {
        "architecture_style": "FullStack",
        "database": "PostgreSQL (Supabase)",
    }
    result = validate_implementation(files, architecture=arch)
    assert not result.passed
    assert any(
        i.check == "no_silent_sqlite_fallback" and "sqlite:///./app.db" in i.message
        for i in result.blocking_issues
    )


def test_regression_10_startup_instructions_mismatch():
    """Regression 10: Startup instructions specify 'python app.py' when file is at 'backend/app.py'."""
    files = [
        {"path": "backend/app.py", "content": "from fastapi import FastAPI\napp = FastAPI()\n"},
        {"path": "requirements.txt", "content": "fastapi\n"},
    ]
    instructions = ["pip install -r requirements.txt", "python app.py"]
    result = validate_implementation(files, setup_instructions=instructions)
    assert not result.passed
    assert any(
        i.check == "startup_path_validation" and "backend/app.py" in i.message
        for i in result.blocking_issues
    )


def test_valid_coherent_project_passes_all_checks():
    """Verify that a fully coherent, well-implemented project passes all checks with 0 blocking issues."""
    files = [
        {
            "path": "backend/app.py",
            "content": """
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, create_engine
from backend.models import Task, SubTask

app = FastAPI()
db_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/todo")
engine = create_engine(db_url)

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

@app.get("/api/tasks")
def list_tasks():
    return []

@app.post("/api/v1/tasks/decompose")
def decompose_task(payload: dict):
    title = payload.get("title", "")
    # Genuine rule-based breakdown implementation
    steps = [f"Plan {title}", f"Execute {title}", f"Review {title}"]
    return {"steps": steps}

app.mount("/", StaticFiles(directory="static", html=True), name="static")
""",
        },
        {
            "path": "backend/models.py",
            "content": """
from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    sub_tasks: List["SubTask"] = Relationship(back_populates="parent")

class SubTask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    task_id: int = Field(foreign_key="task.id")
    parent: Optional[Task] = Relationship(back_populates="sub_tasks")
""",
        },
        {
            "path": "static/index.html",
            "content": """<!DOCTYPE html>
<html>
<head><title>To-Do</title></head>
<body>
  <h1>To-Do App</h1>
  <script src="/app.js"></script>
</body>
</html>""",
        },
        {
            "path": "static/app.js",
            "content": """
async function decompose(title) {
    const res = await fetch("/api/v1/tasks/decompose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title })
    });
    return res.json();
}

function renderTask(task) {
    const div = document.createElement("div");
    div.textContent = task.title; // Safe textContent
    document.body.appendChild(div);
}
""",
        },
        {
            "path": "requirements.txt",
            "content": "fastapi\nuvicorn\nsqlmodel\npsycopg2-binary\n",
        },
    ]
    arch = {
        "architecture_style": "FullStack Web Application",
        "database": "PostgreSQL (Supabase)",
        "frontend": "Vanilla HTML/JS",
    }
    setup = ["pip install -r requirements.txt", "python backend/app.py"]
    result = validate_implementation(files, architecture=arch, setup_instructions=setup)
    assert result.passed
    assert len(result.blocking_issues) == 0
