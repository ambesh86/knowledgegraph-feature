import { NextResponse } from "next/server";
import { currentUser, setSessionCookie, signSession } from "@/lib/atlas/auth";
import { query } from "@/lib/atlas/db";
import { FOCUS_AREAS } from "@/lib/atlas/areas";

export const runtime = "nodejs";

/** PATCH — update the signed-in user's profile (currently: focus area). */
export async function PATCH(req: Request) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  let body: { focusArea?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid body" }, { status: 400 });
  }

  const focusArea = (body.focusArea ?? "").trim().toLowerCase();
  if (!FOCUS_AREAS[focusArea]) {
    return NextResponse.json({ error: "Unknown focus area" }, { status: 400 });
  }

  await query("UPDATE users SET focus_area = $2 WHERE id = $1", [user.id, focusArea]);

  // Re-issue the session cookie so the new focus area is reflected immediately.
  const updated = { ...user, focusArea };
  await setSessionCookie(await signSession(updated));
  return NextResponse.json({ user: updated });
}
