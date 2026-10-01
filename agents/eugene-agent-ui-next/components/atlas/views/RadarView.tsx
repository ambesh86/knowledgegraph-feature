"use client";

import { useMemo, useState } from "react";
import {
  Box,
  Button,
  Collapse,
  HStack,
  Link,
  Spinner,
  Text,
  VStack,
  Wrap,
  WrapItem,
  useColorModeValue,
} from "@chakra-ui/react";
import {
  LuCheckCheck,
  LuClock,
  LuExternalLink,
  LuEyeOff,
  LuRefreshCw,
  LuChevronDown,
  LuTrendingUp,
  LuTriangleAlert,
  LuX,
} from "react-icons/lu";
import type { Priority, SignalType } from "@/lib/atlas/seed";
import {
  REVIEW_REASON_LABEL,
  SOURCE_LABEL,
  absoluteDate,
  factorLabel,
  relativeDay,
  topFactors,
  type Signal,
  type SignalsResponse,
} from "@/lib/atlas/scout";
import { useScoutAction, useScoutData } from "@/hooks/useScout";
import { PageContainer, PageHeader, PriorityBadge, Card } from "@/components/atlas/ui";
import { scoreTone, typeMeta, typeTone } from "@/lib/atlas/signalStyle";

/**
 * Radar — live competitive monitoring.
 *
 * Every row here comes from a scan of ClinicalTrials.gov, Europe PMC, USPTO and SEC
 * EDGAR, scored deterministically and served from S3. Three things are surfaced that
 * a demo Radar would not bother with, and each is there to make the ranking
 * challengeable rather than merely presentable:
 *
 *  * **Every source is a link.** A signal an analyst cannot click through to verify
 *    is an assertion, not evidence.
 *  * **The score breakdown is expandable.** "Why is this ranked here" is answered by
 *    naming the factors that contributed, not by a tooltip saying "AI-powered".
 *  * **Rationale provenance is labelled.** Prose written by a language model and
 *    prose composed from the score are visibly different claims.
 */

const TYPES: (SignalType | "All")[] = ["All", "Trial", "Patent", "Publication", "Regulatory", "Corporate"];
const PRIORITIES: (Priority | "all")[] = ["all", "high", "med", "watch"];
const PRI_LABEL: Record<string, string> = { all: "All", high: "High", med: "Medium", watch: "Watch" };

/**
 * Type filters, each in its own hue.
 *
 * The selected filter is filled with the same colour that marks rows of that type,
 * so "I am looking at trials" and "this row is a trial" are stated by one visual
 * fact rather than two unrelated ones. "All" stays neutral because it means no
 * type is being singled out.
 */
function TypeFilter({ value, onChange, counts, mode }: {
  value: SignalType | "All";
  onChange: (v: SignalType | "All") => void;
  counts: Record<string, number>;
  mode: "light" | "dark";
}) {
  return (
    <Wrap spacing={1.5}>
      {TYPES.map((o) => {
        const active = value === o;
        const meta = o === "All" ? null : typeMeta(o);
        const tone = meta ? meta[mode] : null;
        const n = o === "All" ? undefined : counts[o];
        return (
          <WrapItem key={o}>
            <Button
              size="xs" h="30px" borderRadius="full" fontWeight={600} fontSize="12px"
              data-testid={`filter-${o}`}
              aria-pressed={active}
              variant="outline"
              bg={active ? (tone?.bg ?? "bg.inverse") : "transparent"}
              color={active ? (tone?.fg ?? "text.inverse") : "text.secondary"}
              borderColor={active ? (tone?.border ?? "bg.inverse") : "border.default"}
              _hover={{
                bg: active ? (tone?.bg ?? "bg.inverse") : "bg.hover",
                borderColor: tone?.border ?? "border.strong",
                color: active ? undefined : tone?.fg,
              }}
              leftIcon={meta ? <Box as={meta.icon} boxSize="12px" aria-hidden /> : undefined}
              onClick={() => onChange(o)}
            >
              {o}
              {n ? (
                <Text as="span" ml={1.5} fontSize="11px" opacity={0.65} fontWeight={700}>
                  {n}
                </Text>
              ) : null}
            </Button>
          </WrapItem>
        );
      })}
    </Wrap>
  );
}

