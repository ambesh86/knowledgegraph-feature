"use client";

import cytoscape from "cytoscape";
import cola from "cytoscape-cola";
import dagre from "cytoscape-dagre";
import cxtmenu from "cytoscape-cxtmenu";

let registered = false;

/** Register Cytoscape plugins exactly once. Static imports so we never race. */
export function registerCytoscapeExtensions(): void {
  if (registered) return;
  registered = true;
  for (const [name, ext] of [
    ["cola", cola],
    ["dagre", dagre],
    ["cxtmenu", cxtmenu],
  ] as const) {
    try {
      cytoscape.use(ext as unknown as cytoscape.Ext);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn(`cytoscape plugin ${name} failed to register`, e);
    }
  }
}
