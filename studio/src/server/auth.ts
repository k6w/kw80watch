import { hashSync, compareSync } from "bcryptjs";
import { createId } from "./lib/id.ts";
import { db } from "./db/index.ts";
import { user, session, account } from "./db/schema.ts";
import { eq } from "drizzle-orm";
import { cookies } from "next/headers";

const SESSION_COOKIE = "kw80_session";
const SESSION_MAX_AGE = 60 * 60 * 24 * 30; // 30 days

export function hashPassword(password: string): string {
  return hashSync(password, 10);
}

export function verifyPassword(password: string, hash: string): boolean {
  return compareSync(password, hash);
}

export async function createUser(username: string, email: string, password: string) {
  const existing = db.select().from(user)
    .where(eq(user.email, email))
    .get();
  if (existing) throw new Error("Email already registered");

  const existingUsername = db.select().from(user)
    .where(eq(user.username, username))
    .get();
  if (existingUsername) throw new Error("Username already taken");

  const id = createId();
  const now = Math.floor(Date.now() / 1000);
  const passwordHash = hashPassword(password);

  db.insert(user).values({
    id, username, email, emailVerified: 1,
    name: username, role: "user",
    createdAt: now, updatedAt: now,
  }).run();

  db.insert(account).values({
    id: createId(), userId: id,
    accountId: id, providerId: "credential",
    password: passwordHash,
    createdAt: now, updatedAt: now,
  }).run();

  return { id, username, email, role: "user" };
}

export async function authenticate(email: string, password: string) {
  const u = db.select().from(user).where(eq(user.email, email)).get();
  if (!u) throw new Error("Invalid credentials");

  const acct = db.select().from(account)
    .where(eq(account.userId, u.id))
    .get();
  if (!acct?.password) throw new Error("Invalid credentials");

  if (!verifyPassword(password, acct.password)) {
    throw new Error("Invalid credentials");
  }

  return { id: u.id, username: u.username, email: u.email, role: u.role };
}

export async function createSessionToken(userId: string): Promise<string> {
  const token = createId() + createId();
  const now = Math.floor(Date.now() / 1000);
  db.insert(session).values({
    id: createId(), userId, token,
    expiresAt: now + SESSION_MAX_AGE,
    createdAt: now, updatedAt: now,
  }).run();
  return token;
}

export function getSessionFromRequest(headers: Headers) {
  const cookie = headers.get("cookie") || "";
  const match = cookie.match(new RegExp(`${SESSION_COOKIE}=([^;]+)`));
  if (!match) return null;

  const token = match[1];
  const sess = db.select().from(session)
    .where(eq(session.token, token))
    .get();
  if (!sess) return null;

  const now = Math.floor(Date.now() / 1000);
  if (sess.expiresAt < now) return null;

  const u = db.select().from(user)
    .where(eq(user.id, sess.userId))
    .get();
  if (!u) return null;

  return {
    user: { id: u.id, username: u.username, email: u.email, role: u.role },
    session: { id: sess.id, userId: sess.userId },
  };
}

export function destroySession(token: string) {
  db.delete(session).where(eq(session.token, token)).run();
}

export function setSessionCookie(token: string): string {
  return `${SESSION_COOKIE}=${token}; Path=/; HttpOnly; Max-Age=${SESSION_MAX_AGE}; SameSite=Lax`;
}

export function clearSessionCookie(): string {
  return `${SESSION_COOKIE}=; Path=/; HttpOnly; Max-Age=0; SameSite=Lax`;
}

export function getTokenFromHeaders(headers: Headers): string | null {
  const cookie = headers.get("cookie") || "";
  const match = cookie.match(new RegExp(`${SESSION_COOKIE}=([^;]+)`));
  return match ? match[1] : null;
}
