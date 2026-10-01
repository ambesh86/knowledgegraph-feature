import { NextResponse } from "next/server";

/**
 * Pre-flight readiness probe. The UI pings this before sending a prompt so
 * we refuse fast if the agent is genuinely down. We try multiple paths
 * because production ALBs may not expose /health/ready (only /query/stream),
 * and we treat ANY non-5xx response as "agent is reachable" — a 404 means
 * the endpoint is missing but the listener is alive, which is still "ready
 * enough" to attempt a real query and surface the real error if it fails.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const agentApi =
    process.env.EUGENE_AGENT_API_URL ?? "http://eugene_agent_ws:8000/agent/api";

  // Probe in order of specificity. First non-5xx wins.
  const paths = ["/health/ready", "/health", ""];
  let lastStatus: number | string = "no-response";
  let lastError: string | undefined;

  for (const path of paths) {
    try {
      const res = await fetch(`${agentApi}${path}`, {
        cache: "no-store",
        signal: AbortSignal.timeout(4000),
      });
      lastStatus = res.status;
      if (res.status < 500) {
        return NextResponse.json(
          {
            status: "OK",
            service: "eugene-agent-ws",
            probed_path: path || "/",
            probed_status: res.status,
          },
          { status: 200 }
        );
      }
    } catch (e) {
      lastError = (e as Error).message;
    }
  }

  return NextResponse.json(
    { status: "DOWN", probed_status: lastStatus, error: lastError },
    { status: 503 }
  );
}
