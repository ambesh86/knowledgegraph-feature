import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

/** Proxy: fetch full node details via Core API `/node/details` (POST, body=[node_id]). */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  _req: NextRequest,
  ctx: { params: Promise<{ id: string }> }
) {
  const { id } = await ctx.params;
  const core = process.env.EUGENE_CORE_API_URL ?? "http://eugene_ws:8000";
  const store = await cookies();
  const jwt = store.get("eugene_jwt")?.value;
  if (!jwt) return NextResponse.json({ error: "no auth" }, { status: 401 });

  const res = await fetch(`${core}/node/details`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${jwt}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify([id]),
    cache: "no-store",
  });
  const body = await res.text();
  return new NextResponse(body, {
    status: res.status,
    headers: { "Content-Type": res.headers.get("content-type") ?? "application/json" },
  });
}
