"use client";

import {
  Box,
  Button,
  HStack,
  IconButton,
  Input,
  InputGroup,
  InputLeftElement,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  Tag,
  TagCloseButton,
  TagLabel,
  Text,
  Tooltip,
  VStack,
  Wrap,
  WrapItem,
} from "@chakra-ui/react";
import {
  LuLayoutGrid,
  LuChevronDown,
  LuTarget,
  LuFlag,
  LuRouter,
  LuSearch,
  LuMaximize2,
  LuRotateCcw,
  LuDownload,
  LuExpand,
} from "react-icons/lu";
import type { GraphLayoutKind, GraphNode } from "@/lib/types";

interface Props {
  layout: GraphLayoutKind;
  onLayoutChange: (l: GraphLayoutKind) => void;
  source: GraphNode | null;
  sink: GraphNode | null;
  onClearSource: () => void;
  onClearSink: () => void;
  onFindPath: () => void;
  finding: boolean;
  nodeCount: number;
  edgeCount: number;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  allEdgeTypes: string[];
  hiddenEdgeTypes: Set<string>;
  onToggleEdgeType: (t: string) => void;
  onFit: () => void;
  onReset: () => void;
  onExpandAll: () => void;
  onExportPng: () => void;
}

const LAYOUT_LABELS: Record<GraphLayoutKind, string> = {
  cola: "Force (cola)",
  dagre: "Hierarchy (dagre)",
  concentric: "Concentric",
  circle: "Circle",
};

export function GraphToolbar(props: Props) {
  const {
    layout,
    onLayoutChange,
    source,
    sink,
    onClearSource,
    onClearSink,
    onFindPath,
    finding,
    nodeCount,
    searchQuery,
    onSearchChange,
    allEdgeTypes,
    hiddenEdgeTypes,
    onToggleEdgeType,
    onFit,
    onReset,
    onExpandAll,
    onExportPng,
  } = props;

  return (
    <VStack align="stretch" spacing={2} px={3} py={2.5}>
      {/* Row 1 — primary actions */}
      <HStack justify="space-between" spacing={2}>
        <HStack spacing={2} flexWrap="wrap">
          <Menu>
            <MenuButton
              as={Button}
              leftIcon={<LuLayoutGrid />}
              rightIcon={<LuChevronDown />}
              size="xs"
              variant="ghost"
              color="text.primary"
              _hover={{ bg: "whiteAlpha.100" }}
            >
              {LAYOUT_LABELS[layout]}
            </MenuButton>
            <MenuList bg="bg.surface" borderColor="border.muted" fontSize="sm">
              {(Object.keys(LAYOUT_LABELS) as GraphLayoutKind[]).map((k) => (
                <MenuItem
                  key={k}
                  bg="transparent"
                  _hover={{ bg: "whiteAlpha.100" }}
                  onClick={() => onLayoutChange(k)}
                >
                  {LAYOUT_LABELS[k]}
                </MenuItem>
              ))}
            </MenuList>
          </Menu>

          <Tooltip label="Fit to screen" fontSize="xs">
            <IconButton
              aria-label="Fit"
              icon={<LuMaximize2 />}
              size="xs"
              variant="ghost"
              color="text.muted"
              onClick={onFit}
              _hover={{ bg: "whiteAlpha.100", color: "text.primary" }}
            />
          </Tooltip>
          <Tooltip label="Expand all nodes (1-hop)" fontSize="xs">
            <IconButton
              aria-label="Expand all"
              icon={<LuExpand />}
              size="xs"
              variant="ghost"
              color="text.muted"
              onClick={onExpandAll}
              isDisabled={nodeCount === 0}
              _hover={{ bg: "whiteAlpha.100", color: "text.primary" }}
            />
          </Tooltip>
          <Tooltip label="Download PNG" fontSize="xs">
            <IconButton
              aria-label="Download PNG"
              icon={<LuDownload />}
              size="xs"
              variant="ghost"
              color="text.muted"
              onClick={onExportPng}
              isDisabled={nodeCount === 0}
              _hover={{ bg: "whiteAlpha.100", color: "text.primary" }}
            />
          </Tooltip>
          <Tooltip label="Reset graph" fontSize="xs">
            <IconButton
              aria-label="Reset"
              icon={<LuRotateCcw />}
              size="xs"
              variant="ghost"
              color="text.muted"
              onClick={onReset}
              isDisabled={nodeCount === 0}
              _hover={{ bg: "whiteAlpha.100", color: "text.primary" }}
            />
          </Tooltip>

          {source && (
            <RoleBadge
              icon={<LuTarget />}
              label="src"
              colorScheme="blue"
              text={source.caption || source.id}
              onClear={onClearSource}
            />
          )}
          {sink && (
            <RoleBadge
              icon={<LuFlag />}
              label="sink"
              colorScheme="red"
              text={sink.caption || sink.id}
              onClear={onClearSink}
            />
          )}

          {source && sink && (
            <Tooltip label="Find paths via Core API /graph/path">
              <Button
                size="xs"
                leftIcon={<LuRouter />}
                onClick={onFindPath}
                isLoading={finding}
                colorScheme="accent"
              >
                Find path
              </Button>
            </Tooltip>
          )}
        </HStack>

      </HStack>

      {/* Row 2 — search + edge-type filters */}
      <HStack spacing={3} align="flex-start">
        <InputGroup size="xs" maxW="240px">
          <InputLeftElement pointerEvents="none" color="text.muted">
            <LuSearch size={12} />
          </InputLeftElement>
          <Input
            placeholder="Search nodes…"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            borderColor="border.muted"
            bg="bg.surface"
            fontSize="12px"
            _focus={{ borderColor: "accent.400", boxShadow: "none" }}
          />
        </InputGroup>

        {allEdgeTypes.length > 0 && (
          <Wrap spacing={1.5} flex="1">
            {allEdgeTypes.map((t) => {
              const hidden = hiddenEdgeTypes.has(t);
              return (
                <WrapItem key={t}>
                  <Tag
                    size="sm"
                    as="button"
                    onClick={() => onToggleEdgeType(t)}
                    cursor="pointer"
                    variant="subtle"
                    borderRadius="full"
                    bg={hidden ? "transparent" : "whiteAlpha.100"}
                    color={hidden ? "text.muted" : "text.primary"}
                    border="1px solid"
                    borderColor={hidden ? "border.muted" : "transparent"}
                    opacity={hidden ? 0.55 : 1}
                    transition="all 120ms ease"
                    _hover={{ borderColor: "accent.400" }}
                  >
                    <Box
                      w="8px"
                      h="2px"
                      bg={hidden ? "text.muted" : "accent.300"}
                      mr={1.5}
                    />
                    <TagLabel fontSize="10px">{t.replace(/_/g, " ")}</TagLabel>
                  </Tag>
                </WrapItem>
              );
            })}
          </Wrap>
        )}
      </HStack>
    </VStack>
  );
}

function RoleBadge({
  icon,
  label,
  colorScheme,
  text,
  onClear,
}: {
  icon: React.ReactNode;
  label: string;
  colorScheme: string;
  text: string;
  onClear: () => void;
}) {
  return (
    <Tag size="sm" colorScheme={colorScheme} borderRadius="full" variant="subtle">
      <Box mr={1.5}>{icon}</Box>
      <TagLabel fontSize="11px" mr={1}>
        {label}: {text.length > 22 ? text.slice(0, 20) + "…" : text}
      </TagLabel>
      <TagCloseButton onClick={onClear} />
    </Tag>
  );
}
