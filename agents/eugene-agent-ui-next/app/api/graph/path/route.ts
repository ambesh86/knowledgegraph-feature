import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

/** Proxy: find path between two nodes via Core API `/graph/path/start/{a}/end/{b}`. */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const core = process.env.EUGENE_CORE_API_URL ?? "http://eugene_ws:8000";
  const source = req.nextUrl.searchParams.get("source");
  const sink = req.nextUrl.searchParams.get("sink");
  const nHop = req.nextUrl.searchParams.get("n_hop") ?? "4";
  if (!source || !sink) {
    return NextResponse.json(
      { error: "source and sink required" },
      { status: 400 }
    );
  }

  const store = await cookies();
  const jwt = store.get("eugene_jwt")?.value;
  if (!jwt) return NextResponse.json({ error: "no auth" }, { status: 401 });

  const res = await fetch(
    `${core}/graph/path/start/${encodeURIComponent(source)}/end/${encodeURIComponent(sink)}?n_hop=${nHop}`,
    { headers: { Authorization: `Bearer ${jwt}` }, cache: "no-store" }
  );
  const body = await res.text();
  return new NextResponse(body, {
    status: res.status,
    headers: { "Content-Type": res.headers.get("content-type") ?? "application/json" },
  });
}
