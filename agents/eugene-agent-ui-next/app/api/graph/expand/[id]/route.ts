import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

/** Proxy: expand neighbors of a node via Core API `/graph/relationship/start/{id}`. */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  req: NextRequest,
  ctx: { params: Promise<{ id: string }> }
) {
  const { id } = await ctx.params;
  const core = process.env.EUGENE_CORE_API_URL ?? "http://eugene_ws:8000";
  const n_hop = req.nextUrl.searchParams.get("n_hop") ?? "1";

  const store = await cookies();
  const jwt = store.get("eugene_jwt")?.value;
  if (!jwt) return NextResponse.json({ error: "no auth" }, { status: 401 });

  const res = await fetch(
    `${core}/graph/relationship/start/${encodeURIComponent(id)}?n_hop=${n_hop}`,
    { headers: { Authorization: `Bearer ${jwt}` }, cache: "no-store" }
  );
  const body = await res.text();
  return new NextResponse(body, {
    status: res.status,
    headers: { "Content-Type": res.headers.get("content-type") ?? "application/json" },
  });
}
