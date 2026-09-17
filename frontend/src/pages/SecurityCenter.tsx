import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  RotateCcw,
  FileCode2,
  CheckCircle,
  Cpu,
  Info,
  ExternalLink,
} from "lucide-react";
import { getSecurityReport } from "../services/api";
import type { SecurityOutput, VulnerabilityFinding } from "../types";

export const SecurityCenter: React.FC = () => {
  const [searchParams] = useSearchParams();
  const runId = searchParams.get("run_id");

  const [report, setReport] = useState<SecurityOutput | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<VulnerabilityFinding | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const fetchReport = async () => {
      if (!runId) {
        // Provide sample faculty demo findings if no run_id
        setReport({
          overall_status: "PASS",
          severity_summary: { critical: 0, high: 2, medium: 1, low: 0 },
          vulnerabilities: [
            {
              id: "sec-001",
              category: "sql_injection",
              severity: "HIGH",
              description: "Direct SQL string interpolation detected in order lookup query without query parameterization.",
              evidence: 'query = f"SELECT * FROM orders WHERE customer_id = \'{cust_id}\'"',
              affected_file: "backend/api/orders.py",
              affected_line: 42,
              remediation: "Use SQLAlchemy or parameterized placeholders with cursor.execute(query, (cust_id,))",
              confidence: 0.95,
              source: "DETERMINISTIC_FINDING",
              status: "RESOLVED",
              caused_rework: true,
            },
            {
              id: "sec-002",
              category: "hardcoded_secret",
              severity: "HIGH",
              description: "Hardcoded API secret token found in mock payment provider configuration.",
              evidence: 'PAYMENT_SECRET = "sk_live_9381830184019284"',
              affected_file: "backend/config/payments.py",
              affected_line: 14,
              remediation: "Extract secret credentials into environment variables (PAYMENT_SECRET) and read via Pydantic settings.",
              confidence: 0.98,
              source: "DETERMINISTIC_FINDING",
              status: "RESOLVED",
              caused_rework: true,
            },
            {
              id: "sec-003",
              category: "insecure_cryptography",
              severity: "MEDIUM",
              description: "Legacy MD5 hashing used for customer cache key generation.",
              evidence: "hashlib.md5(cache_key.encode()).hexdigest()",
              affected_file: "backend/utils/cache.py",
              affected_line: 28,
              remediation: "Upgrade to SHA-256 (hashlib.sha256) for collision resistance.",
              confidence: 0.88,
              source: "DETERMINISTIC_FINDING",
              status: "OPEN",
              caused_rework: false,
            },
          ],
          recommendations: [
            "Maintain strict separation of payment credentials using environment configuration.",
            "Enforce SQLAlchemy ORM queries to prevent raw string interpolation.",
            "Apply automated dependency vulnerability scanning in CI/CD pipeline.",
          ],
          remediation_actions: [
            "Developer Agent refactored orders.py to use parameterized queries.",
            "Payment secret moved to .env with Settings validator.",
          ],
          affected_files: ["backend/api/orders.py", "backend/config/payments.py", "backend/utils/cache.py"],
          confidence: 0.92,
          scan_timestamp: new Date().toISOString(),
          disclaimer:
            "DISCLAIMER: This automated scan combines deterministic pattern matching with LLM contextual reasoning. It is designed for SDLC feedback and does not replace certified professional penetration testing.",
        });
        setLoading(false);
        return;
      }

      try {
        const data = await getSecurityReport(runId);
        if (mounted && data) setReport(data);
      } catch (e) {
        console.warn(e);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchReport();
    return () => {
      mounted = false;
    };
  }, [runId]);

  const findings = report?.vulnerabilities || [];
  const filteredFindings = findings.filter(
    (f) => filterSeverity === "ALL" || f.severity === filterSeverity
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header & Disclaimer */}
      <div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-amber-400" /> Security & Vulnerability Center
            </h1>
            <p className="text-xs text-zinc-400 mt-1">
              Dual-layer deterministic static analysis + LLM semantic threat assessment with automatic rework triggers.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`px-3 py-1 rounded text-xs font-mono font-semibold uppercase border ${
                report?.overall_status === "PASS"
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                  : "bg-rose-500/10 text-rose-300 border-rose-500/30"
              }`}
            >
              Overall: {report?.overall_status || "ANALYZING"}
            </span>
          </div>
        </div>

        {/* Certified disclaimer notice */}
        <div className="mt-3 p-3 rounded-lg bg-amber-500/5 border border-amber-500/20 text-amber-200/90 text-xs flex items-start gap-2 font-sans">
          <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <span>
            {report?.disclaimer ||
              "DISCLAIMER: This security assessment combines deterministic pattern matching with LLM reasoning for iterative developer remediation. It does not replace a certified enterprise security audit."}
          </span>
        </div>
      </div>

      {/* Severity Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="p-3.5 rounded-lg bg-[#161b22] border border-rose-500/30">
          <div className="text-[11px] text-zinc-400 font-mono">Critical Findings</div>
          <div className="text-2xl font-bold font-mono text-rose-400 mt-1">
            {report?.severity_summary.critical || 0}
          </div>
          <div className="text-[10px] text-zinc-400 mt-0.5">Blocking execution</div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#161b22] border border-amber-500/30">
          <div className="text-[11px] text-zinc-400 font-mono">High Severity</div>
          <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
            {report?.severity_summary.high || 0}
          </div>
          <div className="text-[10px] text-zinc-400 mt-0.5">Triggered Rework</div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#161b22] border border-yellow-500/30">
          <div className="text-[11px] text-zinc-400 font-mono">Medium Severity</div>
          <div className="text-2xl font-bold font-mono text-yellow-300 mt-1">
            {report?.severity_summary.medium || 0}
          </div>
          <div className="text-[10px] text-zinc-400 mt-0.5">Warning alerts</div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#161b22] border border-sky-500/30">
          <div className="text-[11px] text-zinc-400 font-mono">Low / Informational</div>
          <div className="text-2xl font-bold font-mono text-sky-400 mt-1">
            {report?.severity_summary.low || 0}
          </div>
          <div className="text-[10px] text-zinc-400 mt-0.5">Best practices</div>
        </div>

        <div className="p-3.5 rounded-lg bg-[#161b22] border border-emerald-500/30">
          <div className="text-[11px] text-zinc-400 font-mono">Resolved via Rework</div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
            {findings.filter((f) => f.status === "RESOLVED").length}
          </div>
          <div className="text-[10px] text-zinc-400 mt-0.5">Remediated by Dev</div>
        </div>
      </div>

      {/* Main Content: Findings Table (Left) + Finding Details (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 7 Cols: Findings List */}
        <div className="lg:col-span-7 rounded-xl border border-[#30363d] bg-[#161b22] overflow-hidden flex flex-col">
          <div className="p-3.5 border-b border-[#30363d] bg-[#12161f] flex items-center justify-between">
            <span className="text-xs font-semibold text-zinc-200">Discovered Vulnerabilities & Sinks</span>
            <div className="flex items-center gap-1.5 font-mono text-[11px]">
              {["ALL", "HIGH", "MEDIUM", "LOW"].map((lvl) => (
                <button
                  key={lvl}
                  onClick={() => setFilterSeverity(lvl)}
                  className={`px-2 py-0.5 rounded border transition-colors ${
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

          <div className="divide-y divide-[#30363d] overflow-y-auto max-h-[500px]">
            {filteredFindings.length === 0 ? (
              <div className="p-8 text-center text-xs text-zinc-400 font-mono">
                No vulnerabilities matching current filter.
              </div>
            ) : (
              filteredFindings.map((f) => (
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
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase ${
                          f.severity === "CRITICAL" || f.severity === "HIGH"
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                            : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                        }`}
                      >
                        {f.severity}
                      </span>
                      <span className="text-xs font-semibold text-zinc-200">{f.category}</span>
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

                  <p className="mt-1 text-xs text-zinc-300 font-sans leading-relaxed line-clamp-2">
                    {f.description}
                  </p>

                  <div className="mt-2 text-[11px] font-mono text-zinc-400 flex items-center gap-2">
                    <FileCode2 className="w-3.5 h-3.5 text-zinc-400" />
                    <span>{f.affected_file}:{f.affected_line}</span>
                    <span className="ml-auto text-[10px] text-zinc-400 font-sans uppercase">
                      Source: {f.source}
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
                    ID: {selectedFinding.id}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-zinc-100 mt-1 capitalize">
                  {selectedFinding.category.replace("_", " ")}
                </h3>
              </div>

              <div>
                <div className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1">
                  Location & Evidence
                </div>
                <div className="p-2 rounded bg-[#0d1117] border border-[#30363d] font-mono text-xs text-zinc-300">
                  <div className="text-emerald-400 text-[11px] mb-1">
                    {selectedFinding.affected_file} (Line {selectedFinding.affected_line})
                  </div>
                  <pre className="p-2 bg-black/40 rounded overflow-x-auto text-[11px] text-rose-300 whitespace-pre-wrap">
                    {selectedFinding.evidence}
                  </pre>
                </div>
              </div>

              <div>
                <div className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1">
                  Threat Description
                </div>
                <p className="text-xs text-zinc-300 font-sans leading-relaxed bg-[#0d1117] p-3 rounded border border-[#30363d]">
                  {selectedFinding.description}
                </p>
              </div>

              <div>
                <div className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider mb-1 flex items-center gap-1">
                  <CheckCircle className="w-3.5 h-3.5" /> Prescribed Remediation
                </div>
                <p className="text-xs text-emerald-300 font-sans leading-relaxed bg-emerald-500/5 p-3 rounded border border-emerald-500/20">
                  {selectedFinding.remediation}
                </p>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center p-8 text-zinc-400 font-mono text-xs text-center">
              <ShieldCheck className="w-8 h-8 text-zinc-400 mb-2" />
              <span>Select any vulnerability finding on the left to inspect evidence and remediation guidance.</span>
            </div>
          )}

          {/* Remediation Action Summary */}
          <div className="mt-4 pt-3 border-t border-[#30363d] text-[11px] font-mono text-zinc-400 flex items-center justify-between">
            <span>Detection Confidence: <strong>{((selectedFinding?.confidence || 0.95) * 100).toFixed(0)}%</strong></span>
            <span>Origin: <strong>{selectedFinding?.source || "DETERMINISTIC"}</strong></span>
          </div>
        </div>
      </div>
    </div>
  );
};
