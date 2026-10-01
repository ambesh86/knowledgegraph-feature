"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Box, Button, HStack, Spinner, Text } from "@chakra-ui/react";
import { LuArrowRight, LuSparkles } from "react-icons/lu";
import type { StatsResponse } from "@/lib/atlas/scout";
import { useScoutData } from "@/hooks/useScout";

/**
 * "Since you last looked" — real counts, from the scanner.
 *
 * This strip previously read "3 new signals, 2 score moves" as hardcoded text. That
 * is a worse failure than showing nothing: it is a specific, falsifiable claim about
 * the user's data that happened to be fiction, and it stayed constant no matter what
 * the corpus did.
 *
 * "Last looked" is the visit timestamp in localStorage, written on unmount. Counting
 * is on `detected_at` (when this scanner first saw a signal) rather than publication
 * date, because a paper published last week that we indexed this morning is genuinely
 * new *to the analyst* — which is the question the panel is answering.
 */

const STORAGE_KEY = "atlas:last-visit";

export function SinceYouLastLooked() {
  const router = useRouter();
  const [since, setSince] = useState<string | null>(null);

  useEffect(() => {
    // Read before writing: the value we want is the *previous* visit.
    let previous: string | null = null;
    try {
      previous = window.localStorage.getItem(STORAGE_KEY);
    } catch {
      // Private browsing or blocked storage. The panel degrades to a 24h window.
      previous = null;
    }
    setSince(previous ?? new Date(Date.now() - 86_400_000).toISOString());

    return () => {
      try {
        window.localStorage.setItem(STORAGE_KEY, new Date().toISOString());
      } catch {
        /* nothing to do; the panel simply falls back next time */
      }
    };
  }, []);

  const query = useMemo(
    () => (since ? `/api/atlas/scout/stats?since=${encodeURIComponent(since)}` : null),
    [since]
  );
  const { data, loading } = useScoutData<StatsResponse>(query);

  if (loading || !data) {
    return (
      <HStack mt={5} px={4} py={3} bg="bg.subtle" borderRadius="10px" spacing={2.5}>
        <Spinner size="xs" color="accent.iris" />
        <Text fontSize="14px" color="text.muted">Checking what changed…</Text>
      </HStack>
    );
  }

  // The scanner being unreachable is not something to paper over with a cheerful
  // zero — a zero here reads as "nothing happened", which we do not know.
  if (data.degraded) {
    return (
      <HStack mt={5} px={4} py={3} bg="bg.subtle" borderLeft="3px solid" borderColor="border.strong"
        borderRadius="10px" justify="space-between" data-testid="since-degraded">
        <Text fontSize="14px" color="text.muted">
          Could not reach the scanning service, so recent changes are unknown.
        </Text>
      </HStack>
    );
  }

  const newSignals = data.new_signals ?? 0;
  const newHigh = data.new_high_priority ?? 0;

  return (
    <HStack mt={5} px={4} py={3} bg="rgba(109,94,252,0.08)" borderLeft="3px solid"
      borderColor="accent.iris" borderRadius="10px" justify="space-between"
      data-testid="since-you-last-looked">
      <HStack spacing={2.5} color="text.secondary">
        <Box as={LuSparkles} color="accent.iris" boxSize="16px" />
        <Text fontSize="14px">
          {newSignals === 0 ? (
            <>Nothing new since you last looked · <b>{data.signal_count}</b> signals tracked</>
          ) : (
            <>
              Since you last looked: <b>{newSignals} new signal{newSignals === 1 ? "" : "s"}</b>
              {newHigh > 0 && <>, <b>{newHigh} high priority</b></>}
            </>
          )}
        </Text>
      </HStack>
      <Button size="sm" variant="ghost" color="accent.iris"
        rightIcon={<LuArrowRight size={14} />} onClick={() => router.push("/radar")}>
        Show me
      </Button>
    </HStack>
  );
}
