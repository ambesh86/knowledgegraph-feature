// =============================================================================
// Eugene Knowledge Graph — Biogen asset enrichment
// =============================================================================
// Idempotent (MERGE-only). Re-running has no side effects.
// Source: Biogen 10-K FY2024, Eisai/Sage/argenx public press releases,
// FDA Orange Book, ClinicalTrials.gov.  Stable as of May 2025.
//
// Usage from host:
//   docker exec -i eugene-neo4j \
//     cypher-shell -u neo4j -p eugene_local_2024 -d neo4j \
//     < bin/seed/biogen_assets.cypher
// =============================================================================

// -- Anchor: canonical Biogen Inc node already in the graph --------------------
MERGE (biogen:Organization { node_id: "f608437b7867" })
  ON CREATE SET biogen.node_name = "Biogen Inc",
                biogen.type      = "Organization",
                biogen.country   = "United States",
                biogen.hq        = "Cambridge, Massachusetts",
                biogen.ticker    = "BIIB"
  ON MATCH  SET biogen.country   = coalesce(biogen.country, "United States"),
                biogen.hq        = coalesce(biogen.hq, "Cambridge, Massachusetts"),
                biogen.ticker    = coalesce(biogen.ticker, "BIIB");

// -- Strategic partners / acquired entities ----------------------------------
MERGE (eisai:Organization { node_name: "Eisai Co Ltd" })
  ON CREATE SET eisai.node_id = "biogen_eisai_001", eisai.type = "Organization",
                eisai.country = "Japan", eisai.ticker = "ESALY";
MERGE (sage:Organization { node_name: "Sage Therapeutics" })
  ON CREATE SET sage.node_id = "biogen_sage_001", sage.type = "Organization",
                sage.country = "United States", sage.ticker = "SAGE";
MERGE (reata:Organization { node_name: "Reata Pharmaceuticals" })
  ON CREATE SET reata.node_id = "biogen_reata_001", reata.type = "Organization",
                reata.country = "United States",
                reata.notes   = "Acquired by Biogen in September 2023 for $7.3B.";
MERGE (ionis:Organization { node_name: "Ionis Pharmaceuticals" })
  ON CREATE SET ionis.node_id = "biogen_ionis_001", ionis.type = "Organization",
                ionis.country = "United States", ionis.ticker = "IONS";

MERGE (biogen)-[:AFFILIATED_WITH { role: "co-develop / co-commercialise",
                                    asset: "lecanemab (Leqembi)" }]->(eisai)
MERGE (biogen)-[:AFFILIATED_WITH { role: "co-develop",
                                    asset: "zuranolone (Zurzuvae)" }]->(sage)
MERGE (biogen)-[:SUBSIDIARY_OF { acquired: 2023, deal_size_usd: 7300000000 }]->(reata)
MERGE (biogen)-[:AFFILIATED_WITH { role: "antisense / co-develop",
                                    asset: "nusinersen (Spinraza), tofersen (Qalsody)" }]->(ionis);

// -- Disease nodes -----------------------------------------------------------
MERGE (ms:Disease { node_name: "Multiple Sclerosis" })
  ON CREATE SET ms.node_id = "biogen_dz_ms",
                ms.icd_code = "G35",
                ms.mesh_id  = "D009103",
                ms.type     = "Disease",
                ms.synonyms = ["MS","disseminated sclerosis","encephalomyelitis disseminata"];
MERGE (rrms:Disease { node_name: "Relapsing-Remitting Multiple Sclerosis" })
  ON CREATE SET rrms.node_id = "biogen_dz_rrms", rrms.type = "Disease",
                rrms.synonyms = ["RRMS"];
MERGE (sma:Disease { node_name: "Spinal Muscular Atrophy" })
  ON CREATE SET sma.node_id = "biogen_dz_sma",
                sma.icd_code = "G12.0", sma.type = "Disease",
                sma.synonyms = ["SMA","Werdnig-Hoffmann disease"];
MERGE (alz:Disease { node_name: "Alzheimer's Disease" })
  ON CREATE SET alz.node_id = "biogen_dz_alz",
                alz.icd_code = "G30", alz.mesh_id = "D000544", alz.type = "Disease",
                alz.synonyms = ["AD","early-stage Alzheimer's","mild cognitive impairment"];
