"use client";

import { useCallback, useMemo, useState } from "react";
import { expandNode, findPath } from "@/lib/graphApi";
import { GraphExtractor } from "@/lib/graphExtractor";
import type {
  ContextGraph,
  GraphLayoutKind,
  GraphNode,
  Provenance,
} from "@/lib/types";
import type { Core } from "cytoscape";

interface UseGraphExplorerArgs {
  extractor: GraphExtractor;
  graph: ContextGraph;
  setGraph: (g: ContextGraph) => void;
}

interface UseGraphExplorerReturn {
  selectedNodeId: string | null;
  setSelectedNodeId: (id: string | null) => void;
  selectedNode: GraphNode | null;
  evidenceChain: GraphNode[];
  showEvidence: (id: string) => void;
  clearEvidence: () => void;
  source: GraphNode | null;
  sink: GraphNode | null;
  markSource: (id: string) => void;
  markSink: (id: string) => void;
  clearSource: () => void;
  clearSink: () => void;
  clearRoles: () => void;
  findingPath: boolean;
  runPathFinder: () => Promise<void>;
  highlightedPathNodeIds: Set<string>;
  expanding: Set<string>;
  expand: (id: string, hops: 1 | 2) => Promise<void>;
  collapse: (id: string) => void;
  expandAll: () => Promise<void>;
  togglePin: (id: string) => void;
  removeNode: (id: string) => void;
  layout: GraphLayoutKind;
  setLayout: (l: GraphLayoutKind) => void;
  error: string | null;
  // search + filter
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  hiddenEdgeTypes: Set<string>;
  toggleEdgeType: (t: string) => void;
  allEdgeTypes: string[];
  // cy handle (for fit/png/reset)
  cyHandle: { current: Core | null };
  setCyHandle: (cy: Core | null) => void;
  fit: () => void;
  exportPng: () => void;
  resetGraph: () => void;
}

