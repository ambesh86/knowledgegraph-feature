// =============================================================================
// Eugene Knowledge Graph — CSL Behring portfolio enrichment
// =============================================================================
// Idempotent (MERGE-only).  Schema follows the existing PrimeKG-derived
// convention used elsewhere in the graph: lowercase + uppercase label
// pair, `node_index` (text), `node_id`, `node_name`, `node_source`.
//
// Sources (all public, May 2025):
//   - CSL Behring product portfolio:  https://www.cslbehring.com/products
//   - CSL Limited Annual Report FY2024 (Aug 2024 lodgement)
//   - FDA Orange Book / FDA approval letters
//   - EMA EPAR documents
//   - ClinicalTrials.gov (NCT registry)
//   - Andembry / garadacimab launch press releases (CSL, Jun 2024)
// =============================================================================

// -- Anchor canonical CSL Behring org and parent ------------------------------
MERGE (cslb:Organization { node_id: "6b1e0f62918e" })
  ON CREATE SET cslb.node_name = "CSL Behring",
                cslb.type      = "Organization",
                cslb.country   = "United States",
                cslb.hq        = "King of Prussia, Pennsylvania",
                cslb.parent    = "CSL Limited (ASX: CSL)",
                cslb.node_source = "CSL Behring corporate website 2025"
  ON MATCH  SET cslb.country   = coalesce(cslb.country, "United States"),
                cslb.hq        = coalesce(cslb.hq, "King of Prussia, Pennsylvania"),
                cslb.parent    = coalesce(cslb.parent, "CSL Limited (ASX: CSL)"),
                cslb.node_source = coalesce(cslb.node_source, "CSL Behring corporate website 2025");

MERGE (csl:Organization { node_id: "ed87a867a439" })
  ON CREATE SET csl.node_name = "CSL Limited",
                csl.type      = "Organization",
                csl.country   = "Australia",
                csl.hq        = "Melbourne, Victoria",
                csl.ticker    = "ASX: CSL",
                csl.node_source = "CSL Limited Annual Report FY2024"
  ON MATCH  SET csl.country   = coalesce(csl.country, "Australia"),
                csl.hq        = coalesce(csl.hq, "Melbourne, Victoria"),
                csl.ticker    = coalesce(csl.ticker, "ASX: CSL"),
                csl.node_source = coalesce(csl.node_source, "CSL Limited Annual Report FY2024");

// CSL Behring is the biotherapies subsidiary of CSL Limited
MERGE (cslb)-[:SUBSIDIARY_OF { since: 2004,
                                origin: "Acquired Aventis Behring 2004",
                                note: "Renamed CSL Behring 2007" }]->(csl);

// CSL Seqirus — vaccines subsidiary (already exists at b53820730ac9)
MATCH (sei:Organization { node_id: "b53820730ac9" })
SET sei.parent = "CSL Limited",
    sei.note   = "Influenza vaccine division (formed 2015 from BioCSL + bioCSL/Novartis Influenza Vaccines acquisition)",
    sei.node_source = coalesce(sei.node_source, "CSL Seqirus 2024 corporate factsheet");

MATCH (csl:Organization { node_id: "ed87a867a439" })
MATCH (sei:Organization { node_id: "b53820730ac9" })
MERGE (sei)-[:SUBSIDIARY_OF { since: 2015 }]->(csl);

// CSL Vifor — iron / nephrology division (acquired 2022)
MERGE (vifor:Organization { node_name: "CSL Vifor" })
  ON CREATE SET vifor.node_id    = "csl_org_vifor",
                vifor.type        = "Organization",
                vifor.country     = "Switzerland",
                vifor.hq          = "St. Gallen",
                vifor.acquired    = 2022,
                vifor.deal_size_usd = 11700000000,
                vifor.note        = "Acquired Aug 2022 for $11.7B; iron-deficiency, dialysis-related renal anaemia",
                vifor.node_source = "CSL Vifor acquisition press release Aug 2022";

MATCH (csl:Organization { node_id: "ed87a867a439" })
MATCH (vifor:Organization { node_name: "CSL Vifor" })
MERGE (vifor)-[:SUBSIDIARY_OF { since: 2022, deal_size_usd: 11700000000 }]->(csl);


// =============================================================================
// DISEASE NODES — CSL therapeutic areas (with proper MONDO / Orphanet IDs)
// =============================================================================
MERGE (haea:disease { node_name: "Hemophilia A" })
  ON CREATE SET haea:DISEASE,
                haea.node_id     = "34c734063e8e",
                haea.node_index  = "csl_dz_hema",
                haea.type        = "Disease",
                haea.mondo_id    = "0010602",
                haea.icd_code    = "D66",
                haea.orphanet_id = "98878",
                haea.synonyms    = ["Factor VIII deficiency","Classic hemophilia"],
                haea.node_source = "MONDO 2025-04, Orphanet";
MATCH (haea:disease { node_id: "34c734063e8e" })
SET haea:DISEASE,
    haea.mondo_id    = coalesce(haea.mondo_id, "0010602"),
    haea.icd_code    = coalesce(haea.icd_code, "D66"),
    haea.orphanet_id = coalesce(haea.orphanet_id, "98878");

MERGE (hemb:disease { node_name: "Hemophilia B" })
  ON CREATE SET hemb:DISEASE,
                hemb.node_id     = "b4d83e3aac5d",
                hemb.node_index  = "csl_dz_hemb",
                hemb.type        = "Disease",
                hemb.mondo_id    = "0010604",
                hemb.icd_code    = "D67",
                hemb.orphanet_id = "98879",
                hemb.synonyms    = ["Factor IX deficiency","Christmas disease"],
                hemb.node_source = "MONDO 2025-04, Orphanet";
