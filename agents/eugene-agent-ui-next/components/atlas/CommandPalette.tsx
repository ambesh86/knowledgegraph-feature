"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Box,
  HStack,
  Input,
  Kbd,
  Modal,
  ModalBody,
  ModalContent,
  ModalOverlay,
  Text,
  VStack,
} from "@chakra-ui/react";
import { LuCornerDownLeft } from "react-icons/lu";
import { ALL_NAV } from "@/lib/atlas/nav";

const QUICK_ASKS = [
  "What do we know about emicizumab?",
  "Compare emicizumab and marstacimab",
  "What's new on Sangamo?",
  "Show me white space in nephrology",
];

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (path: string) => void;
}

export function CommandPalette({ isOpen, onClose, onNavigate }: Props) {
  const [q, setQ] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const results = useMemo(() => {
    const query = q.trim().toLowerCase();
    const nav = ALL_NAV.filter(
      (n) => !query || n.label.toLowerCase().includes(query) || n.hint.toLowerCase().includes(query)
    ).map((n) => ({ kind: "nav" as const, label: n.label, hint: n.hint, path: n.path }));

    const asks = (query ? QUICK_ASKS.filter((a) => a.toLowerCase().includes(query)) : QUICK_ASKS)
      .map((a) => ({ kind: "ask" as const, label: a, hint: "Ask CSL", path: `/ask?q=${encodeURIComponent(a)}` }));

    return [...nav, ...asks];
  }, [q]);

  useEffect(() => {
    if (isOpen) {
      setQ("");
      setCursor(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [isOpen]);

  useEffect(() => setCursor(0), [q]);

  function onKey(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") { e.preventDefault(); setCursor((c) => Math.min(c + 1, results.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setCursor((c) => Math.max(c - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); const r = results[cursor]; if (r) onNavigate(r.path); }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered motionPreset="scale">
      <ModalOverlay bg="blackAlpha.500" backdropFilter="blur(2px)" />
      <ModalContent bg="bg.panel" borderRadius="16px" boxShadow="pop" mx={4} mt="12vh"
        border="1px solid" borderColor="border.default" overflow="hidden">
        <ModalBody p={0}>
          <HStack px={4} py={3} borderBottom="1px solid" borderColor="border.subtle" spacing={3}>
            <Input ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={onKey}
              variant="unstyled" placeholder="Search views or ask anything…" fontSize="16px" />
            <Kbd fontSize="10px">esc</Kbd>
          </HStack>
          <VStack align="stretch" spacing={0} maxH="52vh" overflowY="auto" py={2}>
            {results.length === 0 && (
              <Text px={4} py={6} color="text.muted" fontSize="sm" textAlign="center">
                No matches for “{q}”.
              </Text>
            )}
            {results.map((r, i) => (
              <HStack key={r.path + i} px={4} py={2.5} mx={2} borderRadius="9px" cursor="pointer"
                bg={i === cursor ? "bg.hover" : "transparent"}
                onMouseEnter={() => setCursor(i)} onClick={() => onNavigate(r.path)} spacing={3}>
                <Box w="6px" h="6px" borderRadius="full"
                  bg={r.kind === "ask" ? "accent.iris" : "accent.brand"} flexShrink={0} />
                <Box flex={1} minW={0}>
                  <Text fontSize="14px" fontWeight={500} color="text.primary" noOfLines={1}>{r.label}</Text>
                  <Text fontSize="12px" color="text.subtle" noOfLines={1}>{r.hint}</Text>
                </Box>
                {i === cursor && <Box as={LuCornerDownLeft} boxSize="14px" color="text.subtle" />}
              </HStack>
            ))}
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}
