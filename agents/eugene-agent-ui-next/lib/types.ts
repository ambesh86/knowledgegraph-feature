export type MessageRole = "user" | "assistant" | "system";

export interface ToolInvocation {
  toolId: string;
  tool: string;
  input: Record<string, unknown>;
  output?: unknown;
  startedAt: number;
  endedAt?: number;
  status: "pending" | "ok" | "error";
  // The user message this tool call is answering — lets us walk evidence chains
  turnId?: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: number;
  toolCalls?: ToolInvocation[];
  citations?: Citation[];
  // Which data source produced this answer (the selected tab). Drives the
  // green source badge on the assistant bubble.
  source?: ToolSelection;
}

export interface Citation {
  nodeId: string;
  tool?: string;
  label?: string;
}

/** Explainable-AI provenance: why does this node exist in the graph? */
export type ProvenanceSource =
  | "user_query" // seeded from the user's question text
  | "tool_call" // emitted from an agent tool result
  | "user_expand" // user right-clicked Expand
  | "path_finder" // returned by source→sink path query
  | "manual_add"; // dropped in by the user

export interface Provenance {
  source: ProvenanceSource;
  toolId?: string;
  toolName?: string;
  turnId?: string; // user message id that triggered the chain
  cypherHint?: string; // human-readable cypher approximation
  parentNodeIds?: string[]; // "who brought us here"
  timestamp: number;
}

export interface GraphNode {
  id: string;
  caption?: string;
  labels?: string[];
  category?: string;
  weight?: number;
  properties?: Record<string, unknown>;
  provenance?: Provenance[];
  role?: "source" | "sink" | "on_path" | null;
  pinned?: boolean;
}

export interface GraphRelationship {
  id: string;
  from: string;
  to: string;
  type?: string;
  caption?: string;
  properties?: Record<string, unknown>;
  provenance?: Provenance[];
  onPath?: boolean;
}

export interface ContextGraph {
  nodes: GraphNode[];
  rels: GraphRelationship[];
}

export type ToolSelection = "all_sources" | "eugene" | "http" | "pubmed";

export interface StreamEvent {
  type: "session" | "content" | "tool_call" | "tool_result" | "done" | "error";
  content?: string;
  session_id?: string;
  tool?: string;
  tool_input?: Record<string, unknown>;
  tool_id?: string;
  tool_output?: unknown;
}

export type GraphLayoutKind = "cola" | "dagre" | "concentric" | "circle";
