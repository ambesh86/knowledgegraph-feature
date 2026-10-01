import { NextRequest, NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { createArtifact } from "@/lib/atlas/artifacts";
import { fetchBriefing, fetchBriefingMarkdown } from "@/lib/atlas/scoutClient";

/**
 * The weekly partnership briefing — UC1's headline deliverable.
 *
 * GET  returns the ranked briefing for the caller's focus area.
 * POST publishes it as an artifact, which gives it a stable shareable URL at
 *      /nextgen/a/<id> plus Markdown / HTML / Word / PDF export. All of that already
 *      exists in lib/atlas/artifacts.ts, so the briefing reuses it rather than
 *      growing a second renderer and a second export path.
 *
 * The scanner has been generating this every Monday and storing it in S3 since the
 * feature shipped. Until this route existed it was written and never read — a
 * briefing nobody could open, which is indistinguishable from not having built it.
 *
 * Area scoping is delegated to the scanner via `ui_area`: the mapping from the UI's
 * coarse profile areas onto the scan taxonomy lives in `areas.UI_AREA_MAP`, and a
 * second copy here would be the one that drifts.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  if (req.nextUrl.searchParams.get("format") === "markdown") {
    const markdown = await fetchBriefingMarkdown(user.focusArea);
    if (markdown === null) {
      return NextResponse.json(
        { error: "Briefing unavailable", degraded: true },
        { status: 502 }
      );
    }
    return new NextResponse(markdown, {
      headers: { "Content-Type": "text/markdown; charset=utf-8" },
    });
  }

  return NextResponse.json(await fetchBriefing(user.focusArea));
}

export async function POST() {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const markdown = await fetchBriefingMarkdown(user.focusArea);
  if (!markdown) {
    return NextResponse.json({ error: "Briefing could not be generated" }, { status: 502 });
  }

  const today = new Date().toISOString().slice(0, 10);
  const artifact = await createArtifact(user.id, {
    title: `Partnership Briefing — ${today}`,
    bodyMd: markdown,
    source: "scout",
  });

  return NextResponse.json({ id: artifact.id, title: artifact.title }, { status: 201 });
}
