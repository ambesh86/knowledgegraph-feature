"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Box, Button, Divider, Flex, HStack, Input, Link, Progress, Spinner, Text, VStack,
  useColorMode,
} from "@chakra-ui/react";
import {
  LuArrowRight, LuCircleAlert, LuClock, LuExternalLink, LuInfo, LuRefreshCw,
  LuSearch, LuShieldAlert, LuSparkles, LuTriangleAlert,
} from "react-icons/lu";
import { apiPath } from "@/lib/basePath";
import {
  BAND_LABEL, datedLabel, relativeDay, shortDate,
  type BriefIndexEntry, type BriefsResponse, type BriefSection,
  type ConfidenceBand, type ConfidenceComponent, type DueDiligenceBrief,
} from "@/lib/atlas/scout";
import { PageContainer, PageHeader, SectionLabel, Card } from "@/components/atlas/ui";

/**
 * Use Case 2 — Accelerated Scientific Due Diligence.
 *
 *   "An on-demand agentic workflow that compresses weeks of analyst due diligence
 *    into hours, producing a structured scientific assessment of a target partner's
 *    pipeline."
 *
 * This page replaces a mock that promised exactly this workflow with seeded data. A
 * convincing mock next to a working backend is worse than no page: it teaches people
 * the feature exists in a shape it does not have.
 *
 * The whole design follows one rule taken from the brief generator itself: **absence
 * is rendered, never hidden.** A section with no evidence still appears, still names
 * the sources it consulted, and still explains what its emptiness implies — because
 * "we found no patents" and "we did not look for patents" are different facts with
 * different remedies, and a UI that draws them identically destroys the distinction
 * the backend worked to preserve.
 */

// ── confidence presentation ────────────────────────────────────────────────
//
// `insufficient_evidence` is deliberately not on the same visual scale as the
// numeric bands. It is not a low score; it is the refusal to produce one, and
// rendering it as a number near zero would invite exactly the comparison the
// backend declines to support.

const BAND_TONE: Record<ConfidenceBand, { fg: string; bg: string; border: string }> = {
  high: { fg: "#15803d", bg: "rgba(34,197,94,0.12)", border: "rgba(34,197,94,0.35)" },
  moderate: { fg: "#b45309", bg: "rgba(245,158,11,0.12)", border: "rgba(245,158,11,0.35)" },
  low: { fg: "#b91c1c", bg: "rgba(239,68,68,0.10)", border: "rgba(239,68,68,0.32)" },
  insufficient_evidence: { fg: "#6b7280", bg: "rgba(107,114,128,0.12)", border: "rgba(107,114,128,0.32)" },
};

const BAND_TONE_DARK: Record<ConfidenceBand, { fg: string; bg: string; border: string }> = {
  high: { fg: "#86efac", bg: "rgba(34,197,94,0.16)", border: "rgba(34,197,94,0.40)" },
  moderate: { fg: "#fcd34d", bg: "rgba(245,158,11,0.16)", border: "rgba(245,158,11,0.40)" },
  low: { fg: "#fca5a5", bg: "rgba(239,68,68,0.16)", border: "rgba(239,68,68,0.38)" },
  insufficient_evidence: { fg: "#9ca3af", bg: "rgba(156,163,175,0.16)", border: "rgba(156,163,175,0.35)" },
};

function bandTone(band: ConfidenceBand, mode: "light" | "dark") {
  return (mode === "dark" ? BAND_TONE_DARK : BAND_TONE)[band] ?? BAND_TONE.insufficient_evidence;
}

const SEVERITY_TONE: Record<string, string> = {
  high: "priority.high",
  medium: "priority.med",
  low: "text.subtle",
};

