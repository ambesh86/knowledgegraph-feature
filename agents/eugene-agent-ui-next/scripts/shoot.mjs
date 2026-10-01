/**
 * Visual-QA harness. Screenshots the running dev UI in several states using the
 * `?demo=` fixtures, so the populated-graph "hero" layout can be inspected
 * without the agent backend.
 *
 * Prereq: dev server running on UI_BASE (default http://localhost:18502).
 * Usage:  node scripts/shoot.mjs [state...]   (default: all)
 *         UI_BASE=http://localhost:3000 node scripts/shoot.mjs answer dense
 * Output: /tmp/ui_<state>.png
 */
import { chromium } from "playwright";

const BASE = process.env.UI_BASE || "http://localhost:18502";
const OUT = process.env.SHOT_DIR || "/tmp";

const STATES = {
  empty: `${BASE}/`,
  answer: `${BASE}/?demo=answer`,
  dense: `${BASE}/?demo=dense`,
  huge: `${BASE}/?demo=huge`,
};

const want = process.argv.slice(2);
const states = Object.entries(STATES).filter(
  ([k]) => want.length === 0 || want.includes(k)
);

const browser = await chromium.launch({ channel: "chrome" });
const ctx = await browser.newContext({
  viewport: { width: 1680, height: 960 },
  deviceScaleFactor: 1.5,
});
const page = await ctx.newPage();
page.on("console", (m) => {
  if (m.type() === "error") console.log("  [browser error]", m.text().slice(0, 200));
});

for (const [name, url] of states) {
  try {
    await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
    // Let Cytoscape's cola layout settle + fixture fetch resolve.
    await page.waitForTimeout(name === "empty" ? 1500 : 4500);
    const file = `${OUT}/ui_${name}.png`;
    await page.screenshot({ path: file });
    console.log(`✔ ${name.padEnd(7)} → ${file}`);
  } catch (e) {
    console.log(`✘ ${name.padEnd(7)} ${String(e).split("\n")[0]}`);
  }
}

await browser.close();