MATCH (hemb:disease { node_id: "b4d83e3aac5d" })
SET hemb:DISEASE,
    hemb.mondo_id    = coalesce(hemb.mondo_id, "0010604"),
    hemb.icd_code    = coalesce(hemb.icd_code, "D67"),
    hemb.orphanet_id = coalesce(hemb.orphanet_id, "98879");

MERGE (vwd:disease { node_name: "Von Willebrand Disease" })
  ON CREATE SET vwd:DISEASE,
                vwd.node_id     = "51bc6dd54d0b",
                vwd.node_index  = "csl_dz_vwd",
                vwd.type        = "Disease",
                vwd.mondo_id    = "0015626",
                vwd.icd_code    = "D68.0",
                vwd.orphanet_id = "903",
                vwd.synonyms    = ["VWD","von Willebrand factor deficiency"],
                vwd.node_source = "MONDO 2025-04, Orphanet";
MATCH (vwd:disease { node_id: "51bc6dd54d0b" })
SET vwd:DISEASE,
    vwd.mondo_id    = coalesce(vwd.mondo_id, "0015626"),
    vwd.icd_code    = coalesce(vwd.icd_code, "D68.0"),
    vwd.orphanet_id = coalesce(vwd.orphanet_id, "903");

MERGE (hae:disease { node_name: "Hereditary Angioedema" })
  ON CREATE SET hae:DISEASE,
                hae.node_id     = "ca9cb8065bc5",
                hae.node_index  = "csl_dz_hae",
                hae.type        = "Disease",
                hae.mondo_id    = "0007243",
                hae.icd_code    = "D84.1",
                hae.orphanet_id = "91378",
                hae.synonyms    = ["HAE","C1 inhibitor deficiency"],
                hae.subtypes    = ["HAE Type I (low C1-INH)","HAE Type II (dysfunctional C1-INH)","HAE with normal C1-INH (HAE-nC1)"],
                hae.node_source = "MONDO 2025-04, Orphanet";
MATCH (hae:disease { node_id: "ca9cb8065bc5" })
SET hae:DISEASE,
    hae.mondo_id    = coalesce(hae.mondo_id, "0007243"),
    hae.icd_code    = coalesce(hae.icd_code, "D84.1"),
    hae.orphanet_id = coalesce(hae.orphanet_id, "91378");

MERGE (aatd:disease { node_name: "Alpha-1 Antitrypsin Deficiency" })
  ON CREATE SET aatd:DISEASE,
                aatd.node_id     = "csl_dz_aatd",
                aatd.node_index  = "csl_dz_aatd",
                aatd.type        = "Disease",
                aatd.mondo_id    = "0008318",
                aatd.icd_code    = "E88.01",
                aatd.orphanet_id = "60",
                aatd.synonyms    = ["AATD","AAT deficiency","SERPINA1 deficiency"],
                aatd.node_source = "MONDO 2025-04, Orphanet";

MERGE (pid:disease { node_name: "Primary Immunodeficiency" })
  ON CREATE SET pid:DISEASE,
                pid.node_id     = "csl_dz_pid",
                pid.node_index  = "csl_dz_pid",
                pid.type        = "Disease",
                pid.mondo_id    = "0021094",
                pid.icd_code    = "D80-D84",
                pid.synonyms    = ["PID","Inborn errors of immunity","Hypogammaglobulinemia"],
                pid.node_source = "MONDO 2025-04";

MERGE (cidp:disease { node_name: "Chronic Inflammatory Demyelinating Polyneuropathy" })
  ON CREATE SET cidp:DISEASE,
                cidp.node_id     = "csl_dz_cidp",
                cidp.node_index  = "csl_dz_cidp",
                cidp.type        = "Disease",
                cidp.mondo_id    = "0017846",
                cidp.icd_code    = "G61.81",
                cidp.synonyms    = ["CIDP"],
                cidp.node_source = "MONDO 2025-04";

MERGE (acs:disease { node_name: "Acute Coronary Syndrome" })
  ON CREATE SET acs:DISEASE,
                acs.node_id     = "csl_dz_acs",
                acs.node_index  = "csl_dz_acs",
                acs.type        = "Disease",
                acs.mondo_id    = "0001119",
                acs.icd_code    = "I24",
                acs.node_source = "MONDO 2025-04";

MERGE (idabd:disease { node_name: "Iron Deficiency Anaemia" })
  ON CREATE SET idabd:DISEASE,
                idabd.node_id     = "csl_dz_ida",
                idabd.node_index  = "csl_dz_ida",
                idabd.type        = "Disease",
                idabd.mondo_id    = "0001185",
                idabd.icd_code    = "D50",
                idabd.node_source = "MONDO 2025-04";


// =============================================================================
// PROTEIN TARGETS for CSL portfolio
// =============================================================================
MERGE (f8:gene_protein { node_name: "Coagulation Factor VIII" })
  ON CREATE SET f8:GENE_PROTEIN, f8.node_id = "csl_gp_f8", f8.node_index = "csl_gp_f8",
                f8.type = "GeneProtein", f8.symbol = "F8", f8.uniprot = "P00451",
                f8.node_source = "UniProt 2025-04";
MERGE (f9:gene_protein { node_name: "Coagulation Factor IX" })
  ON CREATE SET f9:GENE_PROTEIN, f9.node_id = "csl_gp_f9", f9.node_index = "csl_gp_f9",
                f9.type = "GeneProtein", f9.symbol = "F9", f9.uniprot = "P00740",
                f9.node_source = "UniProt 2025-04";