const PRI_TONE: Record<string, { fg: string; bg: string; border: string }> = {
  all: { fg: "text.inverse", bg: "bg.inverse", border: "bg.inverse" },
  high: { fg: "priority.high", bg: "rgba(220,38,38,0.10)", border: "rgba(220,38,38,0.35)" },
  med: { fg: "priority.med", bg: "rgba(217,119,6,0.12)", border: "rgba(217,119,6,0.35)" },
  watch: { fg: "priority.low", bg: "bg.subtle", border: "border.strong" },
};

function PriorityFilter({ value, onChange }: {
  value: Priority | "all"; onChange: (v: Priority | "all") => void;
}) {
  return (
    <Wrap spacing={1.5}>
      {PRIORITIES.map((o) => {
        const active = value === o;
        const t = PRI_TONE[o];
        return (
          <WrapItem key={o}>
            <Button size="xs" h="30px" borderRadius="full" fontWeight={600} fontSize="12px"
              data-testid={`filter-${o}`}
              aria-pressed={active}
              variant="outline"
              bg={active ? t.bg : "transparent"}
              color={active ? t.fg : "text.secondary"}
              borderColor={active ? t.border : "border.default"}
              _hover={{ bg: active ? t.bg : "bg.hover", borderColor: t.border }}
              onClick={() => onChange(o)}>
              {PRI_LABEL[o]}
            </Button>
          </WrapItem>
        );
      })}
    </Wrap>
  );
}

/**
 * A count in the header that is also the filter for that count.
 *
 * "14 medium" was previously a read-only pill sitting next to a Medium filter
 * button that did exactly what clicking the number would suggest. Making the
 * number itself the control removes the duplicate.
 */
function CountChip({ label, count, tone, active, onClick, testId }: {
  label: string;
  count: number;
  tone: { fg: string; bg: string; border: string };
  active: boolean;
  onClick: () => void;
  testId: string;
}) {
  return (
    <Box as="button" onClick={onClick} data-testid={testId} aria-pressed={active}
      px={3} py={1.5} borderRadius="full" bg={tone.bg} color={tone.fg}
      border="1px solid" borderColor={active ? tone.border : "transparent"}
      fontWeight={700} fontSize="13px" lineHeight="1" whiteSpace="nowrap"
      transition="all 0.12s ease"
      _hover={{ borderColor: tone.border, transform: "translateY(-1px)" }}
      title={`Show only ${label} signals`}>
      {count} {label}
    </Box>
  );
}

