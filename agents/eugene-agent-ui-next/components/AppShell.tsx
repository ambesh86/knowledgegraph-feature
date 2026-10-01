"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Flex,
  HStack,
  Heading,
  IconButton,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Text,
  Tooltip,
  VStack,
} from "@chakra-ui/react";
import { LuPanelRightOpen, LuPanelRightClose } from "react-icons/lu";
import { useChatStream } from "@/hooks/useChatStream";
import { useGraphExplorer } from "@/hooks/useGraphExplorer";
import { getDemoParam } from "@/lib/demoSeed";
import { ChatPanel } from "./chat/ChatPanel";
import { KnowledgeGraph } from "./graph/KnowledgeGraph";
import { NodeDetailsPanel } from "./graph/NodeDetailsPanel";
import { EvidencePanel } from "./graph/EvidencePanel";
import { GraphToolbar } from "./graph/GraphToolbar";
import { GraphLegend } from "./graph/GraphLegend";
import { Sidebar } from "./Sidebar";

/**
 * 2026 Aurora layout — results-driven "graph hero" shell.
 *
 *   Sidebar | Chat rail | GRAPH HERO | Inspector rail
 *
 * Empty state is chat-forward (chat dominates, graph shows an invite). The
 * moment the agent populates a reasoning graph, the canvas becomes the hero
 * (flex-1) while chat collapses to a rail and a collapsible Inspector rail
 * (Evidence · Tool Calls · Stats · Lineage) opens on the right. The Cytoscape
 * canvas stays mounted across the transition so it never re-initialises.
 */
