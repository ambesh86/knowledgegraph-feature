import "server-only";

/**
 * Server-side client for the Eugene Scout service.
 *
 * One rule governs every function here: **never throw upward into a page render.**
 * Each call returns either the scanner's payload or a well-formed empty payload
 * carrying `degraded: true` and a reason. This is the same posture
 * `app/api/atlas/digest/route.ts` already takes, and for the same reason — "nothing
 * new" and "the scanner is down" are both legitimate states that the Radar must be
 * able to draw, and neither justifies a 500 that blanks the page.
 */

import type {
  BriefsResponse,
  DueDiligenceBrief,
  FreshnessResponse,
  BriefingResponse,
  RunsResponse,
  ScanConfigView,
  ScoutStatus,
  SignalsResponse,
  StatsResponse,
  WatchlistResponse,
} from "@/lib/atlas/scout";

const SCOUT_URL = process.env.EUGENE_SCOUT_URL ?? "http://eugene_scout:8000";

/**
 * Shared secret for the scanner API. Server-side only — this module is `server-only`,
 * so the token is never shipped to a browser. Absent means the scanner is running
 * unauthenticated, which it reports from /health.
 */
const SCOUT_TOKEN = process.env.SCOUT_API_TOKEN ?? "";

function authHeaders(): Record<string, string> {
  return SCOUT_TOKEN ? { Authorization: `Bearer ${SCOUT_TOKEN}` } : {};
}

/** Queries are served from an in-memory index, so they are fast; a scan is not, and
 *  the manual Rescan button is the only caller that waits on one. */
const QUERY_TIMEOUT_MS = 10_000;
const SCAN_TIMEOUT_MS = 120_000;

async function call<T>(
  path: string,
  fallback: T,
  init?: RequestInit & { timeoutMs?: number }
): Promise<T> {
  const { timeoutMs = QUERY_TIMEOUT_MS, ...rest } = init ?? {};
  try {
    const res = await fetch(`${SCOUT_URL}${path}`, {
      ...rest,
      headers: { Accept: "application/json", ...authHeaders(), ...(rest.headers ?? {}) },
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      return {
        ...fallback,
        degraded: true,
        reason: `scout returned ${res.status}${detail ? `: ${detail.slice(0, 200)}` : ""}`,
      };
    }
    const data = (await res.json()) as T;
    return { ...data, degraded: false };
  } catch (e) {
    return {
      ...fallback,
      degraded: true,
      reason: e instanceof Error ? e.message : String(e),
    };
  }
}

const EMPTY_COUNTS = { high: 0, med: 0, watch: 0 };

export function fetchSignals(params: URLSearchParams): Promise<SignalsResponse> {
  return call<SignalsResponse>(`/signals?${params}`, {
    signals: [],
    total: 0,
    counts: EMPTY_COUNTS,
    limit: 0,
    offset: 0,
    generated_at: null,
    last_run: null,
    degraded: true,
  });
}

export function fetchSignal(id: string): Promise<Record<string, unknown> | null> {
  return call<Record<string, unknown> | null>(
    `/signals/${encodeURIComponent(id)}`,
    null as unknown as Record<string, unknown>
  );
}

export function patchSignal(id: string, dismissed: boolean): Promise<Record<string, unknown>> {
  return call<Record<string, unknown>>(
    `/signals/${encodeURIComponent(id)}`,
    {},
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dismissed }),
    }
  );
}

export function fetchWatchlist(params: URLSearchParams): Promise<WatchlistResponse> {
  return call<WatchlistResponse>(`/companies?${params}`, {
    companies: [],
    total: 0,
    generated_at: null,
    degraded: true,
  });
}

export function fetchStats(params: URLSearchParams): Promise<StatsResponse> {
  return call<StatsResponse>(`/stats?${params}`, {
    areas: [],
    signal_count: 0,
    priority_counts: EMPTY_COUNTS,
    company_count: 0,
    generated_at: null,
    last_run: null,
    degraded: true,
  });
}

export function fetchRuns(limit = 10): Promise<RunsResponse> {
  return call<RunsResponse>(`/runs?limit=${limit}`, { runs: [], total: 0, degraded: true });
}

export function fetchFreshness(uiArea: string | undefined): Promise<FreshnessResponse> {
  const params = new URLSearchParams({ ui_area: uiArea ?? "" });
  return call<FreshnessResponse>(`/freshness?${params}`, {
    today: new Date().toISOString().slice(0, 10),
    index_loaded_at: null,
    areas: [],
    signal_count: 0,
    newest_signal_date: null,
    oldest_signal_date: null,
    sources: [],
    last_scan: null,
    next_scan_at: null,
    schedule: { hour: 2, minute: 0, timezone: "UTC" },
    degraded: true,
  });
}

export function fetchStatus(): Promise<ScoutStatus> {
  return call<ScoutStatus>("/status", {
    running: false,
    last_started: null,
    last_finished: null,
    latest_run: null,
    index: { areas: [], loaded_at: null, empty: true },
    schedule: { daily_hour: 2, daily_minute: 0, timezone: "UTC", weekly_day_of_week: 0 },
    sources_available: {},
    degraded: true,
  });
}

export function fetchConfig(): Promise<ScanConfigView> {
  return call<ScanConfigView>("/config", {
    version: 0,
    updated_at: "",
    updated_by: null,
    enabled_areas: [],
    sources: {},
    weights: {},
    thresholds: { high: 75, med: 55 },
    modalities: [],
    stage_scores: {},
    notify_min_score: 75,
    generic_keywords: [],
    min_specific_matches: 1,
    degraded: true,
  });
}

