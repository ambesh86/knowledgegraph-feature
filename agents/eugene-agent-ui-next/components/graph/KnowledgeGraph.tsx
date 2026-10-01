"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Box, Button, HStack, IconButton, Text, Tooltip, VStack, useColorMode } from "@chakra-ui/react";
import { LuPlus, LuMinus, LuMaximize2, LuLocate } from "react-icons/lu";
import cytoscape, { Core, ElementDefinition } from "cytoscape";
import { registerCytoscapeExtensions } from "./cyRegistry";
import { colorForCategory } from "@/lib/graphExtractor";
import type {
  ContextGraph,
  GraphLayoutKind,
  GraphNode,
  GraphRelationship,
} from "@/lib/types";

// Register plugins once at module load — synchronous, pre-render
if (typeof window !== "undefined") registerCytoscapeExtensions();

export interface KnowledgeGraphHandlers {
  onSelectNode?: (id: string | null) => void;
  onSelectEdge?: (id: string | null) => void;
  onExpand?: (id: string, hops: 1 | 2) => void;
  onCollapse?: (id: string) => void;
  onMarkSource?: (id: string) => void;
  onMarkSink?: (id: string) => void;
  onClearRoles?: () => void;
  onShowEvidence?: (id: string) => void;
  onTogglePin?: (id: string) => void;
  onRemove?: (id: string) => void;
}

interface Props extends KnowledgeGraphHandlers {
  graph: ContextGraph;
  layout: GraphLayoutKind;
  selectedNodeId: string | null;
  highlightedPathNodeIds: Set<string>;
  searchQuery?: string;
  hiddenEdgeTypes?: Set<string>;
  onCyReady?: (cy: Core | null) => void;
}

const LAYOUT_CONFIG: Record<GraphLayoutKind, cytoscape.LayoutOptions> = {
  cola: {
    name: "cola",
    animate: true,
    fit: true,
    // Generous padding keeps the laid-out graph well inside the bounded box.
    padding: 38,
    // avoidOverlap + spacing give the clean, spread, "modern" look (no clumping).
    avoidOverlap: true,
    nodeSpacing: () => 16,
    edgeLength: () => 120,
    randomize: true,
    maxSimulationTime: 2000,
    convergenceThreshold: 0.01,
  } as cytoscape.LayoutOptions,
  dagre: {
    name: "dagre",
    animate: true,
    fit: true,
    rankDir: "LR",
    rankSep: 90,
    nodeSep: 60,
  } as cytoscape.LayoutOptions,
  concentric: {
    name: "concentric",
    animate: true,
    concentric: (n) => (n.data("weight") as number) ?? 1,
    levelWidth: () => 1,
    minNodeSpacing: 40,
    fit: true,
  },
  circle: { name: "circle", animate: true, fit: true },
};

// Keep the graph neat and readable: render only the most relevant nodes by
// default. The user can reveal more in 20-node steps (consent) or show all.
// Capping also keeps the cola simulation fast and inside the bounded box.
const DEFAULT_NODE_CAP = 20;
const NODE_CAP_STEP = 20;
// Above this many rendered nodes, switch to a flat "performance" node style
// (no per-node gradient / text-outline) so dense graphs stay smooth.
const PERF_NODE_THRESHOLD = 120;

