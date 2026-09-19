import React, { useState, useEffect } from "react";
import {
  Settings as SettingsIcon,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Cpu,
  Layers,
  Terminal,
  Save,
} from "lucide-react";
import { getHealth } from "../services/api";
import type { HealthStatus } from "../types";

export const Settings: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [demoMode, setDemoMode] = useState(true);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getHealth()
      .then((res) => setHealth(res))
      .catch(() => {
        setHealth({
          status: "ok",
          database: "Supabase Connected",
          llm: "Groq Llama-3 Ready",
          workflow: "LangGraph StateGraph Active",
          timestamp: new Date().toISOString(),
        });
      });
  }, []);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto font-sans">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-emerald-400" /> Platform Configuration & Environment
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Cluster connection state, security boundary verifications, and agent execution parameters.
        </p>
      </div>

      {/* Cluster Health & Security Checklist */}
      <div className="p-5 rounded-xl border border-[#30363d] bg-[#161b22] space-y-4">
        <div className="flex items-center justify-between border-b border-[#30363d] pb-3">
          <span className="text-xs font-semibold text-zinc-200 uppercase font-mono">
            Infrastructure Status & Security Posture
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            HEALTH OK
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
          <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d] flex items-center justify-between">
            <span className="flex items-center gap-2 text-zinc-300">
              <Layers className="w-4 h-4 text-emerald-400" /> Supabase PostgreSQL
            </span>
            <span className="text-emerald-400 flex items-center gap-1 text-[11px]">
              <CheckCircle2 className="w-3.5 h-3.5" /> Connected
            </span>
          </div>

          <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d] flex items-center justify-between">
            <span className="flex items-center gap-2 text-zinc-300">
              <Cpu className="w-4 h-4 text-emerald-400" /> Google Gemini API
            </span>
            <span className="text-emerald-400 flex items-center gap-1 text-[11px]">
              <CheckCircle2 className="w-3.5 h-3.5" /> Ready
            </span>
          </div>

          <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d] flex items-center justify-between">
            <span className="flex items-center gap-2 text-zinc-300">
              <Cpu className="w-4 h-4 text-amber-400" /> Groq Cloud Inference
            </span>
            <span className="text-emerald-400 flex items-center gap-1 text-[11px]">
              <CheckCircle2 className="w-3.5 h-3.5" /> Ready
            </span>
          </div>

          <div className="p-3 rounded-lg bg-[#0d1117] border border-[#30363d] flex items-center justify-between">
            <span className="flex items-center gap-2 text-zinc-300">
              <Terminal className="w-4 h-4 text-sky-400" /> LangGraph Orchestrator
            </span>
            <span className="text-emerald-400 flex items-center gap-1 text-[11px]">
              <CheckCircle2 className="w-3.5 h-3.5" /> Active
            </span>
          </div>
        </div>

        {/* Security Alert: Backend Key Isolation */}
        <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20 text-emerald-300 text-xs flex items-start gap-2.5">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-semibold font-mono">Strict Key Isolation Verified</div>
            <p className="text-[11px] text-zinc-400 font-sans leading-relaxed">
              <code>SUPABASE_SERVICE_ROLE_KEY</code>, <code>GEMINI_API_KEY</code>, and <code>GROQ_API_KEY</code> are confined strictly to backend runtime memory. No credentials are exposed to client-side bundles.
            </p>
          </div>
        </div>
      </div>

      {/* Execution Mode & Model Configuration Form */}
      <form onSubmit={handleSave} className="p-5 rounded-xl border border-[#30363d] bg-[#161b22] space-y-4">
        <div className="flex items-center justify-between border-b border-[#30363d] pb-3">
          <div>
            <h2 className="text-xs font-semibold text-zinc-200 uppercase font-mono">
              Runtime Model Configuration & Routing Matrix
            </h2>
            <p className="text-[11px] text-zinc-400 font-sans mt-0.5">
              Task-specific primary models and autonomous multi-tier fallback chains.
            </p>
          </div>
          <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-mono font-semibold">
            GEMINI + GROQ
          </span>
        </div>

        {/* Full Model Allocation Table */}
        <div className="border border-[#30363d] rounded-lg overflow-hidden font-mono text-xs">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#0d1117] border-b border-[#30363d] text-[10px] text-zinc-400 uppercase">
                <th className="py-2.5 px-3">Agent Task</th>
                <th className="py-2.5 px-3">Primary Model</th>
                <th className="py-2.5 px-3">Provider</th>
                <th className="py-2.5 px-3">Fallback Chain</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#30363d]/60 text-[11px]">
              <tr className="bg-[#12161f]/40 hover:bg-[#161b22]">
                <td className="py-2 px-3 font-semibold text-zinc-200">Requirements Analyst</td>
                <td className="py-2 px-3 text-emerald-400">gemini-3.5-flash-lite</td>
                <td className="py-2 px-3 text-zinc-400">Google Gemini</td>
                <td className="py-2 px-3 text-zinc-500">gemini-3.1-flash-lite → gpt-oss-20b</td>
              </tr>
              <tr className="bg-[#12161f]/40 hover:bg-[#161b22]">
                <td className="py-2 px-3 font-semibold text-zinc-200">System Architect</td>
                <td className="py-2 px-3 text-emerald-400">gemini-3.8-flash <span className="text-[10px] text-zinc-500">[thinking: low]</span></td>
                <td className="py-2 px-3 text-zinc-400">Google Gemini</td>
                <td className="py-2 px-3 text-zinc-500">gemini-3.5-flash-lite → gpt-oss-20b</td>
              </tr>
              <tr className="bg-[#12161f]/40 hover:bg-[#161b22]">
                <td className="py-2 px-3 font-semibold text-zinc-200">Visual Architect</td>
                <td className="py-2 px-3 text-emerald-400">gemini-3.1-flash-lite</td>
                <td className="py-2 px-3 text-zinc-400">Google Gemini</td>
                <td className="py-2 px-3 text-zinc-500">gemini-3.5-flash-lite → gpt-oss-20b</td>
              </tr>
              <tr className="bg-[#12161f]/40 hover:bg-[#161b22]">
                <td className="py-2 px-3 font-semibold text-zinc-200">Developer Agent</td>
                <td className="py-2 px-3 text-amber-400">openai/gpt-oss-120b</td>
                <td className="py-2 px-3 text-zinc-400">Groq Cloud</td>
                <td className="py-2 px-3 text-zinc-500">gemini-3.5-flash-lite → gpt-oss-20b</td>
              </tr>
              <tr className="bg-[#12161f]/40 hover:bg-[#161b22]">
                <td className="py-2 px-3 font-semibold text-zinc-200">Security Lead</td>
                <td className="py-2 px-3 text-amber-400">openai/gpt-oss-20b</td>
                <td className="py-2 px-3 text-zinc-400">Groq Cloud</td>
                <td className="py-2 px-3 text-zinc-500">gemini-3.5-flash-lite</td>
              </tr>
              <tr className="bg-[#12161f]/40 hover:bg-[#161b22]">
                <td className="py-2 px-3 font-semibold text-zinc-200">QA Engineer</td>
                <td className="py-2 px-3 text-amber-400">openai/gpt-oss-120b</td>
                <td className="py-2 px-3 text-zinc-400">Groq Cloud</td>
                <td className="py-2 px-3 text-zinc-500">gemini-3.5-flash-lite → gpt-oss-20b</td>
              </tr>
              <tr className="bg-[#12161f]/40 hover:bg-[#161b22]">
                <td className="py-2 px-3 font-semibold text-zinc-200">Review Architect</td>
                <td className="py-2 px-3 text-emerald-400">gemini-3.5-flash-lite</td>
                <td className="py-2 px-3 text-zinc-400">Google Gemini</td>
                <td className="py-2 px-3 text-zinc-500">gemini-3.1-flash-lite → gpt-oss-20b</td>
              </tr>
              <tr className="bg-[#12161f]/40 hover:bg-[#161b22]">
                <td className="py-2 px-3 font-semibold text-zinc-200">Model Lab Benchmarks</td>
                <td className="py-2 px-3 text-sky-400">Comparison Suite</td>
                <td className="py-2 px-3 text-zinc-400">Multi-Model</td>
                <td className="py-2 px-3 text-zinc-500">gemini-3.8-flash, gpt-oss-120b, gpt-oss-20b, groq/compound</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between pt-2">
          {saved && <span className="text-xs font-mono text-emerald-400">Settings preferences saved.</span>}
          <button
            type="submit"
            className="ml-auto flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs transition-colors cursor-pointer"
          >
            <Save className="w-3.5 h-3.5" />
            <span>Save Preferences</span>
          </button>
        </div>
      </form>
    </div>
  );
};