export function AppShell() {
  const {
    messages,
    graph,
    setGraph,
    extractor,
    pending,
    conversationId,
    tokenReady,
    error,
    send,
    cancel,
    resetConversation,
    seedDemo,
  } = useChatStream();

  const explorer = useGraphExplorer({ extractor, graph, setGraph });

  const nodeCount = graph.nodes.length;
  const edgeCount = graph.rels.length;
  const evidenceCount = explorer.evidenceChain.length;
  const hasResults = nodeCount > 0;

  const toolCalls = useMemo(
    () =>
      messages.flatMap((m) =>
        (m.toolCalls ?? []).map((t) => ({ ...t, messageId: m.id }))
      ),
    [messages]
  );

  const statusAlert = useMemo(() => error || explorer.error, [error, explorer.error]);

  // Closed by default so chat + graph get the full width. The inspector
  // (Evidence · Activity · Stats · Lineage) opens on demand from the toggle in
  // the graph header, and auto-opens when a node's "Evidence" or a citation
  // chip is clicked (see onShowEvidence / focusNode).
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [inspectorTab, setInspectorTab] = useState(0); // 0=Evidence

  // ── Resizable chat | graph split ──────────────────────────────────────────
  // The chat rail width is user-adjustable by dragging the divider between the
  // chat and the graph hero. Persisted to localStorage; double-click resets.
  const DEFAULT_CHAT_WIDTH = 440;
  const MIN_CHAT_WIDTH = 320;
  const [chatWidth, setChatWidth] = useState(DEFAULT_CHAT_WIDTH);
  const [isDragging, setIsDragging] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);
  const chatWidthRef = useRef(chatWidth);
  const draggingRef = useRef(false);

  useEffect(() => {
    chatWidthRef.current = chatWidth;
  }, [chatWidth]);

  useEffect(() => {
    const saved = Number(localStorage.getItem("eugene.chatWidth"));
    if (saved && saved >= MIN_CHAT_WIDTH) setChatWidth(saved);
  }, []);

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      if (!draggingRef.current || !chatRef.current) return;
      const left = chatRef.current.getBoundingClientRect().left;
      // Keep at least ~520px for the graph hero on the right.
      const max = Math.max(MIN_CHAT_WIDTH, Math.min(window.innerWidth - 520, 880));
      const next = Math.min(Math.max(e.clientX - left, MIN_CHAT_WIDTH), max);
      setChatWidth(next);
    };
    const onUp = () => {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      setIsDragging(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      try {
        localStorage.setItem("eugene.chatWidth", String(Math.round(chatWidthRef.current)));
      } catch {
        /* ignore quota/SSR */
      }
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, []);

  const startDrag = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    draggingRef.current = true;
    setIsDragging(true);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  const resetChatWidth = useCallback(() => {
    setChatWidth(DEFAULT_CHAT_WIDTH);
    try {
      localStorage.setItem("eugene.chatWidth", String(DEFAULT_CHAT_WIDTH));
    } catch {
      /* ignore */
    }
  }, []);

  // Dev/demo seed — populate a real fixture subgraph when ?demo=<name> is set.
  const demo = useMemo(getDemoParam, []);
  useEffect(() => {
    if (demo) void seedDemo(demo);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demo]);

  // Focus a node in the graph (citation chip click) — select + center + zoom.
  const focusNode = useCallback(
    (id: string) => {
      explorer.setSelectedNodeId(id);
      const cy = explorer.cyHandle.current;
      if (!cy) return;
      const n = cy.getElementById(id);
      if (n && n.nonempty()) {
        cy.animate(
          { center: { eles: n }, zoom: Math.max(cy.zoom(), 1.3) },
          { duration: 320 }
        );
      }
    },
    [explorer]
  );

  return (
    <Flex h="100vh" w="100vw" overflow="hidden" bg="bg.canvas">
      <Box display={{ base: "none", lg: "block" }}>
        <Sidebar
          conversationId={conversationId}
          messageCount={messages.filter((m) => m.role !== "system").length}
          graphNodeCount={nodeCount}
          tokenReady={tokenReady}
          onNewConversation={() => {
            resetConversation();
            explorer.clearRoles();
            explorer.clearEvidence();
            explorer.setSelectedNodeId(null);
          }}
        />
      </Box>

      {/* ───── Chat: dominant when empty, a resizable rail once results populate ───── */}
      <Flex
        ref={chatRef}
        direction="column"
        flex={hasResults ? "0 0 auto" : "1"}
        w={hasResults ? { base: "100%", md: `${chatWidth}px` } : "auto"}
        minW={0}
        borderRight={hasResults ? "none" : "1px solid"}
        borderColor="border.subtle"
        bg="bg.canvas"
        transition={isDragging ? "none" : "flex 0.35s ease, width 0.35s ease"}
      >
        <ChatPanel
          messages={messages}
          pending={pending}
          ready={tokenReady}
          error={statusAlert}
          onSend={send}
          onCancel={cancel}
          onCitationClick={focusNode}
        />
      </Flex>

      {/* ───── Draggable chat | graph divider ───── */}
      {hasResults && (
        <Tooltip label="Drag to resize · double-click to reset" fontSize="xs" openDelay={500}>
          <Box
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize chat and graph"
            onPointerDown={startDrag}
            onDoubleClick={resetChatWidth}
            display={{ base: "none", md: "flex" }}
            alignItems="center"
            justifyContent="center"
            flex="0 0 auto"
            w="7px"
            cursor="col-resize"
            bg={isDragging ? "accent.solid" : "border.subtle"}
            _hover={{ bg: "accent.solid" }}
            transition="background 0.15s ease"
            position="relative"
            zIndex={2}
          >
            {/* grip dots */}
            <VStack spacing="3px" pointerEvents="none">
              <Box w="3px" h="3px" borderRadius="full" bg="surface.0" opacity={0.55} />
              <Box w="3px" h="3px" borderRadius="full" bg="surface.0" opacity={0.55} />
              <Box w="3px" h="3px" borderRadius="full" bg="surface.0" opacity={0.55} />
            </VStack>
          </Box>
        </Tooltip>
      )}

      {/* ───── Graph hero ───── */}
      <Flex
        direction="column"
        flex={hasResults ? "1" : "0 0 clamp(360px, 38vw, 560px)"}
        minW={0}
        display={{ base: hasResults ? "flex" : "none", md: "flex" }}
        bg="bg.canvas"
        position="relative"
        minH={0}
      >
        {/* Hero header */}
        <HStack
          px={4}
          py={2.5}
          justify="space-between"
          bgGradient="linear(135deg, rgba(27,184,224,0.16), rgba(66,86,245,0.16) 50%, rgba(255,42,157,0.14))"
          borderBottom="1px solid"
          borderColor="border.subtle"
        >
          <HStack spacing={3} minW={0}>
            <Heading
              size="sm"
              fontWeight={600}
              bgGradient="linear(135deg, cyan.300, accent.300, magenta.300)"
              bgClip="text"
              letterSpacing="-0.01em"
              noOfLines={1}
            >
              Knowledge Graph
            </Heading>
            <HStack spacing={2} fontSize="11px">
              <Badge bg="surface.300" color="text.primary" borderRadius="md" px={2} py={0.5} fontWeight={500}>
                {nodeCount} nodes
              </Badge>
              <Badge bg="surface.300" color="text.primary" borderRadius="md" px={2} py={0.5} fontWeight={500}>
                {edgeCount} rels
              </Badge>
            </HStack>
          </HStack>
          <Tooltip label={inspectorOpen ? "Hide inspector" : "Show inspector"} fontSize="xs">
            <IconButton
              aria-label="Toggle inspector"
              icon={inspectorOpen ? <LuPanelRightClose /> : <LuPanelRightOpen />}
              size="sm"
              variant="ghost"
              color="text.muted"
              onClick={() => setInspectorOpen((v) => !v)}
            />
          </Tooltip>
        </HStack>

        <Box px={3} py={2} borderBottom="1px solid" borderColor="border.subtle" bg="bg.panel">
          <GraphToolbar
            layout={explorer.layout}
            onLayoutChange={explorer.setLayout}
            source={explorer.source}
            sink={explorer.sink}
            onClearSource={explorer.clearSource}
            onClearSink={explorer.clearSink}
            onFindPath={explorer.runPathFinder}
            finding={explorer.findingPath}
            nodeCount={nodeCount}
            edgeCount={edgeCount}
            searchQuery={explorer.searchQuery}
            onSearchChange={explorer.setSearchQuery}
            allEdgeTypes={explorer.allEdgeTypes}
            hiddenEdgeTypes={explorer.hiddenEdgeTypes}
            onToggleEdgeType={explorer.toggleEdgeType}
            onFit={explorer.fit}
            onReset={explorer.resetGraph}
            onExpandAll={explorer.expandAll}
            onExportPng={explorer.exportPng}
          />
        </Box>

        {explorer.error && (
          <Alert status="warning" mx={3} mt={2} bg="signal.warning" color="surface.0" fontSize="xs" borderRadius="lg" py={1.5} px={3}>
            <AlertIcon boxSize="12px" />
            {explorer.error}
          </Alert>
        )}

        <Box flex={1} minH={0} position="relative" overflow="hidden">
          <KnowledgeGraph
            graph={graph}
            layout={explorer.layout}
            selectedNodeId={explorer.selectedNodeId}
            highlightedPathNodeIds={explorer.highlightedPathNodeIds}
            searchQuery={explorer.searchQuery}
            hiddenEdgeTypes={explorer.hiddenEdgeTypes}
            onCyReady={explorer.setCyHandle}
            onSelectNode={explorer.setSelectedNodeId}
            onExpand={explorer.expand}
            onCollapse={explorer.collapse}
            onMarkSource={explorer.markSource}
            onMarkSink={explorer.markSink}
            onClearRoles={explorer.clearRoles}
            onShowEvidence={(id) => {
              explorer.showEvidence(id);
              setInspectorTab(0);
              setInspectorOpen(true);
            }}
            onTogglePin={explorer.togglePin}
            onRemove={explorer.removeNode}
          />
          {/* Selected-node details slide over the graph (Neo4j-style). */}
          <NodeDetailsPanel
            node={explorer.selectedNode}
            onClose={() => explorer.setSelectedNodeId(null)}
          />
        </Box>

        <Box borderTop="1px solid" borderColor="border.subtle" bg="bg.panel">
          <GraphLegend graph={graph} />
        </Box>
      </Flex>

      {/* ───── Inspector rail (collapsible) ───── */}
      <Box
        flexShrink={0}
        w={inspectorOpen ? { base: "0", md: "330px", xl: "360px" } : "0"}
        display={{ base: "none", md: "block" }}
        overflow="hidden"
        borderLeft={inspectorOpen ? "1px solid" : "none"}
        borderColor="border.subtle"
        bg="bg.canvas"
        transition="width 0.3s ease"
      >
        <Flex direction="column" h="100%" minH={0} w={{ md: "330px", xl: "360px" }}>
          <Tabs
            index={inspectorTab}
            onChange={setInspectorTab}
            variant="line"
            colorScheme="accent"
            isLazy
            lazyBehavior="keepMounted"
            flex={1}
            display="flex"
            flexDirection="column"
            minH={0}
          >
            <TabList px={2} borderBottom="1px solid" borderColor="border.subtle" overflowX="auto" sx={{ "&::-webkit-scrollbar": { display: "none" } }}>
              <RailTab label="Evidence" badge={evidenceCount || undefined} />
              <RailTab label="Activity" badge={toolCalls.length || undefined} />
              <RailTab label="Stats" />
              <RailTab label="Lineage" />
            </TabList>
            <TabPanels flex={1} minH={0} display="flex" flexDirection="column">
              <TabPanel p={0} flex={1} minH={0} position="relative" overflowY="auto">
                {evidenceCount > 0 ? (
                  <EvidencePanel embedded chain={explorer.evidenceChain} onClose={explorer.clearEvidence} />
                ) : (
                  <EmptyTab title="No evidence selected" body="Right-click a node in the graph and choose “Evidence”, or click a citation chip under an answer, to trace its provenance chain." />
                )}
              </TabPanel>
              <TabPanel p={0} flex={1} minH={0} overflowY="auto">
                {toolCalls.length === 0 ? (
                  <EmptyTab title="No tool calls yet" body="The agent's tool invocations will appear here with inputs, outputs and the subgraph each contributed." />
                ) : (
                  <ToolCallsView toolCalls={toolCalls} />
                )}
              </TabPanel>
              <TabPanel p={0} flex={1} minH={0} overflowY="auto">
                <StatsView
                  nodeCount={nodeCount}
                  edgeCount={edgeCount}
                  evidenceCount={evidenceCount}
                  toolCallCount={toolCalls.length}
                  edgeTypes={explorer.allEdgeTypes}
                />
              </TabPanel>
              <TabPanel p={0} flex={1} minH={0} overflowY="auto">
                <LineageView conversationId={conversationId} messages={messages} />
              </TabPanel>
            </TabPanels>
          </Tabs>
        </Flex>
      </Box>
    </Flex>
  );
}

