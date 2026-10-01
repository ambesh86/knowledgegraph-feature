import { NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { sendTestNotification } from "@/lib/atlas/scoutClient";

/**
 * "Send test" for the configured notification channel.
 *
 * Exists so an operator can find out whether delivery works without waiting for a
 * scan to produce a high-priority signal. Returns `configured: false` rather than an
 * error when no channel is set up at all — that is a state to display, not a failure.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST() {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  return NextResponse.json(await sendTestNotification());
}
