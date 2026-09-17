import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  FolderGit2,
  Play,
  Calendar,
  Activity,
  ArrowLeft,
  FileCode,
  ShieldCheck,
  TestTube2,
  Clock,
  Layers,
} from "lucide-react";
import { getProject, createRun } from "../services/api";
import type { Project, PipelineRun } from "../types";

export const ProjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState(false);

  useEffect(() => {
    if (!id) return;
    let mounted = true;
    getProject(id)
      .then((data) => {
        if (mounted) setProject(data);
      })
      .catch((e) => console.warn(e))
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [id]);

  const handleLaunchNewRun = async () => {
    if (!id) return;
    setLaunching(true);
    try {
      const run = await createRun(id, { execution_mode: "AUTONOMOUS" });
      navigate(`/live?run_id=${run.id}&project_id=${id}`);
    } catch (err) {
      console.error(err);
      setLaunching(false);
    }
  };

  if (loading) {
    return <div className="text-center py-12 text-xs font-mono text-zinc-400">Loading project details...</div>;
  }

  if (!project) {
    return (
      <div className="text-center py-12 space-y-3">
        <div className="text-sm font-semibold text-zinc-200">Project Not Found</div>
        <Link to="/projects" className="text-xs text-emerald-400 underline">
          &larr; Back to Projects
        </Link>
      </div>
    );
  }

  const runs: PipelineRun[] = project.runs || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Back button */}
      <Link
        to="/projects"
        className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors font-mono"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Back to Projects
      </Link>

      {/* Project Overview Banner */}
      <div className="p-6 rounded-xl border border-[#30363d] bg-[#161b22] space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-zinc-100">{project.name}</h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase">
                {project.status || "ACTIVE"}
              </span>
            </div>
            <div className="text-[11px] font-mono text-zinc-400 mt-1 flex items-center gap-3">
              <span>ID: {project.id}</span>
              <span>Created: {project.created_at ? new Date(project.created_at).toLocaleDateString() : "Active"}</span>
            </div>
          </div>

          <button
            onClick={handleLaunchNewRun}
            disabled={launching}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs transition-colors cursor-pointer disabled:opacity-50"
          >
            <Play className="w-4 h-4 fill-current" />
            <span>{launching ? "Initiating Run..." : "Launch New SDLC Run"}</span>
          </button>
        </div>

        <div>
          <h2 className="text-xs font-mono text-zinc-400 uppercase tracking-wider mb-1">Software Specification Goal</h2>
          <p className="text-xs text-zinc-300 font-sans leading-relaxed bg-[#0d1117] p-3 rounded-lg border border-[#30363d]">
            {project.idea}
          </p>
        </div>
      </div>

      {/* Runs History Table */}
      <div className="rounded-xl border border-[#30363d] bg-[#161b22] overflow-hidden">
        <div className="p-4 border-b border-[#30363d] bg-[#12161f] flex items-center justify-between">
          <h2 className="text-xs font-semibold text-zinc-200 font-mono uppercase flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400" /> Pipeline Execution History ({runs.length})
          </h2>
        </div>

        {runs.length === 0 ? (
          <div className="p-8 text-center text-xs text-zinc-400 font-mono">
            No pipeline runs launched for this project yet. Click &quot;Launch New SDLC Run&quot; to begin.
          </div>
        ) : (
          <div className="divide-y divide-[#30363d]">
            {runs.map((r) => (
              <div key={r.id} className="p-4 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-zinc-200">RUN-{r.id.slice(0, 8)}</span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-semibold uppercase ${
                        r.status === "COMPLETED"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                          : r.status === "RUNNING"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 animate-pulse"
                          : "bg-zinc-800 text-zinc-400"
                      }`}
                    >
                      {r.status}
                    </span>
                    <span className="text-[10px] text-zinc-400">Mode: {r.execution_mode}</span>
                  </div>
                  <div className="text-[11px] text-zinc-400">
                    Current Stage: <strong className="text-zinc-300">{r.current_stage}</strong>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => navigate(`/live?run_id=${r.id}&project_id=${project.id}`)}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-[#0d1117] hover:bg-zinc-800 text-emerald-400 border border-[#30363d] text-xs transition-colors"
                  >
                    <Activity className="w-3.5 h-3.5" />
                    <span>Live Workspace</span>
                  </button>

                  <button
                    onClick={() => navigate(`/artifacts?run_id=${r.id}`)}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-[#0d1117] hover:bg-zinc-800 text-zinc-300 border border-[#30363d] text-xs transition-colors"
                  >
                    <FileCode className="w-3.5 h-3.5" />
                    <span>Artifacts</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
