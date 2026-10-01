import { NextRequest, NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { fetchBrief } from "@/lib/atlas/scoutClient";

/**
 * One stored due-diligence brief.
 *
 * `?date=YYYY-MM-DD` returns the brief as it read that day. Diligence is a decision
 * record: when someone asks in six months why a partnership was progressed, the
 * answer is the brief as it stood then, not as it reads now.
 *
 * 404 and 502 are kept distinct. "No brief yet" has an obvious remedy — run one —
 * while "the scanner is unreachable" does not, and collapsing them sends the user to
 * press a button that cannot work.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  req: NextRequest,
  { params }: { params: { targetId: string } }
) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const date = req.nextUrl.searchParams.get("date") ?? undefined;
  if (date && !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    return NextResponse.json({ error: "Invalid date — use YYYY-MM-DD." }, { status: 400 });
  }

  const brief = await fetchBrief(params.targetId, date);

  if (brief === null) {
    return NextResponse.json(
      { error: "No brief stored for this target yet." },
      { status: 404 }
    );
  }
  if ("degraded" in brief && brief.degraded === true && !("sections" in brief)) {
    return NextResponse.json({ error: brief.reason }, { status: 502 });
  }
  return NextResponse.json(brief);
}
