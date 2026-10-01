"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Box, HStack, Input, Spinner, Table, Tbody, Td, Text, Th, Thead, Tr, VStack,
} from "@chakra-ui/react";
import { LuTriangleAlert } from "react-icons/lu";
import {
  absoluteDate,
  relativeDay,
  type CompanyScore,
  type WatchlistResponse,
} from "@/lib/atlas/scout";
import { useScoutData } from "@/hooks/useScout";
import { PageContainer, PageHeader, DeltaPill, Card } from "@/components/atlas/ui";

/**
 * Watchlist — companies ranked by the evidence attributed to them.
 *
 * There is no separately-maintained company score here. Each row is derived from that
 * company's signals, so clicking through to the Radar always explains the number, and
 * the two screens cannot disagree.
 *
 * `Δ 30d` renders as "—" rather than "0" when no baseline snapshot exists yet. A zero
 * with an arrow claims the company held steady; on a two-day-old deployment that is
 * a statement nothing in the system could support.
 */

function ScoreBar({ score }: { score: number }) {
  return (
    <HStack spacing={2.5}>
      <Text fontWeight={700} fontSize="15px" color="text.primary" w="30px">
        {score.toFixed(0)}
      </Text>
      <Box w="56px" h="5px" bg="bg.subtle" borderRadius="full" overflow="hidden"
        display={{ base: "none", lg: "block" }}>
        <Box h="100%" w={`${Math.min(100, score)}%`}
          bg={score >= 80 ? "score.up" : score >= 70 ? "accent.iris" : "border.strong"}
          borderRadius="full" />
      </Box>
    </HStack>
  );
}

function hasBaseline(company: CompanyScore): boolean {
  return company.breakdown?.has_baseline === true;
}

export function WatchlistView() {
  const router = useRouter();
  const [search, setSearch] = useState("");

  const query = useMemo(() => {
    const p = new URLSearchParams({ limit: "200" });
    if (search.trim()) p.set("q", search.trim());
    return `/api/atlas/watchlist?${p}`;
  }, [search]);

  const { data, loading } = useScoutData<WatchlistResponse>(query);
  const companies = data?.companies ?? [];
  const degraded = data?.degraded ?? false;

  return (
    <PageContainer maxW="1180px">
      <PageHeader title="Watchlist"
        subtitle="Live-ranked partner portfolio. Every score is derived from the signals attributed to that company."
        action={
          <HStack spacing={3}>
            <Input size="sm" maxW="200px" borderRadius="8px" placeholder="Search companies"
              data-testid="watchlist-search"
              value={search} onChange={(e) => setSearch(e.target.value)} />
            <Box px={3} py={1.5} bg="bg.subtle" borderRadius="full" fontSize="13px"
              fontWeight={600} color="text.muted" data-testid="company-count">
              {data?.total ?? 0} companies
            </Box>
          </HStack>
        } />

      {degraded && (
        <HStack mb={4} px={4} py={3} bg="rgba(217,119,6,0.10)" borderLeft="3px solid"
          borderColor="priority.med" borderRadius="10px" spacing={2.5} data-testid="degraded-banner">
          <Box as={LuTriangleAlert} color="priority.med" boxSize="16px" />
          <Text fontSize="13.5px" color="text.secondary">
            Scanning service unavailable — the watchlist is empty because it could not
            be loaded, not because no companies are tracked.
          </Text>
        </HStack>
      )}

      <Card overflow="hidden">
        {loading ? (
          <HStack px={5} py={10} justify="center" spacing={3} data-testid="loading">
            <Spinner size="sm" color="accent.iris" />
            <Text fontSize="sm" color="text.muted">Loading watchlist…</Text>
          </HStack>
        ) : companies.length === 0 ? (
          <Box px={5} py={10} textAlign="center" color="text.muted" fontSize="sm"
            data-testid="empty-state">
            {degraded
              ? "No data available while the scanning service is unreachable."
              : search
                ? "No companies match that search."
                : "No companies tracked yet. Run a scan from the Radar to populate this list."}
          </Box>
        ) : (
          <Table variant="unstyled" size="md">
            <Thead>
              <Tr borderBottom="1px solid" borderColor="border.subtle">
                <Th color="text.subtle" fontSize="11px" letterSpacing="0.05em" py={3.5}>Company</Th>
                <Th color="text.subtle" fontSize="11px">Score</Th>
                <Th color="text.subtle" fontSize="11px">Δ 30d</Th>
                <Th color="text.subtle" fontSize="11px">Signals</Th>
                <Th color="text.subtle" fontSize="11px" display={{ base: "none", md: "table-cell" }}>
                  Areas
                </Th>
                <Th color="text.subtle" fontSize="11px" display={{ base: "none", lg: "table-cell" }}>
                  Last signal
                </Th>
              </Tr>
            </Thead>
            <Tbody>
              {companies.map((c) => (
                <Tr key={c.id} borderBottom="1px solid" borderColor="border.subtle"
                  _hover={{ bg: "bg.subtle" }} cursor="pointer" transition="background 0.1s"
                  data-testid="company-row"
                  onClick={() => router.push(`/radar?company=${encodeURIComponent(c.id)}`)}>
                  <Td py={3.5}>
                    <VStack align="flex-start" spacing={0}>
                      <Text fontSize="14.5px" fontWeight={600} color="text.primary">{c.name}</Text>
                      <Text fontSize="12px" color="text.subtle">
                        {[c.ticker, c.cik ? `CIK ${c.cik}` : null].filter(Boolean).join(" · ") || "—"}
                      </Text>
                    </VStack>
                  </Td>
                  <Td><ScoreBar score={c.score} /></Td>
                  <Td>
                    {hasBaseline(c)
                      ? <DeltaPill delta={Math.round(c.delta_30d)} />
                      : <Text fontSize="13px" color="text.subtle" title="No 30-day baseline yet">—</Text>}
                  </Td>
                  <Td>
                    <HStack spacing={2}>
                      <Text fontSize="13px" color="text.secondary" fontWeight={600}>
                        {c.signal_count}
                      </Text>
                      {c.high_priority_count > 0 && (
                        <Box px={1.5} py={0.5} borderRadius="4px" bg="rgba(220,38,38,0.10)"
                          color="priority.high" fontSize="10px" fontWeight={700}>
                          {c.high_priority_count} HIGH
                        </Box>
                      )}
                    </HStack>
                  </Td>
                  <Td display={{ base: "none", md: "table-cell" }}>
                    <HStack spacing={1.5}>
                      {c.areas.slice(0, 2).map((a) => (
                        <Box key={a} px={2} py={0.5} bg="bg.subtle" borderRadius="6px"
                          fontSize="11.5px" color="text.muted">{a}</Box>
                      ))}
                      {c.areas.length > 2 && (
                        <Text fontSize="11.5px" color="text.subtle">+{c.areas.length - 2}</Text>
                      )}
                    </HStack>
                  </Td>
                  <Td display={{ base: "none", lg: "table-cell" }}>
                    <Text fontSize="13px" color="text.muted"
                      title={`Last signal ${absoluteDate(c.last_signal_at)}`}>
                      {absoluteDate(c.last_signal_at)}
                    </Text>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Card>
    </PageContainer>
  );
}
