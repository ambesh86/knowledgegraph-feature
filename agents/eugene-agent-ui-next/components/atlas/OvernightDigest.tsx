"use client";

import { useEffect, useState } from "react";
import { Box, HStack, Link, Text, VStack, Spinner, Button } from "@chakra-ui/react";
import { LuBookOpen, LuFlaskConical, LuFileText, LuExternalLink, LuMoonStar, LuRefreshCw, LuScan } from "react-icons/lu";
import NextLink from "next/link";
import { apiPath } from "@/lib/basePath";
import { Card, SectionLabel } from "@/components/atlas/ui";

interface IntelItem {
  id: string;
  type: "paper" | "trial" | "patent";
  title: string;
  meta: string;
  date: string;
  url: string;
}
interface Digest {
  area_label?: string;
  generatedAt: string;
  papers: IntelItem[];
  trials: IntelItem[];
  patents: IntelItem[];
  keywords?: string[];
}

/** Papers our own nightly pipeline ingested — the authoritative "new" signal. */
interface IngestedPaper {
  doc_id: string;
  title: string;
  journal?: string;
  year?: string;
  authors?: string;
  indexed_at: string;
  matched_keywords: string[];
  has_evidence: boolean;
}
interface GraphDigest {
  area_label?: string;
  since: string;
  papers: IngestedPaper[];
  papers_total: number;
  corpus: { papers?: number; passages?: number; trials?: number; last_ingest_at?: string };
  error?: string;
}

const GROUPS: { key: keyof Pick<Digest, "papers" | "trials" | "patents">; label: string; icon: typeof LuBookOpen; color: string }[] = [
  { key: "papers", label: "New research", icon: LuBookOpen, color: "accent.iris" },
  { key: "trials", label: "Clinical trials", icon: LuFlaskConical, color: "score.up" },
  { key: "patents", label: "Patents", icon: LuFileText, color: "priority.med" },
];

function Row({ item }: { item: IntelItem }) {
  return (
    <Link href={item.url} isExternal _hover={{ textDecoration: "none" }} display="block">
      <HStack px={4} py={2.5} spacing={3} _hover={{ bg: "bg.subtle" }} borderRadius="8px" align="flex-start" role="group">
        <Box flex={1} minW={0}>
          <Text fontSize="13.5px" fontWeight={600} color="text.primary" noOfLines={2}>{item.title}</Text>
          {item.meta && <Text fontSize="12px" color="text.subtle" noOfLines={1} mt={0.5}>{item.meta}</Text>}
        </Box>
        <HStack spacing={1.5} flexShrink={0} color="text.subtle" pt={0.5}>
          {item.date && <Text fontSize="11px">{item.date.slice(0, 10)}</Text>}
          <Box as={LuExternalLink} boxSize="13px" _groupHover={{ color: "accent.iris" }} />
        </HStack>
      </HStack>
    </Link>
  );
}

/**
 * "While you were away" — the live overnight digest. Scans PubMed, ClinicalTrials
 * and patents for the researcher's focus area (biased by their recent topics) and
 * shows what published since they last looked.
 */
