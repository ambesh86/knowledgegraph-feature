"use client";

import { useRouter } from "next/navigation";
import {
  Box, Button, Divider, HStack, Link, Spinner, Text, VStack,
} from "@chakra-ui/react";
import {
  LuArrowUpRight, LuExternalLink, LuShare2, LuTriangleAlert,
} from "react-icons/lu";
import {
  SOURCE_LABEL, relativeDay, shortDate,
  type BriefingEntry, type BriefingResponse, type ScoutSource,
} from "@/lib/atlas/scout";
import { useScoutAction, useScoutData } from "@/hooks/useScout";
import { PageContainer, PageHeader, Card, DeltaPill } from "@/components/atlas/ui";

/**
 * The weekly partnership briefing.
 *
 * This is the use case's stated deliverable, quoted: "a ranked weekly briefing
 * showing 8-12 high-priority biotech companies with complementary pipeline assets,
 * each accompanied by a plain-English rationale, the key data sources consulted, and
 * a 'next action' recommendation." All four appear on every entry below.
 *
 * When fewer than eight companies clear the bar, the page says so instead of padding
 * the list. A briefing filled out to hit a target number teaches its readers to stop
 * trusting the ranking, which costs more than a short week ever does.
 */

function Entry({ entry }: { entry: BriefingEntry }) {
  return (
    <Card px={5} py={4} data-testid="briefing-entry">
      <HStack align="flex-start" justify="space-between" spacing={4} mb={2}>
        <HStack align="baseline" spacing={3} minW={0}>
          <Text fontSize="13px" fontWeight={700} color="text.subtle" w="22px" flexShrink={0}>
            {entry.rank}.
          </Text>
          <Box minW={0}>
            <Text fontSize="16px" fontWeight={700} color="text.primary">
              {entry.company}
              {entry.ticker && (
                <Text as="span" fontSize="13px" color="text.subtle" fontWeight={500}>
                  {" "}· {entry.ticker}
                </Text>
              )}
            </Text>
            <HStack spacing={3} mt={0.5}>
              {entry.areas.map((a) => (
                <Text key={a} fontSize="11.5px" color="text.subtle">{a}</Text>
              ))}
            </HStack>
          </Box>
        </HStack>
        <HStack spacing={3} flexShrink={0}>
          {entry.high_priority_count > 0 && (
            <Box px={2} py={0.5} borderRadius="6px" bg="rgba(220,38,38,0.10)"
              color="priority.high" fontSize="10px" fontWeight={700}>
              {entry.high_priority_count} HIGH
            </Box>
          )}
          {entry.delta_30d !== 0 && <DeltaPill delta={Math.round(entry.delta_30d)} />}
          <Text fontSize="18px" fontWeight={700} color="text.primary">
            {entry.score.toFixed(0)}
            <Text as="span" fontSize="12px" color="text.subtle" fontWeight={500}>/100</Text>
          </Text>
        </HStack>
      </HStack>

      <Text fontSize="14px" color="text.secondary" lineHeight={1.6}>{entry.rationale}</Text>

      {/* The 'next action' the use case asks for — rule-derived, so an analyst who
          disagrees can see which condition produced it. */}
      <Box mt={3} px={3.5} py={2.5} bg="rgba(109,94,252,0.07)" borderLeft="3px solid"
        borderColor="accent.iris" borderRadius="8px">
        <Text fontSize="10px" fontWeight={700} letterSpacing="0.06em" color="accent.iris"
          textTransform="uppercase" mb={1}>
          Next action
        </Text>
        <Text fontSize="13.5px" color="text.secondary" lineHeight={1.55}>{entry.next_action}</Text>
      </Box>

      {entry.evidence.length > 0 && (
        <Box mt={3}>
          <Text fontSize="10px" fontWeight={700} letterSpacing="0.06em" color="text.subtle"
            textTransform="uppercase" mb={1.5}>
            Evidence
          </Text>
          <VStack align="stretch" spacing={1.5}>
            {entry.evidence.map((ev) => (
              <Link key={ev.id} href={ev.url} isExternal data-testid="briefing-evidence-link"
                fontSize="13px" color="text.secondary" display="flex" alignItems="baseline"
                gap={2} _hover={{ color: "accent.iris" }}>
                <Box as={LuExternalLink} boxSize="11px" flexShrink={0} mt="3px" />
                <Text noOfLines={1}>{ev.title}</Text>
                <Text fontSize="11.5px" color="text.subtle" flexShrink={0}>
                  {ev.type} · {ev.score.toFixed(0)} · {shortDate(ev.published)}
                </Text>
              </Link>
            ))}
          </VStack>
        </Box>
      )}

      <Text mt={3} fontSize="11.5px" color="text.subtle">
        Sources consulted:{" "}
        {entry.sources_consulted
          .map((s) => SOURCE_LABEL[s as ScoutSource] ?? s)
          .join(" · ") || "none"}
      </Text>
    </Card>
  );
}

