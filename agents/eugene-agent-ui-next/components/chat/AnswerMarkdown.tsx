"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Text } from "@chakra-ui/react";
import type { EvidenceItem } from "@/lib/atlas/evidence";
import { buildSegments, type AnchoredCitation } from "@/lib/atlas/citations";
import { CitationMarkers } from "@/components/chat/Citations";

/**
 * Rendering an answer with its citation markers in place.
 *
 * This lives in its own module because there are two answer renderers — the chat
 * bubble in `Message.tsx` and the Ask view's inline transcript — and they had
 * drifted. Citation markers were added to one of them, which meant the surface
 * users actually read still showed bare `[Evidence 5]` text. One implementation,
 * used by both, is the only arrangement where that cannot silently happen again.
 *
 * Markdown has no concept of a citation, so markers travel through the parser as
 * an inert text token and are swapped for React elements on the way out. The
 * delimiters are deliberately obscure Unicode brackets: anything
 * markdown-meaningful (`[1]`, `^1^`) would be reinterpreted, and anything ASCII
 * risks colliding with real prose about, say, chemical notation.
 */

const CITE_OPEN = "⟦⟦";
const CITE_CLOSE = "⟧⟧";
const CITE_TOKEN = /⟦⟦([\d,]+)⟧⟧/g;

/**
 * Replace citation tokens inside rendered Markdown children with marker components.
 *
 * Walks only string children — everything else (links, emphasis, nested elements)
 * is passed through untouched, so a citation next to bold text does not strip the
 * bold.
 */
function decodeCitations(
  children: React.ReactNode,
  byNumber: Map<number, AnchoredCitation>
): React.ReactNode {
  if (!byNumber.size) return children;

  const decodeOne = (node: React.ReactNode, key: string): React.ReactNode => {
    if (typeof node !== "string") return node;
    CITE_TOKEN.lastIndex = 0;
    if (!CITE_TOKEN.test(node)) return node;

    CITE_TOKEN.lastIndex = 0;
    const out: React.ReactNode[] = [];
    let last = 0;
    for (const m of node.matchAll(CITE_TOKEN)) {
      const at = m.index ?? 0;
      if (at > last) out.push(node.slice(last, at));
      const cites = m[1]
        .split(",")
        .map((n) => byNumber.get(Number(n)))
        .filter((c): c is AnchoredCitation => Boolean(c));
      if (cites.length) out.push(<CitationMarkers key={`${key}-${at}`} citations={cites} />);
      last = at + m[0].length;
    }
    if (last < node.length) out.push(node.slice(last));
    return out;
  };

  if (Array.isArray(children)) {
    return children.map((c, i) => decodeOne(c, `c${i}`));
  }
  return decodeOne(children, "c0");
}

/**
 * Anchor an answer's evidence and encode the markers into the Markdown source.
 *
 * Returned separately from the renderer because callers also need `citations` for
 * the reference list under the answer, and both must agree on the numbering.
 */
export function useAnchoredAnswer(content: string, items: EvidenceItem[]) {
  return React.useMemo(() => {
    const { segments, citations } = buildSegments(content, items);
    const markdown = segments
      .map((seg) =>
        seg.kind === "text"
          ? seg.value
          : `${CITE_OPEN}${seg.citations.map((c) => c.n).join(",")}${CITE_CLOSE}`
      )
      .join("");
    return { markdown, citations, byNumber: new Map(citations.map((c) => [c.n, c])) };
  }, [content, items]);
}

export function AnswerMarkdown({
  markdown,
  byNumber,
  /** When set, a stray "Sources: …" paragraph left in the body is tinted this colour. */
  sourcesColor,
}: {
  markdown: string;
  byNumber: Map<number, AnchoredCitation>;
  sourcesColor?: string;
}) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // Belt-and-suspenders: even if a "Sources: …" line ends up in the body
        // (not extracted), render it clearly.
        p: ({ children }) => {
          const first = Array.isArray(children) ? children[0] : children;
          const isSources =
            sourcesColor && typeof first === "string" && /^\s*Sources?:/i.test(first);
          return isSources ? (
            <Text as="p" mt={2} color={sourcesColor} fontWeight={700} fontSize="13px">
              {decodeCitations(children, byNumber)}
            </Text>
          ) : (
            <Text as="p">{decodeCitations(children, byNumber)}</Text>
          );
        },
        li: ({ children }) => <li>{decodeCitations(children, byNumber)}</li>,
        td: ({ children }) => <td>{decodeCitations(children, byNumber)}</td>,
      }}
    >
      {markdown}
    </ReactMarkdown>
  );
}