export function KnowledgeGraph({
  graph,
  layout,
  selectedNodeId,
  highlightedPathNodeIds,
  searchQuery,
  hiddenEdgeTypes,
  onCyReady,
  onSelectNode,
  onSelectEdge,
  onExpand,
  onCollapse,
  onMarkSource,
  onMarkSink,
  onClearRoles,
  onShowEvidence,
  onTogglePin,
  onRemove,
}: Props) {
  const { colorMode } = useColorMode();
  const cyRef = useRef<Core | null>(null);
  const containerElRef = useRef<HTMLDivElement | null>(null);
  // Manual double-tap detector (Cytoscape has no native dblclick) — powers the
  // Neo4j-style "double-click a node to expand its neighbourhood" interaction.
  const lastTapRef = useRef<{ id: string; t: number }>({ id: "", t: 0 });
  const [ready, setReady] = useState(false);
  const [initError, setInitError] = useState<string | null>(null);

  // Fit / zoom helpers for the floating control cluster (mirrors Neo4j Browser).
  const zoomBy = useCallback((factor: number) => {
    const cy = cyRef.current;
    if (!cy) return;
    const z = cy.zoom() * factor;
    cy.animate({ zoom: { level: z, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } } }, { duration: 180 });
  }, []);
  const fitView = useCallback(() => {
    cyRef.current?.animate({ fit: { eles: cyRef.current.elements(), padding: 60 } }, { duration: 220 });
  }, []);
  // How many nodes the user has consented to see. Resets to the default cap on
  // each new graph; "Show more"/"Show all" raise it.
  const [nodeCap, setNodeCap] = useState(DEFAULT_NODE_CAP);

  const totalNodes = graph.nodes.length;
  // Reset the cap whenever a new reasoning graph arrives (new question).
  useEffect(() => {
    setNodeCap(DEFAULT_NODE_CAP);
  }, [totalNodes]);

  const handlersRef = useRef<KnowledgeGraphHandlers>({});
  handlersRef.current = {
    onSelectNode,
    onSelectEdge,
    onExpand,
    onCollapse,
    onMarkSource,
    onMarkSink,
    onClearRoles,
    onShowEvidence,
    onTogglePin,
    onRemove,
  };
  // Track which nodes the user has expanded so double-click can toggle collapse.
  const expandedRef = useRef<Set<string>>(new Set());

  /**
   * Ref callback — fires exactly when the <div> mounts/unmounts.
   * This is the only reliable way to initialise a native Cytoscape instance
   * against an arbitrary React lifecycle. useEffect+useRef is racy: if the
   * canvas <div> first mounts inside a conditional branch (e.g. after an
   * empty-state swap), useEffect([]) has already captured a null ref and
   * will not re-run.
   */
  const attachContainer = useCallback((el: HTMLDivElement | null) => {
    containerElRef.current = el;
    if (!el) {
      cyRef.current?.destroy();
      cyRef.current = null;
      onCyReady?.(null);
      setReady(false);
      return;
    }
    if (cyRef.current) return; // already initialised

    try {
      const cy = cytoscape({
        container: el,
        wheelSensitivity: 0.25,
        style: cytoscapeStylesheet(colorMode),
        elements: [],
        minZoom: 0.12,
        maxZoom: 3.5,
        // Scale/perf: render hints keep large graphs smooth.
        boxSelectionEnabled: true, // shift-drag to multi-select
        hideEdgesOnViewport: true, // drop edges while panning/zooming
        textureOnViewport: true, // bitmap cache during interaction
        motionBlur: false,
        pixelRatio: 1,
      });
      cyRef.current = cy;
      onCyReady?.(cy);

      cy.on("tap", "node", (evt) => {
        const id = evt.target.id();
        handlersRef.current.onSelectNode?.(id);
        // Double-tap → toggle expand⇄collapse of the node's neighbourhood
        // (Neo4j Browser parity).
        const now = Date.now();
        const prev = lastTapRef.current;
        if (prev.id === id && now - prev.t < 320) {
          if (expandedRef.current.has(id)) {
            handlersRef.current.onCollapse?.(id);
            expandedRef.current.delete(id);
          } else {
            handlersRef.current.onExpand?.(id, 1);
            expandedRef.current.add(id);
          }
          lastTapRef.current = { id: "", t: 0 };
        } else {
          lastTapRef.current = { id, t: now };
        }
      });
      cy.on("tap", "edge", (evt) => {
        handlersRef.current.onSelectEdge?.(evt.target.id());
      });
      cy.on("tap", (evt) => {
        if (evt.target === cy) {
          handlersRef.current.onSelectNode?.(null);
          handlersRef.current.onSelectEdge?.(null);
        }
      });

      // ── Hover spotlight: fade everything except the hovered node, its direct
      //    neighbours and the connecting edges. This is the single most
      //    recognisable Neo4j Browser interaction and makes dense relationship
      //    fans instantly readable.
      cy.on("mouseover", "node", (evt) => {
        const n = evt.target as cytoscape.NodeSingular;
        const keep = n.closedNeighborhood();
        cy.batch(() => {
          cy.elements().difference(keep).addClass("faded");
          keep.addClass("spotlight");
          n.addClass("spotlight-core");
        });
        const c = cy.container();
        if (c) c.style.cursor = "pointer";
      });
      cy.on("mouseout", "node", () => {
        cy.batch(() => {
          cy.elements().removeClass("faded spotlight spotlight-core");
        });
        const c = cy.container();
        if (c) c.style.cursor = "default";
      });

      try {
        // @ts-expect-error — cxtmenu plugin, registered in cyRegistry
        cy.cxtmenu({
          selector: "node",
          menuRadius: 96,
          fillColor: "rgba(12, 16, 28, 0.94)",
          activeFillColor: "rgba(58, 79, 247, 0.85)",
          activePadding: 4,
          indicatorSize: 20,
          separatorWidth: 3,
          spotlightPadding: 6,
          openMenuEvents: "cxttap",
          itemColor: "#f5f7fb",
          itemTextShadowColor: "transparent",
          commands: [
            { content: "⤢ Expand", select: (n: cytoscape.NodeSingular) => { handlersRef.current.onExpand?.(n.id(), 1); expandedRef.current.add(n.id()); } },
            { content: "⤡ Collapse", select: (n: cytoscape.NodeSingular) => { handlersRef.current.onCollapse?.(n.id()); expandedRef.current.delete(n.id()); } },
            { content: "◉ Source", select: (n: cytoscape.NodeSingular) => handlersRef.current.onMarkSource?.(n.id()) },
            { content: "◎ Sink", select: (n: cytoscape.NodeSingular) => handlersRef.current.onMarkSink?.(n.id()) },
            { content: "🔎 Evidence", select: (n: cytoscape.NodeSingular) => handlersRef.current.onShowEvidence?.(n.id()) },
            { content: "📌 Pin/Unpin", select: (n: cytoscape.NodeSingular) => handlersRef.current.onTogglePin?.(n.id()) },
            { content: "✕ Remove", select: (n: cytoscape.NodeSingular) => handlersRef.current.onRemove?.(n.id()) },
          ],
        });
      } catch (e) {
        // eslint-disable-next-line no-console
        console.warn("cxtmenu init failed — right-click menu disabled", e);
      }

      setReady(true);
    } catch (e) {
      const msg = (e as Error).message ?? String(e);
      // eslint-disable-next-line no-console
      console.error("cytoscape init failed", e);
      setInitError(msg);
    }
  }, []);

  // --- Elements reconciled whenever graph/layout change -------------------
  const elements: ElementDefinition[] = useMemo(() => {
    const q = (searchQuery ?? "").trim().toLowerCase();
    const hidden = hiddenEdgeTypes ?? new Set<string>();
    // Cap rendered nodes to keep the canvas responsive: keep the highest-weight
    // (most-connected/relevant) nodes plus any on the highlighted path.
    let nodes = graph.nodes;
    if (nodes.length > nodeCap) {
      nodes = [...nodes]
        .sort(
          (a, b) =>
            (highlightedPathNodeIds.has(b.id) ? Infinity : b.weight ?? 1) -
            (highlightedPathNodeIds.has(a.id) ? Infinity : a.weight ?? 1)
        )
        .slice(0, nodeCap);
    }
    const shownIds = new Set(nodes.map((n) => n.id));
    const perf = nodes.length > PERF_NODE_THRESHOLD;
    return [
      ...nodes.map<ElementDefinition>((n) => {
        const matchesSearch =
          !q ||
          (n.caption ?? "").toLowerCase().includes(q) ||
          n.id.toLowerCase().includes(q) ||
          (n.category ?? "").toLowerCase().includes(q);
        return {
          group: "nodes",
          data: {
            id: n.id,
            label: n.caption ?? n.id,
            category: n.category ?? "UNKNOWN",
            weight: n.weight ?? 1,
            role: n.role ?? "none",
          },
          classes: [
            classesForNode(n, highlightedPathNodeIds),
            q && !matchesSearch ? "dim" : "",
            perf ? "perf" : "",
            `shape-${shapeForCategory(n.category)}`,
          ]
            .filter(Boolean)
            .join(" "),
        };
      }),
      ...graph.rels
        .filter(
          (r) =>
            !hidden.has(r.type ?? "") &&
            shownIds.has(r.from) &&
            shownIds.has(r.to)
        )
        .map<ElementDefinition>((r) => ({
          group: "edges",
          data: {
            id: r.id,
            source: r.from,
            target: r.to,
            label: r.caption ?? r.type ?? "",
          },
          classes: [classesForEdge(r), perf ? "perf" : ""]
            .filter(Boolean)
            .join(" "),
        })),
    ];
  }, [graph, highlightedPathNodeIds, searchQuery, hiddenEdgeTypes, nodeCap]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !ready) return;
    cy.batch(() => {
      cy.elements().remove();
      cy.add(elements);
    });
    if (elements.length === 0) return;

    // Defer one RAF so container has layout-measured dimensions
    requestAnimationFrame(() => {
      cy.resize();
      const runLayout = (cfg: cytoscape.LayoutOptions): boolean => {
        try {
          const lo = cy.layout(cfg);
          lo.one("layoutstop", () => cy.fit(undefined, 60));
          lo.run();
          return true;
        } catch (e) {
          // eslint-disable-next-line no-console
          console.warn(`layout ${cfg.name} failed`, e);
          return false;
        }
      };
      const ok =
        runLayout(LAYOUT_CONFIG[layout]) ||
        runLayout(LAYOUT_CONFIG["concentric"]) ||
        runLayout({ name: "grid", animate: false } as cytoscape.LayoutOptions);
      if (!ok) {
        cy.nodes().forEach((n, i, arr) => {
          const angle = (i / Math.max(arr.length, 1)) * Math.PI * 2;
          n.position({ x: 300 + 220 * Math.cos(angle), y: 300 + 220 * Math.sin(angle) });
        });
        cy.fit(undefined, 60);
      }
    });
  }, [elements, layout, ready]);

  // Pin-lock: pinned nodes stay put while the layout simulates around them.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !ready) return;
    cy.batch(() => {
      cy.nodes().forEach((n) => {
        if (n.hasClass("pinned")) n.lock();
        else n.unlock();
      });
    });
  }, [elements, ready]);

  // Keep canvas sized to container
  useEffect(() => {
    const el = containerElRef.current;
    const cy = cyRef.current;
    if (!el || !cy) return;
    const ro = new ResizeObserver(() => {
      cy.resize();
      if (cy.nodes().length) cy.fit(undefined, 60);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [ready]);

  // Selection sync
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.$(".selected").removeClass("selected");
    if (selectedNodeId) {
      const n = cy.getElementById(selectedNodeId);
      if (n && n.nonempty()) n.addClass("selected");
    }
  }, [selectedNodeId]);

  // Re-apply stylesheet on color-mode flip (edge colors, text outlines, etc.
  // must be legible against both dark and light canvases).
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !ready) return;
    cy.style(cytoscapeStylesheet(colorMode));
  }, [colorMode, ready]);

  const shownNodes = Math.min(nodeCap, totalNodes);
  const isCapped = totalNodes > nodeCap;

  return (
    <Box
      position="absolute"
      inset={3}
      borderRadius="xl"
      border="1px solid"
      borderColor="border.subtle"
      overflow="hidden"
      bg={colorMode === "dark" ? "rgba(8,11,20,0.55)" : "rgba(248,250,255,0.6)"}
    >
      {/* The canvas container is ALWAYS mounted — Cytoscape needs a stable DOM node. */}
      <Box ref={attachContainer} position="absolute" inset={0} />

      {/* Result-count / consent caption: the graph shows only the top N nodes. */}
      {totalNodes > 0 && (
        <HStack
          position="absolute"
          top={2}
          left={2}
          right={2}
          spacing={2}
          align="center"
          bg={colorMode === "dark" ? "rgba(10,14,24,0.82)" : "rgba(255,255,255,0.9)"}
          backdropFilter="blur(8px)"
          border="1px solid"
          borderColor="border.subtle"
          borderRadius="lg"
          px={3}
          py={1.5}
          fontSize="xs"
          zIndex={5}
        >
          <Text color="text.muted" noOfLines={1}>
            {isCapped ? (
              <>
                Showing top <b>{shownNodes}</b> of <b>{totalNodes}</b> nodes for
                a clean view. Want more?
              </>
            ) : (
              <>
                Showing all <b>{totalNodes}</b> node{totalNodes === 1 ? "" : "s"}.
              </>
            )}
          </Text>
          {isCapped && (
            <HStack spacing={1} ml="auto">
              <Button
                size="xs"
                variant="outline"
                onClick={() =>
                  setNodeCap((c) => Math.min(c + NODE_CAP_STEP, totalNodes))
                }
              >
                +{Math.min(NODE_CAP_STEP, totalNodes - nodeCap)} more
              </Button>
              <Button
                size="xs"
                colorScheme="accent"
                onClick={() => setNodeCap(totalNodes)}
              >
                Show all ({totalNodes})
              </Button>
            </HStack>
          )}
          {!isCapped && totalNodes > DEFAULT_NODE_CAP && (
            <Button
              size="xs"
              variant="ghost"
              ml="auto"
              onClick={() => setNodeCap(DEFAULT_NODE_CAP)}
            >
              Collapse
            </Button>
          )}
        </HStack>
      )}

      {/* Floating zoom / fit control cluster — mirrors Neo4j Browser's
          bottom-right controls (zoom in / out / fit / re-center). */}
      {totalNodes > 0 && (
        <VStack
          position="absolute"
          bottom={3}
          right={3}
          spacing={1}
          zIndex={5}
          bg={colorMode === "dark" ? "rgba(10,14,24,0.82)" : "rgba(255,255,255,0.9)"}
          backdropFilter="blur(8px)"
          border="1px solid"
          borderColor="border.subtle"
          borderRadius="lg"
          p={1}
          boxShadow="0 8px 24px -12px rgba(0,0,0,0.5)"
        >
          {[
            { icon: <LuPlus />, label: "Zoom in", fn: () => zoomBy(1.3) },
            { icon: <LuMinus />, label: "Zoom out", fn: () => zoomBy(1 / 1.3) },
            { icon: <LuMaximize2 />, label: "Fit to view", fn: fitView },
            { icon: <LuLocate />, label: "Re-center", fn: () => cyRef.current?.animate({ center: { eles: cyRef.current.elements() } }, { duration: 180 }) },
          ].map((b) => (
            <Tooltip key={b.label} label={b.label} placement="left" openDelay={300} fontSize="xs">
              <IconButton
                aria-label={b.label}
                icon={b.icon}
                size="sm"
                variant="ghost"
                color="text.muted"
                _hover={{ color: "text.primary", bg: "surface.300" }}
                onClick={b.fn}
              />
            </Tooltip>
          ))}
        </VStack>
      )}

      {/* Empty state overlay (pointer-events: none so it doesn't block canvas interactions) */}
      {graph.nodes.length === 0 && !initError && (
        <VStack
          position="absolute"
          inset={0}
          justify="center"
          color="text.muted"
          spacing={4}
          px={8}
          py={6}
          pointerEvents="none"
        >
          <Box
            w="120px"
            h="120px"
            borderRadius="full"
            bgGradient="radial(accent.500, transparent 70%)"
            opacity={0.4}
          />
          <Text fontSize="sm" textAlign="center" maxW="320px">
            Ask the agent a question and its reasoning graph will appear here.
            Double-click a node to expand it, hover to spotlight its
            neighbourhood, or right-click for paths and evidence.
          </Text>
        </VStack>
      )}

      {initError && (
        <VStack
          position="absolute"
          inset={0}
          justify="center"
          color="signal.danger"
          spacing={3}
          px={8}
          py={6}
        >
          <Text fontSize="sm" fontWeight={600}>
            Graph failed to initialise
          </Text>
          <Text fontSize="xs" fontFamily="mono" color="text.muted" textAlign="center">
            {initError}
          </Text>
        </VStack>
      )}
    </Box>
  );
}

