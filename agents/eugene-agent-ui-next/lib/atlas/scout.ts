/**
 * Types and client helpers for the Eugene Scout service (BD Use Case 1).
 *
 * These interfaces mirror the pydantic models in
 * `agents/eugene-scout/src/scout/models.py` field-for-field. When one side changes,
 * the other must — there is no code generation between them, so the field names here
 * are load-bearing documentation of that contract.
 *
 * Deliberately NOT `server-only`: client components render these shapes, and a
 * `server-only` import here would force a parallel set of duplicate type definitions.
 * Nothing in this file touches a secret or the network on its own — the fetching
 * helpers are used exclusively by route handlers under app/api/atlas/.
 */

import type { Priority } from "@/lib/atlas/seed";

/** Mirrors scout.models.SourceId. */
export type ScoutSource =
  | "clinicaltrials"
  | "europepmc_lit"
  | "europepmc_pat"
  | "sec_edgar"
  | "epo_ops";

/** Mirrors scout.models.SignalType — same values as the UI's own SignalType union,
 *  so the existing Radar filter chips work without translation. */
export type ScoutSignalType =
  | "Trial"
  | "Patent"
  | "Publication"
  | "Regulatory"
  | "Corporate";

export const SOURCE_LABEL: Record<ScoutSource, string> = {
  clinicaltrials: "ClinicalTrials.gov",
  europepmc_lit: "Europe PMC",
  europepmc_pat: "USPTO",
  sec_edgar: "SEC EDGAR",
  epo_ops: "EPO",
};

export interface SignalSourceRef {
  source: ScoutSource;
  external_id: string;
  url: string;
  published: string | null;
}

export interface ScoreFactorView {
  name: string;
  value: number;
  weight: number;
  contribution: number;
  inputs: Record<string, unknown>;
}

export interface ScoreBreakdown {
  total?: number;
  priority?: string;
  factors?: ScoreFactorView[];
  /** Source identifiers surfaced for pivoting straight out to EDGAR / the registry. */
  ticker?: string;
  cik?: string;
  nct_id?: string;
  publication_number?: string;
}

/** A node in Eugene's knowledge graph that this signal mentions. Context for the
 *  analyst, never an input to the score — ranking on "we already know this" would put
 *  the familiar above the novel, which is backwards for partnership scouting. */
export interface GraphEntity {
  id: string;
  value: string;
  matched_term: string;
}

/** Why a signal is flagged for a second look. Shown, never used to hide it. */
export type ReviewReason =
  | "borderline_score"
  | "thin_evidence"
  | "unverified_rationale"
  | "undated";

export const REVIEW_REASON_LABEL: Record<ReviewReason, string> = {
  borderline_score: "Score sits on a priority boundary",
  thin_evidence: "Single source with a weak keyword match",
  unverified_rationale: "Generated rationale failed verification",
  undated: "No publication date could be established",
};

export interface Signal {
  id: string;
  area: string;
  type: ScoutSignalType;
  title: string;
  summary: string;
  rationale: string;
  /** 'llm' or 'template'. Surfaced in the UI — an LLM-written paragraph and a
   *  deterministic one are not the same claim. */
  rationale_kind: "llm" | "template";
  score: number;
  score_breakdown: ScoreBreakdown;
  priority: Priority;
  company_name: string | null;
  company_id: string | null;
  stage: string | null;
  matched_keywords: string[];
  published: string | null;
  detected_at: string;
  first_seen_run: string;
  last_seen_run: string;
  sources: SignalSourceRef[];
  dismissed: boolean;
  graph_entities: GraphEntity[];
  needs_review: boolean;
  review_reasons: ReviewReason[];
}

export interface CompanyScore {
  id: string;
  name: string;
  normalized_name: string;
  ticker: string | null;
  cik: string | null;
  areas: string[];
  score: number;
  delta_30d: number;
  signal_count: number;
  high_priority_count: number;
  top_signal_id: string | null;
  last_signal_at: string | null;
  computed_at: string;
  breakdown: Record<string, unknown>;
}

export interface SourceReportView {
  source: ScoutSource;
  area: string;
  ok: boolean;
  fetched: number;
  kept: number;
  duration_ms: number;
  error: string | null;
}

export interface RunSummary {
  run_id: string;
  trigger: string;
  status: "running" | "ok" | "degraded" | "failed" | "skipped";
  started_at: string;
  finished_at: string | null;
  areas: string[];
  signals_new: number;
  signals_kept: number;
  companies_scored: number;
  error: string | null;
  sources?: SourceReportView[];
  failed_sources?: string[];
}

export interface PriorityCounts {
  high: number;
  med: number;
  watch: number;
}

