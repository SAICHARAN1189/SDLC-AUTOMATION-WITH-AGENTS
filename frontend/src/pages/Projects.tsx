import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  FolderGit2,
  Plus,
  Play,
  Calendar,
  Activity,
  Search,
  ExternalLink,
} from "lucide-react";
import { getProjects, createRun } from "../services/api";
import type { Project } from "../types";

export const Projects: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    getProjects()
      .then((data) => {
        if (mounted) setProjects(data);
      })
      .catch((e) => console.warn(e))
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const handleLaunchRun = async (projectId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const run = await createRun(projectId);
      navigate(`/live?run_id=${run.id}&project_id=${projectId}`);
    } catch (err) {
      console.error(err);
    }
  };

  const filtered = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.idea.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
            <FolderGit2 className="w-5 h-5 text-emerald-400" /> Managed SDLC Projects
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Persisted projects and multi-agent execution pipelines stored in Supabase PostgreSQL.
          </p>
        </div>

        <Link
          to="/projects/new"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs transition-colors cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>New Project</span>
        </Link>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search projects by title or specification..."
          className="w-full pl-9 pr-4 py-2 rounded-lg bg-[#161b22] border border-[#30363d] text-xs text-zinc-200 focus:outline-none focus:border-emerald-500 font-mono"
        />
      </div>

      {/* Projects Grid */}
      {loading ? (
        <div className="text-center py-12 text-xs font-mono text-zinc-400">Loading projects...</div>
      ) : filtered.length === 0 ? (
        <div className="p-12 text-center rounded-xl border border-[#30363d] bg-[#161b22] space-y-3">
          <FolderGit2 className="w-10 h-10 text-zinc-400 mx-auto" />
          <div className="text-sm font-semibold text-zinc-200">No Projects Found</div>
          <p className="text-xs text-zinc-400 max-w-md mx-auto">
            Get started by creating an autonomous SDLC project from a natural language software specification.
          </p>
          <Link
            to="/projects/new"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-500 text-black font-semibold text-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Project</span>
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((proj) => (
            <div
              key={proj.id}
              onClick={() => navigate(`/projects/${proj.id}`)}
              className="p-5 rounded-xl border border-[#30363d] bg-[#161b22] hover:border-[#8b949e]/50 transition-all cursor-pointer flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    {proj.status || "ACTIVE"}
                  </span>
                  <span className="text-[10px] font-mono text-zinc-400 flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {proj.created_at ? new Date(proj.created_at).toLocaleDateString() : "Active"}
                  </span>
                </div>

                <h2 className="text-sm font-bold text-zinc-100 mt-2.5 truncate">{proj.name}</h2>
                <p className="text-xs text-zinc-400 font-sans mt-1.5 line-clamp-3 leading-relaxed">
                  {proj.idea}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-[#30363d] flex items-center justify-between">
                <span className="text-[11px] font-mono text-zinc-400">
                  Runs: <strong>{proj.runs?.length || 0}</strong>
                </span>
                <button
                  onClick={(e) => handleLaunchRun(proj.id, e)}
                  className="flex items-center gap-1 px-2 py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-mono transition-colors"
                >
                  <Play className="w-3 h-3 fill-current" />
                  <span>Launch Run</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
