import { NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { createArtifact, listArtifacts } from "@/lib/atlas/artifacts";

export const runtime = "nodejs";

/** GET — list the current user's published artifacts. */
export async function GET() {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  try {
    const artifacts = await listArtifacts(user.id);
    return NextResponse.json({ artifacts });
  } catch (e) {
    return NextResponse.json({ error: `list failed: ${(e as Error).message}` }, { status: 500 });
  }
}

/** POST — publish an answer as a shareable artifact. Returns { id }. */
export async function POST(req: Request) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  let body: { title?: string; bodyMd?: string; source?: string; conversationId?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid body" }, { status: 400 });
  }
  if (!body.bodyMd || !body.bodyMd.trim()) {
    return NextResponse.json({ error: "bodyMd required" }, { status: 400 });
  }
  try {
    const artifact = await createArtifact(user.id, {
      title: body.title ?? "Untitled",
      bodyMd: body.bodyMd,
      source: body.source ?? null,
      conversationId: body.conversationId ?? null,
    });
    return NextResponse.json({ id: artifact.id }, { status: 201 });
  } catch (e) {
    return NextResponse.json({ error: `publish failed: ${(e as Error).message}` }, { status: 500 });
  }
}
