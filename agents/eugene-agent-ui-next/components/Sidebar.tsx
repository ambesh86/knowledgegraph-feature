"use client";

import {
  Box,
  Button,
  Divider,
  Heading,
  HStack,
  IconButton,
  Tag,
  Text,
  Tooltip,
  VStack,
  useColorMode,
} from "@chakra-ui/react";
import {
  LuSparkles,
  LuRefreshCw,
  LuCircleDot,
  LuSun,
  LuMoon,
} from "react-icons/lu";

interface Props {
  conversationId: string;
  messageCount: number;
  graphNodeCount: number;
  tokenReady: boolean;
  onNewConversation: () => void;
}

export function Sidebar({
  conversationId,
  messageCount,
  graphNodeCount,
  tokenReady,
  onNewConversation,
}: Props) {
  const { colorMode, toggleColorMode } = useColorMode();
  return (
    <VStack
      h="100%"
      align="stretch"
      spacing={4}
      p={5}
      bg="bg.panel"
      borderRight="1px solid"
      borderColor="border.subtle"
      minW="260px"
      maxW="260px"
    >
      <HStack spacing={2} justify="space-between">
        <HStack spacing={2}>
          <Box
            w="32px"
            h="32px"
            borderRadius="10px"
            bgGradient="linear(135deg, accent.400, lumen.500)"
            display="flex"
            alignItems="center"
            justifyContent="center"
            boxShadow="0 8px 22px -10px rgba(58,79,247,0.65)"
          >
            <LuSparkles color="white" size={16} />
          </Box>
          <VStack align="flex-start" spacing={0}>
            <Heading size="sm" fontWeight={600}>
              Eugene
            </Heading>
            <Text fontSize="10px" color="text.muted">
              Biomedical Agent · v2
            </Text>
          </VStack>
        </HStack>
        <Tooltip
          label={`Switch to ${colorMode === "dark" ? "light" : "dark"} mode`}
          fontSize="xs"
        >
          <IconButton
            aria-label="Toggle color mode"
            icon={colorMode === "dark" ? <LuSun /> : <LuMoon />}
            onClick={toggleColorMode}
            size="sm"
            variant="ghost"
            color="text.muted"
            _hover={{ bg: "whiteAlpha.100", color: "text.primary" }}
          />
        </Tooltip>
      </HStack>

      <Button
        leftIcon={<LuRefreshCw size={14} />}
        size="sm"
        variant="outline"
        borderColor="border.muted"
        color="text.primary"
        onClick={onNewConversation}
        _hover={{ bg: "whiteAlpha.100" }}
      >
        New conversation
      </Button>

      <Divider borderColor="border.subtle" />

      <VStack align="stretch" spacing={3}>
        <Text fontSize="11px" color="text.muted" textTransform="uppercase" letterSpacing="wider">
          Session
        </Text>
        <StatRow label="messages" value={messageCount.toString()} />
        <StatRow label="graph nodes" value={graphNodeCount.toString()} />
        <StatRow
          label="conv. id"
          value={conversationId.slice(0, 8) + "…"}
          mono
        />
      </VStack>

      <Divider borderColor="border.subtle" />

      <VStack align="stretch" spacing={2}>
        <Text fontSize="11px" color="text.muted" textTransform="uppercase" letterSpacing="wider">
          Status
        </Text>
        <Tag
          size="sm"
          variant="subtle"
          bg="whiteAlpha.50"
          color={tokenReady ? "signal.success" : "signal.warning"}
          borderRadius="full"
          alignSelf="flex-start"
        >
          <LuCircleDot size={10} style={{ marginRight: 6 }} />
          <Text fontSize="xs">{tokenReady ? "authenticated" : "connecting…"}</Text>
        </Tag>
      </VStack>

      <Box flex="1" />

      <Text fontSize="10px" color="text.muted" opacity={0.7}>
        CSL Behring · Eugene Knowledge Graph · 44 node types · 31 rel. types
      </Text>
    </VStack>
  );
}

function StatRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <HStack justify="space-between" fontSize="13px">
      <Text color="text.muted">{label}</Text>
      <Text fontFamily={mono ? "mono" : undefined} color="text.primary">
        {value}
      </Text>
    </HStack>
  );
}
