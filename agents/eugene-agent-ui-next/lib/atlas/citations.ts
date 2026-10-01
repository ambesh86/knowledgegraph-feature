import type { EvidenceItem } from "@/lib/atlas/evidence";

/**
 * Anchoring citations to the sentences they support.
 *
 * The backend numbers every retrieved passage (`evidence_label` = "Evidence 3")
 * and the agent prompt instructs the model to cite by that label. When it complies,
 * anchoring is exact and this module simply resolves the label.
 *
 * It does not always comply. A real answer about emicizumab cited its sources as a
 * prose paragraph at the end — "Sources: Eugene knowledge graph — Emicizumab, …" —
 * with no labels anywhere, which left the reader with nine evidence chips and no way
 * to tell which claim any of them supported.
 *
 * So there is a fallback: match each passage to the sentence it most plausibly
 * supports, by term overlap. That is a weaker claim than an explicit label and it is
 * treated as one — a passage only anchors when the overlap clears a threshold, and
 * anything that does not clear it appears in the reference list without an inline
 * marker rather than being attached to a sentence it may not support. Guessing an
 * anchor is worse than admitting there isn't one: a marker on the wrong sentence
 * tells the reader we verified something we did not.
 */

export interface AnchoredCitation {
  /** 1-based display number, shared by the inline circle and the reference card. */
  n: number;
  item: EvidenceItem;
  /** How the anchor was established. Surfaced in the UI as a tooltip. */
  origin: "label" | "matched" | "unanchored";
}

export type Segment =
  | { kind: "text"; value: string }
  | { kind: "cite"; citations: AnchoredCitation[] };

/** Matches `[Evidence 3]`, `[evidence 3]`, `[Evidence 3, Evidence 5]`. */
const LABEL_RE = /\[\s*Evidence\s+\d+(?:\s*(?:,|and)\s*(?:Evidence\s+)?\d+)*\s*\]/gi;
const LABEL_NUM_RE = /\d+/g;

/**
 * Words that carry no discriminating power when matching a passage to a sentence.
 * Without this, "the of and in" dominates every overlap score and the highest-scoring
 * sentence is simply the longest one.
 */
const STOP = new Set(
  ("a an the and or but if then than that this these those of in on at to for with by from as is are was " +
   "were be been being it its it's we our you your they their he she his her not no also can may might " +
   "will would should could have has had do does did which who whom what when where how why into over " +
   "under about between both each more most other some such only own same so too very just").split(" ")
);

function terms(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, " ")
      .split(/\s+/)
      .filter((w) => w.length > 2 && !STOP.has(w))
  );
}

/**
 * Split prose into sentences, keeping the delimiter so the text can be rebuilt
 * exactly. Abbreviations common in this corpus ("et al.", "N Engl J Med.", "vs.",
 * "Fig.") would otherwise split mid-citation and strand a marker in the middle of a
 * reference.
 */
const ABBREV = /(?:et al|vs|cf|Fig|Ref|No|Dr|Prof|Inc|Ltd|approx|e\.g|i\.e|Med|Engl|J)\.$/i;

export function splitSentences(text: string): string[] {
  const parts: string[] = [];
  let buf = "";
  for (const chunk of text.split(/(?<=[.!?])\s+/)) {
    buf = buf ? `${buf} ${chunk}` : chunk;
    if (ABBREV.test(buf.trim())) continue; // keep accumulating past the abbreviation
    parts.push(buf);
    buf = "";
  }
  if (buf) parts.push(buf);
  return parts;
}

/** Jaccard-style overlap, normalised by the sentence so long sentences don't win. */
function overlap(sentenceTerms: Set<string>, snippetTerms: Set<string>): number {
  if (!sentenceTerms.size || !snippetTerms.size) return 0;
  let shared = 0;
  for (const t of sentenceTerms) if (snippetTerms.has(t)) shared++;
  return shared / sentenceTerms.size;
}

/**
 * Minimum overlap for an inferred anchor. Calibrated on real answers: at 0.20 a
 * generic sentence like "Key points:" attracted a citation; at 0.45 nothing
 * anchored at all. 0.32 attaches passages to sentences that genuinely restate them
 * and leaves throat-clearing alone.
 */
const MATCH_THRESHOLD = 0.32;

/** Number the evidence in the order the backend returned it, which is rank order. */
export function numberCitations(items: EvidenceItem[]): AnchoredCitation[] {
  return items.map((item, i) => ({ n: i + 1, item, origin: "unanchored" as const }));
}

