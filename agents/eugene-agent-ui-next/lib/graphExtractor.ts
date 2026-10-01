import type {
  ContextGraph,
  GraphNode,
  GraphRelationship,
  Provenance,
  ToolInvocation,
} from "./types";
import { normalizeApiResponse } from "./graphApi";

/**
 * Live context-graph builder.
 *
 * Delegates all shape recognition to the universal `normalizeApiResponse`
 * deep-walker, so every tool output across Eugene's domain contributes real
 * nodes/edges. Each emission is annotated with provenance for XAI traceability.
 */
export class GraphExtractor {
  private nodes = new Map<string, GraphNode>();
  private rels = new Map<string, GraphRelationship>();

  ingest(invocation: ToolInvocation): ContextGraph {
    const prov: Provenance = {
      source: "tool_call",
      toolId: invocation.toolId,
      toolName: invocation.tool,
      turnId: invocation.turnId,
      cypherHint: cypherHintFor(invocation),
      parentNodeIds: idsInObject(invocation.input),
      timestamp: Date.now(),
    };

    // Normalise input (so nodes referenced by tool args get seeded too)
    const { nodes: inNodes } = normalizeApiResponse(invocation.input);
    for (const n of inNodes) this.mergeNode(n, prov);

    if (invocation.output !== undefined) {
      const { nodes, rels } = normalizeApiResponse(invocation.output);
      for (const n of nodes) this.mergeNode(n, prov);
      for (const r of rels) this.mergeRel(r, prov);
    }
    return this.snapshot();
  }

  mergeExternal(
    extNodes: GraphNode[],
    extRels: GraphRelationship[],
    prov: Provenance
  ): ContextGraph {
    for (const n of extNodes) this.mergeNode(n, prov);
    for (const r of extRels) this.mergeRel(r, prov);
    return this.snapshot();
  }

  /**
   * Seed the graph from a pre-built ContextGraph (dev demo / fixture). Preserves
   * each element's provenance so the Evidence chain works, and optionally stamps
   * a turnId so inline citations can be resolved via `nodesForTurn`.
   */
  seed(
    extNodes: GraphNode[],
    extRels: GraphRelationship[],
    turnId?: string
  ): ContextGraph {
    this.reset();
    for (const n of extNodes) {
      const provenance =
        n.provenance && n.provenance.length
          ? n.provenance.map((p) => ({ ...p, turnId: p.turnId ?? turnId }))
          : [{ source: "tool_call" as const, turnId, timestamp: Date.now() }];
      this.nodes.set(n.id, {
        ...n,
        provenance,
        role: n.role ?? null,
        pinned: n.pinned ?? false,
      });
    }
    for (const r of extRels) {
      this.rels.set(r.id, {
        ...r,
        provenance: r.provenance ?? [
          { source: "tool_call", turnId, timestamp: Date.now() },
        ],
        onPath: r.onPath ?? false,
      });
    }
    return this.snapshot();
  }

  /** Nodes a given conversation turn contributed (for inline citations). */
  nodesForTurn(turnId: string): GraphNode[] {
    return Array.from(this.nodes.values()).filter((n) =>
      (n.provenance ?? []).some((p) => p.turnId === turnId)
    );
  }

  setRole(nodeId: string, role: GraphNode["role"]): ContextGraph {
    const n = this.nodes.get(nodeId);
    if (n) n.role = role;
    return this.snapshot();
  }

  clearRoleFor(role: NonNullable<GraphNode["role"]>): ContextGraph {
    for (const n of this.nodes.values()) {
      if (n.role === role) n.role = null;
    }
    return this.snapshot();
  }

  markPath(nodeIds: Set<string>, relIds: Set<string>): ContextGraph {
    for (const n of this.nodes.values())
      n.role = nodeIds.has(n.id) ? n.role ?? "on_path" : n.role;
    for (const r of this.rels.values()) r.onPath = relIds.has(r.id);
    return this.snapshot();
  }

  clearPathHighlights(): ContextGraph {
    for (const n of this.nodes.values()) if (n.role === "on_path") n.role = null;
    for (const r of this.rels.values()) r.onPath = false;
    return this.snapshot();
  }

  remove(nodeId: string): ContextGraph {
    this.nodes.delete(nodeId);
    for (const [id, r] of this.rels) {
      if (r.from === nodeId || r.to === nodeId) this.rels.delete(id);
    }
    return this.snapshot();
  }