MERGE (vwf:gene_protein { node_name: "von Willebrand Factor" })
  ON CREATE SET vwf:GENE_PROTEIN, vwf.node_id = "csl_gp_vwf", vwf.node_index = "csl_gp_vwf",
                vwf.type = "GeneProtein", vwf.symbol = "VWF", vwf.uniprot = "P04275",
                vwf.node_source = "UniProt 2025-04";
MERGE (c1inh:gene_protein { node_name: "C1 Esterase Inhibitor" })
  ON CREATE SET c1inh:GENE_PROTEIN, c1inh.node_id = "csl_gp_c1inh", c1inh.node_index = "csl_gp_c1inh",
                c1inh.type = "GeneProtein", c1inh.symbol = "SERPING1", c1inh.uniprot = "P05155",
                c1inh.node_source = "UniProt 2025-04";
MERGE (kal:gene_protein { node_name: "Plasma Kallikrein" })
  ON CREATE SET kal:GENE_PROTEIN, kal.node_id = "csl_gp_kal", kal.node_index = "csl_gp_kal",
                kal.type = "GeneProtein", kal.symbol = "KLKB1", kal.uniprot = "P03952",
                kal.node_source = "UniProt 2025-04";
MERGE (f12a:gene_protein { node_name: "Coagulation Factor XIIa" })
  ON CREATE SET f12a:GENE_PROTEIN, f12a.node_id = "csl_gp_f12a", f12a.node_index = "csl_gp_f12a",
                f12a.type = "GeneProtein", f12a.symbol = "F12", f12a.uniprot = "P00748",
                f12a.note = "Activated form is the target of garadacimab (CSL312)",
                f12a.node_source = "UniProt 2025-04";
MERGE (aat:gene_protein { node_name: "Alpha-1 Antitrypsin" })
  ON CREATE SET aat:GENE_PROTEIN, aat.node_id = "csl_gp_aat", aat.node_index = "csl_gp_aat",
                aat.type = "GeneProtein", aat.symbol = "SERPINA1", aat.uniprot = "P01009",
                aat.node_source = "UniProt 2025-04";
MERGE (apoa1:gene_protein { node_name: "Apolipoprotein A-I" })
  ON CREATE SET apoa1:GENE_PROTEIN, apoa1.node_id = "csl_gp_apoa1", apoa1.node_index = "csl_gp_apoa1",
                apoa1.type = "GeneProtein", apoa1.symbol = "APOA1", apoa1.uniprot = "P02647",
                apoa1.node_source = "UniProt 2025-04";


// =============================================================================
// CSL BEHRING DRUGS (lowercase :drug:DRUG label per graph convention)
// =============================================================================
MERGE (idelvion:drug { node_name: "Idelvion" })
  ON CREATE SET idelvion:DRUG, idelvion.node_id = "csl_drug_idelvion", idelvion.node_index = "csl_drug_idelvion",
                idelvion.type = "Drug",
                idelvion.generic_name = "albutrepenonacog alfa",
                idelvion.modality = "recombinant fusion protein (rIX-FP)",
                idelvion.fda_approval_year = 2016,
                idelvion.indication_summary = "Hemophilia B (factor IX deficiency)",
                idelvion.atc_4 = "B02BD04",
                idelvion.node_source = "FDA Orange Book; CSL Behring product page 2025";

MERGE (afstyla:drug { node_name: "Afstyla" })
  ON CREATE SET afstyla:DRUG, afstyla.node_id = "csl_drug_afstyla", afstyla.node_index = "csl_drug_afstyla",
                afstyla.type = "Drug",
                afstyla.generic_name = "antihemophilic factor (recombinant), single chain",
                afstyla.modality = "recombinant Factor VIII (single-chain)",
                afstyla.fda_approval_year = 2016,
                afstyla.indication_summary = "Hemophilia A",
                afstyla.atc_4 = "B02BD02",
                afstyla.node_source = "FDA Orange Book";

MERGE (helixate:drug { node_name: "Helixate FS" })
  ON CREATE SET helixate:DRUG, helixate.node_id = "csl_drug_helixate", helixate.node_index = "csl_drug_helixate",
                helixate.type = "Drug",
                helixate.generic_name = "octocog alfa",
                helixate.modality = "recombinant Factor VIII",
                helixate.fda_approval_year = 2000,
                helixate.indication_summary = "Hemophilia A",
                helixate.atc_4 = "B02BD02",
                helixate.notes = "Discontinued in some markets; manufactured under license from Bayer.",
                helixate.node_source = "FDA Orange Book";

MERGE (mononine:drug { node_name: "Mononine" })
  ON CREATE SET mononine:DRUG, mononine.node_id = "csl_drug_mononine", mononine.node_index = "csl_drug_mononine",
                mononine.type = "Drug",
                mononine.generic_name = "factor IX (human, plasma-derived, monoclonal-purified)",
                mononine.modality = "plasma-derived FIX",
                mononine.fda_approval_year = 1992,
                mononine.indication_summary = "Hemophilia B",
                mononine.atc_4 = "B02BD04",
                mononine.node_source = "FDA Orange Book";

MERGE (humate:drug { node_name: "Humate-P" })
  ON CREATE SET humate:DRUG, humate.node_id = "csl_drug_humate", humate.node_index = "csl_drug_humate",
                humate.type = "Drug",
                humate.generic_name = "antihemophilic factor / von Willebrand factor complex (human)",
                humate.modality = "plasma-derived VWF/FVIII",
                humate.fda_approval_year = 1986,
                humate.indication_summary = "von Willebrand Disease; severe Hemophilia A",
                humate.atc_4 = "B02BD06",
                humate.node_source = "FDA Orange Book";