export function OvernightDigest() {
  const [digest, setDigest] = useState<Digest | null>(null);
  const [graph, setGraph] = useState<GraphDigest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    // Both in parallel. The graph digest is the one that must not fail — it is
    // the only source that provably knows what is new, because it reads the
    // `indexed_at` written by the 01:00 ingestion run. External scanning is
    // breadth, and is allowed to come back empty.
    const [g, ext] = await Promise.allSettled([
      fetch(apiPath("/api/atlas/digest"), { cache: "no-store" }).then((r) => r.json()),
      fetch(apiPath("/api/atlas/intel"), { cache: "no-store" }).then((r) => r.json()),
    ]);
    if (g.status === "fulfilled") setGraph(g.value as GraphDigest);
    if (ext.status === "fulfilled") setDigest(ext.value as Digest);
    else setError((ext.reason as Error)?.message ?? "external sources unavailable");
    setLoading(false);
  }
  useEffect(() => {
    void load();
  }, []);

  const ingested = graph?.papers ?? [];
  const externalTotal = digest ? digest.papers.length + digest.trials.length + digest.patents.length : 0;
  const total = ingested.length + externalTotal;

  return (
    <Card overflow="hidden" mb={7} data-testid="overnight-digest">
      <HStack px={5} py={3.5} borderBottom="1px solid" borderColor="border.subtle" justify="space-between"
        bgGradient="linear(to-r, rgba(109,94,252,0.06), transparent)">
        <HStack spacing={2.5}>
          <Box as={LuMoonStar} boxSize="18px" color="accent.iris" />
          <Box>
            <Text fontWeight={700} fontSize="14.5px" color="text.primary">While you were away</Text>
            <Text fontSize="12px" color="text.subtle">
              {graph?.area_label ?? digest?.area_label ?? "Research"} · {total} new item{total === 1 ? "" : "s"}
              {graph?.corpus?.last_ingest_at
                ? ` · last ingest ${graph.corpus.last_ingest_at.slice(0, 16).replace("T", " ")}`
                : ""}
            </Text>
          </Box>
        </HStack>
        <Button size="xs" variant="ghost" leftIcon={<LuRefreshCw size={13} />} color="text.muted"
          onClick={() => void load()} isLoading={loading}>Refresh</Button>
      </HStack>

      <Box px={2} py={2}>
        {loading ? (
          <HStack px={3} py={6} justify="center" color="text.subtle"><Spinner size="sm" /><Text fontSize="13px">Scanning the internet…</Text></HStack>
        ) : error ? (
          <Text px={3} py={5} fontSize="13px" color="text.subtle">Couldn’t reach the live sources right now ({error}).</Text>
        ) : total === 0 ? (
          <Text px={3} py={5} fontSize="13px" color="text.subtle">No new items in the last window for your focus area.</Text>
        ) : (
          <>
          {/* Ingested overnight — from our own pipeline, so every item is
              already extracted and its evidence is one click away. */}
          {ingested.length > 0 && (
            <Box mb={2}>
              <HStack px={4} pt={2} pb={1} spacing={2}>
                <Box as={LuBookOpen} boxSize="14px" color="score.up" />
                <SectionLabel count={graph?.papers_total ?? ingested.length}>
                  Ingested for you overnight
                </SectionLabel>
              </HStack>
              <VStack align="stretch" spacing={0}>
                {ingested.slice(0, 5).map((p) => (
                  <NextLink key={p.doc_id} href={`/evidence/${p.doc_id}`} passHref legacyBehavior>
                    <HStack as="a" px={4} py={2.5} spacing={3} _hover={{ bg: "bg.subtle" }}
                      borderRadius="8px" align="flex-start" role="group">
                      <Box flex={1} minW={0}>
                        <Text fontSize="13.5px" fontWeight={600} color="text.primary" noOfLines={2}>
                          {p.title}
                        </Text>
                        <Text fontSize="12px" color="text.subtle" noOfLines={1} mt={0.5}>
                          {[p.journal, p.year, p.matched_keywords.slice(0, 3).join(", ")]
                            .filter(Boolean).join(" · ")}
                        </Text>
                      </Box>
                      <HStack spacing={1.5} flexShrink={0} color="score.up" pt={0.5}>
                        <Text fontSize="11px">{p.indexed_at.slice(11, 16)}</Text>
                        <Box as={LuScan} boxSize="13px" />
                      </HStack>
                    </HStack>
                  </NextLink>
                ))}
              </VStack>
            </Box>
          )}
          <HStack align="flex-start" spacing={2} flexWrap={{ base: "wrap", lg: "nowrap" }}>
            {GROUPS.map(({ key, label, icon, color }) => {
              const items = digest![key];
              return (
                <Box key={key} flex="1 1 300px" minW={0}>
                  <HStack px={4} pt={2} pb={1} spacing={2}>
                    <Box as={icon} boxSize="14px" color={color} />
                    <SectionLabel count={items.length}>{label}</SectionLabel>
                  </HStack>
                  {items.length === 0 ? (
                    <Text px={4} py={2} fontSize="12px" color="text.subtle">Nothing new.</Text>
                  ) : (
                    <VStack align="stretch" spacing={0}>
                      {items.slice(0, 5).map((it) => <Row key={it.id} item={it} />)}
                    </VStack>
                  )}
                </Box>
              );
            })}
          </HStack>
          </>
        )}
      </Box>
    </Card>
  );
}
