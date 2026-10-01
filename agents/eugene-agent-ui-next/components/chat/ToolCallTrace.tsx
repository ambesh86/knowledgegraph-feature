"use client";

import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Badge,
  Box,
  HStack,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import type { ToolInvocation } from "@/lib/types";

// Utility tools that the agent might call but that don't answer the user's
// question. We hide them from the chat trace to reduce visual noise — they
// still appear in server logs for debugging.
const NOISE_TOOLS = new Set([
  "current_time",
  "calculator",
  "python_repl",
]);

export function ToolCallTrace({ calls }: { calls: ToolInvocation[] }) {
  const visible = calls.filter((c) => !NOISE_TOOLS.has(c.tool));
  if (visible.length === 0) return null;
  return (
    <Accordion allowToggle mt={1}>
      {visible.map((c) => (
        <AccordionItem
          key={c.toolId}
          border="1px solid"
          borderColor="border.subtle"
          borderRadius="lg"
          mb={1.5}
          bg="bg.glass"
          backdropFilter="blur(6px)"
        >
          <AccordionButton _hover={{ bg: "whiteAlpha.50" }} borderRadius="lg">
            <HStack flex="1" spacing={2} textAlign="left">
              {c.status === "pending" ? (
                <Spinner size="xs" color="accent.300" />
              ) : (
                <Box
                  w="8px"
                  h="8px"
                  borderRadius="full"
                  bg={c.status === "ok" ? "signal.success" : "signal.danger"}
                />
              )}
              <Text fontSize="xs" fontFamily="mono" color="text.primary">
                {c.tool}
              </Text>
              {c.endedAt && (
                <Badge
                  fontSize="10px"
                  colorScheme="gray"
                  bg="whiteAlpha.100"
                  color="text.muted"
                >
                  {Math.max(1, c.endedAt - c.startedAt)}ms
                </Badge>
              )}
            </HStack>
            <AccordionIcon color="text.muted" />
          </AccordionButton>
          <AccordionPanel pb={3}>
            <VStack align="stretch" spacing={2} fontSize="xs" fontFamily="mono">
              <Field label="input">{jsonPreview(c.input)}</Field>
              {c.output !== undefined && (
                <Field label="output">{jsonPreview(c.output)}</Field>
              )}
            </VStack>
          </AccordionPanel>
        </AccordionItem>
      ))}
    </Accordion>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <Box>
      <Text color="text.muted" mb={1} fontSize="10px" textTransform="uppercase" letterSpacing="wider">
        {label}
      </Text>
      <Box
        as="pre"
        bg="surface.0"
        p={2}
        borderRadius="md"
        color="ink.100"
        overflowX="auto"
        whiteSpace="pre-wrap"
        maxH="180px"
      >
        {children}
      </Box>
    </Box>
  );
}

function jsonPreview(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2).slice(0, 2000);
  } catch {
    return String(value);
  }
}
