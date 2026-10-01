/**
 * Dev/demo graph seeding.
 *
 * When the app is opened with `?demo=<name>` it loads a real subgraph fixture
 * (exported from the live Neo4j by scripts/gen_graph_fixtures.py) and seeds the
 * context graph + a synthesized conversation. This lets the populated-graph
 * "hero" layout, rich graph interactions and inline/panel evidence be developed,
 * demoed and visual-tested WITHOUT the agent backend.
 *
 * Purely additive and gated behind the query param — the real agent-driven flow
 * (useChatStream.send) is untouched.
 */
import { v4 as uuid } from "uuid";
import { apiPath } from "./basePath";
import type { ChatMessage, ContextGraph, GraphNode } from "./types";

export const DEMO_NAMES = ["answer", "dense", "huge"] as const;
export type DemoName = (typeof DEMO_NAMES)[number];

export function getDemoParam(): DemoName | null {
  if (typeof window === "undefined") return null;
  const v = new URLSearchParams(window.location.search).get("demo");
  return (DEMO_NAMES as readonly string[]).includes(v ?? "")
    ? (v as DemoName)
    : null;
}

export async function loadDemoGraph(name: DemoName): Promise<ContextGraph> {
  const res = await fetch(apiPath(`/fixtures/${name}.json`), {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`demo fixture "${name}" failed: ${res.status}`);
  return (await res.json()) as ContextGraph;
}

const byCategory = (g: ContextGraph, cat: string): GraphNode[] =>
  g.nodes.filter((n) => (n.category ?? "").toUpperCase() === cat);

/**
 * Build a believable user→assistant turn for the seeded graph, with citation
 * chips pointing at the most salient nodes (the disease + candidate drugs).
 */
export function buildDemoConversation(
  g: ContextGraph,
  turnId: string
): { messages: ChatMessage[]; assistantId: string } {
  const disease = byCategory(g, "DISEASE")[0];
  const diseaseName = disease?.caption ?? "the disease";
  const drugs = byCategory(g, "DRUG");
  const proteins = byCategory(g, "GENE_PROTEIN");
  const pathways = byCategory(g, "PATHWAY");

  const topDrugs = drugs.slice(0, 5).map((d) => d.caption).filter(Boolean);
  const topProteins = proteins.slice(0, 4).map((p) => p.caption).filter(Boolean);

  const userMsg: ChatMessage = {
    id: turnId,
    role: "user",
    content: `Which drugs could be repurposed to treat ${diseaseName}, and through which protein targets and pathways?`,
    createdAt: Date.now(),
  };

  const content = [
    `Based on the knowledge graph, **${diseaseName}** is associated with **${proteins.length}** protein targets`,
    pathways.length ? ` across **${pathways.length}** pathways` : "",
    `. I traced **${drugs.length}** drugs that act on those targets.`,
    topProteins.length
      ? `\n\n**Key protein targets:** ${topProteins.join(", ")}.`
      : "",
    topDrugs.length
      ? `\n\n**Candidate drugs:** ${topDrugs.join(", ")}${
          drugs.length > topDrugs.length ? `, and ${drugs.length - topDrugs.length} more` : ""
        }.`
      : "",
    `\n\nExplore the graph on the right — double-click any node to expand its neighbourhood, hover to spotlight relationships, or open a node's evidence to trace the provenance chain.`,
  ].join("");

  const citations = [
    ...(disease ? [{ nodeId: disease.id, label: disease.caption }] : []),
    ...drugs.slice(0, 8).map((d) => ({ nodeId: d.id, label: d.caption, tool: "drug_protein" })),
    ...proteins.slice(0, 4).map((p) => ({ nodeId: p.id, label: p.caption, tool: "disease_protein" })),
  ];

  const assistantId = uuid();
  const assistantMsg: ChatMessage = {
    id: assistantId,
    role: "assistant",
    content,
    createdAt: Date.now() + 1,
    citations,
  };

  return { messages: [userMsg, assistantMsg], assistantId };
}