/**
 * Build the renderable segments for an answer.
 *
 * Two modes, and which one ran is visible to the reader through the marker tooltip
 * rather than hidden: explicit labels are a claim the model made, inferred anchors
 * are a claim this function made.
 */
export function buildSegments(
  content: string,
  items: EvidenceItem[]
): { segments: Segment[]; citations: AnchoredCitation[] } {
  const citations = numberCitations(items);
  if (!citations.length) return { segments: [{ kind: "text", value: content }], citations };

  const byNumber = new Map<number, AnchoredCitation>();
  citations.forEach((c) => {
    // Prefer the backend's own number so "[Evidence 3]" resolves to the passage the
    // backend called 3, even if dedup reordered our list.
    const declared = Number(c.item.evidenceLabel?.match(/\d+/)?.[0]);
    byNumber.set(Number.isFinite(declared) ? declared : c.n, c);
  });

  if (LABEL_RE.test(content)) {
    LABEL_RE.lastIndex = 0;
    return { segments: fromLabels(content, byNumber), citations };
  }
  return { segments: fromMatching(content, citations), citations };
}

/** Exact mode: the model cited by label. */
function fromLabels(content: string, byNumber: Map<number, AnchoredCitation>): Segment[] {
  const out: Segment[] = [];
  let last = 0;
  LABEL_RE.lastIndex = 0;
  for (const m of content.matchAll(LABEL_RE)) {
    const at = m.index ?? 0;
    if (at > last) out.push({ kind: "text", value: content.slice(last, at) });
    const nums = (m[0].match(LABEL_NUM_RE) ?? []).map(Number);
    const cites = nums
      .map((n) => byNumber.get(n))
      .filter((c): c is AnchoredCitation => Boolean(c))
      .map((c) => ({ ...c, origin: "label" as const }));
    if (cites.length) out.push({ kind: "cite", citations: cites });
    last = at + m[0].length;
  }
  if (last < content.length) out.push({ kind: "text", value: content.slice(last) });
  return out;
}

/** Fallback mode: infer the anchor from content overlap. */
function fromMatching(content: string, citations: AnchoredCitation[]): Segment[] {
  const sentences = splitSentences(content);
  const sentenceTerms = sentences.map((s) => terms(s));

  // For each passage, the single best sentence — or none.
  const bestFor = new Map<number, { sentence: number; score: number }>();
  citations.forEach((c) => {
    const snippet = terms(c.item.snippet || c.item.label);
    let best = { sentence: -1, score: 0 };
    sentenceTerms.forEach((st, i) => {
      const score = overlap(st, snippet);
      if (score > best.score) best = { sentence: i, score };
    });
    if (best.sentence >= 0 && best.score >= MATCH_THRESHOLD) {
      bestFor.set(c.n, best);
    }
  });

  // Invert: sentence -> the citations that anchor there, in citation order.
  const perSentence = new Map<number, AnchoredCitation[]>();
  citations.forEach((c) => {
    const hit = bestFor.get(c.n);
    if (!hit) return;
    const list = perSentence.get(hit.sentence) ?? [];
    list.push({ ...c, origin: "matched" });
    perSentence.set(hit.sentence, list);
  });

  const out: Segment[] = [];
  sentences.forEach((sentence, i) => {
    out.push({ kind: "text", value: sentence });
    const cites = perSentence.get(i);
    if (cites?.length) out.push({ kind: "cite", citations: cites });
    if (i < sentences.length - 1) out.push({ kind: "text", value: " " });
  });
  return out;
}

/**
 * One colour for every citation, and it is the highlight green.
 *
 * An earlier version cycled six hues so adjacent markers were easy to tell apart.
 * That traded away the more valuable signal: the green a marker is drawn in is the
 * same green PyMuPDF paints onto the page region in `render.py`
 * (stroke `(0.38,0.67,0.02)`, fill `(0.66,0.85,0.29)`). Clicking a green circle and
 * landing on a green-highlighted paragraph reads as one continuous object. Six
 * arbitrary hues made the marker and its proof look unrelated.
 *
 * Disambiguation is carried by the number, which is exact, rather than by hue,
 * which never was.
 */
export const CITATION_GREEN = {
  bg: "rgba(132,204,22,0.18)",
  fg: "#4d7c0f",
  border: "rgba(97,171,5,0.55)",
  /** The fill PyMuPDF uses for the page highlight — for surfaces, not text. */
  highlight: "#a8d94a",
} as const;

export function citationColor(_n: number) {
  return CITATION_GREEN;
}
