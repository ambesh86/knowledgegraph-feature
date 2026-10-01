import { NextRequest, NextResponse } from "next/server";

/**
 * Catch-all proxy to the eugene-ade service.
 *
 * A single pass-through instead of one route per endpoint: the ADE API is
 * internal to the Docker network and the browser can't reach it directly, but
 * duplicating each of its ~8 routes here would mean two places to keep in sync
 * every time the service grows an endpoint.
 *
 * Binary responses (evidence PNGs, PDFs) are streamed through untouched — the
 * whole point of the evidence viewer is that the user sees the original bytes.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ADE_BASE = process.env.EUGENE_ADE_URL ?? "http://eugene_ade:8000";

/** Long enough for a cold ingest (fetch + parse + YOLO ≈ 70s observed). */
const INGEST_TIMEOUT_MS = 300_000;
const READ_TIMEOUT_MS = 60_000;

function upstreamUrl(req: NextRequest, path: string[]): string {
  const qs = req.nextUrl.search ?? "";
  return `${ADE_BASE}/ade/${path.join("/")}${qs}`;
}

/** Copy through only the headers a browser actually needs. */
function passThroughHeaders(upstream: Response): Headers {
  const h = new Headers();
  for (const k of ["content-type", "content-disposition", "cache-control"]) {
    const v = upstream.headers.get(k);
    if (v) h.set(k, v);
  }
  return h;
}

async function forward(req: NextRequest, path: string[], init: RequestInit, timeoutMs: number) {
  try {
    const upstream = await fetch(upstreamUrl(req, path), {
      ...init,
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
    });
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: passThroughHeaders(upstream),
    });
  } catch (e) {
    return NextResponse.json(
      { error: `ADE service unreachable: ${e instanceof Error ? e.message : String(e)}` },
      { status: 502 }
    );
  }
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return forward(req, path, { method: "GET" }, READ_TIMEOUT_MS);
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const body = await req.text();
  return forward(
    req,
    path,
    { method: "POST", headers: { "Content-Type": "application/json" }, body },
    INGEST_TIMEOUT_MS
  );
}
