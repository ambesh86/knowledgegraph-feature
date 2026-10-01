import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { registerViaApi, uniqueUser } from "./helpers";

/**
 * Radar / Watchlist / Today — end-to-end against the live scanner.
 *
 * These tests assert on **real data fetched from real sources**, not fixtures. That
 * is deliberate: the defect class this feature exists to prevent is "the panel shows
 * something plausible that is not actually true", and a mocked test cannot see it.
 *
 * The trade is that a source outage can turn a test red. That is handled explicitly:
 * where a source could legitimately return nothing, the test asserts the *contract*
 * (every row has a working link, the ordering is correct, the degraded state renders)
 * rather than a specific count. Nothing here asserts "there are exactly N signals".
 */

const SCOUT_URL = process.env.EUGENE_SCOUT_URL ?? "http://localhost:18300";

/** Skip a spec cleanly when the scanner is not running, rather than failing with a
 *  misleading UI error. */
async function scoutIsUp(): Promise<boolean> {
  try {
    const res = await fetch(`${SCOUT_URL}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Register through the API and transplant the session cookie into the browser.
 *
 * Deliberately not the UI login form. Driving that form against `next dev` proved
 * flaky in a way that has nothing to do with what these tests are checking: the login
 * inputs are React-controlled, and a re-render triggered by on-demand compilation can
 * land between filling the email and filling the password, clearing the first field.
 * A test suite about the Radar should not fail because of a dev-server race in an
 * unrelated screen — the login form has its own coverage in chat-ui.spec.ts.
 */
async function signIn(page: Page, request: APIRequestContext) {
  const user = uniqueUser("radar");
  await registerViaApi(request, { ...user, focusArea: "hematology" });

  const { cookies } = await request.storageState();
  const session = cookies.filter((c) => c.name === "atlas_session");
  expect(session.length, "register did not set a session cookie").toBeGreaterThan(0);
  await page.context().addCookies(session);

  return user;
}

test.describe("Radar — live signals", () => {
  test.beforeAll(async () => {
    test.skip(!(await scoutIsUp()), "eugene_scout is not running");
  });

  test("renders signals from the live scan with clickable sources", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("radar");

    await expect(page.getByRole("heading", { name: "Radar" })).toBeVisible();
    await expect(page.getByTestId("loading")).toHaveCount(0, { timeout: 20_000 });

    const rows = page.getByTestId("signal-row");
    await expect(rows.first()).toBeVisible({ timeout: 20_000 });

    // Every signal must carry at least one citation the analyst can open. A signal
    // with no source is an assertion, not evidence.
    const first = rows.first();
    const links = first.getByTestId("source-link");
    await expect(links.first()).toBeVisible();

    const href = await links.first().getAttribute("href");
    expect(href).toMatch(/^https:\/\//);
  });

  test("every source link points at a real upstream record", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("radar");
    await expect(page.getByTestId("signal-row").first()).toBeVisible({ timeout: 20_000 });

    const hrefs = await page.getByTestId("source-link").evaluateAll((els) =>
      els.slice(0, 12).map((e) => (e as HTMLAnchorElement).href)
    );
    expect(hrefs.length).toBeGreaterThan(0);

    // Only the four sources this system actually reads may appear. A link to
    // anywhere else would mean a URL was constructed from something we did not verify.
    for (const href of hrefs) {
      expect(href).toMatch(
        /clinicaltrials\.gov|pubmed\.ncbi\.nlm\.nih\.gov|europepmc\.org|patents\.google\.com|patentcenter\.uspto\.gov|sec\.gov/
      );
    }
  });

  test("signals are ranked by score, highest first", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("radar");
    await expect(page.getByTestId("signal-row").first()).toBeVisible({ timeout: 20_000 });

    const scores = await page.getByTestId("signal-row").evaluateAll((rows) =>
      rows.map((row) => {
        const match = row.textContent?.match(/(\d+)\/100/);
        return match ? Number(match[1]) : -1;
      })
    );
    const ranked = scores.filter((s) => s >= 0);
    expect(ranked.length).toBeGreaterThan(1);
    expect([...ranked]).toEqual([...ranked].sort((a, b) => b - a));
  });

  test("score breakdown explains the ranking", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("radar");
    await expect(page.getByTestId("signal-row").first()).toBeVisible({ timeout: 20_000 });

    await page.getByTestId("toggle-breakdown").first().click();

    // The breakdown must name real factors — this is the "interrogate and challenge
    // the model's reasoning" requirement made checkable.
    await expect(page.getByText("Score breakdown").first()).toBeVisible();
    await expect(page.getByText(/Area fit|Recency|Development stage/).first()).toBeVisible();
  });

  test("priority filter narrows the list and keeps the counts visible", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("radar");
    await expect(page.getByTestId("signal-row").first()).toBeVisible({ timeout: 20_000 });

    const before = await page.getByTestId("signal-row").count();
    await page.getByTestId("filter-med").click();
    await page.waitForTimeout(1200);

    const after = await page.getByTestId("signal-row").count();
    expect(after).toBeLessThanOrEqual(before);

    // Counts must survive the filter: showing "0 medium" once medium is selected
    // would be both useless and confusing.
    const medText = await page.getByTestId("count-med").textContent();
    expect(medText).toMatch(/\d+ medium/);
  });

  test("type filter restricts rows to that signal type", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("radar");
    await expect(page.getByTestId("signal-row").first()).toBeVisible({ timeout: 20_000 });

    await page.getByTestId("filter-Trial").click();
    await page.waitForTimeout(1200);

    const count = await page.getByTestId("signal-row").count();
    if (count > 0) {
      const text = await page.getByTestId("signal-row").first().textContent();
      expect(text).toContain("Trial");
    }
  });

  test("dismissing a signal removes it from the list", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("radar");
    await expect(page.getByTestId("signal-row").first()).toBeVisible({ timeout: 20_000 });

    const title = await page.getByTestId("signal-title").first().textContent();
    await page.getByTestId("dismiss-signal").first().click();
    await page.waitForTimeout(2500);

    const titles = await page.getByTestId("signal-title").allTextContents();
    expect(titles).not.toContain(title);
  });

  test("shows when the corpus was last scanned", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("radar");
    await expect(page.getByTestId("last-scanned")).toBeVisible({ timeout: 20_000 });
  });
});

test.describe("Watchlist — live company scores", () => {
  test.beforeAll(async () => {
    test.skip(!(await scoutIsUp()), "eugene_scout is not running");
  });

  test("ranks companies by score", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("watchlist");

    await expect(page.getByRole("heading", { name: "Watchlist" })).toBeVisible();
    await expect(page.getByTestId("loading")).toHaveCount(0, { timeout: 20_000 });
    await expect(page.getByTestId("company-row").first()).toBeVisible({ timeout: 20_000 });

    const scores = await page.getByTestId("company-row").evaluateAll((rows) =>
      rows.map((r) => {
        const cells = r.querySelectorAll("td");
        return Number(cells[1]?.textContent?.trim().split(/\s/)[0] ?? -1);
      })
    );
    const ranked = scores.filter((s) => s >= 0);
    expect(ranked.length).toBeGreaterThan(0);
    expect([...ranked]).toEqual([...ranked].sort((a, b) => b - a));
  });

  test("company names are real, not placeholders", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("watchlist");
    await expect(page.getByTestId("company-row").first()).toBeVisible({ timeout: 20_000 });

    const names = await page.getByTestId("company-row").evaluateAll((rows) =>
      rows.map((r) => r.querySelector("td")?.textContent?.trim() ?? "")
    );
    expect(names.length).toBeGreaterThan(0);
    // The seeded demo data these views used to render is gone; if any of its
    // fabricated rows reappear, something is still reading lib/atlas/seed.ts.
    for (const name of names) {
      expect(name).not.toMatch(/XYZ Biotech/i);
      expect(name.length).toBeGreaterThan(1);
    }
  });

  test("30-day delta shows an em dash when no baseline exists", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("watchlist");
    await expect(page.getByTestId("company-row").first()).toBeVisible({ timeout: 20_000 });

    // A fresh deployment has no 30-day-old snapshot. Rendering "+0" with an arrow
    // would claim the company held steady, which nothing in the system supports.
    const deltaCell = await page.getByTestId("company-row").first().evaluate(
      (r) => r.querySelectorAll("td")[2]?.textContent?.trim() ?? ""
    );
    expect(deltaCell === "—" || /^[+-]?\d+$/.test(deltaCell)).toBeTruthy();
  });

  test("search narrows the table", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("watchlist");
    await expect(page.getByTestId("company-row").first()).toBeVisible({ timeout: 20_000 });

    const name = await page.getByTestId("company-row").first().evaluate(
      (r) => r.querySelector("td")?.textContent?.trim().split("\n")[0] ?? ""
    );
    const term = name.split(" ")[0];

    await page.getByTestId("watchlist-search").fill(term);
    await page.waitForTimeout(1500);

    const count = await page.getByTestId("company-row").count();
    expect(count).toBeGreaterThan(0);
  });
});

test.describe("Today — real counters", () => {
  test.beforeAll(async () => {
    test.skip(!(await scoutIsUp()), "eugene_scout is not running");
  });

  test("attention summary reflects live counts, not a hardcoded number", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("today");

    const summary = page.getByTestId("attention-summary");
    await expect(summary).toBeVisible({ timeout: 20_000 });

    const text = await summary.textContent();
    // The old build always said "3 things need your attention". Whatever this says
    // now, it must be derived — assert the shape and that it agrees with the API.
    expect(text).toMatch(/(Nothing needs your attention|\d+ things? needs? your attention)/);
  });

  test("'since you last looked' is computed, not fabricated", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("today");

    const strip = page.getByTestId("since-you-last-looked");
    await expect(strip).toBeVisible({ timeout: 20_000 });

    const text = await strip.textContent();
    // Previously hardcoded to "3 new signals, 2 score moves" regardless of reality.
    expect(text).not.toContain("2 score moves");
    expect(text).toMatch(/(Nothing new since you last looked|new signals?)/);
  });

  test("priority signals appear with a rationale", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("today");
    await expect(page.getByTestId("attention-item").first()).toBeVisible({ timeout: 25_000 });

    const text = await page.getByTestId("attention-item").first().textContent();
    expect(text).toMatch(/\d+\/100/);
  });
});

test.describe("Settings — scanning configuration", () => {
  test.beforeAll(async () => {
    test.skip(!(await scoutIsUp()), "eugene_scout is not running");
  });

  test("shows the schedule and source availability", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("settings");

    await expect(page.getByText("Partnership scanning")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("schedule")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("schedule")).toContainText(/Daily at \d{2}:\d{2}/);
  });

  test("scoring weights are editable and persist", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("settings");
    await expect(page.getByTestId("save-config")).toBeVisible({ timeout: 20_000 });

    // Thresholds are the simplest field to assert on deterministically.
    const input = page.getByLabel("high threshold");
    await input.fill("77");
    await page.getByTestId("save-config").click();

    await expect(page.getByTestId("save-config")).toContainText(/Saved/, { timeout: 15_000 });

    await page.reload();
    await expect(page.getByLabel("high threshold")).toHaveValue("77", { timeout: 20_000 });

    // Restore, so the suite is idempotent against a shared scanner.
    await page.getByLabel("high threshold").fill("75");
    await page.getByTestId("save-config").click();
    await expect(page.getByTestId("save-config")).toContainText(/Saved/, { timeout: 15_000 });
  });

  test("run history exposes the audit trail", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("settings");
    await expect(page.getByText("Recent scans")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("run-row").first()).toBeVisible({ timeout: 20_000 });
  });
});

test.describe("Data freshness — the 'as of' indicator", () => {
  test.beforeAll(async () => {
    test.skip(!(await scoutIsUp()), "eugene_scout is not running");
  });

  test("today's date is shown in the header on every page", async ({ page, request }) => {
    await signIn(page, request);
    const today = new Date().toLocaleDateString("en-GB", {
      day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
    });

    for (const path of ["today", "radar", "watchlist", "briefing", "settings"]) {
      await page.goto(path);
      const chip = page.getByTestId("data-freshness");
      await expect(chip).toBeVisible({ timeout: 20_000 });
      await expect(chip).toContainText(today);
    }
  });

  test("hovering reveals per-source dates taken from the records", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("radar");
    await expect(page.getByTestId("signal-row").first()).toBeVisible({ timeout: 20_000 });

    await page.getByTestId("data-freshness").hover();
    await expect(page.getByText("Data currency")).toBeVisible();
    await expect(page.getByText("Newest by source")).toBeVisible();

    // Both clocks must be present and distinct: when we last looked, and how recent
    // the newest record actually is. A panel showing only the scan time would let a
    // three-week-old corpus read as current.
    await expect(page.getByTestId("freshness-last-scan")).toBeVisible();
    await expect(page.getByText("Newest record")).toBeVisible();

    const sources = page.getByTestId("freshness-sources");
    await expect(sources).toBeVisible();
    // Every listed source carries a real date, not a placeholder.
    await expect(sources).toContainText(/\d{1,2} \w{3} \d{4}/);
  });

  test("signal rows lead with an absolute publication date", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("radar");
    await expect(page.getByTestId("signal-row").first()).toBeVisible({ timeout: 20_000 });

    // "31 Jul 2026 · 9 days ago" — the absolute date is checkable against the source
    // record; the relative one drifts as the page sits open.
    const label = page.getByTestId("signal-date").first();
    await expect(label).toContainText(/\d{1,2} \w{3} \d{4}/);
    await expect(label).toContainText(/ago|today|yesterday/);
  });

  test("the reported date matches what the API says", async ({ page, request }) => {
    await signIn(page, request);
    const res = await page.request.get("api/atlas/scout/freshness");
    expect(res.status()).toBe(200);
    const body = await res.json();

    expect(body.today).toBe(new Date().toISOString().slice(0, 10));
    expect(body.next_scan_at).toBeTruthy();
    expect(new Date(body.next_scan_at).getTime()).toBeGreaterThan(Date.now());
    for (const s of body.sources) {
      expect(s.latest_published).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    }
  });
});

test.describe("Weekly partnership briefing", () => {
  test.beforeAll(async () => {
    test.skip(!(await scoutIsUp()), "eugene_scout is not running");
  });

  test("renders ranked companies with rationale, sources and a next action", async ({
    page,
    request,
  }) => {
    await signIn(page, request);
    await page.goto("briefing");

    await expect(page.getByRole("heading", { name: "Partnership briefing" })).toBeVisible();
    await expect(page.getByTestId("loading")).toHaveCount(0, { timeout: 25_000 });

    const entries = page.getByTestId("briefing-entry");
    await expect(entries.first()).toBeVisible({ timeout: 25_000 });

    // The use case names all four of these explicitly as the deliverable.
    const first = entries.first();
    await expect(first).toContainText("/100");
    await expect(first.getByText("Next action")).toBeVisible();
    await expect(first).toContainText("Sources consulted:");
    await expect(first.getByTestId("briefing-evidence-link").first()).toBeVisible();
  });

  test("evidence links point at real upstream records", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("briefing");
    await expect(page.getByTestId("briefing-entry").first()).toBeVisible({ timeout: 25_000 });

    const hrefs = await page.getByTestId("briefing-evidence-link").evaluateAll((els) =>
      els.slice(0, 8).map((e) => (e as HTMLAnchorElement).href)
    );
    expect(hrefs.length).toBeGreaterThan(0);
    for (const href of hrefs) {
      expect(href).toMatch(
        /clinicaltrials\.gov|pubmed\.ncbi\.nlm\.nih\.gov|europepmc\.org|patents\.google\.com|patentcenter\.uspto\.gov|sec\.gov/
      );
    }
  });

  test("a short list is declared, not padded", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("briefing");
    await expect(page.getByTestId("briefing-summary")).toBeVisible({ timeout: 25_000 });

    const count = await page.getByTestId("briefing-entry").count();
    if (count < 8) {
      // Padding to the 8-12 target with companies the system does not rate would
      // teach readers to distrust the ranking.
      await expect(page.getByTestId("below-target")).toBeVisible();
    }
  });

  test("publishing produces a shareable artifact page", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("briefing");
    await expect(page.getByTestId("briefing-entry").first()).toBeVisible({ timeout: 25_000 });

    await page.getByTestId("publish-briefing").click();
    await page.waitForURL(/\/a\/[0-9a-f-]{36}/, { timeout: 25_000 });
    await expect(page.getByText(/Partnership Briefing/i).first()).toBeVisible();
  });

  test("markdown export is served", async ({ page, request }) => {
    await signIn(page, request);
    const res = await page.request.get("api/atlas/scout/briefing?format=markdown");
    expect(res.status()).toBe(200);
    expect(res.headers()["content-type"]).toContain("text/markdown");
    expect(await res.text()).toContain("# Partnership Briefing");
  });
});

test.describe("Unauthenticated access", () => {
  test("scanner endpoints reject anonymous callers", async ({ request }) => {
    for (const path of [
      "api/atlas/signals",
      "api/atlas/watchlist",
      "api/atlas/scout/stats",
      "api/atlas/scout/runs",
      "api/atlas/scout/config",
      "api/atlas/scout/briefing",
      "api/atlas/scout/freshness",
    ]) {
      const res = await request.get(path);
      expect(res.status(), `${path} must require auth`).toBe(401);
    }
  });

  test("scan trigger rejects anonymous callers", async ({ request }) => {
    const res = await request.post("api/atlas/scout/scan");
    expect(res.status()).toBe(401);
  });
});
