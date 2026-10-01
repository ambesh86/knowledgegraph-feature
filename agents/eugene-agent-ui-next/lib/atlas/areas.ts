/**
 * Therapeutic focus areas — the list a researcher picks from in Settings.
 *
 * These now mirror the scan taxonomy in
 * `ingestion/src/pipeline/config/research_areas.yaml`, which is itself derived from
 * CSL's seeded portfolio (`bin/seed/csl_behring_assets.cypher`).
 *
 * They did not always. The original list was generic pharma categories — hematology,
 * nephrology, immunology, oncology — and two of those had no counterpart in CSL's
 * franchises at all. A user who chose "Nephrology" got no nephrology signals, because
 * none are scanned; they silently fell back to the union of every area and were shown
 * the whole corpus labelled as their focus. That is worse than an empty result: it is
 * a wrong answer delivered confidently.
 *
 * Aligning the two vocabularies means the choice a user makes is a choice the system
 * can actually honour. `LEGACY_AREA_MAP` keeps existing `users.focus_area` values
 * working, since the column already holds the old ids.
 *
 * Shared by client and server — no server-only imports here.
 */

export interface FocusArea {
  id: string;
  label: string;
  blurb: string;
  /** Free-text query used against PubMed / Europe PMC / ClinicalTrials. */
  query: string;
  /** Keywords used to filter seeded signals/companies/programs to this area. */
  keywords: string[];
  /** Seeded company tickers most relevant to this area. */
  companies: string[];
  accent: string;
}

/**
 * Keys match `areas[].id` in research_areas.yaml exactly. When one changes, the other
 * must — that pairing is what lets the scanner honour a user's selection directly
 * instead of guessing at a translation.
 */
export const FOCUS_AREAS: Record<string, FocusArea> = {
  hemophilia: {
    id: "hemophilia",
    label: "Hemophilia A & B",
    blurb: "Factor and non-factor therapy, gene therapy, prophylaxis",
    query: "hemophilia gene therapy factor VIII factor IX prophylaxis",
    keywords: ["hemophilia", "factor viii", "factor ix", "gene therapy", "emicizumab", "inhibitor"],
    companies: ["SGMO", "BMRN", "PFE", "ALNY"],
    accent: "#e11d2a",
  },
  hereditary_angioedema: {
    id: "hereditary_angioedema",
    label: "Hereditary angioedema",
    blurb: "C1-INH and plasma kallikrein inhibition",
    query: "hereditary angioedema C1 esterase inhibitor plasma kallikrein",
    keywords: ["hereditary angioedema", "hae", "c1 inhibitor", "kallikrein", "garadacimab"],
    companies: ["TAK", "BCRX"],
    accent: "#7c3aed",
  },
  immunoglobulin: {
    id: "immunoglobulin",
    label: "Immunoglobulin therapy",
    blurb: "PID, CIDP and hypogammaglobulinemia",
    query: "immunoglobulin chronic immunodeficiency CIDP subcutaneous Ig",
    keywords: ["immunoglobulin", "cidp", "primary immunodeficiency", "ivig", "scig"],
    companies: ["PFE", "TAK"],
    accent: "#0ea5e9",
  },
  alpha1_antitrypsin: {
    id: "alpha1_antitrypsin",
    label: "Alpha-1 antitrypsin deficiency",
    blurb: "Augmentation therapy and emphysema progression",
    query: "alpha-1 antitrypsin deficiency augmentation therapy emphysema",
    keywords: ["alpha-1 antitrypsin", "aatd", "augmentation", "emphysema"],
    companies: ["TAK", "VRTX"],
    accent: "#16a34a",
  },
  cardiovascular_apoa1: {
    id: "cardiovascular_apoa1",
    label: "ApoA-I & acute coronary syndrome",
    blurb: "Cholesterol efflux and post-MI risk reduction",
    query: "apolipoprotein A-I acute coronary syndrome cholesterol efflux",
    keywords: ["apoa1", "csl112", "acute coronary syndrome", "hdl"],
    companies: ["NVS", "AMGN"],
    accent: "#d97706",
  },
};

export const DEFAULT_AREA = "hemophilia";

/**
 * Old ids that already exist in the `users.focus_area` column, mapped onto the
 * closest real franchise so signed-up users keep working across this change.
 * `nephrology` and `oncology` map to the broadest plasma-therapy franchise rather
 * than to nothing, and Settings will show them the corrected list on next visit.
 */
const LEGACY_AREA_MAP: Record<string, string> = {
  hematology: "hemophilia",
  immunology: "immunoglobulin",
  nephrology: "immunoglobulin",
  oncology: "immunoglobulin",
};

export function getArea(id: string | null | undefined): FocusArea {
  if (!id) return FOCUS_AREAS[DEFAULT_AREA];
  return (
    FOCUS_AREAS[id] ??
    FOCUS_AREAS[LEGACY_AREA_MAP[id.toLowerCase()] ?? ""] ??
    FOCUS_AREAS[DEFAULT_AREA]
  );
}

/** Canonical scan-area id for a stored profile value, legacy or current. */
export function resolveAreaId(id: string | null | undefined): string {
  return getArea(id).id;
}

export const AREA_OPTIONS = Object.values(FOCUS_AREAS).map((a) => ({
  id: a.id,
  label: a.label,
  blurb: a.blurb,
}));
