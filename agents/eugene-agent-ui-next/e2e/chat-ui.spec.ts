import { test, expect, type Page } from "@playwright/test";
import { registerViaApi, seedConversation, uniqueUser, uuid } from "./helpers";

/**
 * Drives the real browser against the deployed UI. Each test registers a fresh
 * user (via the page's request context, which shares the session cookie) and
 * seeds conversations through the API, then exercises the sidebar + Ask view.
 */

async function setup(page: Page) {
  const user = uniqueUser("ui");
  await registerViaApi(page.request, user); // sets the atlas_session cookie
  const brca = { id: uuid(), userMsg: "What do BRCA1 and BRCA2 encode?", asstMsg: "UI-SEED tumor-suppressor DNA-repair proteins.", title: false as const };
  const emi = { id: uuid(), source: "pubmed", userMsg: "Emicizumab pediatric safety", asstMsg: "UI-SEED favorable long-term safety.", title: false as const };
  await seedConversation(page.request, brca);
  await seedConversation(page.request, emi);
  // give them explicit titles so the sidebar text is deterministic
  await page.request.patch(`api/atlas/conversations/${brca.id}`, { data: { title: "BRCA thread" } });
  await page.request.patch(`api/atlas/conversations/${emi.id}`, { data: { title: "Emicizumab thread" } });
  return { user, brca, emi };
}

test("sidebar lists seeded conversations", async ({ page }) => {
  await setup(page);
  await page.goto("ask", { waitUntil: "domcontentloaded" });
  await expect(page.getByText("BRCA thread")).toBeVisible();
  await expect(page.getByText("Emicizumab thread")).toBeVisible();
  await expect(page.getByRole("button", { name: /New chat/ }).first()).toBeVisible();
});

test("clicking an old chat resumes it and highlights the row", async ({ page }) => {
  const { brca } = await setup(page);
  await page.goto("ask", { waitUntil: "domcontentloaded" });

  await page.getByText("BRCA thread").click();
  // resumed: seeded messages are rendered
  await expect(page.getByText(/UI-SEED tumor-suppressor DNA-repair/)).toBeVisible();
  // url reflects the conversation
  await expect(page).toHaveURL(new RegExp(`\\?c=${brca.id}`));
  // active row is marked current
  const active = page.locator('[data-testid="conversation-row"][aria-current="true"]');
  await expect(active).toHaveCount(1);
  await expect(active).toContainText("BRCA thread");
});

test("switching conversations swaps the transcript", async ({ page }) => {
  await setup(page);
  await page.goto("ask", { waitUntil: "domcontentloaded" });

  await page.getByText("BRCA thread").click();
  await expect(page.getByText(/UI-SEED tumor-suppressor/)).toBeVisible();

  await page.getByText("Emicizumab thread").click();
  await expect(page.getByText(/UI-SEED favorable long-term safety/)).toBeVisible();
  await expect(page.getByText(/UI-SEED tumor-suppressor/)).toHaveCount(0);
});

test("rename a conversation from the row menu", async ({ page }) => {
  await setup(page);
  await page.goto("ask", { waitUntil: "domcontentloaded" });

  const row = page.locator('[data-testid="conversation-row"]', { hasText: "BRCA thread" });
  await row.hover();
  await row.getByRole("button", { name: /Conversation options/ }).click();
  await page.getByRole("menuitem", { name: /Rename/ }).click();
  // Once editing, the row's text becomes an <input> — target it globally.
  const input = page.locator('[data-testid="conversation-row"] input');
  await input.fill("Renamed in UI");
  await input.press("Enter");
  await expect(page.getByText("Renamed in UI")).toBeVisible();
  await expect(page.getByText("BRCA thread")).toHaveCount(0);
});

test("delete a conversation from the row menu", async ({ page }) => {
  await setup(page);
  await page.goto("ask", { waitUntil: "domcontentloaded" });

  const row = page.locator('[data-testid="conversation-row"]', { hasText: "Emicizumab thread" });
  await row.hover();
  await row.getByRole("button", { name: /Conversation options/ }).click();
  await page.getByRole("menuitem", { name: /Delete/ }).click();
  await expect(page.getByText("Emicizumab thread")).toHaveCount(0);
  // still present: the other one
  await expect(page.getByText("BRCA thread")).toBeVisible();
});

test('"New chat" clears the transcript and the ?c param', async ({ page }) => {
  await setup(page);
  await page.goto("ask", { waitUntil: "domcontentloaded" });
  await page.getByText("BRCA thread").click();
  await expect(page.getByText(/UI-SEED tumor-suppressor/)).toBeVisible();

  await page.getByRole("button", { name: /New chat/ }).first().click();
  await expect(page).toHaveURL(/\/ask(?!\?c=)/);
  await expect(page.getByText(/UI-SEED tumor-suppressor/)).toHaveCount(0);
  // no row is current after starting a fresh chat
  await expect(page.locator('[data-testid="conversation-row"][aria-current="true"]')).toHaveCount(0);
});

test("context meter is shown once a conversation has content", async ({ page }) => {
  await setup(page);
  await page.goto("ask", { waitUntil: "domcontentloaded" });
  await page.getByText("BRCA thread").click();
  await expect(page.getByText(/UI-SEED tumor-suppressor/)).toBeVisible();
  // the composer footer renders a percentage meter (e.g. "0%")
  await expect(page.getByText(/^\d{1,3}%$/).last()).toBeVisible();
});