/**
 * Every BFF response carries `degraded`. When the scanner is unreachable the route
 * still returns a well-formed, empty payload with `degraded: true` and a reason,
 * exactly as `app/api/atlas/digest/route.ts` already does — a blank Radar with an
 * explanation beats a 500 that blanks the page.
 */
export interface SignalsResponse {
  signals: Signal[];
  total: number;
  counts: PriorityCounts;
  limit: number;
  offset: number;
  generated_at: string | null;
  last_run: RunSummary | null;
  degraded: boolean;
  reason?: string;
}

export interface WatchlistResponse {
  companies: CompanyScore[];
  total: number;
  generated_at: string | null;
  degraded: boolean;
  reason?: string;
}

export interface StatsResponse {
  areas: string[];
  signal_count: number;
  priority_counts: PriorityCounts;
  company_count: number;
  generated_at: string | null;
  new_signals?: number;
  new_high_priority?: number;
  last_run: RunSummary | null;
  degraded: boolean;
  reason?: string;
}

export interface RunsResponse {
  runs: RunSummary[];
  total: number;
  degraded: boolean;
  reason?: string;
}

/** Per-source data currency. `latest_published` is extracted from the records
 *  themselves — it is the newest publication date that source actually returned. */
export interface SourceFreshness {
  source: ScoutSource;
  latest_published: string | null;
  signal_count: number;
}

/**
 * Three different clocks, reported separately because conflating them misleads:
 * the platform's date, when we last looked, and how recent the newest thing we found
 * is. "Scanned 20 minutes ago" says nothing about whether the field has moved.
 */
export interface FreshnessResponse {
  today: string;
  index_loaded_at: string | null;
  areas: string[];
  signal_count: number;
  newest_signal_date: string | null;
  oldest_signal_date: string | null;
  sources: SourceFreshness[];
  last_scan: {
    run_id: string;
    started_at: string;
    finished_at: string | null;
    status: string;
  } | null;
  next_scan_at: string | null;
  schedule: { hour: number; minute: number; timezone: string };
  degraded: boolean;
  reason?: string;
}

export interface ScoutStatus {
  running: boolean;
  last_started: string | null;
  last_finished: string | null;
  latest_run: RunSummary | null;
  index: { areas: string[]; loaded_at: string | null; empty: boolean };
  schedule: {
    daily_hour: number;
    daily_minute: number;
    timezone: string;
    weekly_day_of_week: number;
  };
  sources_available: Record<string, boolean>;
  degraded: boolean;
  reason?: string;
}

/** One company entry in the weekly briefing. Mirrors `digest._entry()`. */
export interface BriefingEntry {
  rank: number;
  company_id: string;
  company: string;
  ticker: string | null;
  score: number;
  delta_30d: number;
  signal_count: number;
  high_priority_count: number;
  areas: string[];
  rationale: string;
  sources_consulted: string[];
  next_action: string;
  evidence: {
    id: string;
    title: string;
    type: string;
    score: number;
    priority: string;
    published: string | null;
    url: string;
    sources: { source: string; url: string }[];
  }[];
}

/** Mirrors `digest.build()`. The use case's headline deliverable: 8-12 ranked
 *  companies, each with a rationale, the sources consulted and a next action. */
export interface BriefingResponse {
  area: string;
  area_label: string;
  generated_at: string | null;
  run_id?: string | null;
  period_end?: string;
  company_count: number;
  /** True when fewer than 8 companies cleared the bar. Surfaced rather than hidden —
   *  a briefing padded to a target teaches its readers to distrust the ranking. */
  below_target: boolean;
  companies: BriefingEntry[];
  notable_unattributed: {
    id: string;
    title: string;
    type: string;
    score: number;
    priority: string;
    published: string | null;
    url: string;
  }[];
  totals: { signals: number; high: number; companies_tracked: number };
  degraded: boolean;
  reason?: string;
}

export interface ScanConfigView {
  version: number;
  updated_at: string;
  updated_by: string | null;
  enabled_areas: string[];
  sources: Record<string, { enabled: boolean; window_days: number; limit_per_area: number }>;
  weights: Record<string, number>;
  thresholds: { high: number; med: number };
  modalities: string[];
  stage_scores: Record<string, number>;
  notify_min_score: number;
  generic_keywords: string[];
  min_specific_matches: number;
  degraded?: boolean;
  reason?: string;
}

// ── Use Case 2: accelerated scientific due diligence ────────────────────────
//
// Mirrors `scout.duediligence.brief.build()`. The shapes below are deliberately
// permissive about emptiness: a section with no evidence is a normal, meaningful
// result in this workflow, and the UI's job is to render *why* it is empty rather
// than to hide it.

/** One row of `GET /dd/briefs` — enough to list targets without loading briefs. */
export interface BriefIndexEntry {
  id: string;
  company: string;
  asset: string | null;
  label: string;
  generated_at: string;
  confidence_band: ConfidenceBand;
  confidence_score: number | null;
  signals_total: number;
}

