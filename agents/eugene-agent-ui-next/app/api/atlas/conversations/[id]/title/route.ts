import { NextResponse } from "next/server";
import { currentUser } from "@/lib/atlas/auth";
import { getConversation, setTitleIfEmpty } from "@/lib/atlas/conversations";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

/** Cheap deterministic fallback: first user line, cleaned + capped. */
function heuristicTitle(text: string): string {
  const clean = text.replace(/\s+/g, " ").trim().replace(/^["'`]+|["'`]+$/g, "");
  const words = clean.split(" ").slice(0, 8).join(" ");
  const t = words.length > 60 ? words.slice(0, 57) + "…" : words;
  return t.charAt(0).toUpperCase() + t.slice(1);
}

/** Summarize the opening exchange into a 5–8 word topic via OpenAI. */
async function llmTitle(userText: string, assistantText: string): Promise<string | null> {
  const key = process.env.OPENAI_API_KEY;
  if (!key) return null;
  try {
    const res = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${key}`,
      },
      body: JSON.stringify({
        model: process.env.OPENAI_TITLE_MODEL ?? "gpt-4o-mini",
        temperature: 0.2,
        max_tokens: 20,
        messages: [
          {
            role: "system",
            content:
              "You title chat conversations. Reply with ONLY a concise 3–8 word " +
              "topic in Title Case. No quotes, no punctuation at the end, no prefix.",
          },
          {
            role: "user",
            content: `User asked: "${userText.slice(0, 500)}"\nAssistant answered: "${assistantText.slice(
              0,
              500
            )}"\n\nTopic:`,
          },
        ],
      }),
      signal: AbortSignal.timeout(12_000),
    });
    if (!res.ok) return null;
    const data = await res.json();
    const raw: string = data?.choices?.[0]?.message?.content ?? "";
    const title = raw.replace(/\s+/g, " ").trim().replace(/^["'`]+|["'`.]+$/g, "");
    return title ? title.slice(0, 80) : null;
  } catch {
    return null;
  }
}

/** POST — generate + store the conversation title (only if not already set). */
export async function POST(_req: Request, { params }: Ctx) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const { id } = await params;

  const convo = await getConversation(id, user.id);
  if (!convo) return NextResponse.json({ error: "Not found" }, { status: 404 });
  if (convo.conversation.title) {
    return NextResponse.json({ title: convo.conversation.title, unchanged: true });
  }

  const firstUser = convo.messages.find((m) => m.role === "user")?.content ?? "";
  const firstAsst = convo.messages.find((m) => m.role === "assistant")?.content ?? "";
  if (!firstUser) return NextResponse.json({ error: "No content yet" }, { status: 400 });

  const title = (await llmTitle(firstUser, firstAsst)) ?? heuristicTitle(firstUser);
  await setTitleIfEmpty(id, user.id, title);
  return NextResponse.json({ title });
}
