"use client";

import { useCallback, useRef, useState } from "react";
import {
  Box,
  Button,
  HStack,
  IconButton,
  Kbd,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react";
import { LuSend, LuSquare } from "react-icons/lu";
import { ToolChips } from "./ToolChips";
import type { ToolSelection } from "@/lib/types";

interface Props {
  onSend: (prompt: string, tools: ToolSelection[]) => void;
  onCancel: () => void;
  pending: boolean;
  disabled: boolean;
}

export function Composer({ onSend, onCancel, pending, disabled }: Props) {
  const [value, setValue] = useState("");
  const [tools, setTools] = useState<ToolSelection[]>(["eugene"]);
  const taRef = useRef<HTMLTextAreaElement | null>(null);

  const submit = useCallback(() => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text, tools);
    setValue("");
    // Allow height to reset
    requestAnimationFrame(() => {
      if (taRef.current) taRef.current.style.height = "auto";
    });
  }, [value, tools, onSend, disabled]);

  return (
    <Box
      px={{ base: 4, md: 8 }}
      pb={5}
      pt={2}
      bgGradient="linear(to-t, bg.canvas 60%, transparent)"
    >
      <Box
        maxW="900px"
        mx="auto"
        bg="bg.glass"
        backdropFilter="saturate(160%) blur(18px)"
        border="1px solid"
        borderColor="border.muted"
        borderRadius="24px"
        p={3}
        boxShadow="0 20px 60px -30px rgba(0,0,0,0.6)"
      >
        <VStack align="stretch" spacing={2}>
          <Textarea
            ref={taRef}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              const el = e.target as HTMLTextAreaElement;
              el.style.height = "auto";
              el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="Ask Eugene about drugs, targets, trials, patents, or organizations…"
            variant="unstyled"
            rows={1}
            resize="none"
            fontSize="15px"
            color="text.primary"
            _placeholder={{ color: "text.muted" }}
            px={2}
            py={1}
            minH="38px"
            maxH="220px"
          />
          <HStack justify="space-between" align="center" px={1}>
            <ToolChips value={tools} onChange={setTools} />
            <HStack spacing={2}>
              <Text fontSize="xs" color="text.muted" display={{ base: "none", md: "block" }}>
                <Kbd fontSize="10px">Enter</Kbd> to send
              </Text>
              {pending ? (
                <IconButton
                  aria-label="Cancel"
                  icon={<LuSquare />}
                  onClick={onCancel}
                  size="sm"
                  variant="outline"
                  borderColor="signal.danger"
                  color="signal.danger"
                />
              ) : (
                <Button
                  leftIcon={<LuSend />}
                  onClick={submit}
                  isDisabled={disabled || !value.trim()}
                  size="sm"
                  px={5}
                >
                  Send
                </Button>
              )}
            </HStack>
          </HStack>
        </VStack>
      </Box>
    </Box>
  );
}
