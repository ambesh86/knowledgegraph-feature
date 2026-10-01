"use client";

import { useEffect, useState } from "react";
import { HStack, Text, Tooltip, Box } from "@chakra-ui/react";
import { LuClock, LuTriangleAlert } from "react-icons/lu";
import { apiPath } from "@/lib/basePath";
import type { Freshness } from "@/app/api/atlas/freshness/route";

/**
 * "Data as of …" indicator.
 *
 * Answers carry two different dates and conflating them is how stale research
 * gets presented as current: live tool results are current as of TODAY, while
 * graph/vector facts are only as current as the last ingest. This shows both, and
 * warns when the snapshot has aged past a month.
 */
export function FreshnessBadge() {
  const [data, setData] = useState<Freshness | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(apiPath("/api/atlas/freshness"), { cache: "no-store" });
        if (!r.ok) return;
        const j = (await r.json()) as Freshness;
        if (!cancelled) setData(j);
      } catch {
        /* decorative — never surface a fetch error here */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!data) return null;

  const stale = data.stale === true;
  const snapshot = data.snapshot_date;
  const detail = [
    `Today: ${data.today}`,
    snapshot
      ? `Internal snapshot: ${snapshot}${data.age_days != null ? ` (${data.age_days}d old)` : ""}`
      : "Internal snapshot: unknown",
    ...data.sources.map(
      (s) =>
        `· ${s.source}: ${s.ingested_at?.slice(0, 10) ?? "?"}${
          s.record_count ? ` — ${s.record_count.toLocaleString()} records` : ""
        }`
    ),
    "Live sources (ClinicalTrials.gov, PubMed) are queried in real time.",
  ].join("\n");

  return (
    <Tooltip
      label={<Box whiteSpace="pre-line" fontSize="xs">{detail}</Box>}
      placement="bottom-end"
      openDelay={200}
      hasArrow
    >
      <HStack
        spacing={1.5}
        px={2}
        py={1}
        borderRadius="full"
        bg={stale ? "rgba(217,119,6,0.12)" : "bg.subtle"}
        color={stale ? "priority.med" : "text.subtle"}
        cursor="default"
        aria-label={`Data freshness. ${detail}`}
      >
        <Box as={stale ? LuTriangleAlert : LuClock} boxSize={3.5} aria-hidden />
        <Text fontSize="11.5px" fontWeight={600} whiteSpace="nowrap">
          Data as of {snapshot ?? data.today}
        </Text>
      </HStack>
    </Tooltip>
  );
}
