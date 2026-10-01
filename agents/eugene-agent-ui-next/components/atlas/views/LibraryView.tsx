"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Box,
  Button,
  HStack,
  Input,
  InputGroup,
  InputLeftElement,
  Text,
  VStack,
  Wrap,
  WrapItem,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  IconButton,
  Spinner,
} from "@chakra-ui/react";
import { LuFileText, LuSearch, LuMessageSquare, LuEllipsis, LuPencil, LuTrash2, LuPlus } from "react-icons/lu";
import { BRIEFS, type BriefStatus } from "@/lib/atlas/seed";
import { useConversations } from "@/lib/atlas/useConversations";
import { PageContainer, PageHeader, Card } from "@/components/atlas/ui";

const BRIEF_FILTERS: (BriefStatus | "All")[] = ["All", "In progress", "Draft", "In review", "Approved", "Archived"];

/** Persisted `source` values → display labels for the conversation subtitle. */
const SOURCE_LABELS: Record<string, string> = {
  all_sources: "All Sources",
  eugene: "Eugene Graph",
  http: "Web",
  pubmed: "PubMed",
};

const STATUS_STYLE: Record<BriefStatus, { bg: string; color: string }> = {
  "In progress": { bg: "rgba(109,94,252,0.12)", color: "accent.iris" },
  "Draft": { bg: "bg.subtle", color: "text.muted" },
  "In review": { bg: "rgba(217,119,6,0.12)", color: "priority.med" },
  "Approved": { bg: "rgba(22,163,74,0.12)", color: "score.up" },
  "Archived": { bg: "bg.subtle", color: "text.subtle" },
};

function relTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d}d ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function LibraryView() {
  const router = useRouter();
  const [tab, setTab] = useState<"chats" | "briefs">("chats");
  const [q, setQ] = useState("");
  const [briefFilter, setBriefFilter] = useState<BriefStatus | "All">("All");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  const { conversations, loading, rename, remove } = useConversations();

  const chats = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return conversations.filter(
      (c) => !needle || (c.title ?? "").toLowerCase().includes(needle)
    );
  }, [conversations, q]);

  const briefs = BRIEFS.filter((b) => briefFilter === "All" || b.status === briefFilter);

  function commitRename(id: string) {
    const t = draft.trim();
    if (t) void rename(id, t);
    setEditingId(null);
  }

  return (
    <PageContainer maxW="1080px">
      <PageHeader title="Library"
        subtitle="Every conversation, brief, and decision your team has produced — searchable institutional memory." />

      <HStack spacing={2} mb={4}>
        {(["chats", "briefs"] as const).map((t) => (
          <Button key={t} size="sm" h="34px" borderRadius="full" fontWeight={600} fontSize="13px"
            variant={tab === t ? "solid" : "outline"}
            bg={tab === t ? "bg.inverse" : "transparent"}
            color={tab === t ? "text.inverse" : "text.secondary"}
            borderColor="border.default" _hover={{ bg: tab === t ? "bg.inverse" : "bg.hover" }}
            leftIcon={<Box as={t === "chats" ? LuMessageSquare : LuFileText} boxSize="14px" />}
            onClick={() => setTab(t)}>
            {t === "chats" ? `Conversations${conversations.length ? ` (${conversations.length})` : ""}` : "Briefs"}
          </Button>
        ))}
      </HStack>

      {tab === "chats" ? (
        <>
          <HStack mb={4} spacing={3}>
            <InputGroup>
              <InputLeftElement pointerEvents="none">
                <Box as={LuSearch} color="text.subtle" boxSize="16px" />
              </InputLeftElement>
              <Input placeholder="Search conversations…" value={q} onChange={(e) => setQ(e.target.value)}
                bg="bg.panel" borderColor="border.default" fontSize="14px"
                _focus={{ borderColor: "accent.iris", boxShadow: "none" }} />
            </InputGroup>
            <Button size="md" borderRadius="10px" leftIcon={<LuPlus size={16} />}
              onClick={() => router.push("/ask")} flexShrink={0}>New chat</Button>
          </HStack>

          <Card overflow="hidden" data-testid="library-chats">
            {loading && conversations.length === 0 ? (
              <HStack px={5} py={8} justify="center" color="text.subtle"><Spinner size="sm" /><Text>Loading…</Text></HStack>
            ) : chats.length === 0 ? (
              <Box px={5} py={12} textAlign="center" color="text.muted" fontSize="sm">
                {conversations.length === 0
                  ? "No conversations yet. Head to Ask and start researching."
                  : `No conversations match “${q}”.`}
              </Box>
            ) : (
              chats.map((c, i) => (
                <HStack key={c.id} px={5} py={4} borderTop={i ? "1px solid" : "none"} borderColor="border.subtle"
                  _hover={{ bg: "bg.subtle" }} cursor="pointer" transition="background 0.1s" spacing={4} role="group"
                  onClick={() => editingId !== c.id && router.push(`/ask?c=${c.id}`)}>
                  <Box as={LuMessageSquare} color="text.muted" boxSize="18px" flexShrink={0} />
                  <Box flex={1} minW={0}>
                    {editingId === c.id ? (
                      <Input autoFocus size="sm" variant="flushed" fontSize="14.5px" fontWeight={600}
                        value={draft} onChange={(e) => setDraft(e.target.value)}
                        onBlur={() => commitRename(c.id)}
                        onKeyDown={(e) => { if (e.key === "Enter") commitRename(c.id); if (e.key === "Escape") setEditingId(null); }}
                        onClick={(e) => e.stopPropagation()} />
                    ) : (
                      <Text fontSize="14.5px" fontWeight={600} color="text.primary" noOfLines={1}>
                        {c.title || "New conversation"}
                      </Text>
                    )}
                    <Text fontSize="12.5px" color="text.subtle" mt={0.5}>
                      {c.message_count} message{c.message_count === 1 ? "" : "s"}
                      {c.source ? ` · ${SOURCE_LABELS[c.source] ?? c.source}` : ""}
                      {" · "}{relTime(c.last_message_at)}
                    </Text>
                  </Box>
                  <Menu placement="bottom-end" isLazy>
                    <MenuButton as={IconButton} aria-label="Options" icon={<LuEllipsis />} size="sm" variant="ghost"
                      color="text.subtle" opacity={0} _groupHover={{ opacity: 1 }} onClick={(e) => e.stopPropagation()} />
                    <MenuList minW="150px" py={1}>
                      <MenuItem icon={<LuPencil size={14} />} fontSize="13px"
                        onClick={(e) => { e.stopPropagation(); setEditingId(c.id); setDraft(c.title || ""); }}>Rename</MenuItem>
                      <MenuItem icon={<LuTrash2 size={14} />} fontSize="13px" color="priority.high"
                        onClick={(e) => { e.stopPropagation(); void remove(c.id); }}>Delete</MenuItem>
                    </MenuList>
                  </Menu>
                </HStack>
              ))
            )}
          </Card>
        </>
      ) : (
        <>
          <Wrap spacing={1.5} mb={5}>
            {BRIEF_FILTERS.map((f) => (
              <WrapItem key={f}>
                <Button size="sm" h="32px" borderRadius="full" fontWeight={500} fontSize="13px"
                  variant={briefFilter === f ? "solid" : "outline"}
                  bg={briefFilter === f ? "bg.inverse" : "transparent"}
                  color={briefFilter === f ? "text.inverse" : "text.secondary"}
                  borderColor="border.default" _hover={{ bg: briefFilter === f ? "bg.inverse" : "bg.hover" }}
                  onClick={() => setBriefFilter(f)}>{f}</Button>
              </WrapItem>
            ))}
          </Wrap>
          <Card overflow="hidden">
            {briefs.map((b, i) => {
              const ss = STATUS_STYLE[b.status];
              return (
                <HStack key={b.id} px={5} py={4} borderTop={i ? "1px solid" : "none"} borderColor="border.subtle"
                  _hover={{ bg: "bg.subtle" }} cursor="pointer" transition="background 0.1s" spacing={4}>
                  <Box as={LuFileText} color="text.muted" boxSize="18px" flexShrink={0} />
                  <Box flex={1} minW={0}>
                    <Text fontSize="14.5px" fontWeight={600} color="text.primary" noOfLines={1}>{b.title}</Text>
                    <Text fontSize="12.5px" color="text.subtle" mt={0.5}>by {b.author} · {b.type} · updated {b.updated}</Text>
                  </Box>
                  <Box px={2.5} py={1} borderRadius="full" bg={ss.bg} color={ss.color} fontSize="12px" fontWeight={600} flexShrink={0}>
                    {b.status}
                  </Box>
                </HStack>
              );
            })}
          </Card>
        </>
      )}
    </PageContainer>
  );
}
