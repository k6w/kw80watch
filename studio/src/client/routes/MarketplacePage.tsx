import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

interface MarketFace {
  id: string;
  name: string;
  description: string;
  authorName: string;
  tags: string;
  downloadCount: number;
  featured: number;
  publishedAt: number;
  hasThumbnail: number;
}

export function MarketplacePage() {
  const [faces, setFaces] = useState<MarketFace[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("newest");

  useEffect(() => {
    const params = new URLSearchParams();
    if (search) params.set("q", search);
    if (sort) params.set("sort", sort);
    fetch(`/api/marketplace?${params}`)
      .then((r) => r.json())
      .then((data) => {
        setFaces(data.faces || []);
        setLoading(false);
      });
  }, [search, sort]);

  return (
    <div className="min-h-screen bg-zinc-950">
      <nav className="flex items-center justify-between border-b border-zinc-800 px-6 py-3">
        <Link to="/marketplace" className="text-lg font-bold text-white">KW80 Studio</Link>
        <Link to="/dashboard" className="text-sm text-indigo-400 hover:text-indigo-300">
          Dashboard
        </Link>
      </nav>

      <div className="mx-auto max-w-6xl p-6">
        <div className="mb-6 flex items-center justify-between gap-4">
          <h1 className="text-2xl font-bold text-white">Marketplace</h1>
          <div className="flex items-center gap-3">
            <input
              type="text"
              placeholder="Search watchfaces..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-64 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-white outline-none focus:border-indigo-500"
            />
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-white outline-none"
            >
              <option value="newest">Newest</option>
              <option value="popular">Most Downloaded</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="text-zinc-500">Loading...</div>
        ) : faces.length === 0 ? (
          <div className="text-zinc-500">No watchfaces found.</div>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {faces.map((face) => (
              <Link
                key={face.id}
                to={`/marketplace/${face.id}`}
                className="group overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900 transition hover:border-indigo-600"
              >
                <div className="aspect-[180/219] bg-black">
                  {face.hasThumbnail ? (
                    <img
                      src={`/api/marketplace/${face.id}/thumbnail`}
                      alt={face.name}
                      className="h-full w-full object-contain"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-zinc-700">
                      <span className="text-xs">No preview</span>
                    </div>
                  )}
                </div>
                <div className="p-3">
                  <div className="truncate text-sm font-medium text-white group-hover:text-indigo-400">
                    {face.name}
                  </div>
                  <div className="text-xs text-zinc-500">
                    by {face.authorName} · {face.downloadCount} downloads
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
