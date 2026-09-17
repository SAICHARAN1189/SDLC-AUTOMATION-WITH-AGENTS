export type ApiResponse<T> = {
  success: boolean;
  data: T;
  error: { code: string; message: string; details: Record<string, unknown> } | null;
};

export type Project = {
  id: string;
  name: string;
  idea: string;
  status: string;
  created_at?: string;
  runs?: PipelineRun[];
};

export type PipelineRun = {
  id: string;
  project_id: string;
  execution_mode: string;
  status: string;
  current_stage: string;
  started_at?: string;
  state?: Record<string, unknown>;
  events?: WorkflowEvent[];
};

export type WorkflowEvent = {
  id?: string;
  event_id?: string;
  run_id: string;
  timestamp: string;
  stage: string;
  agent?: string;
  event_type: string;
  status: string;
  message: string;
  metadata?: Record<string, unknown>;
};

export type AgentIdentity = {
  name: string;
  display_name: string;
  role: string;
  goal: string;
  instructions: string;
  tools: string[];
};
