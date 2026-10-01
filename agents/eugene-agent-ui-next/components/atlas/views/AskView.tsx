"use client";

import { Suspense, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Avatar,
  Box,
  Button,
  Flex,
  HStack,
  Heading,
  Input,
  Text,
  Tag,
  Tooltip,
  VStack,
  Wrap,
  WrapItem,
  useColorModeValue,
  useToast,
} from "@chakra-ui/react";
import { LuSparkles, LuArrowUp, LuDatabase, LuGlobe, LuBookOpen, LuLayers, LuScan, LuSquare, LuWaypoints, LuPlus, LuTriangleAlert, LuCopy, LuFileText, LuCode, LuShare2, LuPaperclip, LuImage, LuX } from "react-icons/lu";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChatStream } from "@/hooks/useChatStream";
import { apiPath } from "@/lib/basePath";
import type { ToolSelection } from "@/lib/types";
import { notifyConversationsChanged } from "@/lib/atlas/useConversations";
import { contextUsage } from "@/lib/atlas/contextUsage";
import { ASK_SUGGESTIONS } from "@/lib/atlas/seed";
import { AtlasMark } from "@/components/atlas/AtlasMark";
import NextLink from "next/link";
import { AskGraphPanel } from "@/components/atlas/AskGraphPanel";
import { evidenceForMessage, type EvidenceItem } from "@/lib/atlas/evidence";
import { AnswerMarkdown, useAnchoredAnswer } from "@/components/chat/AnswerMarkdown";
import { EvidenceReferences } from "@/components/chat/Citations";
import { FreshnessBadge } from "@/components/atlas/FreshnessBadge";

const SOURCES: { id: ToolSelection; label: string; icon: typeof LuDatabase }[] = [
  { id: "all_sources", label: "All Sources", icon: LuLayers },
  { id: "eugene", label: "Eugene Graph", icon: LuDatabase },
  { id: "http", label: "Web", icon: LuGlobe },
  { id: "pubmed", label: "PubMed", icon: LuBookOpen },
];

const MD_STYLES = {
  "p:not(:last-of-type)": { mb: 2.5 },
  "ol, ul": { pl: 5, mb: 2.5 },
  "li": { mb: 1.5 },
  "li::marker": { color: "accent.iris" },
  a: { color: "accent.iris", textDecoration: "underline", fontWeight: 600 },
  strong: { color: "text.primary", fontWeight: 700 },
  em: { color: "text.secondary" },
  "h1,h2,h3,h4": { fontWeight: 700, mt: 3, mb: 1.5, color: "accent.iris", letterSpacing: "-0.01em", lineHeight: 1.3 },
  h1: { fontSize: "18px" },
  h2: { fontSize: "16px" },
  h3: { fontSize: "15px" },
  code: { bg: "bg.subtle", px: "5px", py: "1px", borderRadius: "5px", fontSize: "12.5px", fontFamily: "mono", color: "accent.iris" },
  pre: { bg: "bg.subtle", border: "1px solid", borderColor: "border.subtle", p: 3, borderRadius: "10px", overflowX: "auto", my: 2.5 },
  "pre code": { bg: "transparent", px: 0, color: "text.primary" },
  blockquote: { borderLeft: "3px solid", borderColor: "accent.iris", pl: 3, my: 2, opacity: 0.92, fontStyle: "italic" },
  table: { borderCollapse: "collapse", width: "100%", my: 2.5, fontSize: "13px" },
  "thead th": { bg: "bg.subtle", fontWeight: 700 },
  "th, td": { border: "1px solid", borderColor: "border.subtle", px: 2.5, py: 1.5, textAlign: "left" },
  "tbody tr:nth-of-type(even)": { bg: "bg.subtle" },
  hr: { my: 3, borderColor: "border.subtle" },
} as const;

// Reasoning-tag names some models emit despite the system prompt. Matched
// case-insensitively, with optional attributes/whitespace.
const REASON_TAGS = "thinking|thought|reasoning|reflection|scratchpad|plan|analysis";