export function useGraphExplorer({
  extractor,
  graph,
  setGraph,
}: UseGraphExplorerArgs): UseGraphExplorerReturn {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [evidenceChain, setEvidenceChain] = useState<GraphNode[]>([]);
  const [expanding, setExpanding] = useState<Set<string>>(new Set());
  const [findingPath, setFindingPath] = useState(false);
  const [highlightedPathNodeIds, setHighlightedPathNodeIds] = useState<Set<string>>(
    new Set()
  );
  const [layout, setLayout] = useState<GraphLayoutKind>("cola");
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [hiddenEdgeTypes, setHiddenEdgeTypes] = useState<Set<string>>(new Set());
  const cyHandle = useMemo(() => ({ current: null as Core | null }), []);
  const setCyHandle = useCallback(
    (cy: Core | null) => {
      cyHandle.current = cy;
    },
    [cyHandle]
  );
  const allEdgeTypes = useMemo(() => {
    const s = new Set<string>();
    for (const r of graph.rels) if (r.type) s.add(r.type);
    return [...s].sort();
  }, [graph.rels]);
  const toggleEdgeType = useCallback((t: string) => {
    setHiddenEdgeTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  }, []);
  const fit = useCallback(() => {
    cyHandle.current?.fit(undefined, 60);
  }, [cyHandle]);
  const exportPng = useCallback(() => {
    const cy = cyHandle.current;
    if (!cy) return;
    const png = cy.png({ bg: "transparent", full: true, scale: 2 });
    const a = document.createElement("a");
    a.href = png;
    a.download = `eugene-graph-${Date.now()}.png`;
    a.click();
  }, [cyHandle]);
  const resetGraph = useCallback(() => {
    extractor.reset();
    setGraph({ nodes: [], rels: [] });
    setHiddenEdgeTypes(new Set());
    setSearchQuery("");
  }, [extractor, setGraph]);

  const source = useMemo(
    () => graph.nodes.find((n) => n.role === "source") ?? null,
    [graph.nodes]
  );
  const sink = useMemo(
    () => graph.nodes.find((n) => n.role === "sink") ?? null,
    [graph.nodes]
  );
  const selectedNode = useMemo(
    () => (selectedNodeId ? graph.nodes.find((n) => n.id === selectedNodeId) ?? null : null),
    [selectedNodeId, graph.nodes]
  );

  const showEvidence = useCallback(
    (id: string) => {
      setEvidenceChain(extractor.evidenceChain(id));
    },
    [extractor]
  );
  const clearEvidence = useCallback(() => setEvidenceChain([]), []);

  const clearRole = useCallback(
    (role: "source" | "sink") => {
      setGraph(extractor.clearRoleFor(role));
      setHighlightedPathNodeIds(new Set());
      setGraph(extractor.clearPathHighlights());
    },
    [extractor, setGraph]
  );

  const markSource = useCallback(
    (id: string) => {
      extractor.clearRoleFor("source");
      setGraph(extractor.setRole(id, "source"));
    },
    [extractor, setGraph]
  );
  const markSink = useCallback(
    (id: string) => {
      extractor.clearRoleFor("sink");
      setGraph(extractor.setRole(id, "sink"));
    },
    [extractor, setGraph]
  );

  const clearRoles = useCallback(() => {
    extractor.clearRoleFor("source");
    extractor.clearRoleFor("sink");
    setHighlightedPathNodeIds(new Set());
    setGraph(extractor.clearPathHighlights());
  }, [extractor, setGraph]);

  const runPathFinder = useCallback(async () => {
    if (!source || !sink) return;
    setFindingPath(true);
    setError(null);
    try {
      const { nodes, rels } = await findPath(source.id, sink.id);
      const prov: Provenance = {
        source: "path_finder",
        parentNodeIds: [source.id, sink.id],
        timestamp: Date.now(),
        cypherHint: `MATCH p=shortestPath((a {node_id:'${source.id}'})-[*..4]-(b {node_id:'${sink.id}'})) RETURN p`,
      };
      setGraph(extractor.mergeExternal(nodes, rels, prov));
      const pathNodeIds = new Set(nodes.map((n) => n.id));
      const pathRelIds = new Set(rels.map((r) => r.id));
      setHighlightedPathNodeIds(pathNodeIds);
      setGraph(extractor.markPath(pathNodeIds, pathRelIds));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setFindingPath(false);
    }
  }, [source, sink, extractor, setGraph]);

  const expand = useCallback(
    async (id: string, hops: 1 | 2) => {
      setExpanding((s) => new Set(s).add(id));
      setError(null);
      try {
        const { nodes, rels } = await expandNode(id, hops);
        const prov: Provenance = {
          source: "user_expand",
          parentNodeIds: [id],
          timestamp: Date.now(),
          cypherHint: `MATCH (n {node_id:'${id}'})-[r*..${hops}]-(m) RETURN n,r,m`,
        };
        setGraph(extractor.mergeExternal(nodes, rels, prov));
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setExpanding((s) => {
          const next = new Set(s);
          next.delete(id);
          return next;
        });
      }
    },
    [extractor, setGraph]
  );

  const collapse = useCallback(
    (id: string) => {
      setGraph(extractor.collapse(id));
    },
    [extractor, setGraph]
  );

  const togglePin = useCallback(
    (id: string) => {
      const n = extractor.getNode(id);
      if (!n) return;
      n.pinned = !n.pinned;
      setGraph(extractor.snapshot());
    },
    [extractor, setGraph]
  );

  const removeNode = useCallback(
    (id: string) => {
      setGraph(extractor.remove(id));
      if (selectedNodeId === id) setSelectedNodeId(null);
    },
    [extractor, selectedNodeId, setGraph]
  );

  const expandAll = useCallback(async () => {
    const targets = graph.nodes.filter((n) => !n.pinned).map((n) => n.id);
    for (const id of targets) {
      try {
        const { nodes, rels } = await expandNode(id, 1);
        const prov: Provenance = {
          source: "user_expand",
          parentNodeIds: [id],
          timestamp: Date.now(),
          cypherHint: `MATCH (n {node_id:'${id}'})-[r*..1]-(m) RETURN n,r,m`,
        };
        setGraph(extractor.mergeExternal(nodes, rels, prov));
      } catch {
        /* swallow per-node errors to let others succeed */
      }
    }
  }, [graph.nodes, extractor, setGraph]);

  return {
    selectedNodeId,
    setSelectedNodeId,
    selectedNode,
    evidenceChain,
    showEvidence,
    clearEvidence,
    source,
    sink,
    markSource,
    markSink,
    clearSource: () => clearRole("source"),
    clearSink: () => clearRole("sink"),
    clearRoles,
    findingPath,
    runPathFinder,
    highlightedPathNodeIds,
    expanding,
    expand,
    collapse,
    togglePin,
    removeNode,
    layout,
    setLayout,
    error,
    searchQuery,
    setSearchQuery,
    hiddenEdgeTypes,
    toggleEdgeType,
    allEdgeTypes,
    cyHandle,
    setCyHandle,
    fit,
    exportPng,
    resetGraph,
    expandAll,
  };
}
