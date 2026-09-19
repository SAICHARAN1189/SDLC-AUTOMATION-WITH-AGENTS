import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  CheckCircle2,
  AlertTriangle,
  Layers,
  FileCheck,
  RotateCcw,
  ShieldCheck,
  Code2,
  FolderGit2,
  Loader2,
} from "lucide-react";
import { getReviewReport, getProjects, getProject } from "../services/api";
import type { ReviewOutput, Project, PipelineRun } from "../types";

export const ReviewCenter: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlRunId = searchParams.get("run_id");
  const urlProjectId = searchParams.get("project_id");

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(urlProjectId || "");
  const [selectedRunId, setSelectedRunId] = useState<string>(urlRunId || "");
  const [projectRuns, setProjectRuns] = useState<PipelineRun[]>([]);

  const [review, setReview] = useState<ReviewOutput | null>(null);
  const [loading, setLoading] = useState(true);

  // 1. Initial Load of Projects
  useEffect(() => {
    let mounted = true;
    getProjects()
      .then((projs) => {
        if (mounted && projs?.length) {
          setProjects(projs);
          if (!selectedProjectId) {
            setSelectedProjectId(projs[0].id);
          }
        }
      })
      .catch((err) => console.warn(err));
    return () => {
      mounted = false;
    };
  }, []);

  // 2. Load Project Runs
  useEffect(() => {
    let mounted = true;
    if (!selectedProjectId) return;
    getProject(selectedProjectId)
      .then((proj: any) => {
        if (mounted) {
          const runs: PipelineRun[] = proj?.runs || [];
          setProjectRuns(runs);
          if (!selectedRunId && runs.length) {
            setSelectedRunId(runs[0].id);
          }
        }
      })
      .catch((err) => console.warn(err));
    return () => {
      mounted = false;
    };
  }, [selectedProjectId]);

  // 3. Load Review Report for selected run
  useEffect(() => {
    let mounted = true;
    const fetchReport = async () => {
      if (!selectedRunId) {
        setLoading(false);
        setReview(null);
        return;
      }
      setLoading(true);
      try {
        const res = await getReviewReport(selectedRunId);
        if (mounted) setReview(res);
      } catch (err) {
        console.warn(err);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchReport();
    return () => {
      mounted = false;
    };
  }, [selectedRunId]);

  const handleProjectChange = (projId: string) => {
    setSelectedProjectId(projId);
    setSelectedRunId("");
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("project_id", projId);
      next.delete("run_id");
      return next;
    }, { replace: true });
  };

  const handleRunChange = (runId: string) => {
    setSelectedRunId(runId);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("run_id", runId);
      return next;
    }, { replace: true });
  };

  const isApproved = review?.review_status === "APPROVED";

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Filter Bar */}
      <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d] flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-bold tracking-tight text-zinc-100 flex items-center gap-2">
            <Layers className="w-5 h-5 text-emerald-400" /> Architectural & Code Review Center
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Senior engineer review evaluating architectural consistency, modularity, security remediation, and sign-off.
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 font-mono text-xs">
          {/* Project Filter */}
          <div className="flex items-center gap-1.5 bg-[#0d1117] border border-[#30363d] rounded-lg px-2.5 py-1.5">
            <FolderGit2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span className="text-zinc-500 text-[10px] uppercase font-semibold">Project:</span>
            <select
              value={selectedProjectId}
              onChange={(e) => handleProjectChange(e.target.value)}
              aria-label="Select Project"
              className="bg-transparent text-zinc-200 focus:outline-none cursor-pointer pr-2"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id} className="bg-[#161b22] text-zinc-100">
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Run Filter */}
          <div className="flex items-center gap-1.5 bg-[#0d1117] border border-[#30363d] rounded-lg px-2.5 py-1.5">
            <Layers className="w-3.5 h-3.5 text-sky-400 shrink-0" />
            <span className="text-zinc-500 text-[10px] uppercase font-semibold">Run:</span>
            <select
              value={selectedRunId}
              onChange={(e) => handleRunChange(e.target.value)}
              aria-label="Select Pipeline Run"
              className="bg-transparent text-zinc-200 focus:outline-none cursor-pointer pr-2"
            >
              {projectRuns.length === 0 ? (
                <option value="" className="bg-[#161b22] text-zinc-400">
                  No runs available
                </option>
              ) : (
                projectRuns.map((r) => (
                  <option key={r.id} value={r.id} className="bg-[#161b22] text-zinc-100">
                    Run {r.id.split("-")[0].toUpperCase()} ({r.status})
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Gate Status Badge */}
          <span
            className={`px-2.5 py-1 rounded text-xs font-semibold uppercase border ${
              isApproved
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                : "bg-amber-500/10 text-amber-300 border-amber-500/30"
            }`}
          >
            Review Gate: {review?.review_status || "PENDING"}
          </span>
        </div>
      </div>

      {loading ? (
        <div className="p-16 flex flex-col items-center justify-center gap-2 text-zinc-500">
          <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
          <span className="text-xs font-mono">Loading code review sign-off from Supabase...</span>
        </div>
      ) : !review ? (
        <div className="p-16 flex flex-col items-center justify-center gap-2 text-center text-zinc-400 font-mono text-xs rounded-xl border border-[#30363d] bg-[#161b22]">
          <Layers className="w-8 h-8 text-zinc-600 mb-2" />
          <span>No code review sign-offs recorded for this project yet.</span>
        </div>
      ) : (
        <>
          {/* Summary Card */}
          <div className="p-5 rounded-xl border border-[#30363d] bg-[#161b22] space-y-2">
            <div className="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
              Executive Review Assessment
            </div>
            <p className="text-xs text-zinc-300 font-sans leading-relaxed bg-[#0d1117] p-3 rounded-lg border border-[#30363d]">
              {review.summary || "No executive summary provided."}
            </p>
          </div>

          {/* Detailed Findings List */}
          <div className="rounded-xl border border-[#30363d] bg-[#161b22] overflow-hidden">
            <div className="p-3.5 border-b border-[#30363d] bg-[#12161f] text-xs font-semibold text-zinc-200">
              Review Findings & Recommendations ({review.findings?.length || 0})
            </div>
            <div className="divide-y divide-[#30363d]">
              {(review.findings?.length ?? 0) === 0 ? (
                <div className="p-8 text-center text-xs text-zinc-400 font-mono">
                  No review blocking items or warnings flagged.
                </div>
              ) : (
                review.findings.map((f, idx) => (
                  <div key={idx} className="p-4 space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold uppercase ${
                            f.severity === "BLOCKING"
                              ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                              : f.severity === "WARNING"
                              ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                              : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                          }`}
                        >
                          {f.severity}
                        </span>
                        <span className="font-semibold text-zinc-200">{f.title}</span>
                      </div>
                      <span className="text-[10px] font-mono text-zinc-400 capitalize">
                        {f.category?.replace("_", " ") || "Finding"}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-300 font-sans leading-relaxed">{f.description}</p>
                    {f.recommendation && (
                      <div className="text-[11px] text-emerald-400 font-sans bg-emerald-500/5 p-2 rounded border border-emerald-500/10">
                        <strong>Action:</strong> {f.recommendation}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
