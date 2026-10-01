"use client";

import { Box, Heading, HStack, Text } from "@chakra-ui/react";
import { LuArrowUp, LuArrowDown } from "react-icons/lu";
import type { Priority } from "@/lib/atlas/seed";

/** Centered content column used by every view. */
export function PageContainer({ children, maxW = "1080px" }: { children: React.ReactNode; maxW?: string }) {
  return (
    <Box px={{ base: 5, md: 8 }} py={{ base: 6, md: 8 }} maxW={maxW} mx="auto" w="100%">
      {children}
    </Box>
  );
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <HStack justify="space-between" align="flex-start" mb={6} spacing={4}>
      <Box>
        <Heading size="lg" fontWeight={700} letterSpacing="-0.02em" color="text.primary">
          {title}
        </Heading>
        {subtitle && (
          <Text color="text.muted" mt={1.5} fontSize="15px" maxW="640px">
            {subtitle}
          </Text>
        )}
      </Box>
      {action}
    </HStack>
  );
}

export function SectionLabel({ children, count }: { children: React.ReactNode; count?: React.ReactNode }) {
  return (
    <HStack spacing={2} mb={3}>
      <Text fontSize="11px" fontWeight={700} letterSpacing="0.08em" color="text.subtle" textTransform="uppercase">
        {children}
      </Text>
      {count != null && <Text fontSize="11px" color="text.subtle">· {count}</Text>}
    </HStack>
  );
}

const PRIORITY_STYLE: Record<Priority, { bg: string; color: string; label: string }> = {
  high: { bg: "rgba(220,38,38,0.10)", color: "priority.high", label: "HIGH" },
  med: { bg: "rgba(217,119,6,0.12)", color: "priority.med", label: "MED" },
  watch: { bg: "bg.subtle", color: "priority.low", label: "WATCH" },
};

export function PriorityBadge({ priority }: { priority: Priority }) {
  const s = PRIORITY_STYLE[priority];
  return (
    <Box bg={s.bg} color={s.color} px={2} py={0.5} borderRadius="6px" fontSize="10px" fontWeight={700}
      letterSpacing="0.04em">
      {s.label}
    </Box>
  );
}

/** Score move: "76 › 84  +8" with directional color. */
export function ScoreDelta({ from, to }: { from?: number; to?: number }) {
  if (from == null || to == null) return null;
  const delta = to - from;
  const up = delta >= 0;
  return (
    <HStack spacing={1.5} fontSize="12px" color="text.muted">
      <Text>Score</Text>
      <Text color="text.subtle">{from}</Text>
      <Text color="text.subtle">›</Text>
      <Text fontWeight={600} color="text.primary">{to}</Text>
      <HStack spacing={0.5} color={up ? "score.up" : "score.down"} fontWeight={700}>
        <Box as={up ? LuArrowUp : LuArrowDown} boxSize="12px" />
        <Text>{up ? "+" : ""}{delta}</Text>
      </HStack>
    </HStack>
  );
}

export function DeltaPill({ delta }: { delta: number }) {
  const up = delta >= 0;
  return (
    <HStack spacing={0.5} color={up ? "score.up" : "score.down"} fontWeight={700} fontSize="13px">
      <Box as={up ? LuArrowUp : LuArrowDown} boxSize="13px" />
      <Text>{up ? "+" : ""}{delta}</Text>
    </HStack>
  );
}

export function Card({ children, ...rest }: React.ComponentProps<typeof Box>) {
  return (
    <Box bg="bg.panel" border="1px solid" borderColor="border.subtle" borderRadius="card"
      boxShadow="card" {...rest}>
      {children}
    </Box>
  );
}