export function BriefingView() {
  const router = useRouter();
  const { data, loading } = useScoutData<BriefingResponse>("/api/atlas/scout/briefing");
  const { run, pending } = useScoutAction();

  async function publish() {
    const result = await run("/api/atlas/scout/briefing");
    // Publishing hands the briefing to the existing artifact path, which is what
    // gives it a shareable URL and Word/PDF export without a second renderer.
    if (result?.id) router.push(`/a/${result.id}`);
  }

  const entries = data?.companies ?? [];

  return (
    <PageContainer>
      <PageHeader title="Partnership briefing"
        subtitle="Companies ranked by the evidence gathered this period, each with a rationale, the sources consulted, and a recommended next action."
        action={
          <Button size="sm" onClick={publish} isLoading={pending} loadingText="Publishing"
            data-testid="publish-briefing"
            leftIcon={<Box as={LuShare2} boxSize="14px" />}
            isDisabled={loading || entries.length === 0}>
            Publish & share
          </Button>
        } />

      {loading && (
        <Card px={5} py={10}>
          <HStack justify="center" spacing={3} data-testid="loading">
            <Spinner size="sm" color="accent.iris" />
            <Text fontSize="sm" color="text.muted">Building the briefing…</Text>
          </HStack>
        </Card>
      )}

      {!loading && data?.degraded && (
        <HStack mb={4} px={4} py={3} bg="rgba(217,119,6,0.10)" borderLeft="3px solid"
          borderColor="priority.med" borderRadius="10px" spacing={2.5}
          data-testid="degraded-banner">
          <Box as={LuTriangleAlert} color="priority.med" boxSize="16px" />
          <Text fontSize="13.5px" color="text.secondary">
            Scanning service unavailable — no briefing could be built. {data.reason}
          </Text>
        </HStack>
      )}

      {!loading && !data?.degraded && (
        <>
          <HStack mb={5} spacing={5} flexWrap="wrap" data-testid="briefing-summary">
            <Text fontSize="13px" color="text.muted">
              <b>{data?.totals.signals ?? 0}</b> signals · <b>{data?.totals.high ?? 0}</b> high
              priority · <b>{data?.totals.companies_tracked ?? 0}</b> companies tracked
            </Text>
            {data?.generated_at && (
              <Text fontSize="13px" color="text.subtle">
                Generated {relativeDay(data.generated_at)}
              </Text>
            )}
          </HStack>

          {/* Honesty about a short list, rather than padding it to the target. */}
          {data?.below_target && entries.length > 0 && (
            <HStack mb={4} px={4} py={3} bg="bg.subtle" borderLeft="3px solid"
              borderColor="border.strong" borderRadius="10px" data-testid="below-target">
              <Text fontSize="13.5px" color="text.muted">
                Only {data.company_count} companies cleared the scoring threshold this period
                (the target is 8–12). The list is short because the evidence was, not because
                the scan was incomplete.
              </Text>
            </HStack>
          )}

          <VStack align="stretch" spacing={4}>
            {entries.map((entry) => <Entry key={entry.company_id} entry={entry} />)}
          </VStack>

          {entries.length === 0 && (
            <Card px={5} py={10} textAlign="center" data-testid="empty-state">
              <Text color="text.muted" fontSize="sm">
                No companies have cleared the scoring threshold yet. Run a scan from the
                Radar to gather evidence.
              </Text>
              <Button mt={4} size="sm" variant="outline" borderColor="border.default"
                rightIcon={<Box as={LuArrowUpRight} boxSize="14px" />}
                onClick={() => router.push("/radar")}>
                Go to Radar
              </Button>
            </Card>
          )}

          {(data?.notable_unattributed?.length ?? 0) > 0 && (
            <Box mt={8}>
              <Divider borderColor="border.subtle" mb={4} />
              <Text fontSize="11px" fontWeight={700} letterSpacing="0.06em" color="text.subtle"
                textTransform="uppercase" mb={2.5}>
                Notable signals without a company attribution
              </Text>
              <VStack align="stretch" spacing={1.5}>
                {data!.notable_unattributed.map((item) => (
                  <Link key={item.id} href={item.url} isExternal fontSize="13.5px"
                    color="text.secondary" display="flex" alignItems="baseline" gap={2}
                    _hover={{ color: "accent.iris" }}>
                    <Box as={LuExternalLink} boxSize="11px" flexShrink={0} mt="3px" />
                    <Text noOfLines={1}>{item.title}</Text>
                    <Text fontSize="11.5px" color="text.subtle" flexShrink={0}>
                      {item.type} · {item.score.toFixed(0)}
                    </Text>
                  </Link>
                ))}
              </VStack>
            </Box>
          )}
        </>
      )}
    </PageContainer>
  );
}
