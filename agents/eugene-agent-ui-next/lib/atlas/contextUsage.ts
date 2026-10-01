import type { ChatMessage } from "@/lib/types";

/**
 * Client-side context-window estimation (claude-code-style meter). We don't have
 * the model's exact tokenizer, so we approximate tokens as ~4 chars/token across
 * message content + tool-call payloads. Good enough to drive a usage meter and a
 * "nearly full — start a new chat" nudge.
 */

// Working context budget for a single research thread (tokens). Tunable via env.
export const CONTEXT_BUDGET_TOKENS = Number(
  process.env.NEXT_PUBLIC_CONTEXT_BUDGET ?? 24000
);

const WARN_AT = 0.9; // 90%

// A small flat overhead per tool call. We deliberately do NOT count the full
// tool-call OUTPUT: a single graph query can return a huge neighbourhood payload
// (hundreds of KB), which would instantly max the meter on the very first
// question. The meter should track CONVERSATION length (what the user typed and
// read), not the size of one answer's internal graph data.
const TOOL_CALL_OVERHEAD_CHARS = 240;

export function estimateTokens(messages: ChatMessage[]): number {
  let chars = 0;
  for (const m of messages) {
    chars += (m.content ?? "").length;
    if (m.toolCalls?.length) chars += m.toolCalls.length * TOOL_CALL_OVERHEAD_CHARS;
  }
  return Math.ceil(chars / 4);
}

export interface ContextUsage {
  tokens: number;
  budget: number;
  pct: number; // 0..100
  nearFull: boolean; // >= 90%
  full: boolean; // >= 100%
}

export function contextUsage(messages: ChatMessage[]): ContextUsage {
  const tokens = estimateTokens(messages);
  const budget = CONTEXT_BUDGET_TOKENS;
  const ratio = budget > 0 ? tokens / budget : 0;
  return {
    tokens,
    budget,
    pct: Math.min(100, Math.round(ratio * 100)),
    nearFull: ratio >= WARN_AT,
    full: ratio >= 1,
  };
}
