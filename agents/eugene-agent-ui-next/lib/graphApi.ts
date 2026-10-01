import type { GraphNode, GraphRelationship } from "./types";
import { apiPath } from "./basePath";

/**
 * Thin client + universal normalizer.
 *
 * Eugene emits five distinct shapes across the MCP tool surface:
 *
 *   A. `{results: [{id, value}], count, query, fuzzy_match}` — lookup_node_by_value
 *   B. `{node_count, nodes: [{id, value, labels}], relationships: {src: [{id, rel}]}}` — n-hop
 *   C. `[[{org_id, org_name, org_type}]]` — find_organization_names (non-standard keys)
 *   D. `[{drug_id, drug_name, ...}]` / `[{patent_id, ...}]` — asset lists
 *   E. `"No results ..."` or `[]` — empty
 *
 * The normalizer deep-walks any value and recognises the ID/name keys used
 * across Eugene's domain, so every tool output contributes something real.
 */

const ID_KEYS = [
  "node_id",
  "id",
  "org_id",
  "drug_id",
  "drug_product_id",
  "patent_id",
  "patent_number",
  "nct_id",
  "pmid",
  "clinical_trial_id",
  "organization_id",
  "gene_protein_id",
  "disease_id",
];

const NAME_KEYS = [
  "node_name",
  "name",
  "value",
  "caption",
  "org_name",
  "drug_name",
  "patent_title",
  "title",
  "pubmed_title",
];

const LABEL_KEYS = ["label", "node_label", "labels", "type", "node_type", "org_type"];

function firstString(obj: Record<string, unknown>, keys: string[]): string | undefined {
  for (const k of keys) {
    const v = obj[k];
    if (typeof v === "string" && v.length) return v;
  }
  return undefined;
}

function extractCategory(obj: Record<string, unknown>): string | undefined {
  for (const k of LABEL_KEYS) {
    const v = obj[k];
    if (typeof v === "string" && v.length) return v.toUpperCase();
    if (Array.isArray(v) && v.length) {
      // labels: ["drug", "DRUG"] — prefer the uppercase one
      const upper = (v as unknown[]).find(
        (x) => typeof x === "string" && x === (x as string).toUpperCase()
      );
      if (upper) return String(upper);
      return String(v[0]).toUpperCase();
    }
  }
  // Specialised key → category inference
  if ("org_id" in obj) return "ORGANIZATION";
  if ("drug_id" in obj) return "DRUG";
  if ("patent_id" in obj || "patent_number" in obj) return "PATENT";
  if ("nct_id" in obj) return "CLINICAL_TRIAL";
  if ("pmid" in obj) return "PUBMED_DOCUMENT";
  return undefined;
}

/**
 * Universal deep-walking normaliser. Handles any nesting depth.
 */
export function normalizeApiResponse(payload: unknown): {
  nodes: GraphNode[];
  rels: GraphRelationship[];
} {
  const nodes = new Map<string, GraphNode>();
  const rels = new Map<string, GraphRelationship>();

  const addNode = (raw: Record<string, unknown>): string | null => {
    const id = firstString(raw, ID_KEYS);
    if (!id) return null;
    if (nodes.has(id)) {
      // Merge properties
      const existing = nodes.get(id)!;
      existing.properties = { ...existing.properties, ...raw };
      const cap = firstString(raw, NAME_KEYS);
      if (cap && (!existing.caption || existing.caption === existing.id))
        existing.caption = cap;
      const cat = extractCategory(raw);
      if (cat && (!existing.category || existing.category === "UNKNOWN"))
        existing.category = cat;
      return id;
    }
    const caption = firstString(raw, NAME_KEYS) ?? id;
    const category = extractCategory(raw) ?? "UNKNOWN";
    const labels = Array.isArray(raw.labels) ? (raw.labels as string[]) : undefined;
    nodes.set(id, {
      id,
      caption,
      category,
      labels,
      properties: raw,
      weight: 1,
    });
    return id;
  };

  const addRel = (from: string, to: string, type?: string): void => {
    if (!nodes.has(from)) nodes.set(from, { id: from, caption: from, category: "UNKNOWN", weight: 1 });
    if (!nodes.has(to)) nodes.set(to, { id: to, caption: to, category: "UNKNOWN", weight: 1 });
    const id = `${from}->${to}:${type ?? ""}`;
    if (rels.has(id)) return;
    rels.set(id, {
      id,
      from,
      to,
      type,
      caption: (type ?? "").replace(/_/g, " "),
    });
  };

  const walk = (v: unknown, depth = 0): void => {
    if (v === null || v === undefined || depth > 20) return;

    if (Array.isArray(v)) {
      for (const item of v) walk(item, depth + 1);
      return;
    }
    if (typeof v !== "object") return;

    const obj = v as Record<string, unknown>;

    // Shape B: relationships as adjacency dict { srcId: [{id, rel}] }
    if (obj.relationships && typeof obj.relationships === "object" && !Array.isArray(obj.relationships)) {
      for (const [src, list] of Object.entries(obj.relationships as Record<string, unknown>)) {
        if (!Array.isArray(list)) continue;
        for (const entry of list) {
          if (!entry || typeof entry !== "object") continue;
          const e = entry as { id?: string; rel?: string };
          if (e.id) addRel(src, e.id, e.rel);
        }
      }
    }

    // Shape: flat edge triple { start_node_id / from / source, end_node_id / to / target }
    const from =
      (obj.start_node_id ?? obj.from ?? obj.source ?? obj.src_id) as string | undefined;
    const to = (obj.end_node_id ?? obj.to ?? obj.target ?? obj.dst_id) as string | undefined;
    const relType = (obj.rel_type ?? obj.type ?? obj.relationship_type ?? obj.rel) as
      | string
      | undefined;
    if (typeof from === "string" && typeof to === "string") {
      addRel(from, to, relType);
    }

    // Node emission — any object containing one of the known ID keys
    const hasId = ID_KEYS.some((k) => typeof obj[k] === "string");
    if (hasId) addNode(obj);

    // Recurse into all child values
    for (const val of Object.values(obj)) walk(val, depth + 1);
  };

  walk(payload);
  return { nodes: [...nodes.values()], rels: [...rels.values()] };
}

// ---- API client -----------------------------------------------------------

export async function expandNode(nodeId: string, nHop: 1 | 2 = 1) {
  const res = await fetch(
    apiPath(`/api/graph/expand/${encodeURIComponent(nodeId)}?n_hop=${nHop}`),
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error(`expand failed: ${res.status}`);
  return normalizeApiResponse(await res.json());
}

export async function findPath(source: string, sink: string, nHop: 2 | 3 | 4 = 4) {
  const res = await fetch(
    apiPath(`/api/graph/path?source=${encodeURIComponent(source)}&sink=${encodeURIComponent(sink)}&n_hop=${nHop}`),
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error(`path failed: ${res.status}`);
  return normalizeApiResponse(await res.json());
}

export async function fetchNodeDetails(nodeId: string) {
  const res = await fetch(apiPath(`/api/graph/node/${encodeURIComponent(nodeId)}`), {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`node details failed: ${res.status}`);
  const data = await res.json();
  if (Array.isArray(data) && data.length) return data[0];
  return data;
}