// --- Styling helpers -------------------------------------------------------

/**
 * Map node category → Cytoscape shape. Mirrors the Bessemer Ontology Explorer
 * convention: structural nodes are square, documents/references are diamonds,
 * individuals (drugs, diseases, etc.) stay round.
 */
function shapeForCategory(cat: string | undefined): string {
  const c = (cat ?? "UNKNOWN").toUpperCase();
  if (/(PATENT|USPTO|PUBMED|DOCUMENT|SUMMARY|TPP|RESEARCH)/.test(c)) return "diamond";
  if (/(ORGANIZATION|CARRIER|SPONSOR|COLLABORATOR|FUNDER)/.test(c)) return "square";
  if (/(CLINICAL_TRIAL|PHASE|CONDITION|INTERVENTION|OUTCOME)/.test(c)) return "hexagon";
  if (/(PATHWAY|BIOLOGICAL_PROCESS|MOLECULAR_FUNCTION|CELLULAR_COMPONENT)/.test(c))
    return "round-rectangle";
  return "ellipse";
}

function classesForNode(n: GraphNode, pathSet: Set<string>): string {
  const c = [`cat-${(n.category ?? "UNKNOWN").toLowerCase()}`];
  if (n.role === "source") c.push("source");
  if (n.role === "sink") c.push("sink");
  if (n.pinned) c.push("pinned");
  if (pathSet.has(n.id)) c.push("on-path");
  return c.join(" ");
}

