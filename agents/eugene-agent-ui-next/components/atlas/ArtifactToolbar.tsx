"use client";

import { useState } from "react";
import { apiPath } from "@/lib/basePath";

const btn: React.CSSProperties = {
  font: "13px/1 -apple-system,Segoe UI,Roboto,sans-serif",
  padding: "8px 12px",
  border: "1px solid #d6dae4",
  borderRadius: "8px",
  background: "#fff",
  color: "#2d3748",
  cursor: "pointer",
};

/** Print + download + copy-link controls for a shared artifact page. */
export function ArtifactToolbar({ id }: { id: string }) {
  const [copied, setCopied] = useState(false);
  const dl = (fmt: string) => {
    window.location.href = apiPath(`/api/atlas/artifacts/${id}/export?fmt=${fmt}`);
  };
  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* ignore */
    }
  };
  return (
    <div className="no-print" style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "10px 0 28px" }}>
      <button style={btn} onClick={() => window.print()}>🖨 Print / Save as PDF</button>
      <button style={btn} onClick={() => dl("docx")}>⬇ Word</button>
      <button style={btn} onClick={() => dl("html")}>⬇ HTML</button>
      <button style={btn} onClick={() => dl("md")}>⬇ Markdown</button>
      <button style={{ ...btn, color: copied ? "#15803d" : "#2d3748" }} onClick={copyLink}>
        {copied ? "✓ Link copied" : "🔗 Copy link"}
      </button>
    </div>
  );
}
