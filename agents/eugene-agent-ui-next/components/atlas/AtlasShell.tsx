"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  Box,
  Flex,
  HStack,
  Text,
  VStack,
  Tooltip,
  Kbd,
  useColorMode,
} from "@chakra-ui/react";
import { LuSearch, LuBell, LuMoon, LuSun } from "react-icons/lu";
import { NAV, SETTINGS_ITEM } from "@/lib/atlas/nav";
import type { AtlasUser } from "@/lib/atlas/useAuth";
import { AtlasMark } from "./AtlasMark";
import { CommandPalette } from "./CommandPalette";
import { ConversationList } from "./ConversationList";
import { UserMenu } from "./UserMenu";
import { DataFreshness } from "./DataFreshness";

const RAIL_W = 232;

export function AtlasShell({
  user,
  children,
}: {
  user: AtlasUser;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { colorMode, toggleColorMode } = useColorMode();
  const [paletteOpen, setPaletteOpen] = useState(false);

  const go = useCallback((path: string) => router.push(path), [router]);

  // Global keyboard shortcuts: ⌘K palette, ⌘1–8 navigation.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
        return;
      }
      if (mod && /^[1-7]$/.test(e.key)) {
        const item = NAV.find((n) => n.shortcut === e.key);
        if (item) {
          e.preventDefault();
          go(item.path);
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go]);

  const isActive = (path: string) => pathname === path || pathname?.startsWith(path + "/");

  return (
    <Flex h="100vh" w="100vw" overflow="hidden" bg="bg.canvas">
      {/* ───────────── Sidebar rail ───────────── */}
      <Flex
        direction="column"
        w={`${RAIL_W}px`}
        flexShrink={0}
        borderRight="1px solid"
        borderColor="border.subtle"
        bg="bg.panel"
        py={4}
        display={{ base: "none", md: "flex" }}
      >
        <HStack px={5} pb={5} spacing={2.5}>
          <AtlasMark size={28} />
          <Box>
            <Text fontWeight={800} fontSize="15px" lineHeight={1} letterSpacing="-0.02em">
              CSL
            </Text>
            <Text fontSize="9px" letterSpacing="0.16em" color="text.subtle" mt={0.5}>
              BD · Q3 2026
            </Text>
          </Box>
        </HStack>

        <VStack align="stretch" spacing={0.5} px={2.5} flexShrink={0}>
          {NAV.map((item) => {
            const active = isActive(item.path);
            return (
              <HStack
                key={item.id}
                as="button"
                onClick={() => go(item.path)}
                spacing={3}
                px={3}
                py={2}
                borderRadius="9px"
                bg={active ? "bg.active" : "transparent"}
                color={active ? "text.primary" : "text.muted"}
                _hover={{ bg: active ? "bg.active" : "bg.hover", color: "text.primary" }}
                transition="background 0.12s, color 0.12s"
                role="group"
                position="relative"
              >
                {active && (
                  <Box position="absolute" left="-10px" top="20%" bottom="20%" w="3px"
                    bg="accent.brand" borderRadius="full" />
                )}
                <Box as={item.icon} boxSize="18px" />
                <Text fontSize="14px" fontWeight={active ? 600 : 500} flex={1} textAlign="left">
                  {item.label}
                </Text>
                <Kbd fontSize="10px" bg="transparent" border="none" color="text.subtle"
                  _groupHover={{ color: "text.muted" }}>
                  ⌘{item.shortcut}
                </Kbd>
              </HStack>
            );
          })}
        </VStack>

        {/* Conversation history (claude.ai-style recents) */}
        <Box mt={3} mx={2.5} pt={3} borderTop="1px solid" borderColor="border.subtle"
          flex={1} minH={0} display="flex" flexDirection="column">
          <Suspense fallback={null}>
            <ConversationList />
          </Suspense>
        </Box>

        <Box px={2.5} pt={2}>
          <HStack
            as="button"
            onClick={() => go(SETTINGS_ITEM.path)}
            spacing={3} px={3} py={2} borderRadius="9px"
            color={isActive("/settings") ? "text.primary" : "text.muted"}
            bg={isActive("/settings") ? "bg.active" : "transparent"}
            _hover={{ bg: "bg.hover", color: "text.primary" }} w="100%"
          >
            <Box as={SETTINGS_ITEM.icon} boxSize="18px" />
            <Text fontSize="14px" fontWeight={500}>Settings</Text>
          </HStack>
        </Box>
      </Flex>

      {/* ───────────── Main column ───────────── */}
      <Flex direction="column" flex={1} minW={0}>
        {/* Topbar */}
        <HStack
          h="56px"
          flexShrink={0}
          px={4}
          borderBottom="1px solid"
          borderColor="border.subtle"
          bg="bg.panel"
          spacing={3}
          justify="space-between"
        >
          <HStack
            as="button"
            onClick={() => setPaletteOpen(true)}
            spacing={2.5}
            px={3}
            h="36px"
            minW={{ base: "auto", md: "420px" }}
            maxW="520px"
            flex={{ base: 1, md: "initial" }}
            bg="bg.subtle"
            border="1px solid"
            borderColor="border.subtle"
            borderRadius="10px"
            color="text.muted"
            _hover={{ borderColor: "border.default", bg: "bg.hover" }}
            transition="all 0.12s"
          >
            <Box as={LuSearch} boxSize="16px" />
            <Text fontSize="14px" flex={1} textAlign="left">Search or ask anything…</Text>
            <HStack spacing={1}>
              <Kbd fontSize="10px">⌘</Kbd><Kbd fontSize="10px">K</Kbd>
            </HStack>
          </HStack>

          <HStack spacing={1.5}>
            {/* "As of <date>" on every page. The first question anyone asks of a
                competitive dashboard is how old it is; answering it once, globally,
                beats repeating it per panel. */}
            <DataFreshness />
            <Tooltip label={`Switch to ${colorMode === "light" ? "dark" : "light"} mode`} fontSize="xs">
              <Box as="button" onClick={toggleColorMode} p={2} borderRadius="8px"
                color="text.muted" _hover={{ bg: "bg.hover", color: "text.primary" }}>
                <Box as={colorMode === "light" ? LuMoon : LuSun} boxSize="18px" />
              </Box>
            </Tooltip>
            <Box as="button" position="relative" p={2} borderRadius="8px"
              color="text.muted" _hover={{ bg: "bg.hover", color: "text.primary" }}>
              <Box as={LuBell} boxSize="18px" />
              <Box position="absolute" top="6px" right="6px" boxSize="7px" bg="accent.brand"
                borderRadius="full" border="1.5px solid" borderColor="bg.panel" />
            </Box>
            <UserMenu user={user} />
          </HStack>
        </HStack>

        {/* Routed view */}
        <Box flex={1} minH={0} overflowY="auto" bg="bg.canvas">
          {children}
        </Box>
      </Flex>

      <CommandPalette
        isOpen={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onNavigate={(path) => { setPaletteOpen(false); go(path); }}
      />
    </Flex>
  );
}