MERGE (vonvendi:drug { node_name: "Vonvendi" })
  ON CREATE SET vonvendi:DRUG, vonvendi.node_id = "csl_drug_vonvendi", vonvendi.node_index = "csl_drug_vonvendi",
                vonvendi.type = "Drug",
                vonvendi.generic_name = "vonicog alfa",
                vonvendi.modality = "recombinant von Willebrand factor",
                vonvendi.fda_approval_year = 2015,
                vonvendi.indication_summary = "von Willebrand Disease (treatment of bleeding events; perioperative)",
                vonvendi.note = "Marketed by Takeda US; CSL competes via Humate-P",
                vonvendi.node_source = "FDA Orange Book — competitor reference";

MERGE (berinert:drug { node_name: "Berinert" })
  ON CREATE SET berinert:DRUG, berinert.node_id = "csl_drug_berinert", berinert.node_index = "csl_drug_berinert",
                berinert.type = "Drug",
                berinert.generic_name = "C1 esterase inhibitor (human)",
                berinert.modality = "plasma-derived C1-INH (IV)",
                berinert.fda_approval_year = 2009,
                berinert.indication_summary = "Acute treatment of HAE attacks (laryngeal, abdominal, facial)",
                berinert.atc_4 = "B06AC01",
                berinert.node_source = "FDA Orange Book; EMA EPAR";

MERGE (haegarda:drug { node_name: "Haegarda" })
  ON CREATE SET haegarda:DRUG, haegarda.node_id = "03a2b41a2411", haegarda.node_index = "csl_drug_haegarda",
                haegarda.type = "Drug",
                haegarda.generic_name = "C1 esterase inhibitor (human, subcutaneous)",
                haegarda.modality = "plasma-derived C1-INH (SC, prophylaxis)",
                haegarda.fda_approval_year = 2017,
                haegarda.indication_summary = "Routine prophylaxis to prevent HAE attacks (≥6 yo)",
                haegarda.atc_4 = "B06AC01",
                haegarda.node_source = "FDA Orange Book";
MATCH (h:drug { node_id: "03a2b41a2411" })
SET h:DRUG, h.generic_name = coalesce(h.generic_name, "C1 esterase inhibitor (human, subcutaneous)"),
    h.modality = coalesce(h.modality, "plasma-derived C1-INH (SC)"),
    h.fda_approval_year = coalesce(h.fda_approval_year, 2017),
    h.node_source = coalesce(h.node_source, "FDA Orange Book");

MERGE (andembry:drug { node_name: "Andembry" })
  ON CREATE SET andembry:DRUG, andembry.node_id = "csl_drug_andembry", andembry.node_index = "csl_drug_andembry",
                andembry.type = "Drug",
                andembry.generic_name = "garadacimab",
                andembry.modality = "monoclonal antibody (anti-FXIIa)",
                andembry.fda_approval_year = 2025,
                andembry.indication_summary = "Long-term prophylaxis of HAE (≥12 yo)",
                andembry.note = "First-in-class anti-FXIIa mAb; once-monthly subcutaneous; CSL312",
                andembry.first_approval = "Australia TGA Feb 2024; EMA Apr 2024; FDA Jun 2025",
                andembry.node_source = "CSL Behring press release Jun 2025; FDA approval letter";

MERGE (privigen:drug { node_name: "Privigen" })
  ON CREATE SET privigen:DRUG, privigen.node_id = "csl_drug_privigen", privigen.node_index = "csl_drug_privigen",
                privigen.type = "Drug",
                privigen.generic_name = "immune globulin intravenous (human), 10% liquid",
                privigen.modality = "plasma-derived IVIG",
                privigen.fda_approval_year = 2007,
                privigen.indication_summary = "Primary immunodeficiency, chronic ITP, CIDP",
                privigen.atc_4 = "J06BA02",
                privigen.node_source = "FDA Orange Book";

MERGE (hizentra:drug { node_name: "Hizentra" })
  ON CREATE SET hizentra:DRUG, hizentra.node_id = "csl_drug_hizentra", hizentra.node_index = "csl_drug_hizentra",
                hizentra.type = "Drug",
                hizentra.generic_name = "immune globulin subcutaneous (human), 20% liquid",
                hizentra.modality = "plasma-derived SCIG",
                hizentra.fda_approval_year = 2010,
                hizentra.indication_summary = "Primary immunodeficiency; CIDP maintenance",
                hizentra.atc_4 = "J06BA01",
                hizentra.node_source = "FDA Orange Book";

MERGE (zemaira:drug { node_name: "Zemaira" })
  ON CREATE SET zemaira:DRUG, zemaira.node_id = "csl_drug_zemaira", zemaira.node_index = "csl_drug_zemaira",
                zemaira.type = "Drug",
                zemaira.generic_name = "alpha-1 proteinase inhibitor (human)",
                zemaira.modality = "plasma-derived alpha-1 antitrypsin",
                zemaira.fda_approval_year = 2003,
                zemaira.indication_summary = "Chronic augmentation for emphysema in adults with AAT deficiency",
                zemaira.atc_4 = "B02AB02",
                zemaira.node_source = "FDA Orange Book";

MERGE (kcentra:drug { node_name: "Kcentra" })
  ON CREATE SET kcentra:DRUG, kcentra.node_id = "csl_drug_kcentra", kcentra.node_index = "csl_drug_kcentra",
                kcentra.type = "Drug",
                kcentra.generic_name = "prothrombin complex concentrate (human, 4-factor)",
                kcentra.modality = "plasma-derived 4F-PCC",
                kcentra.fda_approval_year = 2013,
                kcentra.indication_summary = "Urgent reversal of vitamin K antagonist (warfarin) anticoagulation",
                kcentra.atc_4 = "B02BD01",
                kcentra.node_source = "FDA Orange Book";

