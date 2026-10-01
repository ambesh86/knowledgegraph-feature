import "server-only";
import { query } from "./db";

/**
 * Durable conversation memory. Every chat thread is one `conversations` row
 * (keyed by the same UUID the client sends to the agent as conversation_id),
 * with its turns in `messages`. All reads/writes are scoped to a user_id so a
 * user can only ever touch their own history.
 */

export interface ConversationRow {
  id: string;
  user_id: string;
  title: string | null;
  source: string | null;
  archived: boolean;
  created_at: string;
  updated_at: string;
  last_message_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  source: string | null;
  archived: boolean;
  last_message_at: string;
  message_count: number;
}

export interface MessageRow {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  tool_calls: unknown;
  citations: unknown;
  source: string | null;
  created_at: string;
}

/** Create (or upsert) a conversation shell for `id` owned by `userId`. */
export async function createConversation(
  id: string,
  userId: string,
  source: string | null
): Promise<ConversationRow> {
  const rows = await query<ConversationRow>(
    `INSERT INTO conversations (id, user_id, source)
     VALUES ($1, $2, $3)
     ON CONFLICT (id) DO UPDATE SET source = COALESCE(conversations.source, EXCLUDED.source)
     RETURNING *`,
    [id, userId, source]
  );
  return rows[0];
}

/** List a user's conversations (newest activity first), with message counts. */
export async function listConversations(
  userId: string,
  includeArchived = false
): Promise<ConversationSummary[]> {
  return query<ConversationSummary>(
    `SELECT c.id, c.title, c.source, c.archived, c.last_message_at,
            COALESCE(m.cnt, 0)::int AS message_count
       FROM conversations c
       LEFT JOIN (
         SELECT conversation_id, count(*) AS cnt
           FROM messages GROUP BY conversation_id
       ) m ON m.conversation_id = c.id
      WHERE c.user_id = $1 ${includeArchived ? "" : "AND c.archived = false"}
      ORDER BY c.last_message_at DESC
      LIMIT 200`,
    [userId]
  );
}

/** Fetch one conversation + its ordered messages — only if owned by userId. */
export async function getConversation(
  id: string,
  userId: string
): Promise<{ conversation: ConversationRow; messages: MessageRow[] } | null> {
  const conv = await query<ConversationRow>(
    "SELECT * FROM conversations WHERE id = $1 AND user_id = $2",
    [id, userId]
  );
  if (conv.length === 0) return null;
  const messages = await query<MessageRow>(
    "SELECT * FROM messages WHERE conversation_id = $1 ORDER BY created_at ASC",
    [id]
  );
  return { conversation: conv[0], messages };
}

/** Ownership check helper. */
async function ownsConversation(id: string, userId: string): Promise<boolean> {
  const rows = await query<{ id: string }>(
    "SELECT id FROM conversations WHERE id = $1 AND user_id = $2",
    [id, userId]
  );
  return rows.length > 0;
}

/** Append a message and bump the conversation's activity timestamp. */
export async function appendMessage(
  conversationId: string,
  userId: string,
  msg: {
    role: string;
    content: string;
    toolCalls?: unknown;
    citations?: unknown;
    source?: string | null;
  }
): Promise<MessageRow | null> {
  if (!(await ownsConversation(conversationId, userId))) return null;
  const rows = await query<MessageRow>(
    `INSERT INTO messages (conversation_id, role, content, tool_calls, citations, source)
     VALUES ($1, $2, $3, $4, $5, $6)
     RETURNING *`,
    [
      conversationId,
      msg.role,
      msg.content ?? "",
      msg.toolCalls ? JSON.stringify(msg.toolCalls) : null,
      msg.citations ? JSON.stringify(msg.citations) : null,
      msg.source ?? null,
    ]
  );
  await query(
    "UPDATE conversations SET last_message_at = now(), updated_at = now() WHERE id = $1",
    [conversationId]
  );
  return rows[0];
}

export async function renameConversation(
  id: string,
  userId: string,
  title: string
): Promise<boolean> {
  const rows = await query<{ id: string }>(
    "UPDATE conversations SET title = $3, updated_at = now() WHERE id = $1 AND user_id = $2 RETURNING id",
    [id, userId, title]
  );
  return rows.length > 0;
}

export async function setArchived(
  id: string,
  userId: string,
  archived: boolean
): Promise<boolean> {
  const rows = await query<{ id: string }>(
    "UPDATE conversations SET archived = $3, updated_at = now() WHERE id = $1 AND user_id = $2 RETURNING id",
    [id, userId, archived]
  );
  return rows.length > 0;
}

export async function deleteConversation(id: string, userId: string): Promise<boolean> {
  const rows = await query<{ id: string }>(
    "DELETE FROM conversations WHERE id = $1 AND user_id = $2 RETURNING id",
    [id, userId]
  );
  return rows.length > 0;
}

/** Set the title only if it's still empty (used by auto-title so a user's
 *  manual rename is never clobbered by a late LLM response). */
export async function setTitleIfEmpty(
  id: string,
  userId: string,
  title: string
): Promise<boolean> {
  const rows = await query<{ id: string }>(
    `UPDATE conversations SET title = $3, updated_at = now()
      WHERE id = $1 AND user_id = $2 AND (title IS NULL OR title = '')
      RETURNING id`,
    [id, userId, title]
  );
  return rows.length > 0;
}

/**
 * The user's recent research focus, distilled from their latest conversation
 * titles + first user prompts. Used to bias the live digest toward what they've
 * actually been researching (history analysis).
 */
export async function recentTopics(userId: string, limit = 12): Promise<string[]> {
  const rows = await query<{ text: string }>(
    `SELECT COALESCE(NULLIF(c.title, ''), first_msg.content) AS text
       FROM conversations c
       LEFT JOIN LATERAL (
         SELECT content FROM messages
          WHERE conversation_id = c.id AND role = 'user'
          ORDER BY created_at ASC LIMIT 1
       ) first_msg ON true
      WHERE c.user_id = $1
      ORDER BY c.last_message_at DESC
      LIMIT $2`,
    [userId, limit]
  );
  return rows.map((r) => (r.text ?? "").trim()).filter(Boolean);
}
