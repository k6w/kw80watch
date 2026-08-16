import { sqliteTable, text, integer, blob } from "drizzle-orm/sqlite-core";

// --- Better Auth tables ---

export const user = sqliteTable("user", {
  id: text("id").primaryKey(),
  username: text("username").notNull().default(""),
  email: text("email").notNull().unique(),
  emailVerified: integer("email_verified").notNull().default(0),
  name: text("name"),
  image: text("image"),
  role: text("role").notNull().default("user"),
  createdAt: integer("created_at").notNull().default(Math.floor(Date.now() / 1000)),
  updatedAt: integer("updated_at").notNull().default(Math.floor(Date.now() / 1000)),
});

export const session = sqliteTable("session", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull().references(() => user.id),
  token: text("token").notNull().unique(),
  expiresAt: integer("expires_at").notNull(),
  ipAddress: text("ip_address"),
  userAgent: text("user_agent"),
  createdAt: integer("created_at").notNull().default(Math.floor(Date.now() / 1000)),
  updatedAt: integer("updated_at").notNull().default(Math.floor(Date.now() / 1000)),
});

export const account = sqliteTable("account", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull().references(() => user.id),
  accountId: text("account_id").notNull(),
  providerId: text("provider_id").notNull(),
  accessToken: text("access_token"),
  refreshToken: text("refresh_token"),
  expiresAt: integer("expires_at"),
  password: text("password"),
  createdAt: integer("created_at").notNull().default(Math.floor(Date.now() / 1000)),
  updatedAt: integer("updated_at").notNull().default(Math.floor(Date.now() / 1000)),
});

export const verification = sqliteTable("verification", {
  id: text("id").primaryKey(),
  identifier: text("identifier").notNull(),
  value: text("value").notNull(),
  expiresAt: integer("expires_at").notNull(),
  createdAt: integer("created_at").notNull().default(0),
  updatedAt: integer("updated_at").notNull().default(0),
});

// --- App tables ---

export const projects = sqliteTable("projects", {
  id: text("id").primaryKey(),
  authorId: text("author_id").notNull().references(() => user.id),
  name: text("name").notNull(),
  document: text("document").notNull().default('{"version":1,"elements":[],"assets":[]}'),
  thumbnail: blob("thumbnail"),
  createdAt: integer("created_at").notNull().default(Math.floor(Date.now() / 1000)),
  updatedAt: integer("updated_at").notNull().default(Math.floor(Date.now() / 1000)),
});

export const publishedWatchfaces = sqliteTable("published_watchfaces", {
  id: text("id").primaryKey(),
  projectId: text("project_id").notNull().references(() => projects.id),
  authorId: text("author_id").notNull().references(() => user.id),
  name: text("name").notNull(),
  description: text("description").notNull().default(""),
  binData: blob("bin_data"),
  thumbnail: blob("thumbnail"),
  tags: text("tags").notNull().default("[]"),
  downloadCount: integer("download_count").notNull().default(0),
  featured: integer("featured").notNull().default(0),
  publishedAt: integer("published_at").notNull().default(Math.floor(Date.now() / 1000)),
});

export const assets = sqliteTable("assets", {
  id: text("id").primaryKey(),
  ownerId: text("owner_id").references(() => user.id),
  kind: text("kind").notNull(),
  name: text("name").notNull(),
  storageKey: text("storage_key").notNull(),
  width: integer("width"),
  height: integer("height"),
  cf: integer("cf"),
  meta: text("meta").notNull().default("{}"),
  createdAt: integer("created_at").notNull().default(Math.floor(Date.now() / 1000)),
});

export const ratings = sqliteTable("ratings", {
  userId: text("user_id").notNull().references(() => user.id),
  watchfaceId: text("watchface_id").notNull().references(() => publishedWatchfaces.id),
  score: integer("score").notNull(),
});
