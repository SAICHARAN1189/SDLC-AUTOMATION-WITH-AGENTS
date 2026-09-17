from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class ExecutionMode(str, Enum):
    FULL_AUTONOMOUS = "FULL_AUTONOMOUS"
    STEP_BY_STEP = "STEP_BY_STEP"
    MODEL_COMPARISON = "MODEL_COMPARISON"


class WorkflowStage(str, Enum):
    START = "START"
    REQUIREMENTS = "REQUIREMENTS"
    ARCHITECTURE = "ARCHITECTURE"
    VISUAL_ARCHITECTURE = "VISUAL_ARCHITECTURE"
    DEVELOPER = "DEVELOPER"
    SECURITY = "SECURITY"
    QA = "QA"
    REVIEW = "REVIEW"
    MODEL_COMPARISON = "MODEL_COMPARISON"
    FINALIZATION = "FINALIZATION"
    END = "END"


class AgentName(str, Enum):
    REQUIREMENTS = "requirements_agent"
    ARCHITECTURE = "architecture_agent"
    VISUAL_ARCHITECTURE = "visual_architecture_agent"
    DEVELOPER = "developer_agent"
    SECURITY = "security_agent"
    QA = "qa_agent"
    REVIEW = "review_agent"
    MULTI_MODEL = "multi_model_agent"
    FINALIZER = "finalizer"


class RunStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    WAITING = "WAITING"
    REWORKING = "REWORKING"
    STOPPED = "STOPPED"
    MANUAL_INTERVENTION_REQUIRED = "MANUAL_INTERVENTION_REQUIRED"


class EventType(str, Enum):
    PIPELINE_STARTED = "PIPELINE_STARTED"
    PIPELINE_COMPLETED = "PIPELINE_COMPLETED"
    PIPELINE_FAILED = "PIPELINE_FAILED"
    AGENT_STARTED = "AGENT_STARTED"
    AGENT_COMPLETED = "AGENT_COMPLETED"
    AGENT_FAILED = "AGENT_FAILED"
    FEEDBACK_CREATED = "FEEDBACK_CREATED"
    REWORK_STARTED = "REWORK_STARTED"
    REWORK_COMPLETED = "REWORK_COMPLETED"
    SECURITY_FINDINGS_FOUND = "SECURITY_FINDINGS_FOUND"
    SECURITY_PASSED = "SECURITY_PASSED"
    TESTS_STARTED = "TESTS_STARTED"
    TESTS_COMPLETED = "TESTS_COMPLETED"
    TESTS_FAILED = "TESTS_FAILED"
    TESTS_PASSED = "TESTS_PASSED"
    REVIEW_STARTED = "REVIEW_STARTED"
    REVIEW_COMPLETED = "REVIEW_COMPLETED"
    MANUAL_INTERVENTION_REQUIRED = "MANUAL_INTERVENTION_REQUIRED"


class ErrorCategory(str, Enum):
    LLM_ERROR = "LLM_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TOOL_ERROR = "TOOL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    AUTH_ERROR = "AUTH_ERROR"
    SECURITY_ERROR = "SECURITY_ERROR"
    TEST_ERROR = "TEST_ERROR"
    WORKFLOW_ERROR = "WORKFLOW_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"