// ---------------------------------------------------------------------------
function RailTab({ label, badge }: { label: string; badge?: number }) {
  return (
    <Tab
      fontSize="12.5px"
      fontWeight={500}
      color="text.muted"
      _selected={{ color: "text.primary", borderBottom: "2px solid", borderColor: "accent.solid" }}
      _hover={{ color: "text.primary" }}
      px={2.5}
      py={2}
    >
      {label}
      {typeof badge === "number" && badge > 0 && (
        <Badge ml={1.5} fontSize="10px" colorScheme="accent" variant="subtle" borderRadius="md" px={1.5}>
          {badge}
        </Badge>
      )}
    </Tab>
  );
}

function EmptyTab({ title, body }: { title: string; body: string }) {
  return (
    <VStack h="100%" justify="center" align="center" color="text.muted" px={8} py={6} spacing={3}>
      <Box w="72px" h="72px" borderRadius="full" bgGradient="radial(rgba(66,86,245,0.4), transparent 70%)" opacity={0.6} />
      <Text fontSize="sm" fontWeight={600} color="text.primary">
        {title}
      </Text>
      <Text fontSize="xs" textAlign="center" maxW="320px">
        {body}
      </Text>
    </VStack>
  );
}

function ToolCallsView({
  toolCalls,
}: {
  toolCalls: { toolId?: string; tool?: string; input?: unknown; output?: unknown }[];
}) {
  return (
    <Box px={3} py={3}>
      {toolCalls.map((t, i) => {
        const inputStr = typeof t.input === "string" ? t.input : JSON.stringify(t.input);
        const outputStr =
          typeof t.output === "string"
            ? t.output
            : t.output !== undefined
            ? JSON.stringify(t.output)
            : "";
        return (
          <Box key={`${t.toolId ?? i}`} mb={3} p={3} bg="bg.surface" border="1px solid" borderColor="border.subtle" borderRadius="lg">
            <HStack mb={1} spacing={2}>
              <Badge colorScheme="cyan" variant="subtle" fontSize="10px" px={2}>
                {t.tool ?? "tool"}
              </Badge>
              <Text fontSize="11px" color="text.subtle">
                #{i + 1}
              </Text>
            </HStack>
            {inputStr && (
              <Text fontFamily="mono" fontSize="11px" color="text.muted" whiteSpace="pre-wrap" mb={1}>
                {"→ " + inputStr}
              </Text>
            )}
            {outputStr && (
              <Text fontFamily="mono" fontSize="11px" color="text.primary" whiteSpace="pre-wrap">
                {"← " + outputStr.slice(0, 320) + (outputStr.length > 320 ? " …" : "")}
              </Text>
            )}
          </Box>
        );
      })}
    </Box>
  );
}

