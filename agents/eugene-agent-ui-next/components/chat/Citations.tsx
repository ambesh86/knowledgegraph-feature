"use client";

import NextLink from "next/link";
import {
  Box,
  HStack,
  Text,
  Tooltip,
  VStack,
} from "@chakra-ui/react";
import { LuArrowUpRight, LuFileText, LuQuote } from "react-icons/lu";
import { evidenceLink } from "@/lib/atlas/evidence";
import { citationColor, type AnchoredCitation } from "@/lib/atlas/citations";

/**
 * Inline citation markers and the reference list they point at.
 *
 * Two problems this fixes, both reported from a real answer:
 *
 *  1. The answer carried nine evidence chips and no way to tell which claim any of
 *     them supported. A reader who wants to check one sentence had to open all nine.
 *  2. The chips were unnumbered, so the reference list could not be cross-referenced
 *     with anything.
 *
 * Now every passage has a number, the number appears as a small circle at the end of
 * the sentence it supports, and the same number and colour identify it in the
 * reference list. Clicking either opens the highlighted region of the source PDF.
 *
 * Colour is redundant with the number on purpose. It is a fast pairing cue for the
 * eye, never the only carrier of meaning — the number and the tooltip both work
 * without it, which matters for colour-blind readers and for print.
 */

interface MarkerProps {
  citations: AnchoredCitation[];
}

/**
 * A green numbered circle that links to the evidence it stands for.
 *
 * Extracted because the same object appears in three places — inline in the answer,
 * in the reference list, and on a cited document — and they have to look identical
 * or the number stops reading as one identity carried across the page.
 */
export function EvidenceNumber({
  n,
  href,
  label,
  dashed = false,
  size = "17px",
}: {
  n: number;
  href: string;
  label: string;
  /** Dashed ring = the anchor was inferred, not asserted by the model. */
  dashed?: boolean;
  size?: string;
}) {
  const color = citationColor(n);
  return (
    <Box
      as={NextLink}
      href={href}
      aria-label={label}
      data-testid="evidence-number"
      display="inline-flex"
      alignItems="center"
      justifyContent="center"
      minW={size}
      h={size}
      px="4px"
      borderRadius="full"
      bg={color.bg}
      color={color.fg}
      border="1px solid"
      borderColor={color.border}
      borderStyle={dashed ? "dashed" : "solid"}
      fontSize={`calc(${size} * 0.62)`}
      fontWeight={800}
      lineHeight="1"
      textDecoration="none"
      flexShrink={0}
      transition="transform 0.12s ease, box-shadow 0.12s ease, filter 0.12s ease"
      _hover={{
        transform: "translateY(-1px) scale(1.08)",
        filter: "brightness(1.06)",
        boxShadow: `0 2px 8px -2px ${color.border}`,
      }}
    >
      {n}
    </Box>
  );
}

/** The small numbered circle rendered inline, at the end of a supported claim. */
export function CitationMarkers({ citations }: MarkerProps) {
  if (!citations.length) return null;
  return (
    <Box as="span" display="inline-flex" gap="2px" ml="3px" verticalAlign="super">
      {citations.map((c) => {
        const why =
          c.origin === "label"
            ? "Cited directly by the model"
            : "Matched to this sentence by content overlap";
        return (
          <Tooltip
            key={`${c.item.docId}:${c.item.chunkId}`}
            hasArrow
            placement="top"
            openDelay={250}
            maxW="360px"
            label={
              <Box fontSize="xs" py={1}>
                <Text fontWeight={700} mb={0.5}>
                  {c.n}. {c.item.label}
                </Text>
                <Text opacity={0.85} mb={1}>
                  page {c.item.page + 1} · {why}
                </Text>
                <Text noOfLines={4} opacity={0.9}>
                  {c.item.snippet}
                </Text>
              </Box>
            }
          >
            <Box as="span" data-testid="citation-marker">
              <EvidenceNumber
                n={c.n}
                href={evidenceLink(c.item)}
                label={`Source ${c.n}: ${c.item.label}, page ${c.item.page + 1}`}
                // Dashed ring distinguishes an inferred anchor from one the model
                // asserted. The reader can see which claim is ours.
                dashed={c.origin === "matched"}
              />
            </Box>
          </Tooltip>
        );
      })}
    </Box>
  );
}

