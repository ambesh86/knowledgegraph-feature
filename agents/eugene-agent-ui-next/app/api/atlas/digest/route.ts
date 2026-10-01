import { NextRequest, NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { getArea } from "@/lib/atlas/areas";

/**
 * The researcher's digest — what actually changed in their areas.
 *
 * Backed primarily by our OWN graph, where every paper carries `indexed_at` from
 * the 01:00 ingestion run. That is the only signal in the system that provably
 * knows what is new, and it is already scoped to the declared research areas.
 *
 * The previous panel asked live external APIs for "latest" and displayed whatever
 * came back. It could not work: Europe PMC does not reliably honour
 * `sort=P_PDATE_D desc` on these queries (measured order was 2026-06-11,
 * 2026-07-01, 2026-03-03 — not sorted), and there was no date FILTER at all, so
 * the patent column showed 2002–2010 grants under a heading saying "overnight".
 *
 * Scoping comes from the user's profile focus area. Keywords are passed to the
 * backend rather than defined there, so the taxonomy has one home
 * (`lib/atlas/areas.ts`) instead of drifting across three.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const CORE_API = process.env.EUGENE_CORE_API_URL ?? "http://eugene_ws:8000";

export interface DigestPaper {
  doc_id: string;
  title: string;
  journal?: string;
  year?: string;
  authors?: string;
  url?: string;
  pmid?: string;
  pmcid?: string;
  indexed_at: string;
  pages?: number;
  matched_keywords: string[];
  has_evidence: boolean;
}

export interface DigestTrial {
  nct_id: string;
  title: string;
  status?: string;
  phase?: string;
  sponsor?: string;
  url?: string;
  start_date?: string;
}

export interface DigestResponse {
  since: string;
  generated_at: string;
  area: string;
  area_label: string;
  keywords: string[];
  papers: DigestPaper[];
  papers_total: number;
  trials: DigestTrial[];
  trials_total: number;
  corpus: {
    papers?: number;
    passages?: number;
    trials?: number;
    last_ingest_at?: string;
  };
  error?: string;
}

export async function GET(req: NextRequest) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const area = getArea(user.focusArea);
  // Default window is 24h — "since you last looked" for a daily-standup pattern.
  // The caller can widen it, which matters after a weekend.
  const hours = Number(req.nextUrl.searchParams.get("hours") ?? 24);
  const since = new Date(Date.now() - Math.max(1, hours) * 3600_000).toISOString();

  try {
    const r = await fetch(`${CORE_API}/research/digest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keywords: area.keywords, since, limit: 8 }),
      cache: "no-store",
      signal: AbortSignal.timeout(20_000),
    });
    if (!r.ok) throw new Error(`core API ${r.status}`);
    const data = await r.json();
    return NextResponse.json({
      ...data,
      area: area.id,
      area_label: area.label,
    } satisfies DigestResponse);
  } catch (e) {
    // Degrade to an explicit empty digest rather than an error card. "Nothing
    // new" is a legitimate answer for a narrow area on a quiet night, and the
    // UI should render that state either way.
    return NextResponse.json({
      since,
      generated_at: new Date().toISOString(),
      area: area.id,
      area_label: area.label,
      keywords: area.keywords,
      papers: [],
      papers_total: 0,
      trials: [],
      trials_total: 0,
      corpus: {},
      error: e instanceof Error ? e.message : String(e),
    } satisfies DigestResponse);
  }
}
