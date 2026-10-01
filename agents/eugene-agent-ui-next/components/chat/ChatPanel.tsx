"use client";

import { useRef } from "react";
import { Alert, AlertIcon, Box, Flex } from "@chakra-ui/react";
import { MessageList } from "./MessageList";
import { Composer } from "./Composer";
import type { ChatMessage, ToolSelection } from "@/lib/types";

interface Props {
  messages: ChatMessage[];
  pending: boolean;
  ready: boolean;
  error: string | null;
  onSend: (prompt: string, tools: ToolSelection[]) => void;
  onCancel: () => void;
  onCitationClick?: (nodeId: string) => void;
}

export function ChatPanel({
  messages,
  pending,
  ready,
  error,
  onSend,
  onCancel,
  onCitationClick,
}: Props) {
  const pendingToolsRef = useRef<ToolSelection[]>(["eugene"]);
  return (
    <Flex direction="column" h="100%" minW={0} flex="1">
      {error && (
        <Alert
          status="error"
          bg="signal.danger"
          color="white"
          variant="solid"
          borderRadius={0}
          fontSize="sm"
        >
          <AlertIcon />
          {error}
        </Alert>
      )}
      <Box flex="1" display="flex" flexDir="column" minH={0}>
        <MessageList
          messages={messages}
          onQuickStart={(p) => onSend(p, pendingToolsRef.current)}
          onCitationClick={onCitationClick}
        />
      </Box>
      <Composer
        onSend={(p, tools) => {
          pendingToolsRef.current = tools;
          onSend(p, tools);
        }}
        onCancel={onCancel}
        pending={pending}
        disabled={!ready}
      />
    </Flex>
  );
}
