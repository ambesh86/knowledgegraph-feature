import { NextResponse } from "next/server";
import { getArtifact, toHtml, toDocxBuffer } from "@/lib/atlas/artifacts";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/** GET ?fmt=md|html|docx — download a published artifact in the given format. */
export async function GET(req: Request, { params }: Ctx) {
  const { id } = await params;
  const a = await getArtifact(id);
  if (!a) return NextResponse.json({ error: "Not found" }, { status: 404 });

  const fmt = new URL(req.url).searchParams.get("fmt") ?? "md";
  const safe = (a.title.replace(/[^\w.-]+/g, "_").slice(0, 60) || "artifact");

  if (fmt === "html") {
    return new NextResponse(toHtml(a), {
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        "Content-Disposition": `attachment; filename="${safe}.html"`,
      },
    });
  }
  if (fmt === "docx") {
    const buf = await toDocxBuffer(a);
    return new NextResponse(new Uint8Array(buf), {
      headers: {
        "Content-Type":
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "Content-Disposition": `attachment; filename="${safe}.docx"`,
      },
    });
  }
  // default: markdown
  return new NextResponse(a.body_md, {
    headers: {
      "Content-Type": "text/markdown; charset=utf-8",
      "Content-Disposition": `attachment; filename="${safe}.md"`,
    },
  });
}
