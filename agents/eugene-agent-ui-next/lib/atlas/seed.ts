/**
 * Seeded demo intelligence for the Atlas workspace. All descriptive copy is
 * original. Company tickers / locations are public facts; scores, signals,
 * programs and briefs are illustrative sample data for the demo environment.
 */

export type Priority = "high" | "med" | "watch";
export type SignalType = "Trial" | "Patent" | "Publication" | "Regulatory" | "Corporate";
export type Stage = "Watching" | "Pre-Engage" | "In Discussion" | "Diligence";
export type BriefStatus = "In progress" | "Draft" | "In review" | "Approved" | "Archived";

export interface Signal {
  id: string;
  title: string;
  summary: string;
  type: SignalType;
  priority: Priority;
  date: string;
  scoreFrom?: number;
  scoreTo?: number;
  company?: string;
}

export interface Company {
  id: string;
  name: string;
  ticker: string;
  hq: string;
  score: number;
  delta30: number;
  stage: Stage;
  areas: string[];
  lastUpdate: string;
}

export interface Program {
  id: string;
  name: string;
  area: string;
  modality: string;
  phase: string;
  description: string;
  relatedSignals: number;
  highPriority: number;
}

export interface Brief {
  id: string;
  title: string;
  status: BriefStatus;
  author: string;
  type: string;
  updated: string;
}

export interface ResearchTemplate {
  id: string;
  name: string;
  description: string;
  sections: number;
  duration: string;
  recommended?: boolean;
}

export const SIGNALS: Signal[] = [
  {
    id: "sig-1",
    title: "Sangamo posts Phase III interim for Hemophilia B gene therapy",
    summary:
      "Interim readout reports durable Factor IX expression at 18 months, strengthening Sangamo's position as a late-stage partner candidate in your Hemophilia B program.",
    type: "Trial", priority: "high", date: "Jun 24", scoreFrom: 76, scoreTo: 84, company: "Sangamo Therapeutics",
  },
  {
    id: "sig-2",
    title: "Pfizer files patent on bispecific Factor IXa antibody",
    summary:
      "A non-Factor mechanism filing that overlaps your Hemophilia A priority, suggesting a hedge beyond marstacimab and a shift in the competitive landscape.",
    type: "Patent", priority: "med", date: "Jun 25", scoreFrom: 72, scoreTo: 76, company: "Pfizer",
  },
  {
    id: "sig-3",
    title: "Diligence brief — IP section ready for review",
    summary:
      "Your Roche immunology adjacency brief auto-completed its freedom-to-operate and IP landscape analysis. Ready for your review.",
    type: "Corporate", priority: "high", date: "Jun 26",
  },
  {
    id: "sig-4",
    title: "Apellis reports positive complement data in IgA nephropathy",
    summary:
      "Proteinuria reduction at 24 weeks supports the C3-targeting thesis in IgAN and tightens the competitive map for your nephrology program.",
    type: "Publication", priority: "med", date: "Jun 23", scoreFrom: 78, scoreTo: 81, company: "Apellis Pharmaceuticals",
  },
  {
    id: "sig-5",
    title: "FDA grants Fast Track to a recombinant subcutaneous Ig candidate",
    summary:
      "A regulatory designation in chronic immunodeficiency that may pressure plasma-derived Ig franchises over the medium term.",
    type: "Regulatory", priority: "watch", date: "Jun 22",
  },
  {
    id: "sig-6",
    title: "Alnylam expands RNAi pipeline into cardiovascular indications",
    summary:
      "Pipeline diversification signal; limited direct overlap today but worth monitoring for platform-level partnership opportunities.",
    type: "Corporate", priority: "watch", date: "Jun 21", scoreFrom: 70, scoreTo: 73, company: "Alnylam Pharmaceuticals",
  },
  {
    id: "sig-7",
    title: "BioMarin AAV durability questioned in new long-term analysis",
    summary:
      "Independent re-analysis raises durability questions for AAV Factor VIII, a potential opening for differentiated long-acting prophylaxis.",
    type: "Publication", priority: "med", date: "Jun 20", scoreFrom: 73, scoreTo: 71, company: "BioMarin Pharmaceutical",
  },
];