  /**
   * Collapse the neighbourhood a node introduced: remove the non-pinned leaf
   * nodes that were brought in by expanding `nodeId` (provenance: user_expand
   * with this node as parent) and that hang off it alone (degree ≤ 1). Inverse
   * of `expand`; lets the user contract a fan they opened.
   */
  collapse(nodeId: string): ContextGraph {
    const degree = new Map<string, number>();
    for (const r of this.rels.values()) {
      degree.set(r.from, (degree.get(r.from) ?? 0) + 1);
      degree.set(r.to, (degree.get(r.to) ?? 0) + 1);
    }
    const toRemove: string[] = [];
    for (const n of this.nodes.values()) {
      if (n.pinned || n.id === nodeId) continue;
      const introducedByThis = (n.provenance ?? []).some(
        (p) =>
          p.source === "user_expand" &&
          (p.parentNodeIds ?? []).includes(nodeId)
      );
      if (introducedByThis && (degree.get(n.id) ?? 0) <= 1) toRemove.push(n.id);
    }
    for (const id of toRemove) this.remove(id);
    return this.snapshot();
  }

  getNode(id: string): GraphNode | undefined {
    return this.nodes.get(id);
  }

  /** Walk provenance leaf→root starting from `nodeId`. */
  evidenceChain(nodeId: string): GraphNode[] {
    const chain: GraphNode[] = [];
    const seen = new Set<string>();
    const walk = (id: string) => {
      if (seen.has(id)) return;
      seen.add(id);
      const n = this.nodes.get(id);
      if (!n) return;
      chain.push(n);
      const parents = new Set<string>();
      for (const p of n.provenance ?? []) {
        for (const pid of p.parentNodeIds ?? []) parents.add(pid);
      }
      parents.forEach(walk);
    };
    walk(nodeId);
    return chain;
  }

  snapshot(): ContextGraph {
    return {
      nodes: Array.from(this.nodes.values()),
      rels: Array.from(this.rels.values()),
    };
  }

  reset(): void {
    this.nodes.clear();
    this.rels.clear();
  }

  // --- internals ----------------------------------------------------------

  private mergeNode(incoming: GraphNode, prov: Provenance): void {
    const existing = this.nodes.get(incoming.id);
    if (existing) {
      existing.weight = (existing.weight ?? 0) + 0.25;
      if (incoming.caption && (!existing.caption || existing.caption === existing.id))
        existing.caption = incoming.caption;
      if (incoming.category && (!existing.category || existing.category === "UNKNOWN"))
        existing.category = incoming.category;
      if (incoming.labels && !existing.labels) existing.labels = incoming.labels;
      if (incoming.properties)
        existing.properties = { ...existing.properties, ...incoming.properties };
      existing.provenance = [...(existing.provenance ?? []), prov];
      return;
    }
    this.nodes.set(incoming.id, {
      ...incoming,
      provenance: [prov],
      role: null,
      pinned: false,
    });
  }

  private mergeRel(incoming: GraphRelationship, prov: Provenance): void {
    const existing = this.rels.get(incoming.id);
    if (existing) {
      existing.provenance = [...(existing.provenance ?? []), prov];
      if (incoming.properties)
        existing.properties = { ...existing.properties, ...incoming.properties };
      return;
    }
    this.rels.set(incoming.id, {
      ...incoming,
      provenance: [prov],
      onPath: false,
    });
  }
}

function idsInObject(input: Record<string, unknown> | undefined): string[] {
  if (!input) return [];
  const keys = [
    "node_id",
    "id",
    "org_id",
    "drug_id",
    "patent_id",
    "nct_id",
    "pmid",
    "organization_id",
    "start_node_id",
    "end_node_id",
  ];
  const out: string[] = [];
  for (const k of keys) {
    const v = input[k];
    if (typeof v === "string") out.push(v);
    if (Array.isArray(v))
      for (const x of v) if (typeof x === "string") out.push(x);
  }
  return out;
}