class GateStatus(str, Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"
    REWORK = "REWORK"
    BLOCKED = "BLOCKED"


class DeveloperMode(str, Enum):
    INITIAL_IMPLEMENTATION = "INITIAL_IMPLEMENTATION"
    SECURITY_REWORK = "SECURITY_REWORK"
    QA_REWORK = "QA_REWORK"
    REVIEW_REWORK = "REVIEW_REWORK"


class FindingSource(str, Enum):
    DETERMINISTIC_FINDING = "DETERMINISTIC_FINDING"
    LLM_ANALYSIS = "LLM_ANALYSIS"


class AgentMessage(BaseModel):
    sender: str
    receiver: str
    message_type: str
    severity: Optional[str] = None
    content: str
    affected_files: List[str] = Field(default_factory=list)
    recommended_action: Optional[str] = None
    timestamp: datetime = Field(default_factory=utc_now)


class WorkflowEvent(BaseModel):
    event_id: str = Field(default_factory=new_id)
    run_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    stage: str
    agent: Optional[str] = None
    event_type: str
    status: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowError(BaseModel):
    category: ErrorCategory
    message: str
    stage: Optional[str] = None
    agent: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class RequirementsOutput(BaseModel):
    project_summary: str
    stakeholders: List[str] = Field(default_factory=list)
    target_users: List[str] = Field(default_factory=list)
    functional_requirements: List[str] = Field(default_factory=list)
    non_functional_requirements: List[str] = Field(default_factory=list)
    user_stories: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    edge_cases: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class ArchitectureOutput(BaseModel):
    architecture_style: str
    frontend: str
    backend: str
    database: str
    services: List[str] = Field(default_factory=list)
    modules: List[str] = Field(default_factory=list)
    apis: List[str] = Field(default_factory=list)
    authentication: str
    authorization: str
    data_model: List[str] = Field(default_factory=list)
    integrations: List[str] = Field(default_factory=list)
    deployment_architecture: str
    security_considerations: List[str] = Field(default_factory=list)
    scalability_considerations: List[str] = Field(default_factory=list)


class DiagramNode(BaseModel):
    id: str
    label: str
    kind: str = "component"


class DiagramEdge(BaseModel):
    source: str
    target: str
    label: str = ""


class VisualDiagram(BaseModel):
    diagram_type: str
    title: str
    mermaid_code: str
    nodes: List[DiagramNode] = Field(default_factory=list)
    edges: List[DiagramEdge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    valid: bool = True
    validation_error: Optional[str] = None


class VisualArchitectureOutput(BaseModel):
    diagrams: List[VisualDiagram] = Field(default_factory=list)


class CodeFile(BaseModel):
    path: str
    content: str


class CodeOutput(BaseModel):
    project_structure: List[str] = Field(default_factory=list)
    files: List[CodeFile] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    setup_instructions: List[str] = Field(default_factory=list)
    implementation_notes: str = ""
    changed_files: List[str] = Field(default_factory=list)
    change_summary: str = ""
    mode: DeveloperMode = DeveloperMode.INITIAL_IMPLEMENTATION


class Vulnerability(BaseModel):
    id: str = Field(default_factory=new_id)
    category: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    description: str
    evidence: str
    affected_file: Optional[str] = None
    affected_line: Optional[int] = None
    remediation: str
    confidence: float = 0.7
    source: FindingSource
    caused_rework: bool = False


class SecurityOutput(BaseModel):
    overall_status: GateStatus
    severity_summary: Dict[str, int] = Field(default_factory=dict)
    vulnerabilities: List[Vulnerability] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    remediation_actions: List[str] = Field(default_factory=list)
    affected_files: List[str] = Field(default_factory=list)
    confidence: float = 0.7
    scan_timestamp: datetime = Field(default_factory=utc_now)
    blocking: bool = False
    disclaimer: str = (
        "This is an automated engineering scan combining deterministic pattern "
        "checks and LLM interpretation. It is not a certified security product."
    )


class TestFailure(BaseModel):
    test_name: str
    expected: Optional[str] = None
    actual: Optional[str] = None
    stack_trace: Optional[str] = None
    affected_component: Optional[str] = None


class TestOutput(BaseModel):
    summary: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration: float = 0.0
    failures: List[TestFailure] = Field(default_factory=list)
    coverage: Optional[str] = None
    generated_tests: List[CodeFile] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    executed: bool = False
    overall_status: GateStatus = GateStatus.PENDING


class ReviewFinding(BaseModel):
    severity: Literal["BLOCKING", "WARNING", "INFO"]
    category: str
    description: str
    recommendation: str


class ReviewOutput(BaseModel):
    review_status: GateStatus
    blocking_issues: List[str] = Field(default_factory=list)
    findings: List[ReviewFinding] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    required_changes: List[str] = Field(default_factory=list)
    summary: str
    rework_required: bool = False


class ModelComparisonResult(BaseModel):
    model: str
    latency_ms: float
    output: str
    output_length: int
    requirement_coverage: Optional[float] = None
    structure_adherence: Optional[float] = None
    technical_depth: Optional[float] = None
    security_awareness: Optional[float] = None
    error: Optional[str] = None


class ModelComparisonOutput(BaseModel):
    prompt: str
    results: List[ModelComparisonResult] = Field(default_factory=list)
    notes: str = "Scores are measured heuristics for this prompt, not a universal ranking."


class AgentIdentity(BaseModel):
    name: AgentName
    display_name: str
    role: str
    goal: str
    instructions: str
    tools: List[str] = Field(default_factory=list)
    default_model_slot: Literal["primary", "fast", "reasoning"] = "primary"


class ApiError(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
