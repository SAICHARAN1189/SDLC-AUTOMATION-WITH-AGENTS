import React, { useEffect, useRef } from "react";
import {
  ArrowRight,
  ShieldAlert,
  Bug,
  FileCode2,
  CheckCircle,
  Clock,
  Send,
  AlertOctagon,
} from "lucide-react";
import type { WorkflowEvent } from "../../types";

interface CommunicationTimelineProps {
  events: WorkflowEvent[];
}

export const CommunicationTimeline: React.FC<CommunicationTimelineProps> = ({ events }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new events
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [events.length]);

  // Format time (HH:MM:SS)
  const formatTime = (iso?: string) => {
    if (!iso) return "--:--:--";
    try {
      return new Date(iso).toLocaleTimeString();
    } catch {
      return iso.slice(11, 19);
    }
  };

  // Derive message styling and metadata
  const getEventBadge = (event: WorkflowEvent) => {
    const type = event.event_type;
    if (type.includes("SECURITY_FINDINGS")) {
      return {
        icon: ShieldAlert,
        color: "text-amber-400 bg-amber-500/10 border-amber-500/20",
        label: "SECURITY FEEDBACK",
      };
    }
    if (type.includes("REWORK")) {
      return {
        icon: AlertOctagon,
        color: "text-rose-400 bg-rose-500/10 border-rose-500/20",
        label: "REWORK TRIGGERED",
      };
    }
    if (type.includes("TESTS_FAILED")) {
      return {
        icon: Bug,
        color: "text-rose-400 bg-rose-500/10 border-rose-500/20",
        label: "TEST FAILURE",
      };
    }
    if (type.includes("COMPLETED") || type.includes("PASSED")) {
      return {
        icon: CheckCircle,
        color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
        label: "STAGE PASSED",
      };
    }
    return {
      icon: Send,
      color: "text-zinc-400 bg-zinc-800/40 border-zinc-700/40",
      label: "AGENT TRANSMISSION",
    };
  };

  // Resolve sender/receiver agent names cleanly
  const resolveAgents = (event: WorkflowEvent) => {
    const stage = event.stage || "workflow";
    const agent = event.agent || stage;

    let sender = agent.replace("_node", "").replace("_agent", "").replace("_", " ").toUpperCase();
    let receiver = "LANGGRAPH STATE";

    if (event.event_type.includes("SECURITY_FINDINGS")) {
      sender = "SECURITY SCANNER";
      receiver = "DEVELOPER AGENT";
    } else if (event.event_type.includes("REWORK_STARTED")) {
      sender = "WORKFLOW ROUTER";
      receiver = "DEVELOPER AGENT";
    } else if (event.event_type.includes("TESTS_COMPLETED")) {
      sender = "QA ENGINEER";
      receiver = "REVIEW AGENT";
    } else if (event.stage === "REQUIREMENTS") {
      receiver = "SYSTEM ARCHITECT";
    } else if (event.stage === "ARCHITECTURE") {
      receiver = "DEVELOPER AGENT";
    } else if (event.stage === "DEVELOPMENT") {
      receiver = "SECURITY SCANNER";
    }

    return { sender, receiver };
  };

  return (
    <div className="flex flex-col h-full bg-[#0b0e14] rounded-lg border border-[#30363d] overflow-hidden">
      {/* Header */}
      <div className="h-10 border-b border-[#30363d] bg-[#161b22] px-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Clock className="w-3.5 h-3.5 text-zinc-400" />
          <span className="text-xs font-semibold text-zinc-200 uppercase tracking-wide">
            Inter-Agent Communication Stream
          </span>
        </div>
        <span className="text-[10px] font-mono text-zinc-400 bg-zinc-800/60 px-2 py-0.5 rounded border border-zinc-700/50">
          {events.length} Transmissions
        </span>
      </div>

      {/* Messages Stream */}
      <div ref={containerRef} className="flex-1 p-3 overflow-y-auto space-y-2 font-mono text-xs">
        {events.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-zinc-400 space-y-2">
            <Send className="w-6 h-6 text-zinc-400 animate-pulse" />
            <span className="text-xs">Awaiting workflow initialization and agent transmissions...</span>
          </div>
        ) : (
          events.map((ev, index) => {
            const badge = getEventBadge(ev);
            const BadgeIcon = badge.icon;
            const { sender, receiver } = resolveAgents(ev);

            return (
              <div
                key={ev.id || ev.event_id || index}
                className="p-2.5 rounded bg-[#161b22]/70 border border-[#30363d] hover:border-[#8b949e]/40 transition-colors"
              >
                {/* Meta header */}
                <div className="flex items-center justify-between text-[11px] text-zinc-400 mb-1.5">
                  <div className="flex items-center gap-1.5 font-medium">
                    <span className="text-zinc-200">{sender}</span>
                    <ArrowRight className="w-3 h-3 text-zinc-400" />
                    <span className="text-emerald-400">{receiver}</span>
                  </div>
                  <span className="text-[10px] text-zinc-400">{formatTime(ev.timestamp)}</span>
                </div>

                {/* Event Type Badge & Message */}
                <div className="flex items-start gap-2">
                  <span
                    className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] uppercase font-semibold border shrink-0 mt-0.5 ${badge.color}`}
                  >
                    <BadgeIcon className="w-3 h-3" />
                    {badge.label}
                  </span>
                  <div className="text-zinc-300 font-sans text-xs leading-relaxed flex-1">
                    {ev.message}
                  </div>
                </div>

                {/* Metadata tags if present */}
                {ev.metadata && Object.keys(ev.metadata).length > 0 && (
                  <div className="mt-2 pt-1.5 border-t border-white/5 flex flex-wrap gap-2 text-[10px] text-zinc-400">
                    {Boolean(ev.metadata.rework_count) && (
                      <span className="bg-amber-500/10 text-amber-300 px-1.5 py-0.5 rounded border border-amber-500/20">
                        Rework Loop #{String(ev.metadata.rework_count)}
                      </span>
                    )}
                    {Boolean(ev.metadata.severity) && (
                      <span className="bg-rose-500/10 text-rose-300 px-1.5 py-0.5 rounded border border-rose-500/20">
                        Severity: {String(ev.metadata.severity)}
                      </span>
                    )}
                    {Boolean(ev.metadata.affected_file) && (
                      <span className="flex items-center gap-1 bg-zinc-800 text-zinc-300 px-1.5 py-0.5 rounded">
                        <FileCode2 className="w-3 h-3 text-zinc-400" />
                        {String(ev.metadata.affected_file)}
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
