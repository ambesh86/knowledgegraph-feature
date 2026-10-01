import { test, expect, request as pwRequest } from "@playwright/test";
import { registerViaApi, uniqueUser, uuid } from "./helpers";

/**
 * API-level coverage for auth + conversation persistence + live intel. Fast and
 * deterministic — does not drive the slow LLM agent.
 */
test.describe("API — auth, conversations, intel", () => {
  test("register → me → focus area persisted", async ({ baseURL }) => {
    const ctx = await pwRequest.newContext({ baseURL });
    const user = uniqueUser("api");
    const reg = await registerViaApi(ctx, { ...user, focusArea: "oncology" });
    expect(reg.user.email).toBe(user.email.toLowerCase());
    expect(reg.user.focusArea).toBe("oncology");

    const me = await ctx.get("api/atlas/auth/me");
    expect(me.ok()).toBeTruthy();
    const meBody = await me.json();
    expect(meBody.user.focusArea).toBe("oncology");
    expect(meBody.greeting).toMatch(/Good (morning|afternoon|evening)/);
    await ctx.dispose();
  });

  test("unauthenticated conversations list is 401", async ({ baseURL }) => {
    const ctx = await pwRequest.newContext({ baseURL });
    const res = await ctx.get("api/atlas/conversations");
    expect(res.status()).toBe(401);
    await ctx.dispose();
  });

  test("conversation CRUD + title + ownership isolation", async ({ baseURL }) => {
    const owner = await pwRequest.newContext({ baseURL });
    const other = await pwRequest.newContext({ baseURL });
    await registerViaApi(owner, uniqueUser("owner"));
    await registerViaApi(other, uniqueUser("other"));

    const id = uuid();
    // create
    let r = await owner.post("api/atlas/conversations", { data: { id, source: "eugene" } });
    expect(r.status()).toBe(201);

    // append two turns
    r = await owner.post(`api/atlas/conversations/${id}/messages`, {
      data: { role: "user", content: "What proteins do BRCA1 and BRCA2 encode?" },
    });
    expect(r.status()).toBe(201);
    r = await owner.post(`api/atlas/conversations/${id}/messages`, {
      data: { role: "assistant", content: "Tumor-suppressor DNA-repair proteins." },
    });
    expect(r.status()).toBe(201);

    // title (LLM or heuristic — must be non-empty)
    r = await owner.post(`api/atlas/conversations/${id}/title`);
    expect(r.ok()).toBeTruthy();
    const title = (await r.json()).title as string;
    expect(title.length).toBeGreaterThan(2);

    // list shows it with 2 messages
    r = await owner.get("api/atlas/conversations");
    const list = (await r.json()).conversations as Array<{ id: string; message_count: number; title: string }>;
    const mine = list.find((c) => c.id === id);
    expect(mine, "own conversation appears in list").toBeTruthy();
    expect(mine!.message_count).toBe(2);

    // fetch full conversation
    r = await owner.get(`api/atlas/conversations/${id}`);
    expect(r.ok()).toBeTruthy();
    expect((await r.json()).messages.length).toBe(2);

    // OTHER user cannot see or fetch it
    r = await other.get(`api/atlas/conversations/${id}`);
    expect(r.status()).toBe(404);
    r = await other.delete(`api/atlas/conversations/${id}`);
    expect(r.status()).toBe(404);

    // rename
    r = await owner.patch(`api/atlas/conversations/${id}`, { data: { title: "Renamed thread" } });
    expect(r.ok()).toBeTruthy();
    r = await owner.get("api/atlas/conversations");
    expect((await r.json()).conversations.find((c: { id: string }) => c.id === id).title).toBe("Renamed thread");

    // delete (cascades messages)
    r = await owner.delete(`api/atlas/conversations/${id}`);
    expect(r.ok()).toBeTruthy();
    r = await owner.get(`api/atlas/conversations/${id}`);
    expect(r.status()).toBe(404);

    await owner.dispose();
    await other.dispose();
  });

  test("rejects a non-UUID conversation id", async ({ baseURL }) => {
    const ctx = await pwRequest.newContext({ baseURL });
    await registerViaApi(ctx, uniqueUser("uuid"));
    const res = await ctx.post("api/atlas/conversations", { data: { id: "not-a-uuid" } });
    expect(res.status()).toBe(400);
    await ctx.dispose();
  });

  test("live intel digest returns per-area feeds", async ({ baseURL }) => {
    test.slow(); // hits live public APIs
    const ctx = await pwRequest.newContext({ baseURL });
    await registerViaApi(ctx, { ...uniqueUser("intel"), focusArea: "hemophilia" });
    const res = await ctx.get("api/atlas/intel", { timeout: 50_000 });
    expect(res.ok()).toBeTruthy();
    const d = await res.json();
    expect(d.area).toBe("hemophilia");
    expect(Array.isArray(d.papers)).toBeTruthy();
    expect(Array.isArray(d.trials)).toBeTruthy();
    expect(Array.isArray(d.patents)).toBeTruthy();
    // At least one live source should return something for hemophilia.
    expect(d.papers.length + d.trials.length + d.patents.length).toBeGreaterThan(0);
    await ctx.dispose();
  });
});
