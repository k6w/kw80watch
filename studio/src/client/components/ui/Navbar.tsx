import { Outlet, Link, useLocation } from "react-router-dom";
import { useAuth } from "../../lib/store/auth.ts";

export function Navbar() {
  const { user, signOut } = useAuth();
  const location = useLocation();

  return (
    <>
      <nav className="flex items-center justify-between border-b border-zinc-800 bg-zinc-950 px-6 py-3">
        <div className="flex items-center gap-8">
          <Link to="/dashboard" className="text-lg font-bold text-white">
            KW80 Studio
          </Link>
          <div className="flex items-center gap-4 text-sm">
            <Link
              to="/dashboard"
              className={location.pathname.startsWith("/dashboard") || location.pathname.startsWith("/editor")
                ? "text-indigo-400"
                : "text-zinc-400 hover:text-white"}
            >
              My Projects
            </Link>
            <Link
              to="/marketplace"
              className={location.pathname.startsWith("/marketplace")
                ? "text-indigo-400"
                : "text-zinc-400 hover:text-white"}
            >
              Marketplace
            </Link>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-zinc-400">{user?.username}</span>
          <button
            onClick={signOut}
            className="rounded-md bg-zinc-800 px-3 py-1.5 text-sm text-zinc-300 hover:bg-zinc-700"
          >
            Sign Out
          </button>
        </div>
      </nav>
      <Outlet />
    </>
  );
}
