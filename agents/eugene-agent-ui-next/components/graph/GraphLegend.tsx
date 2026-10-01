"use client";

import { Box, HStack, Text, Wrap, WrapItem } from "@chakra-ui/react";
import { colorForCategory } from "@/lib/graphExtractor";
import type { ContextGraph } from "@/lib/types";

const DEFAULT_CATEGORIES = [
  "DRUG",
  "DISEASE",
  "GENE_PROTEIN",
  "PATHWAY",
  "CLINICAL_TRIAL",
  "PATENT",
  "ORGANIZATION",
  "PUBMED_DOCUMENT",
  "CONDITION",
  "INTERVENTION",
];

interface LegendProps {
  /** When provided, the colour legend reflects only the categories present,
   *  each annotated with its live count — so the legend matches the graph. */
  graph?: ContextGraph;
}

const SHAPES: { key: string; label: string; svg: React.ReactNode }[] = [
  {
    key: "ellipse",
    label: "individual",
    svg: (
      <svg width="12" height="12" viewBox="0 0 12 12">
        <circle cx="6" cy="6" r="5" fill="#aeb7cc" />
      </svg>
    ),
  },
  {
    key: "square",
    label: "organization",
    svg: (
      <svg width="12" height="12" viewBox="0 0 12 12">
        <rect x="1" y="1" width="10" height="10" rx="2" fill="#aeb7cc" />
      </svg>
    ),
  },
  {
    key: "diamond",
    label: "document / patent",
    svg: (
      <svg width="12" height="12" viewBox="0 0 12 12">
        <path d="M6 1 L11 6 L6 11 L1 6 Z" fill="#aeb7cc" />
      </svg>
    ),
  },
  {
    key: "hexagon",
    label: "trial / phase",
    svg: (
      <svg width="12" height="12" viewBox="0 0 12 12">
        <path d="M3 1 L9 1 L11 6 L9 11 L3 11 L1 6 Z" fill="#aeb7cc" />
      </svg>
    ),
  },
];

export function GraphLegend({ graph }: LegendProps) {
  // Present categories (with counts) when a graph is supplied; else the default
  // reference palette.
  const counts = new Map<string, number>();
  for (const n of graph?.nodes ?? []) {
    const c = (n.category ?? "UNKNOWN").toUpperCase();
    counts.set(c, (counts.get(c) ?? 0) + 1);
  }
  const categories =
    counts.size > 0
      ? [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([c]) => c)
      : DEFAULT_CATEGORIES;

  return (
    <Box px={4} py={2.5}>
      <HStack spacing={2} mb={1.5} align="center">
        <Text fontSize="10px" color="text.muted" textTransform="uppercase" letterSpacing="wider" minW="48px">
          shapes
        </Text>
        <Wrap spacing={3}>
          {SHAPES.map((s) => (
            <WrapItem key={s.key}>
              <HStack spacing={1.5}>
                {s.svg}
                <Text fontSize="10px" color="text.muted">
                  {s.label}
                </Text>
              </HStack>
            </WrapItem>
          ))}
        </Wrap>
      </HStack>
      <HStack spacing={2} align="center">
        <Text fontSize="10px" color="text.muted" textTransform="uppercase" letterSpacing="wider" minW="48px">
          colors
        </Text>
        <Wrap spacing={3}>
          {categories.map((c) => (
            <WrapItem key={c}>
              <HStack spacing={1.5}>
                <Box
                  w="9px"
                  h="9px"
                  borderRadius="full"
                  bg={colorForCategory(c)}
                  boxShadow="0 0 6px currentColor"
                />
                <Text fontSize="10px" color="text.muted">
                  {c.replace(/_/g, " ").toLowerCase()}
                  {counts.has(c) && (
                    <Text as="span" color="text.subtle" ml={1}>
                      {counts.get(c)}
                    </Text>
                  )}
                </Text>
              </HStack>
            </WrapItem>
          ))}
        </Wrap>
      </HStack>
    </Box>
  );
}
