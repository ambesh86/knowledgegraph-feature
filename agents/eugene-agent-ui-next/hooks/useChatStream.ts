"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { v4 as uuid } from "uuid";
import { openStream, requestDevToken } from "@/lib/api";
import { apiPath } from "@/lib/basePath";
import { parseStream } from "@/lib/streamParser";
import { GraphExtractor } from "@/lib/graphExtractor";
import {
  buildDemoConversation,
  loadDemoGraph,
  type DemoName,
} from "@/lib/demoSeed";
import type {
  ChatMessage,
  ContextGraph,
  ToolInvocation,
  ToolSelection,
} from "@/lib/types";

interface UseChatStreamReturn {
  messages: ChatMessage[];
  graph: ContextGraph;
  setGraph: (g: ContextGraph) => void;
  extractor: GraphExtractor;
  pending: boolean;
  conversationId: string;
  tokenReady: boolean;
  error: string | null;
  send: (prompt: string, tools: ToolSelection[], displayText?: string) => Promise<void>;
  cancel: () => void;
  resetConversation: () => void;
  /** Rehydrate a persisted conversation into the chat (resume from history). */
  loadConversation: (id: string) => Promise<void>;
  /** Dev/demo: seed a real fixture subgraph + synthesized turn (behind ?demo=). */
  seedDemo: (name: DemoName) => Promise<void>;
}

interface UseChatStreamOptions {
  /** Called after a conversation is created or a turn is persisted, so a
   *  history list (sidebar/Library) can refresh. */
  onSaved?: (conversationId: string) => void;
}

