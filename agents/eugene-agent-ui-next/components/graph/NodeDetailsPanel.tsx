"use client";

import { useEffect, useState } from "react";
import {
  Badge,
  Box,
  Divider,
  HStack,
  IconButton,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { LuX, LuCopy } from "react-icons/lu";
import { colorForCategory } from "@/lib/graphExtractor";
import { fetchNodeDetails } from "@/lib/graphApi";
import type { GraphNode } from "@/lib/types";

interface Props {
  node: GraphNode | null;
  onClose: () => void;
}

export function NodeDetailsPanel({ node, onClose }: Props) {
  const [remote, setRemote] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!node) {
      setRemote(null);
      return;
    }
    setRemote(null);
    // Skip fetching for synthetic "name:..." placeholder nodes
    if (node.id.startsWith("name:")) return;
    setLoading(true);
    fetchNodeDetails(node.id)
      .then((d) => setRemote(d))
      .catch(() => setRemote(null))
      .finally(() => setLoading(false));
  }, [node?.id]);

  if (!node) return null;

  const color = colorForCategory(node.category);
  const props = { ...(node.properties ?? {}), ...(remote ?? {}) };

  return (
    <Box
      position="absolute"
      top={0}
      right={0}
      bottom={0}
      w={{ base: "100%", md: "360px" }}
      bg="rgba(11,14,22,0.92)"
      backdropFilter="saturate(160%) blur(22px)"
      borderLeft="1px solid"
      borderColor="border.muted"
      overflowY="auto"
      zIndex={2}
      boxShadow="-24px 0 60px -40px rgba(0,0,0,0.6)"
    >
      <VStack align="stretch" spacing={0}>
        <HStack
          justify="space-between"
          px={5}
          py={4}
          borderBottom="1px solid"
          borderColor="border.subtle"
          position="sticky"
          top={0}
          bg="rgba(11,14,22,0.95)"
          zIndex={1}
        >
          <HStack spacing={3}>
            <Box w="12px" h="12px" borderRadius="full" bg={color} />
            <VStack align="flex-start" spacing={0}>
              <Text fontSize="sm" fontWeight={600} color="text.primary" noOfLines={1}>
                {node.caption || node.id}
              </Text>
              <Text fontSize="10px" color="text.muted" textTransform="uppercase" letterSpacing="wider">
                {(node.category || "UNKNOWN").replace(/_/g, " ").toLowerCase()}
              </Text>
            </VStack>
          </HStack>
          <IconButton
            aria-label="Close"
            icon={<LuX />}
            size="xs"
            variant="ghost"
            color="text.muted"
            onClick={onClose}
          />
        </HStack>

        <VStack align="stretch" px={5} py={4} spacing={4}>
          <Field label="node_id" value={node.id} copyable mono />
          {node.role && (
            <Field
              label="role"
              renderValue={() => (
                <Badge
                  colorScheme={
                    node.role === "source"
                      ? "blue"
                      : node.role === "sink"
                      ? "red"
                      : "yellow"
                  }
                  borderRadius="full"
                  px={2}
                  py={0.5}
                  fontSize="10px"
                >
                  {node.role}
                </Badge>
              )}
            />
          )}

          <Divider borderColor="border.subtle" />

          <Text fontSize="10px" color="text.muted" textTransform="uppercase" letterSpacing="wider">
            Properties
          </Text>
          {loading && <Spinner size="xs" color="accent.300" />}
          {Object.entries(props)
            .filter(([k]) => !["node_id", "id", "start_node_id", "end_node_id"].includes(k))
            .slice(0, 40)
            .map(([k, v]) => (
              <Field key={k} label={k} value={stringify(v)} mono small />
            ))}
        </VStack>
      </VStack>
    </Box>
  );
}

function Field({
  label,
  value,
  renderValue,
  copyable,
  mono,
  small,
}: {
  label: string;
  value?: string;
  renderValue?: () => React.ReactNode;
  copyable?: boolean;
  mono?: boolean;
  small?: boolean;
}) {
  return (
    <Box>
      <HStack justify="space-between" mb={1}>
        <Text fontSize="10px" color="text.muted" textTransform="uppercase" letterSpacing="wider">
          {label}
        </Text>
        {copyable && value && (
          <IconButton
            aria-label="Copy"
            size="xs"
            variant="ghost"
            icon={<LuCopy />}
            color="text.muted"
            onClick={() => navigator.clipboard?.writeText(value)}
          />
        )}
      </HStack>
      {renderValue ? (
        renderValue()
      ) : (
        <Text
          fontFamily={mono ? "mono" : undefined}
          fontSize={small ? "12px" : "13px"}
          color="text.primary"
          wordBreak="break-word"
          whiteSpace="pre-wrap"
        >
          {value ?? "—"}
        </Text>
      )}
    </Box>
  );
}

function stringify(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}
