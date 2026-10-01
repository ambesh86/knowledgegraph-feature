import "server-only";
import crypto from "crypto";
import { SignJWT } from "jose";
import { getSetting, setSetting } from "./db";

/**
 * Self-minting of Eugene backend access tokens.
 *
 * The Eugene backend validates a symmetric (HS256) JWT signed with a shared
 * secret (EUGENE_CLIENT_SECRET) and checks issuer/audience + the claims
 * tid/sub/roles/upn. Given that secret we can mint valid tokens on demand —
 * so the UI never depends on a short-lived pasted token again.
 *
 * The secret is entered once via Settings > Backend Connection and stored
 * ENCRYPTED (AES-256-GCM) in Postgres (app_settings), so it survives reboots
 * without ever living in the container image or in env/version control.
 */

const SETTING_SECRET = "eugene_client_secret_enc"; // AES-GCM ciphertext
const SETTING_UPN = "eugene_mint_upn"; // UPN stamped into minted tokens

// Non-secret backend identifiers. Recoverable from any issued token; defaults
// match the prod Eugene deployment. Overridable via env if it ever changes.
const TENANT_ID =
  process.env.EUGENE_TENANT_ID ?? "f8645748-68c6-4eec-bd61-c71341a6ed7d";
const CLIENT_ID =
  process.env.EUGENE_CLIENT_ID ?? "ff58ded5-c309-4cc8-ae6a-3b7157b83879";
const ISSUER =
  process.env.EUGENE_ISSUER ?? `https://eugene.ai.cslg1.cslg.net/${TENANT_ID}`;
const AUDIENCE = process.env.EUGENE_AUDIENCE ?? `api://eugene/${CLIENT_ID}`;
// UPN stamped into minted tokens. Rajesh.Gupta is the deploying user and is
// proven-accepted by the prod agent (the backend-issued token we validated
// carried exactly this UPN). Overridable in Settings or via env.
const DEFAULT_UPN =
  process.env.EUGENE_MINT_UPN ?? "Rajesh.Gupta@cslbehring.com";
const ROLES = (process.env.EUGENE_MINT_ROLES ?? "user.public.read").split(",");
// Minted-token lifetime. The UI re-mints on every load, so this only needs to
// outlast a single session; keep it well under the backend's 24h ceiling.
const TOKEN_TTL_SECONDS = 60 * 60 * 12;

/** 32-byte key for encrypting the stored secret, derived from ATLAS_JWT_SECRET. */
function encKey(): Buffer {
  const base =
    process.env.ATLAS_JWT_SECRET ??
    "dev-atlas-secret-change-in-prod-please-32chars";
  return crypto.createHash("sha256").update(base).digest();
}

function encrypt(plain: string): string {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", encKey(), iv);
  const ct = Buffer.concat([cipher.update(plain, "utf8"), cipher.final()]);
  const tag = cipher.getAuthTag();
  return `${iv.toString("base64")}.${tag.toString("base64")}.${ct.toString("base64")}`;
}

function decrypt(blob: string): string {
  const [ivB, tagB, ctB] = blob.split(".");
  const decipher = crypto.createDecipheriv(
    "aes-256-gcm",
    encKey(),
    Buffer.from(ivB, "base64")
  );
  decipher.setAuthTag(Buffer.from(tagB, "base64"));
  return Buffer.concat([
    decipher.update(Buffer.from(ctB, "base64")),
    decipher.final(),
  ]).toString("utf8");
}

/** Persist the signing secret (encrypted) and optional UPN. */
export async function saveBackendConfig(
  secret: string,
  upn?: string
): Promise<void> {
  await setSetting(SETTING_SECRET, encrypt(secret));
  if (upn && upn.trim()) await setSetting(SETTING_UPN, upn.trim());
}

async function getSecret(): Promise<string | null> {
  const blob = await getSetting(SETTING_SECRET);
  if (!blob) return null;
  try {
    return decrypt(blob);
  } catch {
    return null; // ATLAS_JWT_SECRET changed → force re-entry
  }
}

/** True when a signing secret is stored and self-minting is possible. */
export async function backendConfigured(): Promise<boolean> {
  return (await getSecret()) !== null;
}

export interface BackendStatus {
  configured: boolean;
  upn: string;
  issuer: string;
  audience: string;
}

/** Non-sensitive status for the Settings UI (never returns the secret). */
export async function backendStatus(): Promise<BackendStatus> {
  return {
    configured: await backendConfigured(),
    upn: (await getSetting(SETTING_UPN)) ?? DEFAULT_UPN,
    issuer: ISSUER,
    audience: AUDIENCE,
  };
}

/**
 * Mint a fresh Eugene access token. Returns { token, expiresIn } or null when
 * no secret is configured (caller falls back to env/dev token).
 */
export async function mintEugeneToken(): Promise<{
  token: string;
  expiresIn: number;
} | null> {
  const secret = await getSecret();
  if (!secret) return null;
  const upn = (await getSetting(SETTING_UPN)) ?? DEFAULT_UPN;
  const user = upn.split("@", 1)[0];

  const token = await new SignJWT({
    tid: TENANT_ID,
    sub: user,
    roles: ROLES,
    upn,
    name: user,
    preferred_username: upn,
    oid: "",
  })
    .setProtectedHeader({ alg: "HS256", typ: "JWT" })
    .setIssuer(ISSUER)
    .setAudience(AUDIENCE)
    .setIssuedAt()
    .setExpirationTime(`${TOKEN_TTL_SECONDS}s`)
    .sign(new TextEncoder().encode(secret));

  return { token, expiresIn: TOKEN_TTL_SECONDS };
}
