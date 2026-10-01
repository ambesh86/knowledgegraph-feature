import { test, expect, request as pwRequest } from "@playwright/test";
import { registerViaApi, seedConversation, uiLogin, uniqueUser, uuid } from "./helpers";

test.describe("Views — auth form, Library, Settings, Today digest", () => {
  test("register + sign-in through the UI form shows the greeting", async ({ page, baseURL }) => {
    // Register out-of-band, then exercise the login FORM.
    const ctx = await pwRequest.newContext({ baseURL });
    const user = uniqueUser("form");
    await registerViaApi(ctx, user);
    await ctx.dispose();

    await uiLogin(page, user.email, user.password);
    await expect(page.getByRole("heading", { name: /Good (morning|afternoon|evening)/ })).toBeVisible();
  });

  test("invalid credentials are rejected in the UI", async ({ page }) => {
    await page.goto("login", { waitUntil: "domcontentloaded" });
    await page.getByPlaceholder(/you@company/i).fill("nobody@e2e.test");
    await page.locator('input[type="password"]').fill("wrongpassword123");
    await page.getByRole("button", { name: /^Sign in$/ }).click();
    await expect(page.getByText(/invalid|not found|incorrect|failed/i)).toBeVisible();
  });

  test("Library is a searchable conversation history", async ({ page }) => {
    const user = uniqueUser("lib");
    await registerViaApi(page.request, user);
    const id = uuid();
    await seedConversation(page.request, {
      id, userMsg: "Nephrology complement landscape", asstMsg: "LIB-SEED answer.", title: false,
    });
    await page.request.patch(`api/atlas/conversations/${id}`, { data: { title: "Complement Landscape Review" } });

    await page.goto("library", { waitUntil: "domcontentloaded" });
    // Scope to the Library list (the title also appears in the sidebar recents).
    const list = page.getByTestId("library-chats");
    await expect(list.getByText("Complement Landscape Review")).toBeVisible();
    // search narrows the list
    await page.getByPlaceholder(/Search conversations/i).fill("complement");
    await expect(list.getByText("Complement Landscape Review")).toBeVisible();
    await page.getByPlaceholder(/Search conversations/i).fill("zzz-no-match");
    await expect(list.getByText(/No conversations match/i)).toBeVisible();
  });

  test("Settings can change the research focus area", async ({ page }) => {
    const user = uniqueUser("set");
    await registerViaApi(page.request, { ...user, focusArea: "hemophilia" });
    await page.goto("settings", { waitUntil: "domcontentloaded" });
    await expect(page.getByText("Research focus")).toBeVisible();

    const select = page.locator("select").first();
    // Focus areas now mirror the scan taxonomy in research_areas.yaml. "nephrology"
    // was removed because CSL has no such franchise — picking it used to silently
    // show the analyst every area's signals labelled as their own.
    await select.selectOption("immunoglobulin");
    // the profile PATCH persists it — reflected by /me
    await expect
      .poll(async () => (await (await page.request.get("api/atlas/auth/me")).json()).user.focusArea)
      .toBe("immunoglobulin");
  });

  test("Today shows the live overnight digest", async ({ page }) => {
    test.slow(); // digest hits live public APIs
    await registerViaApi(page.request, { ...uniqueUser("today"), focusArea: "hemophilia" });
    await page.goto("today", { waitUntil: "domcontentloaded" });
    await expect(page.getByText(/While you were away/i)).toBeVisible();
    // it resolves to either results or a graceful empty/error state (never spins forever)
    await expect(page.getByText(/Scanning the internet/i)).toHaveCount(0, { timeout: 50_000 });
    // Scoped to the digest card. A page-wide text match is fragile: the header's
    // data-currency popover also mentions "Patents", and an unscoped `.first()`
    // resolved to that hidden element instead.
    await expect(
      page.getByTestId("overnight-digest")
        .getByText(/New research|Clinical trials|Patents|No new items|Couldn.t reach/i)
        .first()
    ).toBeVisible();
  });
});