function classesForEdge(r: GraphRelationship): string {
  return r.onPath ? "on-path" : "";
}

/**
 * Stable colour for a given relationship type. Inspired by the Bessemer
 * ontology explorer, where each rel type has a distinct colour (subClassOf
 * green, relation orange, etc.). Consistent colours let users mentally group
 * edges across layouts.
 */
function colorForRelType(type: string | undefined, mode: "light" | "dark"): string {
  const t = (type ?? "").toLowerCase();
  // Two-tone palette: bright for dark mode, deeper for light mode contrast.
  const PALETTE: Array<[RegExp, string, string]> = [
    // rel match               dark hex    light hex
    [/drug_protein|drug_target/, "#3ecab4", "#0f8c79"],
    [/protein_protein|gene_protein|ppi/, "#7c8cff", "#3a4ff7"],
    [/disease_protein|indication|contraindication/, "#ff5d7a", "#c4244a"],
    [/pathway/, "#f8c26b", "#b87a17"],
    [/drug_effect|side_effect|effect_phenotype/, "#ff9566", "#d65b2c"],
    [/anatomy/, "#d4a5ff", "#8a4ed1"],
    [/patent|disclosed_in/, "#ffd37f", "#b87f15"],
    [/pubmed|publication|has_publication/, "#a5b0ff", "#5d6edb"],
    [/clinical_trial|featured_in|trial/, "#5d70ff", "#2c3dd6"],
    [/alias|synonym/, "#23a591", "#0a6f60"],
  ];
  for (const [re, dark, light] of PALETTE) if (re.test(t)) return mode === "dark" ? dark : light;
  return mode === "dark" ? "#9aa3bb" : "#4a5268";
}

