import type { StreamEvent } from "./types";

/**
 * The Eugene agent WS emits newline-delimited JSON fragments (one per chunk)
 * via StreamingResponse. Each fragment has the shape described in StreamEvent.
 * We try JSON.parse; if that fails, the chunk is a raw text token (legacy path)
 * and we surface it as `{ type: "content", content: chunk }`.
 */
export async function* parseStream(
  response: Response
): AsyncGenerator<StreamEvent, void, void> {
  if (!response.body) return;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Split on newline first; fall back to balanced-brace scan for inline JSON.
      let lines = buffer.split(/\r?\n/);
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        yield parseFragment(trimmed);
      }
    }
    const tail = buffer.trim();
    if (tail) yield parseFragment(tail);
  } finally {
    reader.releaseLock();
  }
}

function parseFragment(fragment: string): StreamEvent {
  // Strip SSE data: prefix if present
  const payload = fragment.startsWith("data:") ? fragment.slice(5).trim() : fragment;
  if (payload.startsWith("{") && payload.endsWith("}")) {
    try {
      const obj = JSON.parse(payload) as StreamEvent;
      if (obj && typeof obj === "object" && "type" in obj) return obj;
    } catch {
      /* fall through to text handling */
    }
  }
  return { type: "content", content: payload };
}
