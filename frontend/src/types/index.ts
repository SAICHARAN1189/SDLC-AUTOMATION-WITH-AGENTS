export type ApiResponse<T> = {
  success: boolean;
  data: T;
  error: { code: string; message: string; details: Record<string, unknown> } | null;
};

export type Project = {
  id: string;
  user_id?: string;
  name: string;
  idea: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  runs?: PipelineRun[];
};

export type StageName =
  | "REQUIREMENTS"
  | "ARCHITECTURE"
  | "VISUAL_ARCHITECTURE"
  | "DEVELOPMENT"
  | "SECURITY"
  | "QA"
  | "REVIEW"
  | "MODEL_COMPARISON"
  | "FINALIZATION";

export type StageStatus =
  | "QUEUED"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "WAITING"
  | "REWORKING"
  | "MANUAL_INTERVENTION_REQUIRED";

export type PipelineRun = {
  id: string;
  project_id: string;
  user_id?: string;
  execution_mode: "AUTONOMOUS" | "STEP_BY_STEP";
  status: "PENDING" | "RUNNING" | "WAITING" | "COMPLETED" | "FAILED" | "MANUAL_INTERVENTION_REQUIRED" | "STOPPED";
  current_stage: StageName;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  state?: Record<string, unknown>;
  primary_model?: string;
  events?: WorkflowEvent[];
};

export type WorkflowEvent = {
  id?: string;
  event_id?: string;
  run_id: string;
  timestamp: string;
  stage: string;
  agent?: string;
  event_type:
    | "PIPELINE_STARTED"
    | "PIPELINE_COMPLETED"
    | "PIPELINE_FAILED"
    | "AGENT_STARTED"
    | "AGENT_COMPLETED"
    | "AGENT_FAILED"
    | "FEEDBACK_CREATED"
    | "REWORK_STARTED"
    | "REWORK_COMPLETED"
    | "SECURITY_FINDINGS_FOUND"
    | "SECURITY_PASSED"
    | "TESTS_STARTED"
    | "TESTS_COMPLETED"
    | "TESTS_FAILED"
    | "TESTS_PASSED"
    | "REVIEW_STARTED"
    | "REVIEW_COMPLETED"
    | "MANUAL_INTERVENTION_REQUIRED";
  status: string;
  message: string;
  metadata?: Record<string, unknown>;
};

export type InterAgentMessage = {
  sender: string;
  receiver: string;
  message_type: "SECURITY_FEEDBACK" | "QA_FEEDBACK" | "REVIEW_FEEDBACK" | "SPEC_HANDOFF" | "APPROVAL";
  severity?: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
  content: string;
  affected_files?: string[];
  recommended_action?: "REWORK" | "PROCEED" | "MANUAL_REVIEW";
  timestamp: string;
};

export type AgentIdentity = {
  name: string;
  display_name: string;
  role: string;
  goal: string;
  instructions: string;
  tools: string[];
  model?: string;
  provider?: string;
  fallbacks?: Array<{ provider: string; model: string }>;
};

export type RequirementsOutput = {
  project_summary: string;
  stakeholders: string[];
  target_users: string[];
  functional_requirements: string[];
  non_functional_requirements: string[];
  user_stories: Array<{ title: string; as_a: string; i_want: string; so_that: string }>;
  acceptance_criteria: string[];
  assumptions: string[];
  constraints: string[];
  dependencies: string[];
  edge_cases: string[];
  risks: string[];
};

export type ArchitectureOutput = {
  architecture_style: string;
  frontend: { framework: string; styling: string; state_management: string };
  backend: { framework: string; api_style: string; runtime: string };
  database: { primary: string; orm: string; schema_strategy: string };
  services: string[];
  modules: Array<{ name: string; responsibility: string; dependencies: string[] }>;
  apis: Array<{ endpoint: string; method: string; description: string }>;
  authentication: string;
  authorization: string;
  data_model: Array<{ entity: string; fields: string[]; relations: string[] }>;
  integrations: string[];
  deployment_architecture: string;
  security_considerations: string[];
  scalability_considerations: string[];
};

export type VisualDiagram = {
  diagram_type: "system_architecture" | "component" | "database_er" | "api_sequence" | "workflow";
  title: string;
  mermaid_code: string;
  nodes?: string[];
  edges?: string[];
  metadata?: Record<string, unknown>;
};

export type VisualArchitectureOutput = {
  diagrams: VisualDiagram[];
};

export type GeneratedFile = {
  path: string;
  content: string;
};

export type CodeOutput = {
  project_structure: string[];
  files: GeneratedFile[];
  dependencies: string[];
  setup_instructions: string[];
  implementation_notes: string[];
  changed_files?: string[];
  change_summary?: string;
};

export type VulnerabilityFinding = {
  id: string;
  category: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  description: string;
  evidence: string;
  affected_file: string;
  affected_line: number;
  remediation: string;
  confidence: number;
  source: "DETERMINISTIC_FINDING" | "LLM_ANALYSIS";
  status?: "OPEN" | "RESOLVED";
  caused_rework?: boolean;
};

export type SecurityOutput = {
  overall_status: "PASS" | "FAIL" | "WARNING";
  severity_summary: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  vulnerabilities: VulnerabilityFinding[];
  recommendations: string[];
  remediation_actions: string[];
  affected_files: string[];
  confidence: number;
  scan_timestamp: string;
  disclaimer?: string;
};

export type TestCaseFailure = {
  test_name: string;
  expected: string;
  actual: string;
  stack_trace: string;
  affected_component: string;
};

export type TestOutput = {
  summary: string;
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  duration: number;
  failures: TestCaseFailure[];
  coverage: number;
  generated_tests: GeneratedFile[];
  recommendations: string[];
  execution_status: "PASSED" | "FAILED";
};

export type ReviewFinding = {
  id: string;
  category: string;
  severity: "BLOCKING" | "WARNING" | "INFO";
  title: string;
  description: string;
  file?: string;
  recommendation: string;
};

export type ReviewOutput = {
  review_status: "APPROVED" | "REJECTED" | "NEEDS_REWORK";
  blocking_issues: string[];
  findings: ReviewFinding[];
  recommendations: string[];
  required_changes: string[];
  summary: string;
};

export type ModelMetric = {
  model: string;
  latency_ms: number;
  output_tokens: number;
  requirement_coverage: number;
  structure_adherence: number;
  technical_depth: number;
  security_awareness: number;
  raw_response: string;
};

export type ModelComparisonOutput = {
  prompt: string;
  comparisons: ModelMetric[];
  benchmark_timestamp: string;
};

export type ArtifactItem = {
  id: string;
  run_id: string;
  artifact_type:
    | "requirements"
    | "architecture"
    | "visual_architecture"
    | "code"
    | "security_report"
    | "test_report"
    | "review_report"
    | "model_comparison";
  title: string;
  content: string | Record<string, unknown>;
  storage_path?: string;
  metadata?: Record<string, unknown>;
  created_at?: string;
};

export type HealthStatus = {
  status: string;
  database: string;
  llm: string;
  workflow: string;
  timestamp: string;
};
