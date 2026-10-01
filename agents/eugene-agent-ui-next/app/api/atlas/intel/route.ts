import { NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { getArea } from "@/lib/atlas/areas";
import { recentTopics } from "@/lib/atlas/conversations";
import { buildDigest, getCached, setCached } from "@/lib/atlas/intel";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const STOP = new Set([
  "the", "and", "for", "with", "what", "which", "how", "are", "does", "from",
  "that", "this", "about", "into", "your", "you", "new", "any", "can", "give",
  "show", "find", "compare", "between", "them", "their", "have", "has", "why",
  "who", "run", "quick", "readout", "known", "connected", "path", "shortest",
]);

/** Distill recent conversation topics into biasing keywords (history analysis). */
function topicKeywords(topics: string[], max = 6): string[] {
  const freq = new Map<string, number>();
  for (const t of topics) {
    for (const raw of t.toLowerCase().split(/[^a-z0-9-]+/)) {
      const w = raw.trim();
      if (w.length < 4 || STOP.has(w) || /^\d+$/.test(w)) continue;
      freq.set(w, (freq.get(w) ?? 0) + 1);
    }
  }
  return [...freq.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, max)
    .map(([w]) => w);
}

/** GET — the current user's live overnight digest for their focus area,
 *  biased by the topics they've recently been researching. */
export async function GET() {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const area = getArea(user.focusArea);

  let keywords: string[] = [];
  try {
    keywords = topicKeywords(await recentTopics(user.id));
  } catch {
    /* history is optional — fall back to the area query alone */
  }

  const query = [area.query, ...keywords].join(" ").trim();

  // Patents live in a small corpus — a long AND phrase returns nothing. Use the
  // area's curated disease/drug keywords (skip the generic area name) OR'd
  // together, quoting multi-word terms for Lucene.
  const patentQuery = area.keywords
    .slice(1, 5)
    .map((k) => (k.includes(" ") ? `"${k}"` : k))
    .join(" OR ");

  const cacheKey = `${user.id}:${query}`;
  const cached = getCached(cacheKey);
  if (cached) return NextResponse.json({ ...cached, cached: true, keywords });

  const digest = await buildDigest(area.id, query, patentQuery);
  setCached(cacheKey, digest);
  return NextResponse.json({ ...digest, area_label: area.label, keywords });
}