function ScoreBreakdownPanel({ signal }: { signal: Signal }) {
  const factors = signal.score_breakdown.factors ?? [];
  if (!factors.length) return null;

  return (
    <Box mt={3} pt={3} borderTop="1px solid" borderColor="border.subtle">
      <Text fontSize="11px" fontWeight={700} letterSpacing="0.06em" color="text.subtle"
        textTransform="uppercase" mb={2}>
        Score breakdown
      </Text>
      {factors.map((f) => (
        <HStack key={f.name} spacing={3} mb={1.5} align="center">
          <Text fontSize="12.5px" color="text.secondary" w="130px" flexShrink={0}>
            {factorLabel(f.name)}
          </Text>
          <Box flex={1} h="5px" bg="bg.subtle" borderRadius="full" overflow="hidden" maxW="180px">
            <Box h="100%" w={`${Math.round(f.value * 100)}%`} bg="accent.iris" borderRadius="full" />
          </Box>
          <Text fontSize="11.5px" color="text.subtle" w="92px" flexShrink={0}>
            {(f.value * 100).toFixed(0)}% × {f.weight.toFixed(2)}
          </Text>
          <Text fontSize="11.5px" color="text.muted" flex={1} noOfLines={1}>
            {describeInputs(f.inputs)}
          </Text>
        </HStack>
      ))}
      {/* Uncertainty, stated plainly. The use case asks the system to "flag
          low-confidence outputs for human review rather than suppressing
          uncertainty" — so the reasons are spelled out, not just badged. */}
      {signal.needs_review && signal.review_reasons.length > 0 && (
        <Box mt={3} px={3.5} py={2.5} bg="rgba(217,119,6,0.08)" borderLeft="3px solid"
          borderColor="priority.med" borderRadius="8px" data-testid="review-reasons">
          <Text fontSize="10px" fontWeight={700} letterSpacing="0.06em" color="priority.med"
            textTransform="uppercase" mb={1}>
            Worth a second look
          </Text>
          {signal.review_reasons.map((r) => (
            <Text key={r} fontSize="12.5px" color="text.secondary" lineHeight={1.5}>
              · {REVIEW_REASON_LABEL[r]}
            </Text>
          ))}
        </Box>
      )}

      {/* Knowledge-graph context. Shown next to the score but explicitly NOT part
          of it: a drug absent from CSL's graph is more likely the novel opportunity,
          so ranking on graph membership would favour the familiar. */}
      {signal.graph_entities?.length > 0 && (
        <Box mt={3} pt={3} borderTop="1px solid" borderColor="border.subtle">
          <Text fontSize="11px" fontWeight={700} letterSpacing="0.06em" color="text.subtle"
            textTransform="uppercase" mb={1.5}>
            Known to the CSL graph
          </Text>
          <HStack spacing={2} flexWrap="wrap" data-testid="graph-entities">
            {signal.graph_entities.map((e) => (
              <Box key={e.id} px={2} py={0.5} bg="bg.subtle" borderRadius="6px"
                fontSize="11.5px" color="text.secondary">
                {e.value}
                <Text as="span" color="text.subtle"> · {e.id}</Text>
              </Box>
            ))}
          </HStack>
          <Text fontSize="11px" color="text.subtle" mt={1.5}>
            Context only — graph membership does not affect the score.
          </Text>
        </Box>
      )}

      {signal.rationale && (
        <Box mt={3} p={3} bg="bg.subtle" borderRadius="8px">
          <HStack spacing={2} mb={1}>
            <Text fontSize="10px" fontWeight={700} letterSpacing="0.06em" color="text.subtle"
              textTransform="uppercase">
              Rationale
            </Text>
            {/* Provenance is shown, not hidden. An LLM paragraph and a computed one
                are different kinds of claim and the reader is entitled to know which. */}
            <Box px={1.5} py={0.5} borderRadius="4px" fontSize="9px" fontWeight={700}
              bg={signal.rationale_kind === "llm" ? "rgba(109,94,252,0.14)" : "bg.panel"}
              color={signal.rationale_kind === "llm" ? "accent.iris" : "text.subtle"}>
              {signal.rationale_kind === "llm" ? "AI-WRITTEN" : "COMPUTED"}
            </Box>
          </HStack>
          <Text fontSize="13px" color="text.secondary" lineHeight={1.55}>{signal.rationale}</Text>
        </Box>
      )}
    </Box>
  );
}

function describeInputs(inputs: Record<string, unknown>): string {
  const matched = inputs.matched;
  if (Array.isArray(matched) && matched.length) return `matched: ${matched.slice(0, 3).join(", ")}`;
  if (inputs.stage) return `stage: ${inputs.stage}`;
  if (inputs.age_days != null) return `${inputs.age_days}d old, ${inputs.window_days}d window`;
  if (inputs.source_count != null) return `${inputs.source_count} source(s)`;
  if (inputs.company != null) return String(inputs.company);
  return "";
}

/**
 * The type chip: icon, name, and the hue that identifies this kind of evidence
 * everywhere on the page — the row's left rail, the filter button, and here.
 */
function TypeChip({ type, mode, size = "sm" }: {
  type: string; mode: "light" | "dark"; size?: "sm" | "xs";
}) {
  const meta = typeMeta(type);
  const tone = meta[mode];
  return (
    <HStack
      spacing={1.5}
      px={size === "sm" ? 2.5 : 2}
      py={size === "sm" ? 1 : 0.5}
      borderRadius="full"
      bg={tone.bg}
      border="1px solid"
      borderColor={tone.border}
      color={tone.fg}
      flexShrink={0}
    >
      <Box as={meta.icon} boxSize={size === "sm" ? "12px" : "11px"} aria-hidden />
      <Text fontSize={size === "sm" ? "11.5px" : "10.5px"} fontWeight={700} letterSpacing="0.01em">
        {meta.label}
      </Text>
    </HStack>
  );
}

