import { NextResponse } from "next/server";
import { query } from "@/lib/atlas/db";
import {
  verifyPassword,
  signSession,
  setSessionCookie,
  EMAIL_RE,
  type SessionUser,
} from "@/lib/atlas/auth";
import { clientMeta, greeting } from "@/lib/atlas/request";

export const runtime = "nodejs";

interface AuthRow {
  id: string;
  email: string;
  name: string;
  role: string;
  focus_area: string;
  password_hash: string;
}

export async function POST(req: Request) {
  let body: { email?: string; password?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid request body." }, { status: 400 });
  }

  const email = (body.email ?? "").trim().toLowerCase();
  const password = body.password ?? "";
  if (!EMAIL_RE.test(email) || !password) {
    return NextResponse.json({ error: "Enter your email and password." }, { status: 400 });
  }

  const { ip, userAgent } = clientMeta(req);

  try {
    const rows = await query<AuthRow>(
      "SELECT id, email, name, role, focus_area, password_hash FROM users WHERE email = $1",
      [email]
    );
    const user = rows[0];
    const ok = user ? await verifyPassword(password, user.password_hash) : false;

    if (!user || !ok) {
      await query(
        `INSERT INTO login_audit (user_id, email, event, ip, user_agent)
         VALUES ($1, $2, 'login_failed', $3, $4)`,
        [user?.id ?? null, email, ip, userAgent]
      );
      // Constant message — never reveal whether the email exists.
      return NextResponse.json({ error: "Invalid email or password." }, { status: 401 });
    }

    await query("UPDATE users SET last_login_at = now() WHERE id = $1", [user.id]);
    await query(
      `INSERT INTO login_audit (user_id, email, event, ip, user_agent)
       VALUES ($1, $2, 'login', $3, $4)`,
      [user.id, email, ip, userAgent]
    );

    const session: SessionUser = {
      id: user.id,
      email: user.email,
      name: user.name,
      role: user.role,
      focusArea: user.focus_area,
    };
    await setSessionCookie(await signSession(session));

    return NextResponse.json({ user: session, greeting: greeting(session.name) });
  } catch (err) {
    console.error("atlas login failed:", err);
    return NextResponse.json({ error: "Sign-in failed. Please try again." }, { status: 500 });
  }
}
