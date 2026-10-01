"use client";

import { Box, Divider, HStack, Popover, PopoverArrow, PopoverBody, PopoverContent,
  PopoverTrigger, Text, VStack } from "@chakra-ui/react";
import { LuCalendarClock, LuTriangleAlert } from "react-icons/lu";
import {
  SOURCE_LABEL, absoluteDate, relativeDay,
  type FreshnessResponse, type ScoutSource,
} from "@/lib/atlas/scout";
import { useScoutData } from "@/hooks/useScout";

/**
 * The "as of" indicator, shown in the top bar on every page.
 *
 * Standard market-intelligence platforms (Bloomberg, PitchBook, FactSet) all lead with
 * an as-of date because the first question anyone asks of a competitive dashboard is
 * "how old is this?". Answering it in one glance, everywhere, is worth more than any
 * individual panel.
 *
 * Three distinct clocks are reported, and keeping them separate is the point:
 *
 *   1. **Today** — the platform's own date, so a screenshot is self-dating.
 *   2. **Last scanned** — when this service last looked.
 *   3. **Newest record per source** — extracted from the data itself.
 *
 * The third is the one a naive implementation leaves out, and it is the one that
 * actually indicates staleness. A panel can truthfully say "scanned 20 minutes ago"
 * while its newest paper is three weeks old; a reader seeing only the scan time would
 * conclude the field is quiet when really the search is stale. Both are shown.
 *
 * The chip turns amber when the newest signal in the whole corpus is older than
 * `STALE_AFTER_DAYS` — a real signal that something upstream has stopped flowing.
 */

const STALE_AFTER_DAYS = 14;

function daysSince(iso: string | null): number | null {
  if (!iso) return null;
  const t = Date.parse(iso.length <= 10 ? `${iso}T00:00:00Z` : iso);
  if (Number.isNaN(t)) return null;
  return Math.floor((Date.now() - t) / 86_400_000);
}

export function DataFreshness() {
  const { data } = useScoutData<FreshnessResponse>("/api/atlas/scout/freshness");

  // Render today's date even before the scanner answers — it never depends on a
  // network call, and a header that pops in late is worse than one that fills in.
  const today = data?.today ?? new Date().toISOString().slice(0, 10);
  const age = daysSince(data?.newest_signal_date ?? null);
  const stale = data ? age === null || age > STALE_AFTER_DAYS : false;
  const degraded = data?.degraded ?? false;

  const label = degraded
    ? `As of ${absoluteDate(today)}`
    : `As of ${absoluteDate(today)}`;

  return (
    <Popover trigger="hover" placement="bottom-end" openDelay={150} closeDelay={100}>
      <PopoverTrigger>
        <HStack
          spacing={1.5} px={2.5} py={1} borderRadius="full" cursor="default"
          data-testid="data-freshness"
          bg={stale || degraded ? "rgba(217,119,6,0.12)" : "bg.subtle"}
          color={stale || degraded ? "priority.med" : "text.subtle"}
          aria-label={`Data as of ${today}`}
        >
          <Box as={stale || degraded ? LuTriangleAlert : LuCalendarClock} boxSize="13px" />
          <Text fontSize="11.5px" fontWeight={600} whiteSpace="nowrap">{label}</Text>
        </HStack>
      </PopoverTrigger>

      <PopoverContent w="330px" bg="bg.panel" borderColor="border.default" boxShadow="card">
        <PopoverArrow bg="bg.panel" />
        <PopoverBody px={4} py={3.5}>
          <VStack align="stretch" spacing={2.5}>
            <HStack justify="space-between">
              <Text fontSize="11px" fontWeight={700} letterSpacing="0.06em"
                color="text.subtle" textTransform="uppercase">
                Data currency
              </Text>
              <Text fontSize="11.5px" color="text.subtle">{absoluteDate(today)}</Text>
            </HStack>

            {degraded ? (
              <Text fontSize="12.5px" color="priority.med">
                The scanning service is unreachable, so currency cannot be established.
              </Text>
            ) : (
              <>
                <VStack align="stretch" spacing={1}>
                  <HStack justify="space-between">
                    <Text fontSize="12.5px" color="text.muted">Last scanned</Text>
                    <Text fontSize="12.5px" color="text.secondary" fontWeight={600}
                      data-testid="freshness-last-scan">
                      {data?.last_scan?.started_at
                        ? relativeDay(data.last_scan.started_at)
                        : "never"}
                    </Text>
                  </HStack>
                  <HStack justify="space-between">
                    <Text fontSize="12.5px" color="text.muted">Next scan</Text>
                    <Text fontSize="12.5px" color="text.secondary" fontWeight={600}>
                      {data?.next_scan_at
                        ? `${absoluteDate(data.next_scan_at)}, ${String(data.schedule.hour).padStart(2, "0")}:${String(data.schedule.minute).padStart(2, "0")} ${data.schedule.timezone}`
                        : "—"}
                    </Text>
                  </HStack>
                  <HStack justify="space-between">
                    <Text fontSize="12.5px" color="text.muted">Newest record</Text>
                    <Text fontSize="12.5px" fontWeight={600}
                      color={stale ? "priority.med" : "text.secondary"}>
                      {data?.newest_signal_date ? absoluteDate(data.newest_signal_date) : "—"}
                      {age !== null && ` · ${age}d`}
                    </Text>
                  </HStack>
                </VStack>

                <Divider borderColor="border.subtle" />

                {/* Per-source dates, read off the records themselves. This is what
                    tells an analyst WHICH feed has gone quiet, rather than just that
                    something has. */}
                <Text fontSize="11px" fontWeight={700} letterSpacing="0.06em"
                  color="text.subtle" textTransform="uppercase">
                  Newest by source
                </Text>
                <VStack align="stretch" spacing={1} data-testid="freshness-sources">
                  {(data?.sources ?? []).map((s) => {
                    const sAge = daysSince(s.latest_published);
                    return (
                      <HStack key={s.source} justify="space-between">
                        <Text fontSize="12.5px" color="text.muted">
                          {SOURCE_LABEL[s.source as ScoutSource] ?? s.source}
                        </Text>
                        <HStack spacing={2}>
                          <Text fontSize="12.5px" color="text.secondary">
                            {absoluteDate(s.latest_published)}
                          </Text>
                          <Text fontSize="11px"
                            color={sAge !== null && sAge > STALE_AFTER_DAYS
                              ? "priority.med" : "text.subtle"}
                            w="34px" textAlign="right">
                            {sAge !== null ? `${sAge}d` : "—"}
                          </Text>
                        </HStack>
                      </HStack>
                    );
                  })}
                  {(data?.sources ?? []).length === 0 && (
                    <Text fontSize="12.5px" color="text.subtle">No data scanned yet.</Text>
                  )}
                </VStack>

                <Text fontSize="11px" color="text.subtle" lineHeight={1.45}>
                  Dates are taken from the source records, not from when we fetched
                  them. Patents publish on a grant lag of months to years.
                </Text>
              </>
            )}
          </VStack>
        </PopoverBody>
      </PopoverContent>
    </Popover>
  );
}
