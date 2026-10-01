"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import {
  Badge,
  Box,
  Button,
  Flex,
  HStack,
  Heading,
  Image,
  Input,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import {
  LuArrowLeft,
  LuChevronDown,
  LuChevronUp,
  LuDownload,
  LuExternalLink,
  LuFileText,
  LuImage,
  LuSearch,
} from "react-icons/lu";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import {
  evidenceImageUrl,
  getChunks,
  getManifest,
  ingest,
  pdfUrl,
  refFromDocId,
  type AdeChunk,
  type AdeManifest,
  type AdeRef,
} from "@/lib/atlas/ade";
import { PageContainer } from "@/components/atlas/ui";
import { CITATION_GREEN } from "@/lib/atlas/citations";

/** Colour per chunk type — the DL layout labels, so the user can see structure. */
const TYPE_COLOR: Record<string, string> = {
  title: "purple",
  text: "gray",
  table: "blue",
  figure: "orange",
  caption: "teal",
  footnote: "yellow",
  marginalia: "gray",
  formula: "pink",
};

function EvidenceView() {
  // `useParams()`, not React's `use(params)`: on Next 14 the `params` prop
  // reaching a client component is a plain object, and `use()` on a non-thenable
  // throws — which surfaced as a blank "client-side exception" page.
  const routeParams = useParams<{ docId: string }>();
  const docId = String(routeParams?.docId ?? "");
  const router = useRouter();
  const search = useSearchParams();
  // The citation link passes the original identifier through, because the
  // doc_id slug alone cannot always be reversed into one.
  const qsSource = search.get("source");
  const qsId = search.get("id");
  /** Passage to preselect, set by "Source evidence" links in the chat. */
  const qsChunk = search.get("chunk");
  const qsRef: AdeRef | null =
    qsSource && qsId
      ? { source: qsSource as AdeRef["source"], id: qsId }
      : null;

  const [manifest, setManifest] = useState<AdeManifest | null>(null);
  const [chunks, setChunks] = useState<AdeChunk[]>([]);
  const [selected, setSelected] = useState<AdeChunk | null>(null);
  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState(false);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  /** A reader who arrived from a citation came to check one claim; one who typed the
      URL has no passage in mind, so the browser opens for them. */
  const [browsing, setBrowsing] = useState(!qsChunk);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const m = await getManifest(docId);
      setManifest(m);
      if (m?.status === "ready") {
        const cs = await getChunks(docId);
        setChunks(cs);
        // Deep link from a citation wins: open on the exact passage the answer
        // used. Otherwise land on something substantive rather than a header.
        const deepLinked = qsChunk ? cs.find((c) => c.chunk_id === qsChunk) : null;
        setSelected(
          deepLinked ??
            cs.find((c) => c.chunk_type === "text" && c.text.length > 200) ??
            cs[0] ??
            null
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [docId, qsChunk]);

  useEffect(() => {
    void load();
  }, [load]);

  /** Not yet extracted → let the user trigger the pipeline from here.
   *
   * The identifier comes from the query string the citation link supplied;
   * `refFromDocId` is only a fallback, because the doc_id slug is lossy for
   * DOI-derived ids and cannot be reversed.
   */
  const runIngest = async () => {
    const ref = qsRef ?? refFromDocId(docId);
    if (!ref) {
      setError(
        "Cannot determine the source identifier for this document. " +
          "Open it from a citation link so the identifier is carried through."
      );
      return;
    }
    setIngesting(true);
    setError(null);
    try {
      await ingest(ref);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setIngesting(false);
    }
  };

  const visible = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const base = chunks.filter((c) => c.chunk_type !== "marginalia");
    return q ? base.filter((c) => c.text.toLowerCase().includes(q)) : base;
  }, [chunks, filter]);

  const meta = manifest?.metadata ?? {};
  /** What to call this document in the header line. The title is what a reader
      recognises; the doc_id slug is the fallback when extraction found no title. */
  const docLabel = meta.title || manifest?.doc_id || docId;

  return (
    <PageContainer>
      <HStack mb={4} spacing={3}>
        <Button size="sm" variant="ghost" leftIcon={<LuArrowLeft />} onClick={() => router.back()}>
          Back
        </Button>
        <Heading size="md" fontWeight={700} letterSpacing="-0.02em">
          Source evidence
        </Heading>
        {manifest?.layout_model && (
          <Badge colorScheme="purple" fontSize="10px">DL layout</Badge>
        )}
      </HStack>

      {loading && (
        <HStack py={10} justify="center"><Spinner size="sm" /><Text fontSize="sm">Loading…</Text></HStack>
      )}

      {!loading && !manifest && (
        <VStack align="start" spacing={3} p={5} borderWidth="1px" borderColor="border.subtle" borderRadius="12px">
          <Text fontSize="sm" color="text.secondary">
            This document has not been extracted yet.
          </Text>
          <Button size="sm" onClick={runIngest} isLoading={ingesting} loadingText="Extracting…">
            Run extraction pipeline
          </Button>
        </VStack>
      )}

      {/* A paywalled paper is a normal outcome, not a failure — say so plainly. */}
      {!loading && manifest && manifest.status !== "ready" && (
        <VStack align="start" spacing={3} p={5} borderWidth="1px" borderColor="border.subtle" borderRadius="12px">
          <Badge colorScheme={manifest.status === "unavailable" ? "orange" : "red"}>
            {manifest.status}
          </Badge>
          <Text fontSize="sm" color="text.secondary">{manifest.reason}</Text>
          <HStack spacing={2}>
            {/* A `failed` manifest is a transient error, so offer a retry.
                `unavailable` (paywalled) will not change on retry — only the
                publisher link helps there. */}
            {manifest.status === "failed" && (
              <Button size="sm" onClick={runIngest} isLoading={ingesting} loadingText="Retrying…">
                Retry extraction
              </Button>
            )}
            {meta.publisher_url && (
              <Button as="a" href={meta.publisher_url} target="_blank" rel="noopener noreferrer"
                size="sm" variant="outline" rightIcon={<LuExternalLink />}>
                Read at publisher
              </Button>
            )}
          </HStack>
        </VStack>
      )}

      {error && <Text fontSize="sm" color="red.400" mb={3}>{error}</Text>}

      {!loading && manifest?.status === "ready" && (
        <>
          {/* The document and page this evidence comes from, stated before anything
              else — a reader arriving from a citation wants to know what they are
              looking at before they read it. */}
          <Text fontSize="12.5px" color="text.subtle" mt={-2} mb={4}>
            {docLabel}
            {selected && ` | page ${selected.page + 1}`}
          </Text>

          <Flex gap={4} align="start" direction={{ base: "column", lg: "row" }}>
            {/* The proof: the page itself, with the cited region highlighted. Widest
                element on the page because it is the thing being verified. */}
            <Box flex={1} minW={0} borderWidth="1px" borderColor="border.subtle"
              borderRadius="14px" overflow="hidden" bg="bg.panel">
              <HStack px={4} py={3} justify="space-between" borderBottom="1px solid"
                borderColor="border.subtle" bg="bg.subtle" gap={2} flexWrap="wrap">
                <Box>
                  <Text fontSize="10.5px" fontWeight={800} letterSpacing="0.08em"
                    textTransform="uppercase" color="text.subtle">
                    Highlighted page
                  </Text>
                  <Text fontSize="14px" fontWeight={700} color="text.primary">
                    Page {(selected?.page ?? 0) + 1}
                  </Text>
                </Box>
                <HStack spacing={2} px={3} py={2} borderRadius="10px" borderWidth="1px"
                  borderColor={CITATION_GREEN.border} bg={CITATION_GREEN.bg}>
                  <Box as={LuImage} boxSize={3.5} color={CITATION_GREEN.fg} aria-hidden />
                  <Text fontSize="12px" fontWeight={700} color={CITATION_GREEN.fg}>
                    Highlighted image
                  </Text>
                </HStack>
              </HStack>

              {selected ? (
                <Box p={4} bg="bg.subtle" maxH="76vh" overflowY="auto">
                  <Box borderRadius="8px" overflow="hidden" bg="white"
                    boxShadow="0 1px 10px -4px rgba(0,0,0,0.25)">
                    {/* Rendered on the fly by PyMuPDF from the stored bbox — the
                        same green as the inline citation marker. */}
                    <Image src={evidenceImageUrl(docId, selected.chunk_id, 150)}
                      alt={`Evidence for chunk ${selected.chunk_id} on page ${selected.page + 1}`}
                      w="100%" />
                  </Box>
                </Box>
              ) : (
                <Text p={5} fontSize="sm" color="text.subtle">
                  Select a passage to see its source region.
                </Text>
              )}
            </Box>

            {/* Sidebar: the original document, then the exact text that was cited. */}
            <VStack align="stretch" spacing={4} w={{ base: "100%", lg: "320px" }} flexShrink={0}>
              <Box p={4} borderWidth="1px" borderColor="border.subtle" borderRadius="14px"
                bg="bg.panel">
                <Flex align="center" justify="center" w="42px" h="42px" borderRadius="12px"
                  bg="bg.subtle" borderWidth="1px" borderColor="border.subtle" mb={3}>
                  <Box as={LuFileText} boxSize={5} color="text.secondary" aria-hidden />
                </Flex>
                <Text fontSize="16px" fontWeight={700} color="text.primary" mb={1}>
                  Original PDF
                </Text>
                <Text fontSize="12.5px" color="text.muted" lineHeight={1.6} mb={3}>
                  Download the complete source document from S3. The preview highlights
                  the exact cited area.
                </Text>
                <Button as="a" href={pdfUrl(docId, true)} w="100%" size="sm"
                  leftIcon={<LuDownload />} bg={CITATION_GREEN.fg} color="white"
                  _hover={{ filter: "brightness(1.08)" }}>
                  Download original PDF
                </Button>
                {meta.europepmc_url && (
                  <Button as="a" href={meta.europepmc_url} target="_blank" rel="noopener noreferrer"
                    w="100%" mt={2} size="sm" variant="ghost" rightIcon={<LuExternalLink />}>
                    Europe PMC
                  </Button>
                )}
              </Box>

              {selected && (
                <Box borderWidth="1px" borderColor="border.subtle" borderRadius="14px"
                  bg="bg.panel" overflow="hidden">
                  <HStack px={4} py={2.5} spacing={2} borderBottom="1px solid"
                    borderColor="border.subtle" bg="bg.subtle">
                    <Box as={LuFileText} boxSize={3.5} color={CITATION_GREEN.fg} aria-hidden />
                    <Text fontSize="10.5px" fontWeight={800} letterSpacing="0.08em"
                      textTransform="uppercase" color={CITATION_GREEN.fg}>
                      Highlighted text
                    </Text>
                  </HStack>
                  <Box px={4} py={3} maxH="46vh" overflowY="auto">
                    <Text fontSize="13px" color="text.secondary" whiteSpace="pre-wrap"
                      lineHeight={1.65}>
                      {selected.text}
                    </Text>
                  </Box>
                </Box>
              )}

              <Box p={4} borderWidth="1px" borderColor="border.subtle" borderRadius="14px"
                bg="bg.panel">
                <Text fontSize="13px" fontWeight={700} color="text.primary" noOfLines={3}>
                  {meta.title}
                </Text>
                <Text fontSize="12px" color="text.subtle" mt={1}>
                  {[meta.authors, meta.journal, meta.year].filter(Boolean).join(" · ")}
                </Text>
                <HStack mt={2.5} spacing={2} flexWrap="wrap">
                  <Badge fontSize="10px">{manifest.page_count} pages</Badge>
                  <Badge fontSize="10px">{manifest.chunk_count} chunks</Badge>
                  {selected && (
                    <Badge fontSize="10px"
                      colorScheme={TYPE_COLOR[selected.chunk_type] ?? "gray"}>
                      {selected.chunk_type}
                    </Badge>
                  )}
                  {meta.is_open_access && (
                    <Badge colorScheme="green" fontSize="10px">Open access</Badge>
                  )}
                  {meta.pmcid && <Badge fontSize="10px">{meta.pmcid}</Badge>}
                </HStack>
              </Box>
            </VStack>
          </Flex>

          {/* Every other extracted passage. Collapsed when the reader arrived from a
              citation — they came to check one claim, not to browse the paper — and
              open when they didn't, because then there is nothing else to do here. */}
          <Box mt={4} borderWidth="1px" borderColor="border.subtle" borderRadius="14px"
            bg="bg.panel" overflow="hidden">
            <HStack as="button" w="100%" px={4} py={3} justify="space-between"
              onClick={() => setBrowsing((b) => !b)} _hover={{ bg: "bg.hover" }}
              aria-expanded={browsing} data-testid="passage-browser-toggle">
              <Text fontSize="12.5px" fontWeight={700} color="text.secondary">
                All extracted passages · {visible.length}
              </Text>
              <Box as={browsing ? LuChevronUp : LuChevronDown} boxSize={4} color="text.subtle" />
            </HStack>
            {browsing && (
              <VStack align="stretch" spacing={2} px={4} pb={4} maxH="60vh" overflowY="auto">
                <HStack>
                  <Box as={LuSearch} boxSize={3.5} color="text.subtle" />
                  <Input size="sm" placeholder="Search extracted text…" value={filter}
                    onChange={(e) => setFilter(e.target.value)} borderRadius="8px" />
                </HStack>
                {visible.map((c) => {
                  const active = selected?.chunk_id === c.chunk_id;
                  return (
                    <Box key={c.chunk_id} p={2.5} borderRadius="10px" cursor="pointer"
                      borderWidth="1px"
                      borderColor={active ? CITATION_GREEN.border : "border.subtle"}
                      bg={active ? CITATION_GREEN.bg : "transparent"}
                      _hover={{ bg: active ? CITATION_GREEN.bg : "bg.hover" }}
                      onClick={() => setSelected(c)}>
                      <HStack spacing={2} mb={1}>
                        <Badge fontSize="9px" colorScheme={TYPE_COLOR[c.chunk_type] ?? "gray"}>
                          {c.chunk_type}
                        </Badge>
                        <Text fontSize="10px" color="text.subtle">p.{c.page + 1}</Text>
                        {c.layout_confidence != null && (
                          <Text fontSize="10px" color="text.subtle">
                            {Math.round(c.layout_confidence * 100)}%
                          </Text>
                        )}
                      </HStack>
                      <Text fontSize="12px" color="text.secondary" noOfLines={3}>{c.text}</Text>
                    </Box>
                  );
                })}
              </VStack>
            )}
          </Box>
        </>
      )}
    </PageContainer>
  );
}

/**
 * `useSearchParams` in a client component must sit under a Suspense boundary,
 * or Next bails out of rendering the whole route.
 */
export default function EvidencePage() {
  return (
    <Suspense
      fallback={
        <PageContainer>
          <HStack py={10} justify="center">
            <Spinner size="sm" />
            <Text fontSize="sm">Loading evidence…</Text>
          </HStack>
        </PageContainer>
      }
    >
      <EvidenceView />
    </Suspense>
  );
}