export const COMPANIES: Company[] = [
  { id: "c-sgmo", name: "Sangamo Therapeutics", ticker: "SGMO", hq: "Brisbane, CA", score: 84, delta30: 8, stage: "In Discussion", areas: ["Hematology", "Neurology"], lastUpdate: "Jun 24" },
  { id: "c-apls", name: "Apellis Pharmaceuticals", ticker: "APLS", hq: "Waltham, MA", score: 81, delta30: 6, stage: "Pre-Engage", areas: ["Nephrology", "Hematology"], lastUpdate: "Jun 23" },
  { id: "c-chnk", name: "Chinook (Novartis)", ticker: "NVS", hq: "Vancouver, BC", score: 79, delta30: 5, stage: "Watching", areas: ["Nephrology"], lastUpdate: "Jun 21" },
  { id: "c-pfe", name: "Pfizer", ticker: "PFE", hq: "New York, NY", score: 76, delta30: 4, stage: "Watching", areas: ["Hematology", "Immunology"], lastUpdate: "Jun 25" },
  { id: "c-alny", name: "Alnylam Pharmaceuticals", ticker: "ALNY", hq: "Cambridge, MA", score: 73, delta30: 3, stage: "Pre-Engage", areas: ["Hematology", "Cardiovascular"], lastUpdate: "Jun 21" },
  { id: "c-bmrn", name: "BioMarin Pharmaceutical", ticker: "BMRN", hq: "San Rafael, CA", score: 71, delta30: -2, stage: "Watching", areas: ["Hematology", "Rare disease"], lastUpdate: "Jun 20" },
  { id: "c-rare", name: "Ultragenyx", ticker: "RARE", hq: "Novato, CA", score: 68, delta30: 2, stage: "Watching", areas: ["Rare disease", "Metabolic"], lastUpdate: "Jun 19" },
  { id: "c-rcus", name: "Arcus Biosciences", ticker: "RCUS", hq: "Hayward, CA", score: 66, delta30: 1, stage: "Watching", areas: ["Oncology", "Immunology"], lastUpdate: "Jun 18" },
  { id: "c-vrtx", name: "Vertex Pharmaceuticals", ticker: "VRTX", hq: "Boston, MA", score: 64, delta30: 3, stage: "Watching", areas: ["Hematology", "Nephrology"], lastUpdate: "Jun 17" },
  { id: "c-iona", name: "Ionis Pharmaceuticals", ticker: "IONS", hq: "Carlsbad, CA", score: 61, delta30: -1, stage: "Watching", areas: ["Cardiovascular", "Neurology"], lastUpdate: "Jun 16" },
];

export const PROGRAMS: Program[] = [
  { id: "p-hema", name: "Hemophilia A — next-gen prophylaxis", area: "Hematology", modality: "Bispecific antibody / gene therapy", phase: "Phase 2", description: "Long-acting prophylaxis for severe Hemophilia A with and without inhibitors, targeting monthly-or-longer dosing with non-Factor VIII mechanisms.", relatedSignals: 5, highPriority: 1 },
  { id: "p-hemb", name: "Hemophilia B — gene therapy partnership", area: "Hematology", modality: "AAV gene therapy", phase: "Phase 3", description: "Strategic interest in late-stage AAV-based Factor IX therapies; evaluating partnership and licensing pathways.", relatedSignals: 2, highPriority: 1 },
  { id: "p-ig", name: "Plasma-derived Ig — chronic indications", area: "Immunology", modality: "Plasma-derived therapy", phase: "Approved", description: "Lifecycle expansion into adjacent chronic immunodeficiency indications, with monitoring of subcutaneous and recombinant alternatives.", relatedSignals: 1, highPriority: 1 },
  { id: "p-neph", name: "Nephrology — IgA nephropathy & complement", area: "Nephrology", modality: "Complement inhibitor", phase: "Phase 2", description: "Complement-pathway modulation for IgAN and related glomerular diseases across C5/C3/Factor B targets.", relatedSignals: 3, highPriority: 0 },
  { id: "p-vacc", name: "Influenza vaccines — cell-based franchise", area: "Vaccines", modality: "Cell-based vaccine", phase: "Approved", description: "Defending and extending the cell-based influenza franchise against mRNA and recombinant entrants.", relatedSignals: 1, highPriority: 0 },
];

