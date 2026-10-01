"use client";

import {
  Box,
  HStack,
  IconButton,
  Tag,
  Text,
  VStack,
} from "@chakra-ui/react";
import { LuX, LuCornerDownRight } from "react-icons/lu";
import type { GraphNode } from "@/lib/types";
import { colorForCategory } from "@/lib/graphExtractor";

interface Props {
  chain: GraphNode[];
  onClose: () => void;
  /** Render in-flow inside the Inspector rail (no absolute overlay/backdrop). */
  embedded?: boolean;
}

/**
 * Leaf → root evidence trace.
 *
 * `chain[0]` is the node the user clicked (leaf); subsequent entries are the
 * parent nodes whose tool-call brought the leaf into the graph. Each hop
 * carries the tool name + reconstructed Cypher so the user can audit *how*
 * the agent derived the fact.
 */
export function EvidencePanel({ chain, onClose, embedded }: Props) {
  if (chain.length === 0) return null;
  const containerProps = embedded
    ? ({ position: "relative", w: "100%", h: "100%", overflowY: "auto", bg: "transparent" } as const)
    : ({
        position: "absolute",
        top: 0,
        right: 0,
        bottom: 0,
        w: { base: "100%", md: "400px" },
        bg: "rgba(11,14,22,0.94)",
        backdropFilter: "saturate(160%) blur(22px)",
        borderLeft: "1px solid",
        borderColor: "border.muted",
        overflowY: "auto",
        zIndex: 3,
        boxShadow: "-24px 0 60px -40px rgba(0,0,0,0.6)",
      } as const);
  return (
    <Box {...containerProps}>
      <HStack
        justify="space-between"
        px={5}
        py={4}
        borderBottom="1px solid"
        borderColor="border.subtle"
        position="sticky"
        top={0}
        bg="rgba(11,14,22,0.96)"
      >
        <VStack align="flex-start" spacing={0}>
          <Text fontSize="sm" fontWeight={600}>
            Evidence Trace
          </Text>
          <Text fontSize="10px" color="text.muted">
            leaf → root · {chain.length} hop{chain.length > 1 ? "s" : ""}
          </Text>
        </VStack>
        <IconButton
          aria-label="Close"
          icon={<LuX />}
          size="xs"
          variant="ghost"
          color="text.muted"
          onClick={onClose}
        />
      </HStack>

      <VStack align="stretch" spacing={0} px={5} py={4}>
        {chain.map((n, i) => (
          <HStack key={`${n.id}-${i}`} align="flex-start" spacing={3}>
            <VStack spacing={0} align="center" minW="20px" pt={1}>
              <Box
                w="10px"
                h="10px"
                borderRadius="full"
                bg={colorForCategory(n.category)}
                border="2px solid"
                borderColor="bg.canvas"
                boxShadow="0 0 8px currentColor"
                color={colorForCategory(n.category)}
              />
              {i < chain.length - 1 && (
                <Box w="1px" h="36px" bg="border.muted" my={1} />
              )}
            </VStack>
            <VStack align="stretch" spacing={1.5} flex="1" pb={5}>
              <Text fontSize="sm" fontWeight={500} noOfLines={1}>
                {n.caption || n.id}
              </Text>
              <HStack spacing={2} flexWrap="wrap">
                <Tag size="sm" bg="whiteAlpha.100" color="text.muted" fontSize="10px">
                  {(n.category || "UNKNOWN").toLowerCase()}
                </Tag>
                <Text fontSize="10px" color="text.muted" fontFamily="mono">
                  {n.id}
                </Text>
              </HStack>
              {(n.provenance ?? []).slice(-2).map((p, j) => (
                <Box
                  key={j}
                  bg="surface.100"
                  border="1px solid"
                  borderColor="border.subtle"
                  borderRadius="md"
                  p={2.5}
                  mt={1}
                >
                  <HStack spacing={2} mb={1}>
                    <LuCornerDownRight size={12} color="var(--chakra-colors-text-muted)" />
                    <Text fontSize="10px" color="text.muted" textTransform="uppercase" letterSpacing="wider">
                      {p.source.replace("_", " ")}
                    </Text>
                    {p.toolName && (
                      <Tag size="sm" colorScheme="purple" bg="accent.800" color="accent.100" fontSize="10px">
                        {p.toolName}
                      </Tag>
                    )}
                  </HStack>
                  {p.cypherHint && (
                    <Box
                      as="pre"
                      bg="surface.0"
                      p={2}
                      borderRadius="sm"
                      fontSize="10px"
                      fontFamily="mono"
                      color="ink.100"
                      whiteSpace="pre-wrap"
                      wordBreak="break-all"
                    >
                      {p.cypherHint}
                    </Box>
                  )}
                </Box>
              ))}
            </VStack>
          </HStack>
        ))}
      </VStack>
    </Box>
  );
}
