import { NextRequest, NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { fetchRuns, fetchStatus } from "@/lib/atlas/scoutClient";

/**
 * Scan history and live scanner status, for Settings > Scanning.
 *
 * Both are fetched together because the panel always renders both, and two sequential
 * round trips from the client would make the section flash twice on every open.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const limit = Math.min(Number(req.nextUrl.searchParams.get("limit") ?? 10) || 10, 50);
  const [runs, status] = await Promise.all([fetchRuns(limit), fetchStatus()]);

  return NextResponse.json({
    runs: runs.runs,
    total: runs.total,
    status,
    degraded: runs.degraded || status.degraded,
    reason: runs.reason ?? status.reason,
  });
}