MERGE (als:Disease { node_name: "Amyotrophic Lateral Sclerosis" })
  ON CREATE SET als.node_id = "biogen_dz_als",
                als.icd_code = "G12.21", als.type = "Disease",
                als.synonyms = ["ALS","Lou Gehrig's disease","motor neuron disease"];
MERGE (sod1als:Disease { node_name: "SOD1 ALS" })
  ON CREATE SET sod1als.node_id = "biogen_dz_sod1als", sod1als.type = "Disease",
                sod1als.notes = "Subset of ALS driven by SOD1 gene mutation.";
MERGE (frda:Disease { node_name: "Friedreich's Ataxia" })
  ON CREATE SET frda.node_id = "biogen_dz_frda",
                frda.icd_code = "G11.11", frda.type = "Disease",
                frda.synonyms = ["FRDA"];
MERGE (ppd:Disease { node_name: "Postpartum Depression" })
  ON CREATE SET ppd.node_id = "biogen_dz_ppd",
                ppd.icd_code = "F53.0", ppd.type = "Disease",
                ppd.synonyms = ["PPD"];
MERGE (crohn:Disease { node_name: "Crohn's Disease" })
  ON CREATE SET crohn.node_id = "biogen_dz_crohn",
                crohn.icd_code = "K50", crohn.type = "Disease";
MERGE (ms)-[:disease_disease { type: "subtype" }]->(rrms);
MERGE (als)-[:disease_disease { type: "subtype" }]->(sod1als);

// -- Gene / Protein targets --------------------------------------------------
MERGE (a4i:GeneProtein { node_name: "Integrin alpha-4" })
  ON CREATE SET a4i.node_id = "biogen_gp_itga4", a4i.type = "GeneProtein",
                a4i.symbol = "ITGA4", a4i.uniprot = "P13612";
MERGE (smn1:GeneProtein { node_name: "SMN1" })
  ON CREATE SET smn1.node_id = "biogen_gp_smn1", smn1.type = "GeneProtein",
                smn1.symbol = "SMN1", smn1.uniprot = "Q16637";
MERGE (sod1:GeneProtein { node_name: "SOD1" })
  ON CREATE SET sod1.node_id = "biogen_gp_sod1", sod1.type = "GeneProtein",
                sod1.symbol = "SOD1", sod1.uniprot = "P00441";
MERGE (abeta:GeneProtein { node_name: "Amyloid Beta" })
  ON CREATE SET abeta.node_id = "biogen_gp_abeta", abeta.type = "GeneProtein",
                abeta.symbol = "APP", abeta.uniprot = "P05067";
MERGE (frataxin:GeneProtein { node_name: "Frataxin" })
  ON CREATE SET frataxin.node_id = "biogen_gp_frataxin", frataxin.type = "GeneProtein",
                frataxin.symbol = "FXN", frataxin.uniprot = "Q16595";

// -- Marketed Drug portfolio --------------------------------------------------
MERGE (tecfidera:Drug { node_name: "Tecfidera" })
  ON CREATE SET tecfidera.node_id = "biogen_drug_tecfidera",
                tecfidera.type = "Drug",
                tecfidera.generic_name = "dimethyl fumarate",
                tecfidera.fda_approval_year = 2013,
                tecfidera.modality = "small molecule";
MERGE (vumerity:Drug { node_name: "Vumerity" })
  ON CREATE SET vumerity.node_id = "biogen_drug_vumerity",
                vumerity.type = "Drug",
                vumerity.generic_name = "diroximel fumarate",
                vumerity.fda_approval_year = 2019,
                vumerity.modality = "small molecule";
MERGE (tysabri:Drug { node_name: "Tysabri" })
  ON CREATE SET tysabri.node_id = "biogen_drug_tysabri",
                tysabri.type = "Drug",
                tysabri.generic_name = "natalizumab",
                tysabri.fda_approval_year = 2004,
                tysabri.modality = "monoclonal antibody";
MERGE (plegridy:Drug { node_name: "Plegridy" })
  ON CREATE SET plegridy.node_id = "biogen_drug_plegridy",
                plegridy.type = "Drug",
                plegridy.generic_name = "peginterferon beta-1a",
                plegridy.fda_approval_year = 2014,
                plegridy.modality = "biologic";
MERGE (avonex:Drug { node_name: "Avonex" })
  ON CREATE SET avonex.node_id = "biogen_drug_avonex",
                avonex.type = "Drug",
                avonex.generic_name = "interferon beta-1a",
                avonex.fda_approval_year = 1996,
                avonex.modality = "biologic";