function LineageView({
  conversationId,
  messages,
}: {
  conversationId: string | null;
  messages: { id: string; role: string; content?: string; createdAt?: number }[];
}) {
  const turns = messages.filter((m) => m.role !== "system");
  if (turns.length === 0) {
    return <EmptyTab title="No conversation yet" body="Send a question to start a reasoning lineage. Each turn appears here with routing decisions." />;
  }
  return (
    <Box px={4} py={3}>
      <Text fontSize="11px" color="text.subtle" mb={3} fontFamily="mono">
        conversation_id: {conversationId ?? "—"}
      </Text>
      {turns.map((m, i) => (
        <Box key={m.id} mb={3} pl={4} borderLeft="2px solid" borderColor={m.role === "user" ? "cyan.400" : "magenta.400"}>
          <HStack mb={1} spacing={2}>
            <Badge colorScheme={m.role === "user" ? "cyan" : "purple"} variant="subtle" fontSize="10px" px={2}>
              {m.role}
            </Badge>
            <Text fontSize="11px" color="text.subtle">
              turn {i + 1}
            </Text>
          </HStack>
          <Text fontSize="13px" color="text.primary" whiteSpace="pre-wrap">
            {(m.content ?? "").slice(0, 320)}
            {(m.content ?? "").length > 320 && " …"}
          </Text>
        </Box>
      ))}
    </Box>
  );
}

