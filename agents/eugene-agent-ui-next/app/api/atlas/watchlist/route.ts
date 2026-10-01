import { NextRequest, NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { fetchWatchlist } from "@/lib/atlas/scoutClient";

/**
 * Watchlist → eugene_scout `/companies`.
 *
 * Company scores are derived from the signals attributed to them, so this endpoint
 * has no independent source of truth to drift from the Radar. Ask why a company ranks
 * where it does and the answer is a list of signals the analyst can click.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const params = new URLSearchParams({ ui_area: user.focusArea || "" });
  const search = req.nextUrl.searchParams.get("q");
  if (search) params.set("q", search);
  params.set("limit", String(Math.min(Number(req.nextUrl.searchParams.get("limit") ?? 100) || 100, 300)));

  return NextResponse.json(await fetchWatchlist(params));
}
