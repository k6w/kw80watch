import { db } from "./index.ts";
import { sql } from "drizzle-orm";

export async function migrate() {
  console.log("Running migrations...");

  // Better Auth tables
  db.run(sql`CREATE TABLE IF NOT EXISTS user (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL UNIQUE,
    email_verified INTEGER NOT NULL DEFAULT 0,
    name TEXT,
    image TEXT,
    role TEXT NOT NULL DEFAULT 'user',
    created_at INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL DEFAULT 0
  )`);

  db.run(sql`CREATE TABLE IF NOT EXISTS session (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES user(id),
    token TEXT NOT NULL UNIQUE,
    expires_at INTEGER NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    created_at INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL DEFAULT 0
  )`);

  db.run(sql`CREATE TABLE IF NOT EXISTS account (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES user(id),
    account_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    expires_at INTEGER,
    password TEXT,
    created_at INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL DEFAULT 0
  )`);

  db.run(sql`CREATE TABLE IF NOT EXISTS verification (
    id TEXT PRIMARY KEY,
    identifier TEXT NOT NULL,
    value TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL DEFAULT 0
  )`);

  // App tables
  db.run(sql`CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    author_id TEXT NOT NULL REFERENCES user(id),
    name TEXT NOT NULL,
    document TEXT NOT NULL DEFAULT '{"version":1,"elements":[],"assets":[]}',
    thumbnail BLOB,
    created_at INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL DEFAULT 0
  )`);

  db.run(sql`CREATE TABLE IF NOT EXISTS published_watchfaces (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    author_id TEXT NOT NULL REFERENCES user(id),
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    bin_data BLOB,
    thumbnail BLOB,
    tags TEXT NOT NULL DEFAULT '[]',
    download_count INTEGER NOT NULL DEFAULT 0,
    featured INTEGER NOT NULL DEFAULT 0,
    published_at INTEGER NOT NULL DEFAULT 0
  )`);

  db.run(sql`CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    owner_id TEXT REFERENCES user(id),
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    cf INTEGER,
    meta TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL DEFAULT 0
  )`);

  db.run(sql`CREATE TABLE IF NOT EXISTS ratings (
    user_id TEXT NOT NULL REFERENCES user(id),
    watchface_id TEXT NOT NULL REFERENCES published_watchfaces(id),
    score INTEGER NOT NULL,
    PRIMARY KEY (user_id, watchface_id)
  )`);

  console.log("Migrations complete.");
}

if (import.meta.main) {
  migrate();
}
