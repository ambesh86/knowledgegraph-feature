import { NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { appendMessage } from "@/lib/atlas/conversations";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/** POST — append one turn (role, content, tool_calls, citations, source). */
export async function POST(req: Request, { params }: Ctx) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const { id } = await params;

  let body: {
    role?: string;
    content?: string;
    toolCalls?: unknown;
    citations?: unknown;
    source?: string | null;
  };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid body" }, { status: 400 });
  }

  const role = body.role ?? "";
  if (!["user", "assistant", "system"].includes(role)) {
    return NextResponse.json({ error: "Invalid role" }, { status: 400 });
  }

  const row = await appendMessage(id, user.id, {
    role,
    content: body.content ?? "",
    toolCalls: body.toolCalls,
    citations: body.citations,
    source: body.source ?? null,
  });
  if (!row) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json({ message: row }, { status: 201 });
}
