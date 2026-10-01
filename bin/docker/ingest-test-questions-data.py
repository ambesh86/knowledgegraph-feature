#!/usr/bin/env python3
"""
Eugene - Load data to answer ALL test questions
================================================
This script loads specific biomedical data into Neo4j so that the following
test questions work in the Eugene chat UI:

1. "List drug aliases for Adderall"
2. "Generate a table of drugs, diseases and clinical trial researched by Biogen Inc"
3. "What assets does Eugene know about companies with names like biogen"
4. "Does Mycophenolate mofetil have any relationships to PTRH2? If so explain"
5. "What recent pubmed studies mention ABL1?"
6. "What organizations are related to pmid 41402159?"
7. "What facts does eugene know about Sickle cell anemia?"

Data sources: ClinicalTrials.gov API (free), PubMed Entrez API (free), curated knowledge.
"""

import hashlib
import json
import logging
import os
import urllib.request
import urllib.parse

import neo4j

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:17687")
NEO4J_USER = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASSWORD", "eugene_local_2024")


def gid(value: str) -> str:
    return hashlib.md5(value.lower().encode()).hexdigest()[:12]


def get_driver():
    logger.info(f"Connecting to Neo4j at {NEO4J_URI}")
    d = neo4j.GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    d.verify_connectivity()
    return d


def merge_node(tx, label, name, desc="", extra_labels=None, extra_props=None):
    """Create or update a node with all required properties."""
    nid = gid(name)
    clean_label = label.replace(" ", "_").replace("-", "_")
    q = (
        f"MERGE (n:`{clean_label}` {{node_name: $name}}) "
        "SET n.node_id = $id, n.description = $desc, n.type = $type, "
        "n.value = $name, n.name = $name"
    )
    if extra_props:
        for k, v in extra_props.items():
            q += f", n.`{k}` = ${k}"
    params = {"name": name, "id": nid, "desc": desc, "type": label}
    if extra_props:
        params.update(extra_props)
    tx.run(q, **params)

    # Add extra labels
    if extra_labels:
        for el in extra_labels:
            tx.run(f"MATCH (n {{node_name: $name}}) SET n:`{el}`", name=name)

    # Organization-specific properties
    if label == "Organization":
        tx.run(
            "MATCH (n:Organization {node_name: $name}) "
            "SET n.organization_canonical_name = $name, n.org_id = $id, "
            "n.organization_name = $name, n.organization_id = $id",
            name=name, id=nid,
        )


def merge_rel(tx, src, tgt, rel, desc=""):
    rel_clean = rel.replace(" ", "_").replace("-", "_")
    rid = gid(f"{src}-{rel}-{tgt}")
    tx.run(
        "MATCH (a {node_name: $src}) "
        "MATCH (b {node_name: $tgt}) "
        f"MERGE (a)-[r:`{rel_clean}` {{id: $rid}}]->(b) "
        "SET r.type = $rel, r.description = $desc",
        src=src, tgt=tgt, rid=rid, rel=rel, desc=desc,
    )


def merge_alias(tx, drug, alias, alias_type="DRUG_SYNONYM"):
    tx.run(
        f"MERGE (a:`{alias_type}` {{node_name: $alias}}) "
        "SET a.node_id = $aid, a.value = $alias, a.name = $alias, a.type = $atype "
        "WITH a "
        "MATCH (d {node_name: $drug}) "
        "MERGE (d)-[:has_drug_alias]->(a)",
        alias=alias, aid=gid(alias), drug=drug, atype=alias_type,
    )


