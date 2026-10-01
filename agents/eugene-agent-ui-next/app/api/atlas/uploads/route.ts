import { NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import {
  createUpload,
  extractDocText,
  isAccepted,
  listUploads,
  MAX_UPLOAD_BYTES,
  MAX_CONTEXT_CHARS,
} from "@/lib/atlas/uploads";

export const runtime = "nodejs";

/** GET — list uploads (optionally scoped to ?conversationId=). */
export async function GET(req: Request) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const cid = new URL(req.url).searchParams.get("conversationId");
  try {
    const uploads = await listUploads(user.id, cid);
    return NextResponse.json({ uploads });
  } catch (e) {
    return NextResponse.json({ error: `list failed: ${(e as Error).message}` }, { status: 500 });
  }
}

/** POST — multipart file upload. Stores bytes + extracts text on-box. */
export async function POST(req: Request) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  let form: FormData;
  try {
    form = await req.formData();
  } catch {
    return NextResponse.json({ error: "Invalid multipart body" }, { status: 400 });
  }
  const file = form.get("file");
  if (!(file instanceof File)) {
    return NextResponse.json({ error: "file field required" }, { status: 400 });
  }
  if (!isAccepted(file.type, file.name)) {
    return NextResponse.json({ error: "Unsupported file type" }, { status: 415 });
  }
  const buf = Buffer.from(await file.arrayBuffer());
  if (buf.length === 0) return NextResponse.json({ error: "Empty file" }, { status: 400 });
  if (buf.length > MAX_UPLOAD_BYTES) {
    return NextResponse.json({ error: "File exceeds 20 MB" }, { status: 413 });
  }
  const conversationId = (form.get("conversationId") as string) || null;
  const mime = file.type || "application/octet-stream";

  try {
    const { text, pageCount } = await extractDocText(mime, file.name, buf);
    const up = await createUpload(user.id, {
      conversationId,
      filename: file.name,
      mime,
      bytes: buf,
      extractedText: text,
      pageCount,
    });
    return NextResponse.json(
      {
        id: up.id,
        filename: up.filename,
        mime: up.mime,
        sizeBytes: up.size_bytes,
        pageCount: up.page_count,
        textChars: text.length,
        isImage: mime.startsWith("image/"),
        // capped grounding text the client injects into the next prompt
        contextText: text ? text.slice(0, MAX_CONTEXT_CHARS) : "",
        truncated: text.length > MAX_CONTEXT_CHARS,
      },
      { status: 201 }
    );
  } catch (e) {
    return NextResponse.json({ error: `upload failed: ${(e as Error).message}` }, { status: 500 });
  }
}
