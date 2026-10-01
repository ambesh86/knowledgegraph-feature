/**
 * Client helpers for talking to the Eugene Core API + Agent WS.
 * All calls go through Next.js route handlers so we never expose the
 * JWT to the browser JS for longer than a session.
 */
import { apiPath } from "./basePath";

export async function requestDevToken(): Promise<string> {
  const res = await fetch(apiPath("/api/auth/token"), { method: "POST" });
  if (!res.ok) {
    throw new Error(`token issue failed: ${res.status}`);
  }
  const data = (await res.json()) as { access_token: string };
  return data.access_token;
}

export interface StreamRequestBody {
  prompt: string;
  conversation_id: string;
  include_tools: string[];
}

export async function openStream(
  body: StreamRequestBody,
  signal: AbortSignal
): Promise<Response> {
  const res = await fetch(apiPath("/api/stream"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => "");
    throw new Error(`stream failed: ${res.status} ${text}`);
  }
  return res;
}