function cypherHintFor(inv: ToolInvocation): string {
  const input = inv.input ?? {};
  const label = (input.label ?? input.node_label) as string | undefined;
  const name = (input.node_name ?? input.name ?? input.organization_name) as
    | string
    | undefined;
  const id = (input.node_id ?? input.id ?? input.organization_id) as string | undefined;
  const from = input.start_node_id as string | undefined;
  const to = input.end_node_id as string | undefined;
  const query = input.query as string | undefined;
  // Hybrid retrieval: there is no single Cypher equivalent (half the work happens
  // in Milvus), so describe both legs rather than inventing a query that lies.
  if (inv.tool.includes("fused") && query) {
    return `fulltext('${query}') ⊕ vector('${query}') → reciprocal rank fusion`;
  }
  if (inv.tool.includes("path") && from && to) {
    return `MATCH p=shortestPath((a {node_id:'${from}'})-[*..4]-(b {node_id:'${to}'})) RETURN p`;
  }
  if (inv.tool.includes("relationship") && id) {
    return `MATCH (n {node_id:'${id}'})-[r*..2]-(m) RETURN n,r,m`;
  }
  if (inv.tool.includes("label") && label) {
    return `MATCH (n:${label})${name ? ` WHERE n.node_name='${name}'` : ""} RETURN n LIMIT 50`;
  }
  if ((inv.tool.includes("find") || inv.tool.includes("lookup")) && name) {
    return `MATCH (n) WHERE n.node_name =~ '(?i).*${name}.*' RETURN n LIMIT 25`;
  }
  if (inv.tool.includes("organization") && name) {
    return `MATCH (o:Organisation) WHERE o.node_name =~ '(?i).*${name}.*' RETURN o`;
  }
  return `call ${inv.tool}(${JSON.stringify(input).slice(0, 80)}…)`;
}

/** Stable color palette for Eugene's 44 node categories. */
export function colorForCategory(cat: string | undefined): string {
  const c = (cat ?? "UNKNOWN").toUpperCase();
  const palette: Record<string, string> = {
    DRUG: "#7fe7d4",
    DRUG_PRODUCT: "#3ecab4",
    DRUG_SYNONYM: "#23a591",
    DISEASE: "#ff5d7a",
    GENE_PROTEIN: "#7c8cff",
    ANATOMY: "#d4a5ff",
    PATHWAY: "#f8c26b",
    BIOLOGICAL_PROCESS: "#ffb37f",
    MOLECULAR_FUNCTION: "#c7a5ff",
    CELLULAR_COMPONENT: "#8fe0a5",
    CLINICAL_TRIAL: "#5d70ff",
    CONDITION: "#ff7d9b",
    INTERVENTION: "#66d9b0",
    PHASE: "#b3a5ff",
    PATENT: "#ffd37f",
    APPROVED_PATENT: "#ffc14f",
    PATENT_APPLICATION: "#ffe4a3",
    USPTO_PATENT: "#ffd37f",
    ORGANIZATION: "#ff9566",
    RESEARCH: "#ffae88",
    PUBMED: "#a5b0ff",
    PUBMED_DOCUMENT: "#a5b0ff",
    PUBMED_SUMMARY: "#bcc4ff",
    AUTHORS: "#c8b0ff",
    EFFECT_PHENOTYPE: "#ff8fb0",
    EXPOSURE: "#ffc59e",
    UNKNOWN: "#8a93ad",
  };
  if (palette[c]) return palette[c];
  // Substring fallback so unmapped / compound Neo4j labels still get a sensible,
  // stable type colour (the graph must reflect node TYPE, not all be grey).
  if (c.includes("DRUG")) return palette.DRUG;
  if (c.includes("DISEASE")) return palette.DISEASE;
  if (c.includes("GENE") || c.includes("PROTEIN")) return palette.GENE_PROTEIN;
  if (c.includes("PATENT") || c.includes("USPTO")) return palette.PATENT;
  if (c.includes("TRIAL") || c.includes("PHASE")) return palette.CLINICAL_TRIAL;
  if (c.includes("PUBMED") || c.includes("RESEARCH") || c.includes("AUTHOR")) return palette.PUBMED;
  if (c.includes("ORGAN") || c.includes("SPONSOR") || c.includes("CARRIER")) return palette.ORGANIZATION;
  if (c.includes("PATHWAY") || c.includes("PROCESS") || c.includes("FUNCTION") || c.includes("COMPONENT"))
    return palette.PATHWAY;
  if (c.includes("PHENOTYPE") || c.includes("EFFECT")) return palette.EFFECT_PHENOTYPE;
  if (c.includes("ANATOMY")) return palette.ANATOMY;
  return "#8a93ad";
}
