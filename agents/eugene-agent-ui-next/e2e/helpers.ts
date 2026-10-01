import { type APIRequestContext, type Page, expect } from "@playwright/test";

/** Deterministic-but-unique identity per run (Date.now is allowed in tests). */
export function uniqueUser(prefix = "e2e") {
  const tag = `${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
  return {
    name: `E2E ${prefix} ${tag}`,
    email: `${prefix}.${tag}@e2e.test`,
    password: "e2e-password-2026",
  };
}

/** Register a user through the API; the request context keeps the session cookie. */
export async function registerViaApi(
  request: APIRequestContext,
  user: { name: string; email: string; password: string; focusArea?: string }
) {
  const res = await request.post("api/atlas/auth/register", {
    data: { ...user, focusArea: user.focusArea ?? "hematology" },
  });
  expect(res.ok(), `register failed: ${res.status()} ${await res.text()}`).toBeTruthy();
  return res.json();
}

/** Create a titled conversation with two messages via the API (seed for UI tests). */
export async function seedConversation(
  request: APIRequestContext,
  opts: { id: string; source?: string; userMsg: string; asstMsg: string; title?: boolean }
) {
  let r = await request.post("api/atlas/conversations", {
    data: { id: opts.id, source: opts.source ?? "eugene" },
  });
  expect(r.status(), "create conversation").toBe(201);
  r = await request.post(`api/atlas/conversations/${opts.id}/messages`, {
    data: { role: "user", content: opts.userMsg, source: opts.source ?? "eugene" },
  });
  expect(r.status(), "append user msg").toBe(201);
  r = await request.post(`api/atlas/conversations/${opts.id}/messages`, {
    data: { role: "assistant", content: opts.asstMsg, source: opts.source ?? "eugene" },
  });
  expect(r.status(), "append assistant msg").toBe(201);
  if (opts.title !== false) {
    await request.post(`api/atlas/conversations/${opts.id}/title`);
  }
}

/** Log in through the UI form and land on the app. */
export async function uiLogin(page: Page, email: string, password: string) {
  await page.goto("login", { waitUntil: "domcontentloaded" });
  await page.getByPlaceholder(/you@company/i).fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: /^Sign in$/ }).click();
  await page.waitForURL(/\/today/, { timeout: 20_000 });
}

export function uuid(): string {
  // RFC4122 v4 — fine to generate in tests.
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
