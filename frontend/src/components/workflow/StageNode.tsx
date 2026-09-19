import React from "react";
import { Handle, Position } from "@xyflow/react";
import {
  FileText,
  Boxes,
  Palette,
  Code2,
  ShieldCheck,
  TestTube2,
  CheckCircle2,
  Flag,
  Loader2,
  AlertTriangle,
  RotateCcw,
} from "lucide-react";
import type { StageStatus } from "../../types";

const STAGE_ICONS: Record<string, React.ElementType> = {
  requirements_node: FileText,
  architecture_node: Boxes,
  visual_architecture_node: Palette,
  developer_node: Code2,
  security_node: ShieldCheck,
  qa_node: TestTube2,
  review_node: CheckCircle2,
  finalization_node: Flag,
};

interface StageNodeData {
  label: string;
  stageKey: string;
  role: string;
  status: StageStatus;
  duration?: string;
  retries?: number;
  selected?: boolean;
  modelBadge?: string;
}

export const StageNode: React.FC<{ data: StageNodeData }> = ({ data }) => {
  const Icon = STAGE_ICONS[data.stageKey] || Boxes;
  const isRunning = data.status === "RUNNING";
  const isReworking = data.status === "REWORKING";
  const isCompleted = data.status === "COMPLETED";
  const isFailed = data.status === "FAILED";

  // Border & background based on status
  let statusStyles = "border-[#30363d] bg-[#161b22] text-zinc-300";
  if (isRunning) {
    statusStyles = "border-emerald-500 bg-[#0f241a] text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.3)] animate-pulse";
  } else if (isReworking) {
    statusStyles = "border-amber-500 bg-[#261c0a] text-amber-300 shadow-[0_0_15px_rgba(245,158,11,0.3)] animate-pulse";
  } else if (isCompleted) {
    statusStyles = "border-emerald-500/60 bg-[#121d18] text-zinc-100";
  } else if (isFailed) {
    statusStyles = "border-rose-500 bg-[#251014] text-rose-300";
  }

  return (
    <div
      className={`px-4 py-3 rounded-lg border min-w-[200px] transition-all cursor-pointer select-none font-sans ${statusStyles} ${
        data.selected ? "ring-2 ring-emerald-400 ring-offset-2 ring-offset-[#0d1117]" : ""
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-[#30363d] !w-2.5 !h-2.5" />

      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2">
          <div
            className={`w-7 h-7 rounded flex items-center justify-center ${
              isCompleted
                ? "bg-emerald-500/20 text-emerald-400"
                : isRunning || isReworking
                ? "bg-amber-500/20 text-amber-400"
                : "bg-zinc-800 text-zinc-400"
            }`}
          >
            <Icon className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-semibold tracking-tight">{data.label}</div>
            <div className="text-[10px] text-zinc-400 font-mono">{data.role}</div>
            {data.modelBadge && (
              <div className="text-[9px] text-emerald-400/90 font-mono flex items-center gap-1 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400/70 inline-block" />
                {data.modelBadge}
              </div>
            )}
          </div>
        </div>

        {/* Status Badge */}
        <div>
          {isRunning && <Loader2 className="w-3.5 h-3.5 text-emerald-400 animate-spin" />}
          {isReworking && <RotateCcw className="w-3.5 h-3.5 text-amber-400 animate-spin" />}
          {isCompleted && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
          {isFailed && <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />}
        </div>
      </div>

      <div className="flex items-center justify-between text-[10px] font-mono border-t border-white/5 pt-1.5 mt-1.5 text-zinc-400">
        <span className="uppercase tracking-wider">
          {data.status || "QUEUED"}
        </span>
        <div className="flex items-center gap-1.5">
          {(data.retries ?? 0) > 0 && (
            <span className="px-1 rounded bg-amber-500/20 text-amber-300 font-semibold">
              Rework #{data.retries}
            </span>
          )}
          {data.duration && <span>{data.duration}</span>}
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-[#30363d] !w-2.5 !h-2.5" />
    </div>
  );
};
