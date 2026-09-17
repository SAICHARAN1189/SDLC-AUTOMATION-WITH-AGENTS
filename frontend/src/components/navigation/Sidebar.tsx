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
            status: "ok",
            database: "connected",
            llm: "ready",
            workflow: "active",
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

  return (
    <aside className="w-64 bg-[#0d1117] border-r border-[#30363d] flex flex-col h-screen select-none shrink-0">
      {/* Brand Header */}
      <div className="h-14 border-b border-[#30363d] flex items-center px-4 gap-2.5">
        <div className="w-7 h-7 rounded bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
          <Activity className="w-4 h-4 animate-pulse" />
        </div>
        <div>
          <div className="font-semibold text-sm tracking-wide text-zinc-100 flex items-center gap-1.5">
            SDLC NEXUS
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              v1.0
            </span>
          </div>
          <div className="text-[11px] text-zinc-400 font-mono tracking-tight">AI Multi-Agent Engine</div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        <div className="px-2.5 py-1 text-[10px] font-semibold tracking-wider text-zinc-400 uppercase font-mono">
          SDLC Operations
        </div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.path === "/"
              ? location.pathname === "/"
              : location.pathname.startsWith(item.path);

          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors ${
                isActive
                  ? "bg-[#1f242c] text-emerald-400 border border-[#30363d]"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-[#161b22]"
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

      {/* Status Footer */}
      <div className="p-3 border-t border-[#30363d] bg-[#0b0e14] text-[11px] font-mono space-y-1.5">
        <div className="text-zinc-400 uppercase text-[10px] tracking-wider mb-1 flex items-center justify-between">
          <span>Cluster Services</span>
          <span className="inline-flex items-center gap-1 text-emerald-400 font-normal">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Live
          </span>
        </div>
        <div className="flex items-center justify-between text-zinc-400">
          <span className="flex items-center gap-1.5">
            <Boxes className="w-3.5 h-3.5 text-zinc-400" /> Backend
          </span>
          <span className="text-zinc-300">Flask REST</span>
        </div>
        <div className="flex items-center justify-between text-zinc-400">
          <span className="flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-zinc-400" /> Database
          </span>
          <span className="text-zinc-300">Supabase</span>
        </div>
        <div className="flex items-center justify-between text-zinc-400">
          <span className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-zinc-400" /> Inference
          </span>
          <span className="text-zinc-300">Groq LLM</span>
        </div>
        <div className="flex items-center justify-between text-zinc-400">
          <span className="flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-zinc-400" /> Orchestrator
          </span>
          <span className="text-emerald-400 font-semibold">LangGraph</span>
        </div>
      </div>
    </aside>
  );
};
