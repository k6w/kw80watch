import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";

interface FaceDetail {
  id: string;
  name: string;
  description: string;
  authorName: string;
  tags: string;
  downloadCount: number;
  featured: number;
  publishedAt: number;
  hasThumbnail: number;
  hasBin: number;
}

export function MarketplaceDetail() {
  const { id } = useParams();
  const [face, setFace] = useState<FaceDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/marketplace/${id}`)
      .then((r) => r.json())
      .then((data) => {
        setFace(data.face);
        setLoading(false);
      });
  }, [id]);

  if (loading) return <div className="p-8 text-zinc-500">Loading...</div>;
  if (!face) return <div className="p-8 text-zinc-500">Not found</div>;

  return (
    <div className="min-h-screen bg-zinc-950">
      <nav className="flex items-center justify-between border-b border-zinc-800 px-6 py-3">
        <Link to="/marketplace" className="text-lg font-bold text-white">KW80 Studio</Link>
        <Link to="/dashboard" className="text-sm text-indigo-400 hover:text-indigo-300">
          Dashboard
        </Link>
      </nav>

      <div className="mx-auto flex max-w-4xl gap-8 p-8">
        {/* Preview */}
        <div className="shrink-0">
          <div className="overflow-hidden rounded-2xl border border-zinc-800 bg-black">
            {face.hasThumbnail ? (
              <img
                src={`/api/marketplace/${id}/thumbnail`}
                alt={face.name}
                className="h-[438px] w-[360px] object-contain"
              />
            ) : (
              <div className="flex h-[438px] w-[360px] items-center justify-center text-zinc-700">
                <span>No preview</span>
              </div>
            )}
          </div>
        </div>

        {/* Details */}
        <div className="flex-1">
          <div className="mb-1 flex items-center gap-2">
            {face.featured ? (
              <span className="rounded-full bg-indigo-500/20 px-2 py-0.5 text-xs text-indigo-400">Featured</span>
            ) : null}
          </div>
          <h1 className="mb-2 text-3xl font-bold text-white">{face.name}</h1>
          <p className="mb-4 text-sm text-zinc-400">
            by <span className="text-indigo-400">{face.authorName}</span>
          </p>
          <p className="mb-6 text-sm text-zinc-400">{face.description}</p>

          <div className="mb-6 flex gap-4 text-sm text-zinc-500">
            <span>{face.downloadCount} downloads</span>
            <span>·</span>
            <span>{new Date(face.publishedAt * 1000).toLocaleDateString()}</span>
          </div>

          <div className="flex gap-3">
            {face.hasBin ? (
              <>
                <a
                  href={`/api/marketplace/${id}/download`}
                  className="rounded-lg bg-indigo-600 px-4 py-2.5 font-medium text-white transition hover:bg-indigo-500"
                >
                  Download .bin
                </a>
                <button
                  className="rounded-lg bg-zinc-800 px-4 py-2.5 font-medium text-zinc-300 transition hover:bg-zinc-700"
                >
                  Send to Watch
                </button>
              </>
            ) : (
              <span className="text-sm text-zinc-500">No binary available</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
