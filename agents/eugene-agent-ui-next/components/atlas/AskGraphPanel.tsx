"use client";

import { Alert, AlertIcon, Box, Flex, HStack, Text, IconButton, Tooltip } from "@chakra-ui/react";
import { LuX } from "react-icons/lu";
import { useGraphExplorer } from "@/hooks/useGraphExplorer";
import type { ContextGraph } from "@/lib/types";
import type { GraphExtractor } from "@/lib/graphExtractor";
import { KnowledgeGraph } from "@/components/graph/KnowledgeGraph";
import { GraphToolbar } from "@/components/graph/GraphToolbar";
import { GraphLegend } from "@/components/graph/GraphLegend";
import { NodeDetailsPanel } from "@/components/graph/NodeDetailsPanel";

interface Props {
  graph: ContextGraph;
  setGraph: (g: ContextGraph) => void;
  extractor: GraphExtractor;
  onClose: () => void;
}

/**
 * On-demand context-graph panel for the Ask view. Reuses the exact same
 * Cytoscape visualization (KnowledgeGraph + useGraphExplorer) that the original
 * Eugene workspace shipped — expand/collapse, path-finding, evidence — but only
 * mounts when the user opts in via the "Graph" toggle.
 */
export function AskGraphPanel({ graph, setGraph, extractor, onClose }: Props) {
  const explorer = useGraphExplorer({ extractor, graph, setGraph });
  const nodeCount = graph.nodes.length;
  const edgeCount = graph.rels.length;

  return (
    <Flex direction="column" h="100%" minH={0} bg="bg.canvas">
      {/* header */}
      <HStack px={4} py={2.5} borderBottom="1px solid" borderColor="border.subtle"
        bg="bg.panel" justify="space-between" flexShrink={0}>
        <HStack spacing={3} minW={0}>
          <Text fontSize="14px" fontWeight={700} color="text.primary" letterSpacing="-0.01em">
            Context graph
          </Text>
          <HStack spacing={2} fontSize="11px">
            <Box bg="bg.subtle" color="text.muted" borderRadius="full" px={2} py={0.5} fontWeight={600}>
              {nodeCount} nodes
            </Box>
            <Box bg="bg.subtle" color="text.muted" borderRadius="full" px={2} py={0.5} fontWeight={600}>
              {edgeCount} rels
            </Box>
          </HStack>
        </HStack>
        <Tooltip label="Hide graph" fontSize="xs">
          <IconButton aria-label="Hide graph" icon={<LuX />} size="sm" variant="ghost"
            color="text.muted" onClick={onClose} />
        </Tooltip>
      </HStack>

      {/* toolbar */}
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
        <Alert status="warning" mx={3} mt={2} fontSize="xs" borderRadius="lg" py={1.5} px={3}>
          <AlertIcon boxSize="12px" />
          {explorer.error}
        </Alert>
      )}

      {/* canvas */}
      <Box flex={1} minH={0} position="relative" overflow="hidden">
        {nodeCount === 0 ? (
          <Flex h="100%" align="center" justify="center" px={8}>
            <Text fontSize="sm" color="text.muted" textAlign="center" maxW="320px">
              Ask a question with the <b>All Sources</b> or <b>Eugene Graph</b> source
              selected — the agent&apos;s reasoning path will appear here as an
              interactive graph.
            </Text>
          </Flex>
        ) : (
          <>
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
              onShowEvidence={explorer.showEvidence}
              onTogglePin={explorer.togglePin}
              onRemove={explorer.removeNode}
            />
            <NodeDetailsPanel
              node={explorer.selectedNode}
              onClose={() => explorer.setSelectedNodeId(null)}
            />
          </>
        )}
      </Box>

      <Box borderTop="1px solid" borderColor="border.subtle" bg="bg.panel">
        <GraphLegend graph={graph} />
      </Box>
    </Flex>
  );
}
