import React, { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  MarkerType,
  BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { StageNode } from "./StageNode";
import type { StageName, StageStatus } from "../../types";

const nodeTypes = {
  stageNode: StageNode,
};

interface WorkflowCanvasProps {
  currentStage?: StageName;
  runStatus?: string;
  selectedStageKey?: string;
  onSelectStage?: (stageKey: string) => void;
  securityReworkCount?: number;
  qaReworkCount?: number;
  reviewReworkCount?: number;
}

export const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({
  currentStage = "REQUIREMENTS",
  runStatus = "PENDING",
  selectedStageKey,
  onSelectStage,
  securityReworkCount = 0,
  qaReworkCount = 0,
  reviewReworkCount = 0,
}) => {
  // Compute stage statuses based on currentStage and runStatus
  const stageOrder: StageName[] = [
    "REQUIREMENTS",
    "ARCHITECTURE",
    "VISUAL_ARCHITECTURE",
    "DEVELOPMENT",
    "SECURITY",
    "QA",
    "REVIEW",
    "FINALIZATION",
  ];

  const getStatus = (stage: StageName): StageStatus => {
    if (runStatus === "COMPLETED") return "COMPLETED";
    if (runStatus === "FAILED" && stage === currentStage) return "FAILED";

    const currentIndex = stageOrder.indexOf(currentStage);
    const targetIndex = stageOrder.indexOf(stage);

    if (stage === currentStage) {
      if (runStatus === "RUNNING") {
        if (
          (stage === "DEVELOPMENT" && (securityReworkCount > 0 || qaReworkCount > 0 || reviewReworkCount > 0)) ||
          (stage === "SECURITY" && securityReworkCount > 0)
        ) {
          return "REWORKING";
        }
        return "RUNNING";
      }
      return "WAITING";
    }

    if (targetIndex < currentIndex) {
      return "COMPLETED";
    }

    return "QUEUED";
  };

  const nodes: Node[] = useMemo(() => {
    return [
      {
        id: "requirements_node",
        type: "stageNode",
        position: { x: 250, y: 30 },
        data: {
          label: "Requirements Analyst",
          stageKey: "requirements_node",
          role: "PRD & User Stories",
          status: getStatus("REQUIREMENTS"),
          selected: selectedStageKey === "requirements_node",
        },
      },
      {
        id: "architecture_node",
        type: "stageNode",
        position: { x: 250, y: 140 },
        data: {
          label: "System Architect",
          stageKey: "architecture_node",
          role: "Tech Stack & Modular Specs",
          status: getStatus("ARCHITECTURE"),
          selected: selectedStageKey === "architecture_node",
        },
      },
      {
        id: "visual_architecture_node",
        type: "stageNode",
        position: { x: 250, y: 250 },
        data: {
          label: "Visual Architect",
          stageKey: "visual_architecture_node",
          role: "Mermaid & Flow Topology",
          status: getStatus("VISUAL_ARCHITECTURE"),
          selected: selectedStageKey === "visual_architecture_node",
        },
      },
      {
        id: "developer_node",
        type: "stageNode",
        position: { x: 250, y: 360 },
        data: {
          label: "Developer Agent",
          stageKey: "developer_node",
          role: "Code Generation & Rework",
          status: getStatus("DEVELOPMENT"),
          retries: Math.max(securityReworkCount, qaReworkCount, reviewReworkCount),
          selected: selectedStageKey === "developer_node",
        },
      },
      {
        id: "security_node",
        type: "stageNode",
        position: { x: 100, y: 480 },
        data: {
          label: "Security Scanner",
          stageKey: "security_node",
          role: "Deterministic + LLM Scan",
          status: getStatus("SECURITY"),
          retries: securityReworkCount,
          selected: selectedStageKey === "security_node",
        },
      },
      {
        id: "qa_node",
        type: "stageNode",
        position: { x: 400, y: 480 },
        data: {
          label: "QA Test Engineer",
          stageKey: "qa_node",
          role: "Unit & Integration Tests",
          status: getStatus("QA"),
          retries: qaReworkCount,
          selected: selectedStageKey === "qa_node",
        },
      },
      {
        id: "review_node",
        type: "stageNode",
        position: { x: 250, y: 600 },
        data: {
          label: "Code Reviewer",
          stageKey: "review_node",
          role: "Standards & Gate Approval",
          status: getStatus("REVIEW"),
          retries: reviewReworkCount,
          selected: selectedStageKey === "review_node",
        },
      },
      {
        id: "finalization_node",
        type: "stageNode",
        position: { x: 250, y: 710 },
        data: {
          label: "SDLC Finalization",
          stageKey: "finalization_node",
          role: "Artifact Packaging & Handoff",
          status: getStatus("FINALIZATION"),
          selected: selectedStageKey === "finalization_node",
        },
      },
    ];
  }, [currentStage, runStatus, selectedStageKey, securityReworkCount, qaReworkCount, reviewReworkCount]);

  const edges: Edge[] = useMemo(() => {
    const defaultEdgeStyle = { stroke: "#30363d", strokeWidth: 1.5 };
    const activeEdgeStyle = { stroke: "#10b981", strokeWidth: 2 };
    const reworkEdgeStyle = { stroke: "#f59e0b", strokeWidth: 2, strokeDasharray: "5,5" };

    return [
      // Direct forward edges
      {
        id: "e-req-arch",
        source: "requirements_node",
        target: "architecture_node",
        animated: currentStage === "REQUIREMENTS",
        style: currentStage === "REQUIREMENTS" ? activeEdgeStyle : defaultEdgeStyle,
        markerEnd: { type: MarkerType.ArrowClosed, color: "#30363d" },
      },
      {
        id: "e-arch-vis",
        source: "architecture_node",
        target: "visual_architecture_node",
        animated: currentStage === "ARCHITECTURE",
        style: currentStage === "ARCHITECTURE" ? activeEdgeStyle : defaultEdgeStyle,
        markerEnd: { type: MarkerType.ArrowClosed, color: "#30363d" },
      },
      {
        id: "e-vis-dev",
        source: "visual_architecture_node",
        target: "developer_node",
        animated: currentStage === "VISUAL_ARCHITECTURE",
        style: currentStage === "VISUAL_ARCHITECTURE" ? activeEdgeStyle : defaultEdgeStyle,
        markerEnd: { type: MarkerType.ArrowClosed, color: "#30363d" },
      },
      {
        id: "e-dev-sec",
        source: "developer_node",
        target: "security_node",
        animated: currentStage === "DEVELOPMENT" || currentStage === "SECURITY",
        style: currentStage === "SECURITY" ? activeEdgeStyle : defaultEdgeStyle,
        markerEnd: { type: MarkerType.ArrowClosed, color: "#30363d" },
      },
      {
        id: "e-sec-qa",
        source: "security_node",
        target: "qa_node",
        animated: currentStage === "QA",
        style: currentStage === "QA" ? activeEdgeStyle : defaultEdgeStyle,
        markerEnd: { type: MarkerType.ArrowClosed, color: "#30363d" },
      },
      {
        id: "e-qa-rev",
        source: "qa_node",
        target: "review_node",
        animated: currentStage === "REVIEW",
        style: currentStage === "REVIEW" ? activeEdgeStyle : defaultEdgeStyle,
        markerEnd: { type: MarkerType.ArrowClosed, color: "#30363d" },
      },
      {
        id: "e-rev-fin",
        source: "review_node",
        target: "finalization_node",
        animated: currentStage === "FINALIZATION",
        style: currentStage === "FINALIZATION" ? activeEdgeStyle : defaultEdgeStyle,
        markerEnd: { type: MarkerType.ArrowClosed, color: "#30363d" },
      },

      // Rework Loops (Backward Feedback)
      {
        id: "e-sec-rework-dev",
        source: "security_node",
        target: "developer_node",
        label: "Security Rework Loop",
        labelStyle: { fill: "#f59e0b", fontSize: 10, fontFamily: "monospace" },
        labelBgStyle: { fill: "#161b22", fillOpacity: 0.8 },
        animated: securityReworkCount > 0,
        style: reworkEdgeStyle,
        markerEnd: { type: MarkerType.ArrowClosed, color: "#f59e0b" },
      },
      {
        id: "e-qa-rework-dev",
        source: "qa_node",
        target: "developer_node",
        label: "QA Fix Loop",
        labelStyle: { fill: "#f59e0b", fontSize: 10, fontFamily: "monospace" },
        labelBgStyle: { fill: "#161b22", fillOpacity: 0.8 },
        animated: qaReworkCount > 0,
        style: reworkEdgeStyle,
        markerEnd: { type: MarkerType.ArrowClosed, color: "#f59e0b" },
      },
      {
        id: "e-rev-rework-dev",
        source: "review_node",
        target: "developer_node",
        label: "Review Rework Loop",
        labelStyle: { fill: "#f59e0b", fontSize: 10, fontFamily: "monospace" },
        labelBgStyle: { fill: "#161b22", fillOpacity: 0.8 },
        animated: reviewReworkCount > 0,
        style: reworkEdgeStyle,
        markerEnd: { type: MarkerType.ArrowClosed, color: "#f59e0b" },
      },
    ];
  }, [currentStage, securityReworkCount, qaReworkCount, reviewReworkCount]);

  return (
    <div className="w-full h-full bg-[#0b0e14] rounded-lg border border-[#30363d] relative overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onSelectStage?.(node.id)}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.5}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#21262d" />
        <Controls className="!bg-[#161b22] !border-[#30363d] !fill-zinc-300 [&>button]:!border-[#30363d] [&>button]:!bg-[#161b22] [&>button]:!text-zinc-300" />
        <MiniMap
          nodeColor={(n) => {
            if (n.data?.status === "RUNNING") return "#10b981";
            if (n.data?.status === "REWORKING") return "#f59e0b";
            if (n.data?.status === "COMPLETED") return "#388bfd";
            return "#30363d";
          }}
          className="!bg-[#0d1117] !border-[#30363d] rounded"
        />
      </ReactFlow>

      {/* Floating Canvas Legend */}
      <div className="absolute bottom-3 left-3 bg-[#161b22]/90 backdrop-blur-sm border border-[#30363d] rounded px-3 py-1.5 flex items-center gap-4 text-[10px] font-mono text-zinc-400 select-none">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          <span>Active Node</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-amber-400"></span>
          <span>Rework Cycle</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#30363d]"></span>
          <span>Queued / Next</span>
        </div>
      </div>
    </div>
  );
};
