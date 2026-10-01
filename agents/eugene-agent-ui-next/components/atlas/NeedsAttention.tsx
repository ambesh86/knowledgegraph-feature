"use client";

import { useRouter } from "next/navigation";
import { Box, Button, HStack, Spinner, Text } from "@chakra-ui/react";
import { LuClock } from "react-icons/lu";
import { relativeDay, topFactors, factorLabel, type SignalsResponse } from "@/lib/atlas/scout";
import { useScoutData } from "@/hooks/useScout";
import { SectionLabel, PriorityBadge, Card } from "@/components/atlas/ui";

/**
 * "Needs your attention" — the top-scoring live signals.
 *
 * Requests high and medium priority only, ranked, capped at three. The cap is a
 * product decision rather than a technical one: a daily briefing that opens with
 * twenty items is a list nobody triages, and the full set is one click away on Radar.
 */
export function NeedsAttention() {
  const router = useRouter();
  const { data, loading } = useScoutData<SignalsResponse>(
    "/api/atlas/signals?priority=high&limit=3"
  );

  const highs = data?.signals ?? [];
  // High priority alone can legitimately be empty on a quiet day; medium is the
  // honest fallback rather than padding the section with watch-tier noise.
  const { data: medium } = useScoutData<SignalsResponse>(
    highs.length === 0 && !loading ? "/api/atlas/signals?priority=med&limit=3" : null
  );

  const signals = highs.length > 0 ? highs : (medium?.signals ?? []);
  const degraded = data?.degraded ?? false;

  if (loading) {
    return (
      <Box mt={8}>
        <SectionLabel>Needs your attention</SectionLabel>
        <Card px={5} py={8}>
          <HStack justify="center" spacing={3}>
            <Spinner size="sm" color="accent.iris" />
            <Text fontSize="sm" color="text.muted">Loading signals…</Text>
          </HStack>
        </Card>
      </Box>
    );
  }

  return (
    <Box mt={8}>
      <HStack justify="space-between" mb={3}>
        <SectionLabel count={`${signals.length} item${signals.length === 1 ? "" : "s"}`}>
          Needs your attention
        </SectionLabel>
        <Button size="xs" variant="ghost" color="text.muted" onClick={() => router.push("/radar")}>
          View all →
        </Button>
      </HStack>

      <Card overflow="hidden">
        {signals.map((s, i) => (
          <Box key={s.id} px={5} py={4} borderTop={i ? "1px solid" : "none"}
            borderColor="border.subtle" _hover={{ bg: "bg.subtle" }} cursor="pointer"
            transition="background 0.1s" data-testid="attention-item"
            onClick={() => router.push("/radar")}>
            <HStack align="flex-start" justify="space-between" spacing={4}>
              <HStack align="flex-start" spacing={3} flex={1} minW={0}>
                <Box w="7px" h="7px" mt="6px" borderRadius="full" flexShrink={0}
                  bg={s.priority === "high" ? "priority.high" : "priority.med"} />
                <Box minW={0}>
                  <Text fontSize="15px" fontWeight={600} color="text.primary">{s.title}</Text>
                  {s.company_name && (
                    <Text fontSize="12.5px" color="accent.iris" fontWeight={600} mt={0.5}>
                      {s.company_name}
                    </Text>
                  )}
                  <Text fontSize="13.5px" color="text.muted" mt={1} lineHeight={1.5} noOfLines={2}>
                    {s.rationale || s.summary}
                  </Text>
                  <HStack mt={2.5} spacing={4} flexWrap="wrap">
                    <HStack spacing={1.5} color="text.subtle" fontSize="12px">
                      <Box as={LuClock} boxSize="12px" />
                      <Text>{relativeDay(s.published)}</Text>
                    </HStack>
                    <Text fontSize="12px" color="text.muted">
                      <b>{s.score.toFixed(0)}</b>/100
                    </Text>
                    <Text fontSize="11.5px" color="text.subtle" noOfLines={1}>
                      {topFactors(s.score_breakdown).map((f) => factorLabel(f.name)).join(" · ")}
                    </Text>
                  </HStack>
                </Box>
              </HStack>
              <PriorityBadge priority={s.priority} />
            </HStack>
          </Box>
        ))}

        {signals.length === 0 && (
          <Box px={5} py={8} textAlign="center" color="text.muted" fontSize="sm">
            {degraded
              ? "Scanning service unavailable — priority signals could not be loaded."
              : "Nothing needs your attention right now."}
          </Box>
        )}
      </Card>
    </Box>
  );
}
