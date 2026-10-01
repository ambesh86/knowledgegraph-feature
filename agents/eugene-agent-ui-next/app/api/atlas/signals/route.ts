import { NextRequest, NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { fetchSignals } from "@/lib/atlas/scoutClient";

/**
 * Radar signals → eugene_scout `/signals`.
 *
 * Scope is derived from the signed-in user's profile focus area, not from a client
 * parameter. A caller cannot widen their own scope by editing a query string; the
 * scanner maps the profile area onto scan areas via its own taxonomy bridge.
 *
 * Filters are forwarded rather than applied here. The scanner holds the whole corpus
 * in memory and filters it in well under a millisecond, so re-filtering in the BFF
 * would only add a second place for the semantics to drift.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const incoming = req.nextUrl.searchParams;
  const params = new URLSearchParams();

  // Server-controlled: the user's own area scope.
  params.set("ui_area", user.focusArea || "");

  for (const key of ["type", "priority", "company_id", "since", "q", "include_dismissed"]) {
    const value = incoming.get(key);
    if (value) params.set(key, value);
  }
  // Bounded here as well as in the scanner. An unbounded limit from the client would
  // let one request pull the entire corpus through the proxy.
  params.set("limit", String(Math.min(Number(incoming.get("limit") ?? 100) || 100, 300)));
  params.set("offset", String(Math.max(Number(incoming.get("offset") ?? 0) || 0, 0)));

  return NextResponse.json(await fetchSignals(params));
}
