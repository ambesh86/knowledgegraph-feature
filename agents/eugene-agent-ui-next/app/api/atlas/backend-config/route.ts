import { NextRequest, NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { saveBackendConfig, backendStatus } from "@/lib/atlas/backendAuth";

/**
 * Backend connection config: store the Eugene token-signing secret so the UI
 * can self-mint access tokens. Auth-required; the secret is write-only (never
 * returned). GET reports only non-sensitive status.
 */

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  return NextResponse.json(await backendStatus());
}

export async function POST(req: NextRequest) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  let body: { secret?: string; upn?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid body" }, { status: 400 });
  }

  const secret = (body.secret ?? "").trim();
  if (secret.length < 8) {
    return NextResponse.json(
      { error: "secret missing or too short" },
      { status: 400 }
    );
  }

  await saveBackendConfig(secret, body.upn);
  return NextResponse.json({ ok: true, ...(await backendStatus()) });
}
