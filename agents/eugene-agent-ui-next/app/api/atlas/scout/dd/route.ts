import { NextRequest, NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { fetchBriefs, generateBrief } from "@/lib/atlas/scoutClient";

/**
 * Use Case 2 — accelerated scientific due diligence.
 *
 * GET  lists every target with a stored brief.
 * POST runs diligence on one target, or returns the stored brief unless `force`.
 *
 * Unlike Radar, scope is NOT derived from the user's focus area. Diligence is asked
 * about a named company by someone who already decided it is worth asking about, and
 * silently filtering that by a profile setting would produce an empty brief for a
 * real target — the single most misleading thing this workflow can do.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** A completed run is ~30s; the client is told to wait, so the route must too. */
export const maxDuration = 300;

export async function GET() {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  return NextResponse.json(await fetchBriefs());
}

export async function POST(req: NextRequest) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json().catch(() => null);
  const company = typeof body?.company === "string" ? body.company.trim() : "";

  // Validated here as well as in the scanner. The scanner's 422 is a pydantic dump
  // that means nothing to someone who just typed one letter into a search box.
  if (company.length < 2) {
    return NextResponse.json(
      { error: "Enter a company name — at least two characters." },
      { status: 400 }
    );
  }
  if (company.length > 200) {
    return NextResponse.json({ error: "Company name is too long." }, { status: 400 });
  }

  const asset = typeof body?.asset === "string" ? body.asset.trim().slice(0, 200) : null;
  const result = await generateBrief({ company, asset, force: body?.force === true });

  if (!result.ok) {
    // The scanner's own message is preserved — on a serve-only deployment its 409
    // ("no route to the public sources") is the entire diagnosis.
    return NextResponse.json({ error: result.reason }, { status: result.status });
  }
  return NextResponse.json(result.brief);
}
