import React, { useEffect, useState, useCallback } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import {
  Activity,
  AlertOctagon,
  ArrowRight,
  CheckCircle2,
  Cpu,
  FileCode,
  Layers,
  Pause,
  Play,
  RotateCcw,
  ShieldAlert,
  Square,
  TestTube2,
} from "lucide-react";
import { WorkflowCanvas } from "../components/workflow/WorkflowCanvas";
import { AgentInspector } from "../components/agents/AgentInspector";
import { CommunicationTimeline } from "../components/workflow/CommunicationTimeline";
import {
  getRun,
  getRunEvents,
  getAgents,
  stopRun,
  subscribeToRunEvents,
} from "../services/api";
import type {
  AgentIdentity,
  PipelineRun,
  StageName,
  StageStatus,
  WorkflowEvent,
} from "../types";

export const LiveRun: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const runId = searchParams.get("run_id");

  const [run, setRun] = useState<PipelineRun | null>(null);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [agents, setAgents] = useState<Record<string, AgentIdentity>>({});
  const [selectedStageKey, setSelectedStageKey] = useState<string>("developer_node");
  const [loading, setLoading] = useState(true);

  // Rework tracking
  const [securityReworkCount, setSecurityReworkCount] = useState(0);
  const [qaReworkCount, setQaReworkCount] = useState(0);
  const [reviewReworkCount, setReviewReworkCount] = useState(0);

  // Load agent definitions once
  useEffect(() => {
    getAgents()
      .then((list) => {
        const map: Record<string, AgentIdentity> = {};
        list.forEach((a) => {
          map[a.name] = a;
          // map node names as well
          const nodeKey = a.name.replace("_agent", "_node");
          map[nodeKey] = a;
        });
        setAgents(map);
      })
      .catch((e) => console.warn("Failed to load agents registry", e));
  }, []);

  // Fetch initial run data and events
  const fetchRunData = useCallback(async () => {
    if (!runId) return;
    try {
      const [rData, evList] = await Promise.all([
        getRun(runId),
        getRunEvents(runId),
      ]);
      setRun(rData);
      setEvents(evList);

      // Derive rework counts
      let secR = 0;
      let qaR = 0;
      let revR = 0;
      evList.forEach((ev) => {
        if (ev.event_type === "REWORK_STARTED") {
          if (ev.stage === "SECURITY" || ev.message.includes("Security")) secR++;
          if (ev.stage === "QA" || ev.message.includes("QA")) qaR++;
          if (ev.stage === "REVIEW" || ev.message.includes("Review")) revR++;
        }
      });
      setSecurityReworkCount(secR);
      setQaReworkCount(qaR);
      setReviewReworkCount(revR);
    } catch (err) {
      console.warn("Run data fetch warning", err);
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    fetchRunData();
  }, [fetchRunData]);

  // Subscribe to live SSE stream for real-time events
  useEffect(() => {
    if (!runId) return;
    const unsubscribe = subscribeToRunEvents(
      runId,
      (event) => {
        setEvents((prev) => [...prev, event]);

        // Update run state dynamically
        setRun((prev) => {
          if (!prev) return prev;
          let newStatus = prev.status;
          if (event.event_type === "PIPELINE_COMPLETED") newStatus = "COMPLETED";
          if (event.event_type === "PIPELINE_FAILED") newStatus = "FAILED";
          if (event.event_type === "MANUAL_INTERVENTION_REQUIRED")
            newStatus = "MANUAL_INTERVENTION_REQUIRED";

          return {
            ...prev,
            status: newStatus,
            current_stage: (event.stage as StageName) || prev.current_stage,
          };
        });

        // Track rework counts
        if (event.event_type === "REWORK_STARTED") {
          if (event.stage === "SECURITY" || event.message.includes("Security")) {
            setSecurityReworkCount((c) => c + 1);
          } else if (event.stage === "QA" || event.message.includes("QA")) {
            setQaReworkCount((c) => c + 1);
          } else if (event.stage === "REVIEW" || event.message.includes("Review")) {
            setReviewReworkCount((c) => c + 1);
          }
        }
      },
      () => {
        // Fallback polling if SSE disconnects
        fetchRunData();
      }
    );

    return () => unsubscribe();
  }, [runId, fetchRunData]);

  const handleStop = async () => {
    if (!runId) return;
    try {
      await stopRun(runId);
      fetchRunData();
    } catch (e) {
      console.error(e);
    }
  };

  // Selected agent resolution
  const selectedAgent = agents[selectedStageKey] || {
    name: selectedStageKey,
    display_name: selectedStageKey.replace("_node", "").replace("_", " ").toUpperCase(),
    role: "Autonomous SDLC Agent",
    goal: "Execute engineering stage according to requirements and state context.",
    instructions: "Adhere to typed output schemas, invoke deterministic tools, and update LangGraph state.",
    tools: ["file_reader", "state_writer"],
    model: "Groq Llama-3.3-70B",
  };

  if (!runId) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-12 text-center space-y-4">
        <Activity className="w-12 h-12 text-zinc-400 animate-pulse" />
        <div>
          <h2 className="text-base font-semibold text-zinc-200">No Active SDLC Run Selected</h2>
          <p className="text-xs text-zinc-400 mt-1 max-w-md">
            Launch a new run or select an existing pipeline run from the Projects list to enter the live workspace.
          </p>
        </div>
        <button
          onClick={() => navigate("/projects/new")}
          className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs transition-colors cursor-pointer"
        >
          Launch New SDLC Run
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-5rem)] space-y-4">
      {/* Top Header: Run Metadata & Actions */}
      <div className="p-3.5 rounded-lg bg-[#161b22] border border-[#30363d] flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-md bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Activity className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-xs text-zinc-200">RUN-{runId.slice(0, 8)}</span>
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase font-semibold ${
                  run?.status === "RUNNING"
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 animate-pulse"
                    : run?.status === "COMPLETED"
                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                    : run?.status === "FAILED"
                    ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                    : "bg-zinc-800 text-zinc-400"
                }`}
              >
                {run?.status || "INITIALIZING"}
              </span>
              <span className="text-[10px] font-mono text-zinc-400">
                Mode: {run?.execution_mode || "AUTONOMOUS"}
              </span>
            </div>
            <div className="text-[11px] text-zinc-400 font-mono flex items-center gap-2 mt-0.5">
              <span>Current Stage: <strong className="text-zinc-200">{run?.current_stage || "REQUIREMENTS"}</strong></span>
              {(securityReworkCount > 0 || qaReworkCount > 0 || reviewReworkCount > 0) && (
                <span className="text-amber-400 flex items-center gap-1 font-semibold">
                  <RotateCcw className="w-3 h-3" />
                  Reworks: Sec({securityReworkCount}) QA({qaReworkCount}) Rev({reviewReworkCount})
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Quick Links & Control Actions */}
        <div className="flex items-center gap-2">
          <Link
            to={`/artifacts?run_id=${runId}`}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs border border-zinc-700 transition-colors"
          >
            <FileCode className="w-3.5 h-3.5 text-zinc-400" />
            <span>Artifacts</span>
          </Link>

          <Link
            to={`/security?run_id=${runId}`}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs border border-zinc-700 transition-colors"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
            <span>Security</span>
          </Link>

          <Link
            to={`/qa?run_id=${runId}`}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs border border-zinc-700 transition-colors"
          >
            <TestTube2 className="w-3.5 h-3.5 text-sky-400" />
            <span>QA</span>
          </Link>

          <button
            onClick={handleStop}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 text-xs font-medium transition-colors cursor-pointer"
          >
            <Square className="w-3 h-3 fill-current" />
            <span>Stop Run</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Workflow DAG Canvas (Left) + Agent Inspector (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-0">
        {/* Left 7 Cols: Interactive React Flow DAG */}
        <div className="lg:col-span-7 h-full min-h-[400px]">
          <WorkflowCanvas
            currentStage={run?.current_stage || "REQUIREMENTS"}
            runStatus={run?.status || "RUNNING"}
            selectedStageKey={selectedStageKey}
            onSelectStage={(stageKey) => setSelectedStageKey(stageKey)}
            securityReworkCount={securityReworkCount}
            qaReworkCount={qaReworkCount}
            reviewReworkCount={reviewReworkCount}
          />
        </div>

        {/* Right 5 Cols: Agent Inspector Panel */}
        <div className="lg:col-span-5 h-full min-h-[400px]">
          <AgentInspector
            agent={selectedAgent}
            stageKey={selectedStageKey}
            status={
              run?.current_stage === selectedStageKey.replace("_node", "").toUpperCase()
                ? (run.status as StageStatus)
                : "COMPLETED"
            }
            retries={
              selectedStageKey === "security_node"
                ? securityReworkCount
                : selectedStageKey === "qa_node"
                ? qaReworkCount
                : selectedStageKey === "review_node"
                ? reviewReworkCount
                : 0
            }
            duration="1.4s"
            inputs={run?.state ? { stage: selectedStageKey, context: "LangGraph Shared State Snapshot" } : undefined}
            outputs={run?.state ? (run.state as Record<string, unknown>) : undefined}
          />
        </div>
      </div>

      {/* Bottom Section: Live Agent Communication Stream */}
      <div className="h-56 shrink-0">
        <CommunicationTimeline events={events} />
      </div>
    </div>
  );
};