function ConfidenceBadge({
  band, score, size = "md",
}: { band: ConfidenceBand; score: number | null; size?: "sm" | "md" }) {
  const { colorMode } = useColorMode();
  const tone = bandTone(band, colorMode === "dark" ? "dark" : "light");
  const small = size === "sm";
  return (
    <HStack
      spacing={2} px={small ? 2 : 3} py={small ? 0.5 : 1.5} borderRadius="8px"
      bg={tone.bg} border="1px solid" borderColor={tone.border} flexShrink={0}
      data-testid="confidence-badge"
    >
      {score !== null && (
        <Text fontSize={small ? "13px" : "19px"} fontWeight={700} color={tone.fg} lineHeight={1}>
          {score.toFixed(1)}
          <Text as="span" fontSize={small ? "10px" : "11px"} fontWeight={600} opacity={0.75}>
            /10
          </Text>
        </Text>
      )}
      <Text
        fontSize={small ? "10px" : "11px"} fontWeight={700} color={tone.fg}
        letterSpacing="0.03em" textTransform="uppercase"
      >
        {BAND_LABEL[band] ?? band}
      </Text>
    </HStack>
  );
}

/** One scored dimension. An unassessable dimension renders as a gap, not a zero-width
 *  bar — a bar at zero reads as "scored badly", which is the opposite of the truth. */
function Dimension({ c }: { c: ConfidenceComponent }) {
  const { colorMode } = useColorMode();
  const pct = c.score === null ? 0 : Math.round(c.score * 100);
  return (
    <Box py={3} borderTop="1px solid" borderColor="border.subtle">
      <HStack justify="space-between" align="baseline" mb={1.5}>
        <HStack spacing={2}>
          <Text fontSize="13.5px" fontWeight={600} color="text.primary">{c.label}</Text>
          <Text fontSize="10.5px" color="text.subtle">weight {Math.round(c.weight * 100)}%</Text>
        </HStack>
        {c.assessable ? (
          <Text fontSize="13px" fontWeight={700} color="text.primary">{pct}%</Text>
        ) : (
          <Text fontSize="11px" fontWeight={700} color="text.subtle" letterSpacing="0.03em">
            NOT ASSESSED
          </Text>
        )}
      </HStack>
      {c.assessable ? (
        <Progress
          value={pct} size="xs" borderRadius="full"
          colorScheme={pct >= 70 ? "green" : pct >= 45 ? "yellow" : "red"}
          bg={colorMode === "dark" ? "whiteAlpha.200" : "blackAlpha.100"}
        />
      ) : (
        <Box
          h="4px" borderRadius="full" border="1px dashed" borderColor="border.default"
          title="No evidence retrieved for this dimension"
        />
      )}
      <Text fontSize="12.5px" color="text.muted" mt={2} lineHeight={1.55}>{c.finding}</Text>
    </Box>
  );
}

// ── sections ───────────────────────────────────────────────────────────────

function EvidenceRow({ e }: { e: BriefSection["evidence"][number] }) {
  return (
    <HStack
      align="flex-start" justify="space-between" spacing={4} py={2.5}
      borderTop="1px solid" borderColor="border.subtle"
    >
      <Box minW={0}>
        <Link
          href={e.url || undefined} isExternal={!!e.url}
          fontSize="13.5px" fontWeight={500} color={e.url ? "accent.iris" : "text.primary"}
          _hover={e.url ? { textDecoration: "underline" } : undefined}
          noOfLines={2}
        >
          {e.title}
          {e.url && <Box as={LuExternalLink} display="inline" boxSize="11px" ml={1.5} mb="-1px" />}
        </Link>
        <HStack spacing={2.5} mt={1} color="text.subtle" fontSize="11.5px" flexWrap="wrap">
          {e.source && <Text fontWeight={600}>{e.source}</Text>}
          <Text>{e.published ? `${shortDate(e.published)} · ${relativeDay(e.published)}` : "date unknown"}</Text>
        </HStack>
      </Box>
      {e.score !== null && (
        <Text fontSize="12.5px" fontWeight={700} color="text.muted" flexShrink={0}>
          {e.score.toFixed(0)}
        </Text>
      )}
    </HStack>
  );
}

