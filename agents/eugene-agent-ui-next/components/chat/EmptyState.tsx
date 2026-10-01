"use client";

import {
  Box,
  Grid,
  Heading,
  HStack,
  Icon,
  Text,
  VStack,
} from "@chakra-ui/react";
import { LuPill, LuActivity, LuDna, LuBuilding2 } from "react-icons/lu";

// Curated starter prompts that play to the agent's strengths: each names ONE
// entity and asks for a bounded, graph-backed answer. We deliberately avoid
// "every / all / within N hops" phrasings — those make the agent fetch huge
// neighbourhoods that overflow the model's context and stall the graph view.
const SAMPLES: { title: string; prompt: string; icon: typeof LuPill }[] = [
  {
    title: "Drug aliases",
    prompt: "What are the known aliases for the drug Adderall?",
    icon: LuPill,
  },
  {
    title: "Drug indications",
    prompt: "What diseases is emicizumab indicated for?",
    icon: LuActivity,
  },
  {
    title: "Protein connections",
    prompt: "What is the protein Factor VIII directly connected to in the graph?",
    icon: LuDna,
  },
  {
    title: "Company portfolio",
    prompt: "Which drugs does the organization CSL Behring have in the Eugene graph?",
    icon: LuBuilding2,
  },
];

export function EmptyState({
  onQuickStart,
}: {
  onQuickStart?: (prompt: string) => void;
}) {
  return (
    <VStack
      flex="1"
      align="center"
      justify="center"
      px={6}
      py={12}
      spacing={6}
      textAlign="center"
      maxW="860px"
      mx="auto"
    >
      <Box
        w="120px"
        h="120px"
        borderRadius="full"
        bgGradient="radial(accent.400, accent.700 60%, transparent 75%)"
        filter="blur(0.5px)"
        sx={{
          animation: "pulse 3s ease-in-out infinite",
          "@keyframes pulse": {
            "0%,100%": { opacity: 0.6, transform: "scale(1)" },
            "50%": { opacity: 0.95, transform: "scale(1.04)" },
          },
        }}
      />
      <VStack spacing={2}>
        <Heading size="lg" fontWeight={600}>
          Ask Eugene
        </Heading>
        <Text color="text.muted" maxW="560px">
          Ask about a specific drug, gene/protein, disease, clinical trial,
          patent, or organization in the Eugene knowledge graph. The agent
          answers from the graph and its reasoning path appears as a live
          context graph on the right. Tip: name one entity per question for the
          best results.
        </Text>
      </VStack>
      <Grid
        templateColumns={{ base: "1fr", md: "1fr 1fr" }}
        gap={3}
        w="100%"
        maxW="640px"
        pt={4}
      >
        {SAMPLES.map((s) => (
          <HStack
            key={s.title}
            as="button"
            onClick={() => onQuickStart?.(s.prompt)}
            align="flex-start"
            p={4}
            spacing={3}
            bg="bg.glass"
            border="1px solid"
            borderColor="border.subtle"
            borderRadius="xl"
            textAlign="left"
            transition="all 150ms ease"
            _hover={{
              borderColor: "accent.400",
              transform: "translateY(-1px)",
              boxShadow: "0 12px 28px -18px rgba(58,79,247,0.55)",
            }}
          >
            <Icon as={s.icon} boxSize={5} color="accent.300" />
            <VStack align="flex-start" spacing={1}>
              <Text fontWeight={500} fontSize="sm">
                {s.title}
              </Text>
              <Text fontSize="xs" color="text.muted" noOfLines={2}>
                {s.prompt}
              </Text>
            </VStack>
          </HStack>
        ))}
      </Grid>
    </VStack>
  );
}
