import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../lib/store/auth.ts";

interface Project {
  id: string;
  name: string;
  updated_at: number;
}

export function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/projects")
      .then((r) => r.json())
      .then((data) => {
        setProjects(data.projects || []);
        setLoading(false);
      });
  }, []);

  const createProject = async () => {
    const res = await fetch("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Untitled Watchface" }),
    });
    const data = await res.json();
    navigate(`/editor/${data.project.id}`);
  };

  return (
    <div className="mx-auto max-w-5xl p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">My Projects</h1>
          <p className="text-sm text-zinc-500">Welcome back, {user?.username}</p>
        </div>
        <button
          onClick={createProject}
          className="rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white transition hover:bg-indigo-500"
        >
          + New Watchface
        </button>
      </div>

      {loading ? (
        <div className="text-zinc-500">Loading...</div>
      ) : projects.length === 0 ? (
        <div className="rounded-xl border border-dashed border-zinc-800 p-12 text-center">
          <p className="text-zinc-500">No projects yet. Create your first watchface!</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
          {projects.map((p) => (
            <button
              key={p.id}
              onClick={() => navigate(`/editor/${p.id}`)}
              className="group rounded-xl border border-zinc-800 bg-zinc-900 p-4 text-left transition hover:border-indigo-600"
            >
              <div className="mb-3 aspect-[368/448] rounded-lg bg-zinc-800" />
              <div className="truncate text-sm font-medium text-white group-hover:text-indigo-400">
                {p.name}
              </div>
              <div className="text-xs text-zinc-600">
                {new Date(p.updated_at * 1000).toLocaleDateString()}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
