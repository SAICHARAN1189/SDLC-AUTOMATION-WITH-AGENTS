import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  FileCode,
  FolderTree,
  Boxes,
  Palette,
  ShieldCheck,
  TestTube2,
  CheckCircle,
  Download,
  Copy,
  Check,
  FileText,
  AlertTriangle,
  XCircle,
  Info,
  ChevronRight,
  Package,
  Loader2,
  Layers,
  FolderGit2,
  Play,
  Square,
  RotateCw,
  ExternalLink,
  Terminal,
  Globe,
  Activity,
} from "lucide-react";
import { MermaidViewer } from "../components/artifacts/MermaidViewer";
import {
  getRunArtifacts,
  getProjects,
  getProject,
  startApp,
  stopApp,
  getAppStatus,
} from "../services/api";
import type {
  ArtifactItem,
  Project,
  PipelineRun,
  RequirementsOutput,
  ArchitectureOutput,
  VisualArchitectureOutput,
  CodeOutput,
  SecurityOutput,
  TestOutput,
  ReviewOutput,
  AppRunResult,
} from "../types";

/* helpers */
function parseContent<T>(raw: string | Record<string, unknown> | undefined): T | null {
  if (!raw) return null;
  if (typeof raw === "object") return raw as unknown as T;
  try { return JSON.parse(raw) as T; } catch { return null; }
}

function getLatest<T>(artifacts: ArtifactItem[], type: string): T | null {
  const matches = artifacts.filter((a) => a.artifact_type === type);
  if (!matches.length) return null;
  return parseContent<T>(matches[matches.length - 1].content);
}

const Badge: React.FC<{ label: string; color: "green" | "red" | "yellow" | "blue" | "orange" }> = ({ label, color }) => {
  const map = {
    green: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    red: "bg-red-500/15 text-red-400 border-red-500/30",
    yellow: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
    blue: "bg-sky-500/15 text-sky-400 border-sky-500/30",
    orange: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  };
  return <span className={`px-2 py-0.5 rounded border text-[10px] font-bold font-mono uppercase ${map[color]}`}>{label}</span>;
};

const SectionCard: React.FC<{ title: string; children: React.ReactNode; className?: string }> = ({ title, children, className = "" }) => (
  <div className={`rounded-lg border border-[#30363d] bg-[#0d1117] p-4 space-y-3 ${className}`}>
    <h3 className="text-[10px] font-semibold text-emerald-400 uppercase tracking-widest font-mono">{title}</h3>
    {children}
  </div>
);

const BulletList: React.FC<{ items: string[] | undefined }> = ({ items }) => {
  if (!items?.length) return <p className="text-zinc-500 text-xs italic">None specified.</p>;
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-xs text-zinc-300">
          <ChevronRight className="w-3 h-3 text-emerald-500 mt-0.5 shrink-0" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
};

const EmptyState: React.FC<{ message: string }> = ({ message }) => (
  <div className="flex flex-col items-center justify-center h-64 gap-3 text-zinc-500">
    <Info className="w-8 h-8" />
    <p className="text-sm">{message}</p>
  </div>
);

