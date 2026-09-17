import type {
  AgentIdentity,
  ApiResponse,
  ArtifactItem,
  HealthStatus,
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
  const url = `/api/runs/${runId}/stream`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onEvent(data);
    } catch {
      // heartbeats or comments
    }
  };

  eventSource.onerror = (e) => {
    if (onError) onError(e);
  };

  return () => {
    eventSource.close();
  };
}
