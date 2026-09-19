import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  Boxes,
  CheckCircle2,
  Clock,
  Cpu,
  FileCode2,
  FolderGit2,
  Play,
  Radio,
  ShieldAlert,
  Sparkles,
  TestTube2,
} from "lucide-react";
import { getProjects } from "../services/api";
import type { Project } from "../types";

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const fetchAll = async () => {
      try {
        const pList = await getProjects();
        if (mounted) setProjects(pList);
      } catch (err) {
        console.warn("Using local state for dashboard", err);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    fetchAll();
    return () => {
      mounted = false;
    };
  }, []);

  // Compute metrics
  const totalProjects = projects.length;
  const allRuns = projects.flatMap((p) => p.runs || []);
  const activeRuns = allRuns.filter((r) => r.status === "RUNNING").length;
  const completedRuns = allRuns.filter((r) => r.status === "COMPLETED").length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-xl border border-[#30363d] bg-gradient-to-b from-[#161b22] to-[#0d1117] p-7 shadow-xl">
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono font-medium mb-3">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Autonomous Multi-Agent SDLC Platform</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-zinc-100">
            AI Software Engineering Control Center
          </h1>
          <p className="mt-2 text-sm text-zinc-300 leading-relaxed font-sans max-w-2xl">
            Transform natural-language software ideas into requirements, architecture, code, security validation, testing, and review through coordinated AI engineering agents.
          </p>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button
              onClick={() => navigate("/projects/new")}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs transition-colors shadow-sm cursor-pointer"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>Start New SDLC Run</span>
            </button>

            <Link
              to="/live"
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[#21262d] hover:bg-[#30363d] text-zinc-200 border border-[#30363d] text-xs font-medium transition-colors"
            >
              <Radio className="w-3.5 h-3.5 text-emerald-400" />
              <span>View Active Workspace</span>
            </Link>

            <button
              onClick={() => {
                navigate("/projects/new?preset=food_delivery");
              }}
              className="flex items-center gap-1.5 px-3 py-2 text-zinc-400 hover:text-zinc-200 text-xs transition-colors cursor-pointer"
            >
              <Sparkles className="w-3 h-3 text-amber-400" />
              <span>Load Food Delivery Preset</span>
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="p-4 rounded-lg bg-[#161b22] border border-[#30363d]">
          <div className="text-zinc-400 text-xs flex items-center justify-between">
            <span>Managed Projects</span>
            <FolderGit2 className="w-4 h-4 text-zinc-400" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-zinc-100">{totalProjects}</div>
          <div className="text-[11px] text-zinc-400 mt-0.5">Persisted in Supabase</div>
        </div>

        <div className="p-4 rounded-lg bg-[#161b22] border border-[#30363d]">
          <div className="text-zinc-400 text-xs flex items-center justify-between">
            <span>Active Runs</span>
            <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-emerald-400">{activeRuns}</div>
          <div className="text-[11px] text-zinc-400 mt-0.5">Running threads</div>
        </div>

        <div className="p-4 rounded-lg bg-[#161b22] border border-[#30363d]">
          <div className="text-zinc-400 text-xs flex items-center justify-between">
            <span>Completed Runs</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-zinc-100">{completedRuns}</div>
          <div className="text-[11px] text-zinc-400 mt-0.5">Full SDLC pipelines</div>
        </div>

        <div className="p-4 rounded-lg bg-[#161b22] border border-[#30363d]">
          <div className="text-zinc-400 text-xs flex items-center justify-between">
            <span>Specialized Agents</span>
            <Cpu className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-amber-300">8 Agents</div>
          <div className="text-[11px] text-zinc-400 mt-0.5">Autonomous roles</div>
        </div>

        <div className="p-4 rounded-lg bg-[#161b22] border border-[#30363d]">
          <div className="text-zinc-400 text-xs flex items-center justify-between">
            <span>Feedback Loops</span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-zinc-100">3 Loops</div>
          <div className="text-[11px] text-zinc-400 mt-0.5">Sec, QA, Review rework</div>
        </div>
      </div>

      {/* Two Column Layout: Architecture Diagram + Recent Pipelines */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Pipeline Architecture Card */}
        <div className="lg:col-span-2 rounded-xl border border-[#30363d] bg-[#161b22] p-5 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-zinc-100">Multi-Agent Workflow Architecture</h2>
              <p className="text-xs text-zinc-400">Deterministic verification & feedback loops coordinated via LangGraph</p>
            </div>
          </div>

          <div className="flex-1 bg-[#0b0e14] rounded-lg border border-[#30363d] p-4 flex flex-col justify-between text-xs font-mono space-y-4">
            {/* Sequential Phase 1: Requirements to Development */}
            <div>
              <div className="text-[10px] uppercase text-zinc-500 font-semibold tracking-wider mb-2">Phase 1: Synthesis & Architecture</div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
                <div className="p-2.5 rounded bg-[#161b22] border border-[#30363d]">
                  <div className="text-emerald-400 font-bold">1. Requirements</div>
                  <div className="text-[10px] text-zinc-400 mt-0.5">PRD & User Stories</div>
                </div>
                <div className="p-2.5 rounded bg-[#161b22] border border-[#30363d]">
                  <div className="text-emerald-400 font-bold">2. Architecture</div>
                  <div className="text-[10px] text-zinc-400 mt-0.5">Tech Specs & Models</div>
                </div>
                <div className="p-2.5 rounded bg-[#161b22] border border-[#30363d]">
                  <div className="text-emerald-400 font-bold">3. Visual Diagram</div>
                  <div className="text-[10px] text-zinc-400 mt-0.5">Mermaid System DAG</div>
                </div>
                <div className="p-2.5 rounded bg-[#161b22] border border-amber-500/30">
                  <div className="text-amber-300 font-bold">4. Developer</div>
                  <div className="text-[10px] text-zinc-400 mt-0.5">Code Synthesis</div>
                </div>
              </div>
            </div>

            {/* Quality Gates with Rework */}
            <div>
              <div className="text-[10px] uppercase text-zinc-500 font-semibold tracking-wider mb-2 flex items-center justify-between">
                <span>Phase 2: Quality Gates & Automated Rework Loops</span>
                <span className="text-[10px] text-rose-400">Rework &rarr; Developer Node</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-center">
                <div className="p-2.5 rounded bg-[#1b1419] border border-rose-500/30">
                  <div className="text-rose-300 font-bold flex items-center justify-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5" /> 5. Security Scanner
                  </div>
                  <div className="text-[10px] text-zinc-400 mt-0.5">
                    AST Pattern Scanning & Threat Score
                  </div>
                </div>
                <div className="p-2.5 rounded bg-[#141d24] border border-sky-500/30">
                  <div className="text-sky-300 font-bold flex items-center justify-center gap-1.5">
                    <TestTube2 className="w-3.5 h-3.5" /> 6. QA & Test Runner
                  </div>
                  <div className="text-[10px] text-zinc-400 mt-0.5">
                    Sandboxed Pytest Execution & Coverage
                  </div>
                </div>
              </div>
            </div>

            {/* Final Sign-Off */}
            <div>
              <div className="text-[10px] uppercase text-zinc-500 font-semibold tracking-wider mb-2">Phase 3: Review & Deliverables Finalization</div>
              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="p-2.5 rounded bg-[#161b22] border border-[#30363d]">
                  <div className="text-emerald-400 font-bold">7. Code Reviewer</div>
                  <div className="text-[10px] text-zinc-400 mt-0.5">Architectural Consistency</div>
                </div>
                <div className="p-2.5 rounded bg-[#161b22] border border-emerald-500/40">
                  <div className="text-emerald-300 font-bold">8. Finalizer</div>
                  <div className="text-[10px] text-zinc-400 mt-0.5">Deliverables & Checkpoints</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Col: Recent Projects */}
        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-5 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-zinc-100">Managed Projects</h2>
            <Link to="/projects" className="text-xs text-emerald-400 hover:underline flex items-center gap-1">
              View All <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="flex-1 space-y-2.5 overflow-y-auto">
            {loading ? (
              <div className="text-xs text-zinc-400 font-mono py-8 text-center">Loading projects...</div>
            ) : projects.length === 0 ? (
              <div className="text-center py-8 text-xs text-zinc-400 space-y-2">
                <div>No projects created yet.</div>
                <button
                  onClick={() => navigate("/projects/new")}
                  className="text-xs text-emerald-400 underline cursor-pointer"
                >
                  Create your first SDLC project
                </button>
              </div>
            ) : (
              projects.slice(0, 5).map((proj) => (
                <div
                  key={proj.id}
                  onClick={() => navigate(`/projects/${proj.id}`)}
                  className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d] hover:border-[#8b949e]/40 transition-colors cursor-pointer"
                >
                  <div className="flex items-center justify-between text-xs font-semibold text-zinc-200">
                    <span className="truncate">{proj.name}</span>
                    <span className="text-[10px] font-mono uppercase text-emerald-400">
                      {proj.status || "ACTIVE"}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] text-zinc-400 line-clamp-2 font-sans">{proj.idea}</p>
                  <div className="mt-2 text-[10px] font-mono text-zinc-400 flex items-center justify-between">
                    <span>Runs: {proj.runs?.length || 0}</span>
                    <span>{proj.created_at ? new Date(proj.created_at).toLocaleDateString() : "Active"}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
