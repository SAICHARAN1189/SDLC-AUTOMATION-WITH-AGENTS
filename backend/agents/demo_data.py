from __future__ import annotations

from backend.models.schemas import (
    ArchitectureOutput,
    CodeFile,
    CodeOutput,
    DeveloperMode,
    FindingSource,
    GateStatus,
    ModelComparisonOutput,
    ModelComparisonResult,
    RequirementsOutput,
    ReviewFinding,
    ReviewOutput,
    SecurityOutput,
    TestFailure,
    TestOutput,
    VisualArchitectureOutput,
    VisualDiagram,
    Vulnerability,
)


FOOD_IDEA_HINT = "food delivery"


def is_food_demo(idea: str) -> bool:
    return FOOD_IDEA_HINT in (idea or "").lower()


def demo_requirements(idea: str) -> RequirementsOutput:
    return RequirementsOutput(
        project_summary=(
            f"DEMO MODE sample requirements for: {idea}. "
            "This package is deterministic sample output, not live Groq inference."
        ),
        stakeholders=["Customer", "Restaurant partner", "Delivery courier", "Operations admin", "Support agent"],
        target_users=["Hungry customers ordering meals", "Restaurant staff confirming orders", "Couriers completing deliveries"],
        functional_requirements=[
            "Customers can browse restaurants and menus",
            "Customers can place authenticated orders",
            "Payments are authorized before kitchen confirmation",
            "Couriers can update delivery status",
            "Admins can view order audit history",
        ],
        non_functional_requirements=[
            "Order placement p95 under 500ms for cached menus",
            "All customer PII encrypted in transit",
            "Role-based access for admin vs courier vs customer",
            "Availability target 99.5% for order API",
        ],
        user_stories=[
            "As a customer I can place a food order so that I receive a meal",
            "As a courier I can accept a delivery so that I can complete it",
            "As a restaurant I can confirm an order so that kitchen work starts",
        ],
        acceptance_criteria=[
            "Unauthenticated users cannot place orders",
            "Order totals match menu prices plus tax and delivery fee",
            "Status transitions follow placed → confirmed → picked_up → delivered",
            "SQL queries use parameterization",
        ],
        assumptions=["Single metro launch", "Card payments via a provider", "English-only UI for MVP"],
        constraints=["No storing raw card PANs", "Must support demo mode without live payment credentials"],
        dependencies=["Auth provider", "Maps/geocoding", "Payment processor"],
        edge_cases=["Restaurant goes offline mid-order", "Courier cancels after pickup", "Duplicate checkout submissions"],
        risks=["Injection flaws in order queries", "Broken access control on admin routes", "PII leakage in logs"],
    )


def demo_architecture(idea: str) -> ArchitectureOutput:
    return ArchitectureOutput(
        architecture_style="Modular monolith with clear domain modules, ready to extract services later",
        frontend="React + TypeScript customer/courier web clients",
        backend="Python Flask API with domain modules for catalog, orders, delivery, and identity",
        database="PostgreSQL (Supabase) for transactional data",
        services=["Order service module", "Catalog module", "Delivery assignment module", "Notification hooks"],
        modules=["identity", "catalog", "orders", "delivery", "payments"],
        apis=[
            "POST /api/orders",
            "GET /api/restaurants",
            "POST /api/orders/{id}/status",
            "GET /api/admin/orders",
        ],
        authentication="Supabase Auth JWT verified on the API",
        authorization="RBAC: customer, courier, restaurant, admin",
        data_model=["users", "restaurants", "menu_items", "orders", "order_items", "deliveries"],
        integrations=["Payment provider", "Push/email notifications", "Maps"],
        deployment_architecture="React static frontend + Flask API + Supabase PostgreSQL/Auth/Storage",
        security_considerations=[
            "Parameterized SQL only",
            "No secrets in source",
            "Authorize order access by owner or role",
            "Rate-limit order placement",
        ],
        scalability_considerations=["Cache restaurant menus", "Queue delivery assignment", "Horizontal API instances"],
    )


