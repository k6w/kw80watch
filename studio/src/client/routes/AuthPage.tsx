import { useState } from "react";
import { useAuth } from "../lib/store/auth.ts";

export function AuthPage() {
  const { signIn, signUp } = useAuth();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const ok = mode === "login"
      ? await signIn(email, password)
      : await signUp(username, email, password);

    if (!ok) {
      setError(mode === "login" ? "Invalid credentials" : "Sign up failed — username or email may be taken");
    }
    setLoading(false);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950">
      <div className="w-full max-w-sm space-y-6 rounded-2xl border border-zinc-800 bg-zinc-900 p-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white">KW80 Studio</h1>
          <p className="mt-1 text-sm text-zinc-500">
            {mode === "login" ? "Welcome back" : "Create your account"}
          </p>
        </div>

        <div className="flex rounded-lg bg-zinc-800 p-0.5">
          <button
            onClick={() => setMode("login")}
            className={`flex-1 rounded-md py-2 text-sm font-medium transition ${
              mode === "login" ? "bg-zinc-700 text-white" : "text-zinc-400"
            }`}
          >
            Login
          </button>
          <button
            onClick={() => setMode("signup")}
            className={`flex-1 rounded-md py-2 text-sm font-medium transition ${
              mode === "signup" ? "bg-zinc-700 text-white" : "text-zinc-400"
            }`}
          >
            Sign Up
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "signup" && (
            <div>
              <label className="mb-1.5 block text-sm text-zinc-400">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2.5 text-white outline-none focus:border-indigo-500"
                placeholder="your_username"
              />
            </div>
          )}
          <div>
            <label className="mb-1.5 block text-sm text-zinc-400">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2.5 text-white outline-none focus:border-indigo-500"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-zinc-400">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2.5 text-white outline-none focus:border-indigo-500"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-400">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-indigo-600 py-2.5 font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
          >
            {loading ? "..." : mode === "login" ? "Login" : "Create Account"}
          </button>
        </form>

        <p className="text-center text-xs text-zinc-600">
          No name required — just username, email, and password.
        </p>
      </div>
    </div>
  );
}
