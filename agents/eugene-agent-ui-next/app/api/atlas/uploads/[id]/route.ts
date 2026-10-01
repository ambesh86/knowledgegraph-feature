import { NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { getUploadBytes, deleteUpload } from "@/lib/atlas/uploads";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/** GET — download/inline the uploaded file (owner only). */
export async function GET(req: Request, { params }: Ctx) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const { id } = await params;
  const f = await getUploadBytes(id, user.id);
  if (!f) return NextResponse.json({ error: "Not found" }, { status: 404 });

  const inline =
    new URL(req.url).searchParams.get("inline") === "1" || f.mime.startsWith("image/");
  return new NextResponse(new Uint8Array(f.bytes), {
    headers: {
      "Content-Type": f.mime || "application/octet-stream",
      "Content-Disposition": `${inline ? "inline" : "attachment"}; filename="${f.filename.replace(/"/g, "")}"`,
    },
  });
}

/** DELETE — remove an upload (owner only). */
export async function DELETE(_req: Request, { params }: Ctx) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const { id } = await params;
  const ok = await deleteUpload(id, user.id);
  return NextResponse.json({ ok }, { status: ok ? 200 : 404 });
}