/**
 * Score as a ring rather than a number in a row of numbers.
 *
 * The old presentation put "69 /100" inline with the date and the factor names,
 * where it read as one more grey detail. Ranking is the whole product of this page,
 * so the score gets a shape the eye can compare down a column without reading.
 *
 * The digits stay in the DOM as "69/100" — a ring alone is not a value a screen
 * reader or a test can read.
 */
function ScoreMeter({ score, mode }: { score: number; mode: "light" | "dark" }) {
  const value = Math.max(0, Math.min(100, score));
  const tone = scoreTone(value, mode);
  const r = 20;
  const circumference = 2 * Math.PI * r;
  return (
    <Box position="relative" w="52px" h="52px" flexShrink={0} title={`Score ${value.toFixed(0)} of 100`}>
      <Box as="svg" viewBox="0 0 48 48" w="52px" h="52px" transform="rotate(-90deg)" aria-hidden>
        <circle cx="24" cy="24" r={r} fill="none" stroke="currentColor" strokeWidth="4"
          opacity={0.12} color="var(--chakra-colors-text-subtle)" />
        <circle cx="24" cy="24" r={r} fill="none" stroke={tone} strokeWidth="4"
          strokeLinecap="round" strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - value / 100)}
          style={{ transition: "stroke-dashoffset 0.5s ease" }} />
      </Box>
      <Box position="absolute" inset={0} display="flex" alignItems="center" justifyContent="center">
        <Text fontSize="15px" fontWeight={800} color={tone} lineHeight="1">
          {value.toFixed(0)}
        </Text>
        {/* Present for assistive tech and for the ranking test; the ring is the
            visual carrier. */}
        <Text position="absolute" opacity={0} fontSize="1px">/100</Text>
      </Box>
    </Box>
  );
}