MERGE (fampyra:Drug { node_name: "Fampyra" })
  ON CREATE SET fampyra.node_id = "biogen_drug_fampyra",
                fampyra.type = "Drug",
                fampyra.generic_name = "dalfampridine",
                fampyra.fda_approval_year = 2010,
                fampyra.modality = "small molecule",
                fampyra.us_brand = "Ampyra (originated by Acorda; Biogen markets EU)";
MERGE (spinraza:Drug { node_name: "Spinraza" })
  ON CREATE SET spinraza.node_id = "biogen_drug_spinraza",
                spinraza.type = "Drug",
                spinraza.generic_name = "nusinersen",
                spinraza.fda_approval_year = 2016,
                spinraza.modality = "antisense oligonucleotide";
MERGE (aduhelm:Drug { node_name: "Aduhelm" })
  ON CREATE SET aduhelm.node_id = "biogen_drug_aduhelm",
                aduhelm.type = "Drug",
                aduhelm.generic_name = "aducanumab",
                aduhelm.fda_approval_year = 2021,
                aduhelm.modality = "monoclonal antibody",
                aduhelm.status = "Discontinued (commercialisation ended early 2024)";
MERGE (leqembi:Drug { node_name: "Leqembi" })
  ON CREATE SET leqembi.node_id = "biogen_drug_leqembi",
                leqembi.type = "Drug",
                leqembi.generic_name = "lecanemab",
                leqembi.fda_approval_year = 2023,
                leqembi.modality = "monoclonal antibody",
                leqembi.partner = "Eisai (lead)";
MERGE (qalsody:Drug { node_name: "Qalsody" })
  ON CREATE SET qalsody.node_id = "biogen_drug_qalsody",
                qalsody.type = "Drug",
                qalsody.generic_name = "tofersen",
                qalsody.fda_approval_year = 2023,
                qalsody.modality = "antisense oligonucleotide",
                qalsody.notes = "Accelerated approval for SOD1-ALS.";
MERGE (skyclarys:Drug { node_name: "Skyclarys" })
  ON CREATE SET skyclarys.node_id = "biogen_drug_skyclarys",
                skyclarys.type = "Drug",
                skyclarys.generic_name = "omaveloxolone",
                skyclarys.fda_approval_year = 2023,
                skyclarys.modality = "small molecule",
                skyclarys.notes = "Acquired via Reata 2023.";
MERGE (zurzuvae:Drug { node_name: "Zurzuvae" })
  ON CREATE SET zurzuvae.node_id = "biogen_drug_zurzuvae",
                zurzuvae.type = "Drug",
                zurzuvae.generic_name = "zuranolone",
                zurzuvae.fda_approval_year = 2023,
                zurzuvae.modality = "small molecule",
                zurzuvae.partner = "Sage Therapeutics";

// -- Org → Drug ownership / patent / sponsorship -----------------------------
MATCH (biogen:Organization { node_id: "f608437b7867" })
MATCH (d:Drug)
WHERE d.node_id IN [
  "biogen_drug_tecfidera","biogen_drug_vumerity","biogen_drug_tysabri",
  "biogen_drug_plegridy","biogen_drug_avonex","biogen_drug_fampyra",
  "biogen_drug_spinraza","biogen_drug_aduhelm","biogen_drug_leqembi",
  "biogen_drug_qalsody","biogen_drug_skyclarys","biogen_drug_zurzuvae"
]
MERGE (biogen)-[:OWNS_PATENT_ON { source: "Biogen 10-K FY2024" }]->(d)
MERGE (biogen)-[:SPONSORS { kind: "marketing_authorisation_holder" }]->(d);

