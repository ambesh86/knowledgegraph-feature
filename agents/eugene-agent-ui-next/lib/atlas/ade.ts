import { apiPath } from "@/lib/basePath";

/**
 * Client for the ADE (agentic document extraction) service.
 *
 * The identifier logic lives here rather than in a component because two
 * different call sites need it — the "Show evidence" affordance on a citation
 * and the background auto-ingest of a whole result set — and they must agree on
 * the doc_id, or the pre-warmed document and the one the user clicks won't match.
 */

export interface AdeChunk {
  chunk_id: string;
  chunk_type: string;
  page: number;
  bbox: { left: number; top: number; right: number; bottom: number };
  text: string;
  order: number;
  doc_id?: string;
  source?: string;
  layout_label?: string;
  layout_confidence?: number;
}

export interface AdeManifest {
  doc_id: string;
  status: "ready" | "unavailable" | "failed";
  reason?: string;
  metadata?: {
    title?: string;
    authors?: string;
    year?: string;
    journal?: string;
    doi?: string;
    pmid?: string;
    pmcid?: string;
    is_open_access?: boolean;
    publisher_url?: string;
    europepmc_url?: string;
  };
  page_count?: number;
  chunk_count?: number;
  chunk_types?: Record<string, number>;
  layout_model?: boolean;
  total_s?: number;
  ingested_at?: string;
  cached?: boolean;
}

/** A literature identifier we can hand to the ADE service. */
export interface AdeRef {
  source: "europepmc" | "pubmed" | "pmc" | "url";
  id: string;
}

/**
 * Extract a literature identifier from a citation URL.
 *
 * Returns null for links that aren't papers (clinical trials, patents, generic
 * web pages) — those have no PDF pipeline and must not be offered an evidence
 * button that would only 404.
 */
export function refFromUrl(url: string): AdeRef | null {
  const pmc = url.match(/PMC\d+/i);
  if (pmc) return { source: "pmc", id: pmc[0].toUpperCase() };

  const pubmed = url.match(/pubmed\.ncbi\.nlm\.nih\.gov\/(\d{5,9})/i);
  if (pubmed) return { source: "pubmed", id: pubmed[1] };

  const epmc = url.match(/europepmc\.org\/article\/[A-Z]+\/(\d{5,9})/i);
  if (epmc) return { source: "europepmc", id: epmc[1] };

  const doi = url.match(/doi\.org\/(10\.[^\s?#]+)/i);
  if (doi) return { source: "europepmc", id: doi[1] };

  return null;
}

/** Mirror of the server-side `doc_id_for` — the two MUST stay in agreement. */
export function docIdFor(ref: AdeRef): string {
  return ref.id
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 120);
}

/**
 * Best-effort inverse of `docIdFor`, for when a doc_id arrives with no context
 * (a bookmarked evidence URL, a shared link).
 *
 * It is genuinely lossy: a DOI-derived id like `10_1016_j_xkme_2026_101354`
 * cannot be turned back into `10.1016/j.xkme.2026.101354`, because the slug
 * replaced both `.` and `/` with the same `_`. So the evidence page carries the
 * original identifier in the query string and only falls back to this when it
 * is absent — recognising the two shapes that ARE reversible.
 */
export function refFromDocId(docId: string): AdeRef | null {
  if (/^pmc\d+$/i.test(docId)) return { source: "pmc", id: docId.toUpperCase() };
  if (/^\d{5,9}$/.test(docId)) return { source: "pubmed", id: docId };
  return null;
}

/** Link to the evidence viewer, carrying the identifier that produced it. */
export function evidenceHref(ref: AdeRef): string {
  const qs = new URLSearchParams({ source: ref.source, id: ref.id }).toString();
  return `/evidence/${docIdFor(ref)}?${qs}`;
}

export async function ingest(ref: AdeRef): Promise<AdeManifest> {
  const r = await fetch(apiPath("/api/atlas/ade/ingest"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source: ref.source, id: ref.id }),
  });
  if (!r.ok) throw new Error(`ingest failed: ${r.status}`);
  return r.json();
}

/**
 * Fire-and-forget pre-warm for a whole result set.
 *
 * Deliberately not awaited by callers: extraction takes ~70s per paper, so
 * blocking the chat on it would be unusable. The user clicks minutes later, by
 * which point the document is already extracted.
 */
export async function ingestBatch(refs: AdeRef[]): Promise<void> {
  if (refs.length === 0) return;
  await fetch(apiPath("/api/atlas/ade/ingest/batch"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items: refs.map((r) => ({ source: r.source, id: r.id })) }),
  }).catch(() => {
    /* pre-warming is best-effort — never surface an error for it */
  });
}

export async function getManifest(docId: string): Promise<AdeManifest | null> {
  const r = await fetch(apiPath(`/api/atlas/ade/documents/${docId}`), { cache: "no-store" });
  if (!r.ok) return null;
  return r.json();
}

export async function getChunks(docId: string): Promise<AdeChunk[]> {
  // Ask for the API maximum. The server default is 500, and documents run well
  // past that (a 14-page meta-analysis produced 643) — a truncated list silently
  // breaks deep links to any passage after the cutoff, which is precisely the
  // long-document case evidence links matter most for.
  const r = await fetch(
    apiPath(`/api/atlas/ade/documents/${docId}/chunks?limit=5000`),
    { cache: "no-store" }
  );
  if (!r.ok) return [];
  return (await r.json()).chunks ?? [];
}

export function evidenceImageUrl(docId: string, chunkId: string, dpi = 150): string {
  return apiPath(`/api/atlas/ade/evidence/${docId}/${chunkId}.png?dpi=${dpi}`);
}

export function pdfUrl(docId: string, download = false): string {
  return apiPath(`/api/atlas/ade/documents/${docId}/pdf${download ? "?download=true" : ""}`);
}
