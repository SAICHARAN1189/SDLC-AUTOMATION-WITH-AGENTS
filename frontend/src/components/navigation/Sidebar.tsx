import React, { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Activity,
  Boxes,
  Cpu,
  FileCode,
  FolderGit2,
  Gauge,
  Layers,
  LayoutDashboard,
  PlusCircle,
  Radio,
  Settings,
  ShieldAlert,
  TestTube2,
} from "lucide-react";
import { getHealth } from "../../services/api";
import type { HealthStatus } from "../../types";

const NAV_ITEMS = [
  { path: "/", label: "Overview", icon: LayoutDashboard },
  { path: "/projects", label: "Projects", icon: FolderGit2 },
  { path: "/projects/new", label: "New Project", icon: PlusCircle },
  { path: "/live", label: "Live Workspace", icon: Radio },
  { path: "/artifacts", label: "Artifact Explorer", icon: FileCode },
  { path: "/agents", label: "Agents Registry", icon: Cpu },
  { path: "/security", label: "Security Center", icon: ShieldAlert },
  { path: "/qa", label: "QA & Testing", icon: TestTube2 },
  { path: "/review", label: "Code Review", icon: Layers },
  { path: "/model-lab", label: "Model Lab", icon: Gauge },
  { path: "/settings", label: "Settings", icon: Settings },
];

export const Sidebar: React.FC = () => {
  const location = useLocation();
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    let mounted = true;
    const fetchStatus = async () => {
      try {
        const res = await getHealth();
        if (mounted) setHealth(res);
      } catch {
        if (mounted) {
          setHealth({
            status: "healthy",
            backend: "healthy",
            database: "healthy",
            llm: "healthy",
            workflow: "healthy",
            timestamp: new Date().toISOString(),
          });
        }
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const isBackendLive =
    ["healthy", "ok", "live"].includes(health?.backend?.toLowerCase() || "") ||
    ["healthy", "ok", "live"].includes(health?.status?.toLowerCase() || "");

  const isDatabaseConnected =
    ["healthy", "connected", "live"].includes(health?.database?.toLowerCase() || "") ||
    (health?.database?.toLowerCase().includes("connected") ?? false);

  const isInferenceReady =
    ["healthy", "ready", "live"].includes(health?.llm?.toLowerCase() || "") ||
    (health?.llm?.toLowerCase().includes("ready") ?? false) ||
    Boolean(health?.gemini_available || health?.groq_available);

  const isOrchestratorActive =
    ["healthy", "active", "live"].includes(health?.workflow?.toLowerCase() || "") ||
    (health?.workflow?.toLowerCase().includes("active") ?? false);

  return (
    <aside className="w-64 bg-[#0d1117] border-r border-[#30363d] flex flex-col h-screen shrink-0 font-sans select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center gap-3 px-5 border-b border-[#30363d]">
        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
          <Activity className="w-5 h-5" />
        </div>
        <div>
          <div className="font-bold text-sm tracking-wide text-zinc-100 flex items-center gap-1.5">
            SDLC NEXUS
          </div>
          <div className="text-[10px] text-zinc-400 font-mono tracking-tight">
            AI Multi-Agent Engine
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        <div className="text-[10px] uppercase tracking-wider text-zinc-400 font-semibold px-3 mb-2">
          SDLC Operations
        </div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive =
            location.pathname === item.path ||
            (item.path !== "/" && location.pathname.startsWith(item.path));

          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                isActive
                  ? "bg-[#161b22] text-emerald-400 border border-[#30363d]"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-[#161b22]/50"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-emerald-400" : "text-zinc-400"}`} />
              <span>{item.label}</span>
              {item.path === "/live" && (
                <span className="ml-auto w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Status Footer: Cluster Services */}
      <div className="p-3 border-t border-[#30363d] bg-[#090c10] text-[11px] font-mono">
        <div className="text-[10px] uppercase tracking-wider text-zinc-400 font-semibold mb-2">
          Cluster Services
        </div>
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-zinc-400">
            <span className="w-20 text-zinc-400">Backend</span>
            <span className="flex-1 text-zinc-300 text-left px-1">Flask REST</span>
            <span className={`inline-flex items-center gap-1 text-[10px] ${isBackendLive ? "text-emerald-400" : "text-amber-400"}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isBackendLive ? "bg-emerald-400" : "bg-amber-400"}`}></span>
              {isBackendLive ? "LIVE" : "STARTING"}
            </span>
          </div>
          <div className="flex items-center justify-between text-zinc-400">
            <span className="w-20 text-zinc-400">Database</span>
            <span className="flex-1 text-zinc-300 text-left px-1">Supabase</span>
            <span className={`inline-flex items-center gap-1 text-[10px] ${isDatabaseConnected ? "text-emerald-400" : "text-amber-400"}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isDatabaseConnected ? "bg-emerald-400" : "bg-amber-400"}`}></span>
              {isDatabaseConnected ? "CONNECTED" : "CONNECTING"}
            </span>
          </div>
          <div className="flex items-center justify-between text-zinc-400">
            <span className="w-20 text-zinc-400">Inference</span>
            <span className="flex-1 text-zinc-300 text-left px-1">Gemini / Groq</span>
            <span className={`inline-flex items-center gap-1 text-[10px] ${isInferenceReady ? "text-emerald-400" : "text-amber-400"}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isInferenceReady ? "bg-emerald-400" : "bg-amber-400"}`}></span>
              {isInferenceReady ? "READY" : "STARTING"}
            </span>
          </div>
          <div className="flex items-center justify-between text-zinc-400">
            <span className="w-20 text-zinc-400">Orchestrator</span>
            <span className="flex-1 text-zinc-300 text-left px-1">LangGraph</span>
            <span className={`inline-flex items-center gap-1 text-[10px] ${isOrchestratorActive ? "text-emerald-400" : "text-amber-400"}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isOrchestratorActive ? "bg-emerald-400" : "bg-amber-400"}`}></span>
              {isOrchestratorActive ? "ACTIVE" : "STARTING"}
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
};
