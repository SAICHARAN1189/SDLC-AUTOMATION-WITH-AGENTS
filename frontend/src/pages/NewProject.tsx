import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Boxes,
  Play,
  Sparkles,
  Sliders,
  ShieldAlert,
  TestTube2,
  CheckCircle,
  Cpu,
  Layers,
  HelpCircle,
} from "lucide-react";
import { createProject, createRun } from "../services/api";

const PRESETS = [
  {
    id: "food_delivery",
    title: "Secure Food Delivery Platform (Faculty Demo)",
    description:
      "Build a secure online food delivery platform with customer ordering, driver real-time tracking, restaurant menu management, and strict payment card isolation.",
    badge: "Recommended Faculty Demo",
  },
  {
    id: "telemedicine",
    title: "Healthcare Telemedicine & Patient Portal",
    description:
      "Build a HIPAA-compliant telemedicine platform with encrypted patient records, doctor scheduling, video consultation tokens, and audit logs.",
    badge: "HIPAA Compliant",
  },
  {
    id: "payment_gateway",
    title: "High-Throughput FinTech Payment Gateway",
    description:
      "Build an enterprise payment gateway supporting idempotency keys, webhook signature verification, PCI-DSS tokenization, and anomaly fraud detection.",
    badge: "FinTech Standard",
  },
];

