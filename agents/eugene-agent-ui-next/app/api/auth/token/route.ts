import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { mintEugeneToken } from "@/lib/atlas/backendAuth";

/** Mint a harmless, unsigned dev JWT so the UI is usable for browsing/demos
 *  when the Core API backend is unreachable (local dev without docker, or the
 *  `?demo=` fixture flows). The backend will reject it, so live queries still
 *  require a real backend — but the app no longer hard-errors on boot. */
function devFallbackToken(): { access_token: string; expires_in: number } {
  const expiresIn = 3600;
  const b64 = (o: unknown) =>
    Buffer.from(JSON.stringify(o))
      .toString("base64")
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/, "");
  const now = Math.floor(Date.now() / 1000);
  const token = `${b64({ alg: "none", typ: "JWT" })}.${b64({
    sub: "dev",
    iss: "eugene-dev",
    iat: now,
    exp: now + expiresIn,
  })}.dev`;
  return { access_token: token, expires_in: expiresIn };
}

/** Server-side proxy to Core API /auth/token. Stores JWT in a httpOnly cookie.
 *
 * If EUGENE_STATIC_TOKEN is set in the environment, that value is returned
 * verbatim as the JWT — used when the prod backend rejects locally-minted
 * tokens (RS256-Entra-only) and a real Entra token must be injected by
 * out-of-band auth (e.g. CSL Citrix logon). The token's `exp` claim still
 * governs how long the cookie is valid for.
 */
export async function POST() {
  let data: { access_token: string; expires_in: number };

  // 0. Preferred: self-mint a token using the backend signing secret stored
  //    (encrypted) via Settings > Backend Connection. This is the permanent
  //    path — no expiry pain, no pasted tokens, no external calls.
  const minted = await mintEugeneToken().catch(() => null);
  const staticToken = process.env.EUGENE_STATIC_TOKEN;
  if (minted) {
    data = { access_token: minted.token, expires_in: minted.expiresIn };
  } else if (staticToken && staticToken.length > 20) {
    // Try to parse the JWT exp claim so the cookie matches the token's lifetime.
    let expiresIn = 3600;
    try {
      const payload = JSON.parse(
        Buffer.from(
          staticToken.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"),
          "base64"
        ).toString("utf8")
      ) as { exp?: number };
      if (payload.exp) {
        const remaining = payload.exp - Math.floor(Date.now() / 1000);
        if (remaining > 0) expiresIn = remaining;
      }
    } catch {
      // ignore — use default expiresIn
    }
    data = { access_token: staticToken, expires_in: expiresIn };
  } else {
    const coreApi = process.env.EUGENE_CORE_API_URL ?? "http://eugene_ws:8000";
    const isDev = process.env.NODE_ENV !== "production";
    try {
      const res = await fetch(`${coreApi}/auth/token`, {
        method: "POST",
        cache: "no-store",
      });
      if (!res.ok) {
        // In dev, fall back to a stub token so the UI boots without a backend.
        if (isDev) {
          data = devFallbackToken();
        } else {
          const text = await res.text().catch(() => "");
          return NextResponse.json(
            { error: `core-api token issue failed: ${res.status} ${text}` },
            { status: res.status }
          );
        }
      } else {
        data = (await res.json()) as { access_token: string; expires_in: number };
      }
    } catch (e) {
      // Backend unreachable (e.g. docker-internal hostname from the host).
      if (!isDev) {
        return NextResponse.json(
          { error: `core-api unreachable: ${(e as Error).message}` },
          { status: 502 }
        );
      }
      data = devFallbackToken();
    }
  }
  const store = await cookies();
  // `secure` MUST be opt-in: browsers reject Secure cookies on http://localhost.
  // Only enable when explicitly behind HTTPS (EUGENE_COOKIE_SECURE=true).
  const useSecure = process.env.EUGENE_COOKIE_SECURE === "true";
  store.set({
    name: "eugene_jwt",
    value: data.access_token,
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: data.expires_in,
    secure: useSecure,
  });
  return NextResponse.json({
    access_token: data.access_token,
    expires_in: data.expires_in,
  });
}