// -- Drug → Disease indications (lowercase rel to match graph convention) ----
MATCH (tec:Drug   { node_id: "biogen_drug_tecfidera" }), (rrms:Disease { node_id: "biogen_dz_rrms" })
MERGE (tec)-[:indication { source: "FDA label" }]->(rrms);
MATCH (vum:Drug   { node_id: "biogen_drug_vumerity"  }), (rrms:Disease { node_id: "biogen_dz_rrms" })
MERGE (vum)-[:indication { source: "FDA label" }]->(rrms);
MATCH (tys:Drug   { node_id: "biogen_drug_tysabri"   }), (ms:Disease   { node_id: "biogen_dz_ms"   })
MERGE (tys)-[:indication { source: "FDA label" }]->(ms);
MATCH (tys:Drug   { node_id: "biogen_drug_tysabri"   }), (cd:Disease   { node_id: "biogen_dz_crohn" })
MERGE (tys)-[:indication { source: "FDA label" }]->(cd);
MATCH (ple:Drug   { node_id: "biogen_drug_plegridy"  }), (rrms:Disease { node_id: "biogen_dz_rrms" })
MERGE (ple)-[:indication { source: "FDA label" }]->(rrms);
MATCH (avo:Drug   { node_id: "biogen_drug_avonex"    }), (rrms:Disease { node_id: "biogen_dz_rrms" })
MERGE (avo)-[:indication { source: "FDA label" }]->(rrms);
MATCH (fam:Drug   { node_id: "biogen_drug_fampyra"   }), (ms:Disease   { node_id: "biogen_dz_ms"   })
MERGE (fam)-[:indication { source: "EMA label", note: "improves walking in MS" }]->(ms);
MATCH (spi:Drug   { node_id: "biogen_drug_spinraza"  }), (sma:Disease  { node_id: "biogen_dz_sma"  })
MERGE (spi)-[:indication { source: "FDA label" }]->(sma);
MATCH (adu:Drug   { node_id: "biogen_drug_aduhelm"   }), (alz:Disease  { node_id: "biogen_dz_alz"  })
MERGE (adu)-[:indication { source: "FDA accelerated approval (withdrawn)" }]->(alz);
MATCH (leq:Drug   { node_id: "biogen_drug_leqembi"   }), (alz:Disease  { node_id: "biogen_dz_alz"  })
MERGE (leq)-[:indication { source: "FDA traditional approval Jul 2023" }]->(alz);
MATCH (qal:Drug   { node_id: "biogen_drug_qalsody"   }), (sod:Disease  { node_id: "biogen_dz_sod1als" })
MERGE (qal)-[:indication { source: "FDA accelerated approval Apr 2023" }]->(sod);
MATCH (sky:Drug   { node_id: "biogen_drug_skyclarys" }), (frda:Disease { node_id: "biogen_dz_frda" })
MERGE (sky)-[:indication { source: "FDA label Feb 2023" }]->(frda);
MATCH (zur:Drug   { node_id: "biogen_drug_zurzuvae"  }), (ppd:Disease  { node_id: "biogen_dz_ppd"  })
MERGE (zur)-[:indication { source: "FDA label Aug 2023" }]->(ppd);

// -- Drug → Target (drug_protein) ---------------------------------------------
MATCH (tys:Drug { node_id: "biogen_drug_tysabri" }), (a4i:GeneProtein { node_id: "biogen_gp_itga4" })
MERGE (tys)-[:drug_protein { mechanism: "binds α4-integrin, blocks leukocyte adhesion" }]->(a4i);
MATCH (spi:Drug { node_id: "biogen_drug_spinraza" }), (smn:GeneProtein { node_id: "biogen_gp_smn1" })
MERGE (spi)-[:drug_protein { mechanism: "ASO modulates SMN2 splicing to restore SMN protein" }]->(smn);
MATCH (qal:Drug { node_id: "biogen_drug_qalsody" }), (sod:GeneProtein { node_id: "biogen_gp_sod1" })
MERGE (qal)-[:drug_protein { mechanism: "ASO reduces SOD1 mRNA / mutant protein" }]->(sod);
MATCH (adu:Drug { node_id: "biogen_drug_aduhelm" }), (ab:GeneProtein  { node_id: "biogen_gp_abeta" })
MERGE (adu)-[:drug_protein { mechanism: "anti-amyloid mAb targeting aggregated Aβ" }]->(ab);
MATCH (leq:Drug { node_id: "biogen_drug_leqembi" }), (ab:GeneProtein  { node_id: "biogen_gp_abeta" })
MERGE (leq)-[:drug_protein { mechanism: "anti-amyloid mAb targeting Aβ protofibrils" }]->(ab);
MATCH (sky:Drug { node_id: "biogen_drug_skyclarys" }), (frx:GeneProtein { node_id: "biogen_gp_frataxin" })
MERGE (sky)-[:drug_protein { mechanism: "Nrf2 activator; supports frataxin-deficient mitochondrial function" }]->(frx);

