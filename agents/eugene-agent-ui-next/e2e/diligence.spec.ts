import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { registerViaApi, uniqueUser } from "./helpers";

/**
 * Use Case 2 — accelerated scientific due diligence, end to end.
 *
 * These run against the live scanner and real public registries, for the same reason
 * the Radar specs do: the defect this feature must not have is "the page shows
 * something plausible that is not actually true", and a fixture cannot catch that.
 *
 * What is asserted is the *contract*, never a specific finding. A brief's confidence
 * band depends on what four public registries returned this morning, so a test that
 * pinned "high" would be red the week a source changed its ranking. What must always
 * hold is structural: every section declares its coverage, an empty section explains
 * what its emptiness means, and a model-written summary is labelled as one.
 */

const SCOUT_URL = process.env.EUGENE_SCOUT_URL ?? "http://localhost:18300";

async function scoutIsUp(): Promise<boolean> {
  try {
    const res = await fetch(`${SCOUT_URL}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

async function signIn(page: Page, request: APIRequestContext) {
  const user = uniqueUser("dd");
  await registerViaApi(request, { ...user, focusArea: "hematology" });
  const { cookies } = await request.storageState();
  const session = cookies.filter((c) => c.name === "atlas_session");
  expect(session.length, "register did not set a session cookie").toBeGreaterThan(0);
  await page.context().addCookies(session);
  return user;
}

/** Seed a stored brief through the API so the page has something to open without
 *  paying a 30s live run inside every test. */
async function seedBrief(request: APIRequestContext, company: string) {
  const res = await request.post("api/atlas/scout/dd", {
    data: { company },
    timeout: 200_000,
  });
  expect(res.ok(), `seeding ${company} failed: ${res.status()} ${await res.text()}`).toBeTruthy();
  return res.json();
}

test.describe("Due diligence — brief rendering", () => {
  test.beforeAll(async () => {
    test.skip(!(await scoutIsUp()), "eugene_scout is not running");
  });

  test("a stored brief opens from the index and renders its assessment", async ({ page, request }) => {
    await signIn(page, request);
    await seedBrief(request, "Alnylam Pharmaceuticals");

    await page.goto("research");
    await expect(page.getByRole("heading", { name: "Due diligence" })).toBeVisible();

    const row = page.getByTestId("dd-index-row").first();
    await expect(row).toBeVisible({ timeout: 20_000 });
    await row.click();

    const brief = page.getByTestId("due-diligence-brief");
    await expect(brief).toBeVisible({ timeout: 30_000 });

    // The four assessment sections plus competitive differentiation. Sections are
    // never dropped for being empty — that is the whole point of the design.
    await expect(page.getByTestId("brief-section")).toHaveCount(5);

    await expect(brief.getByText("NEXT ACTION")).toBeVisible();
  });

  test("every section declares the sources it consulted", async ({ page, request }) => {
    await signIn(page, request);
    await seedBrief(request, "Alnylam Pharmaceuticals");

    await page.goto("research");
    await page.getByTestId("dd-index-row").first().click();
    await expect(page.getByTestId("due-diligence-brief")).toBeVisible({ timeout: 30_000 });

    // A section that does not say where it looked cannot be challenged, and an
    // unchallengeable diligence section is one an analyst learns to ignore.
    const sections = page.getByTestId("brief-section");
    const count = await sections.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < count; i++) {
      await expect(sections.nth(i).getByText(/Sources consulted:/)).toBeVisible();
    }
  });

  test("the confidence score is shown with its band, not as a bare number", async ({ page, request }) => {
    await signIn(page, request);
    await seedBrief(request, "Alnylam Pharmaceuticals");

    await page.goto("research");
    await page.getByTestId("dd-index-row").first().click();
    await expect(page.getByTestId("due-diligence-brief")).toBeVisible({ timeout: 30_000 });

    // A number alone invites a comparison it cannot support; the band is what says
    // how much weight the number carries.
    const badge = page.getByTestId("confidence-badge").first();
    await expect(badge).toBeVisible();
    await expect(badge).toContainText(
      /Insufficient evidence|Low confidence|Moderate confidence|High confidence/
    );
  });

  test("a model-written summary is labelled as model-written", async ({ page, request }) => {
    await signIn(page, request);
    const seeded = await seedBrief(request, "Alnylam Pharmaceuticals");

    await page.goto("research");
    await page.getByTestId("dd-index-row").first().click();
    await expect(page.getByTestId("due-diligence-brief")).toBeVisible({ timeout: 30_000 });

    // Provenance is not decoration: a paragraph a model wrote and a paragraph the
    // system computed are different claims, and the reader is entitled to know which.
    const expected =
      seeded?.executive_summary?.provenance === "llm"
        ? /MODEL-WRITTEN · FACT-CHECKED/
        : /COMPUTED/;
    if (seeded?.executive_summary) {
      await expect(page.getByText(expected)).toBeVisible();
    }
  });

  test("an unassessed dimension reads as not assessed, never as zero", async ({ page, request }) => {
    await signIn(page, request);
    const seeded = await seedBrief(request, "Alnylam Pharmaceuticals");

    await page.goto("research");
    await page.getByTestId("dd-index-row").first().click();
    await expect(page.getByTestId("due-diligence-brief")).toBeVisible({ timeout: 30_000 });

    const unassessable: string[] = seeded?.confidence?.unassessable_components ?? [];
    if (unassessable.length === 0) {
      // Nothing to check today — the target had evidence everywhere. Asserting the
      // absence of the label would be asserting today's data, not the behaviour.
      test.skip(true, "every dimension was assessable for this target today");
    }
    await expect(page.getByText("NOT ASSESSED").first()).toBeVisible();
  });
});

test.describe("Due diligence — input handling", () => {
  test.beforeAll(async () => {
    test.skip(!(await scoutIsUp()), "eugene_scout is not running");
  });

  test("the run button stays disabled until a company is entered", async ({ page, request }) => {
    await signIn(page, request);
    await page.goto("research");

    const run = page.getByTestId("dd-run");
    await expect(run).toBeDisabled();

    await page.getByTestId("dd-company").fill("A");
    await expect(run, "one character is not a company name").toBeDisabled();

    await page.getByTestId("dd-company").fill("Alnylam Pharmaceuticals");
    await expect(run).toBeEnabled();
  });

  test("a too-short company is rejected by the API, not silently accepted", async ({ request }) => {
    const user = uniqueUser("dd-api");
    await registerViaApi(request, { ...user, focusArea: "hematology" });

    const res = await request.post("api/atlas/scout/dd", { data: { company: "A" } });
    expect(res.status()).toBe(400);
    expect((await res.json()).error).toMatch(/at least two characters/i);
  });

  test("an unknown target is a 404, distinct from the scanner being down", async ({ request }) => {
    const user = uniqueUser("dd-404");
    await registerViaApi(request, { ...user, focusArea: "hematology" });

    // "No brief yet" has an obvious remedy; "scanner unreachable" does not. A page
    // that renders them identically sends the user to press a button that cannot work.
    const res = await request.get("api/atlas/scout/dd/definitely-not-a-real-target");
    expect(res.status()).toBe(404);
  });

  test("diligence requires a session", async ({ playwright, baseURL }) => {
    // A fresh context with no cookies — the `request` fixture carries a session from
    // whichever test registered last, which would make this pass for the wrong reason.
    const anon = await playwright.request.newContext({ baseURL });
    try {
      expect((await anon.get("api/atlas/scout/dd")).status()).toBe(401);
      expect(
        (await anon.post("api/atlas/scout/dd", { data: { company: "Alnylam" } })).status()
      ).toBe(401);
    } finally {
      await anon.dispose();
    }
  });
});
