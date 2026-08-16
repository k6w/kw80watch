import { Hono } from "hono";
import { db } from "../db/index.ts";
import { projects } from "../db/schema.ts";
import { eq } from "drizzle-orm";
import { createId } from "../lib/id.ts";

export const projectRoutes = new Hono();

projectRoutes.get("/", async (c) => {
  const u = c.get("user");
  const list = db.select()
    .from(projects)
    .where(eq(projects.authorId, u.id))
    .all();
  return c.json({ projects: list });
});

projectRoutes.post("/", async (c) => {
  const u = c.get("user");
  const body = await c.req.json();
  const id = createId();
  const now = Math.floor(Date.now() / 1000);

  db.insert(projects).values({
    id,
    authorId: u.id,
    name: body.name || "Untitled Watchface",
    document: body.document || '{"version":1,"elements":[],"assets":[]}',
    createdAt: now,
    updatedAt: now,
  }).run();

  const project = db.select().from(projects).where(eq(projects.id, id)).get();
  return c.json({ project });
});

projectRoutes.get("/:id", async (c) => {
  const u = c.get("user");
  const id = c.req.param("id");
  const project = db.select().from(projects).where(eq(projects.id, id)).get();

  if (!project) return c.json({ error: "Not found" }, 404);
  if (project.authorId !== u.id) return c.json({ error: "Forbidden" }, 403);

  return c.json({ project });
});

projectRoutes.put("/:id", async (c) => {
  const u = c.get("user");
  const id = c.req.param("id");
  const project = db.select().from(projects).where(eq(projects.id, id)).get();

  if (!project) return c.json({ error: "Not found" }, 404);
  if (project.authorId !== u.id) return c.json({ error: "Forbidden" }, 403);

  const body = await c.req.json();
  const now = Math.floor(Date.now() / 1000);

  db.update(projects).set({
    name: body.name ?? project.name,
    document: body.document ?? project.document,
    thumbnail: body.thumbnail ?? project.thumbnail,
    updatedAt: now,
  }).where(eq(projects.id, id)).run();

  const updated = db.select().from(projects).where(eq(projects.id, id)).get();
  return c.json({ project: updated });
});

projectRoutes.delete("/:id", async (c) => {
  const u = c.get("user");
  const id = c.req.param("id");
  const project = db.select().from(projects).where(eq(projects.id, id)).get();

  if (!project) return c.json({ error: "Not found" }, 404);
  if (project.authorId !== u.id) return c.json({ error: "Forbidden" }, 403);

  db.delete(projects).where(eq(projects.id, id)).run();
  return c.json({ success: true });
});
