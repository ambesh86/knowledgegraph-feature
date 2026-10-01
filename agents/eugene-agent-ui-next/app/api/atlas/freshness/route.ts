import { NextResponse } from "next/server";

/**
 * Data-freshness proxy → core API `/health/data-freshness`.
 *
 * Surfaces today's date alongside the internal snapshot date so the user can see,
 * structurally, what period an answer covers. This is read from the backend
 * rather than parsed out of the assistant's prose — a regex over model output
 * would be exactly the kind of thing that silently drifts.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export interface FreshnessSource {
  source: string;
  ingested_at: string | null;
  record_count?: number | null;
  window?: string | null;
}

export interface Freshness {
  today: string;
  snapshot_date: string | null;
  age_days: number | null;
  stale: boolean | null;
  sources: FreshnessSource[];
  error?: string;
}

export async function GET() {
  const base = process.env.EUGENE_CORE_API_URL ?? "http://eugene_ws:8000";
  try {
    const resp = await fetch(`${base}/health/data-freshness`, {
      cache: "no-store",
      // Short: this decorates the UI, it must never hold up the page.
      signal: AbortSignal.timeout(6000),
    });
    if (!resp.ok) {
      return NextResponse.json(
        { today: new Date().toISOString().slice(0, 10), snapshot_date: null, age_days: null, stale: null, sources: [], error: `core API ${resp.status}` },
        { status: 200 }
      );
    }
    return NextResponse.json(await resp.json());
  } catch (e) {
    // Degrade to "today only" rather than failing — a missing snapshot date is
    // still better than no date at all.
    return NextResponse.json(
      {
        today: new Date().toISOString().slice(0, 10),
        snapshot_date: null,
        age_days: null,
        stale: null,
        sources: [],
        error: e instanceof Error ? e.message : String(e),
      },
      { status: 200 }
    );
  }
}