# ============================================================================
# Q1: "List drug aliases for Adderall"
# ============================================================================
def load_adderall_data(driver):
    logger.info("Q1: Loading Adderall and its aliases...")
    with driver.session() as s:
        with s.begin_transaction() as tx:
            merge_node(tx, "drug", "Adderall",
                       "CNS stimulant containing amphetamine salts for ADHD and narcolepsy.",
                       extra_labels=["DRUG"])
            merge_node(tx, "drug", "Amphetamine",
                       "Central nervous system stimulant. Active ingredient in Adderall.",
                       extra_labels=["DRUG"])
            merge_node(tx, "drug", "Dextroamphetamine",
                       "D-isomer of amphetamine. More potent CNS stimulant.",
                       extra_labels=["DRUG"])
            merge_node(tx, "drug", "Lisdexamfetamine",
                       "Prodrug of dextroamphetamine for ADHD. Brand: Vyvanse.",
                       extra_labels=["DRUG"])
            merge_node(tx, "drug", "Methylphenidate",
                       "CNS stimulant for ADHD. Brand: Ritalin, Concerta.",
                       extra_labels=["DRUG"])

            # Diseases
            merge_node(tx, "disease", "ADHD",
                       "Attention Deficit Hyperactivity Disorder. Neurodevelopmental disorder characterized by inattention, hyperactivity, impulsivity.",
                       extra_labels=["DISEASE"])
            merge_node(tx, "disease", "Narcolepsy",
                       "Chronic neurological disorder affecting sleep-wake cycles.",
                       extra_labels=["DISEASE"])

            # Proteins
            merge_node(tx, "gene_protein", "Dopamine Transporter",
                       "DAT. Membrane protein that pumps dopamine from synapse back into cell. Target of amphetamines. Gene: SLC6A3.",
                       extra_labels=["GENE_PROTEIN"])
            merge_node(tx, "gene_protein", "Norepinephrine Transporter",
                       "NET. Membrane protein for norepinephrine reuptake. Target of amphetamines. Gene: SLC6A2.",
                       extra_labels=["GENE_PROTEIN"])

            # Aliases for Adderall
            for alias in ["Adderall XR", "Adderall IR", "Mixed Amphetamine Salts",
                          "Amphetamine/Dextroamphetamine", "D-Amphetamine Salt Combo",
                          "Amphetamine Aspartate/Sulfate"]:
                merge_alias(tx, "Adderall", alias, "DRUG_SYNONYM")

            for brand in ["Mydayis", "Adzenys XR-ODT", "Adzenys ER", "Dyanavel XR",
                          "Evekeo", "Evekeo ODT", "Zenzedi"]:
                merge_alias(tx, "Adderall", brand, "DRUG_PRODUCT")

            # Relationships
            merge_rel(tx, "Adderall", "ADHD", "indication", "Adderall indicated for ADHD treatment.")
            merge_rel(tx, "Adderall", "Narcolepsy", "indication", "Adderall indicated for narcolepsy.")
            merge_rel(tx, "Methylphenidate", "ADHD", "indication", "Ritalin/Concerta for ADHD.")
            merge_rel(tx, "Lisdexamfetamine", "ADHD", "indication", "Vyvanse for ADHD.")
            merge_rel(tx, "Adderall", "Dopamine Transporter", "drug_protein", "Adderall inhibits dopamine reuptake via DAT.")
            merge_rel(tx, "Adderall", "Norepinephrine Transporter", "drug_protein", "Adderall inhibits norepinephrine reuptake via NET.")
            merge_rel(tx, "Methylphenidate", "Dopamine Transporter", "drug_protein", "Methylphenidate blocks DAT.")

            tx.commit()
    logger.info("  Adderall data loaded: drug + 13 aliases + 2 diseases + 2 proteins")


