import { NextResponse } from "next/server";
import { query } from "@/lib/atlas/db";
import {
  hashPassword,
  signSession,
  setSessionCookie,
  validateCredentials,
  type SessionUser,
} from "@/lib/atlas/auth";
import { clientMeta, greeting } from "@/lib/atlas/request";

export const runtime = "nodejs";

interface UserRow {
  id: string;
  email: string;
  name: string;
  role: string;
  focus_area: string;
}

export async function POST(req: Request) {
  let body: { email?: string; name?: string; password?: string; focusArea?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid request body." }, { status: 400 });
  }

  const email = (body.email ?? "").trim().toLowerCase();
  const name = (body.name ?? "").trim();
  const password = body.password ?? "";
  const focusArea = (body.focusArea ?? "hematology").trim().toLowerCase();

  const credErr = validateCredentials(email, password);
  if (credErr) return NextResponse.json({ error: credErr }, { status: 400 });
  if (name.length < 2)
    return NextResponse.json({ error: "Enter your full name." }, { status: 400 });

  const { ip, userAgent } = clientMeta(req);

  try {
    const existing = await query<UserRow>("SELECT id FROM users WHERE email = $1", [email]);
    if (existing.length > 0) {
      return NextResponse.json(
        { error: "An account with this email already exists." },
        { status: 409 }
      );
    }

    const passwordHash = await hashPassword(password);
    const rows = await query<UserRow>(
      `INSERT INTO users (email, name, password_hash, focus_area, last_login_at)
       VALUES ($1, $2, $3, $4, now())
       RETURNING id, email, name, role, focus_area`,
      [email, name, passwordHash, focusArea]
    );
    const user = rows[0];

    await query(
      `INSERT INTO login_audit (user_id, email, event, ip, user_agent)
       VALUES ($1, $2, 'register', $3, $4)`,
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

    return NextResponse.json({ user: session, greeting: greeting(user.name) });
  } catch (err) {
    console.error("atlas register failed:", err);
    return NextResponse.json(
      { error: "Could not create account. Please try again." },
      { status: 500 }
    );
  }
}
