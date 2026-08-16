import { db } from "./index.ts";
import { user, publishedWatchfaces, projects, account } from "./schema.ts";
import { migrate } from "./migrate.ts";
import { createId } from "../lib/id.ts";
import { eq } from "drizzle-orm";
import { hashSync } from "bcryptjs";
import { promises as fs } from "fs";
import path from "path";

const ROOT = path.resolve(import.meta.dir, "../../../..");
const SAMPLES_DIR = path.join(ROOT, "artifacts/samples");
const THUMBS_DIR = path.join(ROOT, "artifacts/thumbs");

const ADMIN_USERNAME = "admin";
const ADMIN_EMAIL = "admin@kw80.studio";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "admin123";

async function seed() {
  console.log("Running migrations...");
  await migrate();

  console.log("Creating admin user...");
  let admin = db.select().from(user).where(eq(user.username, ADMIN_USERNAME)).get();
  if (!admin) {
    const adminId = createId();
    const now = Math.floor(Date.now() / 1000);
    const passwordHash = hashSync(ADMIN_PASSWORD, 10);

    db.insert(user).values({
      id: adminId,
      username: ADMIN_USERNAME,
      email: ADMIN_EMAIL,
      emailVerified: 1,
      name: ADMIN_USERNAME,
      role: "admin",
      createdAt: now,
      updatedAt: now,
    }).run();

    // better-auth stores password in account table with providerId "credential"
    db.insert(account).values({
      id: createId(),
      userId: adminId,
      accountId: adminId,
      providerId: "credential",
      password: passwordHash,
      createdAt: now,
      updatedAt: now,
    }).run();

    admin = db.select().from(user).where(eq(user.username, ADMIN_USERNAME)).get();
    console.log(`  Admin created: ${ADMIN_USERNAME} / ${ADMIN_PASSWORD}`);
  } else {
    console.log("  Admin already exists");
  }

  const sampleBins = await fs.readdir(SAMPLES_DIR).catch(() => []);
  const thumbPngs = await fs.readdir(THUMBS_DIR).catch(() => []);

  console.log(`Found ${sampleBins.length} sample faces, ${thumbPngs.length} thumbnails`);

  let imported = 0;
  for (const binFile of sampleBins) {
    if (!binFile.endsWith(".bin")) continue;

    const name = binFile.replace(".bin", "");
    const existing = db.select().from(publishedWatchfaces)
      .where(eq(publishedWatchfaces.name, name))
      .get();
    if (existing) continue;

    const binPath = path.join(SAMPLES_DIR, binFile);
    const binData = await fs.readFile(binPath);

    let thumbnail: Buffer | null = null;
    const thumbBase = name.replace("WF", "");
    const thumbFile = thumbPngs.find(
      (f) => f.replace(".png", "") === name || f.replace(".png", "") === thumbBase,
    );
    if (thumbFile) {
      thumbnail = await fs.readFile(path.join(THUMBS_DIR, thumbFile));
    }

    const projectId = createId();
    const now = Math.floor(Date.now() / 1000);
    db.insert(projects).values({
      id: projectId,
      authorId: admin!.id,
      name,
      document: JSON.stringify({ version: 1, elements: [], assets: [] }),
      createdAt: now,
      updatedAt: now,
    }).run();

    const pubId = createId();
    db.insert(publishedWatchfaces).values({
      id: pubId,
      projectId,
      authorId: admin!.id,
      name,
      description: `Official KW80 watchface ${name}`,
      binData,
      thumbnail,
      tags: JSON.stringify(["official"]),
      featured: imported < 12 ? 1 : 0,
      publishedAt: now - (sampleBins.length - imported) * 1000,
    }).run();

    imported++;
  }

  console.log(`Imported ${imported} official watchfaces`);
  console.log("Seed complete.");
}

seed().catch(console.error);
