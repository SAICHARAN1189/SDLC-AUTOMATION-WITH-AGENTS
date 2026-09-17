import React, { useEffect, useState } from "react";
import {
  Cpu,
  Wrench,
  Compass,
  Terminal,
  FileCode,
  ShieldCheck,
  TestTube2,
  CheckCircle2,
  Palette,
  Boxes,
  Play,
  Check,
} from "lucide-react";
import { getAgents, runSingleAgent } from "../services/api";
import type { AgentIdentity } from "../types";

const FALLBACK_AGENTS: AgentIdentity[] = [
  {
    name: "requirements_agent",
    display_name: "Requirements Analyst Agent",
    role: "PRD & User Story Specification",
    goal: "Transform high-level software ideas into comprehensive, structured PRDs with functional requirements, acceptance criteria, and risk mitigations.",
    instructions: "Analyze target users, identify stakeholders, derive edge cases, and ensure non-functional specifications are measurable.",
    tools: ["spec_validator", "user_story_generator"],
    model: "Groq Llama-3.3-70B",
  },
  {
    name: "architecture_agent",
    display_name: "System Architect Agent",
    role: "Full-Stack System & Data Modeling",
    goal: "Architect modular distributed systems, defining API contracts, database schemas, authentication mechanisms, and scaling boundaries.",
    instructions: "Design clean service abstractions, select appropriate ORM patterns, and isolate sensitive domains.",
    tools: ["schema_validator", "api_contract_builder"],
    model: "Groq Llama-3.3-70B",
  },
  {
    name: "visual_architecture_agent",
    display_name: "Visual Architecture Agent",
    role: "Mermaid & React Flow Diagram Generator",
    goal: "Generate syntactically validated visual diagrams including system architecture, sequence flows, component graphs, and database ER models.",
    instructions: "Generate valid Mermaid code and verify syntax with deterministic AST parser before committing to state.",
    tools: ["mermaid_validator", "dag_renderer"],
    model: "Groq Llama-3.3-70B",
  },
  {
    name: "developer_agent",
    display_name: "Developer Agent",
    role: "Full-Stack Code Generation & Iterative Rework",
    goal: "Implement production-ready code files matching architecture, and iteratively refactor implementation based on Security, QA, and Review feedback.",
    instructions: "Support INITIAL_IMPLEMENTATION, SECURITY_REWORK, QA_REWORK, and REVIEW_REWORK execution modes.",
    tools: ["file_writer", "project_scaffolder", "dependency_resolver"],
    model: "Groq Llama-3.3-70B",
  },
  {
    name: "security_agent",
    display_name: "Security Scanner Agent",
    role: "Deterministic Static Analysis & Threat Reasoning",
    goal: "Scan source code for SQL injection, hardcoded secrets, XSS, and command injection; produce actionable remediation actions and trigger rework on blocking issues.",
    instructions: "Execute deterministic regex scans, evaluate finding severity, and update LangGraph state with remediation guidance.",
    tools: ["security_scanner", "secret_detector", "syntax_tree_inspector"],
    model: "Groq Llama-3.3-70B",
  },
  {
    name: "qa_agent",
    display_name: "QA & Test Engineer Agent",
    role: "Automated Pytest Suite Generation & Sandbox Execution",
    goal: "Derive unit and integration test suites, execute tests within safe isolated sandbox, and pass structured failure reports to Developer Agent.",
    instructions: "Generate pytest scenarios covering edge cases and acceptance criteria; never fabricate test results.",
    tools: ["test_runner", "sandbox_executor", "coverage_analyzer"],
    model: "Groq Llama-3.3-70B",
  },
  {
    name: "review_agent",
    display_name: "Code Reviewer Agent",
    role: "Senior Engineering Review & Approval Gate",
    goal: "Evaluate architectural integrity, modularity, security remediation, and maintainability to issue definitive PASS or FAIL rework gates.",
    instructions: "Inspect diffs, assess compliance with original PRD, verify absence of blocking findings, and authorize finalization.",
    tools: ["diff_inspector", "compliance_checker"],
    model: "Groq Llama-3.3-70B",
  },
  {
    name: "multi_model_agent",
    display_name: "Multi-Model Comparison Agent",
    role: "Empirical LLM Benchmarking & Latency Analysis",
    goal: "Execute identical benchmark tasks across multiple Groq models to record empirical latency, token length, and technical depth.",
    instructions: "Record actual millisecond timings, token counts, and qualitative scores without inventing artificial metrics.",
    tools: ["groq_benchmark_client", "latency_meter"],
    model: "Multi-Engine (Llama 70B, Mixtral, Llama 8B)",
  },
];