function Section({ s }: { s: BriefSection }) {
  const [open, setOpen] = useState(false);
  const empty = s.evidence_count === 0;

  return (
    <Card px={5} py={4} mb={3} data-testid="brief-section">
      <HStack justify="space-between" align="flex-start" spacing={4} mb={1.5}>
        <Text fontSize="15px" fontWeight={700} color="text.primary">{s.title}</Text>
        <Text
          fontSize="11px" fontWeight={700} color={empty ? "text.subtle" : "text.muted"}
          flexShrink={0} letterSpacing="0.03em"
        >
          {s.evidence_count} ITEM{s.evidence_count === 1 ? "" : "S"}
        </Text>
      </HStack>

      <Text fontSize="13.5px" color="text.secondary" lineHeight={1.6}>{s.summary}</Text>

      {/* The coverage note is the load-bearing part of an empty section: it says what
          the emptiness means. Rendered prominently rather than as fine print. */}
      {s.coverage_note && (
        <HStack
          align="flex-start" spacing={2.5} mt={3} px={3} py={2.5} borderRadius="8px"
          bg="bg.subtle" border="1px solid" borderColor="border.subtle"
        >
          <Box as={LuInfo} boxSize="14px" color="text.subtle" mt="2px" flexShrink={0} />
          <Text fontSize="12.5px" color="text.muted" lineHeight={1.55}>{s.coverage_note}</Text>
        </HStack>
      )}

      <HStack mt={3} pt={2.5} borderTop="1px solid" borderColor="border.subtle" justify="space-between">
        <Text fontSize="11.5px" color="text.subtle">
          Sources consulted: {s.sources_consulted.join(", ") || "—"}
        </Text>
        {s.evidence.length > 0 && (
          <Text
            fontSize="12px" fontWeight={600} color="accent.iris" cursor="pointer"
            onClick={() => setOpen((v) => !v)}
          >
            {open ? "Hide evidence" : `Show ${s.evidence.length} evidence item${s.evidence.length === 1 ? "" : "s"}`}
          </Text>
        )}
      </HStack>

      {open && <Box mt={1}>{s.evidence.map((e, i) => <EvidenceRow key={`${e.url}-${i}`} e={e} />)}</Box>}
    </Card>
  );
}

// ── the brief ──────────────────────────────────────────────────────────────

