import { NextRequest, NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { fetchSignal, patchSignal } from "@/lib/atlas/scoutClient";

/**
 * A single signal, and the dismiss action.
 *
 * The dismissal is written through to the scanner's curated tier rather than held in
 * client state, because the next scheduled scan reads it forward. An in-memory
 * dismissal would silently reappear at 02:00, which reads as the product ignoring the
 * analyst's decision.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(_req: NextRequest, { params }: { params: { id: string } }) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const signal = await fetchSignal(params.id);
  if (!signal || signal.degraded) {
    return NextResponse.json(
      { error: "Signal not available", reason: signal?.reason ?? "not found" },
      { status: 404 }
    );
  }
  return NextResponse.json(signal);
}

export async function PATCH(req: NextRequest, { params }: { params: { id: string } }) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  let dismissed: boolean;
  try {
    const body = await req.json();
    if (typeof body?.dismissed !== "boolean") {
      return NextResponse.json({ error: "dismissed must be a boolean" }, { status: 400 });
    }
    dismissed = body.dismissed;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const result = await patchSignal(params.id, dismissed);
  if (result.degraded) {
    return NextResponse.json(
      { error: "Could not update signal", reason: result.reason },
      { status: 502 }
    );
  }
  return NextResponse.json(result);
}