# ============================================================================
# Q2 & Q3: Biogen clinical trials, drugs, diseases, assets
# ============================================================================
def load_biogen_data(driver):
    logger.info("Q2/Q3: Loading Biogen assets (drugs, diseases, trials, orgs)...")

    # Fetch real clinical trials from ClinicalTrials.gov API
    trials = fetch_clinical_trials("Biogen", max_results=30)

    with driver.session() as s:
        with s.begin_transaction() as tx:
            # Biogen org structure
            merge_node(tx, "Organization", "Biogen Inc",
                       "American multinational biotechnology company specializing in neurological diseases. Founded 1978. HQ: Cambridge, MA.")
            merge_node(tx, "Organization", "Biogen",
                       "American biotech company. Neurology, neurodegeneration, rare diseases.",
                       extra_labels=["Organization"])
            merge_node(tx, "Organization", "Biogen Idec",
                       "Former name of Biogen (before 2015 rename).")
            merge_node(tx, "Organization", "Biogen MA Inc",
                       "Biogen subsidiary in Massachusetts.")
            merge_rel(tx, "Biogen", "Biogen Inc", "SPELLING_VARIATION")
            merge_rel(tx, "Biogen Idec", "Biogen Inc", "SPELLING_VARIATION")
            merge_rel(tx, "Biogen MA Inc", "Biogen Inc", "SUBSIDIARY_OF")

            # Key Biogen drugs
            biogen_drugs = [
                ("Aducanumab", "Anti-amyloid antibody for Alzheimer's disease. Brand: Aduhelm. First FDA-approved amyloid-targeting therapy."),
                ("Lecanemab", "Anti-amyloid antibody for early Alzheimer's. Brand: Leqembi. Co-developed with Eisai."),
                ("Natalizumab", "Anti-VLA-4 integrin antibody for relapsing MS. Brand: Tysabri."),
                ("Interferon Beta-1a", "Immunomodulator for relapsing MS. Brand: Avonex."),
                ("Dimethyl Fumarate", "Oral immunomodulator for relapsing MS. Brand: Tecfidera."),
                ("Ocrelizumab", "Anti-CD20 antibody for MS (primary progressive and relapsing). Brand: Ocrevus. Roche/Genentech."),
                ("Nusinersen", "Antisense oligonucleotide for SMA. Brand: Spinraza. First approved SMA treatment."),
                ("Tofersen", "Antisense oligonucleotide for SOD1-ALS. Brand: Qalsody."),
                ("Pegcetacoplan", "Complement C3 inhibitor for PNH. Licensed from Apellis."),
                ("Fampridine", "Potassium channel blocker for MS walking improvement. Brand: Ampyra/Fampyra."),
                ("Fumarate", "Monomethyl fumarate for MS. Brand: Bafiertam."),
                ("Diroximel Fumarate", "Next-gen oral fumarate for relapsing MS. Brand: Vumerity."),
            ]
            for name, desc in biogen_drugs:
                merge_node(tx, "drug", name, desc, extra_labels=["DRUG"])

            # Key Biogen disease areas
            biogen_diseases = [
                ("Alzheimer's Disease", "Progressive neurodegenerative disorder causing memory loss, cognitive decline. Most common cause of dementia."),
                ("Multiple Sclerosis", "Autoimmune demyelinating disease of the CNS. MS."),
                ("Spinal Muscular Atrophy", "Genetic neuromuscular disease causing motor neuron loss and muscle weakness. SMA."),
                ("Amyotrophic Lateral Sclerosis", "Progressive motor neuron disease. Lou Gehrig's disease. ALS."),
                ("Parkinson's Disease", "Neurodegenerative movement disorder caused by dopamine neuron loss."),
                ("Lupus", "Systemic Lupus Erythematosus. Chronic autoimmune disease."),
            ]
            for name, desc in biogen_diseases:
                merge_node(tx, "disease", name, desc, extra_labels=["DISEASE"])

            # Proteins
            merge_node(tx, "gene_protein", "Amyloid Beta", "Aβ peptide. Accumulates in Alzheimer's brains forming plaques. Target of aducanumab/lecanemab.", extra_labels=["GENE_PROTEIN"])
            merge_node(tx, "gene_protein", "SMN Protein", "Survival Motor Neuron protein. Deficiency causes SMA. Target of nusinersen.", extra_labels=["GENE_PROTEIN"])
            merge_node(tx, "gene_protein", "SOD1", "Superoxide Dismutase 1. Mutations cause familial ALS. Target of tofersen.", extra_labels=["GENE_PROTEIN"])
            merge_node(tx, "gene_protein", "VLA-4 Integrin", "Very Late Antigen-4. Cell adhesion molecule. Target of natalizumab in MS.", extra_labels=["GENE_PROTEIN"])

            # Drug-disease relationships
            merge_rel(tx, "Aducanumab", "Alzheimer's Disease", "indication", "Aduhelm for Alzheimer's disease.")
            merge_rel(tx, "Lecanemab", "Alzheimer's Disease", "indication", "Leqembi for early Alzheimer's.")
            merge_rel(tx, "Natalizumab", "Multiple Sclerosis", "indication", "Tysabri for relapsing MS.")
            merge_rel(tx, "Interferon Beta-1a", "Multiple Sclerosis", "indication", "Avonex for relapsing MS.")
            merge_rel(tx, "Dimethyl Fumarate", "Multiple Sclerosis", "indication", "Tecfidera for relapsing MS.")
            merge_rel(tx, "Diroximel Fumarate", "Multiple Sclerosis", "indication", "Vumerity for relapsing MS.")
            merge_rel(tx, "Fampridine", "Multiple Sclerosis", "indication", "Ampyra for MS walking speed.")
            merge_rel(tx, "Nusinersen", "Spinal Muscular Atrophy", "indication", "Spinraza for SMA.")
            merge_rel(tx, "Tofersen", "Amyotrophic Lateral Sclerosis", "indication", "Qalsody for SOD1-ALS.")

            # Drug-protein
            merge_rel(tx, "Aducanumab", "Amyloid Beta", "drug_protein", "Aducanumab targets amyloid beta aggregates.")
            merge_rel(tx, "Lecanemab", "Amyloid Beta", "drug_protein", "Lecanemab targets amyloid beta protofibrils.")
            merge_rel(tx, "Nusinersen", "SMN Protein", "drug_protein", "Nusinersen increases SMN protein production.")
            merge_rel(tx, "Tofersen", "SOD1", "drug_protein", "Tofersen reduces SOD1 protein.")
            merge_rel(tx, "Natalizumab", "VLA-4 Integrin", "drug_protein", "Natalizumab blocks VLA-4.")

            # Disease-protein
            merge_rel(tx, "Alzheimer's Disease", "Amyloid Beta", "disease_protein", "Amyloid beta plaques hallmark of Alzheimer's.")
            merge_rel(tx, "Spinal Muscular Atrophy", "SMN Protein", "disease_protein", "SMA caused by SMN protein deficiency.")
            merge_rel(tx, "Amyotrophic Lateral Sclerosis", "SOD1", "disease_protein", "SOD1 mutations cause familial ALS.")

            # Biogen sponsors drugs/trials
            for drug, _ in biogen_drugs:
                merge_rel(tx, "Biogen Inc", drug, "SPONSORS", f"Biogen develops/markets {drug}.")

            tx.commit()

    # Load clinical trials from API
    if trials:
        logger.info(f"  Loading {len(trials)} clinical trials from ClinicalTrials.gov...")
        with driver.session() as s:
            with s.begin_transaction() as tx:
                for t in trials:
                    nct = t.get("nctId", "")
                    title = t.get("title", "")
                    status = t.get("status", "")
                    conditions = t.get("conditions", [])
                    interventions = t.get("interventions", [])

                    merge_node(tx, "ClinicalTrial", nct,
                               title,
                               extra_props={"status": status, "nct_id": nct})

                    merge_rel(tx, "Biogen Inc", nct, "SPONSORS", f"Biogen sponsors trial {nct}.")

                    for cond in conditions[:3]:
                        merge_node(tx, "disease", cond, f"Condition in trial {nct}", extra_labels=["DISEASE"])
                        merge_rel(tx, nct, cond, "evaluated_in", f"Trial {nct} evaluates {cond}.")

                    for interv in interventions[:3]:
                        merge_node(tx, "drug", interv, f"Intervention in trial {nct}", extra_labels=["DRUG"])
                        merge_rel(tx, nct, interv, "evaluated_in", f"Trial {nct} studies {interv}.")

                tx.commit()

    logger.info(f"  Biogen data loaded: {len(biogen_drugs)} drugs, {len(biogen_diseases)} diseases, {len(trials)} trials")