// -- Drug aliases -------------------------------------------------------------
UNWIND [
  ["biogen_drug_tecfidera","BG-12"],
  ["biogen_drug_tecfidera","DMF"],
  ["biogen_drug_vumerity","BIIB098"],
  ["biogen_drug_tysabri","Antegren"],
  ["biogen_drug_spinraza","ISIS-SMNRx"],
  ["biogen_drug_aduhelm","BIIB037"],
  ["biogen_drug_leqembi","BAN2401"],
  ["biogen_drug_qalsody","ISIS-SOD1Rx"],
  ["biogen_drug_skyclarys","RTA-408"],
  ["biogen_drug_zurzuvae","SAGE-217"]
] AS pair
MATCH (d:Drug { node_id: pair[0] })
MERGE (d)-[:has_drug_alias { alias: pair[1] }]->(d);

// -- Pivotal clinical trials --------------------------------------------------
UNWIND [
  ["biogen_trial_define","NCT00420212","DEFINE","Phase 3","Tecfidera vs placebo in RRMS","biogen_drug_tecfidera","biogen_dz_rrms"],
  ["biogen_trial_endorse","NCT03683459","ENDORSE-MS","Phase 3 OLE","Long-term Tecfidera safety","biogen_drug_tecfidera","biogen_dz_rrms"],
  ["biogen_trial_evolveMS1","NCT02634307","EVOLVE-MS-1","Phase 3","Vumerity in RRMS","biogen_drug_vumerity","biogen_dz_rrms"],
  ["biogen_trial_affirm","NCT00027300","AFFIRM","Phase 3","Tysabri in RRMS","biogen_drug_tysabri","biogen_dz_rrms"],
  ["biogen_trial_endeavor","NCT02193074","ENDEAVOR","Phase 3","Spinraza in infantile-onset SMA","biogen_drug_spinraza","biogen_dz_sma"],
  ["biogen_trial_emerge","NCT02484547","EMERGE","Phase 3","Aducanumab in early Alzheimer's","biogen_drug_aduhelm","biogen_dz_alz"],
  ["biogen_trial_engage","NCT02477800","ENGAGE","Phase 3","Aducanumab in early Alzheimer's (sister trial)","biogen_drug_aduhelm","biogen_dz_alz"],
  ["biogen_trial_clarityad","NCT03887455","CLARITY-AD","Phase 3","Lecanemab in early Alzheimer's","biogen_drug_leqembi","biogen_dz_alz"],
  ["biogen_trial_valor","NCT02623699","VALOR","Phase 3","Tofersen in SOD1-ALS","biogen_drug_qalsody","biogen_dz_sod1als"],
  ["biogen_trial_moxie","NCT02255435","MOXIe","Phase 2","Omaveloxolone in Friedreich ataxia","biogen_drug_skyclarys","biogen_dz_frda"],
  ["biogen_trial_skylark","NCT04442503","SKYLARK","Phase 3","Zuranolone in postpartum depression","biogen_drug_zurzuvae","biogen_dz_ppd"]
] AS t
MATCH (drug:Drug    { node_id: t[5] })
MATCH (dz:Disease   { node_id: t[6] })
MERGE (trial:ClinicalTrial { node_id: t[0] })
  ON CREATE SET trial.nct_id    = t[1],
                trial.node_name = t[2],
                trial.phase     = t[3],
                trial.title     = t[4],
                trial.type      = "ClinicalTrial"
MERGE (trial)-[:evaluated_in { kind: "primary investigational drug" }]->(drug)
MERGE (trial)-[:featured_in  { reason: "indication under study" }]->(dz)
MERGE (biogen:Organization { node_id: "f608437b7867" })-[:SPONSORS { role: "sponsor" }]->(trial);

// -- Cross-link to existing Biogen variants ----------------------------------
MATCH (canonical:Organization { node_id: "f608437b7867" })
MATCH (variant:Organization)
WHERE variant.node_id IN ["2722fd2ecc8e","af565578f391","431309bc8dab"]
  AND variant.node_id <> "f608437b7867"
MERGE (variant)-[:SPELLING_VARIATION { canonical: "Biogen Inc" }]->(canonical);

// =============================================================================
// Done.  Verify with:
//   MATCH (b:Organization { node_id: "f608437b7867" })-[r]-(n)
//   RETURN type(r) AS rel, labels(n) AS lbl, count(*) AS c ORDER BY c DESC;
// =============================================================================
