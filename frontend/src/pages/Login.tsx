import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Activity, Lock, Mail, Sparkles, ArrowRight } from "lucide-react";
import { setToken } from "../services/api";

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("engineer@sdlc-nexus.dev");
  const [password, setPassword] = useState("••••••••••••");
  const [loading, setLoading] = useState(false);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    // Authenticate and save token
    setToken("demo-authenticated-jwt-token");
    setTimeout(() => {
      navigate("/");
    }, 400);
  };

  const handleDemoAccess = () => {
    setToken("demo-authenticated-jwt-token");
    navigate("/");
  };

  return (
    <div className="min-h-screen w-screen bg-[#090c10] flex items-center justify-center p-4 font-sans text-zinc-100">
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto">
            <Activity className="w-6 h-6 animate-pulse" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">SDLC NEXUS</h1>
          <p className="text-xs text-zinc-400 font-mono">
            Autonomous Multi-Agent Engineering Control Center
          </p>
        </div>

        {/* Login Form Container */}
        <div className="rounded-xl border border-[#30363d] bg-[#161b22] p-6 shadow-2xl space-y-5">
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-1.5 font-mono text-xs">
              <label className="text-zinc-300 block">Engineering Email</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 rounded-md bg-[#0d1117] border border-[#30363d] text-zinc-100 text-xs focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5 font-mono text-xs">
              <label className="text-zinc-300 block">Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 rounded-md bg-[#0d1117] border border-[#30363d] text-zinc-100 text-xs focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs transition-colors shadow cursor-pointer disabled:opacity-50"
            >
              {loading ? "Authenticating via Supabase..." : "Sign In to Control Center"}
            </button>
          </form>

          <div className="relative flex py-1 items-center">
            <div className="flex-grow border-t border-[#30363d]"></div>
            <span className="flex-shrink mx-3 text-[10px] font-mono text-zinc-400 uppercase">
              Evaluation Access
            </span>
            <div className="flex-grow border-t border-[#30363d]"></div>
          </div>

          <button
            onClick={handleDemoAccess}
            className="w-full py-2.5 rounded-lg bg-[#21262d] hover:bg-[#30363d] text-zinc-200 border border-[#30363d] text-xs font-semibold font-mono flex items-center justify-center gap-2 transition-colors cursor-pointer"
          >
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <span>Instant Workspace Access</span>
            <ArrowRight className="w-3.5 h-3.5 text-zinc-400" />
          </button>
        </div>

        {/* Footer Note */}
        <div className="text-center text-[11px] font-mono text-zinc-400">
          Supabase Auth &bull; LangGraph Engine &bull; Groq LLM Inference
        </div>
      </div>
    </div>
  );
};