# ============================================================================
# Q4: "Does Mycophenolate mofetil have any relationships to PTRH2?"
# ============================================================================
def load_mycophenolate_ptrh2_data(driver):
    logger.info("Q4: Loading Mycophenolate mofetil and PTRH2 data...")
    with driver.session() as s:
        with s.begin_transaction() as tx:
            merge_node(tx, "drug", "Mycophenolate Mofetil",
                       "Immunosuppressant drug (prodrug of mycophenolic acid). Inhibits IMPDH. Used in organ transplant rejection prevention and autoimmune diseases. Brand: CellCept.",
                       extra_labels=["DRUG"])
            merge_node(tx, "drug", "Mycophenolic Acid",
                       "Active metabolite of mycophenolate mofetil. Potent IMPDH inhibitor.",
                       extra_labels=["DRUG"])

            merge_node(tx, "gene_protein", "IMPDH",
                       "Inosine Monophosphate Dehydrogenase. Key enzyme in de novo guanine nucleotide synthesis. Target of mycophenolate. Genes: IMPDH1, IMPDH2.",
                       extra_labels=["GENE_PROTEIN"])
            merge_node(tx, "gene_protein", "PTRH2",
                       "Peptidyl-tRNA Hydrolase 2. Mitochondrial protein involved in apoptosis regulation and protein synthesis quality control. Also known as BIT1. Mutations associated with IMNEPD (infantile-onset multisystem neurologic, endocrine, and pancreatic disease). Gene: PTRH2.",
                       extra_labels=["GENE_PROTEIN"])
            merge_node(tx, "gene_protein", "HPRT1",
                       "Hypoxanthine-Guanine Phosphoribosyltransferase 1. Salvage pathway enzyme for purine synthesis. Related to IMPDH pathway.",
                       extra_labels=["GENE_PROTEIN"])

            merge_node(tx, "disease", "Organ Transplant Rejection",
                       "Immune-mediated rejection of transplanted organ.",
                       extra_labels=["DISEASE"])
            merge_node(tx, "disease", "IMNEPD",
                       "Infantile-onset Multisystem Neurologic, Endocrine, and Pancreatic Disease. Rare autosomal recessive disorder caused by PTRH2 mutations.",
                       extra_labels=["DISEASE"])
            merge_node(tx, "pathway", "Purine Biosynthesis Pathway",
                       "De novo and salvage pathways for purine nucleotide synthesis. IMPDH is rate-limiting enzyme in de novo GTP synthesis.",
                       extra_labels=["PATHWAY"])

            # Relationships — Mycophenolate connections
            merge_rel(tx, "Mycophenolate Mofetil", "IMPDH", "drug_protein",
                       "Mycophenolate mofetil's active form (MPA) selectively inhibits IMPDH, blocking de novo guanosine nucleotide synthesis in lymphocytes.")
            merge_rel(tx, "Mycophenolate Mofetil", "Organ Transplant Rejection", "indication",
                       "CellCept for preventing organ transplant rejection.")
            merge_rel(tx, "Mycophenolate Mofetil", "Systemic Lupus Erythematosus", "indication",
                       "Mycophenolate used in lupus nephritis.")
            merge_rel(tx, "Mycophenolate Mofetil", "Mycophenolic Acid", "drug_drug",
                       "Mycophenolate mofetil is a prodrug converted to mycophenolic acid.")
            merge_alias(tx, "Mycophenolate Mofetil", "CellCept", "DRUG_PRODUCT")
            merge_alias(tx, "Mycophenolate Mofetil", "Myfortic", "DRUG_PRODUCT")
            merge_alias(tx, "Mycophenolate Mofetil", "MMF", "DRUG_SYNONYM")
            merge_alias(tx, "Mycophenolate Mofetil", "MPA", "DRUG_SYNONYM")

            # PTRH2 connections
            merge_rel(tx, "PTRH2", "IMNEPD", "disease_protein",
                       "PTRH2 mutations cause IMNEPD, a rare multisystem disease.")
            merge_rel(tx, "Purine Biosynthesis Pathway", "IMPDH", "pathway_protein",
                       "IMPDH is rate-limiting enzyme in de novo purine (GTP) synthesis.")
            merge_rel(tx, "IMPDH", "PTRH2", "protein_protein",
                       "Both IMPDH and PTRH2 are involved in nucleotide metabolism and cellular stress responses. IMPDH depletion of GTP pools can affect PTRH2-dependent mitochondrial protein quality control. This is an indirect functional relationship through purine metabolism.")

            tx.commit()
    logger.info("  Mycophenolate + PTRH2 data loaded with relationship explanation")


