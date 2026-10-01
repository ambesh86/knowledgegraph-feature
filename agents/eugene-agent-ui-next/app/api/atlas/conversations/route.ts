import { NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { createConversation, listConversations } from "@/lib/atlas/conversations";

export const runtime = "nodejs";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** GET — list the current user's conversations (newest activity first). */
export async function GET() {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  try {
    const conversations = await listConversations(user.id);
    return NextResponse.json({ conversations });
  } catch (e) {
    return NextResponse.json(
      { error: `list failed: ${(e as Error).message}` },
      { status: 500 }
    );
  }
}

/** POST — create a conversation shell for the client-provided UUID. */
export async function POST(req: Request) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  let body: { id?: string; source?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid body" }, { status: 400 });
  }
  const id = (body.id ?? "").trim();
  if (!UUID_RE.test(id)) {
    return NextResponse.json({ error: "id must be a UUID" }, { status: 400 });
  }
  try {
    const conversation = await createConversation(id, user.id, body.source ?? null);
    return NextResponse.json({ conversation }, { status: 201 });
  } catch (e) {
    return NextResponse.json(
      { error: `create failed: ${(e as Error).message}` },
      { status: 500 }
    );
  }
}
