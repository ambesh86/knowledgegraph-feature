"use client";

import {
  Avatar,
  Box,
  HStack,
  Link,
  Tag,
  Text,
  VStack,
  Wrap,
  WrapItem,
  useColorModeValue,
} from "@chakra-ui/react";
import {
  LuScan,
  LuDatabase,
  LuGlobe,
  LuBookOpen,
  LuLayers,
  LuFileDown,
  LuFileText,
  LuExternalLink,
  LuFlaskConical,
} from "react-icons/lu";
import { useEffect } from "react";
import { docIdFor, evidenceHref, ingestBatch, refFromUrl } from "@/lib/atlas/ade";
import { evidenceForMessage, evidenceLink } from "@/lib/atlas/evidence";
import { EvidenceNumber, EvidenceReferences } from "@/components/chat/Citations";
import { AnswerMarkdown, useAnchoredAnswer } from "@/components/chat/AnswerMarkdown";
import type { ChatMessage, ToolSelection } from "@/lib/types";

interface Props {
  message: ChatMessage;
  onCitationClick?: (nodeId: string) => void;
}

/** Which data source produced the answer — drives the green source badge. */
const SOURCE_META: Record<ToolSelection, { label: string; icon: typeof LuScan }> = {
  all_sources: { label: "All Sources", icon: LuLayers },
  eugene: { label: "Eugene KG", icon: LuDatabase },
  http: { label: "Web", icon: LuGlobe },
  pubmed: { label: "PubMed", icon: LuBookOpen },
};

interface SourceDoc {
  url: string;
  label: string;
  kind: "paper" | "trial" | "patent" | "link";
  isPdf: boolean;
}

/**
 * Pull source URLs out of an assistant answer (the agent appends
 * "Sources: … (https://…)") and classify them so we can offer the user a
 * direct "Read / Download PDF" affordance for research papers.
 */
function extractSourceDocs(content: string): SourceDoc[] {
  const out: SourceDoc[] = [];
  const seen = new Set<string>();
  for (const m of content.matchAll(/https?:\/\/[^\s)\]]+/g)) {
    const url = m[0].replace(/[.,;:'"]+$/, "");
    if (seen.has(url)) continue;
    seen.add(url);
    const isPdf = /\.pdf($|\?)/i.test(url);
    let kind: SourceDoc["kind"] = "link";
    let label = "Open source";
    if (/pubmed\.ncbi|europepmc|ncbi\.nlm\.nih\.gov\/pmc|pmc\/articles|doi\.org/i.test(url)) {
      kind = "paper";
      label = isPdf ? "Download PDF" : "Read paper";
    } else if (/clinicaltrials\.gov/i.test(url)) {
      kind = "trial";
      label = "Clinical trial";
    } else if (/patents\.google|uspto/i.test(url)) {
      kind = "patent";
      label = "Patent";
    } else if (isPdf) {
      label = "Download PDF";
    }
    out.push({ url, label, kind, isPdf });
  }
  return out.slice(0, 10);
}

const DOC_ICON = {
  paper: LuBookOpen,
  trial: LuFlaskConical,
  patent: LuFileDown,
  link: LuExternalLink,
} as const;

/**
 * Strip model meta-tags and internal citation annotations that some Bedrock
 * models (Nova) emit despite the system prompt:
 *   - <thinking>…</thinking> reasoning blocks and <response> wrappers
 *   - reasoning-path citations like "[node_id=DB13923, tool=fetch_facts]",
 *     "[node_id=null, tool=...]", "[start_id=…, end_id=…, tool=has_reachable_path]"
 *   - inline id parentheticals like "(node_id: 2159)"
 * The reasoning graph is rendered separately from tool-call events, so these
 * annotations are pure noise in the chat bubble. Handles a still-streaming,
 * unclosed <thinking> so the bubble stays clean while tokens arrive.
 */
// Reasoning-tag names some models emit despite the system prompt. Matched
// case-insensitively, with optional attributes/whitespace, e.g. `<thinking>`,
// `<Thinking>`, `< thinking type="x" >`, `<thought>`.
const REASON_TAGS = "thinking|thought|reasoning|reflection|scratchpad|plan|analysis";

function cleanAssistantContent(raw: string): string {
  return raw
    // complete blocks: <thinking ...> … </thinking> (any case/attrs/spacing)
    .replace(
      new RegExp(`<\\s*(?:${REASON_TAGS})\\b[^>]*>[\\s\\S]*?<\\s*/\\s*(?:${REASON_TAGS})\\s*>`, "gi"),
      "",
    )
    // unclosed opening block still streaming: <thinking ...> …(to end)
    .replace(new RegExp(`<\\s*(?:${REASON_TAGS})\\b[^>]*>[\\s\\S]*$`, "i"), "")
    // any stray/orphan closing tag left behind
    .replace(new RegExp(`<\\s*/?\\s*(?:${REASON_TAGS})\\b[^>]*>`, "gi"), "")
    // unwrap response/answer/final wrappers
    .replace(/<\/?\s*(?:response|answer|final)\b[^>]*>/gi, "")
    // a trailing partial tag mid-stream ("… <thi") so it never flashes
    .replace(/<\s*\/?\s*[a-z][a-z0-9]*$/i, "")
    // bracketed citation annotations: any [...] containing an internal key=value
    .replace(
      /\s*\[[^\]]*\b(?:node_id|tool|start_id|end_id|n_hop)\s*=[^\]]*\]/gi,
      "",
    )
    // inline parenthetical ids: "(node_id: 2159)"
    .replace(/\s*\(\s*node_id\s*:[^)]*\)/gi, "")
    // tidy any double spaces / spaces before punctuation left behind
    .replace(/[ \t]{2,}/g, " ")
    .replace(/[ \t]+([.,;:])/g, "$1")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/^\s+/, "");
}