function Brief({ brief, onRerun, rerunning }: {
  brief: DueDiligenceBrief;
  onRerun: () => void;
  rerunning: boolean;
}) {
  const c = brief.confidence;
  const summary = brief.executive_summary;

  return (
    <Box data-testid="due-diligence-brief">
      <Card px={6} py={5} mb={4}>
        <HStack justify="space-between" align="flex-start" spacing={4} mb={3}>
          <Box minW={0}>
            <Text fontSize="21px" fontWeight={700} color="text.primary">{brief.target.label}</Text>
            <HStack spacing={2.5} mt={1} color="text.subtle" fontSize="12px" flexWrap="wrap">
              <Text>{datedLabel(brief.generated_at)}</Text>
              <Text>·</Text>
              <Text>{brief.coverage.signals_total} evidence items</Text>
              <Text>·</Text>
              <Text>{brief.coverage.sources_consulted.length} sources</Text>
              {brief.from_cache && (<><Text>·</Text><Text>stored result</Text></>)}
            </HStack>
          </Box>
          <HStack spacing={3} flexShrink={0}>
            <ConfidenceBadge band={c.band} score={c.score} />
            <Button
              size="sm" variant="outline" onClick={onRerun} isLoading={rerunning}
              loadingText="Running" leftIcon={<LuRefreshCw size={13} />}
            >
              Re-run
            </Button>
          </HStack>
        </HStack>

        {/* Coverage failures outrank everything else on the page: a brief built while
            a source was down understates its own evidence, and no score computed
            from it should be read before that is known. */}
        {!brief.coverage.complete && (
          <HStack
            align="flex-start" spacing={2.5} mb={3} px={3.5} py={3} borderRadius="8px"
            bg="rgba(220,38,38,0.08)" border="1px solid" borderColor="rgba(220,38,38,0.28)"
          >
            <Box as={LuTriangleAlert} boxSize="15px" color="priority.high" mt="1px" flexShrink={0} />
            <Text fontSize="13px" color="text.secondary" lineHeight={1.55}>
              <b>Incomplete coverage.</b> These sources failed during the run:{" "}
              {brief.coverage.sources_failed.join(", ")}. Sections drawing on them understate
              the evidence — treat the score as provisional.
            </Text>
          </HStack>
        )}

        {summary && (
          <Box>
            <HStack spacing={2} mb={1.5}>
              <SectionLabel>Executive summary</SectionLabel>
              <HStack
                spacing={1} px={2} py={0.5} borderRadius="full" bg="bg.subtle"
                border="1px solid" borderColor="border.subtle"
                title={
                  summary.provenance === "llm"
                    ? "Written by a language model from the computed facts, then checked: every number in it appears in the underlying evidence."
                    : "Generated from the computed facts by a fixed template — no model involved."
                }
              >
                <Box
                  as={summary.provenance === "llm" ? LuSparkles : LuInfo}
                  boxSize="10px" color="text.subtle"
                />
                <Text fontSize="10px" fontWeight={700} color="text.subtle" letterSpacing="0.03em">
                  {summary.provenance === "llm" ? "MODEL-WRITTEN · FACT-CHECKED" : "COMPUTED"}
                </Text>
              </HStack>
            </HStack>
            <Text fontSize="14.5px" color="text.secondary" lineHeight={1.7}>{summary.text}</Text>
          </Box>
        )}

        <HStack
          align="flex-start" spacing={2.5} mt={4} px={3.5} py={3} borderRadius="8px"
          bg="rgba(109,94,252,0.07)" border="1px solid" borderColor="rgba(109,94,252,0.22)"
        >
          <Box as={LuArrowRight} boxSize="15px" color="accent.iris" mt="1px" flexShrink={0} />
          <Box>
            <Text fontSize="11px" fontWeight={700} color="accent.iris" letterSpacing="0.04em" mb={0.5}>
              NEXT ACTION
            </Text>
            <Text fontSize="13.5px" color="text.secondary" lineHeight={1.55}>{brief.next_action}</Text>
          </Box>
        </HStack>
      </Card>

      {brief.risk_flags.length > 0 && (
        <Card px={5} py={4} mb={4}>
          <HStack spacing={2} mb={2}>
            <Box as={LuShieldAlert} boxSize="14px" color="text.muted" />
            <SectionLabel>Risk flags · {brief.risk_flags.length}</SectionLabel>
          </HStack>
          {brief.risk_flags.map((f, i) => (
            <HStack
              key={f.flag} align="flex-start" spacing={3} py={2.5}
              borderTop={i ? "1px solid" : "none"} borderColor="border.subtle"
            >
              <Text
                fontSize="9.5px" fontWeight={800} color={SEVERITY_TONE[f.severity] ?? "text.subtle"}
                letterSpacing="0.05em" w="52px" flexShrink={0} mt="3px"
              >
                {f.severity.toUpperCase()}
              </Text>
              <Box>
                <Text fontSize="13.5px" fontWeight={600} color="text.primary">{f.flag}</Text>
                <Text fontSize="12.5px" color="text.muted" lineHeight={1.55} mt={0.5}>{f.detail}</Text>
              </Box>
            </HStack>
          ))}
        </Card>
      )}

      <Card px={5} py={4} mb={4}>
        <SectionLabel>Scientific confidence · how the score was reached</SectionLabel>
        <Text fontSize="12.5px" color="text.muted" mt={1} mb={1} lineHeight={1.55}>
          Weighted across the dimensions that could be assessed. A dimension with no
          evidence is left unscored rather than counted as zero — that would make
          &ldquo;we did not find it&rdquo; indistinguishable from &ldquo;it is not there&rdquo;.
        </Text>
        {c.components.map((comp) => <Dimension key={comp.key} c={comp} />)}

        {c.reasons.length > 0 && (
          <Box mt={3} pt={3} borderTop="1px solid" borderColor="border.subtle">
            {c.reasons.map((r, i) => (
              <HStack key={i} align="flex-start" spacing={2} mb={1.5}>
                <Box as={LuCircleAlert} boxSize="13px" color="text.subtle" mt="3px" flexShrink={0} />
                <Text fontSize="12.5px" color="text.muted" lineHeight={1.55}>{r}</Text>
              </HStack>
            ))}
          </Box>
        )}
        {c.needs_human_review && (
          <HStack
            mt={3} px={3.5} py={2.5} borderRadius="8px" spacing={2.5}
            bg="rgba(245,158,11,0.10)" border="1px solid" borderColor="rgba(245,158,11,0.30)"
          >
            <Box as={LuTriangleAlert} boxSize="14px" color="priority.med" flexShrink={0} />
            <Text fontSize="13px" color="text.secondary" fontWeight={500}>
              Flagged for human review before this brief is acted on.
            </Text>
          </HStack>
        )}
      </Card>

      <SectionLabel>Assessment sections</SectionLabel>
      <Box mt={2}>
        {brief.sections.map((s) => <Section key={s.key} s={s} />)}
      </Box>

      {brief.coverage.relevance && (
        <Text fontSize="11.5px" color="text.subtle" lineHeight={1.55} mt={2} mb={6}>
          Relevance: {brief.coverage.relevance}.
        </Text>
      )}
    </Box>
  );
}