export const BRIEFS: Brief[] = [
  { id: "b-1", title: "Diligence — XYZ Biotech (Hemophilia A)", status: "In progress", author: "Sarah Reyes", type: "Company Diligence", updated: "Jun 26" },
  { id: "b-2", title: "Sangamo Therapeutics — Hemophilia partnership thesis", status: "In review", author: "Sarah Reyes", type: "Company Diligence", updated: "Jun 25" },
  { id: "b-3", title: "Roche — Immunology adjacency review", status: "Draft", author: "Sarah Reyes", type: "Company Diligence", updated: "Jun 26" },
  { id: "b-4", title: "Complement landscape — IgAN & C3G", status: "Approved", author: "M. Tran", type: "Indication Deep Dive", updated: "Jun 19" },
  { id: "b-5", title: "Non-Factor MoAs in Hemophilia A — competitive map", status: "Approved", author: "Sarah Reyes", type: "White Space Analysis", updated: "Jun 15" },
  { id: "b-6", title: "AAV durability — cross-program risk review", status: "Archived", author: "J. Okafor", type: "Custom Workflow", updated: "May 30" },
];

export const RESEARCH_TEMPLATES: ResearchTemplate[] = [
  { id: "t-asset", name: "Asset Diligence", description: "Deep evaluation of a single therapeutic asset: mechanism, evidence, IP, regulatory, and strategic fit.", sections: 8, duration: "24–48 hrs" },
  { id: "t-company", name: "Company Diligence", description: "Full company evaluation: pipeline, financials, IP, leadership, and partnership readiness.", sections: 8, duration: "24–48 hrs", recommended: true },
  { id: "t-compare", name: "Competitive Comparison", description: "Side-by-side analysis of 2–5 companies, assets, or trials across the dimensions that matter.", sections: 6, duration: "4–12 hrs" },
  { id: "t-whitespace", name: "White-Space Analysis", description: "Strategic exploration of uncontested opportunities in a therapeutic area.", sections: 7, duration: "24–48 hrs" },
  { id: "t-indication", name: "Indication Deep Dive", description: "Disease-area landscape: epidemiology, competitive map, unmet need, and mechanisms.", sections: 6, duration: "8–24 hrs" },
  { id: "t-custom", name: "Custom Workflow", description: "Define your own research scope and section structure from scratch.", sections: 0, duration: "Variable" },
];

export const ASK_SUGGESTIONS: { group: string; subtitle: string; items: string[] }[] = [
  { group: "Asset Intelligence", subtitle: "Drug & asset deep-dives", items: ["What do we know about emicizumab?", "Compare emicizumab and marstacimab", "What targets Factor VIII in the graph?"] },
  { group: "Company Intelligence", subtitle: "Partner & competitor profiles", items: ["What's new on Sangamo?", "Run a quick BD readout on Apellis", "How is Roche positioned in nephrology?"] },
  { group: "Indication Landscape", subtitle: "Disease-area competitive maps", items: ["Show me the IgA nephropathy competitive map", "Who leads non-Factor MoAs in Hemophilia A?", "Show me white space in nephrology"] },
];

export const priorityLabel: Record<Priority, string> = { high: "HIGH", med: "MED", watch: "WATCH" };
