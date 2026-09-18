import React from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { Sidebar } from "../navigation/Sidebar";
import { Play, Sparkles, ShieldCheck, Terminal } from "lucide-react";

export const AppLayout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  // Route title helper
  const getPageTitle = () => {
    const path = location.pathname;
    if (path === "/") return "Overview & Metrics";
    if (path.startsWith("/projects/new")) return "Configure & Launch SDLC Workflow";
    if (path.startsWith("/projects")) return "Managed Projects";
    if (path.startsWith("/live")) return "Live Autonomous SDLC Workspace";
    if (path.startsWith("/artifacts")) return "Artifact Explorer & Deliverables";
    if (path.startsWith("/agents")) return "Specialized Agent Registry";
    if (path.startsWith("/security")) return "Security & Vulnerability Center";
    if (path.startsWith("/qa")) return "Automated QA & Test Execution";
    if (path.startsWith("/review")) return "Architectural & Code Review";
    if (path.startsWith("/model-lab")) return "Multi-Model Benchmarking Lab";
    if (path.startsWith("/settings")) return "Platform Configuration & Credentials";
    return "SDLC Nexus";
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#090c10] text-[#e6edf3] font-sans antialiased">
      {/* Fixed Left Sidebar */}
      <Sidebar />

      {/* Main Workspace Area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Top Operational Bar */}
        <header className="h-14 border-b border-[#30363d] bg-[#0d1117] flex items-center justify-between px-6 shrink-0 z-10">
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono uppercase text-zinc-400">Workspace /</span>
            <h1 className="text-sm font-semibold text-zinc-100 tracking-tight">{getPageTitle()}</h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Live AI Agents Active Badge */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono font-medium">
              <Sparkles className="w-3.5 h-3.5" />
              <span>LIVE AI AGENTS ACTIVE</span>
            </div>

            {/* Zero-CrewAI Guarantee Pill */}
            <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>LangGraph Native Orchestration</span>
            </div>

            {/* Quick Launch Button */}
            <button
              onClick={() => navigate("/projects/new")}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs transition-colors shadow-sm cursor-pointer"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Launch SDLC Run</span>
            </button>
          </div>
        </header>

        {/* Scrollable Page Body */}
        <main className="flex-1 overflow-y-auto bg-[#090c10] p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
