"use client";

import { HStack, Tag, TagLabel, TagLeftIcon, Text, Tooltip } from "@chakra-ui/react";
import { LuDatabase, LuGlobe, LuBookOpen, LuLayers } from "react-icons/lu";
import type { ToolSelection } from "@/lib/types";

const TOOLS: {
  id: ToolSelection;
  label: string;
  icon: typeof LuDatabase;
  hint: string;
}[] = [
  { id: "all_sources", label: "All Sources", icon: LuLayers, hint: "Cascades in order: Eugene (graph + vector, fused) → ClinicalTrials.gov → PubMed" },
  { id: "eugene", label: "Eugene KG", icon: LuDatabase, hint: "Internal knowledge graph (drugs, diseases, genes, trials, patents)" },
  { id: "http", label: "Web", icon: LuGlobe, hint: "Live internet — ClinicalTrials.gov, Google Patents, web pages" },
  { id: "pubmed", label: "PubMed", icon: LuBookOpen, hint: "Live biomedical literature — PubMed / Europe PMC" },
];

interface Props {
  value: ToolSelection[];
  onChange: (next: ToolSelection[]) => void;
}

/**
 * Source selector — behaves like a single-select tab strip. Picking a source
 * switches to ONLY that source, so "Web"/"PubMed" reliably run their live tools
 * instead of being mixed with (and overridden by) the Eugene graph.
 */
export function ToolChips({ value, onChange }: Props) {
  const active = value[0] ?? "eugene";
  const select = (id: ToolSelection) => onChange([id]); // exclusive: one source
  return (
    <HStack spacing={2} flexWrap="wrap">
      <Text fontSize="11px" color="text.subtle" fontWeight={500} mr={0.5}>
        Source
      </Text>
      {TOOLS.map((t) => {
        const isActive = active === t.id;
        return (
          <Tooltip key={t.id} label={t.hint} fontSize="xs" openDelay={400} placement="top">
            <Tag
              as="button"
              role="radio"
              aria-checked={isActive}
              onClick={() => select(t.id)}
              variant={isActive ? "solid" : "subtle"}
              colorScheme={isActive ? "accent" : "gray"}
              bg={isActive ? "accent.500" : "whiteAlpha.100"}
              color={isActive ? "white" : "text.muted"}
              borderRadius="full"
              px={3}
              py={1}
              fontSize="xs"
              cursor="pointer"
              _hover={{ opacity: 0.9, bg: isActive ? "accent.500" : "whiteAlpha.200" }}
              transition="all 120ms ease"
            >
              <TagLeftIcon as={t.icon} boxSize={3.5} />
              <TagLabel>{t.label}</TagLabel>
            </Tag>
          </Tooltip>
        );
      })}
    </HStack>
  );
}