/* Terminal Console for Test Output */
const TerminalConsole: React.FC<{ title: string; content: string }> = ({ title, content }) => {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lines = content.split("\n");

  return (
    <div className="rounded-lg border border-[#30363d] bg-[#090d13] overflow-hidden shadow-xl font-mono text-xs">
      <div className="h-9 bg-[#161b22] px-3.5 border-b border-[#30363d] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f56]" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#ffbd2e]" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#27c93f]" />
          </div>
          <span className="text-[11px] text-zinc-400 ml-2 font-semibold">{title}</span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-[11px] text-zinc-400 hover:text-zinc-200 px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 cursor-pointer transition-colors"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          <span>{copied ? "Copied" : "Copy Log"}</span>
        </button>
      </div>
      <div className="p-4 overflow-x-auto max-h-[420px] overflow-y-auto space-y-0.5 leading-5 select-text bg-[#090d13]">
        {lines.map((line, idx) => {
          let lineStyle = "text-zinc-300";
          if (line.includes("ERROR") || line.includes("FAILED") || line.includes("SyntaxError") || line.includes("AssertionError") || line.startsWith("E ")) {
            lineStyle = "text-rose-400 font-semibold";
          } else if (line.includes("PASSED") || line.includes("passed in")) {
            lineStyle = "text-emerald-400 font-semibold";
          } else if (line.startsWith("===") || line.startsWith("---")) {
            lineStyle = "text-zinc-500 font-semibold";
          } else if (line.includes("WARNING")) {
            lineStyle = "text-yellow-400";
          }
          return (
            <div key={idx} className={`whitespace-pre ${lineStyle}`}>
              {line || "\u00A0"}
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* Requirements */
const RequirementsTab: React.FC<{ data: RequirementsOutput | null }> = ({ data }) => {
  if (!data) return <EmptyState message="Requirements artifact not found for this run." />;
  return (
    <div className="space-y-4">
      <h2 className="text-base font-bold text-zinc-100 font-mono">Product Requirements Document</h2>
      <SectionCard title="Project Summary">
        <p className="text-xs text-zinc-300 leading-relaxed">{data.project_summary || "None specified."}</p>
      </SectionCard>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SectionCard title="Functional Requirements"><BulletList items={data.functional_requirements} /></SectionCard>
        <SectionCard title="Non-Functional Requirements"><BulletList items={data.non_functional_requirements} /></SectionCard>
      </div>
      {(data.user_stories?.length ?? 0) > 0 && (
        <SectionCard title="User Stories">
          <div className="space-y-2">
            {data.user_stories.map((s: any, i) => {
              if (typeof s === "string") {
                return (
                  <div key={i} className="p-3 rounded bg-[#161b22] border border-[#30363d] text-xs text-zinc-300 flex items-start gap-2.5">
                    <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono text-[10px] shrink-0 font-semibold">US-{i + 1}</span>
                    <p className="leading-relaxed">{s}</p>
                  </div>
                );
              }
              const hasParts = s?.as_a || s?.i_want || s?.so_that;
              return (
                <div key={i} className="p-3 rounded bg-[#161b22] border border-[#30363d] text-xs text-zinc-300 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono text-[10px] font-semibold">US-{i + 1}</span>
                    {s?.title && <span className="text-emerald-400 font-semibold font-mono">{s.title}</span>}
                  </div>
                  {hasParts ? (
                    <p className="leading-relaxed">
                      As <strong className="text-zinc-100">{s.as_a || "user"}</strong>, I want to <strong className="text-zinc-100">{s.i_want || ""}</strong>
                      {s.so_that ? <>, so that <strong className="text-zinc-100">{s.so_that}</strong>.</> : "."}
                    </p>
                  ) : (
                    <p className="leading-relaxed">{s?.description || s?.story || JSON.stringify(s)}</p>
                  )}
                </div>
              );
            })}
          </div>
        </SectionCard>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SectionCard title="Acceptance Criteria"><BulletList items={data.acceptance_criteria} /></SectionCard>
        <SectionCard title="Constraints and Assumptions"><BulletList items={[...(data.constraints || []), ...(data.assumptions || [])]} /></SectionCard>
      </div>
      {(data.risks?.length ?? 0) > 0 && <SectionCard title="Risks"><BulletList items={data.risks} /></SectionCard>}
    </div>
  );
};

/* Architecture */
function formatTechField(val: any, fallback1 = "framework", fallback2 = "styling"): string {
  if (!val) return "Not specified";
  if (typeof val === "string") return val.trim() || "Not specified";
  if (typeof val === "object") {
    const p1 = val[fallback1] || val.primary || val.name || "";
    const p2 = val[fallback2] || val.runtime || val.orm || "";
    if (p1 && p2) return `${p1} / ${p2}`;
    if (p1) return p1;
    if (p2) return p2;
    const parts = Object.values(val).filter((v) => typeof v === "string" && v.trim().length > 0);
    return parts.length ? parts.join(" / ") : "Not specified";
  }
  return String(val);
}

const ArchitectureTab: React.FC<{ data: ArchitectureOutput | null }> = ({ data }) => {
  if (!data) return <EmptyState message="Architecture artifact not found for this run." />;
  return (
    <div className="space-y-4">
      <h2 className="text-base font-bold text-zinc-100 font-mono flex items-center gap-2">
        <Layers className="w-4 h-4 text-emerald-400" /> System Architecture Specification
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono">
        {[
          { label: "Architecture Style", value: data.architecture_style || "Modular Architecture" },
          { label: "Frontend", value: formatTechField(data.frontend, "framework", "styling") },
          { label: "Backend", value: formatTechField(data.backend, "framework", "runtime") },
          { label: "Database", value: formatTechField(data.database, "primary", "orm") },
          { label: "Auth", value: data.authentication || "Not specified" },
          { label: "Deployment", value: data.deployment_architecture || "Not specified" },
        ].map((item) => (
          <div key={item.label} className="p-4 rounded-lg bg-[#0d1117] border border-[#30363d] space-y-1">
            <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">{item.label}</div>
            <div className="text-xs text-zinc-200 leading-snug">{item.value}</div>
          </div>
        ))}
      </div>

      {(data.services?.length ?? 0) > 0 && (
        <SectionCard title="Services & Domain Modules">
          <BulletList items={data.services} />
        </SectionCard>
      )}

      {(data.modules?.length ?? 0) > 0 && (
        <SectionCard title="System Modules">
          <div className="space-y-2">
            {data.modules.map((m: any, i) => {
              if (typeof m === "string") {
                return (
                  <div key={i} className="p-2.5 rounded bg-[#161b22] border border-[#30363d] text-xs flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-sky-400 shrink-0" />
                    <span className="text-zinc-200 font-mono font-medium">{m}</span>
                  </div>
                );
              }
              return (
                <div key={i} className="p-3 rounded bg-[#161b22] border border-[#30363d] text-xs space-y-1">
                  <span className="text-sky-400 font-semibold font-mono">{m.name}</span>
                  {m.responsibility && <p className="text-zinc-300">{m.responsibility}</p>}
                  {(m.dependencies?.length ?? 0) > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {m.dependencies.map((d: string, j: number) => (
                        <span key={j} className="px-1.5 py-0.5 bg-zinc-800 text-zinc-400 rounded text-[10px] font-mono border border-zinc-700">{d}</span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </SectionCard>
      )}

      {(data.apis?.length ?? 0) > 0 && (
        <SectionCard title="API Endpoints">
          <div className="space-y-1.5 font-mono">
            {data.apis.map((api: any, i) => {
              if (typeof api === "string") {
                const parts = api.split(" ");
                const method = parts[0]?.toUpperCase();
                const rest = parts.slice(1).join(" ");
                const isHttp = ["GET", "POST", "PUT", "DELETE", "PATCH"].includes(method);
                return (
                  <div key={i} className="flex items-center gap-3 text-xs px-3 py-2 rounded bg-[#161b22] border border-[#30363d]">
                    {isHttp ? (
                      <span className="w-14 text-center px-1 py-0.5 rounded bg-sky-500/15 text-sky-400 border border-sky-500/30 text-[10px] font-bold shrink-0">{method}</span>
                    ) : (
                      <span className="w-14 text-center px-1 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700 text-[10px] font-bold shrink-0">API</span>
                    )}
                    <span className="text-emerald-400 font-semibold">{isHttp ? rest : api}</span>
                  </div>
                );
              }
              return (
                <div key={i} className="flex items-center gap-3 text-xs px-3 py-2 rounded bg-[#161b22] border border-[#30363d]">
                  <span className="w-14 text-center px-1 py-0.5 rounded bg-sky-500/15 text-sky-400 border border-sky-500/30 text-[10px] font-bold shrink-0">{api.method || "ENDPOINT"}</span>
                  <span className="text-emerald-400 font-semibold">{api.endpoint}</span>
                  {api.description && <span className="text-zinc-400 font-sans">{api.description}</span>}
                </div>
              );
            })}
          </div>
        </SectionCard>
      )}

      {(data.data_model?.length ?? 0) > 0 && (
        <SectionCard title="Data Model Entities">
          <div className="flex flex-wrap gap-2">
            {data.data_model.map((dm: any, idx: number) => {
              const name = typeof dm === "string" ? dm : dm.entity || dm.name || JSON.stringify(dm);
              return (
                <span key={idx} className="px-2.5 py-1 rounded bg-[#161b22] text-emerald-400 border border-[#30363d] font-mono text-xs">
                  {name}
                </span>
              );
            })}
          </div>
        </SectionCard>
      )}

      {(data.integrations?.length ?? 0) > 0 && (
        <SectionCard title="Third-Party Integrations">
          <BulletList items={data.integrations} />
        </SectionCard>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SectionCard title="Security Considerations"><BulletList items={data.security_considerations} /></SectionCard>
        <SectionCard title="Scalability Considerations"><BulletList items={data.scalability_considerations} /></SectionCard>
      </div>
    </div>
  );
};

/* Diagrams */
const DiagramsTab: React.FC<{ data: VisualArchitectureOutput | null }> = ({ data }) => {
  const [activeDiagram, setActiveDiagram] = useState(0);
  if (!data?.diagrams?.length) return <EmptyState message="No architecture diagrams generated for this run." />;
  const diagram = data.diagrams[activeDiagram];
  return (
    <div className="space-y-4 h-full">
      {data.diagrams.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {data.diagrams.map((d, i) => (
            <button key={i} onClick={() => setActiveDiagram(i)}
              className={`px-3 py-1.5 rounded text-xs font-mono border transition-colors cursor-pointer ${i === activeDiagram ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/40" : "bg-[#161b22] text-zinc-400 border-[#30363d] hover:border-zinc-500"}`}>
              {d.title || `Diagram ${i + 1}`}
            </button>
          ))}
        </div>
      )}
      <div className="h-full min-h-[400px]">
        <MermaidViewer code={diagram.mermaid_code} title={diagram.title || "Architecture Diagram"} />
      </div>
    </div>
  );
};

function formatCodeContent(content?: string): string {
  if (!content) return "";
  let s = content.trim();
  if ((s.startsWith('"') && s.endsWith('"') && s.length > 2) || (s.startsWith('\\"') && s.endsWith('\\"'))) {
    if (s.startsWith('\\"')) s = s.slice(2, -2);
    else {
      const inner = s.slice(1, -1).trim();
      if (inner.startsWith('{') || inner.startsWith('<') || inner.startsWith('import') || inner.startsWith('const') || inner.startsWith('def')) {
        s = inner;
      }
    }
  }
  if (s.includes("\\n")) {
    const numEscaped = (s.match(/\\n/g) || []).length;
    const numReal = (s.match(/\n/g) || []).length;
    if (numReal <= 2 || numEscaped > numReal) {
      s = s.replace(/\\r\\n/g, "\n").replace(/\\r/g, "\n").replace(/\\n/g, "\n").replace(/\\t/g, "  ").replace(/\\"/g, '"');
    }
  } else if (s.includes('\\"') && !s.replace(/\\"/g, '').includes('"')) {
    s = s.replace(/\\"/g, '"');
  }
  return s;
}

/* Code */
const CodeTab: React.FC<{ data: CodeOutput | null; runId?: string | null }> = ({ data, runId }) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [copied, setCopied] = useState(false);
  const [activeView, setActiveView] = useState<"code" | "preview" | "health" | "terminal">("code");
  const [appState, setAppState] = useState<AppRunResult | null>(null);
  const [starting, setStarting] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [runnerError, setRunnerError] = useState<string | null>(null);

  // Poll app status if running or on load
  useEffect(() => {
    if (!runId) return;
    let mounted = true;
    getAppStatus(runId)
      .then((res) => {
        if (mounted && res.status === "running") {
          setAppState(res);
        }
      })
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, [runId]);

  const handleStart = async () => {
    if (!runId) return;
    setStarting(true);
    setRunnerError(null);
    try {
      const res = await startApp(runId, data?.files);
      setAppState(res);
      if (res.preview_url) {
        setActiveView("preview");
      } else {
        setActiveView("health");
      }
    } catch (err) {
      setRunnerError(err instanceof Error ? err.message : "Failed to start application");
    } finally {
      setStarting(false);
    }
  };

  const handleStop = async () => {
    if (!runId) return;
    setStopping(true);
    try {
      await stopApp(runId);
      setAppState((prev) => (prev ? { ...prev, status: "stopped" } : null));
      if (activeView === "preview") {
        setActiveView("code");
      }
    } catch (err) {
      setRunnerError(err instanceof Error ? err.message : "Failed to stop application");
    } finally {
      setStopping(false);
    }
  };

  const handleRestart = async () => {
    await handleStop();
    await handleStart();
  };

  if (!data?.files?.length) return <EmptyState message="No source files generated for this run." />;
  const files = data.files;
  const selected = files[selectedIndex];
  const handleCopy = () => {
    navigator.clipboard.writeText(formatCodeContent(selected?.content));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  const ext = selected?.path?.split(".").pop() || "";
  const langMap: Record<string, string> = {
    py: "Python",
    js: "JavaScript",
    ts: "TypeScript",
    tsx: "TSX",
    html: "HTML",
    css: "CSS",
    json: "JSON",
    md: "Markdown",
    sh: "Shell",
    yaml: "YAML",
    yml: "YAML",
    txt: "Text",
  };

  const isRunning = appState?.status === "running";

  return (
    <div className="flex flex-col gap-3 h-full min-h-[580px]">
      {/* Top Execution & Control Bar */}
      <div className="p-3 rounded-lg border border-[#30363d] bg-[#0d1117] flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-zinc-200">
            <FolderTree className="w-4 h-4 text-emerald-400" />
            <span>Generated Codebase</span>
            <span className="text-[11px] font-mono text-zinc-400">({files.length} files)</span>
          </div>

          {isRunning && (
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                <span>LIVE · Port {appState?.port}</span>
              </span>
              {appState?.health_check?.ok && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[11px] font-mono">
                  <CheckCircle className="w-3 h-3 text-emerald-400" />
                  <span>Health Verified (200 OK)</span>
                </span>
              )}
            </div>
          )}

          {appState?.project_type && (
            <span className="text-[11px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700 font-mono">
              {appState.project_type}
            </span>
          )}
        </div>

        {/* Action Buttons & View Mode Tabs */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* View Mode Switcher */}
          <div className="flex items-center bg-[#161b22] border border-[#30363d] rounded p-0.5 text-xs font-mono">
            <button
              onClick={() => setActiveView("code")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded transition-colors cursor-pointer ${
                activeView === "code"
                  ? "bg-[#21262d] text-emerald-400 font-medium"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <FileCode className="w-3.5 h-3.5" />
              <span>Source Files</span>
            </button>

            <button
              onClick={() => setActiveView("preview")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded transition-colors cursor-pointer ${
                activeView === "preview"
                  ? "bg-[#21262d] text-emerald-400 font-medium"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Globe className="w-3.5 h-3.5" />
              <span>Live App Preview</span>
              {isRunning && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />}
            </button>

            <button
              onClick={() => setActiveView("health")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded transition-colors cursor-pointer ${
                activeView === "health"
                  ? "bg-[#21262d] text-emerald-400 font-medium"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Health Checks</span>
            </button>

            <button
              onClick={() => setActiveView("terminal")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded transition-colors cursor-pointer ${
                activeView === "terminal"
                  ? "bg-[#21262d] text-emerald-400 font-medium"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>Console Logs</span>
            </button>
          </div>

          {/* Execution Controls */}
          {!isRunning ? (
            <button
              onClick={handleStart}
              disabled={starting}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white font-medium text-xs shadow-sm shadow-emerald-950 transition-all cursor-pointer disabled:opacity-50"
            >
              {starting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Play className="w-3.5 h-3.5 fill-current" />
              )}
              <span>{starting ? "Starting App..." : "Start App"}</span>
            </button>
          ) : (
            <div className="flex items-center gap-1.5">
              {appState?.preview_url && (
                <a
                  href={appState.preview_url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs border border-zinc-700 transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Open in Tab</span>
                </a>
              )}

              <button
                onClick={handleRestart}
                disabled={starting}
                className="p-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-zinc-100 border border-zinc-700 transition-colors cursor-pointer"
                title="Restart App"
              >
                <RotateCw className={`w-3.5 h-3.5 ${starting ? "animate-spin" : ""}`} />
              </button>

              <button
                onClick={handleStop}
                disabled={stopping}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-red-950/40 hover:bg-red-900/60 border border-red-800/60 text-red-300 hover:text-red-200 text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
              >
                {stopping ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Square className="w-3.5 h-3.5 fill-current" />
                )}
                <span>Stop App</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {runnerError && (
        <div className="p-3 rounded bg-red-950/30 border border-red-800/40 text-red-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{runnerError}</span>
          </div>
          <button onClick={() => setRunnerError(null)} className="text-zinc-400 hover:text-zinc-200">
            <XCircle className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main View Area */}
      <div className="flex-1 min-h-[460px]">
        {activeView === "code" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-full min-h-[460px]">
            {/* File List */}
            <div className="lg:col-span-4 rounded-lg border border-[#30363d] bg-[#0d1117] p-3 flex flex-col gap-2 font-mono text-xs overflow-y-auto">
              <div className="text-[10px] text-zinc-400 uppercase tracking-wider font-semibold flex items-center justify-between shrink-0">
                <span className="flex items-center gap-1.5">
                  <FolderTree className="w-3.5 h-3.5 text-emerald-400" /> Source Files ({files.length})
                </span>
                {selected && (
                  <span className="text-[10px] text-zinc-500 font-normal">
                    {selectedIndex + 1} of {files.length}
                  </span>
                )}
              </div>
              {files.map((file, idx) => (
                <button
                  key={file.path + idx}
                  onClick={() => setSelectedIndex(idx)}
                  className={`w-full text-left px-2.5 py-1.5 rounded flex items-start gap-2 transition-colors cursor-pointer ${
                    selectedIndex === idx
                      ? "bg-[#1f242c] text-emerald-400 border border-[#30363d]"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-[#161b22]"
                  }`}
                >
                  <FileCode className="w-3 h-3 mt-0.5 shrink-0" />
                  <span className="truncate">{file.path}</span>
                </button>
              ))}
              {(data.dependencies?.length ?? 0) > 0 && (
                <div className="mt-2 pt-2 border-t border-[#30363d]">
                  <div className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold flex items-center gap-1.5 mb-1.5">
                    <Package className="w-3 h-3" /> Dependencies
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {data.dependencies.map((dep, i) => (
                      <span key={i} className="px-1.5 py-0.5 bg-zinc-800 text-zinc-400 rounded text-[10px] border border-zinc-700">
                        {dep}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Code Viewer */}
            <div className="lg:col-span-8 rounded-lg border border-[#30363d] bg-[#0d1117] overflow-hidden flex flex-col">
              <div className="h-9 border-b border-[#30363d] bg-[#161b22] px-3 flex items-center justify-between text-xs font-mono shrink-0">
                <div className="flex items-center gap-2">
                  <span className="text-emerald-400 font-semibold truncate max-w-xs">{selected?.path}</span>
                  {ext && (
                    <span className="px-1.5 py-0.5 rounded bg-sky-500/15 text-sky-400 text-[10px] border border-sky-500/30">
                      {langMap[ext] || ext.toUpperCase()}
                    </span>
                  )}
                </div>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1 text-[11px] text-zinc-400 hover:text-zinc-200 px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 cursor-pointer"
                >
                  {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{copied ? "Copied!" : "Copy"}</span>
                </button>
              </div>
              <pre className="flex-1 p-4 text-xs font-mono text-zinc-200 overflow-auto whitespace-pre">
                {formatCodeContent(selected?.content)}
              </pre>
            </div>
          </div>
        )}

        {activeView === "preview" && (() => {
          const proxyUrl = runId ? `/api/runs/${runId}/app/proxy/` : "";
          const previewSrc = (appState?.preview_url && !appState.preview_url.includes("127.0.0.1"))
            ? appState.preview_url
            : proxyUrl;

          return (
            <div className="rounded-lg border border-[#30363d] bg-[#0d1117] overflow-hidden flex flex-col h-full min-h-[500px]">
              {/* Mock Browser URL Bar */}
              <div className="h-10 border-b border-[#30363d] bg-[#161b22] px-3 flex items-center justify-between gap-3 text-xs font-mono shrink-0">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                  <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
                </div>

                <div className="flex-1 max-w-xl mx-auto flex items-center gap-2 px-3 py-1 rounded bg-[#0d1117] border border-[#30363d] text-zinc-300 text-xs truncate">
                  <Globe className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span className="truncate">{previewSrc || "Live Sandbox Preview"}</span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      const iframe = document.getElementById("app-preview-frame") as HTMLIFrameElement | null;
                      if (iframe) iframe.src = iframe.src;
                    }}
                    className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
                    title="Reload Preview"
                  >
                    <RotateCw className="w-3.5 h-3.5" />
                  </button>
                  {previewSrc && (
                    <a
                      href={previewSrc}
                      target="_blank"
                      rel="noreferrer"
                      className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
                      title="Open in new window"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>
              </div>

              {/* Iframe or Not Running Placeholder */}
              {previewSrc ? (
                <div className="flex-1 bg-white relative">
                  <iframe
                    id="app-preview-frame"
                    src={previewSrc}
                    className="w-full h-full border-0 absolute inset-0"
                    title="App Live Preview"
                    sandbox="allow-scripts allow-same-origin allow-forms"
                  />
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center gap-3 p-8 text-center text-zinc-400">
                  <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                    <Play className="w-5 h-5 fill-current ml-0.5" />
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-zinc-200">The application is not running yet</p>
                    <p className="text-xs text-zinc-500">
                      Click "Start App" above to launch the codebase and preview it live.
                    </p>
                  </div>
                  <button
                    onClick={handleStart}
                    disabled={starting}
                    className="px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs shadow-sm transition-all cursor-pointer"
                  >
                    {starting ? "Starting..." : "Start App Now"}
                  </button>
                </div>
              )}
            </div>
          );
        })()}

        {activeView === "health" && (
          <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-4 space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-[#30363d] pb-3">
              <div>
                <h3 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-400" /> Automated Codebase Health & Smoke Check
                </h3>
                <p className="text-[11px] text-zinc-400 mt-0.5">
                  Verifies that the generated application initializes, binds its network port, and handles requests without crashing.
                </p>
              </div>

              {appState?.health_check && (
                <Badge
                  label={appState.health_check.ok ? "APP HEALTHY" : "CHECK REQUIRED"}
                  color={appState.health_check.ok ? "green" : "yellow"}
                />
              )}
            </div>

            {/* Diagnostic Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-3 rounded bg-[#161b22] border border-[#30363d] space-y-1">
                <div className="text-[10px] uppercase tracking-wider text-zinc-500">App Status</div>
                <div className={`text-sm font-bold ${isRunning ? "text-emerald-400" : "text-zinc-400"}`}>
                  {isRunning ? "ONLINE & RUNNING" : "STOPPED / IDLE"}
                </div>
              </div>
              <div className="p-3 rounded bg-[#161b22] border border-[#30363d] space-y-1">
                <div className="text-[10px] uppercase tracking-wider text-zinc-500">Project Type</div>
                <div className="text-sm font-bold text-zinc-200 truncate">
                  {appState?.project_type || "Standard Web App"}
                </div>
              </div>
              <div className="p-3 rounded bg-[#161b22] border border-[#30363d] space-y-1">
                <div className="text-[10px] uppercase tracking-wider text-zinc-500">Local Port</div>
                <div className="text-sm font-bold text-emerald-400">
                  {appState?.port ? `Port ${appState.port}` : "None allocated"}
                </div>
              </div>
              <div className="p-3 rounded bg-[#161b22] border border-[#30363d] space-y-1">
                <div className="text-[10px] uppercase tracking-wider text-zinc-500">Entry Point</div>
                <div className="text-sm font-bold text-sky-400 truncate">
                  {appState?.entry_point || "Auto-detected"}
                </div>
              </div>
            </div>

            {/* Probed Endpoints Table */}
            <div>
              <div className="text-[11px] uppercase tracking-wider text-zinc-400 font-semibold mb-2">
                Probed Endpoints & HTTP Verification
              </div>
              {appState?.health_check?.endpoints?.length ? (
                <div className="rounded border border-[#30363d] bg-[#161b22] overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#0d1117] border-b border-[#30363d] text-zinc-400 text-[10px] uppercase">
                      <tr>
                        <th className="py-2 px-3">Endpoint Route</th>
                        <th className="py-2 px-3">HTTP Status</th>
                        <th className="py-2 px-3">Latency</th>
                        <th className="py-2 px-3">Response Preview</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#30363d]">
                      {appState.health_check.endpoints.map((ep, idx) => (
                        <tr key={idx} className="hover:bg-[#1c2128]">
                          <td className="py-2 px-3 font-semibold text-zinc-200">{ep.endpoint}</td>
                          <td className="py-2 px-3">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                ep.ok
                                  ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                                  : "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                              }`}
                            >
                              {ep.status} {ep.ok ? "OK" : ""}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-zinc-400">{ep.latency_ms}ms</td>
                          <td className="py-2 px-3 text-zinc-500 truncate max-w-xs font-mono text-[11px]">
                            {ep.response_sample || "(empty)"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-4 rounded bg-[#161b22] border border-[#30363d] text-zinc-500 text-center">
                  Start the application above to run automated endpoint verification probes.
                </div>
              )}
            </div>

            {/* Verdict Note */}
            {appState?.health_check && (
              <div className="p-3 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
                <CheckCircle className="w-4 h-4 shrink-0" />
                <span>{appState.health_check.message}</span>
              </div>
            )}
          </div>
        )}

        {activeView === "terminal" && (
          <div className="rounded-lg border border-[#30363d] bg-[#090c10] flex flex-col h-full min-h-[460px] overflow-hidden font-mono text-xs">
            <div className="h-9 border-b border-[#30363d] bg-[#161b22] px-3 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2 text-zinc-300">
                <Terminal className="w-3.5 h-3.5 text-emerald-400" />
                <span className="font-semibold text-xs">Application Server Output & Probes</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-zinc-500">Live Stream</span>
                {isRunning && <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />}
              </div>
            </div>
            <pre className="flex-1 p-4 text-[11px] text-zinc-300 overflow-auto whitespace-pre-wrap leading-relaxed">
              {appState?.stdout ||
                "No logs available. Click 'Start App' above to initialize the sandbox and stream server execution logs."}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

/* Security */
const SecurityTab: React.FC<{ data: SecurityOutput | null }> = ({ data }) => {
  if (!data) return <EmptyState message="Security report not found for this run." />;
  const statusColor: "green" | "yellow" | "red" = data.overall_status === "PASS" ? "green" : data.overall_status === "WARNING" ? "yellow" : "red";
  const sevColor = (s: string): "red" | "orange" | "yellow" | "blue" => ({ CRITICAL: "red" as const, HIGH: "orange" as const, MEDIUM: "yellow" as const, LOW: "blue" as const })[s] ?? "blue";
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-base font-bold text-zinc-100 font-mono">Security Audit Report</h2>
        <Badge label={data.overall_status || "UNKNOWN"} color={statusColor} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono">
        {Object.entries(data.severity_summary || {}).map(([k, v]) => (
          <div key={k} className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d] text-center space-y-1">
            <div className={`text-lg font-bold ${Number(v) > 0 ? (k === "CRITICAL" || k === "HIGH" ? "text-red-400" : "text-yellow-400") : "text-emerald-400"}`}>{String(v)}</div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-wider">{k}</div>
          </div>
        ))}
      </div>
      {(data.vulnerabilities?.length ?? 0) > 0 ? (
        <SectionCard title={`Vulnerabilities (${data.vulnerabilities.length})`}>
          <div className="space-y-3">
            {data.vulnerabilities.map((v, i) => (
              <div key={i} className="p-3 rounded bg-[#161b22] border border-[#30363d] space-y-2 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-zinc-100 font-mono">{v.category?.toUpperCase()} - {v.description}</span>
                  <Badge label={v.severity} color={sevColor(v.severity)} />
                </div>
                {v.affected_file && <div className="text-zinc-500 font-mono">{v.affected_file}{v.affected_line ? `:L${v.affected_line}` : ""}</div>}
                {v.evidence && <pre className="px-3 py-2 bg-[#0d1117] rounded border border-[#30363d] text-[11px] font-mono text-orange-300 whitespace-pre-wrap overflow-x-auto">{v.evidence}</pre>}
                <p className="text-zinc-400"><span className="text-zinc-300 font-semibold">Remediation:</span> {v.remediation}</p>
              </div>
            ))}
          </div>
        </SectionCard>
      ) : (
        <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-2 text-xs text-emerald-400">
          <CheckCircle className="w-4 h-4" /> No vulnerabilities detected.
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SectionCard title="Recommendations"><BulletList items={data.recommendations} /></SectionCard>
        <SectionCard title="Remediation Actions"><BulletList items={data.remediation_actions} /></SectionCard>
      </div>
    </div>
  );
};

/* Tests */
const TestsTab: React.FC<{ data: TestOutput | null }> = ({ data }) => {
  if (!data) return <EmptyState message="QA test report not found for this run." />;
  const passed = data.execution_status === "PASSED";
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-base font-bold text-zinc-100 font-mono">QA Test Report</h2>
        <Badge label={data.execution_status || "UNKNOWN"} color={passed ? "green" : "red"} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono">
        {[
          { label: "Total", value: String(data.total ?? "—"), color: "text-zinc-200" },
          { label: "Passed", value: String(data.passed ?? "—"), color: "text-emerald-400" },
          { label: "Failed", value: String(data.failed ?? "—"), color: (data.failed ?? 0) > 0 ? "text-rose-400" : "text-zinc-400" },
          { label: "Coverage", value: data.coverage != null ? `${data.coverage}%` : "—", color: "text-sky-400" },
        ].map((stat) => (
          <div key={stat.label} className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d] text-center space-y-1">
            <div className={`text-lg font-bold ${stat.color}`}>{stat.value}</div>
            <div className="text-[10px] text-zinc-500 uppercase tracking-wider">{stat.label}</div>
          </div>
        ))}
      </div>

      {data.summary && (
        <div>
          <div className="text-[10px] font-semibold text-emerald-400 uppercase tracking-widest font-mono mb-2">
            Test Runner Execution Output
          </div>
          <TerminalConsole title="pytest --tb=short runner" content={data.summary} />
        </div>
      )}

      {(data.failures?.length ?? 0) > 0 && (
        <SectionCard title={`Test Failures & Exceptions (${data.failures.length})`}>
          <div className="space-y-3">
            {data.failures.map((f, i) => (
              <div key={i} className="p-3.5 rounded-lg bg-[#161b22] border border-rose-500/30 space-y-2.5 text-xs">
                <div className="flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span className="font-semibold text-zinc-100 font-mono">{f.test_name}</span>
                </div>
                {(f.expected || f.actual) && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] font-mono">
                    {f.expected && (
                      <div className="p-2 rounded bg-[#0d1117] border border-[#30363d]">
                        <span className="text-zinc-500 block text-[9px] uppercase tracking-wider">Expected</span>
                        <span className="text-emerald-400">{f.expected}</span>
                      </div>
                    )}
                    {f.actual && (
                      <div className="p-2 rounded bg-[#0d1117] border border-rose-500/20">
                        <span className="text-zinc-500 block text-[9px] uppercase tracking-wider">Actual</span>
                        <span className="text-rose-400">{f.actual}</span>
                      </div>
                    )}
                  </div>
                )}
                {f.stack_trace && (
                  <div className="rounded border border-[#30363d] bg-[#090d13] p-3 font-mono text-[11px] text-rose-300 overflow-x-auto whitespace-pre leading-relaxed">
                    {f.stack_trace}
                  </div>
                )}
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {(data.generated_tests?.length ?? 0) > 0 && (
        <SectionCard title={`Generated Test Files (${data.generated_tests.length})`}>
          <div className="space-y-2 font-mono text-xs">
            {data.generated_tests.map((f, i) => (
              <details key={i} className="group">
                <summary className="flex items-center gap-2 px-3 py-2 rounded bg-[#161b22] border border-[#30363d] cursor-pointer text-zinc-300 hover:text-zinc-100 transition-colors">
                  <FileCode className="w-3 h-3 text-sky-400 shrink-0" />
                  <span>{f.path}</span>
                </summary>
                <pre className="mt-1 px-3 py-2.5 bg-[#090d13] rounded text-[11px] text-zinc-300 whitespace-pre-wrap overflow-x-auto border border-[#30363d]">{formatCodeContent(f.content)}</pre>
              </details>
            ))}
          </div>
        </SectionCard>
      )}

      {(data.recommendations?.length ?? 0) > 0 && (
        <SectionCard title="Recommendations"><BulletList items={data.recommendations} /></SectionCard>
      )}
    </div>
  );
};

/* Review */
const ReviewTab: React.FC<{ data: ReviewOutput | null }> = ({ data }) => {
  if (!data) return <EmptyState message="Code review report not found for this run." />;
  const statusColor: "green" | "yellow" | "red" = data.review_status === "APPROVED" ? "green" : data.review_status === "NEEDS_REWORK" ? "yellow" : "red";
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-base font-bold text-zinc-100 font-mono">Code Review Sign-Off</h2>
        <Badge label={data.review_status || "UNKNOWN"} color={statusColor} />
      </div>
      {data.summary && <SectionCard title="Review Summary"><p className="text-xs text-zinc-300 leading-relaxed">{data.summary}</p></SectionCard>}
      {(data.blocking_issues?.length ?? 0) > 0 && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 space-y-2">
          <div className="flex items-center gap-2 text-red-400 font-semibold text-xs font-mono uppercase"><AlertTriangle className="w-3.5 h-3.5" /> Blocking Issues</div>
          <BulletList items={data.blocking_issues} />
        </div>
      )}
      {(data.findings?.length ?? 0) > 0 && (
        <SectionCard title={`Findings (${data.findings.length})`}>
          <div className="space-y-3">
            {data.findings.map((f, i) => {
              const sev = f.severity;
              const textCol = sev === "BLOCKING" ? "text-red-400" : sev === "WARNING" ? "text-yellow-400" : "text-sky-400";
              const borderCol = sev === "BLOCKING" ? "border-red-500/30" : sev === "WARNING" ? "border-yellow-500/30" : "border-sky-500/30";
              return (
                <div key={i} className={`p-3 rounded bg-[#161b22] border ${borderCol} space-y-1.5 text-xs`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className={`font-semibold font-mono ${textCol}`}>{f.title}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${borderCol} ${textCol}`}>{sev}</span>
                  </div>
                  {f.file && <div className="text-zinc-500 font-mono">{f.file}</div>}
                  <p className="text-zinc-300">{f.description}</p>
                  <p className="text-zinc-400"><span className="text-zinc-200 font-semibold">Recommendation:</span> {f.recommendation}</p>
                </div>
              );
            })}
          </div>
        </SectionCard>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SectionCard title="Recommendations"><BulletList items={data.recommendations} /></SectionCard>
        <SectionCard title="Required Changes"><BulletList items={data.required_changes} /></SectionCard>
      </div>
    </div>
  );
};

/* Main */
export const Artifacts: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const runId = searchParams.get("run_id");
  const tabParam = searchParams.get("tab") as "requirements" | "architecture" | "diagrams" | "code" | "security" | "tests" | "review" | null;

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [projectRuns, setProjectRuns] = useState<PipelineRun[]>([]);

  const [artifacts, setArtifacts] = useState<ArtifactItem[]>([]);
  const [activeTab, setActiveTab] = useState<"requirements" | "architecture" | "diagrams" | "code" | "security" | "tests" | "review">(
    tabParam || "requirements"
  );
  const [exportCopied, setExportCopied] = useState(false);
  const [loading, setLoading] = useState(true);

  // 1. Initial Load of Projects
  useEffect(() => {
    let mounted = true;
    getProjects()
      .then((projs) => {
        if (!mounted) return;
        const list = projs || [];
        setProjects(list);
        if (list.length > 0 && !selectedProjectId) {
          setSelectedProjectId(list[0].id);
        }
      })
      .catch((err) => console.warn("Failed to load projects:", err));
    return () => { mounted = false; };
  }, []);

  // 2. When selectedProjectId changes, load its runs
  useEffect(() => {
    let mounted = true;
    if (!selectedProjectId) return;
    getProject(selectedProjectId)
      .then((proj: any) => {
        if (!mounted) return;
        const runs: PipelineRun[] = proj?.runs || [];
        setProjectRuns(runs);

        // If no runId is currently selected or current runId does not belong to this project, select the latest run
        if (runs.length > 0) {
          const runExistsInProject = runs.some((r) => r.id === runId);
          if (!runId || !runExistsInProject) {
            const latest = runs[0].id;
            setSearchParams((prev) => {
              const next = new URLSearchParams(prev);
              next.set("run_id", latest);
              return next;
            }, { replace: true });
          }
        }
      })
      .catch((err) => console.warn("Failed to load project runs:", err));
    return () => { mounted = false; };
  }, [selectedProjectId]);

  useEffect(() => {
    if (tabParam && tabParam !== activeTab) {
      setActiveTab(tabParam);
    }
  }, [tabParam]);

  useEffect(() => {
    let mounted = true;
    const fetchArtifacts = async () => {
      if (!runId) { setLoading(false); return; }
      setLoading(true);
      try {
        const res = await getRunArtifacts(runId);
        if (mounted) setArtifacts(res || []);
      } catch (err) {
        console.warn(err);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    fetchArtifacts();
    return () => { mounted = false; };
  }, [runId]);

  const handleDownloadZip = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(artifacts, null, 2));
    const a = document.createElement("a");
    a.setAttribute("href", dataStr);
    a.setAttribute("download", `sdlc-artifacts-${runId || "run"}.json`);
    document.body.appendChild(a); a.click(); a.remove();
    setExportCopied(true); setTimeout(() => setExportCopied(false), 2000);
  };

  const tabs = [
    { id: "requirements", label: "Requirements PRD", icon: FileText },
    { id: "architecture", label: "Architecture Spec", icon: Boxes },
    { id: "diagrams", label: "Mermaid Diagrams", icon: Palette },
    { id: "code", label: "Generated Codebase", icon: FolderTree },
    { id: "security", label: "Security Report", icon: ShieldCheck },
    { id: "tests", label: "Test Suites", icon: TestTube2 },
    { id: "review", label: "Review Sign-Off", icon: CheckCircle },
  ];

  const reqData = getLatest<RequirementsOutput>(artifacts, "requirements");
  const archData = getLatest<ArchitectureOutput>(artifacts, "architecture");
  const diagData = getLatest<VisualArchitectureOutput>(artifacts, "diagrams");
  const codeData = getLatest<CodeOutput>(artifacts, "code");
  const secData = getLatest<SecurityOutput>(artifacts, "security");
  const testData = getLatest<TestOutput>(artifacts, "tests");
  const revData = getLatest<ReviewOutput>(artifacts, "review");

  return (
    <div className="flex flex-col h-[calc(100vh-5rem)] space-y-4 max-w-7xl mx-auto">
      <div className="p-3.5 rounded-lg bg-[#161b22] border border-[#30363d] flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div>
          <h1 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
            <FileCode className="w-4 h-4 text-emerald-400" /> Artifact Explorer and Project Deliverables
          </h1>
          <p className="text-[11px] text-zinc-400 mt-0.5">
            {runId
              ? <span>Run <span className="font-mono text-zinc-300">{runId.split("-")[0].toUpperCase()}</span>{" · "}{artifacts.length} artifact{artifacts.length !== 1 ? "s" : ""} loaded</span>
              : "Select a project and run to inspect deliverables."}
          </p>
        </div>

        {/* Project & Run Selectors */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="flex items-center gap-1.5 bg-[#0d1117] border border-[#30363d] rounded px-2.5 py-1.5">
            <FolderGit2 className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              className="bg-transparent text-xs text-zinc-200 outline-none cursor-pointer max-w-[180px] truncate"
            >
              {projects.length === 0 && <option value="">No projects</option>}
              {projects.map((p) => (
                <option key={p.id} value={p.id} className="bg-[#161b22] text-zinc-200">
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5 bg-[#0d1117] border border-[#30363d] rounded px-2.5 py-1.5">
            <Layers className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
            <select
              value={runId || ""}
              onChange={(e) => {
                const newRunId = e.target.value;
                setSearchParams((prev) => {
                  const next = new URLSearchParams(prev);
                  next.set("run_id", newRunId);
                  return next;
                }, { replace: true });
              }}
              className="bg-transparent text-xs text-zinc-200 font-mono outline-none cursor-pointer max-w-[170px] truncate"
            >
              {projectRuns.length === 0 && <option value="">No runs</option>}
              {projectRuns.map((r) => (
                <option key={r.id} value={r.id} className="bg-[#161b22] text-zinc-200 font-mono">
                  {`Run ${r.id.split("-")[0].toUpperCase()} (${r.status})`}
                </option>
              ))}
            </select>
          </div>

          {runId && (
            <button
              onClick={handleDownloadZip}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs border border-zinc-700 transition-colors cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{exportCopied ? "Downloaded!" : "Export Deliverables JSON"}</span>
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col rounded-xl border border-[#30363d] bg-[#161b22] overflow-hidden min-h-0">
        <div className="flex items-center border-b border-[#30363d] bg-[#12161f] px-3 gap-1 text-xs font-mono shrink-0 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  const targetTab = tab.id as typeof activeTab;
                  setActiveTab(targetTab);
                  setSearchParams((prev) => {
                    const next = new URLSearchParams(prev);
                    next.set("tab", targetTab);
                    return next;
                  }, { replace: true });
                }}
                className={`flex items-center gap-1.5 py-2.5 px-3 border-b-2 font-medium transition-colors cursor-pointer whitespace-nowrap ${activeTab === tab.id ? "border-emerald-500 text-emerald-400" : "border-transparent text-zinc-400 hover:text-zinc-200"}`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        <div className="flex-1 p-6 overflow-y-auto font-sans text-xs">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-64 gap-3 text-zinc-500">
              <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
              <p className="text-sm">Loading artifacts...</p>
            </div>
          ) : !runId ? (
            <EmptyState message="No run ID provided. Navigate here from a project run page." />
          ) : (
            <>
              {activeTab === "requirements" && <RequirementsTab data={reqData} />}
              {activeTab === "architecture" && <ArchitectureTab data={archData} />}
              {activeTab === "diagrams" && <DiagramsTab data={diagData} />}
              {activeTab === "code" && <CodeTab data={codeData} runId={runId} />}
              {activeTab === "security" && <SecurityTab data={secData} />}
              {activeTab === "tests" && <TestsTab data={testData} />}
              {activeTab === "review" && <ReviewTab data={revData} />}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