MERGE (hemgenix:drug { node_name: "Hemgenix" })
  ON CREATE SET hemgenix:DRUG, hemgenix.node_id = "csl_drug_hemgenix", hemgenix.node_index = "csl_drug_hemgenix",
                hemgenix.type = "Drug",
                hemgenix.generic_name = "etranacogene dezaparvovec",
                hemgenix.modality = "AAV5 gene therapy (one-time IV infusion)",
                hemgenix.fda_approval_year = 2022,
                hemgenix.indication_summary = "Hemophilia B (adults; one-time gene therapy)",
                hemgenix.list_price_usd = 3500000,
                hemgenix.note = "First gene therapy for Hemophilia B; co-developed with uniQure",
                hemgenix.node_source = "FDA approval letter Nov 2022; CSL press release";

MERGE (csl112:drug { node_name: "CSL112" })
  ON CREATE SET csl112:DRUG, csl112.node_id = "csl_drug_csl112", csl112.node_index = "csl_drug_csl112",
                csl112.type = "Drug",
                csl112.generic_name = "apolipoprotein A-I (human, plasma-derived)",
                csl112.modality = "reconstituted HDL infusion",
                csl112.fda_approval_year = NULL,
                csl112.development_stage = "Phase 3 (AEGIS-II readout 2024 — primary endpoint missed)",
                csl112.indication_summary = "Reduction of recurrent CV events post-myocardial infarction",
                csl112.note = "AEGIS-II Phase 3 (NCT03473223) failed to meet primary endpoint Feb 2024; programme under strategic review",
                csl112.node_source = "CSL ASX announcement Feb 2024; AEGIS-II results";

MERGE (sebetra:drug { node_name: "Sebetralstat" })
  ON CREATE SET sebetra:DRUG, sebetra.node_id = "csl_drug_sebetralstat_ref", sebetra.node_index = "csl_drug_sebetralstat_ref",
                sebetra.type = "Drug",
                sebetra.generic_name = "sebetralstat",
                sebetra.modality = "small molecule plasma kallikrein inhibitor (oral)",
                sebetra.fda_approval_year = 2025,
                sebetra.indication_summary = "On-demand treatment of HAE attacks (≥12 yo) — first oral on-demand HAE therapy",
                sebetra.brand_name = "Ekterly",
                sebetra.developer = "KalVista Pharmaceuticals",
                sebetra.note = "Competitive reference — FDA approval Jul 2025",
                sebetra.node_source = "FDA approval letter Jul 2025";


// =============================================================================
// CSL → DRUG ownership / sponsorship
// =============================================================================
MATCH (cslb:Organization { node_id: "6b1e0f62918e" })
MATCH (d:drug)
WHERE d.node_id IN [
  "csl_drug_idelvion","csl_drug_afstyla","csl_drug_helixate",
  "csl_drug_mononine","csl_drug_humate",
  "csl_drug_berinert","03a2b41a2411","csl_drug_andembry",
  "csl_drug_privigen","csl_drug_hizentra",
  "csl_drug_zemaira","csl_drug_kcentra",
  "csl_drug_hemgenix"
]
MERGE (cslb)-[:OWNS_PATENT_ON { source: "CSL Behring product portfolio 2025" }]->(d)
MERGE (cslb)-[:SPONSORS { kind: "marketing_authorisation_holder" }]->(d);

// CSL Limited owns CSL112 (research-stage, parent-level programme)
MATCH (csl:Organization { node_id: "ed87a867a439" })
MATCH (d:drug { node_id: "csl_drug_csl112" })
MERGE (csl)-[:SPONSORS { kind: "investigational_sponsor" }]->(d);


// =============================================================================
// DRUG → DISEASE indications
// =============================================================================
// Hemophilia A
MATCH (d:drug),(z:disease { node_id: "34c734063e8e" })
WHERE d.node_id IN ["csl_drug_afstyla","csl_drug_helixate","csl_drug_humate"]
MERGE (d)-[:indication { source: "FDA label" }]->(z);

// Hemophilia B
MATCH (d:drug),(z:disease { node_id: "b4d83e3aac5d" })
WHERE d.node_id IN ["csl_drug_idelvion","csl_drug_mononine","csl_drug_hemgenix"]
MERGE (d)-[:indication { source: "FDA label" }]->(z);

// Von Willebrand Disease
MATCH (d:drug),(z:disease { node_id: "51bc6dd54d0b" })
WHERE d.node_id IN ["csl_drug_humate"]
MERGE (d)-[:indication { source: "FDA label" }]->(z);

// HAE
MATCH (d:drug),(z:disease { node_id: "ca9cb8065bc5" })
WHERE d.node_id IN ["csl_drug_berinert","03a2b41a2411","csl_drug_andembry","csl_drug_sebetralstat_ref"]
MERGE (d)-[:indication { source: "FDA label / EMA EPAR" }]->(z);

// AAT deficiency
MATCH (d:drug { node_id: "csl_drug_zemaira" }),(z:disease { node_id: "csl_dz_aatd" })
MERGE (d)-[:indication { source: "FDA label" }]->(z);

// PID + CIDP
MATCH (d:drug),(z:disease { node_id: "csl_dz_pid" })
WHERE d.node_id IN ["csl_drug_privigen","csl_drug_hizentra"]
MERGE (d)-[:indication { source: "FDA label" }]->(z);
MATCH (d:drug),(z:disease { node_id: "csl_dz_cidp" })
WHERE d.node_id IN ["csl_drug_privigen","csl_drug_hizentra"]
MERGE (d)-[:indication { source: "FDA label" }]->(z);

// Acute coronary syndrome (CSL112 investigational)
MATCH (d:drug { node_id: "csl_drug_csl112" }),(z:disease { node_id: "csl_dz_acs" })
MERGE (d)-[:indication { source: "AEGIS-II Phase 3 — primary endpoint missed Feb 2024",
                          status: "investigational" }]->(z);


