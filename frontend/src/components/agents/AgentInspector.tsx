import React, { useState } from "react";
import {
  Cpu,
  Wrench,
  Compass,
  CheckCircle,
  FileCode,
  Terminal,
  ChevronDown,
  ChevronRight,
  Code2,
  Clock,
  RotateCcw,
} from "lucide-react";
import type { AgentIdentity, StageStatus } from "../../types";

interface AgentInspectorProps {
  agent?: AgentIdentity;
  stageKey?: string;
  status?: StageStatus;
  currentTask?: string;
  duration?: string;
  retries?: number;
  inputs?: Record<string, unknown>;
  outputs?: Record<string, unknown>;
  onClose?: () => void;
}

export const AgentInspector: React.FC<AgentInspectorProps> = ({
  agent,
  stageKey = "requirements_node",
  status = "WAITING",
  currentTask,
  duration = "0.0s",
  retries = 0,
  inputs,
  outputs,
}) => {
  const [activeTab, setActiveTab] = useState<"overview" | "inputs" | "outputs" | "tools">("overview");
  const [rawJson, setRawJson] = useState(false);

  if (!agent) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-zinc-400 font-mono text-xs bg-[#0b0e14] rounded-lg border border-[#30363d]">
        <Cpu className="w-8 h-8 text-zinc-400 mb-2 animate-pulse" />
        <span>Select an agent node on the workflow canvas to inspect runtime state.</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[#0b0e14] rounded-lg border border-[#30363d] overflow-hidden text-xs">
      {/* Inspector Header */}
      <div className="h-12 border-b border-[#30363d] bg-[#161b22] px-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Cpu className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="font-semibold text-zinc-200 text-xs">{agent.display_name || agent.name}</div>
            <div className="text-[10px] text-zinc-400 font-mono">{agent.role}</div>
          </div>
        </div>

        {/* State Badge */}
        <div className="flex items-center gap-2 font-mono text-[10px]">
          <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
            {status}
          </span>
          {retries > 0 && (
            <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 flex items-center gap-1">
              <RotateCcw className="w-2.5 h-2.5" /> Rework #{retries}
            </span>
          )}
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex items-center border-b border-[#30363d] bg-[#12161f] px-3 gap-2 font-mono text-[11px] shrink-0">
        {(["overview", "inputs", "outputs", "tools"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`py-2 px-2 border-b-2 font-medium capitalize transition-colors ${
              activeTab === tab
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            {tab}
          </button>
        ))}

        <div className="ml-auto flex items-center gap-1">
          <button
            onClick={() => setRawJson(!rawJson)}
            className={`px-1.5 py-0.5 rounded text-[10px] border transition-colors ${
              rawJson
                ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                : "bg-zinc-800/40 text-zinc-400 border-zinc-700 hover:text-zinc-300"
            }`}
          >
            Raw JSON
          </button>
        </div>
      </div>

      {/* Tab Contents */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4 font-mono">
        {rawJson ? (
          <pre className="text-[11px] text-zinc-300 bg-[#161b22] p-3 rounded border border-[#30363d] overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify({ agent, status, duration, retries, inputs, outputs }, null, 2)}
          </pre>
        ) : (
          <>
            {activeTab === "overview" && (
              <div className="space-y-3.5">
                <div>
                  <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1 flex items-center gap-1">
                    <Compass className="w-3 h-3 text-zinc-400" /> Goal & Objective
                  </div>
                  <p className="text-xs text-zinc-300 font-sans leading-relaxed bg-[#161b22] p-2.5 rounded border border-[#30363d]">
                    {agent.goal}
                  </p>
                </div>

                <div>
                  <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1 flex items-center gap-1">
                    <Terminal className="w-3 h-3 text-zinc-400" /> Operational Instructions
                  </div>
                  <p className="text-xs text-zinc-400 font-sans leading-relaxed bg-[#161b22]/60 p-2.5 rounded border border-[#30363d]/60">
                    {agent.instructions}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div className="p-2 rounded bg-[#161b22] border border-[#30363d]">
                    <div className="text-zinc-400 text-[10px]">Inference Model</div>
                    <div className="text-emerald-400 font-semibold">{agent.model || "Groq Llama-3-70B"}</div>
                  </div>
                  <div className="p-2 rounded bg-[#161b22] border border-[#30363d]">
                    <div className="text-zinc-400 text-[10px]">Stage Runtime</div>
                    <div className="text-zinc-200 flex items-center gap-1">
                      <Clock className="w-3 h-3 text-zinc-400" /> {duration}
                    </div>
                  </div>
                </div>

                {currentTask && (
                  <div>
                    <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1">Current Task</div>
                    <div className="text-xs text-zinc-200 bg-[#161b22] p-2.5 rounded border border-[#30363d]">
                      {currentTask}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "inputs" && (
              <div className="space-y-2">
                <div className="text-[10px] text-zinc-400 uppercase tracking-wider">State Injected Inputs</div>
                {inputs && Object.keys(inputs).length > 0 ? (
                  <pre className="text-[11px] text-zinc-300 bg-[#161b22] p-3 rounded border border-[#30363d] overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(inputs, null, 2)}
                  </pre>
                ) : (
                  <div className="text-zinc-400 p-4 text-center">No input payload captured for this stage.</div>
                )}
              </div>
            )}

            {activeTab === "outputs" && (
              <div className="space-y-2">
                <div className="text-[10px] text-zinc-400 uppercase tracking-wider">Produced Structured Artifact</div>
                {outputs && Object.keys(outputs).length > 0 ? (
                  <pre className="text-[11px] text-zinc-300 bg-[#161b22] p-3 rounded border border-[#30363d] overflow-x-auto whitespace-pre-wrap max-h-96">
                    {JSON.stringify(outputs, null, 2)}
                  </pre>
                ) : (
                  <div className="text-zinc-400 p-4 text-center">Stage output pending completion.</div>
                )}
              </div>
            )}

            {activeTab === "tools" && (
              <div className="space-y-2">
                <div className="text-[10px] text-zinc-400 uppercase tracking-wider">Permitted Deterministic Tools</div>
                <div className="space-y-1.5">
                  {agent.tools && agent.tools.length > 0 ? (
                    agent.tools.map((tool) => (
                      <div
                        key={tool}
                        className="flex items-center gap-2 p-2 rounded bg-[#161b22] border border-[#30363d] text-zinc-300"
                      >
                        <Wrench className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="font-semibold">{tool}</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-zinc-400">No specific external tools assigned.</div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
