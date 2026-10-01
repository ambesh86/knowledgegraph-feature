import { NextRequest, NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { fetchStats } from "@/lib/atlas/scoutClient";

/**
 * Headline counters for the Today view, including "since you last looked".
 *
 * `since` is percent-encoded here rather than concatenated. An ISO timestamp contains
 * `+00:00`, and `+` means "space" in a query string — sending it raw is how the
 * scanner ended up receiving a mangled timestamp and rejecting it.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const params = new URLSearchParams({ ui_area: user.focusArea || "" });
  const since = req.nextUrl.searchParams.get("since");
  if (since) params.set("since", since); // URLSearchParams encodes '+' correctly

  return NextResponse.json(await fetchStats(params));
}
