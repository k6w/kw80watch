import { Hono } from "hono";
import { db } from "../db/index.ts";
import { publishedWatchfaces, user, ratings } from "../db/schema.ts";
import { eq, desc, sql, and } from "drizzle-orm";
import { createId } from "../lib/id.ts";

export const marketplaceRoutes = new Hono();

marketplaceRoutes.get("/", async (c) => {
  const q = c.req.query("q");
  const sort = c.req.query("sort") || "newest";
  const tag = c.req.query("tag");

  const conditions = [];
  if (q) {
    conditions.push(sql`${publishedWatchfaces.name} LIKE ${"%" + q + "%"}`);
  }
  if (tag) {
    conditions.push(sql`${publishedWatchfaces.tags} LIKE ${"%" + tag + "%"}`);
  }

  const where = conditions.length > 0 ? and(...conditions) : undefined;

  const faces = db.select({
    id: publishedWatchfaces.id,
    name: publishedWatchfaces.name,
    description: publishedWatchfaces.description,
    authorId: publishedWatchfaces.authorId,
    authorName: user.username,
    tags: publishedWatchfaces.tags,
    downloadCount: publishedWatchfaces.downloadCount,
    featured: publishedWatchfaces.featured,
    publishedAt: publishedWatchfaces.publishedAt,
    hasThumbnail: sql`${publishedWatchfaces.thumbnail} IS NOT NULL`,
  })
  .from(publishedWatchfaces)
  .innerJoin(user, eq(publishedWatchfaces.authorId, user.id))
  .where(where)
  .orderBy(sort === "popular"
    ? desc(publishedWatchfaces.downloadCount)
    : desc(publishedWatchfaces.publishedAt))
  .all();

  return c.json({ faces });
});

marketplaceRoutes.get("/:id", async (c) => {
  const id = c.req.param("id");
  const face = db.select({
    id: publishedWatchfaces.id,
    projectId: publishedWatchfaces.projectId,
    authorId: publishedWatchfaces.authorId,
    authorName: user.username,
    name: publishedWatchfaces.name,
    description: publishedWatchfaces.description,
    tags: publishedWatchfaces.tags,
    downloadCount: publishedWatchfaces.downloadCount,
    featured: publishedWatchfaces.featured,
    publishedAt: publishedWatchfaces.publishedAt,
    hasThumbnail: sql`${publishedWatchfaces.thumbnail} IS NOT NULL`,
    hasBin: sql`${publishedWatchfaces.binData} IS NOT NULL`,
  })
  .from(publishedWatchfaces)
  .innerJoin(user, eq(publishedWatchfaces.authorId, user.id))
  .where(eq(publishedWatchfaces.id, id))
  .get();

  if (!face) return c.json({ error: "Not found" }, 404);

  return c.json({ face });
});

marketplaceRoutes.get("/:id/thumbnail", async (c) => {
  const id = c.req.param("id");
  const face = db.select({ thumbnail: publishedWatchfaces.thumbnail })
    .from(publishedWatchfaces)
    .where(eq(publishedWatchfaces.id, id))
    .get();

  if (!face?.thumbnail) return c.json({ error: "No thumbnail" }, 404);

  return new Response(face.thumbnail, {
    headers: { "Content-Type": "image/png" },
  });
});

marketplaceRoutes.get("/:id/download", async (c) => {
  const id = c.req.param("id");
  const face = db.select({ binData: publishedWatchfaces.binData, name: publishedWatchfaces.name })
    .from(publishedWatchfaces)
    .where(eq(publishedWatchfaces.id, id))
    .get();

  if (!face?.binData) return c.json({ error: "No binary" }, 404);

  db.update(publishedWatchfaces)
    .set({ downloadCount: sql`${publishedWatchfaces.downloadCount} + 1` })
    .where(eq(publishedWatchfaces.id, id))
    .run();

  return new Response(face.binData, {
    headers: {
      "Content-Type": "application/octet-stream",
      "Content-Disposition": `attachment; filename="${face.name}.bin"`,
    },
  });
});

marketplaceRoutes.post("/publish", async (c) => {
  const u = c.get("user");
  const body = await c.req.json();
  const { name, description, tags, binData, thumbnail, projectId } = body;

  const id = createId();
  const now = Math.floor(Date.now() / 1000);
  const binBytes = binData ? Uint8Array.from(atob(binData), (ch) => ch.charCodeAt(0)) : null;
  const thumbBytes = thumbnail ? Uint8Array.from(atob(thumbnail), (ch) => ch.charCodeAt(0)) : null;

  db.insert(publishedWatchfaces).values({
    id,
    projectId,
    authorId: u.id,
    name,
    description: description || "",
    binData: binBytes,
    thumbnail: thumbBytes,
    tags: JSON.stringify(tags || []),
    publishedAt: now,
  }).run();

  return c.json({ id, success: true });
});

marketplaceRoutes.post("/:id/rate", async (c) => {
  const u = c.get("user");
  const id = c.req.param("id");
  const { score } = await c.req.json();

  if (score < 1 || score > 5) return c.json({ error: "Invalid score" }, 400);

  db.insert(ratings)
    .values({ userId: u.id, watchfaceId: id, score })
    .onConflictDoReplace()
    .run();

  return c.json({ success: true });
});
