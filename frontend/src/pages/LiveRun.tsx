import React, { useEffect, useState, useCallback } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import {
  Activity,
  AlertOctagon,
  ArrowRight,
  CheckCircle2,
  CheckSquare,
  Cpu,
  FileCode,
  Layers,
  Pause,
  Play,
  RotateCcw,
  Send,
  ShieldAlert,
  Square,
  TestTube2,
  Wrench,
  X,
} from "lucide-react";
import { WorkflowCanvas } from "../components/workflow/WorkflowCanvas";
import { AgentInspector } from "../components/agents/AgentInspector";
import { CommunicationTimeline } from "../components/workflow/CommunicationTimeline";
import {
  getRun,
  getRunEvents,
  getRunArtifacts,
  getAgents,
  stopRun,
  continueRun,
  submitIntervention,
  subscribeToRunEvents,
} from "../services/api";
import type {
  AgentIdentity,
  ArtifactItem,
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
  const [artifacts, setArtifacts] = useState<ArtifactItem[]>([]);
  const [agents, setAgents] = useState<Record<string, AgentIdentity>>({});
  const [selectedStageKey, setSelectedStageKey] = useState<string>("requirements_node");
  const [loading, setLoading] = useState(true);
  const [continuing, setContinuing] = useState(false);
  const [intervening, setIntervening] = useState(false);
  const [feedbackText, setFeedbackText] = useState("");
  const [showReworkInput, setShowReworkInput] = useState(false);

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

  // Map stage names to workflow canvas node IDs
  const stageToNodeKey = useCallback((stageName?: string): string | null => {
    if (!stageName) return null;
    const mapping: Record<string, string> = {
      REQUIREMENTS: "requirements_node",
      ARCHITECTURE: "architecture_node",
      VISUAL_ARCHITECTURE: "visual_architecture_node",
      DEVELOPMENT: "developer_node",
      DEVELOPER: "developer_node",
      SECURITY: "security_node",
      QA: "qa_node",
      REVIEW: "review_node",
      MODEL_COMPARISON: "model_comparison_node",
      FINALIZATION: "finalization_node",
    };
    return mapping[stageName] || null;
  }, []);

  // Fetch initial and updated run data, events, and optionally heavy artifacts
  const fetchRunData = useCallback(async (includeArtifacts = false) => {
    if (!runId) return;
    try {
      const [rData, evList, artList] = await Promise.all([
        getRun(runId),
        getRunEvents(runId),
        includeArtifacts ? getRunArtifacts(runId).catch(() => [] as ArtifactItem[]) : Promise.resolve(null),
      ]);
      setRun(rData);
      setEvents(evList);
      if (artList) {
        setArtifacts(artList);
      }

      // Derive rework counts
      let secR = 0;
      let qaR = 0;
      let revR = 0;
      (evList || []).forEach((ev: WorkflowEvent) => {
        if (ev.event_type === "REWORK_STARTED") {
          if (ev.stage === "SECURITY" || ev.message.includes("Security")) secR++;
          if (ev.stage === "QA" || ev.message.includes("QA")) qaR++;
          if (ev.stage === "REVIEW" || ev.message.includes("Review")) revR++;
        }
      });
      setSecurityReworkCount(secR);
      setQaReworkCount(qaR);
      setReviewReworkCount(revR);

      // Keep selectedStageKey aligned with active stage if running
      if (rData && rData.current_stage) {
        const activeNode = stageToNodeKey(rData.current_stage);
        if (activeNode && rData.status === "RUNNING") {
          setSelectedStageKey(activeNode);
        }
      }
    } catch (err) {
      console.warn("Run data fetch warning", err);
    } finally {
      setLoading(false);
    }
  }, [runId, stageToNodeKey]);

  useEffect(() => {
    // Initial fetch includes full artifacts
    fetchRunData(true);
  }, [fetchRunData]);

  // Active run polling fallback: lightweight run/events check every 4 seconds
  useEffect(() => {
    if (!runId) return;
    const isTerminal =
      run?.status === "COMPLETED" ||
      run?.status === "FAILED" ||
      run?.status === "STOPPED" ||
      run?.status === "MANUAL_INTERVENTION_REQUIRED";

    if (isTerminal) return;

    const interval = setInterval(() => {
      fetchRunData(false);
    }, 4000);

    return () => clearInterval(interval);
  }, [runId, run?.status, fetchRunData]);

  // Subscribe to live SSE stream for real-time events
  useEffect(() => {
    if (!runId) return;
    const unsubscribe = subscribeToRunEvents(
      runId,
      (event) => {
        // Append event with deduplication
        setEvents((prev) => {
          const isDup = prev.some(
            (ev) =>
              (event.id && ev.id === event.id) ||
              (event.event_id && ev.event_id === event.event_id) ||
              (ev.event_type === event.event_type && ev.message === event.message && ev.timestamp === event.timestamp)
          );
          if (isDup) return prev;
          return [...prev, event];
        });

        // Update run state dynamically
        setRun((prev) => {
          if (!prev) return prev;
          let newStatus = prev.status;
          if (event.event_type === "PIPELINE_COMPLETED") newStatus = "COMPLETED";
          if (event.event_type === "PIPELINE_FAILED") newStatus = "FAILED";
          if (event.event_type === "MANUAL_INTERVENTION_REQUIRED")
            newStatus = "MANUAL_INTERVENTION_REQUIRED";

          let stage = (event.stage as StageName) || prev.current_stage;
          if ((stage as string) === "DEVELOPER") stage = "DEVELOPMENT" as StageName;
          if ((stage as string) === "WORKFLOW" || (stage as string) === "START") stage = prev.current_stage;

          return {
            ...prev,
            status: newStatus,
            current_stage: stage,
          };
        });

        // Auto focus active stage node on canvas
        const activeNode = stageToNodeKey(event.stage);
        if (activeNode) {
          setSelectedStageKey(activeNode);
        }

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

        // On state transitions, trigger a background state sync
        if (
          event.event_type === "AGENT_STARTED" ||
          event.event_type === "AGENT_COMPLETED" ||
          event.event_type === "TESTS_STARTED" ||
          event.event_type === "TESTS_COMPLETED" ||
          event.event_type === "TESTS_FAILED" ||
          event.event_type === "TESTS_PASSED" ||
          event.event_type === "SECURITY_PASSED" ||
          event.event_type === "SECURITY_FINDINGS_FOUND" ||
          event.event_type === "REVIEW_COMPLETED" ||
          event.event_type === "PIPELINE_STARTED" ||
          event.event_type === "PIPELINE_COMPLETED" ||
          event.event_type === "PIPELINE_FAILED" ||
          event.event_type === "REWORK_STARTED" ||
          event.event_type === "REWORK_COMPLETED" ||
          event.event_type === "FEEDBACK_CREATED"
        ) {
          // On pipeline completion or agent transitions, refresh
          if (event.event_type === "PIPELINE_COMPLETED" || event.event_type === "PIPELINE_FAILED") {
            fetchRunData(true);
          } else {
            fetchRunData(false);
          }
        }
      },
      () => {
        // Fallback polling if SSE disconnects (rate-limited)
        fetchRunData(false);
      }
    );

    return () => unsubscribe();
  }, [runId, fetchRunData, stageToNodeKey]);

  const handleStop = async () => {
    if (!runId) return;
    try {
      await stopRun(runId);
      fetchRunData();
    } catch (e) {
      console.error(e);
    }
  };

  const handleContinue = async () => {
    if (!runId || continuing) return;
    setContinuing(true);
    try {
      await continueRun(runId);
      await fetchRunData();
    } catch (e) {
      console.error("Failed to advance pipeline step", e);
    } finally {
      setContinuing(false);
    }
  };

  const handleIntervention = async (
    action: "OVERRIDE" | "REWORK" | "COMPLETE",
    stage?: string
  ) => {
    if (!runId || intervening) return;
    setIntervening(true);
    try {
      await submitIntervention(runId, {
        action,
        requested_stage: stage,
        feedback: feedbackText || undefined,
      });
      setShowReworkInput(false);
      setFeedbackText("");

      // Optimistically update run status so intervention banner disappears immediately
      setRun((prev) => {
        if (!prev) return prev;
        const nextStatus = action === "COMPLETE" ? "COMPLETED" : "RUNNING";
        const nextStage = action === "REWORK" ? "DEVELOPMENT" : (stage || "REVIEW");
        return {
          ...prev,
          status: nextStatus,
          current_stage: nextStage as StageName,
        };
      });

      // Background sync without blocking the UI
      fetchRunData(false).catch(() => {});
    } catch (e) {
      console.error("Failed to submit manual intervention", e);
    } finally {
      setIntervening(false);
    }
  };

  // Stage output extraction helper
  const getStageOutput = useCallback((stageKey: string): Record<string, unknown> | undefined => {
    const state = (run?.state || {}) as Record<string, any>;
    const mapping: Record<string, string> = {
      requirements_node: "requirements",
      requirements_agent: "requirements",
      REQUIREMENTS: "requirements",

      architecture_node: "architecture",
      architecture_agent: "architecture",
      ARCHITECTURE: "architecture",

      visual_architecture_node: "visual_architecture",
      visual_architecture_agent: "visual_architecture",
      VISUAL_ARCHITECTURE: "visual_architecture",

      developer_node: "code",
      developer_agent: "code",
      DEVELOPER: "code",
      DEVELOPMENT: "code",

      security_node: "security_report",
      security_agent: "security_report",
      SECURITY: "security_report",

      qa_node: "test_report",
      qa_agent: "test_report",
      QA: "test_report",

      review_node: "review_report",
      review_agent: "review_report",
      REVIEW: "review_report",

      model_comparison_node: "model_comparison",
      model_comparison_agent: "model_comparison",
      MODEL_COMPARISON: "model_comparison",
    };

    const key = mapping[stageKey];
    if (key && state[key] && typeof state[key] === "object") {
      return state[key];
    }

    // Fallback: check loaded artifacts
    if (artifacts && artifacts.length > 0) {
      const artMapping: Record<string, string> = {
        requirements_node: "requirements",
        architecture_node: "architecture",
        visual_architecture_node: "diagrams",
        developer_node: "code",
        security_node: "security",
        qa_node: "tests",
        review_node: "review",
        model_comparison_node: "model_comparison",
      };
      const artType = artMapping[stageKey];
      const match = artifacts.find((a) => a.artifact_type === artType);
      if (match && match.content) {
        if (typeof match.content === "object") {
          return match.content as Record<string, unknown>;
        }
        try {
          return JSON.parse(match.content as string);
        } catch {
          return { content: match.content };
        }
      }
    }

    return undefined;
  }, [run?.state, artifacts]);

  // Stage input extraction helper
  const getStageInput = useCallback((stageKey: string): Record<string, unknown> | undefined => {
    const state = (run?.state || {}) as Record<string, any>;
    if (stageKey.includes("requirements")) {
      return {
        user_idea: state.user_idea || run?.project_id || "Live User Input",
        execution_mode: run?.execution_mode || "AUTONOMOUS",
        primary_model: run?.primary_model || "gemini-3.8-flash",
      };
    }
    if (stageKey.includes("architecture")) {
      return state.requirements ? { requirements: state.requirements } : undefined;
    }
    if (stageKey.includes("visual")) {
      return state.architecture ? { architecture: state.architecture } : undefined;
    }
    if (stageKey.includes("developer")) {
      return {
        requirements: state.requirements,
        architecture: state.architecture,
        developer_mode: state.developer_mode || "INITIAL_IMPLEMENTATION",
      };
    }
    if (stageKey.includes("security")) {
      return state.code ? { files_scanned: (state.code.files || []).map((f: any) => f.path) } : undefined;
    }
    if (stageKey.includes("qa")) {
      return {
        requirements_summary: state.requirements?.project_summary,
        code_files: (state.code?.files || []).map((f: any) => f.path),
      };
    }
    if (stageKey.includes("review")) {
      return {
        security_status: state.security_report?.overall_status,
        testing_status: state.test_report?.overall_status,
        files_count: (state.code?.files || []).length,
      };
    }
    return undefined;
  }, [run]);

  // Selected agent resolution
  const selectedAgent = agents[selectedStageKey] || {
    name: selectedStageKey,
    display_name: selectedStageKey.replace("_node", "").replace("_", " ").toUpperCase(),
    role: "Autonomous SDLC Agent",
    goal: "Execute engineering stage according to requirements and state context.",
    instructions: "Adhere to typed output schemas, invoke deterministic tools, and update LangGraph state.",
    tools: ["file_reader", "state_writer"],
    model: run?.primary_model || "Multi-Model Router",
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

          {run?.status === "WAITING" && (
            <button
              onClick={handleContinue}
              disabled={continuing}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-500 hover:bg-emerald-400 text-black text-xs font-semibold shadow-md shadow-emerald-500/20 transition-all cursor-pointer animate-pulse"
              title="Execute next step in pipeline"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{continuing ? "Advancing..." : "Execute Next Agent"}</span>
            </button>
          )}

          <button
            onClick={handleStop}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 text-xs font-medium transition-colors cursor-pointer"
          >
            <Square className="w-3 h-3 fill-current" />
            <span>Stop Run</span>
          </button>
        </div>
      </div>

      {/* Sleek Manual Intervention Action Bar */}
      {run?.status === "MANUAL_INTERVENTION_REQUIRED" && (
        <div className="px-4 py-2.5 rounded-xl bg-[#161b22] border border-amber-500/30 flex flex-wrap items-center justify-between gap-3 shrink-0 shadow-lg shadow-black/40">
          <div className="flex items-center gap-2.5">
            <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-amber-300">Intervention Required</span>
              <span className="text-zinc-600 text-xs">•</span>
              <span className="text-xs text-zinc-300">
                QA retry limit reached on stage <strong className="text-zinc-100">{run.current_stage}</strong>
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleIntervention("OVERRIDE", "REVIEW")}
              disabled={intervening}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black text-xs font-semibold shadow-sm shadow-emerald-500/20 transition-all cursor-pointer disabled:opacity-50"
              title="Override the QA gate failure and advance directly to Code Review"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{intervening ? "Resuming..." : "Override Gate & Proceed"}</span>
            </button>

            <button
              onClick={() => setShowReworkInput(true)}
              disabled={intervening}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-amber-300 border border-amber-500/30 text-xs font-medium transition-all cursor-pointer disabled:opacity-50"
              title="Give custom instructions to Developer Agent"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Instruct Developer...</span>
            </button>

            <button
              onClick={() => handleIntervention("COMPLETE")}
              disabled={intervening}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-zinc-100 border border-zinc-700 text-xs font-medium transition-all cursor-pointer disabled:opacity-50"
              title="Approve deliverables and complete run"
            >
              <CheckSquare className="w-3.5 h-3.5 text-zinc-400" />
              <span>Approve Deliverables</span>
            </button>
          </div>
        </div>
      )}

      {/* Modal Dialog for Rework with Feedback */}
      {showReworkInput && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-xl bg-[#161b22] border border-[#30363d] shadow-2xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
                  <RotateCcw className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-zinc-100">Instruct Developer Agent</h3>
                  <p className="text-[11px] text-zinc-400">Provide guidance on how to fix the issue before restarting rework.</p>
                </div>
              </div>
              <button
                onClick={() => setShowReworkInput(false)}
                className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div>
              <label className="block text-xs text-zinc-300 font-medium mb-1.5">
                Instructions for Developer Agent
              </label>
              <textarea
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                rows={4}
                placeholder="e.g. Do not import or use Selenium. Write standard unit tests with pytest for the pure calculator functions."
                className="w-full px-3 py-2 rounded-lg bg-[#0d1117] border border-[#30363d] text-zinc-100 text-xs placeholder:text-zinc-500 focus:outline-none focus:border-amber-400 resize-none font-mono"
              />
            </div>

            {/* Quick Suggestion Chips */}
            <div>
              <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold block mb-1.5">
                Quick Presets
              </span>
              <div className="flex flex-wrap gap-1.5">
                {[
                  "Do not use Selenium. Use standard pytest unit tests.",
                  "Mock external browser dependencies and test core functions.",
                  "Add input validation and error handling for edge cases.",
                ].map((preset, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setFeedbackText(preset)}
                    className="text-[10px] px-2.5 py-1 rounded bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 hover:text-zinc-100 border border-zinc-700/80 transition-colors cursor-pointer text-left"
                  >
                    {preset}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#30363d]">
              <button
                type="button"
                onClick={() => setShowReworkInput(false)}
                className="px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleIntervention("REWORK", "DEVELOPER")}
                disabled={intervening || !feedbackText.trim()}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-black text-xs font-semibold shadow-md shadow-amber-500/20 transition-all cursor-pointer disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{intervening ? "Submitting..." : "Send & Trigger Rework"}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step-by-Step interactive advance banner */}
      {run?.status === "WAITING" && (
        <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 flex flex-wrap items-center justify-between gap-3 text-xs text-amber-200 shrink-0">
          <div className="flex items-center gap-2">
            <Pause className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Step-by-Step Mode Paused:</strong> Stage <strong>{run.current_stage}</strong> completed. Click <strong>Execute Next Agent</strong> to advance pipeline execution.
            </span>
          </div>
          <button
            onClick={handleContinue}
            disabled={continuing}
            className="px-3 py-1.5 bg-amber-400 hover:bg-amber-300 text-black font-semibold rounded text-xs shrink-0 flex items-center gap-1.5 transition-colors cursor-pointer shadow"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>{continuing ? "Advancing..." : "Execute Next Agent"}</span>
          </button>
        </div>
      )}

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
            inputs={getStageInput(selectedStageKey)}
            outputs={getStageOutput(selectedStageKey)}
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
