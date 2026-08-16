import { Hono } from "hono";
import { logger } from "hono/logger";
import { cors } from "hono/cors";
import { serveStatic } from "hono/bun";
import {
  createUser, authenticate, createSessionToken,
  getSessionFromRequest, destroySession, setSessionCookie,
  clearSessionCookie, getTokenFromHeaders,
} from "./auth.ts";
import { projectRoutes } from "./routes/projects.ts";
import { marketplaceRoutes } from "./routes/marketplace.ts";

const app = new Hono();

app.use("*", logger());
app.use("*", cors({
  origin: ["http://localhost:5173", "http://localhost:3000"],
  credentials: true,
}));

// Auth routes
app.post("/api/auth/sign-up", async (c) => {
  try {
    const body = await c.req.json();
    const { username, email, password } = body;
    if (!username || !email || !password) {
      return c.json({ error: "Missing fields" }, 400);
    }
    if (password.length < 8) {
      return c.json({ error: "Password must be at least 8 characters" }, 400);
    }
    const u = await createUser(username, email, password);
    const token = await createSessionToken(u.id);
    c.header("Set-Cookie", setSessionCookie(token));
    return c.json({ user: u });
  } catch (e) {
    return c.json({ error: e instanceof Error ? e.message : "Sign up failed" }, 400);
  }
});

app.post("/api/auth/sign-in", async (c) => {
  try {
    const body = await c.req.json();
    const { email, password } = body;
    if (!email || !password) {
      return c.json({ error: "Missing email or password" }, 400);
    }
    const u = await authenticate(email, password);
    const token = await createSessionToken(u.id);
    c.header("Set-Cookie", setSessionCookie(token));
    return c.json({ user: u });
  } catch {
    return c.json({ error: "Invalid credentials" }, 401);
  }
});

app.post("/api/auth/sign-out", async (c) => {
  const token = getTokenFromHeaders(c.req.raw.headers);
  if (token) destroySession(token);
  c.header("Set-Cookie", clearSessionCookie());
  return c.json({ success: true });
});

app.get("/api/me", async (c) => {
  const session = getSessionFromRequest(c.req.raw.headers);
  if (!session) return c.json({ user: null });
  return c.json({ user: session.user });
});

// Auth middleware for protected routes
app.use("/api/projects/*", async (c, next) => {
  const session = getSessionFromRequest(c.req.raw.headers);
  if (!session) return c.json({ error: "Unauthorized" }, 401);
  c.set("user", session.user as any);
  await next();
});

app.use("/api/marketplace/publish", async (c, next) => {
  const session = getSessionFromRequest(c.req.raw.headers);
  if (!session) return c.json({ error: "Unauthorized" }, 401);
  c.set("user", session.user as any);
  await next();
});

app.route("/api/projects", projectRoutes);
app.route("/api/marketplace", marketplaceRoutes);

app.get("/api/health", (c) => c.json({ status: "ok", time: Date.now() }));

app.use("/assets/*", serveStatic({ root: "./data/" }));

if (process.env.NODE_ENV === "production") {
  app.use("*", serveStatic({ root: "./dist/client" }));
  app.get("*", serveStatic({ path: "./dist/client/index.html" }));
}

const port = Number(process.env.PORT) || 3000;

export default {
  port,
  fetch: app.fetch,
};

console.log(`KW80 Studio running on http://localhost:${port}`);
