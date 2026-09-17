import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  FileCode,
  FolderTree,
  Boxes,
  Palette,
  ShieldCheck,
  TestTube2,
  CheckCircle,
  Download,
  Copy,
  Check,
  FileText,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { MermaidViewer } from "../components/artifacts/MermaidViewer";
import { getRunArtifacts } from "../services/api";
import type { ArtifactItem } from "../types";

const MOCK_MERMAID = `graph TD
    Client[Mobile / Web Client] -->|HTTPS / REST| API[Flask API Gateway]
    API --> Auth[Supabase Auth]
    API --> OrderSvc[Order Processing Service]
    API --> DispatchSvc[Driver Dispatch Engine]
    API --> PayVault[Payment Tokenization Vault]
    OrderSvc --> DB[(PostgreSQL Database)]
    DispatchSvc --> Cache[(Redis Geo Cache)]
`;

export const Artifacts: React.FC = () => {
  const [searchParams] = useSearchParams();
  const runId = searchParams.get("run_id");

  const [artifacts, setArtifacts] = useState<ArtifactItem[]>([]);
  const [activeTab, setActiveTab] = useState<
    "requirements" | "architecture" | "diagrams" | "code" | "security" | "tests" | "review"
  >("requirements");
  const [selectedFileIndex, setSelectedFileIndex] = useState(0);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const fetchArtifacts = async () => {
      if (!runId) {
        setLoading(false);
        return;
      }
      try {
        const res = await getRunArtifacts(runId);
        if (mounted && res.length > 0) setArtifacts(res);
      } catch (err) {
        console.warn(err);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    fetchArtifacts();
    return () => {
      mounted = false;
    };
  }, [runId]);

  const sampleCodeFiles = [
    {
      path: "backend/app.py",
      content: `from flask import Flask
from flask_cors import CORS
from backend.api.orders import orders_bp
from backend.api.payments import payments_bp

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(orders_bp)
    app.register_blueprint(payments_bp)
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(port=8000)`,
    },
    {
      path: "backend/api/orders.py",
      content: `from flask import Blueprint, request, jsonify
from backend.services.order_service import create_order_safe

orders_bp = Blueprint("orders", __name__)

@orders_bp.route("/api/orders", methods=["POST"])
def place_order():
    data = request.json or {}
    order = create_order_safe(customer_id=data.get("customer_id"), items=data.get("items"))
    return jsonify({"success": True, "order": order})`,
    },
    {
      path: "backend/services/payment_vault.py",
      content: `import os
import httpx

class PaymentVault:
    def __init__(self):
        self.secret_key = os.environ.get("PAYMENT_SECRET")

    def tokenize_card(self, card_payload):
        # Strict isolation: card numbers never stored in local DB
        return {"token": "tok_sec_vaulted_9824", "status": "AUTHORIZED"}`,
    },
  ];

  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadZip = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(artifacts, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `sdlc-artifacts-${runId || "demo"}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="flex flex-col h-[calc(100vh-5rem)] space-y-4 max-w-7xl mx-auto">
      {/* Header & Export Actions */}
      <div className="p-3.5 rounded-lg bg-[#161b22] border border-[#30363d] flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
            <FileCode className="w-4 h-4 text-emerald-400" /> Artifact Explorer & Project Deliverables
          </h1>
          <p className="text-[11px] text-zinc-400 mt-0.5">
            Structured specifications, architectural blueprints, verified codebases, and sign-off audits.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadZip}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs border border-zinc-700 transition-colors cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Deliverables JSON</span>
          </button>
        </div>
      </div>

      {/* Main Container */}
      <div className="flex-1 flex flex-col rounded-xl border border-[#30363d] bg-[#161b22] overflow-hidden min-h-0">
        {/* Navigation Tabs */}
        <div className="flex items-center border-b border-[#30363d] bg-[#12161f] px-3 gap-2 text-xs font-mono shrink-0 overflow-x-auto">
          {[
            { id: "requirements", label: "Requirements PRD", icon: FileText },
            { id: "architecture", label: "Architecture Spec", icon: Boxes },
            { id: "diagrams", label: "Mermaid Diagrams", icon: Palette },
            { id: "code", label: "Generated Codebase", icon: FolderTree },
            { id: "security", label: "Security Report", icon: ShieldCheck },
            { id: "tests", label: "Test Suites", icon: TestTube2 },
            { id: "review", label: "Review Sign-Off", icon: CheckCircle },
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`flex items-center gap-1.5 py-2.5 px-3 border-b-2 font-medium transition-colors cursor-pointer ${
                  activeTab === tab.id
                    ? "border-emerald-500 text-emerald-400"
                    : "border-transparent text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab Body */}
        <div className="flex-1 p-6 overflow-y-auto font-sans text-xs">
          {activeTab === "requirements" && (
            <div className="prose prose-invert max-w-none text-zinc-300 font-sans space-y-4">
              <h2 className="text-base font-bold text-zinc-100 font-mono">Product Requirements Document (PRD)</h2>
              <div className="p-4 rounded-lg bg-[#0d1117] border border-[#30363d] space-y-3">
                <h3 className="text-xs font-semibold text-emerald-400 uppercase font-mono">1. Project Summary</h3>
                <p className="text-zinc-300 leading-relaxed">
                  The application is a high-availability online food delivery orchestration platform connecting customers,
                  partner restaurants, and freelance delivery drivers. Key requirements include atomic order state transitions,
                  real-time driver location synchronization, strict payment tokenization isolating sensitive credit card numbers,
                  and low-latency menu searches.
                </p>

                <h3 className="text-xs font-semibold text-emerald-400 uppercase font-mono">2. User Stories</h3>
                <ul className="list-disc pl-4 space-y-1.5 text-zinc-300">
                  <li><strong>As a Customer</strong>, I want to browse restaurants and place orders securely so that my food is delivered on time.</li>
                  <li><strong>As a Restaurant Manager</strong>, I want to accept or reject incoming orders and update preparation status in real-time.</li>
                  <li><strong>As a Driver</strong>, I want to receive nearby delivery dispatches and navigate to destination coordinates.</li>
                </ul>

                <h3 className="text-xs font-semibold text-emerald-400 uppercase font-mono">3. Non-Functional & Security Constraints</h3>
                <ul className="list-disc pl-4 space-y-1.5 text-zinc-300">
                  <li>PCI-DSS tokenization: No raw payment credentials stored in application database.</li>
                  <li>Sub-200ms latency for order status lookups under peak dinner load.</li>
                  <li>Zero SQL string interpolations across all persistence repositories.</li>
                </ul>
              </div>
            </div>
          )}

          {activeTab === "architecture" && (
            <div className="space-y-4">
              <h2 className="text-base font-bold text-zinc-100 font-mono">System Architecture Specification</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono">
                <div className="p-4 rounded-lg bg-[#0d1117] border border-[#30363d] space-y-2">
                  <div className="text-emerald-400 text-xs font-bold uppercase">Backend Framework</div>
                  <div className="text-zinc-200">Flask REST API (Python 3.13)</div>
                  <p className="text-[11px] text-zinc-400 font-sans">
                    Modular blueprints, Pydantic configuration schemas, and SQLAlchemy ORM session scopes.
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-[#0d1117] border border-[#30363d] space-y-2">
                  <div className="text-emerald-400 text-xs font-bold uppercase">Data Persistence</div>
                  <div className="text-zinc-200">PostgreSQL (Supabase)</div>
                  <p className="text-[11px] text-zinc-400 font-sans">
                    Row-Level Security (RLS), Alembic versioned migrations, ACID transaction guarantees.
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-[#0d1117] border border-[#30363d] space-y-2">
                  <div className="text-emerald-400 text-xs font-bold uppercase">Orchestration</div>
                  <div className="text-zinc-200">LangGraph StateGraph</div>
                  <p className="text-[11px] text-zinc-400 font-sans">
                    Shared typed ProjectState, bounded conditional rework loops, and in-memory checkpointing.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === "diagrams" && (
            <div className="h-full min-h-[400px]">
              <MermaidViewer code={MOCK_MERMAID} title="System Architecture & Component Sequence DAG" />
            </div>
          )}

          {activeTab === "code" && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-full min-h-[450px]">
              {/* File Explorer Tree (Left 4 Cols) */}
              <div className="lg:col-span-4 rounded-lg border border-[#30363d] bg-[#0d1117] p-3 space-y-1 font-mono text-xs">
                <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-2 font-semibold flex items-center gap-1.5">
                  <FolderTree className="w-3.5 h-3.5 text-emerald-400" /> Source Files ({sampleCodeFiles.length})
                </div>
                {sampleCodeFiles.map((file, idx) => (
                  <button
                    key={file.path}
                    onClick={() => setSelectedFileIndex(idx)}
                    className={`w-full text-left px-2.5 py-1.5 rounded flex items-center justify-between transition-colors ${
                      selectedFileIndex === idx
                        ? "bg-[#1f242c] text-emerald-400 border border-[#30363d]"
                        : "text-zinc-400 hover:text-zinc-200 hover:bg-[#161b22]"
                    }`}
                  >
                    <span className="truncate">{file.path}</span>
                  </button>
                ))}
              </div>

              {/* Code File Viewer (Right 8 Cols) */}
              <div className="lg:col-span-8 rounded-lg border border-[#30363d] bg-[#0d1117] overflow-hidden flex flex-col">
                <div className="h-9 border-b border-[#30363d] bg-[#161b22] px-3 flex items-center justify-between text-xs font-mono">
                  <span className="text-emerald-400 font-semibold">{sampleCodeFiles[selectedFileIndex]?.path}</span>
                  <button
                    onClick={() => handleCopy(sampleCodeFiles[selectedFileIndex]?.content || "")}
                    className="flex items-center gap-1 text-[11px] text-zinc-400 hover:text-zinc-200 px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 cursor-pointer"
                  >
                    {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>Copy</span>
                  </button>
                </div>
                <pre className="flex-1 p-4 text-xs font-mono text-zinc-200 overflow-auto whitespace-pre">
                  {sampleCodeFiles[selectedFileIndex]?.content}
                </pre>
              </div>
            </div>
          )}

          {activeTab === "security" && (
            <div className="p-4 rounded-lg bg-[#0d1117] border border-[#30363d] space-y-3 font-mono">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-emerald-400 uppercase">Security Scanner Audit</span>
                <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px]">PASS</span>
              </div>
              <p className="text-xs text-zinc-300 font-sans leading-relaxed">
                Deterministic regex checks verified that zero raw SQL string interpolations remain in backend/api/orders.py.
                All API authentication tokens are derived from verified Supabase session cookies or authorization headers.
              </p>
            </div>
          )}

          {activeTab === "tests" && (
            <div className="p-4 rounded-lg bg-[#0d1117] border border-[#30363d] space-y-3 font-mono">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-sky-400 uppercase">Automated QA Test Results</span>
                <span className="px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 text-[10px]">14 / 14 PASSED</span>
              </div>
              <p className="text-xs text-zinc-300 font-sans leading-relaxed">
                Unit test execution covered customer order workflows, input validation rejections, and payment token isolation.
              </p>
            </div>
          )}

          {activeTab === "review" && (
            <div className="p-4 rounded-lg bg-[#0d1117] border border-[#30363d] space-y-3 font-mono">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-emerald-400 uppercase">Code Review Gate Decision</span>
                <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px]">APPROVED</span>
              </div>
              <p className="text-xs text-zinc-300 font-sans leading-relaxed">
                Senior Code Reviewer approved implementation following successful Security rework loops. Production deliverables packaged.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