def _diagram(diagram_type: str, title: str, mermaid: str, nodes: list[tuple[str, str]], edges: list[tuple[str, str, str]]) -> VisualDiagram:
    return VisualDiagram(
        diagram_type=diagram_type,
        title=title,
        mermaid_code=mermaid,
        nodes=[{"id": n[0], "label": n[1], "kind": "component"} for n in nodes],
        edges=[{"source": e[0], "target": e[1], "label": e[2]} for e in edges],
        metadata={"demo": True},
        valid=True,
    )


def demo_visuals() -> VisualArchitectureOutput:
    return VisualArchitectureOutput(
        diagrams=[
            _diagram(
                "system",
                "System architecture",
                "flowchart TD\n  U[Customer] --> FE[React Client]\n  FE --> API[Flask API]\n  API --> DB[(PostgreSQL)]\n  API --> AUTH[Supabase Auth]\n  API --> ST[Storage]",
                [("U", "Customer"), ("FE", "React"), ("API", "Flask"), ("DB", "PostgreSQL")],
                [("U", "FE", "uses"), ("FE", "API", "HTTPS"), ("API", "DB", "SQL")],
            ),
            _diagram(
                "component",
                "Component diagram",
                "flowchart LR\n  ID[Identity] --> ORD[Orders]\n  CAT[Catalog] --> ORD\n  ORD --> DEL[Delivery]\n  ORD --> PAY[Payments]",
                [("ID", "Identity"), ("CAT", "Catalog"), ("ORD", "Orders"), ("DEL", "Delivery")],
                [("ID", "ORD", "authz"), ("CAT", "ORD", "menu"), ("ORD", "DEL", "assign")],
            ),
            _diagram(
                "er",
                "Database ER",
                "erDiagram\n  USERS ||--o{ ORDERS : places\n  RESTAURANTS ||--o{ MENU_ITEMS : has\n  ORDERS ||--|{ ORDER_ITEMS : contains\n  ORDERS ||--o| DELIVERIES : fulfills",
                [("USERS", "users"), ("ORDERS", "orders"), ("MENU_ITEMS", "menu_items")],
                [("USERS", "ORDERS", "places"), ("ORDERS", "MENU_ITEMS", "contains")],
            ),
            _diagram(
                "sequence",
                "Place order sequence",
                "sequenceDiagram\n  participant C as Customer\n  participant A as API\n  participant D as Database\n  C->>A: POST /api/orders\n  A->>A: Verify JWT and authorize\n  A->>D: Insert parameterized order\n  D-->>A: order_id\n  A-->>C: 201 Created",
                [("C", "Customer"), ("A", "API"), ("D", "Database")],
                [("C", "A", "POST"), ("A", "D", "insert")],
            ),
            _diagram(
                "workflow",
                "Order workflow",
                "flowchart TD\n  P[Placed] --> C[Confirmed]\n  C --> K[Kitchen]\n  K --> U[Picked up]\n  U --> D[Delivered]",
                [("P", "Placed"), ("C", "Confirmed"), ("D", "Delivered")],
                [("P", "C", ""), ("C", "D", "")],
            ),
        ]
    )


def demo_initial_code() -> CodeOutput:
    files = [
        CodeFile(
            path="app.py",
            content='''"""DEMO MODE generated sample — not live Groq inference."""
from flask import Flask, request, jsonify

app = Flask(__name__)
# Intentionally insecure first pass for the security feedback loop demo.
DB_PASSWORD = "super-secret-db-password"
orders = []

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/orders")
def create_order():
    restaurant = request.json.get("restaurant")
    # Vulnerable pattern: string-formatted query
    query = f"INSERT INTO orders (restaurant) VALUES ('{restaurant}')"
    orders.append({"restaurant": restaurant, "query": query, "status": "placed"})
    return jsonify({"ok": True, "query": query}), 201

@app.get("/admin/orders")
def admin_orders():
    # Missing authorization check
    return jsonify(orders)
''',
        ),
        CodeFile(
            path="orders.py",
            content='''def order_total(items):
    return sum(item["price"] * item.get("qty", 1) for item in items)


def next_status(current):
    flow = ["placed", "confirmed", "picked_up", "delivered"]
    if current not in flow:
        raise ValueError("invalid status")
    idx = flow.index(current)
    if idx == len(flow) - 1:
        return current
    return flow[idx + 1]
''',
        ),
        CodeFile(
            path="requirements.txt",
            content="flask\n",
        ),
        CodeFile(
            path="README.md",
            content="# Food Delivery API (DEMO MODE sample)\n\nThis source is deterministic demo output labeled as DEMO MODE.\n",
        ),
    ]
    return CodeOutput(
        project_structure=[f.path for f in files],
        files=files,
        dependencies=["flask"],
        setup_instructions=["python -m pip install flask", "python app.py"],
        implementation_notes="Initial implementation includes known unsafe patterns for the demo security loop.",
        changed_files=[f.path for f in files],
        change_summary="Created initial Flask order API with intentional security defects for demo rework.",
        mode=DeveloperMode.INITIAL_IMPLEMENTATION,
    )