export function saveConfig(payload: Record<string, unknown>): Promise<ScanConfigView> {
  return call<ScanConfigView>(
    "/config",
    { degraded: true } as unknown as ScanConfigView,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

/** Trigger a scan. Long timeout — this is the only call that waits on real work. */
export function triggerScan(areas?: string[]): Promise<Record<string, unknown>> {
  return call<Record<string, unknown>>(
    "/scan",
    { status: "failed" },
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trigger: "manual", areas: areas ?? null }),
      timeoutMs: SCAN_TIMEOUT_MS,
    }
  );
}

export function sendTestNotification(): Promise<Record<string, unknown>> {
  return call<Record<string, unknown>>(
    "/notify/test",
    { configured: false, delivered: false },
    { method: "POST" }
  );
}

/**
 * The weekly partnership briefing.
 *
 * Scoped by `ui_area` rather than by a scan-area id resolved here: the mapping from
 * the UI's coarse profile areas onto the scan taxonomy lives in `areas.UI_AREA_MAP`
 * in the scanner, and a second copy of it in TypeScript would be the one that
 * silently drifts.
 */
export function fetchBriefing(uiArea: string | undefined): Promise<BriefingResponse> {
  const params = new URLSearchParams({ ui_area: uiArea ?? "" });
  return call<BriefingResponse>(`/digest?${params}`, {
    area: "",
    area_label: "",
    generated_at: null,
    company_count: 0,
    below_target: false,
    companies: [],
    notable_unattributed: [],
    totals: { signals: 0, high: 0, companies_tracked: 0 },
    degraded: true,
  });
}

export function fetchBriefingMarkdown(uiArea: string | undefined): Promise<string | null> {
  const params = new URLSearchParams({ ui_area: uiArea ?? "", format: "markdown" });
  return fetch(`${SCOUT_URL}/digest?${params}`, {
    headers: authHeaders(),
    cache: "no-store",
    signal: AbortSignal.timeout(QUERY_TIMEOUT_MS),
  })
    .then((r) => (r.ok ? r.text() : null))
    .catch(() => null);
}

// ── Use Case 2: accelerated scientific due diligence ────────────────────────

/**
 * Running a brief is not a query.
 *
 * `POST /dd/brief` fans out across four live public registries and takes ~30s
 * against a cold target. The 10s query timeout would abort every genuine first run
 * and leave the user staring at "the scanner is down" while the scanner was, in
 * fact, working. Sized above the measured worst case rather than at it, because the
 * cost of waiting a little longer is nothing next to discarding a completed run.
 */
const DILIGENCE_TIMEOUT_MS = 180_000;

export function fetchBriefs(): Promise<BriefsResponse> {
  return call<BriefsResponse>("/dd/briefs", { count: 0, targets: [], degraded: true });
}

/**
 * One stored brief, or null when there is none.
 *
 * Distinguished from the degraded case deliberately: "no brief for this target yet"
 * is a normal state with an obvious remedy (run one), while "the scanner is
 * unreachable" is not, and a page that renders them identically sends the user to
 * press a button that cannot work.
 */
export async function fetchBrief(
  targetId: string,
  date?: string
): Promise<DueDiligenceBrief | null | { degraded: true; reason: string }> {
  const params = date ? `?${new URLSearchParams({ date })}` : "";
  try {
    const res = await fetch(`${SCOUT_URL}/dd/brief/${encodeURIComponent(targetId)}${params}`, {
      headers: { Accept: "application/json", ...authHeaders() },
      cache: "no-store",
      signal: AbortSignal.timeout(QUERY_TIMEOUT_MS),
    });
    if (res.status === 404) return null;
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      return { degraded: true, reason: `scout returned ${res.status}${detail ? `: ${detail.slice(0, 200)}` : ""}` };
    }
    return (await res.json()) as DueDiligenceBrief;
  } catch (e) {
    return { degraded: true, reason: e instanceof Error ? e.message : String(e) };
  }
}

/**
 * Generate (or return the stored) brief for a target.
 *
 * The scanner's own 409 — "this instance is serve-only and has no route to the
 * public sources" — is passed through with its message intact rather than being
 * flattened into a generic failure. On the split AWS deployment that message is the
 * entire diagnosis, and replacing it with "something went wrong" would send someone
 * to read logs for an answer they were already given.
 */
export async function generateBrief(payload: {
  company: string;
  asset?: string | null;
  force?: boolean;
}): Promise<{ ok: true; brief: DueDiligenceBrief } | { ok: false; status: number; reason: string }> {
  try {
    const res = await fetch(`${SCOUT_URL}/dd/brief`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json", ...authHeaders() },
      body: JSON.stringify({
        company: payload.company,
        asset: payload.asset || null,
        force: payload.force ?? false,
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(DILIGENCE_TIMEOUT_MS),
    });
    if (!res.ok) {
      let reason = `scout returned ${res.status}`;
      const body = await res.json().catch(() => null);
      if (body && typeof body.detail === "string") reason = body.detail;
      return { ok: false, status: res.status, reason };
    }
    return { ok: true, brief: (await res.json()) as DueDiligenceBrief };
  } catch (e) {
    const timedOut = e instanceof DOMException && e.name === "TimeoutError";
    return {
      ok: false,
      status: timedOut ? 504 : 502,
      reason: timedOut
        ? "The diligence run exceeded 3 minutes and was abandoned. The sources it reads are live public registries; one of them is likely rate-limiting or down."
        : e instanceof Error ? e.message : String(e),
    };
  }
}
