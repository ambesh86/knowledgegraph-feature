import "server-only";
import mammoth from "mammoth";
import { extractText as pdfExtractText, getDocumentProxy } from "unpdf";
import { query } from "./db";

/**
 * Document & image uploads.
 *
 * Files are stored in Postgres (BYTEA). For PDFs and Word docs we extract text
 * ON-BOX (unpdf / mammoth — pure JS, no cloud, works in the no-egress VPC) so
 * the content can be fed to the Eugene agent as grounding context. Images are
 * stored + displayed; vision analysis is an egress-gated future tier.
 */

export const MAX_UPLOAD_BYTES = 20 * 1024 * 1024; // 20 MB
/** How much extracted text we inject into a prompt per document. */
export const MAX_CONTEXT_CHARS = 6000;

const ACCEPTED = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
  "text/markdown",
  "text/csv",
  "image/png",
  "image/jpeg",
  "image/webp",
  "image/gif",
];

export function isAccepted(mime: string, filename: string): boolean {
  if (ACCEPTED.includes(mime)) return true;
  return /\.(pdf|docx|txt|md|markdown|csv|png|jpe?g|webp|gif)$/i.test(filename);
}

export interface UploadMeta {
  id: string;
  user_id: string;
  conversation_id: string | null;
  filename: string;
  mime: string;
  size_bytes: number;
  extracted_text: string | null;
  page_count: number | null;
  created_at: string;
}

/** Extract text from a document buffer (offline). Images → empty. */
export async function extractDocText(
  mime: string,
  filename: string,
  buf: Buffer
): Promise<{ text: string; pageCount: number | null }> {
  try {
    if (mime === "application/pdf" || /\.pdf$/i.test(filename)) {
      const pdf = await getDocumentProxy(new Uint8Array(buf));
      const r = await pdfExtractText(pdf, { mergePages: true });
      return { text: String(r.text ?? ""), pageCount: (r.totalPages as number) ?? null };
    }
    if (mime.includes("wordprocessingml") || /\.docx$/i.test(filename)) {
      const r = await mammoth.extractRawText({ buffer: buf });
      return { text: r.value ?? "", pageCount: null };
    }
    if (mime.startsWith("text/") || /\.(txt|md|markdown|csv)$/i.test(filename)) {
      return { text: buf.toString("utf8"), pageCount: null };
    }
  } catch {
    /* corrupt/unsupported → treat as no extractable text */
  }
  return { text: "", pageCount: null };
}

export async function createUpload(
  userId: string,
  input: {
    conversationId?: string | null;
    filename: string;
    mime: string;
    bytes: Buffer;
    extractedText: string;
    pageCount: number | null;
  }
): Promise<UploadMeta> {
  const rows = await query<UploadMeta>(
    `INSERT INTO uploads (user_id, conversation_id, filename, mime, size_bytes, bytes, extracted_text, page_count)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
     RETURNING id, user_id, conversation_id, filename, mime, size_bytes, extracted_text, page_count, created_at`,
    [
      userId,
      input.conversationId ?? null,
      input.filename.slice(0, 300),
      input.mime,
      input.bytes.length,
      input.bytes,
      input.extractedText || null,
      input.pageCount,
    ]
  );
  return rows[0];
}

/** Fetch raw bytes for download/inline (owner only). */
export async function getUploadBytes(
  id: string,
  userId: string
): Promise<{ filename: string; mime: string; bytes: Buffer } | null> {
  const rows = await query<{ filename: string; mime: string; bytes: Buffer }>(
    "SELECT filename, mime, bytes FROM uploads WHERE id = $1 AND user_id = $2",
    [id, userId]
  );
  return rows[0] ?? null;
}

export async function listUploads(userId: string, conversationId?: string | null): Promise<UploadMeta[]> {
  if (conversationId) {
    return query<UploadMeta>(
      `SELECT id, user_id, conversation_id, filename, mime, size_bytes, extracted_text, page_count, created_at
       FROM uploads WHERE user_id = $1 AND conversation_id = $2 ORDER BY created_at DESC`,
      [userId, conversationId]
    );
  }
  return query<UploadMeta>(
    `SELECT id, user_id, conversation_id, filename, mime, size_bytes, extracted_text, page_count, created_at
     FROM uploads WHERE user_id = $1 ORDER BY created_at DESC LIMIT 100`,
    [userId]
  );
}

export async function deleteUpload(id: string, userId: string): Promise<boolean> {
  const rows = await query<{ id: string }>(
    "DELETE FROM uploads WHERE id = $1 AND user_id = $2 RETURNING id",
    [id, userId]
  );
  return rows.length > 0;
}