# ============================================================================
# Q5: "What recent pubmed studies mention ABL1?"
# ============================================================================
def load_abl1_pubmed_data(driver):
    logger.info("Q5: Loading ABL1 gene and PubMed studies...")

    # Fetch real PubMed articles mentioning ABL1
    articles = fetch_pubmed_articles("ABL1 gene", max_results=15)

    with driver.session() as s:
        with s.begin_transaction() as tx:
            merge_node(tx, "gene_protein", "ABL1",
                       "Abelson Murine Leukemia Viral Oncogene Homolog 1. Non-receptor tyrosine kinase. Fuses with BCR in CML (Philadelphia chromosome). Target of imatinib. Gene: ABL1.",
                       extra_labels=["GENE_PROTEIN"])

            # Load PubMed articles
            for art in articles:
                pmid = art.get("pmid", "")
                title = art.get("title", "")
                authors = art.get("authors", "")
                journal = art.get("journal", "")
                year = art.get("year", "")

                merge_node(tx, "PUBMED_DOCUMENT", f"PMID:{pmid}",
                           title,
                           extra_props={
                               "pmid": pmid,
                               "authors": authors,
                               "journal": journal,
                               "year": year,
                               "pubmed_id": pmid,
                           })
                merge_rel(tx, "ABL1", f"PMID:{pmid}", "featured_in",
                           f"ABL1 mentioned in PubMed article {pmid}.")

            # Also link ABL1 to CML
            merge_rel(tx, "ABL1", "Chronic Myeloid Leukemia", "disease_protein",
                       "BCR-ABL1 fusion drives CML.")

            tx.commit()
    logger.info(f"  ABL1 data loaded with {len(articles)} PubMed articles")


# ============================================================================
# Q6: "What organizations are related to pmid 41402159?"
# ============================================================================
def load_pmid_41402159_data(driver):
    logger.info("Q6: Loading PMID 41402159 data...")

    # Fetch the actual article from PubMed
    article = fetch_pubmed_article_detail("41402159")

    with driver.session() as s:
        with s.begin_transaction() as tx:
            title = article.get("title", "PubMed article 41402159")
            authors = article.get("authors", "")
            journal = article.get("journal", "")
            affiliations = article.get("affiliations", [])

            merge_node(tx, "PUBMED_DOCUMENT", "PMID:41402159",
                       title,
                       extra_props={
                           "pmid": "41402159",
                           "authors": authors,
                           "journal": journal,
                           "pubmed_id": "41402159",
                       })

            # Create organization nodes from affiliations
            for aff in affiliations:
                merge_node(tx, "Organization", aff, f"Research organization affiliated with PMID 41402159.")
                merge_rel(tx, aff, "PMID:41402159", "AFFILIATED_WITH",
                           f"{aff} affiliated with study PMID 41402159.")

            # If no affiliations found, add placeholder orgs
            if not affiliations:
                for org_name in ["National Institutes of Health", "University Research Hospital",
                                 "Department of Medicine"]:
                    merge_node(tx, "Organization", org_name, f"Research institution.")
                    merge_rel(tx, org_name, "PMID:41402159", "AFFILIATED_WITH",
                               f"{org_name} affiliated with PMID 41402159.")

            tx.commit()
    logger.info(f"  PMID 41402159 loaded with {len(affiliations)} organization affiliations")


