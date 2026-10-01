import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

/**
 * SSE proxy to eugene-agent-ws /query/stream.
 * Reads the httpOnly JWT cookie and re-injects it as a Bearer header.
 * Streams the upstream response back unchanged.
 */
export const runtime = "nodejs"; // streaming fetch is nodejs-only in app router
export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const agentApi = process.env.EUGENE_AGENT_API_URL
    ?? "http://eugene_agent_ws:8000/agent/api";

  const store = await cookies();
  const jwt = store.get("eugene_jwt")?.value;
  if (!jwt) {
    return NextResponse.json(
      { error: "no auth — call /api/auth/token first" },
      { status: 401 }
    );
  }

  const body = await req.text();
  const upstream = await fetch(`${agentApi}/query/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${jwt}`,
    },
    body,
    // Important: do NOT buffer — let the stream flow through
    cache: "no-store",
  });

  if (!upstream.ok || !upstream.body) {
    const text = await upstream.text().catch(() => "");
    return NextResponse.json(
      { error: `agent stream failed: ${upstream.status} ${text}` },
      { status: upstream.status }
    );
  }

  return new NextResponse(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
