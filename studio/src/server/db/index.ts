import { Database } from "bun:sqlite";
import { drizzle } from "drizzle-orm/bun-sqlite";
import * as schema from "./schema.ts";

const DB_PATH = "./data/studio.db";

export const db = drizzle(new Database(DB_PATH, { create: true }), { schema });

export type DB = typeof db;