def demo_secure_code() -> CodeOutput:
    files = [
        CodeFile(
            path="app.py",
            content='''"""DEMO MODE remediations — not live Groq inference."""
import os
from flask import Flask, request, jsonify

app = Flask(__name__)
orders = []
ROLES = {}

def current_user():
    return {"id": request.headers.get("X-User", "anon"), "role": request.headers.get("X-Role", "customer")}

def require_role(*roles):
    user = current_user()
    if user["role"] not in roles:
        return False
    return True

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/orders")
def create_order():
    user = current_user()
    if user["role"] != "customer":
        return jsonify({"error": "forbidden"}), 403
    payload = request.get_json(silent=True) or {}
    restaurant = payload.get("restaurant")
    if not restaurant:
        return jsonify({"error": "restaurant required"}), 400
    # Parameterized query placeholder (no string interpolation)
    query = "INSERT INTO orders (restaurant, user_id) VALUES (%s, %s)"
    params = (restaurant, user["id"])
    order = {"restaurant": restaurant, "user_id": user["id"], "status": "placed", "query": query, "params": params}
    orders.append(order)
    return jsonify({"ok": True, "order": order}), 201

@app.get("/admin/orders")
def admin_orders():
    if not require_role("admin"):
        return jsonify({"error": "forbidden"}), 403
    return jsonify(orders)
''',
        ),
        CodeFile(
            path="orders.py",
            content='''def order_total(items):
    if not items:
        return 0
    total = 0
    for item in items:
        price = item.get("price")
        qty = item.get("qty", 1)
        if price is None or qty < 0:
            raise ValueError("invalid item")
        total += price * qty
    return total


def next_status(current):
    flow = ["placed", "confirmed", "picked_up", "delivered"]
    if current not in flow:
        raise ValueError("invalid status")
    idx = flow.index(current)
    if idx == len(flow) - 1:
        return current
    return flow[idx + 1]
''',
        ),
        CodeFile(
            path="requirements.txt",
            content="flask\n",
        ),
        CodeFile(
            path="README.md",
            content="# Food Delivery API (DEMO MODE remediations)\nSecrets removed. Queries parameterized. Admin route authorized.\n",
        ),
    ]
    return CodeOutput(
        project_structure=[f.path for f in files],
        files=files,
        dependencies=["flask"],
        setup_instructions=["python -m pip install flask"],
        implementation_notes="Removed hardcoded secrets, parameterized SQL, added role checks.",
        changed_files=["app.py", "orders.py", "README.md"],
        change_summary="Security rework: secrets, injection, and missing authorization addressed.",
        mode=DeveloperMode.SECURITY_REWORK,
    )


def demo_tests() -> list[CodeFile]:
    return [
        CodeFile(
            path="test_orders.py",
            content='''from orders import order_total, next_status


def test_order_total():
    assert order_total([{"price": 10, "qty": 2}]) == 20


def test_next_status():
    assert next_status("placed") == "confirmed"


def test_invalid_status():
    try:
        next_status("lost")
        assert False
    except ValueError:
        assert True
''',
        )
    ]


