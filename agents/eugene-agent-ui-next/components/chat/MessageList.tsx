"use client";

import { useEffect, useRef } from "react";
import { Box, VStack } from "@chakra-ui/react";
import { Message } from "./Message";
import { EmptyState } from "./EmptyState";
import type { ChatMessage } from "@/lib/types";

interface Props {
  messages: ChatMessage[];
  onQuickStart?: (prompt: string) => void;
  onCitationClick?: (nodeId: string) => void;
}

export function MessageList({ messages, onQuickStart, onCitationClick }: Props) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  if (messages.length === 0) {
    return <EmptyState onQuickStart={onQuickStart} />;
  }

  return (
    <Box flex="1" overflowY="auto" px={{ base: 4, md: 8 }} py={6}>
      <VStack spacing={6} align="stretch" maxW="900px" mx="auto">
        {messages.map((m) => (
          <Message key={m.id} message={m} onCitationClick={onCitationClick} />
        ))}
        <div ref={endRef} />
      </VStack>
    </Box>
  );
}
