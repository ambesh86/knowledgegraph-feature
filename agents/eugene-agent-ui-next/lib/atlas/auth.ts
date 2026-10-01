import "server-only";
import { cookies } from "next/headers";
import bcrypt from "bcryptjs";
import { SignJWT, jwtVerify, type JWTPayload } from "jose";

/**
 * Atlas authentication primitives: password hashing (bcrypt), stateless
 * session tokens (signed JWT in an httpOnly cookie), and helpers to read the
 * current user on the server.
 */

export const SESSION_COOKIE = "atlas_session";
const SESSION_TTL_SECONDS = 60 * 60 * 24 * 7; // 7 days
const BCRYPT_ROUNDS = 12;

export interface SessionUser {
  id: string;
  email: string;
  name: string;
  role: string;
  focusArea: string;
}

function secret(): Uint8Array {
  const raw =
    process.env.ATLAS_JWT_SECRET ??
    "dev-atlas-secret-change-in-prod-please-32chars";
  return new TextEncoder().encode(raw);
}

export function hashPassword(plain: string): Promise<string> {
  return bcrypt.hash(plain, BCRYPT_ROUNDS);
}

export function verifyPassword(plain: string, hash: string): Promise<boolean> {
  return bcrypt.compare(plain, hash);
}

export async function signSession(user: SessionUser): Promise<string> {
  return new SignJWT({
    email: user.email,
    name: user.name,
    role: user.role,
    focusArea: user.focusArea,
  })
    .setProtectedHeader({ alg: "HS256", typ: "JWT" })
    .setSubject(user.id)
    .setIssuedAt()
    .setIssuer("atlas")
    .setExpirationTime(`${SESSION_TTL_SECONDS}s`)
    .sign(secret());
}

export async function verifySession(token: string): Promise<SessionUser | null> {
  try {
    const { payload } = await jwtVerify(token, secret(), { issuer: "atlas" });
    const p = payload as JWTPayload & {
      email?: string;
      name?: string;
      role?: string;
      focusArea?: string;
    };
    if (!p.sub || !p.email || !p.name) return null;
    return {
      id: p.sub,
      email: p.email,
      name: p.name,
      role: p.role ?? "analyst",
      focusArea: p.focusArea ?? "hematology",
    };
  } catch {
    return null;
  }
}

/** Set the session cookie (httpOnly). Secure only behind HTTPS. */
export async function setSessionCookie(token: string): Promise<void> {
  const store = await cookies();
  store.set({
    name: SESSION_COOKIE,
    value: token,
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_TTL_SECONDS,
    secure: process.env.ATLAS_COOKIE_SECURE === "true",
  });
}

export async function clearSessionCookie(): Promise<void> {
  const store = await cookies();
  store.delete(SESSION_COOKIE);
}

/** Read + verify the current session from the request cookies. */
export async function currentUser(): Promise<SessionUser | null> {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!token) return null;
  return verifySession(token);
}

// ── validation helpers ────────────────────────────────────────────────────
export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateCredentials(email: string, password: string): string | null {
  if (!email || !EMAIL_RE.test(email)) return "Enter a valid email address.";
  if (!password || password.length < 8)
    return "Password must be at least 8 characters.";
  return null;
}