export interface BriefsResponse {
  count: number;
  targets: BriefIndexEntry[];
  degraded: boolean;
  reason?: string;
}

/** Mirrors `duediligence.confidence.ConfidenceBand`. `insufficient_evidence` is not
 *  a low score — it is the refusal to produce one, and the UI must not render it as
 *  a number near zero. */
export type ConfidenceBand = "insufficient_evidence" | "low" | "moderate" | "high";

export interface ConfidenceComponent {
  key: string;
  label: string;
  /** null means the dimension could not be assessed. NOT zero — see confidence.py. */
  score: number | null;
  weight: number;
  assessable: boolean;
  finding: string;
  evidence: string[];
}

export interface ConfidenceView {
  band: ConfidenceBand;
  score: number | null;
  score_out_of: number;
  needs_human_review: boolean;
  reasons: string[];
  signals_considered: number;
  distinct_sources: number;
  components: ConfidenceComponent[];
  unassessable_components: string[];
}

export interface BriefEvidence {
  title: string;
  url: string;
  source: string;
  published: string | null;
  score: number | null;
}

export interface BriefSection {
  key: string;
  title: string;
  summary: string;
  evidence_count: number;
  sources_consulted: string[];
  evidence: BriefEvidence[];
  /** Present only when the section is empty: what that emptiness actually implies. */
  coverage_note: string | null;
}

export interface BriefRiskFlag {
  severity: "high" | "medium" | "low";
  flag: string;
  detail: string;
}

export interface DueDiligenceBrief {
  schema: string;
  target: {
    id: string;
    company: string;
    asset: string | null;
    label: string;
    search_terms: string[];
  };
  generated_at: string;
  /** `provenance` distinguishes a model-written paragraph from a computed one. The
   *  UI shows which, because they are different claims. */
  executive_summary?: { text: string; provenance: "llm" | "template" };
  confidence: ConfidenceView;
  sections: BriefSection[];
  risk_flags: BriefRiskFlag[];
  coverage: {
    sources_consulted: string[];
    sources_failed: string[];
    signals_total: number;
    complete: boolean;
    relevance?: string;
  };
  next_action: string;
  timing_ms?: number;
  from_cache?: boolean;
  stored?: boolean;
  storage_error?: string;
  degraded?: boolean;
  reason?: string;
}

export const BAND_LABEL: Record<ConfidenceBand, string> = {
  insufficient_evidence: "Insufficient evidence",
  low: "Low confidence",
  moderate: "Moderate confidence",
  high: "High confidence",
};

// ── presentation helpers (shared by several views) ──────────────────────────

/** "3 days ago" / "today". Dates from the scanner are ISO strings or null. */
export function relativeDay(iso: string | null | undefined): string {
  if (!iso) return "date unknown";
  const then = Date.parse(iso.length <= 10 ? `${iso}T00:00:00Z` : iso);
  if (Number.isNaN(then)) return "date unknown";
  const days = Math.floor((Date.now() - then) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  if (days < 365) return `${Math.floor(days / 30)} mo ago`;
  return `${Math.floor(days / 365)} yr ago`;
}

/** Short absolute date for table cells, e.g. "Aug 7". */
export function shortDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const t = Date.parse(iso.length <= 10 ? `${iso}T00:00:00Z` : iso);
  if (Number.isNaN(t)) return "—";
  return new Date(t).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** Absolute date in the platform's display format: "7 Aug 2026".
 *  Standard platforms lead with the absolute date and treat "2 days ago" as the
 *  supporting detail, because an absolute date is verifiable against the source and
 *  a relative one drifts as the page sits open. */
export function absoluteDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const t = Date.parse(iso.length <= 10 ? `${iso}T00:00:00Z` : iso);
  if (Number.isNaN(t)) return "—";
  return new Date(t).toLocaleDateString("en-GB", {
    day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
  });
}

/** "7 Aug 2026 · 2 days ago" — absolute first, relative as context. */
export function datedLabel(iso: string | null | undefined): string {
  if (!iso) return "date unknown";
  return `${absoluteDate(iso)} · ${relativeDay(iso)}`;
}

/** The two factors that contributed most — the question an analyst challenging a
 *  score actually asks. */
export function topFactors(breakdown: ScoreBreakdown, n = 2): ScoreFactorView[] {
  return [...(breakdown.factors ?? [])]
    .filter((f) => f.contribution > 0)
    .sort((a, b) => b.contribution - a.contribution)
    .slice(0, n);
}

export function factorLabel(name: string): string {
  return (
    {
      area_fit: "Area fit",
      stage_fit: "Development stage",
      recency: "Recency",
      modality_fit: "Modality fit",
      corroboration: "Corroboration",
      company_context: "Company context",
    }[name] ?? name
  );
}
