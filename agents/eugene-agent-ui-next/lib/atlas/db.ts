import "server-only";
import { Pool, type PoolClient } from "pg";

/**
 * Postgres access for Atlas auth (users, login audit).
 *
 * A single pooled connection is shared across the Next.js server runtime.
 * Schema is created lazily on first use (idempotent) so there is no separate
 * migration step to run in dev or on a fresh container.
 */

const CONNECTION_STRING =
  process.env.ATLAS_DATABASE_URL ??
  "postgres://atlas:atlas_local_2026@atlas_postgres:5432/atlas";

declare global {
  // Reuse the pool across hot reloads in dev (avoids exhausting connections).
  // eslint-disable-next-line no-var
  var __atlasPgPool: Pool | undefined;
  // eslint-disable-next-line no-var
  var __atlasSchemaReady: Promise<void> | undefined;
}

export function pool(): Pool {
  if (!global.__atlasPgPool) {
    global.__atlasPgPool = new Pool({
      connectionString: CONNECTION_STRING,
      max: 10,
      idleTimeoutMillis: 30_000,
      connectionTimeoutMillis: 8_000,
    });
  }
  return global.__atlasPgPool;
}

const SCHEMA_SQL = `
CREATE TABLE IF NOT EXISTS users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         TEXT NOT NULL UNIQUE,
  name          TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'analyst',
  focus_area    TEXT NOT NULL DEFAULT 'hematology',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at TIMESTAMPTZ
);

-- Backfill for tables created before focus_area existed.
ALTER TABLE users ADD COLUMN IF NOT EXISTS focus_area TEXT NOT NULL DEFAULT 'hematology';

CREATE TABLE IF NOT EXISTS login_audit (
  id         BIGSERIAL PRIMARY KEY,
  user_id    UUID REFERENCES users(id) ON DELETE SET NULL,
  email      TEXT NOT NULL,
  event      TEXT NOT NULL,            -- 'login' | 'login_failed' | 'register' | 'logout'
  ip         TEXT,
  user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_login_audit_user   ON login_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_login_audit_created ON login_audit(created_at DESC);

-- Conversation memory: one row per chat thread, keyed by the SAME UUID the
-- client sends to the agent as conversation_id (so agent-side session memory
-- and our durable history line up).
CREATE TABLE IF NOT EXISTS conversations (
  id              UUID PRIMARY KEY,
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title           TEXT,
  source          TEXT,                              -- 'eugene' | 'http' | 'pubmed'
  archived        BOOLEAN NOT NULL DEFAULT false,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_message_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role            TEXT NOT NULL,                     -- 'user' | 'assistant' | 'system'
  content         TEXT NOT NULL DEFAULT '',
  tool_calls      JSONB,
  citations       JSONB,
  source          TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user
  ON conversations(user_id, last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation
  ON messages(conversation_id, created_at);

-- Small key/value store for server-side app configuration that must survive
-- container restarts/reboots WITHOUT baking secrets into the image or env.
-- Used to hold the (encrypted) Eugene backend token-signing secret so the UI
-- can self-mint access tokens. Set once via the Settings > Backend Connection
-- page; never committed, never in the image.
CREATE TABLE IF NOT EXISTS app_settings (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Published artifacts: a saved, shareable snapshot of an answer that can be
-- viewed at /nextgen/a/<id> and downloaded as Markdown / HTML / Word / PDF.
-- Mirrors the Claude "Publish" model (owner-created, revocable, link-shareable).
CREATE TABLE IF NOT EXISTS artifacts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  conversation_id UUID,
  title           TEXT NOT NULL DEFAULT 'Untitled',
  body_md         TEXT NOT NULL DEFAULT '',
  source          TEXT,                              -- 'eugene' | 'http' | 'pubmed'
  revoked         BOOLEAN NOT NULL DEFAULT false,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_artifacts_user
  ON artifacts(user_id, created_at DESC);

-- Uploaded documents/images attached to a chat. Bytes live in BYTEA; extracted
-- text (from on-box PDF/DOCX parsing) is prepended to the agent prompt so the
-- answer is grounded in the file. No cloud calls — works in the no-egress VPC.
CREATE TABLE IF NOT EXISTS uploads (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  conversation_id UUID,
  filename        TEXT NOT NULL,
  mime            TEXT NOT NULL DEFAULT 'application/octet-stream',
  size_bytes      INTEGER NOT NULL DEFAULT 0,
  bytes           BYTEA NOT NULL,
  extracted_text  TEXT,
  page_count      INTEGER,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_uploads_user
  ON uploads(user_id, created_at DESC);
`;

/** Ensure the schema exists. Runs at most once per server process. */
export function ensureSchema(): Promise<void> {
  if (!global.__atlasSchemaReady) {
    global.__atlasSchemaReady = pool()
      .query(SCHEMA_SQL)
      .then(() => undefined)
      .catch((err) => {
        // Reset so a later request can retry if the DB was briefly unavailable.
        global.__atlasSchemaReady = undefined;
        throw err;
      });
  }
  return global.__atlasSchemaReady;
}

/** Run a query with the schema guaranteed to exist. */
export async function query<T = Record<string, unknown>>(
  text: string,
  params: ReadonlyArray<unknown> = []
): Promise<T[]> {
  await ensureSchema();
  const res = await pool().query(text, params as unknown[]);
  return res.rows as T[];
}

/** Read a single app_settings value (or null if unset). */
export async function getSetting(key: string): Promise<string | null> {
  const rows = await query<{ value: string }>(
    "SELECT value FROM app_settings WHERE key = $1",
    [key]
  );
  return rows[0]?.value ?? null;
}

/** Upsert an app_settings value. */
export async function setSetting(key: string, value: string): Promise<void> {
  await query(
    `INSERT INTO app_settings (key, value, updated_at)
     VALUES ($1, $2, now())
     ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()`,
    [key, value]
  );
}

/** Run several statements in a single transaction. */
export async function withTransaction<T>(
  fn: (client: PoolClient) => Promise<T>
): Promise<T> {
  await ensureSchema();
  const client = await pool().connect();
  try {
    await client.query("BEGIN");
    const result = await fn(client);
    await client.query("COMMIT");
    return result;
  } catch (err) {
    await client.query("ROLLBACK").catch(() => undefined);
    throw err;
  } finally {
    client.release();
  }
}