// =============================================================================
// DRUG → PROTEIN target relationships (drug_protein)
// =============================================================================
MATCH (d:drug { node_id: "csl_drug_afstyla" }),    (p:gene_protein { node_id: "csl_gp_f8" })
MERGE (d)-[:drug_protein { mechanism: "FVIII replacement (recombinant single-chain)" }]->(p);
MATCH (d:drug { node_id: "csl_drug_helixate" }),   (p:gene_protein { node_id: "csl_gp_f8" })
MERGE (d)-[:drug_protein { mechanism: "FVIII replacement (recombinant)" }]->(p);
MATCH (d:drug { node_id: "csl_drug_humate" }),     (p:gene_protein { node_id: "csl_gp_f8" })
MERGE (d)-[:drug_protein { mechanism: "FVIII replacement (plasma-derived complex with VWF)" }]->(p);
MATCH (d:drug { node_id: "csl_drug_humate" }),     (p:gene_protein { node_id: "csl_gp_vwf" })
MERGE (d)-[:drug_protein { mechanism: "VWF replacement (plasma-derived complex)" }]->(p);
MATCH (d:drug { node_id: "csl_drug_idelvion" }),   (p:gene_protein { node_id: "csl_gp_f9" })
MERGE (d)-[:drug_protein { mechanism: "FIX replacement (recombinant FIX-albumin fusion)" }]->(p);
MATCH (d:drug { node_id: "csl_drug_mononine" }),   (p:gene_protein { node_id: "csl_gp_f9" })
MERGE (d)-[:drug_protein { mechanism: "FIX replacement (plasma-derived)" }]->(p);
MATCH (d:drug { node_id: "csl_drug_hemgenix" }),   (p:gene_protein { node_id: "csl_gp_f9" })
MERGE (d)-[:drug_protein { mechanism: "AAV5 delivery of FIX-Padua transgene; restores FIX activity" }]->(p);
MATCH (d:drug { node_id: "csl_drug_berinert" }),   (p:gene_protein { node_id: "csl_gp_c1inh" })
MERGE (d)-[:drug_protein { mechanism: "C1-INH replacement (plasma-derived IV)" }]->(p);
MATCH (d:drug { node_id: "03a2b41a2411" }),        (p:gene_protein { node_id: "csl_gp_c1inh" })
MERGE (d)-[:drug_protein { mechanism: "C1-INH replacement (plasma-derived SC, prophylaxis)" }]->(p);
MATCH (d:drug { node_id: "csl_drug_andembry" }),   (p:gene_protein { node_id: "csl_gp_f12a" })
MERGE (d)-[:drug_protein { mechanism: "Anti-activated factor XII (FXIIa) mAb; blocks contact-system activation" }]->(p);
MATCH (d:drug { node_id: "csl_drug_sebetralstat_ref" }), (p:gene_protein { node_id: "csl_gp_kal" })
MERGE (d)-[:drug_protein { mechanism: "Selective oral plasma kallikrein inhibitor" }]->(p);
MATCH (d:drug { node_id: "csl_drug_zemaira" }),    (p:gene_protein { node_id: "csl_gp_aat" })
MERGE (d)-[:drug_protein { mechanism: "AAT replacement (plasma-derived)" }]->(p);
MATCH (d:drug { node_id: "csl_drug_csl112" }),     (p:gene_protein { node_id: "csl_gp_apoa1" })
MERGE (d)-[:drug_protein { mechanism: "Reconstituted HDL; promotes cholesterol efflux from atherosclerotic plaques" }]->(p);


// =============================================================================
// DRUG ALIASES
// =============================================================================
UNWIND [
  ["csl_drug_idelvion","albutrepenonacog alfa"],
  ["csl_drug_idelvion","rIX-FP"],
  ["csl_drug_idelvion","CSL654"],
  ["csl_drug_afstyla","lonoctocog alfa"],
  ["csl_drug_afstyla","CSL627"],
  ["csl_drug_andembry","garadacimab"],
  ["csl_drug_andembry","CSL312"],
  ["csl_drug_hemgenix","etranacogene dezaparvovec"],
  ["csl_drug_hemgenix","AMT-061"],
  ["csl_drug_hemgenix","Etrana"],
  ["csl_drug_csl112","apolipoprotein A-I (human)"],
  ["csl_drug_sebetralstat_ref","Ekterly"],
  ["csl_drug_sebetralstat_ref","KVD900"]
] AS pair
MATCH (d:drug { node_id: pair[0] })
MERGE (d)-[:has_drug_alias { alias: pair[1] }]->(d);


// =============================================================================
// PIVOTAL CLINICAL TRIALS — CSL portfolio
// =============================================================================
UNWIND [
  ["csl_trial_phoenix","NCT03936660","VANGUARD","Phase 3","Garadacimab in HAE prophylaxis","csl_drug_andembry","ca9cb8065bc5"],
  ["csl_trial_compact","NCT01912521","COMPACT","Phase 3","Subcutaneous C1-INH (Haegarda) prophylaxis in HAE","03a2b41a2411","ca9cb8065bc5"],
  ["csl_trial_hopebcl","NCT03489291","HOPE-B","Phase 3","Etranacogene dezaparvovec gene therapy in Hemophilia B","csl_drug_hemgenix","b4d83e3aac5d"],
  ["csl_trial_paradigm","NCT01512147","PROLONG-9FP","Phase 3","Idelvion in Hemophilia B","csl_drug_idelvion","b4d83e3aac5d"],
  ["csl_trial_paths","NCT01486784","AFFINITY","Phase 3","Afstyla in Hemophilia A","csl_drug_afstyla","34c734063e8e"],
  ["csl_trial_aegisii","NCT03473223","AEGIS-II","Phase 3","CSL112 in post-MI cardiovascular risk reduction","csl_drug_csl112","csl_dz_acs"]
] AS t
MATCH (drug:drug { node_id: t[5] })
MATCH (dz:disease { node_id: t[6] })
MERGE (trial:ClinicalTrial { node_id: t[0] })
  ON CREATE SET trial.nct_id    = t[1],
                trial.node_name = t[2],
                trial.phase     = t[3],
                trial.title     = t[4],
                trial.type      = "ClinicalTrial",
                trial.node_source = "ClinicalTrials.gov 2025-04"
