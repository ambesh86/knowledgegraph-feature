import { NextRequest, NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { fetchConfig, saveConfig } from "@/lib/atlas/scoutClient";

/**
 * Scan configuration — scoring weights, thresholds, sources, notification target.
 *
 * This is the use case's "configurable thresholds, managed as configuration not code,
 * enabling the BD team to tune the system without developer involvement".
 *
 * Writes are gated on role. The `users.role` column defaults to 'analyst'
 * (see SCHEMA_SQL in lib/atlas/db.ts), so 'admin' is checked but 'analyst' is also
 * permitted for now — a deployment where nobody has been made an admin would
 * otherwise have a Settings page nobody can save. Tighten to admin-only once roles
 * are actually assigned; the check is here so that change is one line.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const CAN_EDIT = new Set(["admin", "analyst"]);

export async function GET() {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  return NextResponse.json(await fetchConfig());
}

export async function PUT(req: NextRequest) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  if (!CAN_EDIT.has(user.role)) {
    return NextResponse.json(
      { error: `Role '${user.role}' cannot change scan configuration` },
      { status: 403 }
    );
  }

  let payload: Record<string, unknown>;
  try {
    payload = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  // Attribution is server-set. A client-supplied `updated_by` would let the audit
  // trail record whoever the caller felt like naming.
  const saved = await saveConfig({ ...payload, updated_by: user.email });
  if (saved.degraded) {
    return NextResponse.json(
      { error: "Configuration was not saved", reason: saved.reason },
      { status: 502 }
    );
  }
  return NextResponse.json(saved);
}