export const Agents: React.FC = () => {
  const [agents, setAgents] = useState<AgentIdentity[]>(FALLBACK_AGENTS);
  const [selectedAgent, setSelectedAgent] = useState<AgentIdentity>(FALLBACK_AGENTS[0]);
  const [testPayload, setTestPayload] = useState('{"task": "Evaluate security posture for payment gateway"}');
  const [runResult, setRunResult] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    getAgents()
      .then((list) => {
        if (list && list.length > 0) {
          setAgents(list);
          setSelectedAgent(list[0]);
        }
      })
      .catch((e) => console.warn(e));
  }, []);

  const handleTestRun = async () => {
    setRunning(true);
    setRunResult(null);
    try {
      let parsed = {};
      try {
        parsed = JSON.parse(testPayload);
      } catch {
        parsed = { prompt: testPayload };
      }
      const res = await runSingleAgent(selectedAgent.name, parsed);
      setRunResult(JSON.stringify(res, null, 2));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setRunResult(`Execution completed in Demo Mode: ${msg}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-emerald-400" /> Specialized Agent Registry ({agents.length})
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Autonomous engineering agents orchestrated via LangGraph. Each agent possesses dedicated instructions, deterministic tools, and typed schemas.
        </p>
      </div>

      {/* Main Container: Agent Cards (Left) + Interactive Sandbox Inspector (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 7 Cols: Agents Grid */}
        <div className="lg:col-span-7 grid grid-cols-1 md:grid-cols-2 gap-3">
          {agents.map((ag) => (
            <div
              key={ag.name}
              onClick={() => setSelectedAgent(ag)}
              className={`p-4 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${
                selectedAgent.name === ag.name
                  ? "border-emerald-500 bg-[#161b22] shadow-[0_0_15px_rgba(16,185,129,0.15)]"
                  : "border-[#30363d] bg-[#0d1117] hover:border-[#8b949e]/40"
              }`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-zinc-200">{ag.display_name || ag.name}</span>
                  <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                </div>
                <div className="text-[10px] font-mono text-emerald-400 mt-0.5">{ag.role}</div>
                <p className="text-[11px] text-zinc-400 font-sans mt-2 line-clamp-3 leading-relaxed">
                  {ag.goal}
                </p>
              </div>

              <div className="mt-3 pt-2.5 border-t border-[#30363d] flex items-center justify-between text-[10px] font-mono text-zinc-400">
                <span>Tools: {ag.tools?.length || 0}</span>
                <span className="text-zinc-300">{ag.model || "Groq Llama-3"}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Right 5 Cols: Selected Agent Detailed Inspector & Sandbox */}
        <div className="lg:col-span-5 rounded-xl border border-[#30363d] bg-[#161b22] p-5 space-y-4 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="border-b border-[#30363d] pb-3">
              <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider">
                Agent Specification
              </span>
              <h2 className="text-base font-bold text-zinc-100 mt-1">
                {selectedAgent.display_name || selectedAgent.name}
              </h2>
              <div className="text-xs text-zinc-400 font-mono mt-0.5">{selectedAgent.role}</div>
            </div>

            <div>
              <div className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1 flex items-center gap-1">
                <Compass className="w-3 h-3 text-zinc-400" /> Goal & Objective
              </div>
              <p className="text-xs text-zinc-300 font-sans leading-relaxed bg-[#0d1117] p-2.5 rounded border border-[#30363d]">
                {selectedAgent.goal}
              </p>
            </div>

            <div>
              <div className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1 flex items-center gap-1">
                <Terminal className="w-3 h-3 text-zinc-400" /> Operational Directives
              </div>
              <p className="text-xs text-zinc-400 font-sans leading-relaxed bg-[#0d1117] p-2.5 rounded border border-[#30363d]">
                {selectedAgent.instructions}
              </p>
            </div>

            <div>
              <div className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1 flex items-center gap-1">
                <Wrench className="w-3 h-3 text-emerald-400" /> Assigned Tools
              </div>
              <div className="flex flex-wrap gap-1.5">
                {selectedAgent.tools?.map((tool) => (
                  <span
                    key={tool}
                    className="px-2 py-0.5 rounded bg-[#0d1117] border border-[#30363d] text-[11px] font-mono text-emerald-300"
                  >
                    {tool}
                  </span>
                ))}
              </div>
            </div>

            {/* Single Agent Sandbox Runner */}
            <div className="pt-2 border-t border-[#30363d] space-y-2 font-mono text-xs">
              <label className="text-[10px] text-zinc-400 uppercase tracking-wider block">
                Single Agent Execution Sandbox
              </label>
              <textarea
                rows={2}
                value={testPayload}
                onChange={(e) => setTestPayload(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded bg-[#0d1117] border border-[#30363d] text-zinc-200 text-xs focus:outline-none"
              />
              <button
                onClick={handleTestRun}
                disabled={running}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs transition-colors cursor-pointer disabled:opacity-50"
              >
                <Play className="w-3 h-3 fill-current" />
                <span>{running ? "Executing Agent..." : "Trigger Single Agent Run"}</span>
              </button>

              {runResult && (
                <pre className="mt-2 p-3 rounded bg-[#0d1117] border border-[#30363d] text-[11px] text-emerald-400 overflow-x-auto whitespace-pre-wrap max-h-48">
                  {runResult}
                </pre>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
