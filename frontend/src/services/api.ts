import type {
  AgentIdentity,
  ApiResponse,
  ArtifactItem,
  HealthStatus,
  AppRunResult,
  ModelComparisonOutput,
  PipelineRun,
  Project,
  ReviewOutput,
  SecurityOutput,
  TestOutput,
  WorkflowEvent,
} from "../types";

const TOKEN_KEY = "sdlc_nexus_token";

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || "demo-token";
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
      ...(init.headers || {}),
    },
  });

  if (!response.ok && response.status === 401) {
    // Demo fallback: keep going with local demo token
  }

  const payload = (await response.json()) as ApiResponse<T>;
  if (!payload.success) {
    throw new Error(payload.error?.message || "Request failed");
  }
  return payload.data;
}

// Projects API
export async function getProjects(): Promise<Project[]> {
  return api<Project[]>("/api/projects");
}

export async function getProject(id: string): Promise<Project> {
  return api<Project>(`/api/projects/${id}`);
}

export async function createProject(data: { name: string; idea: string }): Promise<Project> {
  return api<Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// Runs API
export async function createRun(
  projectId: string,
  options: {
    execution_mode?: "AUTONOMOUS" | "STEP_BY_STEP";
    stage?: string;
    demo_mode?: boolean;
    primary_model?: string;
    security_max_retries?: number;
    qa_max_retries?: number;
    review_max_retries?: number;
  } = {}
): Promise<PipelineRun> {
  return api<PipelineRun>(`/api/projects/${projectId}/runs`, {
    method: "POST",
    body: JSON.stringify(options),
  });
}

export async function getRun(runId: string): Promise<PipelineRun> {
  return api<PipelineRun>(`/api/runs/${runId}`);
}

export async function stopRun(runId: string): Promise<{ status: string }> {
  return api<{ status: string }>(`/api/runs/${runId}/stop`, {
    method: "POST",
  });
}

export async function getRunEvents(runId: string): Promise<WorkflowEvent[]> {
  return api<WorkflowEvent[]>(`/api/runs/${runId}/events`);
}

export async function getRunArtifacts(runId: string): Promise<ArtifactItem[]> {
  return api<ArtifactItem[]>(`/api/runs/${runId}/artifacts`);
}

// Specialized Centers API
export interface CentralSecurityOverview {
  summary: {
    total_projects: number;
    total_scans: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    resolved: number;
    open: number;
  };
  projects: Array<{
    project_id: string;
    project_name: string;
    description: string;
    total_runs: number;
    latest_run_id: string | null;
    overall_status: string;
    findings_count: number;
    severity_summary: { critical: number; high: number; medium: number; low: number };
    last_scanned_at: string | null;
  }>;
  findings: Array<{
    id: string;
    project_id: string;
    project_name: string;
    run_id: string;
    category: string;
    severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
    description: string;
    evidence: string;
    remediation: string;
    affected_file: string;
    affected_line: number;
    status: string;
    source: string;
    caused_rework: boolean;
  }>;
}

export async function getCentralSecurityOverview(projectId?: string): Promise<CentralSecurityOverview | null> {
  try {
    const query = projectId ? `?project_id=${projectId}` : "";
    return await api<CentralSecurityOverview>(`/api/security${query}`);
  } catch {
    return null;
  }
}

export async function getSecurityReport(runId: string): Promise<SecurityOutput | null> {
  try {
    return await api<SecurityOutput>(`/api/security/${runId}`);
  } catch {
    return null;
  }
}

export async function getQAReport(runId: string): Promise<TestOutput | null> {
  try {
    return await api<TestOutput>(`/api/tests/${runId}`);
  } catch {
    return null;
  }
}

export async function getReviewReport(runId: string): Promise<ReviewOutput | null> {
  try {
    return await api<ReviewOutput>(`/api/review/${runId}`);
  } catch {
    return null;
  }
}

export async function getModelComparison(runId: string): Promise<ModelComparisonOutput | null> {
  try {
    return await api<ModelComparisonOutput>(`/api/models/${runId}`);
  } catch {
    return null;
  }
}

// Agents API
export async function getAgents(): Promise<AgentIdentity[]> {
  return api<AgentIdentity[]>("/api/agents");
}

export async function runAgent(agentName: string, payload: Record<string, unknown>): Promise<unknown> {
  return api<unknown>(`/api/agents/${agentName}/run`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export const runSingleAgent = runAgent;

// Continue / Step Run API
export async function continueRun(
  runId: string,
  requestedStage?: string
): Promise<{ state: Record<string, unknown> }> {
  return api<{ state: Record<string, unknown> }>(`/api/runs/${runId}/continue`, {
    method: "POST",
    body: JSON.stringify({ requested_stage: requestedStage }),
  });
}

// Manual Intervention API
export async function submitIntervention(
  runId: string,
  data: {
    action: "OVERRIDE" | "REWORK" | "COMPLETE";
    requested_stage?: string;
    feedback?: string;
  }
): Promise<{ status: string; message: string }> {
  return api<{ status: string; message: string }>(`/api/runs/${runId}/intervention`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// Health API
export async function getHealth(): Promise<HealthStatus> {
  return api<HealthStatus>("/api/health");
}

// SSE Subscription
export function subscribeToRunEvents(
  runId: string,
  onEvent: (event: WorkflowEvent) => void,
  onError?: (err: Event) => void
): () => void {
  const token = getToken();
  const url = `/api/runs/${runId}/stream?token=${encodeURIComponent(token)}`;
  const eventSource = new EventSource(url);
  let closed = false;
  let lastErrorTime = 0;

  const handleMessage = (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data);
      if (data && (data.event_type || data.id || data.event_id)) {
        onEvent(data as WorkflowEvent);
        if (data.event_type === "PIPELINE_COMPLETED" || data.event_type === "PIPELINE_FAILED") {
          closed = true;
          eventSource.close();
        }
      }
    } catch {
      // heartbeats or comments
    }
  };

  eventSource.onmessage = handleMessage;
  eventSource.addEventListener("workflow", handleMessage as EventListener);

  eventSource.onerror = (e) => {
    if (closed) return;
    const now = Date.now();
    // Rate limit onError callbacks to at most once every 5 seconds
    if (onError && now - lastErrorTime > 5000) {
      lastErrorTime = now;
      onError(e);
    }
  };

  return () => {
    closed = true;
    eventSource.removeEventListener("workflow", handleMessage as EventListener);
    eventSource.close();
  };
}

// App Runner & Codebase Live Execution API
export async function startApp(
  runId: string,
  files?: { path: string; content: string }[]
): Promise<AppRunResult> {
  return api<AppRunResult>(`/api/runs/${runId}/app/start`, {
    method: "POST",
    body: JSON.stringify({ files }),
  });
}

export async function stopApp(
  runId: string
): Promise<{ success: boolean; status: string; message: string }> {
  return api<{ success: boolean; status: string; message: string }>(
    `/api/runs/${runId}/app/stop`,
    { method: "POST" }
  );
}

export async function getAppStatus(runId: string): Promise<AppRunResult> {
  return api<AppRunResult>(`/api/runs/${runId}/app/status`);
}

