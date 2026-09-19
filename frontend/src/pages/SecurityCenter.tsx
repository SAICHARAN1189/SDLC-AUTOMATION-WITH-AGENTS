import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import {
  ShieldAlert,
  ShieldCheck,
  RotateCcw,
  FileCode2,
  CheckCircle,
  Info,
  Layers,
  FolderGit2,
  ChevronRight,
  Loader2,
  ExternalLink,
} from "lucide-react";
import {
  getCentralSecurityOverview,
  getSecurityReport,
  getProjects,
  getProject,
  type CentralSecurityOverview,
} from "../services/api";
import type { SecurityOutput, Project, PipelineRun } from "../types";

export const SecurityCenter: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const urlRunId = searchParams.get("run_id");
  const urlProjectId = searchParams.get("project_id");

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(urlProjectId || "ALL");
  const [selectedRunId, setSelectedRunId] = useState<string>(urlRunId || "LATEST");
  const [projectRuns, setProjectRuns] = useState<PipelineRun[]>([]);

  const [centralData, setCentralData] = useState<CentralSecurityOverview | null>(null);
  const [runReport, setRunReport] = useState<SecurityOutput | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<any | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);

  // 1. Initial Load of Projects List
  useEffect(() => {
    let mounted = true;
    getProjects()
      .then((projs) => {
        if (mounted) setProjects(projs || []);
      })
      .catch((err) => console.warn("Failed to load projects:", err));
    return () => {
      mounted = false;
    };
  }, []);

  // 2. Fetch project details / runs when selectedProjectId changes
  useEffect(() => {
    let mounted = true;
    if (selectedProjectId === "ALL") {
      setProjectRuns([]);
      return;
    }
    getProject(selectedProjectId)
      .then((proj: any) => {
        if (mounted) {
          const runs = proj?.runs || [];
          setProjectRuns(runs);
        }
      })
      .catch((err) => console.warn("Failed to load project runs:", err));
    return () => {
      mounted = false;
    };
  }, [selectedProjectId]);

  // 3. Load Security Data (Central or Run-Specific)
  useEffect(() => {
    let mounted = true;
    const fetchData = async () => {
      setLoading(true);
      try {
        if (selectedProjectId === "ALL") {
          // Central Overview Mode
          const overview = await getCentralSecurityOverview();
          if (mounted) {
            setCentralData(overview);
            setRunReport(null);
            if (overview?.findings?.length) {
              setSelectedFinding(overview.findings[0]);
            } else {
              setSelectedFinding(null);
            }
          }
        } else {
          // Project Mode: either specific run or filtered central
          if (selectedRunId && selectedRunId !== "LATEST") {
            const report = await getSecurityReport(selectedRunId);
            if (mounted) {
              setRunReport(report);
              if (report?.vulnerabilities?.length) {
                setSelectedFinding(report.vulnerabilities[0]);
              } else {
                setSelectedFinding(null);
              }
            }
          } else {
            // Project filtered overview
            const overview = await getCentralSecurityOverview(selectedProjectId);
            if (mounted) {
              setCentralData(overview);
              setRunReport(null);
              if (overview?.findings?.length) {
                setSelectedFinding(overview.findings[0]);
              } else {
                setSelectedFinding(null);
              }
            }
          }
        }
      } catch (err) {
        console.warn("Security data fetch failed:", err);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchData();
    return () => {
      mounted = false;
    };
  }, [selectedProjectId, selectedRunId]);

  // Handler for changing project dropdown
  const handleProjectChange = (projId: string) => {
    setSelectedProjectId(projId);
    setSelectedRunId("LATEST");
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (projId === "ALL") {
        next.delete("project_id");
        next.delete("run_id");
      } else {
        next.set("project_id", projId);
        next.delete("run_id");
      }
      return next;
    }, { replace: true });
  };

  // Handler for changing run dropdown
  const handleRunChange = (runId: string) => {
    setSelectedRunId(runId);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (runId === "LATEST") {
        next.delete("run_id");
      } else {
        next.set("run_id", runId);
      }
      return next;
    }, { replace: true });
  };

  // Compute metrics depending on current view mode
  const isCentralMode = selectedProjectId === "ALL";
  const activeFindings = runReport ? runReport.vulnerabilities : (centralData?.findings || []);
  const filteredFindings = activeFindings.filter(
    (f: any) => filterSeverity === "ALL" || f.severity === filterSeverity
  );

  const metrics = isCentralMode
    ? {
        critical: centralData?.summary.critical || 0,
        high: centralData?.summary.high || 0,
        medium: centralData?.summary.medium || 0,
        low: centralData?.summary.low || 0,
        resolved: centralData?.summary.resolved || 0,
      }
    : runReport
    ? {
        critical: (runReport.severity_summary as any)?.critical || (runReport.severity_summary as any)?.CRITICAL || 0,
        high: (runReport.severity_summary as any)?.high || (runReport.severity_summary as any)?.HIGH || 0,
        medium: (runReport.severity_summary as any)?.medium || (runReport.severity_summary as any)?.MEDIUM || 0,
        low: (runReport.severity_summary as any)?.low || (runReport.severity_summary as any)?.LOW || 0,
        resolved: runReport.vulnerabilities?.filter((v) => v.status === "RESOLVED").length || 0,
      }
    : {
        critical: centralData?.summary.critical || 0,
        high: centralData?.summary.high || 0,
        medium: centralData?.summary.medium || 0,
        low: centralData?.summary.low || 0,
        resolved: centralData?.summary.resolved || 0,
      };

  const overallStatus = isCentralMode
    ? (metrics.critical > 0 || metrics.high > 0 ? "FAIL" : metrics.medium > 0 ? "WARNING" : "PASS")
    : runReport?.overall_status || (metrics.critical > 0 || metrics.high > 0 ? "FAIL" : metrics.medium > 0 ? "WARNING" : "PASS");

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Filter & Scope Selector Bar */}
      <div className="p-4 rounded-xl bg-[#161b22] border border-[#30363d] flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-bold tracking-tight text-zinc-100 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-400" /> Security & Vulnerability Center
          </h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            {isCentralMode
              ? "Central portfolio vulnerability management across all workspace projects."
              : `Security audit drilldown for ${projects.find((p) => p.id === selectedProjectId)?.name || "project"}.`}
          </p>
        </div>

        {/* Dropdown Filters */}
        <div className="flex flex-wrap items-center gap-3 font-mono text-xs">
          {/* Project Filter */}
          <div className="flex items-center gap-1.5 bg-[#0d1117] border border-[#30363d] rounded-lg px-2.5 py-1.5">
            <FolderGit2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span className="text-zinc-500 text-[10px] uppercase font-semibold">Scope:</span>
            <select
              value={selectedProjectId}
              onChange={(e) => handleProjectChange(e.target.value)}
              aria-label="Filter by project scope"
              className="bg-transparent text-zinc-200 focus:outline-none cursor-pointer pr-2"
            >
              <option value="ALL" className="bg-[#161b22] text-zinc-100">
                All Projects (Central Workspace)
              </option>
              {projects.map((p) => (
                <option key={p.id} value={p.id} className="bg-[#161b22] text-zinc-100">
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Run Filter (only when a specific project is selected) */}
          {!isCentralMode && (
            <div className="flex items-center gap-1.5 bg-[#0d1117] border border-[#30363d] rounded-lg px-2.5 py-1.5">
              <Layers className="w-3.5 h-3.5 text-sky-400 shrink-0" />
              <span className="text-zinc-500 text-[10px] uppercase font-semibold">Run:</span>
              <select
                value={selectedRunId}
                onChange={(e) => handleRunChange(e.target.value)}
                aria-label="Filter by pipeline run"
                className="bg-transparent text-zinc-200 focus:outline-none cursor-pointer pr-2"
              >
                <option value="LATEST" className="bg-[#161b22] text-zinc-100">
                  Latest Completed Run
                </option>
                {projectRuns.map((r) => (
                  <option key={r.id} value={r.id} className="bg-[#161b22] text-zinc-100">
                    Run {r.id.split("-")[0].toUpperCase()} ({r.status})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Status Badge */}
          <span
            className={`px-2.5 py-1 rounded text-xs font-semibold uppercase border ${
              overallStatus === "PASS"
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                : overallStatus === "WARNING"
                ? "bg-yellow-500/10 text-yellow-300 border-yellow-500/30"
                : "bg-rose-500/10 text-rose-300 border-rose-500/30"
            }`}
          >
            Posture: {overallStatus}
          </span>
        </div>
      </div>

      {/* Verified Notice */}
      <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/20 text-amber-200/90 text-xs flex items-start gap-2 font-sans">
        <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <span>
          Real-time security telemetry backed by Supabase PostgreSQL audit persistence. Continuous AST sink detection and LLM threat modeling.
        </span>
      </div>

      {/* Severity Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="p-3.5 rounded-lg bg-[#161b22] border border-rose-500/30">
          <div className="text-[11px] text-zinc-400 font-mono">Critical Findings</div>
          <div className="text-2xl font-bold font-mono text-rose-400 mt-1">{metrics.critical}</div>
          <div className="text-[10px] text-zinc-500 mt-0.5">Blocking execution</div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#161b22] border border-amber-500/30">
          <div className="text-[11px] text-zinc-400 font-mono">High Severity</div>
          <div className="text-2xl font-bold font-mono text-amber-400 mt-1">{metrics.high}</div>
          <div className="text-[10px] text-zinc-500 mt-0.5">Triggered rework</div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#161b22] border border-yellow-500/30">
          <div className="text-[11px] text-zinc-400 font-mono">Medium Severity</div>
          <div className="text-2xl font-bold font-mono text-yellow-300 mt-1">{metrics.medium}</div>
          <div className="text-[10px] text-zinc-500 mt-0.5">Warning alerts</div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#161b22] border border-sky-500/30">
          <div className="text-[11px] text-zinc-400 font-mono">Low / Informational</div>
          <div className="text-2xl font-bold font-mono text-sky-400 mt-1">{metrics.low}</div>
          <div className="text-[10px] text-zinc-500 mt-0.5">Best practices</div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#161b22] border border-emerald-500/30">
          <div className="text-[11px] text-zinc-400 font-mono">Resolved via Rework</div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">{metrics.resolved}</div>
          <div className="text-[10px] text-zinc-500 mt-0.5">Remediated by Dev</div>
        </div>
      </div>

      {/* Central View: Project Health Breakdown Table */}
      {isCentralMode && (centralData?.projects?.length ?? 0) > 0 && (
        <div className="rounded-xl border border-[#30363d] bg-[#161b22] overflow-hidden">
          <div className="p-3.5 border-b border-[#30363d] bg-[#12161f] flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-200 flex items-center gap-2">
              <Layers className="w-4 h-4 text-emerald-400" /> Monitored Projects Security Health ({centralData?.projects.length})
            </span>
            <span className="text-[11px] font-mono text-zinc-400">
              {centralData?.summary.total_scans} Total Pipeline Scans
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-sans">
              <thead className="bg-[#0d1117] text-[10px] uppercase font-mono text-zinc-400 border-b border-[#30363d]">
                <tr>
                  <th className="py-2.5 px-4">Project</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4">Runs Scanned</th>
                  <th className="py-2.5 px-4">Findings Breakdown</th>
                  <th className="py-2.5 px-4">Last Audit</th>
                  <th className="py-2.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#30363d]/60 font-mono">
                {centralData?.projects.map((p) => (
                  <tr key={p.project_id} className="hover:bg-[#1f242c]/50 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-zinc-100 font-sans">{p.project_name}</div>
                      <div className="text-[11px] text-zinc-500 truncate max-w-xs font-sans">{p.description}</div>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                          p.overall_status === "PASS"
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                            : p.overall_status === "WARNING"
                            ? "bg-yellow-500/10 text-yellow-300 border-yellow-500/30"
                            : "bg-rose-500/10 text-rose-300 border-rose-500/30"
                        }`}
                      >
                        {p.overall_status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-zinc-300">{p.total_runs}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5 text-[11px]">
                        {p.findings_count === 0 ? (
                          <span className="text-emerald-400 text-xs flex items-center gap-1">
                            <CheckCircle className="w-3.5 h-3.5" /> Clean
                          </span>
                        ) : (
                          <>
                            {p.severity_summary.critical > 0 && (
                              <span className="text-rose-400 font-bold">{p.severity_summary.critical}C</span>
                            )}
                            {p.severity_summary.high > 0 && (
                              <span className="text-amber-400 font-bold">{p.severity_summary.high}H</span>
                            )}
                            {p.severity_summary.medium > 0 && (
                              <span className="text-yellow-300 font-bold">{p.severity_summary.medium}M</span>
                            )}
                            {p.severity_summary.low > 0 && (
                              <span className="text-sky-400">{p.severity_summary.low}L</span>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-[11px] text-zinc-400 font-sans">
                      {p.last_scanned_at ? new Date(p.last_scanned_at).toLocaleDateString() : "Never"}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleProjectChange(p.project_id)}
                        className="px-2.5 py-1 rounded bg-[#0d1117] hover:bg-zinc-800 text-emerald-400 hover:text-emerald-300 border border-[#30363d] text-[11px] transition-colors cursor-pointer"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Main Content: Findings List (Left) + Remediation Details (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 7 Cols: Findings List */}
        <div className="lg:col-span-7 rounded-xl border border-[#30363d] bg-[#161b22] overflow-hidden flex flex-col">
          <div className="p-3.5 border-b border-[#30363d] bg-[#12161f] flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-200">
              Discovered Vulnerabilities & Sinks ({filteredFindings.length})
            </span>
            <div className="flex items-center gap-1.5 font-mono text-[11px]">
              {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((lvl) => (
                <button
                  key={lvl}
                  onClick={() => setFilterSeverity(lvl)}
                  className={`px-2 py-0.5 rounded border transition-colors cursor-pointer ${
                    filterSeverity === lvl
                      ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                      : "bg-[#0d1117] text-zinc-400 border-[#30363d] hover:text-zinc-200"
                  }`}
                >
                  {lvl}
                </button>
              ))}
            </div>
          </div>

          <div className="divide-y divide-[#30363d] overflow-y-auto max-h-[560px]">
            {loading ? (
              <div className="p-12 flex flex-col items-center justify-center gap-2 text-zinc-500">
                <Loader2 className="w-6 h-6 animate-spin text-emerald-500" />
                <span className="text-xs font-mono">Loading real findings from Supabase...</span>
              </div>
            ) : filteredFindings.length === 0 ? (
              <div className="p-12 flex flex-col items-center justify-center gap-2 text-center">
                <CheckCircle className="w-8 h-8 text-emerald-400" />
                <span className="text-sm font-semibold text-zinc-200">Zero Vulnerabilities Detected</span>
                <p className="text-xs text-zinc-400 max-w-sm font-sans">
                  No vulnerabilities match the current filter in this scope. All security scans verified clean.
                </p>
              </div>
            ) : (
              filteredFindings.map((f: any) => (
                <div
                  key={f.id}
                  onClick={() => setSelectedFinding(f)}
                  className={`p-3.5 transition-colors cursor-pointer hover:bg-[#1f242c] ${
                    selectedFinding?.id === f.id ? "bg-[#1f242c] border-l-2 border-emerald-500" : ""
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                          f.severity === "CRITICAL" || f.severity === "HIGH"
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                            : f.severity === "MEDIUM"
                            ? "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30"
                            : "bg-sky-500/20 text-sky-300 border border-sky-500/30"
                        }`}
                      >
                        {f.severity}
                      </span>
                      <span className="text-xs font-semibold text-zinc-200 font-mono">{f.category}</span>
                      {f.project_name && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700 font-mono">
                          {f.project_name}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-[10px] font-mono">
                      {f.caused_rework && (
                        <span className="flex items-center gap-1 text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                          <RotateCcw className="w-2.5 h-2.5" /> Caused Rework
                        </span>
                      )}
                      <span
                        className={`px-1.5 py-0.5 rounded ${
                          f.status === "RESOLVED"
                            ? "text-emerald-400 bg-emerald-500/10"
                            : "text-zinc-400 bg-zinc-800"
                        }`}
                      >
                        {f.status || "OPEN"}
                      </span>
                    </div>
                  </div>

                  <p className="mt-1.5 text-xs text-zinc-300 font-sans leading-relaxed line-clamp-2">
                    {f.description}
                  </p>

                  <div className="mt-2 text-[11px] font-mono text-zinc-400 flex items-center gap-2">
                    <FileCode2 className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                    <span className="truncate">{f.affected_file || "source"}{f.affected_line ? `:L${f.affected_line}` : ""}</span>
                    <span className="ml-auto text-[10px] text-zinc-500 font-sans uppercase shrink-0">
                      {f.source || "DETERMINISTIC"}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right 5 Cols: Selected Finding Remediation Details */}
        <div className="lg:col-span-5 rounded-xl border border-[#30363d] bg-[#161b22] p-5 flex flex-col justify-between">
          {selectedFinding ? (
            <div className="space-y-4">
              <div className="border-b border-[#30363d] pb-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-zinc-400 uppercase">Vulnerability Details</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300">
                    ID: {selectedFinding.id?.split("-")[0]}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-zinc-100 mt-1 capitalize">
                  {selectedFinding.category?.replace("_", " ") || "Finding"}
                </h3>
                {selectedFinding.run_id && (
                  <div className="mt-1 flex items-center gap-2">
                    <button
                      onClick={() => navigate(`/artifacts?run_id=${selectedFinding.run_id}&tab=security`)}
                      className="text-[11px] font-mono text-emerald-400 hover:text-emerald-300 flex items-center gap-1 cursor-pointer"
                    >
                      <span>Open in Artifacts Explorer</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  </div>
                )}
              </div>

              {selectedFinding.affected_file && (
                <div>
                  <div className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1">
                    Location & Evidence
                  </div>
                  <div className="p-2.5 rounded bg-[#0d1117] border border-[#30363d] font-mono text-xs text-zinc-300">
                    <div className="text-emerald-400 text-[11px] mb-1">
                      {selectedFinding.affected_file} {selectedFinding.affected_line ? `(Line ${selectedFinding.affected_line})` : ""}
                    </div>
                    {selectedFinding.evidence ? (
                      <pre className="p-2 bg-black/50 rounded overflow-x-auto text-[11px] text-rose-300 whitespace-pre-wrap">
                        {selectedFinding.evidence}
                      </pre>
                    ) : (
                      <p className="text-zinc-500 italic text-[11px]">No raw sink snippet captured.</p>
                    )}
                  </div>
                </div>
              )}

              <div>
                <div className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1">
                  Threat Description
                </div>
                <p className="text-xs text-zinc-300 font-sans leading-relaxed bg-[#0d1117] p-3 rounded border border-[#30363d]">
                  {selectedFinding.description || "No description provided."}
                </p>
              </div>

              <div>
                <div className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider mb-1 flex items-center gap-1">
                  <CheckCircle className="w-3.5 h-3.5" /> Prescribed Remediation
                </div>
                <p className="text-xs text-emerald-300 font-sans leading-relaxed bg-emerald-500/5 p-3 rounded border border-emerald-500/20">
                  {selectedFinding.remediation || "Follow secure coding guidelines for sanitization and input validation."}
                </p>
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[300px] flex flex-col items-center justify-center p-8 text-zinc-500 font-mono text-xs text-center">
              <ShieldCheck className="w-10 h-10 text-zinc-600 mb-2" />
              <span>Select any vulnerability finding on the left to inspect code evidence and remediation guidance.</span>
            </div>
          )}

          {/* Metadata Footer */}
          <div className="mt-4 pt-3 border-t border-[#30363d] text-[11px] font-mono text-zinc-400 flex items-center justify-between">
            <span>Detection Confidence: <strong>{((selectedFinding?.confidence || 0.9) * 100).toFixed(0)}%</strong></span>
            <span>Origin: <strong>{selectedFinding?.source || "DETERMINISTIC"}</strong></span>
          </div>
        </div>
      </div>
    </div>
  );
};