function SignalRow({ signal, first, onDismiss }: {
  signal: Signal; first: boolean; onDismiss: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const factors = topFactors(signal.score_breakdown);
  const mode = useColorModeValue<"light", "dark">("light", "dark");
  const tone = typeTone(signal.type, mode);

  return (
    <Box
      position="relative"
      pl={5}
      pr={4}
      py={4}
      borderTop={first ? "none" : "1px solid"}
      borderColor="border.subtle"
      _hover={{ bg: "bg.subtle" }}
      transition="background 0.12s ease"
      data-testid="signal-row"
    >
      {/* Type rail. A few pixels of colour is enough to let the eye group and skip
          rows without reading a word of them — but only at full strength; at the
          chip's border opacity it read as a rendering artefact. */}
      <Box position="absolute" left={0} top={0} bottom={0} w="5px" bg={tone.fg} opacity={0.85} />

      <HStack align="flex-start" justify="space-between" spacing={4}>
        <Box flex={1} minW={0}>
          {/* Classification first: what kind of thing this is, how urgent, and
              whether it is trustworthy — before the reader invests in the title. */}
          <HStack spacing={2} mb={2} flexWrap="wrap">
            <TypeChip type={signal.type} mode={mode} />
            {signal.stage && (
              <Box px={2} py={0.5} bg="bg.subtle" borderRadius="full" fontSize="11px"
                fontWeight={600} color="text.muted" border="1px solid" borderColor="border.subtle">
                {signal.stage}
              </Box>
            )}
            <PriorityBadge priority={signal.priority} />
            {/* Flagged, not hidden. An analyst who discovers the system quietly
                dropped something stops trusting everything it did show. */}
            {signal.needs_review && (
              <HStack spacing={1} px={1.5} py={0.5} borderRadius="5px" bg="rgba(217,119,6,0.14)"
                color="priority.med" fontSize="9px" fontWeight={700} letterSpacing="0.04em"
                data-testid="needs-review-badge"
                title={signal.review_reasons.map((r) => REVIEW_REASON_LABEL[r]).join("; ")}>
                <Box as={LuTriangleAlert} boxSize="9px" aria-hidden />
                <Text>REVIEW</Text>
              </HStack>
            )}
          </HStack>

          <Text fontSize="15.5px" fontWeight={650} color="text.primary" lineHeight={1.4}
            data-testid="signal-title">
            {signal.title}
          </Text>

          {signal.company_name && (
            <Text fontSize="12.5px" color="accent.iris" fontWeight={650} mt={1}>
              {signal.company_name}
              {signal.score_breakdown.ticker ? ` · ${signal.score_breakdown.ticker}` : ""}
            </Text>
          )}

          <Text fontSize="13.5px" color="text.muted" lineHeight={1.55} mt={1.5} noOfLines={2}>
            {signal.summary}
          </Text>

          <HStack mt={2.5} spacing={3} flexWrap="wrap" fontSize="12px">
            {/* Absolute date leads, relative follows. The absolute one is what an
                analyst can check against the source record; the relative one drifts
                as the page sits open. */}
            <HStack spacing={1.5} color="text.subtle"
              title={`Published ${absoluteDate(signal.published)}`}>
              <Box as={LuClock} boxSize="12px" />
              <Text data-testid="signal-date">
                {absoluteDate(signal.published)}
                <Text as="span" color="text.subtle"> · {relativeDay(signal.published)}</Text>
              </Text>
            </HStack>

            {factors.length > 0 && (
              <HStack spacing={1.5} color="text.subtle" minW={0}>
                <Box as={LuTrendingUp} boxSize="12px" flexShrink={0} />
                <Text fontSize="11.5px" noOfLines={1}>
                  {factors.map((f) => factorLabel(f.name)).join(" · ")}
                </Text>
              </HStack>
            )}
          </HStack>

          {/* Every citation, individually clickable. */}
          <HStack mt={2.5} spacing={2} flexWrap="wrap">
            {signal.sources.map((src) => (
              <Link key={`${src.source}-${src.external_id}`} href={src.url} isExternal
                data-testid="source-link"
                title={`${SOURCE_LABEL[src.source] ?? src.source} · ${src.external_id}${
                  src.published ? ` · published ${absoluteDate(src.published)}` : ""
                }`}
                px={2} py={1} borderRadius="7px" bg="bg.subtle" fontSize="11px"
                fontWeight={600} color="text.secondary" display="inline-flex" alignItems="center"
                gap={1} border="1px solid" borderColor="border.subtle"
                transition="all 0.12s ease"
                _hover={{ bg: "bg.hover", color: tone.fg, borderColor: tone.border }}>
                {SOURCE_LABEL[src.source] ?? src.source}
                <Box as={LuExternalLink} boxSize="10px" />
              </Link>
            ))}
            {signal.sources.length > 1 && (
              <HStack spacing={1} px={2} py={1} borderRadius="7px" fontSize="11px"
                fontWeight={700} color="score.up" bg="rgba(22,163,74,0.10)">
                <Box as={LuCheckCheck} boxSize="11px" aria-hidden />
                <Text>corroborated</Text>
              </HStack>
            )}
          </HStack>
        </Box>

        <VStack spacing={2} flexShrink={0} align="center">
          <ScoreMeter score={signal.score} mode={mode} />
          <HStack spacing={0.5}>
            <Button size="xs" variant="ghost" color="text.subtle" fontSize="11px" h="26px"
              data-testid="toggle-breakdown"
              aria-expanded={open}
              rightIcon={<Box as={LuChevronDown} boxSize="12px"
                transform={open ? "rotate(180deg)" : undefined} transition="transform 0.15s" />}
              onClick={() => setOpen((v) => !v)}>
              Why
            </Button>
            <Button size="xs" variant="ghost" color="text.subtle" aria-label="Dismiss signal"
              h="26px" minW="26px" px={0}
              data-testid="dismiss-signal"
              title="Dismiss — hide this signal from the Radar"
              _hover={{ color: "priority.high", bg: "rgba(220,38,38,0.08)" }}
              onClick={() => onDismiss(signal.id)}>
              <Box as={LuEyeOff} boxSize="13px" />
            </Button>
          </HStack>
        </VStack>
      </HStack>

      <Collapse in={open} animateOpacity>
        <ScoreBreakdownPanel signal={signal} />
      </Collapse>
    </Box>
  );
}

export function RadarView() {
  const [type, setType] = useState<SignalType | "All">("All");
  const [priority, setPriority] = useState<Priority | "all">("all");

  const query = useMemo(() => {
    const p = new URLSearchParams({ limit: "200" });
    if (type !== "All") p.set("type", type);
    if (priority !== "all") p.set("priority", priority);
    return `/api/atlas/signals?${p}`;
  }, [type, priority]);

  const { data, loading, error, refetch } = useScoutData<SignalsResponse>(query);
  const { run, pending } = useScoutAction();

  const signals = data?.signals ?? [];
  const counts = data?.counts ?? { high: 0, med: 0, watch: 0 };
  const degraded = data?.degraded ?? false;
  const mode = useColorModeValue<"light", "dark">("light", "dark");

  /**
   * How many of each type are in the list as currently shown.
   *
   * Counted from the rendered set rather than requested from the API, so the number
   * on a filter always describes the list under it. Only meaningful while no type
   * filter is applied — with one on, the set has already been narrowed to that type
   * and the other counts would all read zero, which is true but useless.
   */
  const typeCounts = useMemo(() => {
    if (type !== "All") return {};
    const out: Record<string, number> = {};
    for (const s of signals) out[s.type] = (out[s.type] ?? 0) + 1;
    return out;
  }, [signals, type]);

  async function rescan() {
    await run("/api/atlas/scout/scan");
    refetch();
  }

  async function dismiss(id: string) {
    await run(`/api/atlas/signals/${encodeURIComponent(id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dismissed: true }),
    });
    refetch();
  }

  const lastRun = data?.last_run;

  return (
    <PageContainer>
      <PageHeader title="Radar"
        subtitle="Continuous monitoring across trials, literature, patents and corporate filings — scored against CSL's strategic filter."
        action={
          <HStack spacing={2} fontSize="13px">
            {/* Each count is the filter for that count — see CountChip. */}
            <CountChip label="high" count={counts.high} testId="count-high"
              tone={PRI_TONE.high} active={priority === "high"}
              onClick={() => setPriority(priority === "high" ? "all" : "high")} />
            <CountChip label="medium" count={counts.med} testId="count-med"
              tone={PRI_TONE.med} active={priority === "med"}
              onClick={() => setPriority(priority === "med" ? "all" : "med")} />
            <CountChip label="watch" count={counts.watch} testId="count-watch"
              tone={{ fg: "text.muted", bg: "bg.subtle", border: "border.strong" }}
              active={priority === "watch"}
              onClick={() => setPriority(priority === "watch" ? "all" : "watch")} />
            <Button size="sm" variant="outline" borderColor="border.default" fontWeight={600}
              data-testid="rescan"
              isLoading={pending} loadingText="Scanning"
              leftIcon={<Box as={LuRefreshCw} boxSize="13px" />}
              onClick={rescan}>
              Rescan
            </Button>
          </HStack>
        } />

      {/* Degraded is a first-class state: an empty Radar because the scanner is
          unreachable must never be mistaken for a quiet night. */}
      {degraded && (
        <HStack mb={4} px={4} py={3} bg="rgba(217,119,6,0.10)" borderLeft="3px solid"
          borderColor="priority.med" borderRadius="10px" spacing={2.5} data-testid="degraded-banner">
          <Box as={LuTriangleAlert} color="priority.med" boxSize="16px" flexShrink={0} />
          <Box>
            <Text fontSize="14px" color="text.secondary" fontWeight={600}>
              Scanning service unavailable
            </Text>
            <Text fontSize="12.5px" color="text.muted">
              Showing no signals because the scanner could not be reached — not because
              nothing was found. {data?.reason}
            </Text>
          </Box>
        </HStack>
      )}

      {error && !degraded && (
        <HStack mb={4} px={4} py={3} bg="rgba(220,38,38,0.08)" borderLeft="3px solid"
          borderColor="priority.high" borderRadius="10px" data-testid="error-banner">
          <Text fontSize="13.5px" color="text.secondary">{error}</Text>
        </HStack>
      )}

      {/* Filter bar, in its own surface. Grouping the controls separates "what am I
          looking at" from the list itself, which was previously one undifferentiated
          run of chips floating above the card. */}
      <Card mb={4} px={4} py={3.5}>
        <HStack spacing={5} align="center" flexWrap="wrap" rowGap={3}>
          <HStack spacing={2.5} align="center">
            <Text fontSize="11px" color="text.subtle" fontWeight={700} letterSpacing="0.06em"
              textTransform="uppercase">
              Type
            </Text>
            <TypeFilter value={type} onChange={setType} counts={typeCounts} mode={mode} />
          </HStack>
          <Box w="1px" h="22px" bg="border.subtle" display={{ base: "none", xl: "block" }} />
          <HStack spacing={2.5} align="center">
            <Text fontSize="11px" color="text.subtle" fontWeight={700} letterSpacing="0.06em"
              textTransform="uppercase">
              Priority
            </Text>
            <PriorityFilter value={priority} onChange={setPriority} />
          </HStack>
          <Box flex={1} />
          <HStack spacing={3}>
            {(type !== "All" || priority !== "all") && (
              <Button size="xs" h="28px" variant="ghost" fontSize="11.5px" color="text.muted"
                data-testid="clear-filters"
                leftIcon={<Box as={LuX} boxSize="12px" />}
                onClick={() => { setType("All"); setPriority("all"); }}>
                Clear
              </Button>
            )}
            {lastRun?.started_at && (
              <HStack spacing={1.5} color="text.subtle" fontSize="11.5px" data-testid="last-scanned">
                <Box as={LuClock} boxSize="11px" aria-hidden />
                <Text>
                  Last scanned {relativeDay(lastRun.started_at)}
                  {lastRun.status === "degraded" && " · some sources failed"}
                </Text>
              </HStack>
            )}
          </HStack>
        </HStack>
      </Card>

      {/* What the list is currently showing, in words. A filtered list that looks
          identical to an unfiltered one is how an analyst concludes "there is
          nothing here" while a filter is quietly on. */}
      {!loading && signals.length > 0 && (
        <HStack mb={2.5} px={1} justify="space-between" flexWrap="wrap" gap={2}>
          <Text fontSize="12.5px" color="text.muted">
            Showing <b>{signals.length}</b>
            {data?.total != null && signals.length !== data.total ? ` of ${data.total}` : ""}{" "}
            {type === "All" ? "signals" : `${type.toLowerCase()} signals`}
            {priority !== "all" ? ` · ${PRI_LABEL[priority].toLowerCase()} priority` : ""}
          </Text>
          <Text fontSize="11.5px" color="text.subtle">Ranked by score</Text>
        </HStack>
      )}

      <Card overflow="hidden">
        {loading && (
          <HStack px={5} py={10} justify="center" spacing={3} data-testid="loading">
            <Spinner size="sm" color="accent.iris" />
            <Text fontSize="sm" color="text.muted">Loading signals…</Text>
          </HStack>
        )}

        {!loading && signals.map((signal, i) => (
          <SignalRow key={signal.id} signal={signal} first={i === 0} onDismiss={dismiss} />
        ))}

        {!loading && signals.length === 0 && (
          <Box px={5} py={10} textAlign="center" data-testid="empty-state">
            <Text color="text.muted" fontSize="sm">
              {degraded
                ? "No data available while the scanning service is unreachable."
                : data?.total === 0 && type === "All" && priority === "all"
                  ? "No signals yet. Run a scan to populate the Radar."
                  : "No signals match these filters."}
            </Text>
            {!degraded && data?.total === 0 && (
              <Button mt={4} size="sm" onClick={rescan} isLoading={pending}
                leftIcon={<Box as={LuRefreshCw} boxSize="13px" />}>
                Run first scan
              </Button>
            )}
          </Box>
        )}
      </Card>
    </PageContainer>
  );
}
