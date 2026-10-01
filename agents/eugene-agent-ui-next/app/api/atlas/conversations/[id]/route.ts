import { NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import {
  deleteConversation,
  getConversation,
  renameConversation,
  setArchived,
} from "@/lib/atlas/conversations";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/** GET — a conversation + its ordered messages (owner only). */
export async function GET(_req: Request, { params }: Ctx) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const { id } = await params;
  const result = await getConversation(id, user.id);
  if (!result) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json(result);
}

/** PATCH — rename ({ title }) or archive ({ archived }). */
export async function PATCH(req: Request, { params }: Ctx) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const { id } = await params;

  let body: { title?: string; archived?: boolean };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid body" }, { status: 400 });
  }

  let ok = false;
  if (typeof body.title === "string") {
    const title = body.title.trim().slice(0, 160);
    if (!title) return NextResponse.json({ error: "Title required" }, { status: 400 });
    ok = await renameConversation(id, user.id, title);
  } else if (typeof body.archived === "boolean") {
    ok = await setArchived(id, user.id, body.archived);
  } else {
    return NextResponse.json({ error: "Nothing to update" }, { status: 400 });
  }

  if (!ok) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json({ ok: true });
}

/** DELETE — remove a conversation (cascades its messages). */
export async function DELETE(_req: Request, { params }: Ctx) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const { id } = await params;
  const ok = await deleteConversation(id, user.id);
  if (!ok) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json({ ok: true });
}