/**
 * Split off the trailing "Sources: …" line the agent appends (e.g.
 * "Sources: Eugene knowledge graph — Emicizumab, hemophilia, F9, F10, …") so we
 * can render it as a distinct green provenance footer instead of plain body text.
 */
function splitSources(content: string): { body: string; sources: string | null } {
  const m = content.match(/(?:^|\n)\s*(Sources?:\s*[^\n]+?)\s*$/i);
  if (!m || m.index == null) return { body: content, sources: null };
  return { body: content.slice(0, m.index).trimEnd(), sources: m[1].trim() };
}


export function Message({ message, onCitationClick }: Props) {
  const isUser = message.role === "user";
  const cleaned = isUser ? message.content : cleanAssistantContent(message.content ?? "");
  const { body: content, sources } = isUser
    ? { body: cleaned, sources: null }
    : splitSources(cleaned);
  const citations = !isUser ? message.citations ?? [] : [];
  const sourceMeta = !isUser && message.source ? SOURCE_META[message.source] : null;
  // Green provenance chip tints (app's score.up green).
  const sourceBg = useColorModeValue("rgba(22,163,74,0.12)", "rgba(74,222,128,0.14)");
  const sourceBorder = useColorModeValue("rgba(22,163,74,0.45)", "rgba(74,222,128,0.40)");
  const sourceText = useColorModeValue("#15803d", "#86efac");
  const sourceDocs = !isUser ? extractSourceDocs(message.content ?? "") : [];
  // Structured evidence from the tool trace — see lib/atlas/evidence.ts for why
  // this is read from tool output rather than scraped from the answer text.
  const evidenceItems = !isUser ? evidenceForMessage(message) : [];
  const evidenceBg = useColorModeValue("rgba(22,163,74,0.10)", "rgba(74,222,128,0.12)");
  const evidenceBorder = useColorModeValue("rgba(22,163,74,0.40)", "rgba(74,222,128,0.35)");

  // Citation markers have to survive Markdown parsing, so they travel through it as
  // an inert text token and are swapped for components on the way out. Rendering
  // each segment as its own <ReactMarkdown> was the obvious alternative and it
  // breaks lists and tables the moment a citation lands mid-structure.
  const anchoredAnswer = useAnchoredAnswer(isUser ? "" : content, evidenceItems);
  const anchored = isUser ? [] : anchoredAnswer.citations;
  const markedContent = isUser ? content : anchoredAnswer.markdown;
  const citationByNumber = anchoredAnswer.byNumber;

  /**
   * Numbering for cited documents.
   *
   * A paper can reach the reader two ways — as a retrieved passage (`anchored`,
   * with an exact chunk) or as a bare URL in the prose (`sourceDocs`). Both are the
   * same source, so a document that already has a passage number reuses it rather
   * than being issued a second one; a reader seeing "3" twice for one paper would
   * reasonably conclude they were different sources.
   *
   * Documents with no resolvable identifier (clinical trials, patents, generic
   * links) get no number, because there is no evidence page for the number to open.
   */
  const numberedDocs = (() => {
    const byDocId = new Map<string, number>();
    anchored.forEach((c) => {
      if (!byDocId.has(c.item.docId)) byDocId.set(c.item.docId, c.n);
    });
    let next = anchored.length;
    return sourceDocs.map((d) => {
      const ref = refFromUrl(d.url);
      if (!ref) return { doc: d, ref: null, n: null };
      const docId = docIdFor(ref);
      let n = byDocId.get(docId);
      if (n == null) {
        n = ++next;
        byDocId.set(docId, n);
      }
      return { doc: d, ref, n };
    });
  })();

  // Pre-warm extraction for every paper this answer cites. Extraction takes
  // ~70s per document, so waiting until the user clicks "Show evidence" would
  // mean staring at a spinner; kicking it off when the answer lands means the
  // document is usually already extracted by the time they look. Fire-and-forget
  // and idempotent server-side, so a re-render or a repeat query costs nothing.
  const ingestKey = sourceDocs.map((d) => d.url).join("|");
  useEffect(() => {
    if (isUser || !ingestKey) return;
    const refs = sourceDocs
      .map((d) => refFromUrl(d.url))
      .filter((r): r is NonNullable<typeof r> => r !== null);
    if (refs.length) void ingestBatch(refs);
    // `ingestKey` is the stable identity of this citation set; sourceDocs is a
    // fresh array each render and would loop forever as a dependency.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ingestKey, isUser]);
  const bubbleBg = isUser ? "accent.500" : "bg.glass";
  const align = isUser ? "flex-end" : "flex-start";
  const radius = isUser
    ? "22px 22px 6px 22px"
    : "22px 22px 22px 6px";

  return (
    <VStack align={align} spacing={2} w="100%">
      <HStack
        align="flex-start"
        spacing={3}
        maxW="min(760px, 90%)"
        flexDir={isUser ? "row-reverse" : "row"}
      >
        <Avatar
          size="sm"
          name={isUser ? "You" : "Eugene"}
          bg={isUser ? "accent.600" : "lumen.500"}
          color="white"
          getInitials={(n) => n[0]}
        />
        <Box
          bg={bubbleBg}
          backdropFilter="saturate(140%) blur(14px)"
          border="1px solid"
          borderColor={isUser ? "accent.400" : "border.subtle"}
          px={4}
          py={3}
          borderRadius={radius}
          boxShadow={isUser ? "0 8px 24px -12px rgba(58,79,247,0.55)" : "none"}
          color={isUser ? "white" : "text.primary"}
          lineHeight={1.55}
          fontSize="15px"
          sx={{
            "p:not(:last-of-type)": { mb: 2 },
            "ol, ul": { pl: 5, mb: 2 },
            code: {
              bg: useColorModeValue("blackAlpha.100", "whiteAlpha.200"),
              px: "4px",
              borderRadius: "4px",
              fontSize: "13px",
            },
            pre: {
              bg: "surface.200",
              border: "1px solid",
              borderColor: "border.subtle",
              p: 3,
              borderRadius: "lg",
              overflowX: "auto",
              fontSize: "13px",
              my: 2,
            },
            a: { color: "accent.200", textDecoration: "underline" },
            table: { borderCollapse: "collapse", width: "100%", mb: 2 },
            "th, td": {
              border: "1px solid",
              borderColor: "border.subtle",
              px: 2,
              py: 1,
              textAlign: "left",
            },
          }}
        >
          {content ? (
            <AnswerMarkdown
              markdown={markedContent}
              byNumber={citationByNumber}
              sourcesColor={sourceText}
            />
          ) : (
            !sources && (
              <Text opacity={0.6} fontStyle="italic">
                thinking…
              </Text>
            )
          )}

          {/* Green provenance chip — the full "Sources: …" line (source + the
              entities the answer drew on). Falls back to a source badge. */}
          {sources ? (
            <HStack
              mt={3}
              px={3}
              py={2}
              align="flex-start"
              spacing={2}
              bg={sourceBg}
              border="1px solid"
              borderColor={sourceBorder}
              borderLeft="3px solid"
              borderLeftColor="score.up"
              borderRadius="10px"
            >
              <Box
                as={sourceMeta?.icon ?? LuDatabase}
                color="score.up"
                mt="1px"
                flexShrink={0}
                boxSize="14px"
                aria-hidden
              />
              <Text fontSize="12.5px" fontWeight={700} lineHeight={1.5} color={sourceText}>
                {sources}
              </Text>
            </HStack>
          ) : (
            sourceMeta && (
              <Tag
                size="sm"
                mt={2}
                bg="moss.500"
                color="white"
                borderRadius="full"
                px={2.5}
                py={1}
                fontSize="11px"
                fontWeight={600}
              >
                <Box as={sourceMeta.icon} mr={1.5} flexShrink={0} aria-hidden />
                Source: {sourceMeta.label}
              </Tag>
            )
          )}
        </Box>
      </HStack>

      {/* Source evidence — numbered to match the inline markers, so a reader can
          go from a specific claim to the passage behind it in one step. Built from
          the `search_fused` tool result rather than the prose, so it appears
          whenever the agent used a passage regardless of how it phrased the
          citation. */}
      {anchored.length > 0 && (
        <Box maxW="min(760px, 90%)" pl={{ base: 0, md: 12 }} w="100%" mt={1}>
          <EvidenceReferences citations={anchored} />
        </Box>
      )}

      {/* Downloadable research papers / source documents the answer cites. */}
      {sourceDocs.length > 0 && (
        <Box maxW="min(760px, 90%)" pl={{ base: 0, md: 12 }} w="100%">
          <Text fontSize="10px" color="text.subtle" textTransform="uppercase" letterSpacing="wider" mb={1.5}>
            Documents · {sourceDocs.length}
          </Text>
          <Wrap spacing={1.5}>
            {numberedDocs.map(({ doc: d, ref, n }) => {
              const Icon = DOC_ICON[d.kind];
              return (
                <WrapItem key={d.url}>
                  {/* Papers we can resolve to a PDF get a numbered green circle,
                      the same object used inline in the answer: clicking it runs
                      (or reuses) the extraction pipeline and opens the highlighted
                      source region. Non-papers get no circle — an evidence link
                      that only 404s is worse than none. */}
                  {ref && n != null && (
                    <Box mr={1.5} display="inline-flex" alignItems="center">
                      <EvidenceNumber
                        n={n}
                        href={evidenceHref(ref)}
                        label={`Source ${n}: open the highlighted evidence for ${d.label}`}
                        size="20px"
                      />
                    </Box>
                  )}
                  <Link
                    href={d.url}
                    isExternal
                    {...(d.isPdf ? { download: "" } : {})}
                    _hover={{ textDecoration: "none" }}
                  >
                    <Tag
                      size="sm"
                      bg={d.kind === "paper" ? "green.600" : "surface.200"}
                      color={d.kind === "paper" ? "white" : "text.primary"}
                      border="1px solid"
                      borderColor={d.kind === "paper" ? "green.500" : "border.subtle"}
                      borderRadius="full"
                      px={2.5}
                      py={1}
                      fontSize="11px"
                      transition="all 0.12s ease"
                      _hover={{ transform: "translateY(-1px)", filter: "brightness(1.08)" }}
                    >
                      <Box as={Icon} mr={1.5} flexShrink={0} aria-hidden />
                      <Text noOfLines={1} maxW="220px">
                        {d.label}
                      </Text>
                    </Tag>
                  </Link>
                </WrapItem>
              );
            })}
          </Wrap>
        </Box>
      )}

      {/* Inline evidence: citation chips for the entities this answer draws on.
          Clicking a chip focuses (centers + selects) that node in the graph. */}
      {citations.length > 0 && (
        <Box maxW="min(760px, 90%)" pl={{ base: 0, md: 12 }} w="100%">
          <Text fontSize="10px" color="text.subtle" textTransform="uppercase" letterSpacing="wider" mb={1.5}>
            Evidence · {citations.length} {citations.length === 1 ? "entity" : "entities"}
          </Text>
          <Wrap spacing={1.5}>
            {dedupeCitations(citations)
              .slice(0, 14)
              .map((c) => (
                <WrapItem key={c.nodeId}>
                  <Tag
                    size="sm"
                    role="button"
                    tabIndex={0}
                    cursor="pointer"
                    bg="surface.200"
                    color="text.primary"
                    border="1px solid"
                    borderColor="border.subtle"
                    borderRadius="full"
                    px={2.5}
                    py={1}
                    fontSize="11px"
                    transition="all 0.12s ease"
                    _hover={{ borderColor: "accent.solid", bg: "surface.300", transform: "translateY(-1px)" }}
                    onClick={() => onCitationClick?.(c.nodeId)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") onCitationClick?.(c.nodeId);
                    }}
                  >
                    <Box as={LuScan} mr={1.5} flexShrink={0} aria-hidden />
                    <Text noOfLines={1} maxW="160px">
                      {c.label || c.nodeId}
                    </Text>
                  </Tag>
                </WrapItem>
              ))}
          </Wrap>
        </Box>
      )}
    </VStack>
  );
}

function dedupeCitations(
  cites: NonNullable<ChatMessage["citations"]>
): NonNullable<ChatMessage["citations"]> {
  const seen = new Set<string>();
  const out: NonNullable<ChatMessage["citations"]> = [];
  for (const c of cites) {
    if (seen.has(c.nodeId)) continue;
    seen.add(c.nodeId);
    out.push(c);
  }
  return out;
}