MERGE (trial)-[:evaluated_in { kind: "primary investigational drug" }]->(drug)
MERGE (trial)-[:featured_in  { reason: "indication under study" }]->(dz);

// CSL is sponsor for its own trials
MATCH (trial:ClinicalTrial)
WHERE trial.node_id IN ["csl_trial_phoenix","csl_trial_compact","csl_trial_hopebcl",
                         "csl_trial_paradigm","csl_trial_paths","csl_trial_aegisii"]
MATCH (cslb:Organization { node_id: "6b1e0f62918e" })
MERGE (cslb)-[:SPONSORS { role: "sponsor" }]->(trial);


// =============================================================================
// COMPETITORS in hemophilia / HAE space (anchor nodes for cross-org analysis)
// =============================================================================
MERGE (takeda:Organization { node_id: "42ce2f91530a" })
  ON MATCH SET takeda.node_source = coalesce(takeda.node_source, "Takeda Annual Report FY2024");
MERGE (novo:Organization { node_id: "027a14a695fd" })
  ON MATCH SET novo.node_source  = coalesce(novo.node_source, "Novo Nordisk Annual Report 2024");

MERGE (kalvista:Organization { node_name: "KalVista Pharmaceuticals" })
  ON CREATE SET kalvista.node_id = "csl_org_kalvista", kalvista.type = "Organization",
                kalvista.country = "United States", kalvista.ticker = "KALV",
                kalvista.note = "First-in-class oral HAE therapy (sebetralstat / Ekterly)",
                kalvista.node_source = "KalVista press release 2025";
MERGE (pharvaris:Organization { node_name: "Pharvaris" })
  ON CREATE SET pharvaris.node_id = "csl_org_pharvaris", pharvaris.type = "Organization",
                pharvaris.country = "Netherlands", pharvaris.ticker = "PHVS",
                pharvaris.note = "Oral bradykinin B2 receptor antagonist (deucrictibant) for HAE — Phase 3",
                pharvaris.node_source = "Pharvaris press release 2025";
MERGE (biomarin:Organization { node_name: "BioMarin Pharmaceutical" })
  ON CREATE SET biomarin.node_id = "csl_org_biomarin", biomarin.type = "Organization",
                biomarin.country = "United States", biomarin.ticker = "BMRN",
                biomarin.note = "Roctavian (valoctocogene roxaparvovec) — Hemophilia A gene therapy",
                biomarin.node_source = "BioMarin Annual Report 2024";

// Competitive drugs (referenced for competitive intelligence queries)
MERGE (roctavian:drug { node_name: "Roctavian" })
  ON CREATE SET roctavian:DRUG, roctavian.node_id = "csl_drug_roctavian", roctavian.node_index = "csl_drug_roctavian",
                roctavian.type = "Drug",
                roctavian.generic_name = "valoctocogene roxaparvovec",
                roctavian.modality = "AAV5 gene therapy (Hemophilia A)",
                roctavian.fda_approval_year = 2023,
                roctavian.indication_summary = "Hemophilia A gene therapy",
                roctavian.developer = "BioMarin Pharmaceutical",
                roctavian.list_price_usd = 2900000,
                roctavian.node_source = "FDA approval letter Jun 2023";

MERGE (takhzyro:drug { node_name: "Takhzyro" })
  ON CREATE SET takhzyro:DRUG, takhzyro.node_id = "csl_drug_takhzyro", takhzyro.node_index = "csl_drug_takhzyro",
                takhzyro.type = "Drug",
                takhzyro.generic_name = "lanadelumab",
                takhzyro.modality = "monoclonal antibody (anti-plasma kallikrein)",
                takhzyro.fda_approval_year = 2018,
                takhzyro.indication_summary = "HAE long-term prophylaxis",
                takhzyro.developer = "Takeda",
                takhzyro.atc_4 = "B06AC02",
                takhzyro.node_source = "FDA Orange Book";

MERGE (orladeyo:drug { node_name: "Orladeyo" })
  ON CREATE SET orladeyo:DRUG, orladeyo.node_id = "csl_drug_orladeyo", orladeyo.node_index = "csl_drug_orladeyo",
                orladeyo.type = "Drug",
                orladeyo.generic_name = "berotralstat",
                orladeyo.modality = "small molecule oral plasma kallikrein inhibitor",
                orladeyo.fda_approval_year = 2020,
                orladeyo.indication_summary = "HAE long-term prophylaxis (oral)",
                orladeyo.developer = "BioCryst Pharmaceuticals",
                orladeyo.atc_4 = "B06AC03",
                orladeyo.node_source = "FDA Orange Book";

MERGE (alhemo:drug { node_name: "Alhemo" })
  ON CREATE SET alhemo:DRUG, alhemo.node_id = "csl_drug_alhemo", alhemo.node_index = "csl_drug_alhemo",
                alhemo.type = "Drug",
                alhemo.generic_name = "concizumab",
                alhemo.modality = "monoclonal antibody (anti-TFPI)",
                alhemo.fda_approval_year = 2024,
                alhemo.indication_summary = "Hemophilia A and B with inhibitors (subcutaneous prophylaxis)",
                alhemo.developer = "Novo Nordisk",
                alhemo.node_source = "FDA approval letter Dec 2024";

