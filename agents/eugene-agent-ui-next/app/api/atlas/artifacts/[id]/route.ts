import { NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { getArtifact, revokeArtifact } from "@/lib/atlas/artifacts";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/** GET — public fetch of a published artifact (anyone with the link). */
export async function GET(_req: Request, { params }: Ctx) {
  const { id } = await params;
  const a = await getArtifact(id);
  if (!a) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json({
    id: a.id,
    title: a.title,
    body_md: a.body_md,
    source: a.source,
    created_at: a.created_at,
  });
}

/** DELETE — revoke an artifact (owner only). */
export async function DELETE(_req: Request, { params }: Ctx) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const { id } = await params;
  const ok = await revokeArtifact(id, user.id);
  return NextResponse.json({ ok }, { status: ok ? 200 : 404 });
}