def demo_security_fail() -> SecurityOutput:
    vulns = [
        Vulnerability(
            id="SEC-DEMO-001",
            category="sql_injection",
            severity="HIGH",
            description="Order insert builds SQL with unsanitized user input.",
            evidence="query = f\"INSERT INTO orders (restaurant) VALUES ('{restaurant}')\"",
            affected_file="app.py",
            affected_line=18,
            remediation="Use parameterized queries with bound parameters.",
            confidence=0.95,
            source=FindingSource.DETERMINISTIC_FINDING,
            caused_rework=True,
        ),
        Vulnerability(
            id="SEC-DEMO-002",
            category="hardcoded_secret",
            severity="HIGH",
            description="Database password hardcoded in source.",
            evidence='DB_PASSWORD = "super-secret-db-password"',
            affected_file="app.py",
            affected_line=7,
            remediation="Load secrets from environment variables.",
            confidence=0.99,
            source=FindingSource.DETERMINISTIC_FINDING,
            caused_rework=True,
        ),
        Vulnerability(
            id="SEC-DEMO-003",
            category="broken_authorization",
            severity="HIGH",
            description="Admin order listing has no authorization check.",
            evidence="@app.get(\"/admin/orders\")",
            affected_file="app.py",
            affected_line=23,
            remediation="Enforce admin role before returning order data.",
            confidence=0.8,
            source=FindingSource.LLM_ANALYSIS,
            caused_rework=True,
        ),
    ]
    return SecurityOutput(
        overall_status=GateStatus.FAIL,
        severity_summary={"CRITICAL": 0, "HIGH": 3, "MEDIUM": 0, "LOW": 0},
        vulnerabilities=vulns,
        recommendations=["Parameterize SQL", "Remove secrets", "Add RBAC on admin routes"],
        remediation_actions=["SECURITY_REWORK"],
        affected_files=["app.py"],
        confidence=0.9,
        blocking=True,
    )


def demo_security_pass() -> SecurityOutput:
    return SecurityOutput(
        overall_status=GateStatus.PASS,
        severity_summary={"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
        vulnerabilities=[],
        recommendations=["Keep using parameterized queries", "Add automated secret scanning in CI"],
        remediation_actions=[],
        affected_files=[],
        confidence=0.86,
        blocking=False,
    )


def demo_qa_pass() -> TestOutput:
    tests = demo_tests()
    return TestOutput(
        summary="DEMO MODE: pytest executed against generated tests.",
        total=3,
        passed=3,
        failed=0,
        skipped=0,
        duration=0.12,
        failures=[],
        coverage=None,
        generated_tests=tests,
        recommendations=["Add API contract tests for authorization"],
        executed=True,
        overall_status=GateStatus.PASS,
    )


def demo_qa_fail() -> TestOutput:
    tests = demo_tests()
    return TestOutput(
        summary="DEMO MODE: failing total calculation before developer fix.",
        total=3,
        passed=2,
        failed=1,
        skipped=0,
        duration=0.18,
        failures=[
            TestFailure(
                test_name="test_order_total",
                expected="20",
                actual="None",
                stack_trace="AssertionError: assert None == 20",
                affected_component="orders.py",
            )
        ],
        generated_tests=tests,
        recommendations=["Fix order_total for qty handling"],
        executed=True,
        overall_status=GateStatus.FAIL,
    )


def demo_review_pass() -> ReviewOutput:
    return ReviewOutput(
        review_status=GateStatus.PASS,
        blocking_issues=[],
        findings=[
            ReviewFinding(
                severity="INFO",
                category="maintainability",
                description="Order module is small and testable.",
                recommendation="Extract a repository layer when adding real PostgreSQL.",
            )
        ],
        recommendations=["Add integration tests against PostgreSQL in CI"],
        required_changes=[],
        summary="DEMO MODE review: implementation matches the architecture enough to finalize.",
        rework_required=False,
    )


def demo_model_comparison(prompt: str, models: list[str]) -> ModelComparisonOutput:
    results = []
    for idx, model in enumerate(models):
        text = (
            f"DEMO MODE sample response from {model} for prompt: {prompt[:180]}. "
            "Latency and scores are measured placeholders from the demo runner, not live Groq calls."
        )
        results.append(
            ModelComparisonResult(
                model=model,
                latency_ms=120.0 + idx * 35,
                output=text,
                output_length=len(text),
                requirement_coverage=0.72 + idx * 0.04,
                structure_adherence=0.8,
                technical_depth=0.65 + idx * 0.05,
                security_awareness=0.7 + (0.05 if "120b" in model else 0.0),
            )
        )
    return ModelComparisonOutput(prompt=prompt, results=results)
