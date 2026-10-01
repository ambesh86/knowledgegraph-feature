"use client";

import { useCallback, useEffect, useState } from "react";
import { apiPath } from "@/lib/basePath";

/** Window event any component can dispatch after creating/renaming/deleting a
 *  conversation, so all history lists (sidebar + Library) re-sync. */
export const CONVERSATIONS_CHANGED = "atlas:conversations-changed";
export function notifyConversationsChanged() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(CONVERSATIONS_CHANGED));
  }
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  source: string | null;
  archived: boolean;
  last_message_at: string;
  message_count: number;
}

interface UseConversations {
  conversations: ConversationSummary[];
  loading: boolean;
  refresh: () => Promise<void>;
  rename: (id: string, title: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
}

/**
 * Client-side view of the current user's persisted conversations. Shared by the
 * sidebar recents and the Library page. Reads/writes the /api/atlas/conversations
 * routes; all ownership enforcement happens server-side.
 */
export function useConversations(): UseConversations {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch(apiPath("/api/atlas/conversations"), { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        setConversations(data.conversations ?? []);
      } else {
        setConversations([]);
      }
    } catch {
      setConversations([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    // Refresh when any part of the app persists/changes a conversation.
    const onChange = () => void refresh();
    window.addEventListener(CONVERSATIONS_CHANGED, onChange);
    return () => window.removeEventListener(CONVERSATIONS_CHANGED, onChange);
  }, [refresh]);

  const rename = useCallback(
    async (id: string, title: string) => {
      await fetch(apiPath(`/api/atlas/conversations/${id}`), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title } : c))
      );
      notifyConversationsChanged();
    },
    []
  );

  const remove = useCallback(async (id: string) => {
    await fetch(apiPath(`/api/atlas/conversations/${id}`), { method: "DELETE" });
    setConversations((prev) => prev.filter((c) => c.id !== id));
    notifyConversationsChanged();
  }, []);

  return { conversations, loading, refresh, rename, remove };
}