export const NewProject: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [name, setName] = useState("Nexus Secure Food Delivery");
  const [idea, setIdea] = useState(
    "Build a secure online food delivery platform with customer ordering, driver real-time tracking, restaurant menu management, and strict payment card isolation."
  );
  const [executionMode, setExecutionMode] = useState<"AUTONOMOUS" | "STEP_BY_STEP">("AUTONOMOUS");
  const [primaryModel, setPrimaryModel] = useState("groq/llama-3.3-70b-versatile");
  const [securityMaxRetries, setSecurityMaxRetries] = useState(2);
  const [qaMaxRetries, setQaMaxRetries] = useState(2);
  const [reviewMaxRetries, setReviewMaxRetries] = useState(2);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check query params for preset selection
  useEffect(() => {
    const presetParam = searchParams.get("preset");
    if (presetParam) {
      const preset = PRESETS.find((p) => p.id === presetParam);
      if (preset) {
        setName(`Nexus ${preset.title.split("(")[0].trim()}`);
        setIdea(preset.description);
      }
    }
  }, [searchParams]);

  const handlePresetSelect = (preset: (typeof PRESETS)[0]) => {
    setName(`Nexus ${preset.title.split("(")[0].trim()}`);
    setIdea(preset.description);
  };

  const handleLaunch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !idea.trim()) {
      setError("Please provide a project name and software specification idea.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // 1. Create project
      const project = await createProject({ name: name.trim(), idea: idea.trim() });

      // 2. Launch initial run
      const run = await createRun(project.id, {
        execution_mode: executionMode,
      });

      // 3. Navigate to live workspace
      navigate(`/live?run_id=${run.id}&project_id=${project.id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Failed to launch SDLC pipeline: ${msg}`);
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-zinc-100">Configure & Launch SDLC Workflow</h1>
        <p className="text-xs text-zinc-400 mt-1">
          Specify your software concept to initiate the autonomous multi-agent engineering lifecycle.
        </p>
      </div>

      {/* Preset Recommendation Cards */}
      <div className="space-y-2">
        <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Quick-Start Demo Presets
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {PRESETS.map((preset) => (
            <div
              key={preset.id}
              onClick={() => handlePresetSelect(preset)}
              className="p-3.5 rounded-lg bg-[#161b22] border border-[#30363d] hover:border-emerald-500/50 transition-all cursor-pointer flex flex-col justify-between"
            >
              <div>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  {preset.badge}
                </span>
                <h2 className="text-xs font-semibold text-zinc-200 mt-2">{preset.title}</h2>
                <p className="text-[11px] text-zinc-400 font-sans mt-1 line-clamp-3 leading-relaxed">
                  {preset.description}
                </p>
              </div>
              <div className="mt-3 text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                <span>Select preset</span> &rarr;
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Configuration Form */}
      <form onSubmit={handleLaunch} className="space-y-5 rounded-xl border border-[#30363d] bg-[#161b22] p-6 shadow-md">
        {error && (
          <div className="p-3 rounded-md bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs font-mono">
            {error}
          </div>
        )}

        {/* Project Name */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-zinc-200 flex items-center justify-between">
            <span>Project Identifier</span>
            <span className="text-[10px] font-mono text-zinc-400">Required</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Nexus Food Delivery Platform"
            className="w-full px-3 py-2 rounded-md bg-[#0d1117] border border-[#30363d] text-zinc-100 text-xs focus:outline-none focus:border-emerald-500 font-mono"
            required
          />
        </div>

        {/* Software Idea / Specification */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-zinc-200 flex items-center justify-between">
            <span>Natural-Language Software Idea / Architecture Goal</span>
            <span className="text-[10px] font-mono text-zinc-400">Fed to Requirements Analyst</span>
          </label>
          <textarea
            rows={4}
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="Describe the application, target audience, core capabilities, and architectural constraints..."
            className="w-full px-3 py-2 rounded-md bg-[#0d1117] border border-[#30363d] text-zinc-100 text-xs focus:outline-none focus:border-emerald-500 font-sans leading-relaxed"
            required
          />
        </div>

        {/* Execution Mode Selection */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-zinc-200">Execution Mode</label>
          <div className="grid grid-cols-2 gap-3">
            <div
              onClick={() => setExecutionMode("AUTONOMOUS")}
              className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                executionMode === "AUTONOMOUS"
                  ? "border-emerald-500 bg-emerald-500/10 text-zinc-100"
                  : "border-[#30363d] bg-[#0d1117] text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <div className="flex items-center justify-between text-xs font-semibold">
                <span>Full Autonomous SDLC</span>
                {executionMode === "AUTONOMOUS" && <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />}
              </div>
              <p className="text-[11px] font-sans mt-1 text-zinc-400 leading-snug">
                Executes all 8 engineering stages continuously with automatic feedback loops and rework resolution.
              </p>
            </div>

            <div
              onClick={() => setExecutionMode("STEP_BY_STEP")}
              className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                executionMode === "STEP_BY_STEP"
                  ? "border-emerald-500 bg-emerald-500/10 text-zinc-100"
                  : "border-[#30363d] bg-[#0d1117] text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <div className="flex items-center justify-between text-xs font-semibold">
                <span>Step-by-Step Interactive</span>
                {executionMode === "STEP_BY_STEP" && <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />}
              </div>
              <p className="text-[11px] font-sans mt-1 text-zinc-400 leading-snug">
                Pauses after key stages to allow manual inspection and stage-by-stage authorization.
              </p>
            </div>
          </div>
        </div>

        {/* Advanced Settings: Models & Retries */}
        <div className="pt-2 border-t border-[#30363d] space-y-3">
          <div className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
            <Sliders className="w-3.5 h-3.5" /> Advanced Engineering Parameters
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs font-mono">
            <div>
              <label className="text-[11px] text-zinc-400 block mb-1">Primary LLM</label>
              <select
                value={primaryModel}
                onChange={(e) => setPrimaryModel(e.target.value)}
                className="w-full px-2 py-1.5 rounded bg-[#0d1117] border border-[#30363d] text-zinc-200 text-xs focus:outline-none"
              >
                <option value="groq/llama-3.3-70b-versatile">Groq Llama-3.3-70B</option>
                <option value="groq/mixtral-8x7b-32768">Groq Mixtral-8x7B</option>
                <option value="groq/llama-3.1-8b-instant">Groq Llama-3.1-8B (Fast)</option>
                <option value="demo-deterministic">Demo Deterministic</option>
              </select>
            </div>

            <div>
              <label className="text-[11px] text-zinc-400 block mb-1">Security Retries</label>
              <input
                type="number"
                min={1}
                max={5}
                value={securityMaxRetries}
                onChange={(e) => setSecurityMaxRetries(parseInt(e.target.value) || 2)}
                className="w-full px-2 py-1.5 rounded bg-[#0d1117] border border-[#30363d] text-zinc-200 text-xs focus:outline-none"
              />
            </div>

            <div>
              <label className="text-[11px] text-zinc-400 block mb-1">QA Max Retries</label>
              <input
                type="number"
                min={1}
                max={5}
                value={qaMaxRetries}
                onChange={(e) => setQaMaxRetries(parseInt(e.target.value) || 2)}
                className="w-full px-2 py-1.5 rounded bg-[#0d1117] border border-[#30363d] text-zinc-200 text-xs focus:outline-none"
              />
            </div>

            <div>
              <label className="text-[11px] text-zinc-400 block mb-1">Review Retries</label>
              <input
                type="number"
                min={1}
                max={5}
                value={reviewMaxRetries}
                onChange={(e) => setReviewMaxRetries(parseInt(e.target.value) || 2)}
                className="w-full px-2 py-1.5 rounded bg-[#0d1117] border border-[#30363d] text-zinc-200 text-xs focus:outline-none"
              />
            </div>
          </div>
        </div>

        {/* Submit CTA */}
        <div className="pt-4 flex items-center justify-between">
          <span className="text-[11px] text-zinc-400 font-mono">
            Orchestration powered by native <strong>LangGraph</strong> state machine.
          </span>
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs transition-colors shadow-md disabled:opacity-50 cursor-pointer"
          >
            {loading ? (
              <span>Initializing Workflow...</span>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Launch SDLC Pipeline</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
