import { NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { fetchFreshness } from "@/lib/atlas/scoutClient";

/**
 * Data currency for the global "as of" indicator.
 *
 * Scoped to the caller's focus area, because staleness is per-area: literature in a
 * busy franchise moves weekly while a narrow one can genuinely have nothing new for a
 * month, and a global average would hide both.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  return NextResponse.json(await fetchFreshness(user.focusArea));
}