export function useChatStream(opts?: UseChatStreamOptions): UseChatStreamReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [graph, setGraph] = useState<ContextGraph>({ nodes: [], rels: [] });
  const [pending, setPending] = useState(false);
  // Generated client-side only: a uuid in initial state would differ between
  // the server-rendered HTML and the client, triggering a hydration mismatch.
  const [conversationId, setConversationId] = useState("");
  useEffect(() => {
    setConversationId((id) => id || uuid());
  }, []);
  const [tokenReady, setTokenReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const extractor = useMemo(() => new GraphExtractor(), []);
  const abortRef = useRef<AbortController | null>(null);

  // ── durable persistence (best-effort, never blocks the chat) ──────────────
  const onSavedRef = useRef(opts?.onSaved);
  useEffect(() => {
    onSavedRef.current = opts?.onSaved;
  }, [opts?.onSaved]);
  // Conversation ids we've already created a DB row for (or loaded from history).
  const createdRef = useRef<Set<string>>(new Set());

  const persistCreate = useCallback(async (id: string, source?: string) => {
    if (!id || createdRef.current.has(id)) return;
    createdRef.current.add(id);
    try {
      await fetch(apiPath("/api/atlas/conversations"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, source }),
      });
      onSavedRef.current?.(id);
    } catch {
      createdRef.current.delete(id); // allow a retry on the next turn
    }
  }, []);

  const persistMessage = useCallback(
    async (
      id: string,
      msg: {
        role: string;
        content: string;
        toolCalls?: unknown;
        citations?: unknown;
        source?: string;
      }
    ) => {
      try {
        await fetch(apiPath(`/api/atlas/conversations/${id}/messages`), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(msg),
        });
      } catch {
        /* best-effort */
      }
    },
    []
  );

  const persistTitle = useCallback(async (id: string) => {
    try {
      await fetch(apiPath(`/api/atlas/conversations/${id}/title`), { method: "POST" });
      onSavedRef.current?.(id);
    } catch {
      /* best-effort */
    }
  }, []);

  // Bootstrap: fetch a dev JWT once on mount
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await requestDevToken();
        if (!cancelled) setTokenReady(true);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const send = useCallback(
    // `displayText` (when the prompt is augmented with attached-document context)
    // is what shows in the bubble/history; `prompt` is the full text sent to the agent.
    async (prompt: string, tools: ToolSelection[], displayText?: string) => {
      if (!prompt.trim()) return;
      const shown = displayText ?? prompt;
      setError(null);
      setPending(true);

      // Pre-flight: verify backend + dependencies are healthy before burning
      // an LLM turn on a request that would 500 anyway.
      try {
        const probe = await fetch(apiPath("/api/health"), { cache: "no-store" });
        if (!probe.ok) {
          setError(`Service not ready (HTTP ${probe.status}). Check backend status.`);
          setPending(false);
          return;
        }
      } catch (e) {
        setError(`Backend unreachable: ${(e as Error).message}`);
        setPending(false);
        return;
      }

      // Wipe the previous prompt's graph so each question gets a clean canvas.
      // Evidence of prior turns still lives in the chat trace; the graph
      // visualises the *current* reasoning path.
      extractor.reset();
      setGraph({ nodes: [], rels: [] });

      const userMsg: ChatMessage = {
        id: uuid(),
        role: "user",
        content: shown,
        createdAt: Date.now(),
      };
      const asstMsg: ChatMessage = {
        id: uuid(),
        role: "assistant",
        content: "",
        createdAt: Date.now(),
        toolCalls: [],
        // Record the active source so the bubble can show a green source badge.
        source: tools[0],
      };
      setMessages((m) => [...m, userMsg, asstMsg]);

      // Persist: create the conversation row (once) + the user turn. First turn
      // in this conversation triggers auto-titling after the answer lands.
      const cid = conversationId;
      const firstTurn = !createdRef.current.has(cid);
      void persistCreate(cid, tools[0]).then(() =>
        persistMessage(cid, { role: "user", content: shown, source: tools[0] })
      );
      let finalContent = "";

      const toolInvocations = new Map<string, ToolInvocation>();
      const ac = new AbortController();
      abortRef.current = ac;

      try {
        const res = await openStream(
          {
            prompt,
            conversation_id: conversationId,
            include_tools: tools,
          },
          ac.signal
        );

        for await (const ev of parseStream(res)) {
          if (ev.type === "content" && ev.content) {
            const text = ev.content;
            finalContent += text;
            setMessages((m) =>
              m.map((msg) =>
                msg.id === asstMsg.id
                  ? { ...msg, content: msg.content + text }
                  : msg
              )
            );
          } else if (ev.type === "tool_call" && ev.tool_id) {
            const inv: ToolInvocation = {
              toolId: ev.tool_id,
              tool: ev.tool ?? "unknown",
              input: ev.tool_input ?? {},
              startedAt: Date.now(),
              status: "pending",
            };
            toolInvocations.set(ev.tool_id, inv);
            setMessages((m) =>
              m.map((msg) =>
                msg.id === asstMsg.id
                  ? {
                      ...msg,
                      toolCalls: [...(msg.toolCalls ?? []), inv],
                    }
                  : msg
              )
            );
            setGraph(extractor.ingest(inv));
          } else if (ev.type === "tool_result" && ev.tool_id) {
            const inv = toolInvocations.get(ev.tool_id);
            if (inv) {
              inv.output = ev.tool_output;
              inv.endedAt = Date.now();
              inv.status = "ok";
              setMessages((m) =>
                m.map((msg) =>
                  msg.id === asstMsg.id
                    ? {
                        ...msg,
                        toolCalls: (msg.toolCalls ?? []).map((t) =>
                          t.toolId === inv.toolId ? { ...inv } : t
                        ),
                      }
                    : msg
                )
              );
              setGraph(extractor.ingest(inv));
            }
          } else if (ev.type === "error" && ev.content) {
            setError(ev.content);
          }
        }
      } catch (e) {
        if ((e as Error).name !== "AbortError") {
          setError((e as Error).message);
        }
      } finally {
        setPending(false);
        abortRef.current = null;
        // Persist the assistant turn (even if aborted mid-stream, save what we
        // have) and, on the first turn, generate the conversation title.
        if (finalContent.trim() || toolInvocations.size > 0) {
          const finalTools = Array.from(toolInvocations.values());
          void persistMessage(cid, {
            role: "assistant",
            content: finalContent,
            toolCalls: finalTools.length ? finalTools : undefined,
            source: tools[0],
          }).then(() => {
            if (firstTurn) void persistTitle(cid);
          });
        }
      }
    },
    [conversationId, extractor, persistCreate, persistMessage, persistTitle]
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const resetConversation = useCallback(() => {
    cancel();
    setMessages([]);
    setGraph({ nodes: [], rels: [] });
    extractor.reset();
    setConversationId(uuid());
    setError(null);
  }, [cancel, extractor]);

  const loadConversation = useCallback(
    async (id: string) => {
      cancel();
      try {
        const res = await fetch(apiPath(`/api/atlas/conversations/${id}`), {
          cache: "no-store",
        });
        if (!res.ok) return;
        const data = await res.json();
        const msgs: ChatMessage[] = (data.messages ?? []).map(
          (m: {
            id: string;
            role: string;
            content: string;
            tool_calls?: ToolInvocation[] | null;
            citations?: unknown;
            source?: string | null;
            created_at: string;
          }) => ({
            id: m.id,
            role: m.role as ChatMessage["role"],
            content: m.content,
            createdAt: new Date(m.created_at).getTime(),
            toolCalls: m.tool_calls ?? undefined,
            source: (m.source ?? undefined) as ToolSelection | undefined,
          })
        );
        // Rebuild the context graph from the last turn's persisted tool calls,
        // so reopening a chat restores its graph instead of showing an empty
        // canvas (the graph itself isn't stored — it's derived from tool calls).
        extractor.reset();
        let g: ContextGraph = { nodes: [], rels: [] };
        const lastWithTools = [...msgs]
          .reverse()
          .find((m) => (m.toolCalls?.length ?? 0) > 0);
        if (lastWithTools?.toolCalls) {
          for (const tc of lastWithTools.toolCalls) g = extractor.ingest(tc);
        }
        setGraph(g);
        setMessages(msgs);
        setConversationId(id);
        createdRef.current.add(id); // already persisted — don't re-create
        setError(null);
      } catch {
        /* ignore — leave current state */
      }
    },
    [cancel, extractor]
  );

  const seedDemo = useCallback(
    async (name: DemoName) => {
      try {
        const g = await loadDemoGraph(name);
        const turnId = uuid();
        setGraph(extractor.seed(g.nodes, g.rels, turnId));
        const { messages: demoMsgs } = buildDemoConversation(g, turnId);
        setMessages(demoMsgs);
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [extractor]
  );

  return {
    messages,
    graph,
    setGraph,
    extractor,
    pending,
    conversationId,
    tokenReady,
    error,
    send,
    cancel,
    resetConversation,
    loadConversation,
    seedDemo,
  };
}