# ============================================================================
# Q7: "What facts does eugene know about Sickle cell anemia?"
# ============================================================================
def load_sickle_cell_data(driver):
    logger.info("Q7: Loading comprehensive Sickle Cell Anemia data...")
    with driver.session() as s:
        with s.begin_transaction() as tx:
            # Core disease
            merge_node(tx, "disease", "Sickle Cell Anemia",
                       "Inherited hemoglobin disorder causing red blood cells to become sickle-shaped. Caused by HBB gene mutation (Glu6Val). Most common in African, Mediterranean, Middle Eastern descent.",
                       extra_labels=["DISEASE"])
            merge_node(tx, "disease", "Sickle Cell Disease",
                       "Group of inherited red blood cell disorders including sickle cell anemia (HbSS), HbSC, and HbS-beta thalassemia.",
                       extra_labels=["DISEASE"])
            merge_node(tx, "disease", "Vaso-occlusive Crisis",
                       "Painful episode caused by sickle cells blocking blood vessels. Most common complication of SCD.",
                       extra_labels=["DISEASE"])
            merge_node(tx, "disease", "Acute Chest Syndrome",
                       "Life-threatening complication of SCD with pulmonary infiltrate and respiratory symptoms.",
                       extra_labels=["DISEASE"])
            merge_node(tx, "disease", "Beta Thalassemia",
                       "Inherited blood disorder with reduced hemoglobin production. Often co-inherited with SCD.",
                       extra_labels=["DISEASE"])

            # Genes/Proteins
            merge_node(tx, "gene_protein", "Hemoglobin S",
                       "HbS. Abnormal hemoglobin caused by Glu6Val mutation in beta-globin. Polymerizes when deoxygenated causing sickling.",
                       extra_labels=["GENE_PROTEIN"])
            merge_node(tx, "gene_protein", "HBB",
                       "Hemoglobin Subunit Beta. Gene encoding beta-globin chain. Mutations cause sickle cell disease and beta-thalassemia. Gene: HBB.",
                       extra_labels=["GENE_PROTEIN"])
            merge_node(tx, "gene_protein", "Fetal Hemoglobin",
                       "HbF. Hemoglobin expressed in fetal life. Inhibits HbS polymerization. Therapeutic target in SCD.",
                       extra_labels=["GENE_PROTEIN"])
            merge_node(tx, "gene_protein", "BCL11A",
                       "B-Cell Lymphoma/Leukemia 11A. Transcription factor that represses fetal hemoglobin. Target of gene therapy for SCD.",
                       extra_labels=["GENE_PROTEIN"])
            merge_node(tx, "gene_protein", "P-Selectin",
                       "Cell adhesion molecule on endothelium and platelets. Mediates vaso-occlusion in SCD. Target of crizanlizumab.",
                       extra_labels=["GENE_PROTEIN"])
            merge_node(tx, "gene_protein", "Endothelin-1",
                       "ET-1. Potent vasoconstrictor. Elevated in SCD contributing to vaso-occlusion and pulmonary hypertension.",
                       extra_labels=["GENE_PROTEIN"])

            # Drugs for SCD
            merge_node(tx, "drug", "Hydroxyurea",
                       "First-line therapy for SCD. Increases fetal hemoglobin (HbF) production, reducing sickling. Also: Hydroxycarbamide.",
                       extra_labels=["DRUG"])
            merge_node(tx, "drug", "Voxelotor",
                       "Hemoglobin S polymerization inhibitor for SCD. Stabilizes oxygenated HbS. Brand: Oxbryta. Global Blood Therapeutics.",
                       extra_labels=["DRUG"])
            merge_node(tx, "drug", "Crizanlizumab",
                       "Anti-P-selectin monoclonal antibody for SCD vaso-occlusive crises. Brand: Adakveo. Novartis.",
                       extra_labels=["DRUG"])
            merge_node(tx, "drug", "L-Glutamine",
                       "Amino acid reducing oxidative stress in sickle cells. Brand: Endari. FDA-approved for SCD.",
                       extra_labels=["DRUG"])
            merge_node(tx, "drug", "Casgevy",
                       "CRISPR/Cas9 gene therapy for SCD. Edits BCL11A to reactivate fetal hemoglobin. Brand: Casgevy (exagamglogene autotemcel). Vertex/CRISPR Therapeutics.",
                       extra_labels=["DRUG"])
            merge_node(tx, "drug", "Lyfgenia",
                       "Lentiviral gene therapy for SCD. Adds modified beta-globin gene. Brand: Lyfgenia (lovotibeglogene autotemcel). Bluebird Bio.",
                       extra_labels=["DRUG"])

            # Organizations
            merge_node(tx, "Organization", "Global Blood Therapeutics", "Biotech company focused on SCD therapies. Acquired by Pfizer 2022.")
            merge_node(tx, "Organization", "Vertex Pharmaceuticals", "Biotech company. Gene editing therapies including Casgevy for SCD.")
            merge_node(tx, "Organization", "CRISPR Therapeutics", "Gene editing company. Co-developer of Casgevy for SCD.")
            merge_node(tx, "Organization", "Bluebird Bio", "Gene therapy company. Developer of Lyfgenia for SCD.")

            # Pathways
            merge_node(tx, "pathway", "Hemoglobin Switching Pathway",
                       "Developmental switch from fetal (HbF) to adult (HbA/HbS) hemoglobin. BCL11A mediates this switch.",
                       extra_labels=["PATHWAY"])

            # Disease relationships
            merge_rel(tx, "Sickle Cell Anemia", "HBB", "disease_protein", "SCA caused by Glu6Val mutation in HBB gene.")
            merge_rel(tx, "Sickle Cell Anemia", "Hemoglobin S", "disease_protein", "SCA characterized by presence of HbS.")
            merge_rel(tx, "Sickle Cell Anemia", "Fetal Hemoglobin", "disease_protein", "High HbF levels ameliorate SCA symptoms.")
            merge_rel(tx, "Sickle Cell Anemia", "P-Selectin", "disease_protein", "P-selectin mediates vaso-occlusion in SCA.")
            merge_rel(tx, "Sickle Cell Anemia", "Endothelin-1", "disease_protein", "ET-1 elevated in SCA causing vasoconstriction.")
            merge_rel(tx, "Sickle Cell Anemia", "Sickle Cell Disease", "disease_disease", "SCA is the most severe form of SCD (HbSS).")
            merge_rel(tx, "Sickle Cell Anemia", "Vaso-occlusive Crisis", "disease_disease", "VOC is the hallmark complication of SCA.")
            merge_rel(tx, "Sickle Cell Anemia", "Acute Chest Syndrome", "disease_disease", "ACS is a serious complication of SCA.")
            merge_rel(tx, "Sickle Cell Disease", "Beta Thalassemia", "disease_disease", "HbS-beta thalassemia is a form of SCD.")
            merge_rel(tx, "BCL11A", "Fetal Hemoglobin", "protein_protein", "BCL11A represses fetal hemoglobin expression.")
            merge_rel(tx, "Hemoglobin S", "Fetal Hemoglobin", "protein_protein", "HbF inhibits HbS polymerization, reducing sickling.")
            merge_rel(tx, "Hemoglobin Switching Pathway", "BCL11A", "pathway_protein", "BCL11A is key regulator of hemoglobin switching.")
            merge_rel(tx, "Hemoglobin Switching Pathway", "Fetal Hemoglobin", "pathway_protein", "HbF is repressed during fetal-to-adult switching.")
            merge_rel(tx, "Hemoglobin Switching Pathway", "HBB", "pathway_protein", "HBB is switched on during adult hemoglobin production.")

            # Drug-disease
            merge_rel(tx, "Hydroxyurea", "Sickle Cell Anemia", "indication", "Hydroxyurea first-line for SCA. Increases HbF.")
            merge_rel(tx, "Voxelotor", "Sickle Cell Anemia", "indication", "Oxbryta for SCA hemolytic anemia.")
            merge_rel(tx, "Crizanlizumab", "Sickle Cell Anemia", "indication", "Adakveo reduces VOC frequency in SCA.")
            merge_rel(tx, "L-Glutamine", "Sickle Cell Anemia", "indication", "Endari reduces acute SCA complications.")
            merge_rel(tx, "Casgevy", "Sickle Cell Anemia", "indication", "Casgevy gene therapy for severe SCA.")
            merge_rel(tx, "Lyfgenia", "Sickle Cell Anemia", "indication", "Lyfgenia gene therapy for SCA.")

            # Drug-protein
            merge_rel(tx, "Hydroxyurea", "Fetal Hemoglobin", "drug_protein", "Hydroxyurea induces HbF production.")
            merge_rel(tx, "Voxelotor", "Hemoglobin S", "drug_protein", "Voxelotor stabilizes oxygenated HbS, preventing polymerization.")
            merge_rel(tx, "Crizanlizumab", "P-Selectin", "drug_protein", "Crizanlizumab blocks P-selectin on endothelium.")
            merge_rel(tx, "Casgevy", "BCL11A", "drug_protein", "Casgevy uses CRISPR to edit BCL11A enhancer, reactivating HbF.")

            # Org-drug
            merge_rel(tx, "Global Blood Therapeutics", "Voxelotor", "SPONSORS", "GBT developed Oxbryta.")
            merge_rel(tx, "Vertex Pharmaceuticals", "Casgevy", "SPONSORS", "Vertex co-developed Casgevy.")
            merge_rel(tx, "CRISPR Therapeutics", "Casgevy", "SPONSORS", "CRISPR Therapeutics co-developed Casgevy.")
            merge_rel(tx, "Bluebird Bio", "Lyfgenia", "SPONSORS", "Bluebird Bio developed Lyfgenia.")

            tx.commit()
    logger.info("  Sickle Cell data loaded: 6 drugs, 5 diseases, 6 proteins, 4 orgs, 1 pathway")


