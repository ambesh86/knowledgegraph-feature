"use client";

import { Box, Grid, HStack, Text, VStack } from "@chakra-ui/react";
import { PROGRAMS } from "@/lib/atlas/seed";
import { PageContainer, PageHeader, Card } from "@/components/atlas/ui";

const PHASE_COLOR: Record<string, string> = {
  "Approved": "score.up", "Phase 3": "accent.iris", "Phase 2": "priority.med", "Phase 1": "text.muted",
};

export function ProgramsView() {
  return (
    <PageContainer maxW="1180px">
      <PageHeader title="Programs"
        subtitle="Strategic priorities and target product profiles, each linked to competitive context, recent signals, and watchlist activity." />
      <Grid templateColumns={{ base: "1fr", lg: "1fr 1fr" }} gap={5}>
        {PROGRAMS.map((p) => (
          <Card key={p.id} p={5} cursor="pointer" transition="all 0.12s"
            _hover={{ borderColor: "border.default", boxShadow: "pop", transform: "translateY(-1px)" }}>
            <HStack justify="space-between" align="flex-start" mb={2}>
              <Text fontSize="16px" fontWeight={700} color="text.primary" letterSpacing="-0.01em">{p.name}</Text>
              <Box px={2.5} py={1} borderRadius="full" bg="bg.subtle" fontSize="12px" fontWeight={700}
                color={PHASE_COLOR[p.phase] ?? "text.muted"} flexShrink={0}>{p.phase}</Box>
            </HStack>
            <Text fontSize="12.5px" color="text.subtle" fontWeight={500} mb={3}>{p.area} · {p.modality}</Text>
            <Text fontSize="14px" color="text.muted" lineHeight={1.55} mb={4}>{p.description}</Text>
            <HStack spacing={4} pt={3} borderTop="1px solid" borderColor="border.subtle">
              <HStack spacing={1.5}>
                <Text fontSize="14px" fontWeight={700} color="text.primary">{p.relatedSignals}</Text>
                <Text fontSize="13px" color="text.muted">related signals</Text>
              </HStack>
              <Box w="3px" h="3px" borderRadius="full" bg="border.strong" />
              <HStack spacing={1.5}>
                <Text fontSize="14px" fontWeight={700} color={p.highPriority ? "priority.high" : "text.primary"}>{p.highPriority}</Text>
                <Text fontSize="13px" color="text.muted">high priority</Text>
              </HStack>
            </HStack>
          </Card>
        ))}
      </Grid>
    </PageContainer>
  );
}