MERGE (hympavzi:drug { node_name: "Hympavzi" })
  ON CREATE SET hympavzi:DRUG, hympavzi.node_id = "csl_drug_hympavzi", hympavzi.node_index = "csl_drug_hympavzi",
                hympavzi.type = "Drug",
                hympavzi.generic_name = "marstacimab",
                hympavzi.modality = "monoclonal antibody (anti-TFPI)",
                hympavzi.fda_approval_year = 2024,
                hympavzi.indication_summary = "Hemophilia A and B without inhibitors (SC prophylaxis)",
                hympavzi.developer = "Pfizer",
                hympavzi.node_source = "FDA approval letter Oct 2024";

MERGE (qfitlia:drug { node_name: "Qfitlia" })
  ON CREATE SET qfitlia:DRUG, qfitlia.node_id = "csl_drug_qfitlia", qfitlia.node_index = "csl_drug_qfitlia",
                qfitlia.type = "Drug",
                qfitlia.generic_name = "fitusiran",
                qfitlia.modality = "siRNA targeting antithrombin",
                qfitlia.fda_approval_year = 2025,
                qfitlia.indication_summary = "Hemophilia A and B (with or without inhibitors); SC prophylaxis",
                qfitlia.developer = "Sanofi (acquired from Alnylam programme)",
                qfitlia.node_source = "FDA approval letter Mar 2025";

// Link competitors to their drugs
MATCH (b:Organization { node_id: "csl_org_biomarin" }), (d:drug { node_id: "csl_drug_roctavian" })
MERGE (b)-[:OWNS_PATENT_ON {}]->(d) MERGE (b)-[:SPONSORS {}]->(d);
MATCH (t:Organization { node_id: "42ce2f91530a" }),     (d:drug { node_id: "csl_drug_takhzyro" })
MERGE (t)-[:OWNS_PATENT_ON {}]->(d) MERGE (t)-[:SPONSORS {}]->(d);
MATCH (n:Organization { node_id: "027a14a695fd" }),     (d:drug { node_id: "csl_drug_alhemo" })
MERGE (n)-[:OWNS_PATENT_ON {}]->(d) MERGE (n)-[:SPONSORS {}]->(d);
MATCH (k:Organization { node_id: "csl_org_kalvista" }), (d:drug { node_id: "csl_drug_sebetralstat_ref" })
MERGE (k)-[:OWNS_PATENT_ON {}]->(d) MERGE (k)-[:SPONSORS {}]->(d);

// Competitor-drug indications + targets
MATCH (d:drug { node_id: "csl_drug_roctavian" }), (z:disease { node_id: "34c734063e8e" })
MERGE (d)-[:indication { source: "FDA label Jun 2023" }]->(z);
MATCH (d:drug { node_id: "csl_drug_roctavian" }), (p:gene_protein { node_id: "csl_gp_f8" })
MERGE (d)-[:drug_protein { mechanism: "AAV5 delivery of B-domain-deleted FVIII transgene" }]->(p);

MATCH (d:drug { node_id: "csl_drug_takhzyro" }), (z:disease { node_id: "ca9cb8065bc5" })
MERGE (d)-[:indication { source: "FDA label Aug 2018" }]->(z);
MATCH (d:drug { node_id: "csl_drug_takhzyro" }), (p:gene_protein { node_id: "csl_gp_kal" })
MERGE (d)-[:drug_protein { mechanism: "Selective monoclonal antibody inhibitor of plasma kallikrein" }]->(p);

MATCH (d:drug { node_id: "csl_drug_orladeyo" }), (z:disease { node_id: "ca9cb8065bc5" })
MERGE (d)-[:indication { source: "FDA label Dec 2020" }]->(z);
MATCH (d:drug { node_id: "csl_drug_orladeyo" }), (p:gene_protein { node_id: "csl_gp_kal" })
MERGE (d)-[:drug_protein { mechanism: "Oral selective plasma kallikrein inhibitor" }]->(p);

MATCH (d:drug { node_id: "csl_drug_alhemo" }), (z:disease { node_id: "34c734063e8e" })
MERGE (d)-[:indication { source: "FDA label Dec 2024" }]->(z);
MATCH (d:drug { node_id: "csl_drug_alhemo" }), (z:disease { node_id: "b4d83e3aac5d" })
MERGE (d)-[:indication { source: "FDA label Dec 2024" }]->(z);

MATCH (d:drug { node_id: "csl_drug_hympavzi" }), (z:disease { node_id: "34c734063e8e" })
MERGE (d)-[:indication { source: "FDA label Oct 2024" }]->(z);
MATCH (d:drug { node_id: "csl_drug_hympavzi" }), (z:disease { node_id: "b4d83e3aac5d" })
MERGE (d)-[:indication { source: "FDA label Oct 2024" }]->(z);

MATCH (d:drug { node_id: "csl_drug_qfitlia" }), (z:disease { node_id: "34c734063e8e" })
MERGE (d)-[:indication { source: "FDA label Mar 2025" }]->(z);
MATCH (d:drug { node_id: "csl_drug_qfitlia" }), (z:disease { node_id: "b4d83e3aac5d" })
MERGE (d)-[:indication { source: "FDA label Mar 2025" }]->(z);


// =============================================================================
// Done.  Verify with:
//   MATCH (cslb:Organization { node_id: "6b1e0f62918e" })-[r]-(n)
//   RETURN type(r) AS rel, labels(n)[0] AS lbl, count(*) AS c ORDER BY c DESC;
// =============================================================================