// ── page ───────────────────────────────────────────────────────────────────

export function ResearchView() {
  const [company, setCompany] = useState("");
  const [asset, setAsset] = useState("");
  const [brief, setBrief] = useState<DueDiligenceBrief | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [index, setIndex] = useState<BriefIndexEntry[]>([]);

  const loadIndex = useCallback(async () => {
    try {
      const res = await fetch(apiPath("/api/atlas/scout/dd"), { cache: "no-store" });
      if (!res.ok) return;
      const body = (await res.json()) as BriefsResponse;
      setIndex(body.targets ?? []);
    } catch {
      // The index is a convenience; failing to load it must not block a new run.
    }
  }, []);

  useEffect(() => { void loadIndex(); }, [loadIndex]);

  const run = useCallback(
    async (payload: { company: string; asset?: string; force?: boolean }) => {
      setRunning(true);
      setError(null);
      try {
        const res = await fetch(apiPath("/api/atlas/scout/dd"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          cache: "no-store",
        });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(body?.error || `Request failed (${res.status})`);
        setBrief(body as DueDiligenceBrief);
        void loadIndex();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setRunning(false);
      }
    },
    [loadIndex]
  );

  const open = useCallback(async (targetId: string) => {
    setRunning(true);
    setError(null);
    try {
      const res = await fetch(apiPath(`/api/atlas/scout/dd/${encodeURIComponent(targetId)}`), {
        cache: "no-store",
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body?.error || `Request failed (${res.status})`);
      setBrief(body as DueDiligenceBrief);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }, []);

  const submit = () => {
    if (company.trim().length < 2 || running) return;
    void run({ company: company.trim(), asset: asset.trim() || undefined });
  };

  return (
    <PageContainer maxW="1180px">
      <PageHeader
        title="Due diligence"
        subtitle="On-demand scientific assessment of a target partner — literature, clinical data, IP and regulatory disclosure, scored and fully cited."
      />

      <Card px={5} py={4} mb={7}>
        <Flex gap={3} direction={{ base: "column", md: "row" }} align={{ md: "flex-end" }}>
          <Box flex="2" minW={0}>
            <Text fontSize="11px" fontWeight={700} color="text.subtle" letterSpacing="0.04em" mb={1.5}>
              COMPANY
            </Text>
            <Input
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder="e.g. Alnylam Pharmaceuticals"
              size="md" data-testid="dd-company"
            />
          </Box>
          <Box flex="1" minW={0}>
            <Text fontSize="11px" fontWeight={700} color="text.subtle" letterSpacing="0.04em" mb={1.5}>
              ASSET <Text as="span" fontWeight={500}>(optional)</Text>
            </Text>
            <Input
              value={asset}
              onChange={(e) => setAsset(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder="e.g. vutrisiran"
              size="md" data-testid="dd-asset"
            />
          </Box>
          <Button
            colorScheme="purple" size="md" onClick={submit}
            isDisabled={company.trim().length < 2}
            isLoading={running} loadingText="Running diligence"
            leftIcon={<LuSearch size={15} />} flexShrink={0}
            data-testid="dd-run"
          >
            Run diligence
          </Button>
        </Flex>
        <HStack spacing={1.5} mt={2.5} color="text.subtle">
          <Box as={LuClock} boxSize="12px" />
          <Text fontSize="11.5px">
            A first run queries four live registries and takes around 30 seconds. A target
            already assessed returns its stored brief immediately.
          </Text>
        </HStack>
      </Card>

      {error && (
        <HStack
          align="flex-start" spacing={2.5} mb={6} px={4} py={3.5} borderRadius="10px"
          bg="rgba(220,38,38,0.08)" border="1px solid" borderColor="rgba(220,38,38,0.28)"
          data-testid="dd-error"
        >
          <Box as={LuTriangleAlert} boxSize="16px" color="priority.high" mt="1px" flexShrink={0} />
          <Box>
            <Text fontSize="13.5px" fontWeight={600} color="text.primary">
              Diligence could not be completed
            </Text>
            <Text fontSize="13px" color="text.muted" mt={0.5} lineHeight={1.55}>{error}</Text>
          </Box>
        </HStack>
      )}

      {running && !brief && (
        <Card px={6} py={10} mb={7}>
          <VStack spacing={3}>
            <Spinner size="lg" color="accent.iris" thickness="3px" />
            <Text fontSize="14px" fontWeight={600} color="text.primary">
              Querying ClinicalTrials.gov, Europe PMC, patents and SEC EDGAR…
            </Text>
            <Text fontSize="12.5px" color="text.subtle" textAlign="center" maxW="440px">
              Sources are queried in parallel and each one is allowed to fail without
              costing the brief. This normally takes about 30 seconds.
            </Text>
          </VStack>
        </Card>
      )}

      {brief && (
        <Box mb={8}>
          <Brief
            brief={brief}
            rerunning={running}
            onRerun={() => void run({
              company: brief.target.company,
              asset: brief.target.asset ?? undefined,
              force: true,
            })}
          />
        </Box>
      )}

      {index.length > 0 && (
        <>
          <Divider mb={5} />
          <SectionLabel count={index.length}>Previously assessed</SectionLabel>
          <Card overflow="hidden" mt={2}>
            {index.map((t, i) => (
              <HStack
                key={t.id} px={5} py={3.5} spacing={4} justify="space-between" cursor="pointer"
                borderTop={i ? "1px solid" : "none"} borderColor="border.subtle"
                _hover={{ bg: "bg.subtle" }} onClick={() => void open(t.id)}
                data-testid="dd-index-row"
              >
                <Box minW={0}>
                  <Text fontSize="14px" fontWeight={600} color="text.primary">{t.label}</Text>
                  <Text fontSize="11.5px" color="text.subtle" mt={0.5}>
                    {t.signals_total} evidence items · assessed {relativeDay(t.generated_at)}
                  </Text>
                </Box>
                <ConfidenceBadge band={t.confidence_band} score={t.confidence_score} size="sm" />
              </HStack>
            ))}
          </Card>
        </>
      )}

      {!brief && !running && index.length === 0 && (
        <Card px={6} py={9}>
          <VStack spacing={2}>
            <Text fontSize="15px" fontWeight={600} color="text.primary">No assessments yet</Text>
            <Text fontSize="13px" color="text.muted" textAlign="center" maxW="460px" lineHeight={1.6}>
              Enter a company above to run diligence. Every brief states what was found,
              what was not, and what the difference means — and is stored so the
              assessment behind a decision can be read back later.
            </Text>
          </VStack>
        </Card>
      )}
    </PageContainer>
  );
}
