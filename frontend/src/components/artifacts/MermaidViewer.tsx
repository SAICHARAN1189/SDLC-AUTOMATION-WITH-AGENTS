import React, { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { Copy, Check, AlertTriangle, Code2 } from "lucide-react";

interface MermaidViewerProps {
  code: string;
  title?: string;
}

export const MermaidViewer: React.FC<MermaidViewerProps> = ({ code, title }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string>("");
  const [renderError, setRenderError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showCode, setShowCode] = useState(false);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: "dark",
      themeVariables: {
        darkMode: true,
        background: "#0d1117",
        primaryColor: "#161b22",
        primaryTextColor: "#e6edf3",
        primaryBorderColor: "#30363d",
        lineColor: "#10b981",
        secondaryColor: "#1f242c",
        tertiaryColor: "#161b22",
      },
      fontFamily: "IBM Plex Sans, sans-serif",
    });

    let isMounted = true;
    const renderDiagram = async () => {
      if (!code.trim()) return;
      try {
        const id = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
        const { svg } = await mermaid.render(id, code.trim());
        if (isMounted) {
          setSvgContent(svg);
          setRenderError(null);
        }
      } catch (err: unknown) {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : String(err);
          setRenderError(msg);
        }
      }
    };

    renderDiagram();
    return () => {
      isMounted = false;
    };
  }, [code]);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col h-full bg-[#0b0e14] rounded-lg border border-[#30363d] overflow-hidden">
      {/* Header */}
      <div className="h-10 border-b border-[#30363d] bg-[#161b22] px-3 flex items-center justify-between shrink-0">
        <span className="text-xs font-semibold text-zinc-200">{title || "Mermaid Architecture Diagram"}</span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCode(!showCode)}
            className="flex items-center gap-1 text-[11px] font-mono text-zinc-400 hover:text-zinc-200 px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700"
          >
            <Code2 className="w-3 h-3" />
            {showCode ? "Show Diagram" : "View Source"}
          </button>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 text-[11px] font-mono text-zinc-400 hover:text-zinc-200 px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>

      {/* Content Body */}
      <div className="flex-1 p-4 overflow-auto flex items-center justify-center">
        {showCode ? (
          <pre className="w-full h-full text-xs font-mono text-zinc-300 bg-[#161b22] p-4 rounded border border-[#30363d] overflow-auto whitespace-pre">
            {code}
          </pre>
        ) : renderError ? (
          <div className="p-4 rounded-md bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs font-mono max-w-lg space-y-2">
            <div className="flex items-center gap-2 font-semibold">
              <AlertTriangle className="w-4 h-4" /> Mermaid Render Warning
            </div>
            <p className="text-[11px] text-zinc-400 font-sans">{renderError}</p>
            <pre className="p-2 bg-black/40 rounded text-[10px] overflow-x-auto">{code}</pre>
          </div>
        ) : (
          <div
            ref={containerRef}
            className="w-full h-full flex items-center justify-center [&>svg]:max-h-full [&>svg]:w-auto"
            dangerouslySetInnerHTML={{ __html: svgContent }}
          />
        )}
      </div>
    </div>
  );
};