/**
 * Strip model meta-tags (`<thinking>…</thinking>`, `<Thinking type="x">…`,
 * `<thought>…`, unclosed blocks still streaming, stray closing tags) and
 * internal reasoning-path citation annotations, so the chat bubble shows only
 * the answer. The reasoning graph is rendered separately.
 */
function cleanAssistantContent(raw: string): string {
  return raw
    .replace(new RegExp(`<\\s*(?:${REASON_TAGS})\\b[^>]*>[\\s\\S]*?<\\s*/\\s*(?:${REASON_TAGS})\\s*>`, "gi"), "")
    .replace(new RegExp(`<\\s*(?:${REASON_TAGS})\\b[^>]*>[\\s\\S]*$`, "i"), "")
    .replace(new RegExp(`<\\s*/?\\s*(?:${REASON_TAGS})\\b[^>]*>`, "gi"), "")
    .replace(/<\/?\s*(?:response|answer|final)\b[^>]*>/gi, "")
    .replace(/<\s*\/?\s*[a-z][a-z0-9]*$/i, "")
    .replace(/\s*\[[^\]]*\b(?:node_id|tool|start_id|end_id|n_hop)\s*=[^\]]*\]/gi, "")
    .replace(/\s*\(\s*node_id\s*:[^)]*\)/gi, "")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/[ \t]+([.,;:])/g, "$1")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/^\s+/, "");
}

interface Attachment {
  id: string;
  filename: string;
  mime: string;
  isImage: boolean;
  pageCount: number | null;
  textChars: number;
  contextText: string;
}

/** Split off the trailing "Sources: …" line so it renders as a green chip. */
function splitSources(content: string): { body: string; sources: string | null } {
  const m = content.match(/(?:^|\n)\s*(Sources?:\s*[^\n]+?)\s*$/i);
  if (!m || m.index == null) return { body: content, sources: null };
  return { body: content.slice(0, m.index).trimEnd(), sources: m[1].trim() };
}

/**
 * One assistant answer: prose with inline citation markers, then whatever the
 * caller wants between (the provenance chip), then the numbered reference list.
 *
 * A component rather than inline JSX because anchoring is memoised with a hook,
 * and hooks cannot be called from inside the message `.map()`. Keeping the markers
 * and the reference list in the same component is also what guarantees they agree
 * on the numbering — marker "5" and reference "5" are the same object by
 * construction, not by two call sites happening to compute the same order.
 */
function AnchoredAnswer({
  body,
  evidence,
  sourcesColor,
  children,
}: {
  body: string;
  evidence: EvidenceItem[];
  sourcesColor: string;
  children?: ReactNode;
}) {
  const { markdown, citations, byNumber } = useAnchoredAnswer(body, evidence);
  return (
    <>
      {body && (
        <AnswerMarkdown markdown={markdown} byNumber={byNumber} sourcesColor={sourcesColor} />
      )}
      {children}
      {citations.length > 0 && <EvidenceReferences citations={citations} />}
    </>
  );
}

function AskViewInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const cParam = searchParams.get("c");
  const {
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
  } = useChatStream({ onSaved: notifyConversationsChanged });
  const [source, setSource] = useState<ToolSelection>("eugene");
  const [input, setInput] = useState("");
  const [showGraph, setShowGraph] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const sentInitial = useRef(false);
  const loadedIdRef = useRef<string | null>(null);

  const hasChat = messages.some((m) => m.role !== "system");
  const graphNodeCount = graph.nodes.length;

  // Context-window usage (claude-code-style meter + 90% nudge).
  const usage = useMemo(() => contextUsage(messages), [messages]);

  // Green provenance-chip tints (app's score.up green).
  const srcBg = useColorModeValue("rgba(22,163,74,0.12)", "rgba(74,222,128,0.14)");
  const srcBorder = useColorModeValue("rgba(22,163,74,0.45)", "rgba(74,222,128,0.40)");
  const srcText = useColorModeValue("#15803d", "#86efac");

  // ── Export & Publish (artifacts) ──────────────────────────────────────────
  const toast = useToast();
  const artifactCache = useRef<Map<string, string>>(new Map());

  function titleFromBody(body: string): string {
    const line =
      body
        .split("\n")
        .map((l) => l.replace(/^[#>*\-\s]+/, "").trim())
        .find(Boolean) ?? "Atlas answer";
    return line.length > 70 ? `${line.slice(0, 67)}…` : line;
  }

  async function ensureArtifact(mid: string, title: string, bodyMd: string): Promise<string | null> {
    const cached = artifactCache.current.get(mid);
    if (cached) return cached;
    try {
      const res = await fetch(apiPath("/api/atlas/artifacts"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, bodyMd, source, conversationId }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const { id } = (await res.json()) as { id: string };
      artifactCache.current.set(mid, id);
      return id;
    } catch {
      toast({ title: "Could not publish this answer", status: "error", duration: 3500 });
      return null;
    }
  }

  async function copyAnswer(bodyMd: string) {
    try {
      await navigator.clipboard.writeText(bodyMd);
      toast({ title: "Answer copied", status: "success", duration: 1600 });
    } catch {
      /* ignore */
    }
  }

  async function downloadAnswer(mid: string, title: string, bodyMd: string, fmt: "docx" | "html") {
    const id = await ensureArtifact(mid, title, bodyMd);
    if (id) window.location.href = apiPath(`/api/atlas/artifacts/${id}/export?fmt=${fmt}`);
  }

  async function publishAnswer(mid: string, title: string, bodyMd: string) {
    const id = await ensureArtifact(mid, title, bodyMd);
    if (!id) return;
    const link = `${window.location.origin}${apiPath(`/a/${id}`)}`;
    try {
      await navigator.clipboard.writeText(link);
    } catch {
      /* ignore */
    }
    toast({ title: "Published — link copied", description: link, status: "success", duration: 5000, isClosable: true });
  }

  // ── Attachments: upload → on-box parse → ground the next prompt ────────────
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function uploadFiles(files: File[]) {
    if (!files.length) return;
    setUploading(true);
    for (const file of files) {
      const fd = new FormData();
      fd.append("file", file);
      if (conversationId) fd.append("conversationId", conversationId);
      try {
        const res = await fetch(apiPath("/api/atlas/uploads"), { method: "POST", body: fd });
        const data = await res.json();
        if (!res.ok) {
          toast({ title: data.error ?? "Upload failed", status: "error", duration: 3500 });
          continue;
        }
        setAttachments((a) => [
          ...a,
          {
            id: data.id,
            filename: data.filename,
            mime: data.mime,
            isImage: !!data.isImage,
            pageCount: data.pageCount ?? null,
            textChars: data.textChars ?? 0,
            contextText: data.contextText ?? "",
          },
        ]);
        if (!data.isImage && (data.textChars ?? 0) === 0) {
          toast({ title: `No text extracted from ${data.filename}`, status: "warning", duration: 3500 });
        }
      } catch {
        toast({ title: `Could not upload ${file.name}`, status: "error", duration: 3500 });
      }
    }
    setUploading(false);
  }

  function removeAttachment(id: string) {
    setAttachments((a) => a.filter((x) => x.id !== id));
    void fetch(apiPath(`/api/atlas/uploads/${id}`), { method: "DELETE" }).catch(() => {});
  }

  // One-time bootstrap: auto-send a question passed via ?q= (Today / palette).
  useEffect(() => {
    if (sentInitial.current) return;
    const q = new URLSearchParams(window.location.search).get("q");
    if (!cParam && q && tokenReady) {
      sentInitial.current = true;
      void send(q, [source]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tokenReady]);

  // Resume from history whenever ?c=<id> changes (clicking a sidebar chat). The
  // component doesn't remount on a search-param change, so we react to cParam.
  useEffect(() => {
    if (!cParam) {
      // Navigated to a blank /ask FROM a conversation (e.g. sidebar "New chat")
      // → start a fresh thread. Only reset when leaving a real conversation so
      // an initial mount / ?q= bootstrap isn't wiped.
      if (loadedIdRef.current) {
        loadedIdRef.current = null;
        resetConversation();
      }
      return;
    }
    if (cParam === conversationId || cParam === loadedIdRef.current) return;
    loadedIdRef.current = cParam;
    sentInitial.current = true;
    void loadConversation(cParam);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cParam]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  function submit(text: string) {
    const t = text.trim();
    if ((!t && attachments.length === 0) || pending || !tokenReady) return;
    const fresh = !cParam; // a brand-new thread (not opened from history)

    // Ground the prompt in any attached documents (on-box extracted text).
    const docs = attachments.filter((a) => a.contextText);
    let promptToSend = t;
    let displayText: string | undefined;
    if (attachments.length) {
      if (docs.length) {
        const ctx = docs
          .map((a) => `[Attached document: ${a.filename}${a.pageCount ? ` — ${a.pageCount} pages` : ""}]\n${a.contextText}`)
          .join("\n\n---\n\n");
        promptToSend = `${ctx}\n\n=====\nUsing the attached document(s) above where relevant, answer this question:\n${t || "Summarise the attached document(s)."}`;
      } else {
        promptToSend = t || "Describe the attached file(s).";
      }
      displayText = `${t || "Analyse the attached file(s)."}\n\n📎 ${attachments.map((a) => a.filename).join(", ")}`;
    }

    void send(promptToSend, [source], displayText);
    setInput("");
    setAttachments([]);
    // Reflect the new conversation in the URL so it's bookmarkable + highlighted
    // in the sidebar (like claude.ai), without triggering a reload of it.
    if (fresh && conversationId) {
      loadedIdRef.current = conversationId;
      router.replace(`/ask?c=${conversationId}`, { scroll: false });
    }
  }

  function startNewChat() {
    resetConversation();
    setInput("");
    sentInitial.current = true; // don't re-run ?q= bootstrap
    loadedIdRef.current = null;
    router.replace("/ask", { scroll: false });
  }

  return (
    <Flex direction="column" h="100%" minH={0}>
      {/* header */}
      <HStack px={{ base: 5, md: 8 }} py={4} borderBottom="1px solid" borderColor="border.subtle"
        justify="space-between" flexShrink={0}>
        <HStack spacing={2.5}>
          <Heading size="md" fontWeight={700} letterSpacing="-0.02em">Ask</Heading>
          <Text fontSize="13px" color="text.subtle">· graph-grounded research</Text>
          <FreshnessBadge />
        </HStack>
        <HStack spacing={1.5}>
          {SOURCES.map((s) => {
            const active = source === s.id;
            return (
              <Button key={s.id} size="sm" h="32px" borderRadius="full" fontWeight={500} fontSize="13px"
                leftIcon={<Box as={s.icon} boxSize="14px" />}
                variant={active ? "solid" : "outline"}
                bg={active ? "accent.iris" : "transparent"} color={active ? "white" : "text.secondary"}
                borderColor="border.default" _hover={{ bg: active ? "iris.600" : "bg.hover" }}
                onClick={() => setSource(s.id)}>{s.label}</Button>
            );
          })}
          <Box w="1px" h="20px" bg="border.default" mx={1} />
          <Tooltip label={showGraph ? "Hide context graph" : "Show context graph"} fontSize="xs">
            <Button size="sm" h="32px" borderRadius="full" fontWeight={600} fontSize="13px"
              leftIcon={<Box as={LuWaypoints} boxSize="15px" />}
              variant={showGraph ? "solid" : "outline"}
              bg={showGraph ? "bg.inverse" : "transparent"}
              color={showGraph ? "text.inverse" : "text.secondary"}
              borderColor="border.default" _hover={{ bg: showGraph ? "bg.inverse" : "bg.hover" }}
              onClick={() => setShowGraph((v) => !v)}>
              Graph
              {graphNodeCount > 0 && (
                <Box as="span" ml={1.5} px={1.5} py={0.5} borderRadius="full" fontSize="10px"
                  bg={showGraph ? "whiteAlpha.300" : "accent.iris"} color="white">
                  {graphNodeCount}
                </Box>
              )}
            </Button>
          </Tooltip>
        </HStack>
      </HStack>

      <Flex flex={1} minH={0}>
        {/* chat column */}
        <Flex direction="column" flex={1} minW={0}>

      {/* body */}
      <Box flex={1} minH={0} overflowY="auto" ref={scrollRef}>
        <Box maxW="820px" mx="auto" px={{ base: 5, md: 8 }} py={6}>
          {!hasChat ? (
            <VStack align="stretch" spacing={7}>
              <VStack spacing={3} py={6}>
                <AtlasMark size={40} />
                <Heading size="md" fontWeight={700}>Ask anything about your competitive landscape</Heading>
                <Text color="text.muted" textAlign="center" maxW="520px">
                  Every answer is grounded in the Eugene knowledge graph and cited to its source.
                  Pick a starting point — or ask your own question below.
                </Text>
              </VStack>
              {ASK_SUGGESTIONS.map((group) => (
                <Box key={group.group}>
                  <Text fontSize="13px" fontWeight={700} color="text.primary">{group.group}</Text>
                  <Text fontSize="12.5px" color="text.subtle" mb={2.5}>{group.subtitle}</Text>
                  <VStack align="stretch" spacing={2}>
                    {group.items.map((q) => (
                      <HStack key={q} as="button" onClick={() => submit(q)} spacing={3}
                        px={4} py={3} bg="bg.panel" border="1px solid" borderColor="border.subtle"
                        borderRadius="11px" _hover={{ borderColor: "iris.300", bg: "bg.subtle" }}
                        transition="all 0.1s" textAlign="left">
                        <Box as={LuSparkles} color="accent.iris" boxSize="15px" flexShrink={0} />
                        <Text fontSize="14px" color="text.secondary">{q}</Text>
                      </HStack>
                    ))}
                  </VStack>
                </Box>
              ))}
            </VStack>
          ) : (
            <VStack align="stretch" spacing={6}>
              {messages.filter((m) => m.role !== "system").map((m) => (
                <HStack key={m.id} align="flex-start" spacing={3}
                  flexDir={m.role === "user" ? "row-reverse" : "row"}>
                  {m.role === "user" ? (
                    <Avatar size="sm" bg="brand.500" color="white" name="You" getInitials={() => "You"} boxSize="30px" fontSize="11px" />
                  ) : (
                    <Box flexShrink={0}><AtlasMark size={30} /></Box>
                  )}
                  <Box maxW="80%" bg={m.role === "user" ? "accent.iris" : "bg.panel"}
                    color={m.role === "user" ? "white" : "text.primary"}
                    border={m.role === "user" ? "none" : "1px solid"} borderColor="border.subtle"
                    borderLeft={m.role === "assistant" ? "3px solid" : undefined}
                    borderLeftColor={m.role === "assistant" ? "accent.iris" : undefined}
                    boxShadow={m.role === "user" ? "0 6px 20px -10px rgba(58,79,247,0.5)" : "0 2px 12px -6px rgba(0,0,0,0.18)"}
                    px={4} py={3} borderRadius={m.role === "user" ? "16px 16px 4px 16px" : "4px 16px 16px 16px"}
                    fontSize="14.5px" lineHeight={1.6} sx={m.role === "assistant" ? MD_STYLES : undefined}>
                    {m.content ? (
                      m.role === "assistant" ? (
                        (() => {
                          const { body, sources } = splitSources(cleanAssistantContent(m.content));
                          const exportMd = sources ? `${body}\n\n${sources}` : body;
                          const artTitle = titleFromBody(body);
                          // Passages this answer was actually built from, read
                          // from the tool trace (see lib/atlas/evidence.ts).
                          const evidence = evidenceForMessage(m);
                          return (
                            <>
                              {/* Body, then the provenance chip, then the numbered
                                  reference list — all three share one numbering,
                                  computed once inside AnchoredAnswer. */}
                              <AnchoredAnswer body={body} evidence={evidence} sourcesColor={srcText}>
                                {sources && (
                                  <HStack mt={3} px={3} py={2} align="flex-start" spacing={2}
                                    bg={srcBg} border="1px solid" borderColor={srcBorder}
                                    borderLeft="3px solid" borderLeftColor="score.up" borderRadius="10px">
                                    <Box as={LuDatabase} color="score.up" mt="1px" flexShrink={0} boxSize="14px" aria-hidden />
                                    <Text fontSize="12.5px" fontWeight={700} lineHeight={1.5} color={srcText}>
                                      {sources}
                                    </Text>
                                  </HStack>
                                )}
                              </AnchoredAnswer>
                              {body && (
                                <HStack spacing={0.5} mt={2.5} ml={-1} flexWrap="wrap">
                                  {([
                                    { icon: LuCopy, label: "Copy", on: () => void copyAnswer(exportMd) },
                                    { icon: LuFileText, label: "Word", on: () => void downloadAnswer(m.id, artTitle, exportMd, "docx") },
                                    { icon: LuCode, label: "HTML", on: () => void downloadAnswer(m.id, artTitle, exportMd, "html") },
                                    { icon: LuShare2, label: "Publish", on: () => void publishAnswer(m.id, artTitle, exportMd) },
                                  ] as const).map((b) => (
                                    <Button key={b.label} size="xs" variant="ghost" h="26px" px={2}
                                      color="text.secondary" fontWeight={600} fontSize="12px"
                                      leftIcon={<Box as={b.icon} boxSize="13px" />} onClick={b.on}>
                                      {b.label}
                                    </Button>
                                  ))}
                                </HStack>
                              )}
                            </>
                          );
                        })()
                      ) : (
                        <Text>{m.content}</Text>
                      )
                    ) : (
                      <Text opacity={0.6} fontStyle="italic">thinking…</Text>
                    )}
                  </Box>
                </HStack>
              ))}
            </VStack>
          )}
          {error && (
            <Box mt={4} bg="brand.50" color="brand.700" border="1px solid" borderColor="brand.200"
              borderRadius="10px" px={4} py={3} fontSize="14px">{error}</Box>
          )}
        </Box>
      </Box>

      {/* composer */}
      <Box flexShrink={0} px={{ base: 5, md: 8 }} pb={5} pt={2} bgGradient="linear(to-t, bg.canvas, transparent)">
        {/* Context nearly full — nudge to start a new chat (claude-code style). */}
        {usage.nearFull && (
          <HStack maxW="820px" mx="auto" mb={2.5} px={4} py={2.5} borderRadius="12px"
            bg={usage.full ? "rgba(220,38,38,0.10)" : "rgba(217,119,6,0.12)"}
            border="1px solid" borderColor={usage.full ? "priority.high" : "priority.med"}
            justify="space-between" spacing={3}>
            <HStack spacing={2.5} minW={0}>
              <Box as={LuTriangleAlert} boxSize="16px" color={usage.full ? "priority.high" : "priority.med"} flexShrink={0} />
              <Text fontSize="13px" color="text.secondary" noOfLines={2}>
                This conversation is <b>{usage.pct}% of the context window</b>.{" "}
                {usage.full
                  ? "Start a new chat so responses keep their full quality."
                  : "Consider starting a new chat soon to avoid losing earlier detail."}
              </Text>
            </HStack>
            <Button size="sm" borderRadius="9px" leftIcon={<LuPlus size={14} />} flexShrink={0}
              onClick={startNewChat}>New chat</Button>
          </HStack>
        )}
        {attachments.length > 0 && (
          <HStack maxW="820px" mx="auto" mb={2} spacing={2} flexWrap="wrap">
            {attachments.map((a) => (
              <HStack key={a.id} spacing={1.5} bg="bg.subtle" border="1px solid" borderColor="border.subtle"
                borderRadius="8px" px={2} py={1}>
                <Box as={a.isImage ? LuImage : LuFileText} boxSize="13px" color="accent.iris" flexShrink={0} />
                <Text fontSize="12px" maxW="170px" isTruncated>{a.filename}</Text>
                <Text fontSize="10px" color="text.subtle" flexShrink={0}>
                  {a.isImage
                    ? "image"
                    : a.textChars > 0
                      ? `${a.pageCount ? `${a.pageCount}p · ` : ""}${Math.max(1, Math.round(a.textChars / 1000))}k`
                      : "no text"}
                </Text>
                <Box as={LuX} boxSize="13px" cursor="pointer" flexShrink={0} color="text.subtle"
                  _hover={{ color: "text.primary" }} onClick={() => removeAttachment(a.id)} />
              </HStack>
            ))}
            {uploading && <Text fontSize="11px" color="text.subtle">uploading…</Text>}
          </HStack>
        )}
        <Flex as="form" maxW="820px" mx="auto" onSubmit={(e) => { e.preventDefault(); submit(input); }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); const fs = Array.from(e.dataTransfer.files); if (fs.length) void uploadFiles(fs); }}
          align="center" bg="bg.panel" border="1px solid" borderColor="border.default"
          borderRadius="14px" px={3.5} py={2} boxShadow="card"
          _focusWithin={{ borderColor: "iris.400", boxShadow: "focus" }}>
          <input ref={fileInputRef} type="file" multiple hidden
            accept=".pdf,.docx,.txt,.md,.csv,image/png,image/jpeg,image/webp,image/gif"
            onChange={(e) => { const fs = Array.from(e.target.files ?? []); if (fs.length) void uploadFiles(fs); e.target.value = ""; }} />
          <Tooltip label="Attach document or image" fontSize="xs" openDelay={300}>
            <Button variant="ghost" size="sm" px={2} minW="auto" mr={1} flexShrink={0} aria-label="Attach file"
              isDisabled={!tokenReady || uploading} onClick={() => fileInputRef.current?.click()}>
              <LuPaperclip size={16} />
            </Button>
          </Tooltip>
          <Input variant="unstyled" value={input} onChange={(e) => setInput(e.target.value)}
            placeholder={tokenReady ? "Ask, or attach a document…" : "Connecting to the agent…"}
            fontSize="15px" py={2} isDisabled={!tokenReady} />
          {pending ? (
            <Button size="sm" variant="outline" borderColor="brand.300" color="brand.500"
              leftIcon={<LuSquare size={13} />} onClick={cancel}>Stop</Button>
          ) : (
            <Button type="submit" size="sm" borderRadius="10px"
              isDisabled={(!input.trim() && attachments.length === 0) || !tokenReady}
              px={3}><LuArrowUp size={17} /></Button>
          )}
        </Flex>
        <HStack maxW="820px" mx="auto" mt={2} justify="space-between" spacing={3}>
          <Text fontSize="11px" color="text.subtle">
            Platform can make mistakes. Verify source-cited facts before acting.
          </Text>
          {hasChat && (
            <Tooltip label={`~${usage.tokens.toLocaleString()} of ${usage.budget.toLocaleString()} tokens`} fontSize="xs" placement="top">
              <HStack spacing={1.5} flexShrink={0}>
                <Box w="52px" h="5px" borderRadius="full" bg="bg.subtle" overflow="hidden">
                  <Box h="100%" w={`${usage.pct}%`} borderRadius="full"
                    bg={usage.full ? "priority.high" : usage.nearFull ? "priority.med" : "accent.iris"}
                    transition="width 0.3s" />
                </Box>
                <Text fontSize="11px" fontWeight={600}
                  color={usage.nearFull ? (usage.full ? "priority.high" : "priority.med") : "text.subtle"}>
                  {usage.pct}%
                </Text>
              </HStack>
            </Tooltip>
          )}
        </HStack>
      </Box>
        </Flex>

        {/* on-demand context graph */}
        {showGraph && (
          <Box w={{ base: "100%", lg: "46%" }} maxW="760px" flexShrink={0}
            borderLeft="1px solid" borderColor="border.subtle">
            <AskGraphPanel graph={graph} setGraph={setGraph} extractor={extractor}
              onClose={() => setShowGraph(false)} />
          </Box>
        )}
      </Flex>
    </Flex>
  );
}

/** Wrapped in Suspense because AskViewInner reads useSearchParams(). */
export function AskView() {
  return (
    <Suspense fallback={null}>
      <AskViewInner />
    </Suspense>
  );
}
