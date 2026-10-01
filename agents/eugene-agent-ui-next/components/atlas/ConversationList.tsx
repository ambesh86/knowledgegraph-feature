"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Box,
  HStack,
  Text,
  VStack,
  Input,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  IconButton,
  Spinner,
} from "@chakra-ui/react";
import { LuPlus, LuEllipsis, LuPencil, LuTrash2, LuMessageSquare } from "react-icons/lu";
import {
  useConversations,
  type ConversationSummary,
} from "@/lib/atlas/useConversations";

/** Bucket a timestamp into claude.ai-style date groups. */
function bucket(iso: string): string {
  const d = new Date(iso).getTime();
  const now = Date.now();
  const day = 24 * 60 * 60 * 1000;
  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  const t0 = startOfToday.getTime();
  if (d >= t0) return "Today";
  if (d >= t0 - day) return "Yesterday";
  if (d >= now - 7 * day) return "Previous 7 days";
  if (d >= now - 30 * day) return "Previous 30 days";
  return "Older";
}

const GROUP_ORDER = ["Today", "Yesterday", "Previous 7 days", "Previous 30 days", "Older"];

/**
 * Sidebar conversation history (claude.ai / chatgpt style): "New chat" plus the
 * user's persisted conversations grouped by recency, with inline rename/delete.
 */
export function ConversationList({ currentId }: { currentId?: string }) {
  const router = useRouter();
  // Reactively track the active conversation from ?c= so the row highlights
  // update when navigating between chats (pathname stays /ask, only ?c changes).
  const activeId = useSearchParams().get("c") ?? currentId;
  const { conversations, loading, rename, remove } = useConversations();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  const groups = useMemo(() => {
    const map = new Map<string, ConversationSummary[]>();
    for (const c of conversations) {
      const b = bucket(c.last_message_at);
      if (!map.has(b)) map.set(b, []);
      map.get(b)!.push(c);
    }
    return GROUP_ORDER.filter((g) => map.has(g)).map((g) => ({ group: g, items: map.get(g)! }));
  }, [conversations]);

  function commitRename(id: string) {
    const t = draft.trim();
    if (t) void rename(id, t);
    setEditingId(null);
  }

  return (
    <VStack align="stretch" spacing={1} flex={1} minH={0}>
      <HStack
        as="button"
        onClick={() => router.push("/ask")}
        spacing={2.5}
        px={3}
        py={2}
        mx={0.5}
        borderRadius="9px"
        color="text.secondary"
        border="1px solid"
        borderColor="border.subtle"
        _hover={{ bg: "bg.hover", color: "text.primary", borderColor: "border.default" }}
        transition="all 0.12s"
      >
        <Box as={LuPlus} boxSize="16px" />
        <Text fontSize="13.5px" fontWeight={600}>New chat</Text>
      </HStack>

      <Text px={3} pt={3} pb={1} fontSize="10px" fontWeight={700} letterSpacing="0.08em"
        color="text.subtle" textTransform="uppercase">
        Chats
      </Text>

      <VStack align="stretch" spacing={0} overflowY="auto" flex={1} minH={0}
        sx={{ "&::-webkit-scrollbar": { width: "6px" }, "&::-webkit-scrollbar-thumb": { background: "var(--chakra-colors-border-default)", borderRadius: "3px" } }}>
        {loading && conversations.length === 0 ? (
          <HStack px={3} py={2} color="text.subtle"><Spinner size="xs" /><Text fontSize="12px">Loading…</Text></HStack>
        ) : conversations.length === 0 ? (
          <Text px={3} py={2} fontSize="12px" color="text.subtle">
            No conversations yet. Ask something to start.
          </Text>
        ) : (
          groups.map(({ group, items }) => (
            <Box key={group}>
              <Text px={3} pt={2.5} pb={1} fontSize="10px" fontWeight={600} color="text.subtle">
                {group}
              </Text>
              {items.map((c) => {
                const active = c.id === activeId;
                return (
                  <HStack
                    key={c.id}
                    role="group"
                    data-testid="conversation-row"
                    aria-current={active ? "true" : undefined}
                    px={3}
                    py={1.5}
                    mx={0.5}
                    borderRadius="8px"
                    spacing={2}
                    cursor="pointer"
                    bg={active ? "bg.active" : "transparent"}
                    _hover={{ bg: active ? "bg.active" : "bg.hover" }}
                    onClick={() => editingId !== c.id && router.push(`/ask?c=${c.id}`)}
                  >
                    <Box as={LuMessageSquare} boxSize="14px" color="text.subtle" flexShrink={0} />
                    {editingId === c.id ? (
                      <Input
                        autoFocus
                        size="xs"
                        variant="unstyled"
                        fontSize="13px"
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        onBlur={() => commitRename(c.id)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") commitRename(c.id);
                          if (e.key === "Escape") setEditingId(null);
                        }}
                        onClick={(e) => e.stopPropagation()}
                      />
                    ) : (
                      <Text flex={1} minW={0} noOfLines={1} fontSize="13px"
                        fontWeight={active ? 600 : 500}
                        color={active ? "text.primary" : "text.secondary"}>
                        {c.title || "New conversation"}
                      </Text>
                    )}
                    <Menu placement="bottom-end" isLazy>
                      <MenuButton
                        as={IconButton}
                        aria-label="Conversation options"
                        icon={<LuEllipsis />}
                        size="xs"
                        variant="ghost"
                        color="text.subtle"
                        opacity={0}
                        _groupHover={{ opacity: 1 }}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <MenuList minW="150px" py={1}>
                        <MenuItem
                          icon={<LuPencil size={14} />}
                          fontSize="13px"
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingId(c.id);
                            setDraft(c.title || "");
                          }}
                        >
                          Rename
                        </MenuItem>
                        <MenuItem
                          icon={<LuTrash2 size={14} />}
                          fontSize="13px"
                          color="priority.high"
                          onClick={(e) => {
                            e.stopPropagation();
                            void remove(c.id);
                          }}
                        >
                          Delete
                        </MenuItem>
                      </MenuList>
                    </Menu>
                  </HStack>
                );
              })}
            </Box>
          ))
        )}
      </VStack>
    </VStack>
  );
}
