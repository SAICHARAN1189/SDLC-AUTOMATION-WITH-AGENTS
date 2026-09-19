import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  TestTube2,
  CheckCircle2,
  XCircle,
  Clock,
  RotateCcw,
  FileCode2,
  Bug,
  Code2,
  AlertCircle,
  FolderGit2,
  Layers,
  Loader2,
  Copy,
  Check,
} from "lucide-react";
import { getQAReport, getProjects, getProject } from "../services/api";
import type { TestOutput, TestCaseFailure, Project, PipelineRun } from "../types";

export const QACenter: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlRunId = searchParams.get("run_id");
  const urlProjectId = searchParams.get("project_id");

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(urlProjectId || "");
  const [selectedRunId, setSelectedRunId] = useState<string>(urlRunId || "");
  const [projectRuns, setProjectRuns] = useState<PipelineRun[]>([]);

  const [qaReport, setQaReport] = useState<TestOutput | null>(null);
  const [selectedFailure, setSelectedFailure] = useState<TestCaseFailure | null>(null);
  const [activeTab, setActiveTab] = useState<"failures" | "tests" | "output" | "recommendations">("failures");
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

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

  // 3. Load QA Report for selected run
  useEffect(() => {
    let mounted = true;
    const fetchReport = async () => {
      if (!selectedRunId) {
        setLoading(false);
        setQaReport(null);
        return;
      }
      setLoading(true);
      try {
        const res = await getQAReport(selectedRunId);
        if (mounted) {
          setQaReport(res);
          if (res?.failures?.length) {
            setSelectedFailure(res.failures[0]);
          } else {
            setSelectedFailure(null);
          }
        }
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

  const handleCopyOutput = () => {
    if (!qaReport?.summary) return;
    navigator.clipboard.writeText(qaReport.summary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Filter & Scope Selector Bar */}
      <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d] flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-bold tracking-tight text-zinc-100 flex items-center gap-2">
            <TestTube2 className="w-5 h-5 text-sky-400" /> Automated QA & Test Execution Center
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Dynamic test execution sandbox, AST verification, and automated rework telemetry.
          </p>
        </div>

        {/* Dropdown Filters */}
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

          {/* Status Badge */}
          <span
            className={`px-2.5 py-1 rounded text-xs font-semibold uppercase border ${
              qaReport?.execution_status === "PASSED"
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                : "bg-rose-500/10 text-rose-300 border-rose-500/30"
            }`}
          >
            Status: {qaReport?.execution_status || "UNKNOWN"}
          </span>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="p-3.5 rounded-lg bg-[#161b22] border border-[#30363d]">
          <div className="text-[11px] text-zinc-400 font-mono">Total Tests</div>
          <div className="text-2xl font-bold font-mono text-zinc-100 mt-1">{qaReport?.total ?? "—"}</div>
          <div className="text-[10px] text-zinc-500 mt-0.5">Automated cases</div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#161b22] border border-emerald-500/30">
          <div className="text-[11px] text-zinc-400 font-mono">Passed Tests</div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">{qaReport?.passed ?? "—"}</div>
          <div className="text-[10px] text-zinc-500 mt-0.5">Green assertions</div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#161b22] border border-rose-500/30">
          <div className="text-[11px] text-zinc-400 font-mono">Failed Tests</div>
          <div className="text-2xl font-bold font-mono text-rose-400 mt-1">{qaReport?.failed ?? "—"}</div>
          <div className="text-[10px] text-zinc-500 mt-0.5">Rework triggers</div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#161b22] border border-[#30363d]">
          <div className="text-[11px] text-zinc-400 font-mono">Test Coverage</div>
          <div className="text-2xl font-bold font-mono text-sky-400 mt-1">
            {qaReport?.coverage != null ? `${qaReport.coverage}%` : "—"}
          </div>
          <div className="text-[10px] text-zinc-500 mt-0.5">Code branch coverage</div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#161b22] border border-[#30363d]">
          <div className="text-[11px] text-zinc-400 font-mono">Execution Time</div>
          <div className="text-2xl font-bold font-mono text-zinc-200 mt-1">
            {qaReport?.duration != null ? `${qaReport.duration}s` : "—"}
          </div>
          <div className="text-[10px] text-zinc-500 mt-0.5">Sandboxed runtime</div>
        </div>
      </div>

      {/* Main Container */}
      <div className="rounded-xl border border-[#30363d] bg-[#161b22] overflow-hidden flex flex-col">
        {/* Navigation Tabs */}
        <div className="p-3 border-b border-[#30363d] bg-[#12161f] flex flex-wrap items-center gap-2 font-mono text-xs">
          <button
            onClick={() => setActiveTab("failures")}
            className={`flex items-center gap-1.5 py-1 px-3 rounded transition-colors cursor-pointer ${
              activeTab === "failures"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Bug className="w-3.5 h-3.5" />
            <span>Failures & Tracebacks ({qaReport?.failures?.length || 0})</span>
          </button>

          <button
            onClick={() => setActiveTab("output")}
            className={`flex items-center gap-1.5 py-1 px-3 rounded transition-colors cursor-pointer ${
              activeTab === "output"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <FileCode2 className="w-3.5 h-3.5" />
            <span>Runner Stdout / Log</span>
          </button>

          <button
            onClick={() => setActiveTab("tests")}
            className={`flex items-center gap-1.5 py-1 px-3 rounded transition-colors cursor-pointer ${
              activeTab === "tests"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Code2 className="w-3.5 h-3.5" />
            <span>Generated Test Suites ({qaReport?.generated_tests?.length || 0})</span>
          </button>

          <button
            onClick={() => setActiveTab("recommendations")}
            className={`flex items-center gap-1.5 py-1 px-3 rounded transition-colors cursor-pointer ${
              activeTab === "recommendations"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-semibold"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <AlertCircle className="w-3.5 h-3.5" />
            <span>QA Recommendations ({qaReport?.recommendations?.length || 0})</span>
          </button>
        </div>

        {/* Tab Body */}
        <div className="p-5">
          {loading ? (
            <div className="p-12 flex flex-col items-center justify-center gap-2 text-zinc-500">
              <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
              <span className="text-xs font-mono">Loading real QA results from Supabase...</span>
            </div>
          ) : !qaReport ? (
            <div className="p-12 flex flex-col items-center justify-center gap-2 text-center text-zinc-400 font-mono text-xs">
              <TestTube2 className="w-8 h-8 text-zinc-600 mb-2" />
              <span>No QA test runs recorded for this project yet.</span>
            </div>
          ) : (
            <>
              {/* Failures Tab */}
              {activeTab === "failures" && (
                <div>
                  {(qaReport.failures?.length ?? 0) === 0 ? (
                    <div className="p-12 flex flex-col items-center justify-center gap-2 text-center">
                      <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                      <span className="text-sm font-semibold text-zinc-200">Zero Failures Detected</span>
                      <p className="text-xs text-zinc-400 max-w-sm font-sans">
                        All unit tests and integration assertions executed cleanly without runtime exceptions.
                      </p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                      <div className="lg:col-span-5 space-y-2">
                        {qaReport.failures.map((f, idx) => (
                          <div
                            key={idx}
                            onClick={() => setSelectedFailure(f)}
                            className={`p-3.5 rounded-lg border transition-colors cursor-pointer ${
                              selectedFailure?.test_name === f.test_name
                                ? "bg-[#1f242c] border-rose-500/50"
                                : "bg-[#0d1117] border-[#30363d] hover:bg-[#161b22]"
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                              <span className="font-mono text-xs text-zinc-100 font-semibold truncate">
                                {f.test_name}
                              </span>
                            </div>
                            <div className="mt-1.5 text-[11px] text-zinc-400 font-sans line-clamp-2">
                              {f.actual || (f as any).root_cause || "Assertion or execution failure"}
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="lg:col-span-7 rounded-lg border border-[#30363d] bg-[#0d1117] p-4 space-y-3 font-mono text-xs">
                        {selectedFailure ? (
                          <>
                            <div className="border-b border-[#30363d] pb-2">
                              <span className="text-[10px] text-zinc-500 uppercase tracking-wider block">Failed Test</span>
                              <span className="text-rose-400 font-semibold">{selectedFailure.test_name}</span>
                            </div>
                            {(selectedFailure.expected || selectedFailure.actual) && (
                              <div className="grid grid-cols-2 gap-2 text-[11px]">
                                <div className="p-2 rounded bg-[#161b22] border border-[#30363d]">
                                  <span className="text-zinc-500 text-[9px] uppercase block">Expected</span>
                                  <span className="text-emerald-400">{selectedFailure.expected || "Clean execution"}</span>
                                </div>
                                <div className="p-2 rounded bg-[#161b22] border border-rose-500/20">
                                  <span className="text-zinc-500 text-[9px] uppercase block">Actual</span>
                                  <span className="text-rose-400">{selectedFailure.actual || "Exception raised"}</span>
                                </div>
                              </div>
                            )}
                            {selectedFailure.stack_trace && (
                              <div>
                                <span className="text-[10px] text-zinc-500 uppercase tracking-wider block mb-1">Traceback</span>
                                <pre className="p-3 bg-[#090d13] rounded border border-[#30363d] text-[11px] text-rose-300 whitespace-pre-wrap overflow-x-auto leading-relaxed">
                                  {selectedFailure.stack_trace}
                                </pre>
                              </div>
                            )}
                          </>
                        ) : (
                          <div className="p-8 text-center text-zinc-500">Select a failed test to inspect traceback.</div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Output Tab */}
              {activeTab === "output" && (
                <div className="rounded-lg border border-[#30363d] bg-[#090d13] overflow-hidden">
                  <div className="h-9 bg-[#161b22] px-3.5 border-b border-[#30363d] flex items-center justify-between">
                    <div className="flex items-center gap-2 font-mono text-[11px] text-zinc-400">
                      <div className="flex items-center gap-1.5">
                        <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f56]" />
                        <div className="w-2.5 h-2.5 rounded-full bg-[#ffbd2e]" />
                        <div className="w-2.5 h-2.5 rounded-full bg-[#27c93f]" />
                      </div>
                      <span className="ml-2 font-semibold">pytest runner execution log</span>
                    </div>
                    <button
                      onClick={handleCopyOutput}
                      className="flex items-center gap-1 text-[11px] text-zinc-400 hover:text-zinc-200 px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 cursor-pointer"
                    >
                      {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{copied ? "Copied" : "Copy Output"}</span>
                    </button>
                  </div>
                  <pre className="p-4 font-mono text-xs text-zinc-300 whitespace-pre-wrap overflow-auto max-h-[500px] leading-5">
                    {qaReport.summary || "No stdout captured for this test execution run."}
                  </pre>
                </div>
              )}

              {/* Generated Tests Tab */}
              {activeTab === "tests" && (
                <div className="space-y-3 font-mono text-xs">
                  {(qaReport.generated_tests?.length ?? 0) === 0 ? (
                    <div className="p-8 text-center text-zinc-500">No test files generated for this run.</div>
                  ) : (
                    qaReport.generated_tests.map((f, i) => (
                      <details key={i} className="group rounded-lg border border-[#30363d] bg-[#0d1117] overflow-hidden">
                        <summary className="flex items-center gap-2 p-3 bg-[#161b22] cursor-pointer text-zinc-200 hover:bg-[#1c2128] transition-colors">
                          <FileCode2 className="w-4 h-4 text-sky-400 shrink-0" />
                          <span className="font-semibold">{f.path}</span>
                        </summary>
                        <pre className="p-4 text-[11px] text-zinc-300 bg-[#090d13] whitespace-pre-wrap overflow-x-auto border-t border-[#30363d]">
                          {f.content}
                        </pre>
                      </details>
                    ))
                  )}
                </div>
              )}

              {/* Recommendations Tab */}
              {activeTab === "recommendations" && (
                <div className="space-y-2 text-xs">
                  {(qaReport.recommendations?.length ?? 0) === 0 ? (
                    <div className="p-8 text-center text-zinc-500 font-mono">No QA recommendations noted.</div>
                  ) : (
                    qaReport.recommendations.map((rec, i) => (
                      <div key={i} className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d] text-zinc-300 flex items-start gap-2">
                        <AlertCircle className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                        <span>{rec}</span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