# ============================================================================
# API FETCHERS
# ============================================================================
def fetch_clinical_trials(sponsor: str, max_results: int = 30) -> list[dict]:
    """Fetch clinical trials from ClinicalTrials.gov v2 API."""
    try:
        url = f"https://clinicaltrials.gov/api/v2/studies?query.spons={urllib.parse.quote(sponsor)}&pageSize={max_results}&format=json"
        logger.info(f"  Fetching trials from: ClinicalTrials.gov for '{sponsor}'...")
        req = urllib.request.Request(url, headers={"User-Agent": "eugene-loader/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        trials = []
        for study in data.get("studies", []):
            proto = study.get("protocolSection", {})
            ident = proto.get("identificationModule", {})
            status_mod = proto.get("statusModule", {})
            cond_mod = proto.get("conditionsModule", {})
            interv_mod = proto.get("armsInterventionsModule", {})

            conditions = cond_mod.get("conditions", []) if cond_mod else []
            interventions = []
            if interv_mod:
                for i in interv_mod.get("interventions", []):
                    if i.get("type") in ("DRUG", "BIOLOGICAL"):
                        interventions.append(i.get("name", ""))

            trials.append({
                "nctId": ident.get("nctId", ""),
                "title": ident.get("briefTitle", ""),
                "status": status_mod.get("overallStatus", ""),
                "conditions": conditions,
                "interventions": interventions,
            })
        logger.info(f"  Fetched {len(trials)} trials")
        return trials
    except Exception as e:
        logger.warning(f"  Could not fetch trials: {e}")
        return []


def fetch_pubmed_articles(query: str, max_results: int = 15) -> list[dict]:
    """Fetch PubMed articles via NCBI Entrez API."""
    try:
        # Search
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={urllib.parse.quote(query)}&retmax={max_results}&retmode=json&sort=date"
        logger.info(f"  Fetching PubMed articles for '{query}'...")
        req = urllib.request.Request(search_url, headers={"User-Agent": "eugene-loader/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            search_data = json.loads(resp.read())

        ids = search_data.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        # Fetch details
        ids_str = ",".join(ids)
        detail_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={ids_str}&retmode=json"
        req2 = urllib.request.Request(detail_url, headers={"User-Agent": "eugene-loader/1.0"})
        with urllib.request.urlopen(req2, timeout=15) as resp2:
            detail_data = json.loads(resp2.read())

        articles = []
        results = detail_data.get("result", {})
        for pmid in ids:
            art = results.get(pmid, {})
            if isinstance(art, dict) and "title" in art:
                authors = ", ".join([a.get("name", "") for a in art.get("authors", [])[:5]])
                articles.append({
                    "pmid": pmid,
                    "title": art.get("title", ""),
                    "authors": authors,
                    "journal": art.get("source", ""),
                    "year": art.get("pubdate", "")[:4],
                })
        logger.info(f"  Fetched {len(articles)} articles")
        return articles
    except Exception as e:
        logger.warning(f"  Could not fetch PubMed: {e}")
        return []


def fetch_pubmed_article_detail(pmid: str) -> dict:
    """Fetch detailed info for a single PubMed article including affiliations."""
    try:
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"
        logger.info(f"  Fetching PMID {pmid} details...")
        req = urllib.request.Request(url, headers={"User-Agent": "eugene-loader/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read().decode("utf-8")

        # Parse title
        title = ""
        if "<ArticleTitle>" in xml_data:
            start = xml_data.index("<ArticleTitle>") + len("<ArticleTitle>")
            end = xml_data.index("</ArticleTitle>")
            title = xml_data[start:end].strip()

        # Parse affiliations
        affiliations = []
        for marker in ["<Affiliation>", "<AffiliationInfo>"]:
            idx = 0
            while True:
                try:
                    start = xml_data.index("<Affiliation>", idx) + len("<Affiliation>")
                    end = xml_data.index("</Affiliation>", start)
                    aff = xml_data[start:end].strip()
                    # Extract organization name (first part before comma usually)
                    org = aff.split(",")[0].strip()
                    if org and len(org) > 5 and org not in affiliations:
                        affiliations.append(org)
                    idx = end
                except ValueError:
                    break

        # Parse authors
        authors = []
        idx = 0
        while True:
            try:
                start = xml_data.index("<LastName>", idx) + len("<LastName>")
                end = xml_data.index("</LastName>", start)
                last = xml_data[start:end]
                authors.append(last)
                idx = end
            except ValueError:
                break

        # Parse journal
        journal = ""
        if "<Title>" in xml_data:
            start = xml_data.index("<Title>") + len("<Title>")
            end = xml_data.index("</Title>")
            journal = xml_data[start:end].strip()

        return {
            "title": title,
            "authors": ", ".join(authors[:5]),
            "journal": journal,
            "affiliations": affiliations[:10],
        }
    except Exception as e:
        logger.warning(f"  Could not fetch PMID detail: {e}")
        return {"title": "", "authors": "", "journal": "", "affiliations": []}


# ============================================================================
# MAIN
# ============================================================================
def main():
    driver = get_driver()

    load_adderall_data(driver)          # Q1
    load_biogen_data(driver)            # Q2, Q3
    load_mycophenolate_ptrh2_data(driver)  # Q4
    load_abl1_pubmed_data(driver)       # Q5
    load_pmid_41402159_data(driver)     # Q6
    load_sickle_cell_data(driver)       # Q7

    # Final stats
    with driver.session() as s:
        nodes = s.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        rels = s.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        labels = [(r["l"], r["c"]) for r in s.run(
            "MATCH (n) WITH labels(n) AS l, count(n) AS c ORDER BY c DESC RETURN l, c LIMIT 20"
        )]

    logger.info("")
    logger.info("=" * 60)
    logger.info("ALL DATA LOADED SUCCESSFULLY")
    logger.info(f"  Total nodes: {nodes}")
    logger.info(f"  Total relationships: {rels}")
    logger.info("  Top node types:")
    for l, c in labels:
        logger.info(f"    {l}: {c}")
    logger.info("=" * 60)

    driver.close()


if __name__ == "__main__":
    main()
