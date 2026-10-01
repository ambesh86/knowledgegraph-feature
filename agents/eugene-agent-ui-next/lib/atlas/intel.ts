import "server-only";

/**
 * Live biomedical intelligence — the "overnight digest". Server-side fetchers
 * that scan public APIs for the newest literature, trials, and patents in a
 * researcher's focus area. No API key required; a descriptive User-Agent keeps
 * us on the right side of NCBI / Europe PMC usage policy (mirrors the proven
 * pattern in agents/eugene-agent-ws/src/query/tools/external_tools.py).
 */

const UA =
  "CSL-Atlas/1.0 (biomedical BD intelligence; +https://github.com/aisemanticexpert/knowledgegraph)";

/** Europe PMC returns titles with markup (<sup>, <i>, &amp; …). Clean to text. */
function clean(s: string): string {
  return (s ?? "")
    .replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#\d+;/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

async function getJson(url: string): Promise<any | null> {
  try {
    const res = await fetch(url, {
      headers: { "User-Agent": UA, Accept: "application/json" },
      signal: AbortSignal.timeout(12_000),
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export interface IntelItem {
  id: string;
  type: "paper" | "trial" | "patent";
  title: string;
  meta: string; // journal / sponsor / source line
  date: string; // ISO or display date
  url: string;
}


/**
 * Europe PMC does NOT reliably honour `sort=P_PDATE_D desc` on these queries.
 * Measured on the hematology area query, results came back ordered
 * 2026-06-11, 2026-07-01, 2026-03-03, 2026-06-01, 2026-05-29 — not sorted at all.
 * So we sort client-side and, more importantly, DROP anything outside the
 * requested window. Sorting alone was why a panel headed "overnight" showed
 * patents granted in 2002.
 */
function withinDays(iso: string, days: number): boolean {
  if (!iso) return false;
  const t = Date.parse(iso.length === 4 ? `${iso}-01-01` : iso);
  if (Number.isNaN(t)) return false;
  return Date.now() - t <= days * 86_400_000;
}

function freshest(items: IntelItem[], days: number, limit: number): IntelItem[] {
  return items
    .filter((i) => withinDays(i.date, days))
    .sort((a, b) => Date.parse(b.date || "0") - Date.parse(a.date || "0"))
    .slice(0, limit);
}

/** Recency windows. Literature moves faster than patents, which are published
 *  on a grant lag measured in years — a 30-day patent window returns nothing
 *  useful, so it is deliberately wider. */
export const WINDOW_DAYS = { paper: 45, trial: 45, patent: 540 } as const;

/** Recent PubMed literature (Europe PMC REST — indexes PubMed + more). */
export async function fetchPapers(query: string, limit = 6): Promise<IntelItem[]> {
  const url =
    "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" +
    new URLSearchParams({
      query: `(${query}) AND SRC:MED`,
      format: "json",
      pageSize: String(Math.max(limit * 5, 25)),
      sort: "P_PDATE_D desc",
      resultType: "lite",
    });
  const data = await getJson(url);
  const hits: any[] = data?.resultList?.result ?? [];
  const mapped = hits.map((h) => ({
    id: `pmc-${h.id}`,
    type: "paper" as const,
    title: clean(h.title) || "(untitled)",
    meta: clean([h.authorString, h.journalTitle || h.source].filter(Boolean).join(" · ")).slice(0, 140),
    date: h.firstPublicationDate || h.pubYear || "",
    url: h.pmid
      ? `https://pubmed.ncbi.nlm.nih.gov/${h.pmid}/`
      : `https://europepmc.org/article/${h.source}/${h.id}`,
  }));
  return freshest(mapped, WINDOW_DAYS.paper, limit);
}

/** Recently-updated clinical trials (ClinicalTrials.gov API v2). */
export async function fetchTrials(query: string, limit = 6): Promise<IntelItem[]> {
  const url =
    "https://clinicaltrials.gov/api/v2/studies?" +
    new URLSearchParams({
      "query.term": query,
      pageSize: String(Math.max(limit * 5, 25)),
      sort: "LastUpdatePostDate:desc",
    });
  const data = await getJson(url);
  const studies: any[] = data?.studies ?? [];
  const mapped = studies.map((s) => {
    const ps = s.protocolSection ?? {};
    const nct = ps.identificationModule?.nctId ?? "";
    return {
      id: `nct-${nct}`,
      type: "trial" as const,
      title: clean(ps.identificationModule?.briefTitle) || "(untitled trial)",
      meta: [
        ps.statusModule?.overallStatus,
        (ps.designModule?.phases ?? []).join(", "),
        ps.sponsorCollaboratorsModule?.leadSponsor?.name,
      ]
        .filter(Boolean)
        .join(" · ")
        .slice(0, 140),
      date: ps.statusModule?.lastUpdatePostDateStruct?.date ?? "",
      url: nct ? `https://clinicaltrials.gov/study/${nct}` : "",
    };
  });
  return freshest(mapped, WINDOW_DAYS.trial, limit);
}

/** Recent patents (Europe PMC patent index). */
export async function fetchPatents(query: string, limit = 6): Promise<IntelItem[]> {
  const url =
    "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" +
    new URLSearchParams({
      query: `(${query}) AND SRC:PAT`,
      format: "json",
      pageSize: String(Math.max(limit * 5, 25)),
      sort: "P_PDATE_D desc",
      resultType: "lite",
    });
  const data = await getJson(url);
  const hits: any[] = data?.resultList?.result ?? [];
  const mapped = hits.map((h) => ({
    id: `pat-${h.id}`,
    type: "patent" as const,
    title: clean(h.title) || "(untitled patent)",
    meta: clean([h.authorString, "Patent"].filter(Boolean).join(" · ")).slice(0, 140),
    date: h.firstPublicationDate || h.pubYear || "",
    url: `https://europepmc.org/article/PAT/${h.id}`,
  }));
  return freshest(mapped, WINDOW_DAYS.patent, limit);
}

export interface DigestResult {
  area: string;
  query: string;
  generatedAt: string;
  papers: IntelItem[];
  trials: IntelItem[];
  patents: IntelItem[];
}

/** Fetch all three feeds in parallel. Patents use a separate, tighter query
 *  (the patent corpus is small — a long free-text AND phrase returns nothing). */
export async function buildDigest(
  area: string,
  query: string,
  patentQuery?: string
): Promise<DigestResult> {
  const [papers, trials, patents] = await Promise.all([
    fetchPapers(query),
    fetchTrials(query),
    fetchPatents(patentQuery ?? query),
  ]);
  return {
    area,
    query,
    generatedAt: new Date().toISOString(),
    papers,
    trials,
    patents,
  };
}

// ── tiny per-user in-memory cache (avoids hammering the public APIs) ─────────
interface CacheEntry {
  at: number;
  data: DigestResult;
}
const CACHE = new Map<string, CacheEntry>();
const TTL_MS = 15 * 60 * 1000; // 15 min

export function getCached(key: string): DigestResult | null {
  const e = CACHE.get(key);
  if (e && Date.now() - e.at < TTL_MS) return e.data;
  return null;
}
export function setCached(key: string, data: DigestResult): void {
  CACHE.set(key, { at: Date.now(), data });
}
