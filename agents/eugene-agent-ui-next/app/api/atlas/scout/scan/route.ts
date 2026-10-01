import { NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { triggerScan } from "@/lib/atlas/scoutClient";

/**
 * Manual rescan — the Radar's "Rescan" button.
 *
 * Synchronous, because the caller needs to know whether it worked. A scan is seconds
 * (measured ~5s for one area across four sources), and the scanner enforces
 * single-flight itself: a second trigger while one is running returns `skipped`
 * rather than queueing a duplicate crawl of rate-limited public APIs.
 *
 * No area parameter is accepted. The scanner decides scope from its own enabled-area
 * config; letting a client name areas would make it possible to hammer one source by
 * looping requests over a list.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
// A scan can take longer than the platform default for a route handler.
export const maxDuration = 300;

export async function POST() {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const result = await triggerScan();
  if (result.degraded) {
    return NextResponse.json(
      { error: "Scan could not be started", reason: result.reason },
      { status: 502 }
    );
  }
  return NextResponse.json(result);
}
