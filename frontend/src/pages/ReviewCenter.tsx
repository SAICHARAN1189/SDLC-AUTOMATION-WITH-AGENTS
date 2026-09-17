import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  CheckCircle2,
  AlertTriangle,
  Layers,
  FileCheck,
  RotateCcw,
  Sparkles,
  ShieldCheck,
  Code2,
} from "lucide-react";
import { getReviewReport } from "../services/api";
import type { ReviewOutput } from "../types";

export const ReviewCenter: React.FC = () => {
  const [searchParams] = useSearchParams();
  const runId = searchParams.get("run_id");

  const [review, setReview] = useState<ReviewOutput | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const fetchReport = async () => {
      if (!runId) {
        setReview({
          review_status: "APPROVED",
          blocking_issues: [],
          findings: [
            {
              id: "rev-01",
              category: "architecture_consistency",
              severity: "INFO",
              title: "Modular Clean Separation",
              description: "The service layer correctly isolates payment tokenization from driver dispatch models.",
              recommendation: "Preserve repository interfaces for future database abstraction.",
            },
            {
              id: "rev-02",
              category: "security_remediation",
              severity: "INFO",
              title: "Remediated SQL Injection",
              description: "Developer Agent successfully refactored orders queries to parameterized SQLAlchemy statements.",
              recommendation: "Ensure all new models adhere to same ORM pattern.",
            },
            {
              id: "rev-03",
              category: "maintainability",
              severity: "WARNING",
              title: "Typed Return Types",
              description: "Several helper functions in utils/time.py lack explicit Python return type annotations.",
              recommendation: "Add PEP-484 type annotations for future strict mypy linting.",
            },
          ],
          recommendations: [
            "Enable strict mypy and ruff linting in CI/CD pipeline.",
            "Consider caching menu item lists with Redis for high-load dinner peaks.",
          ],
          required_changes: [],
          summary:
            "Architecture meets all non-functional requirements and functional user stories. Security and QA rework cycles resolved all blocking items. Approved for finalization.",
        });
        setLoading(false);
        return;
      }

      try {
        const res = await getReviewReport(runId);
        if (mounted && res) setReview(res);
      } catch (err) {
        console.warn(err);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchReport();
    return () => {
      mounted = false;
    };
  }, [runId]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
            <Layers className="w-5 h-5 text-emerald-400" /> Architectural & Code Review Center
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Senior engineer review evaluating architectural consistency, modularity, security remediation, and gate sign-off.
          </p>
        </div>

        <span
          className={`px-3 py-1 rounded text-xs font-mono font-semibold uppercase border ${
            review?.review_status === "APPROVED"
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
              : "bg-amber-500/10 text-amber-300 border-amber-500/30"
          }`}
        >
          Review Gate: {review?.review_status || "PENDING"}
        </span>
      </div>

      {/* Review Lifecycle Progress Bar */}
      <div className="p-4 rounded-xl border border-[#30363d] bg-[#161b22] flex items-center justify-between font-mono text-xs">
        <div className="flex items-center gap-2 text-emerald-400">
          <CheckCircle2 className="w-4 h-4" />
          <span>1. Initial Review</span>
        </div>
        <span className="text-zinc-600">&rarr;</span>
        <div className="flex items-center gap-2 text-emerald-400">
          <CheckCircle2 className="w-4 h-4" />
          <span>2. Feedback Handoff</span>
        </div>
        <span className="text-zinc-600">&rarr;</span>
        <div className="flex items-center gap-2 text-emerald-400">
          <CheckCircle2 className="w-4 h-4" />
          <span>3. Developer Rework</span>
        </div>
        <span className="text-zinc-600">&rarr;</span>
        <div className="flex items-center gap-2 text-emerald-400 font-bold">
          <FileCheck className="w-4 h-4" />
          <span>4. Final Sign-Off (APPROVED)</span>
        </div>
      </div>

      {/* Summary Card */}
      <div className="p-5 rounded-xl border border-[#30363d] bg-[#161b22] space-y-2">
        <div className="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
          Executive Review Assessment
        </div>
        <p className="text-xs text-zinc-300 font-sans leading-relaxed bg-[#0d1117] p-3 rounded-lg border border-[#30363d]">
          {review?.summary}
        </p>
      </div>

      {/* Detailed Findings List */}
      <div className="rounded-xl border border-[#30363d] bg-[#161b22] overflow-hidden">
        <div className="p-3.5 border-b border-[#30363d] bg-[#12161f] text-xs font-semibold text-zinc-200">
          Review Findings & Recommendations
        </div>
        <div className="divide-y divide-[#30363d]">
          {review?.findings?.map((f) => (
            <div key={f.id} className="p-4 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold uppercase ${
                      f.severity === "BLOCKING"
                        ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                        : f.severity === "WARNING"
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                        : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                    }`}
                  >
                    {f.severity}
                  </span>
                  <span className="font-semibold text-zinc-200">{f.title}</span>
                </div>
                <span className="text-[10px] font-mono text-zinc-400 capitalize">
                  {f.category.replace("_", " ")}
                </span>
              </div>
              <p className="text-xs text-zinc-300 font-sans leading-relaxed">{f.description}</p>
              <div className="text-[11px] text-emerald-400 font-sans bg-emerald-500/5 p-2 rounded border border-emerald-500/10">
                <strong>Action:</strong> {f.recommendation}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