/**
 * The ordered reference list.
 *
 * Numbered to match the inline markers, so "where does claim 3 come from" is one
 * glance rather than nine clicks.
 */
export function EvidenceReferences({ citations }: { citations: AnchoredCitation[] }) {
  if (!citations.length) return null;
  const anchored = citations.filter((c) => c.origin !== "unanchored").length;

  return (
    <Box
      w="100%"
      mt={2}
      borderRadius="14px"
      border="1px solid"
      borderColor="border.subtle"
      bg="bg.panel"
      overflow="hidden"
    >
      <HStack
        px={4}
        py={2.5}
        borderBottom="1px solid"
        borderColor="border.subtle"
        bg="bg.subtle"
        justify="space-between"
      >
        <HStack spacing={2}>
          <Box as={LuQuote} boxSize="13px" color="text.subtle" aria-hidden />
          <Text
            fontSize="10.5px"
            fontWeight={800}
            letterSpacing="0.08em"
            textTransform="uppercase"
            color="text.secondary"
          >
            Source evidence · {citations.length}
          </Text>
        </HStack>
        {anchored > 0 && (
          <Text fontSize="10.5px" color="text.subtle">
            {anchored} linked to a specific claim
          </Text>
        )}
      </HStack>

      <VStack align="stretch" spacing={0}>
        {citations.map((c, i) => {
          const color = citationColor(c.n);
          return (
            <Box
              key={`${c.item.docId}:${c.item.chunkId}`}
              as={NextLink}
              href={evidenceLink(c.item)}
              data-testid="evidence-reference"
              px={4}
              py={3}
              borderTop={i ? "1px solid" : "none"}
              borderColor="border.subtle"
              textDecoration="none"
              role="group"
              display="block"
              position="relative"
              transition="background 0.12s ease"
              _hover={{ bg: "bg.hover" }}
            >
              {/* Colour rail, matching the inline marker for this number. */}
              <Box
                position="absolute"
                left={0}
                top={0}
                bottom={0}
                w="3px"
                bg={color.fg}
                opacity={0.85}
              />
              <HStack align="flex-start" spacing={3}>
                <Box
                  flexShrink={0}
                  minW="20px"
                  h="20px"
                  mt="1px"
                  px="5px"
                  borderRadius="full"
                  bg={color.bg}
                  color={color.fg}
                  border="1px solid"
                  borderColor={color.border}
                  borderStyle={c.origin === "matched" ? "dashed" : "solid"}
                  fontSize="11px"
                  fontWeight={800}
                  display="flex"
                  alignItems="center"
                  justifyContent="center"
                  lineHeight="1"
                >
                  {c.n}
                </Box>

                <Box minW={0} flex={1}>
                  <HStack spacing={2} mb={0.5} flexWrap="wrap">
                    <Text
                      fontSize="13px"
                      fontWeight={650}
                      color="text.primary"
                      noOfLines={1}
                      _groupHover={{ color: color.fg }}
                      transition="color 0.12s ease"
                    >
                      {c.item.label}
                    </Text>
                    <Box
                      px={1.5}
                      py="1px"
                      borderRadius="5px"
                      bg="bg.subtle"
                      color="text.muted"
                      fontSize="10px"
                      fontWeight={700}
                      flexShrink={0}
                    >
                      p.{c.item.page + 1}
                    </Box>
                  </HStack>
                  <Text fontSize="12.5px" color="text.muted" noOfLines={2} lineHeight={1.5}>
                    {c.item.snippet}
                  </Text>
                </Box>

                <HStack
                  spacing={1}
                  flexShrink={0}
                  color="text.subtle"
                  opacity={0}
                  _groupHover={{ opacity: 1, color: color.fg }}
                  transition="opacity 0.12s ease, color 0.12s ease"
                >
                  <Box as={LuFileText} boxSize="12px" aria-hidden />
                  <Box as={LuArrowUpRight} boxSize="13px" aria-hidden />
                </HStack>
              </HStack>
            </Box>
          );
        })}
      </VStack>
    </Box>
  );
}