function cytoscapeStylesheet(mode: "light" | "dark"): cytoscape.StylesheetStyle[] {
  const isDark = mode === "dark";

  // ── 2026 Aurora palette tokens (must mirror theme/index.ts) ──────────
  const textColor      = isDark ? "#f6f9ff" : "#0d1220";
  const textOutline    = isDark ? "#06080d" : "#ffffff";
  const nodeBorder     = isDark ? "rgba(255,255,255,0.18)" : "rgba(20,30,60,0.18)";
  const edgeLabelBg    = isDark ? "#0f1320" : "#ffffff";
  const edgeLabelColor = isDark ? "#dbe3f5" : "#3a4258";
  const selectedRing   = isDark ? "#7d8eff" : "#4256f5";  // accent.300/500
  const auroraCyan     = "#1bb8e0";
  const auroraIndigo   = "#4256f5";
  const auroraMagenta  = "#ff2a9d";
  const auroraGold     = "#ffc561";
  const auroraDanger   = "#ff5e7a";

  return [
    // ── Shapes ────────────────────────────────────────────────────────
    { selector: "node.shape-ellipse",         style: { shape: "ellipse" } as unknown as cytoscape.Css.Node },
    { selector: "node.shape-square",          style: { shape: "round-rectangle" } as unknown as cytoscape.Css.Node },
    { selector: "node.shape-diamond",         style: { shape: "diamond" } as unknown as cytoscape.Css.Node },
    { selector: "node.shape-hexagon",         style: { shape: "hexagon" } as unknown as cytoscape.Css.Node },
    { selector: "node.shape-round-rectangle", style: { shape: "round-rectangle" } as unknown as cytoscape.Css.Node },

    // ── Base node — radial gradient + soft border ────────────────────
    {
      selector: "node",
      style: {
        width: "mapData(weight, 1, 5, 46, 92)",
        height: "mapData(weight, 1, 5, 46, 92)",
        // Gradient fill: bright top → deeper bottom (2026 look)
        "background-fill": "radial-gradient",
        "background-gradient-stop-colors": (ele: cytoscape.NodeSingular) => {
          const c = colorForCategory(ele.data("category"));
          return `${lighten(c, 0.18)} ${c} ${darken(c, 0.22)}`;
        },
        "background-gradient-stop-positions": "0 50 100",
        "background-color": (ele: cytoscape.NodeSingular) => colorForCategory(ele.data("category")),
        "background-opacity": 0.97,
        "border-width": 1.5,
        "border-color": nodeBorder,
        "border-opacity": 1,
        label: "data(label)",
        color: textColor,
        "text-outline-color": textOutline,
        "text-outline-width": 3,
        "text-outline-opacity": 0.95,
        "font-size": 11,
        // Level-of-detail: hide the caption once it would render below this
        // pixel size (i.e. when zoomed out) — keeps dense graphs uncluttered.
        "min-zoomed-font-size": 7,
        "font-family": "Inter, Geist, system-ui, sans-serif",
        "font-weight": 500,
        "text-valign": "center",
        "text-halign": "center",
        "text-wrap": "ellipsis",
        "text-max-width": 110,
        // Subtle glow on hover via overlay
        "overlay-padding": 4,
        "overlay-opacity": 0,
      } as unknown as cytoscape.Css.Node,
    },

    // ── Base edge — type-coloured, smooth bezier, pill label ─────────
    {
      selector: "edge",
      style: {
        width: 1.8,
        "line-color": (ele: cytoscape.EdgeSingular) => colorForRelType(ele.data("label"), mode),
        "line-opacity": isDark ? 0.88 : 0.82,
        "curve-style": "bezier",
        "control-point-step-size": 40,
        "target-arrow-shape": "triangle-backcurve",
        "target-arrow-color": (ele: cytoscape.EdgeSingular) => colorForRelType(ele.data("label"), mode),
        "arrow-scale": 1.15,
        label: "data(label)",
        "font-size": 9,
        // Edge labels are noisier — drop them sooner when zoomed out.
        "min-zoomed-font-size": 10,
        "font-weight": 500,
        color: edgeLabelColor,
        "text-background-color": edgeLabelBg,
        "text-background-opacity": 0.92,
        "text-background-padding": 4,
        "text-background-shape": "round-rectangle",
        "text-border-width": 1,
        "text-border-color": isDark ? "rgba(255,255,255,0.10)" : "rgba(0,0,0,0.10)",
        "text-border-opacity": 1,
        "text-rotation": "autorotate",
      } as unknown as cytoscape.Css.Edge,
    },

    // ── Hover (no native :hover for nodes; still useful for plain edge) ─
    {
      selector: "node:active",
      style: {
        "overlay-color": auroraIndigo,
        "overlay-opacity": 0.18,
        "overlay-padding": 12,
      } as unknown as cytoscape.Css.Node,
    },

    // ── Selection: aurora ring + outer glow halo ─────────────────────
    {
      selector: "node:selected, node.selected",
      style: {
        "border-color": selectedRing,
        "border-width": 4,
        "overlay-color": auroraIndigo,
        "overlay-opacity": 0.22,
        "overlay-padding": 14,
        "z-index": 999,
      } as unknown as cytoscape.Css.Node,
    },

    // ── Roles (path source/sink) ─────────────────────────────────────
    {
      selector: "node.source",
      style: {
        "border-color": auroraCyan,
        "border-width": 5,
        "overlay-color": auroraCyan,
        "overlay-opacity": 0.18,
        "overlay-padding": 10,
      } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "node.sink",
      style: {
        "border-color": auroraMagenta,
        "border-width": 5,
        "overlay-color": auroraMagenta,
        "overlay-opacity": 0.18,
        "overlay-padding": 10,
      } as unknown as cytoscape.Css.Node,
    },

    // ── Pinned & on-path & dim ───────────────────────────────────────
    {
      selector: "node.pinned",
      style: { "border-style": "dashed", "border-width": 3 } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "node.on-path",
      style: {
        "border-color": auroraGold,
        "border-width": 3,
        "overlay-color": auroraGold,
        "overlay-opacity": 0.14,
        "overlay-padding": 8,
      } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "node.dim",
      style: { opacity: 0.12 } as unknown as cytoscape.Css.Node,
    },

    // ── Performance mode (dense graphs): flat fill, no text-outline, no
    //    edge labels — drops per-element cost so 100s of nodes stay smooth.
    {
      selector: "node.perf",
      style: {
        "background-fill": "solid",
        "background-color": (ele: cytoscape.NodeSingular) =>
          colorForCategory(ele.data("category")),
        "text-outline-width": 1.5,
        "border-width": 0.75,
        width: "mapData(weight, 1, 5, 28, 60)",
        height: "mapData(weight, 1, 5, 28, 60)",
      } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "edge.perf",
      style: {
        label: "",
        width: 1.1,
        "line-opacity": isDark ? 0.5 : 0.45,
      } as unknown as cytoscape.Css.Edge,
    },

    // ── Hover spotlight (Neo4j-style neighbourhood focus) ─────────────
    {
      selector: ".faded",
      style: {
        opacity: isDark ? 0.08 : 0.12,
        "text-opacity": 0.05,
        "transition-property": "opacity, text-opacity",
        "transition-duration": "0.18s" as unknown as number,
      } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "node.spotlight",
      style: {
        "border-width": 2.5,
        "border-color": auroraCyan,
        "z-index": 50,
      } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "node.spotlight-core",
      style: {
        "border-width": 4,
        "border-color": auroraIndigo,
        "overlay-color": auroraIndigo,
        "overlay-opacity": 0.18,
        "overlay-padding": 12,
        "z-index": 60,
      } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "edge.spotlight",
      style: {
        width: 3,
        "line-opacity": 1,
        "z-index": 55,
      } as unknown as cytoscape.Css.Edge,
    },
    {
      selector: "edge.dim",
      style: { opacity: 0.10 } as unknown as cytoscape.Css.Edge,
    },
    {
      selector: "edge.on-path",
      style: {
        "line-color": auroraGold,
        "target-arrow-color": auroraGold,
        width: 3.2,
      } as unknown as cytoscape.Css.Edge,
    },
    {
      selector: "edge:selected",
      style: {
        "line-color": selectedRing,
        "target-arrow-color": selectedRing,
        width: 3,
        "z-index": 998,
      } as unknown as cytoscape.Css.Edge,
    },
  ];
}

// ── Tiny colour helpers for gradient stops (no extra dependency) ────────
function clamp(v: number) {
  return Math.max(0, Math.min(255, v));
}
function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  const n = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  return [
    parseInt(n.slice(0, 2), 16),
    parseInt(n.slice(2, 4), 16),
    parseInt(n.slice(4, 6), 16),
  ];
}
function rgbToHex(r: number, g: number, b: number): string {
  return "#" + [r, g, b].map((v) => clamp(Math.round(v)).toString(16).padStart(2, "0")).join("");
}
function lighten(hex: string, amt: number): string {
  const [r, g, b] = hexToRgb(hex);
  return rgbToHex(r + (255 - r) * amt, g + (255 - g) * amt, b + (255 - b) * amt);
}
function darken(hex: string, amt: number): string {
  const [r, g, b] = hexToRgb(hex);
  return rgbToHex(r * (1 - amt), g * (1 - amt), b * (1 - amt));
}
