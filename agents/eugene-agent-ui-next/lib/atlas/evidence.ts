import type { ChatMessage, ToolInvocation } from "@/lib/types";

/**
 * Build evidence links from STRUCTURED tool output, not from the answer prose.
 *
 * The first version of this scraped URLs out of the assistant's text with a
 * regex, which only worked when the model happened to emit a recognisable
 * `pubmed.ncbi…/PMC…` link. Answering from fused graph passages it writes
 * "Europe PMC MED/41402784" as plain prose instead — matching nothing — so the
 * evidence affordance silently never appeared.
 *
 * The `search_fused` tool result already carries exactly what the evidence
 * renderer needs (`doc_id`, `chunk_id`, `page`, `paper_title`), so we read that.
 * Structured data the agent actually returned beats pattern-matching what it
 * chose to write.
 */

export interface EvidenceItem {
  docId: string;
  chunkId: string;
  page: number;
  /** Paper title when known, else the passage preview. */
  label: string;
  snippet: string;
  score?: number;
  /** Backend-issued citation label, e.g. "Evidence 3" (mechanism M7). */
  evidenceLabel?: string;
}

/** Walk any nested tool output and collect `paper_chunk` hits. */
function collect(value: unknown, out: EvidenceItem[], seen: Set<string>): void {
  if (Array.isArray(value)) {
    for (const v of value) collect(v, out, seen);
    return;
  }
  if (!value || typeof value !== "object") return;

  const o = value as Record<string, unknown>;
  const docId = typeof o.doc_id === "string" ? o.doc_id : "";
  const chunkId = typeof o.chunk_id === "string" ? o.chunk_id : "";

  if (docId && chunkId) {
    const key = `${docId}:${chunkId}`;
    if (!seen.has(key)) {
      seen.add(key);
      const title = typeof o.paper_title === "string" ? o.paper_title : "";
      const name = typeof o.name === "string" ? o.name : "";
      const text = typeof o.text === "string" ? o.text : name;
      out.push({
        docId,
        chunkId,
        // `page` is 0-based in the pipeline; humans count from 1.
        page: typeof o.page === "number" ? o.page : 0,
        label: title || name || docId,
        snippet: text,
        score: typeof o.rrf_score === "number" ? o.rrf_score : undefined,
        evidenceLabel:
          typeof o.evidence_label === "string" ? o.evidence_label : undefined,
      });
    }
  }

  // Recurse regardless — a hit can be nested inside `results`, and the tool
  // output arrives wrapped in varying envelope shapes across providers.
  for (const v of Object.values(o)) collect(v, out, seen);
}

/** Every citable passage behind an assistant message, best-scored first. */
export function evidenceFromToolCalls(
  toolCalls: ToolInvocation[] | undefined
): EvidenceItem[] {
  if (!toolCalls?.length) return [];
  const out: EvidenceItem[] = [];
  const seen = new Set<string>();
  for (const call of toolCalls) {
    if (call.output === undefined) continue;
    collect(call.output, out, seen);
  }
  out.sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  return out;
}

export function evidenceForMessage(message: ChatMessage): EvidenceItem[] {
  return evidenceFromToolCalls(message.toolCalls);
}

/** Deep-link that opens the viewer with this exact passage preselected. */
export function evidenceLink(item: EvidenceItem): string {
  return `/evidence/${item.docId}?chunk=${encodeURIComponent(item.chunkId)}`;
}

/**
 * Resolve backend-issued `[Evidence N]` labels in the answer text — mechanism M7.
 *
 * The model is forbidden from writing links to internal passages; it may only
 * emit a label. This maps each label back to the evidence item the backend
 * numbered, so the interface produces the link. A model with no mechanism for
 * emitting a URL cannot emit a false one — a structural guarantee rather than a
 * statistical one.
 *
 * Returns the segments of the answer, with label spans marked so the renderer
 * can turn them into clickable pills.
 */
export type AnswerSegment =
  | { kind: "text"; value: string }
  | { kind: "evidence"; label: string; item: EvidenceItem | null };

const EVIDENCE_LABEL = /\[\s*(Evidence\s+\d+)\s*\]/gi;

export function resolveEvidenceLabels(
  content: string,
  items: EvidenceItem[]
): AnswerSegment[] {
  const byLabel = new Map<string, EvidenceItem>();
  items.forEach((it, i) => {
    // Prefer the backend's own label; fall back to positional order so a
    // response that predates labelling still resolves.
    byLabel.set((it.evidenceLabel ?? `Evidence ${i + 1}`).toLowerCase(), it);
  });

  const out: AnswerSegment[] = [];
  let last = 0;
  for (const m of content.matchAll(EVIDENCE_LABEL)) {
    const at = m.index ?? 0;
    if (at > last) out.push({ kind: "text", value: content.slice(last, at) });
    const label = m[1].replace(/\s+/g, " ").trim();
    out.push({ kind: "evidence", label, item: byLabel.get(label.toLowerCase()) ?? null });
    last = at + m[0].length;
  }
  if (last < content.length) out.push({ kind: "text", value: content.slice(last) });
  return out;
}

/** True when the answer uses backend-issued labels at all. */
export function hasEvidenceLabels(content: string): boolean {
  EVIDENCE_LABEL.lastIndex = 0;
  return EVIDENCE_LABEL.test(content);
}