function StatsView({
  nodeCount,
  edgeCount,
  evidenceCount,
  toolCallCount,
  edgeTypes,
}: {
  nodeCount: number;
  edgeCount: number;
  evidenceCount: number;
  toolCallCount: number;
  edgeTypes: string[];
}) {
  const cards = [
    { label: "Graph nodes", value: nodeCount, accent: "cyan.400" },
    { label: "Graph edges", value: edgeCount, accent: "accent.400" },
    { label: "Evidence facts", value: evidenceCount, accent: "magenta.400" },
    { label: "Tool calls", value: toolCallCount, accent: "lumen.500" },
  ];
  return (
    <Box px={4} py={4}>
      <HStack spacing={3} mb={4} flexWrap="wrap">
        {cards.map((c) => (
          <Box key={c.label} flex="1 1 130px" minW="130px" p={3} bg="bg.surface" border="1px solid" borderColor="border.subtle" borderRadius="lg" position="relative" overflow="hidden">
            <Box position="absolute" top={0} left={0} right={0} h="2px" bg={c.accent} />
            <Text fontSize="10px" color="text.subtle" mb={1} letterSpacing="0.04em">
              {c.label.toUpperCase()}
            </Text>
            <Text fontSize="22px" fontWeight={600} color="text.primary" fontFamily="mono">
              {c.value}
            </Text>
          </Box>
        ))}
      </HStack>
      {edgeTypes.length > 0 && (
        <Box>
          <Text fontSize="11px" color="text.subtle" mb={2} letterSpacing="0.04em">
            EDGE TYPES IN GRAPH
          </Text>
          <HStack spacing={2} flexWrap="wrap">
            {edgeTypes.map((t) => (
              <Badge key={t} bg="surface.300" color="text.primary" borderRadius="md" px={2} py={0.5} fontSize="11px" fontWeight={500}>
                {t}
              </Badge>
            ))}
          </HStack>
        </Box>
      )}
    </Box>
  );
}
