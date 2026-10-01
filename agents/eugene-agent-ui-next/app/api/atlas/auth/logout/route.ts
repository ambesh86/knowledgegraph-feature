import { NextResponse } from "next/server";
import { query } from "@/lib/atlas/db";
import { currentUser, clearSessionCookie } from "@/lib/atlas/auth";
import { clientMeta } from "@/lib/atlas/request";

export const runtime = "nodejs";

export async function POST(req: Request) {
  const user = await currentUser();
  if (user) {
    const { ip, userAgent } = clientMeta(req);
    await query(
      `INSERT INTO login_audit (user_id, email, event, ip, user_agent)
       VALUES ($1, $2, 'logout', $3, $4)`,
      [user.id, user.email, ip, userAgent]
    ).catch((err) => console.error("logout audit failed:", err));
  }
  await clearSessionCookie();
  return NextResponse.json({ ok: true });
}
