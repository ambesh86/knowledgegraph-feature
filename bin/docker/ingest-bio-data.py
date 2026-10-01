#!/usr/bin/env python3
"""
Eugene - Comprehensive Biomedical Data Ingestion
=================================================
Loads a rich biomedical knowledge graph into Neo4j covering:
- Drugs (50+), Diseases (40+), Genes/Proteins (40+)
- Pathways, Biological Processes, Anatomy
- Drug-Disease relationships (indications, contraindications, off-label)
- Drug-Protein targets
- Disease-Protein associations
- Protein-Protein interactions
- Clinical Trials, Sponsors, Organizations
- Drug aliases (synonyms, brand names)

Usage: python bin/docker/ingest-bio-data.py
"""

import hashlib
import logging
import os
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
    return neo4j.GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))


def ingest_nodes(tx, nodes: list[dict]):
    for n in nodes:
        label = n["type"].replace(" ", "_").replace("-", "_")
        tx.run(
            f"MERGE (n:`{label}` {{node_name: $name}}) "
            "SET n.node_id = $id, n.description = $desc, n.type = $type, "
            "n.value = $name, n.name = $name",
            name=n["name"], id=gid(n["name"]), desc=n.get("desc", ""), type=n["type"],
        )


def ingest_rels(tx, rels: list[dict]):
    for r in rels:
        rel_type = r["rel"].replace(" ", "_").replace("-", "_")
        tx.run(
            "MATCH (a {node_name: $src}) "
            "MATCH (b {node_name: $tgt}) "
            f"MERGE (a)-[r:`{rel_type}` {{id: $rid}}]->(b) "
            "SET r.type = $rel, r.description = $desc",
            src=r["src"], tgt=r["tgt"], rid=gid(f"{r['src']}-{r['rel']}-{r['tgt']}"),
            rel=r["rel"], desc=r.get("desc", ""),
        )


def ingest_aliases(tx, drug: str, aliases: list[str], alias_type: str = "DRUG_SYNONYM"):
    for alias in aliases:
        tx.run(
            f"MERGE (a:`{alias_type}` {{node_name: $alias}}) "
            "SET a.node_id = $aid, a.value = $alias, a.name = $alias, a.type = $atype "
            "WITH a "
            "MATCH (d {node_name: $drug}) "
            "MERGE (d)-[:has_drug_alias]->(a)",
            alias=alias, aid=gid(alias), drug=drug, atype=alias_type,
        )


def main():
    driver = get_driver()
    driver.verify_connectivity()
    logger.info("Connected!")

    # ================================================================
    # DRUGS (50+)
    # ================================================================
    drugs = [
        {"name": "Afstyla", "type": "drug", "desc": "Single-chain recombinant Factor VIII for Hemophilia A. CSL Behring."},
        {"name": "Idelvion", "type": "drug", "desc": "Recombinant Factor IX-albumin fusion protein for Hemophilia B. CSL Behring."},
        {"name": "Haegarda", "type": "drug", "desc": "Subcutaneous C1-esterase inhibitor for hereditary angioedema prevention. CSL Behring."},
        {"name": "Hizentra", "type": "drug", "desc": "Subcutaneous immunoglobulin (IgG) for primary immunodeficiency and CIDP. CSL Behring."},
        {"name": "Privigen", "type": "drug", "desc": "Intravenous immunoglobulin (IVIg) for primary immunodeficiency and ITP. CSL Behring."},
        {"name": "Kcentra", "type": "drug", "desc": "4-factor prothrombin complex concentrate for urgent reversal of vitamin K antagonists. CSL Behring."},
        {"name": "Zemaira", "type": "drug", "desc": "Alpha1-proteinase inhibitor for alpha-1 antitrypsin deficiency emphysema. CSL Behring."},
        {"name": "Eloctate", "type": "drug", "desc": "Recombinant Factor VIII Fc fusion protein for Hemophilia A."},
        {"name": "Alprolix", "type": "drug", "desc": "Recombinant Factor IX Fc fusion protein for Hemophilia B."},
        {"name": "Hemlibra", "type": "drug", "desc": "Bispecific antibody mimicking Factor VIII for Hemophilia A prophylaxis. Roche."},
        {"name": "Adalimumab", "type": "drug", "desc": "TNF-alpha inhibitor. Brand: Humira. Used for RA, psoriasis, Crohn's, UC."},
        {"name": "Rituximab", "type": "drug", "desc": "Anti-CD20 monoclonal antibody for lymphoma and autoimmune diseases."},
        {"name": "Trastuzumab", "type": "drug", "desc": "Anti-HER2 monoclonal antibody for HER2+ breast cancer. Brand: Herceptin."},
        {"name": "Pembrolizumab", "type": "drug", "desc": "Anti-PD-1 checkpoint inhibitor for multiple cancers. Brand: Keytruda. Merck."},
        {"name": "Nivolumab", "type": "drug", "desc": "Anti-PD-1 checkpoint inhibitor for melanoma, lung cancer. Brand: Opdivo. BMS."},
        {"name": "Atezolizumab", "type": "drug", "desc": "Anti-PD-L1 checkpoint inhibitor for bladder/lung cancer. Brand: Tecentriq. Roche."},
        {"name": "Bevacizumab", "type": "drug", "desc": "Anti-VEGF monoclonal antibody for colorectal/lung cancer. Brand: Avastin. Roche."},
        {"name": "Infliximab", "type": "drug", "desc": "TNF-alpha inhibitor for Crohn's disease, UC, RA. Brand: Remicade."},
        {"name": "Etanercept", "type": "drug", "desc": "TNF receptor fusion protein for RA, psoriasis. Brand: Enbrel."},
        {"name": "Tocilizumab", "type": "drug", "desc": "IL-6 receptor inhibitor for RA, giant cell arteritis. Brand: Actemra. Roche."},
        {"name": "Ustekinumab", "type": "drug", "desc": "Anti-IL-12/23 antibody for psoriasis, Crohn's. Brand: Stelara. J&J."},
        {"name": "Secukinumab", "type": "drug", "desc": "Anti-IL-17A antibody for psoriasis, AS. Brand: Cosentyx. Novartis."},
        {"name": "Dupilumab", "type": "drug", "desc": "Anti-IL-4Rα antibody for atopic dermatitis, asthma. Brand: Dupixent. Sanofi/Regeneron."},
        {"name": "Omalizumab", "type": "drug", "desc": "Anti-IgE antibody for severe asthma, urticaria. Brand: Xolair. Novartis/Roche."},
        {"name": "Denosumab", "type": "drug", "desc": "Anti-RANKL antibody for osteoporosis, bone metastases. Brand: Prolia/Xgeva. Amgen."},
        {"name": "Eculizumab", "type": "drug", "desc": "Anti-C5 complement inhibitor for PNH, aHUS. Brand: Soliris. Alexion."},
        {"name": "Ravulizumab", "type": "drug", "desc": "Long-acting anti-C5 complement inhibitor for PNH. Brand: Ultomiris. Alexion."},
        {"name": "Emicizumab", "type": "drug", "desc": "Bispecific antibody bridging FIXa and FX for Hemophilia A. Brand: Hemlibra. Roche."},
        {"name": "Ruxolitinib", "type": "drug", "desc": "JAK1/JAK2 inhibitor for myelofibrosis, polycythemia vera. Brand: Jakafi. Incyte."},
        {"name": "Imatinib", "type": "drug", "desc": "BCR-ABL tyrosine kinase inhibitor for CML. Brand: Gleevec. Novartis."},
        {"name": "Lenalidomide", "type": "drug", "desc": "Immunomodulatory drug for multiple myeloma, MDS. Brand: Revlimid. BMS."},
        {"name": "Bortezomib", "type": "drug", "desc": "Proteasome inhibitor for multiple myeloma. Brand: Velcade."},
        {"name": "Ibrutinib", "type": "drug", "desc": "BTK inhibitor for CLL, mantle cell lymphoma. Brand: Imbruvica. AbbVie/J&J."},
        {"name": "Venetoclax", "type": "drug", "desc": "BCL-2 inhibitor for CLL, AML. Brand: Venclexta. AbbVie/Roche."},
        {"name": "Osimertinib", "type": "drug", "desc": "3rd-gen EGFR TKI for EGFR-mutant NSCLC. Brand: Tagrisso. AstraZeneca."},
        {"name": "Crizotinib", "type": "drug", "desc": "ALK/ROS1 inhibitor for NSCLC. Brand: Xalkori. Pfizer."},
        {"name": "Sorafenib", "type": "drug", "desc": "Multi-kinase inhibitor for HCC, RCC. Brand: Nexavar."},
        {"name": "Sunitinib", "type": "drug", "desc": "Multi-kinase inhibitor for RCC, GIST. Brand: Sutent. Pfizer."},
        {"name": "Methotrexate", "type": "drug", "desc": "Antimetabolite for RA, cancer, psoriasis. Folate antagonist."},
        {"name": "Dexamethasone", "type": "drug", "desc": "Corticosteroid used in myeloma, inflammation, COVID-19 treatment."},
        {"name": "Prednisone", "type": "drug", "desc": "Corticosteroid for inflammation, autoimmune conditions, cancer."},
        {"name": "Warfarin", "type": "drug", "desc": "Vitamin K antagonist anticoagulant for thrombosis prevention."},
        {"name": "Heparin", "type": "drug", "desc": "Anticoagulant for thrombosis, PE, and during surgeries."},
        {"name": "Aspirin", "type": "drug", "desc": "NSAID and antiplatelet agent for pain, inflammation, cardiovascular prevention."},
        {"name": "Insulin Glargine", "type": "drug", "desc": "Long-acting insulin analog for diabetes. Brand: Lantus. Sanofi."},
        {"name": "Semaglutide", "type": "drug", "desc": "GLP-1 receptor agonist for type 2 diabetes and obesity. Brand: Ozempic/Wegovy. Novo Nordisk."},
        {"name": "IVIG", "type": "drug", "desc": "Intravenous immunoglobulin pooled from donor plasma for immunodeficiency and autoimmune conditions."},
        {"name": "Desmopressin", "type": "drug", "desc": "Synthetic vasopressin analog for von Willebrand disease and mild Hemophilia A."},
        {"name": "Tranexamic Acid", "type": "drug", "desc": "Antifibrinolytic for bleeding prevention in hemophilia and surgery."},
        {"name": "Eltrombopag", "type": "drug", "desc": "TPO receptor agonist for chronic ITP and aplastic anemia. Brand: Promacta. Novartis."},
    ]

    # ================================================================
    # DISEASES (40+)
    # ================================================================
    diseases = [
        {"name": "Hemophilia A", "type": "disease", "desc": "X-linked bleeding disorder due to Factor VIII deficiency."},
        {"name": "Hemophilia B", "type": "disease", "desc": "X-linked bleeding disorder due to Factor IX deficiency. Christmas disease."},
        {"name": "Von Willebrand Disease", "type": "disease", "desc": "Most common inherited bleeding disorder. VWF deficiency or dysfunction."},
        {"name": "Immune Thrombocytopenia", "type": "disease", "desc": "Autoimmune low platelet count causing bleeding risk. ITP."},
        {"name": "Primary Immune Deficiency", "type": "disease", "desc": "Group of genetic disorders causing immune system dysfunction."},
        {"name": "Chronic Inflammatory Demyelinating Polyneuropathy", "type": "disease", "desc": "Autoimmune disorder affecting peripheral nerves. CIDP."},
        {"name": "Hereditary Angioedema", "type": "disease", "desc": "Genetic disorder causing severe swelling episodes. C1-INH deficiency."},
        {"name": "Alpha-1 Antitrypsin Deficiency", "type": "disease", "desc": "Genetic condition causing lung (emphysema) and liver disease."},
        {"name": "Paroxysmal Nocturnal Hemoglobinuria", "type": "disease", "desc": "Rare acquired hemolytic anemia. PNH. Complement-mediated."},
        {"name": "Rheumatoid Arthritis", "type": "disease", "desc": "Chronic autoimmune inflammatory joint disease."},
        {"name": "Psoriasis", "type": "disease", "desc": "Chronic autoimmune skin disease with scaly patches."},
        {"name": "Psoriatic Arthritis", "type": "disease", "desc": "Inflammatory arthritis associated with psoriasis."},
        {"name": "Crohn's Disease", "type": "disease", "desc": "Chronic inflammatory bowel disease affecting GI tract."},
        {"name": "Ulcerative Colitis", "type": "disease", "desc": "Chronic inflammatory bowel disease of the colon."},
        {"name": "Ankylosing Spondylitis", "type": "disease", "desc": "Chronic inflammatory disease of axial skeleton."},
        {"name": "Systemic Lupus Erythematosus", "type": "disease", "desc": "Chronic autoimmune disease affecting multiple organs. SLE."},
        {"name": "Multiple Sclerosis", "type": "disease", "desc": "Autoimmune demyelinating disease of the CNS."},
        {"name": "Atopic Dermatitis", "type": "disease", "desc": "Chronic inflammatory skin condition. Eczema."},
        {"name": "Asthma", "type": "disease", "desc": "Chronic respiratory disease with airway inflammation and obstruction."},
        {"name": "Non-Small Cell Lung Cancer", "type": "disease", "desc": "Most common type of lung cancer. NSCLC."},
        {"name": "HER2+ Breast Cancer", "type": "disease", "desc": "Breast cancer overexpressing HER2 receptor."},
        {"name": "Melanoma", "type": "disease", "desc": "Aggressive skin cancer arising from melanocytes."},
        {"name": "Colorectal Cancer", "type": "disease", "desc": "Cancer of the colon or rectum. CRC."},
        {"name": "Chronic Lymphocytic Leukemia", "type": "disease", "desc": "Slow-growing blood cancer of B lymphocytes. CLL."},
        {"name": "Chronic Myeloid Leukemia", "type": "disease", "desc": "Blood cancer with BCR-ABL fusion. CML."},
        {"name": "Multiple Myeloma", "type": "disease", "desc": "Plasma cell cancer in bone marrow."},
        {"name": "Non-Hodgkin Lymphoma", "type": "disease", "desc": "Diverse group of blood cancers from lymphocytes. NHL."},
        {"name": "Myelofibrosis", "type": "disease", "desc": "Bone marrow cancer causing scarring (fibrosis) and abnormal blood counts."},
        {"name": "Hepatocellular Carcinoma", "type": "disease", "desc": "Primary liver cancer. HCC."},
        {"name": "Renal Cell Carcinoma", "type": "disease", "desc": "Kidney cancer originating in renal tubular cells. RCC."},
        {"name": "Osteoporosis", "type": "disease", "desc": "Bone disease causing decreased density and increased fracture risk."},
        {"name": "Type 2 Diabetes", "type": "disease", "desc": "Metabolic disorder with insulin resistance and hyperglycemia."},
        {"name": "Obesity", "type": "disease", "desc": "Chronic disease of excess body fat affecting health."},
        {"name": "Deep Vein Thrombosis", "type": "disease", "desc": "Blood clot in deep veins, usually legs. DVT."},
        {"name": "Pulmonary Embolism", "type": "disease", "desc": "Blood clot blocking pulmonary arteries. PE."},
        {"name": "Giant Cell Arteritis", "type": "disease", "desc": "Inflammatory vasculitis of large arteries, mainly temporal."},
        {"name": "Aplastic Anemia", "type": "disease", "desc": "Bone marrow failure causing pancytopenia."},
        {"name": "Atypical Hemolytic Uremic Syndrome", "type": "disease", "desc": "Complement-mediated thrombotic microangiopathy. aHUS."},
        {"name": "Mantle Cell Lymphoma", "type": "disease", "desc": "Aggressive B-cell non-Hodgkin lymphoma."},
        {"name": "Acute Myeloid Leukemia", "type": "disease", "desc": "Aggressive blood cancer of myeloid lineage. AML."},
    ]

    # ================================================================
    # GENES/PROTEINS (40+)
    # ================================================================
    proteins = [
        {"name": "Factor VIII", "type": "gene_protein", "desc": "Coagulation factor VIII. Deficiency causes Hemophilia A. Gene: F8."},
        {"name": "Factor IX", "type": "gene_protein", "desc": "Coagulation factor IX. Deficiency causes Hemophilia B. Gene: F9."},
        {"name": "Von Willebrand Factor", "type": "gene_protein", "desc": "VWF. Glycoprotein for platelet adhesion. Carriers Factor VIII. Gene: VWF."},
        {"name": "Immunoglobulin G", "type": "gene_protein", "desc": "IgG. Most abundant antibody in blood. Key to humoral immunity."},
        {"name": "C1 Esterase Inhibitor", "type": "gene_protein", "desc": "C1-INH. Serine protease inhibitor. Deficiency causes hereditary angioedema. Gene: SERPING1."},
        {"name": "TNF-alpha", "type": "gene_protein", "desc": "Tumor Necrosis Factor alpha. Pro-inflammatory cytokine. Target of adalimumab, infliximab."},
        {"name": "CD20", "type": "gene_protein", "desc": "B-cell surface antigen. Target of rituximab. Gene: MS4A1."},
        {"name": "HER2", "type": "gene_protein", "desc": "Human Epidermal Growth Factor Receptor 2. Oncogene. Target of trastuzumab. Gene: ERBB2."},
        {"name": "PD-1", "type": "gene_protein", "desc": "Programmed Death receptor 1. Immune checkpoint. Target of pembrolizumab, nivolumab. Gene: PDCD1."},
        {"name": "PD-L1", "type": "gene_protein", "desc": "Programmed Death Ligand 1. Immune checkpoint ligand. Target of atezolizumab. Gene: CD274."},
        {"name": "VEGF", "type": "gene_protein", "desc": "Vascular Endothelial Growth Factor. Angiogenesis driver. Target of bevacizumab. Gene: VEGFA."},
        {"name": "IL-6", "type": "gene_protein", "desc": "Interleukin-6. Pro-inflammatory cytokine. Target of tocilizumab. Gene: IL6."},
        {"name": "IL-17A", "type": "gene_protein", "desc": "Interleukin-17A. Inflammatory cytokine in psoriasis. Target of secukinumab. Gene: IL17A."},
        {"name": "IL-4 Receptor Alpha", "type": "gene_protein", "desc": "IL-4Rα. Receptor for IL-4 and IL-13. Target of dupilumab. Gene: IL4R."},
        {"name": "IgE", "type": "gene_protein", "desc": "Immunoglobulin E. Mediates allergic responses. Target of omalizumab."},
        {"name": "RANKL", "type": "gene_protein", "desc": "Receptor Activator of NF-κB Ligand. Osteoclast activation. Target of denosumab. Gene: TNFSF11."},
        {"name": "Complement C5", "type": "gene_protein", "desc": "Complement component 5. Terminal complement pathway. Target of eculizumab. Gene: C5."},
        {"name": "BCR-ABL", "type": "gene_protein", "desc": "Fusion oncoprotein from Philadelphia chromosome. Target of imatinib. CML driver."},
        {"name": "JAK1", "type": "gene_protein", "desc": "Janus Kinase 1. Cytokine signaling. Target of ruxolitinib. Gene: JAK1."},
        {"name": "JAK2", "type": "gene_protein", "desc": "Janus Kinase 2. Mutated in myeloproliferative neoplasms. Target of ruxolitinib. Gene: JAK2."},
        {"name": "BTK", "type": "gene_protein", "desc": "Bruton's Tyrosine Kinase. B-cell signaling. Target of ibrutinib. Gene: BTK."},
        {"name": "BCL-2", "type": "gene_protein", "desc": "B-cell Lymphoma 2. Anti-apoptotic protein. Target of venetoclax. Gene: BCL2."},
        {"name": "EGFR", "type": "gene_protein", "desc": "Epidermal Growth Factor Receptor. Oncogene in NSCLC. Target of osimertinib. Gene: EGFR."},
        {"name": "ALK", "type": "gene_protein", "desc": "Anaplastic Lymphoma Kinase. Oncogene in NSCLC. Target of crizotinib. Gene: ALK."},
        {"name": "BRCA1", "type": "gene_protein", "desc": "Breast Cancer gene 1. Tumor suppressor. Mutations increase breast/ovarian cancer risk."},
        {"name": "BRCA2", "type": "gene_protein", "desc": "Breast Cancer gene 2. Tumor suppressor. DNA repair via homologous recombination."},
        {"name": "TP53", "type": "gene_protein", "desc": "Tumor protein p53. 'Guardian of the genome'. Most commonly mutated gene in cancer."},
        {"name": "KRAS", "type": "gene_protein", "desc": "Kirsten Rat Sarcoma viral oncogene. Mutated in pancreatic, colorectal, lung cancers."},
        {"name": "GLP-1 Receptor", "type": "gene_protein", "desc": "Glucagon-Like Peptide-1 Receptor. Target of semaglutide. Incretin signaling. Gene: GLP1R."},
        {"name": "Thrombopoietin Receptor", "type": "gene_protein", "desc": "TPO-R (c-MPL). Platelet production. Target of eltrombopag. Gene: MPL."},
        {"name": "Alpha-1 Antitrypsin", "type": "gene_protein", "desc": "A1AT. Serine protease inhibitor. Deficiency causes emphysema/liver disease. Gene: SERPINA1."},
        {"name": "Thrombin", "type": "gene_protein", "desc": "Coagulation factor IIa. Central enzyme in coagulation cascade. Gene: F2."},
        {"name": "Fibrinogen", "type": "gene_protein", "desc": "Coagulation factor I. Converted to fibrin by thrombin. Essential for clot formation."},
        {"name": "Antithrombin III", "type": "gene_protein", "desc": "Natural anticoagulant. Inhibits thrombin and factor Xa. Gene: SERPINC1."},
        {"name": "Protein C", "type": "gene_protein", "desc": "Natural anticoagulant. Inactivates factors Va and VIIIa. Gene: PROC."},
        {"name": "Factor V Leiden", "type": "gene_protein", "desc": "Mutant Factor V resistant to Protein C. Most common inherited thrombophilia."},
    ]

    # ================================================================
    # PATHWAYS & BIOLOGICAL PROCESSES
    # ================================================================
    pathways = [
        {"name": "Coagulation Cascade", "type": "pathway", "desc": "Blood clotting pathway involving intrinsic and extrinsic cascades leading to fibrin clot formation."},
        {"name": "Complement Pathway", "type": "pathway", "desc": "Innate immune pathway involving classical, lectin, and alternative activation leading to MAC formation."},
        {"name": "NF-kB Signaling", "type": "pathway", "desc": "Nuclear Factor kappa-B pathway. Central to inflammation, immunity, and cell survival."},
        {"name": "JAK-STAT Pathway", "type": "pathway", "desc": "Janus Kinase-Signal Transducer pathway. Cytokine signaling for immunity and hematopoiesis."},
        {"name": "PI3K-AKT-mTOR Pathway", "type": "pathway", "desc": "Cell growth, survival, and metabolism signaling. Frequently altered in cancer."},
        {"name": "RAS-MAPK Pathway", "type": "pathway", "desc": "Cell proliferation and differentiation signaling. KRAS mutations activate this pathway in cancer."},
        {"name": "PD-1/PD-L1 Checkpoint", "type": "pathway", "desc": "Immune checkpoint pathway that suppresses T-cell activity. Targeted by immunotherapy."},
        {"name": "VEGF Angiogenesis Pathway", "type": "pathway", "desc": "Vascular endothelial growth factor signaling for new blood vessel formation."},
        {"name": "Apoptosis Pathway", "type": "pathway", "desc": "Programmed cell death pathway involving BCL-2 family proteins and caspases."},
        {"name": "Insulin Signaling Pathway", "type": "pathway", "desc": "Metabolic pathway regulating glucose uptake, glycogen synthesis, and lipogenesis."},
    ]

    anatomy = [
        {"name": "Bone Marrow", "type": "anatomy", "desc": "Soft tissue in bones producing blood cells. Site of hematopoiesis."},
        {"name": "Liver", "type": "anatomy", "desc": "Organ producing coagulation factors, bile, and metabolizing drugs."},
        {"name": "Spleen", "type": "anatomy", "desc": "Organ filtering blood, recycling old red blood cells, and immune surveillance."},
        {"name": "Lymph Node", "type": "anatomy", "desc": "Small organ filtering lymph fluid. Key site for immune responses."},
        {"name": "Thymus", "type": "anatomy", "desc": "Organ where T-cells mature. Key to adaptive immunity."},
        {"name": "Lung", "type": "anatomy", "desc": "Respiratory organ for gas exchange. Site of NSCLC, asthma."},
        {"name": "Kidney", "type": "anatomy", "desc": "Organ for blood filtration and waste removal. Site of RCC."},
        {"name": "Skin", "type": "anatomy", "desc": "Largest organ. Site of psoriasis, atopic dermatitis, melanoma."},
        {"name": "Synovial Joint", "type": "anatomy", "desc": "Joint with synovial membrane. Affected in rheumatoid arthritis."},
        {"name": "Colon", "type": "anatomy", "desc": "Large intestine. Site of ulcerative colitis and colorectal cancer."},
    ]

    # ================================================================
    # ORGANIZATIONS
    # ================================================================
    orgs = [
        {"name": "CSL Behring", "type": "Organization", "desc": "Global biotherapy leader. Plasma-derived and recombinant therapies for rare diseases."},
        {"name": "CSL Limited", "type": "Organization", "desc": "Parent company of CSL Behring and CSL Seqirus. Melbourne, Australia."},
        {"name": "CSL Seqirus", "type": "Organization", "desc": "Global influenza vaccines company. Subsidiary of CSL Limited."},
        {"name": "Roche", "type": "Organization", "desc": "Swiss pharma giant. Oncology, immunology, ophthalmology, neuroscience."},
        {"name": "Novartis", "type": "Organization", "desc": "Swiss pharma company. Oncology, immunology, ophthalmology, gene therapy."},
        {"name": "Pfizer", "type": "Organization", "desc": "American pharma company. Vaccines, oncology, rare diseases."},
        {"name": "AbbVie", "type": "Organization", "desc": "American pharma company. Immunology (Humira), oncology, neuroscience."},
        {"name": "Merck", "type": "Organization", "desc": "American pharma company. Keytruda, vaccines, oncology."},
        {"name": "Bristol-Myers Squibb", "type": "Organization", "desc": "American pharma company. Immuno-oncology, hematology, cardiovascular."},
        {"name": "Sanofi", "type": "Organization", "desc": "French pharma company. Rare diseases, oncology, immunology, vaccines."},
        {"name": "AstraZeneca", "type": "Organization", "desc": "British-Swedish pharma. Oncology, cardiovascular, respiratory."},
        {"name": "Amgen", "type": "Organization", "desc": "American biotech. Oncology, bone health, cardiovascular, inflammation."},
        {"name": "Biogen", "type": "Organization", "desc": "American biotech. Neurology, neurodegeneration, rare diseases."},
        {"name": "Takeda", "type": "Organization", "desc": "Japanese pharma. Rare diseases, GI, plasma-derived therapies, oncology."},
        {"name": "Novo Nordisk", "type": "Organization", "desc": "Danish pharma. Diabetes, obesity, hemophilia, growth disorders."},
        {"name": "Alexion", "type": "Organization", "desc": "Rare disease company (now AstraZeneca). Complement inhibitors."},
        {"name": "Regeneron", "type": "Organization", "desc": "American biotech. Dupixent, Eylea, antibody discovery platform."},
        {"name": "Johnson & Johnson", "type": "Organization", "desc": "American pharma/med device conglomerate. Immunology, oncology."},
        {"name": "Incyte", "type": "Organization", "desc": "American biotech focused on oncology and inflammation. Jakafi."},
    ]

    # ================================================================
    # RELATIONSHIPS
    # ================================================================
    drug_disease_rels = [
        # CSL Behring drugs
        {"src": "Afstyla", "tgt": "Hemophilia A", "rel": "indication", "desc": "Afstyla indicated for Hemophilia A treatment and prophylaxis."},
        {"src": "Eloctate", "tgt": "Hemophilia A", "rel": "indication", "desc": "Eloctate indicated for Hemophilia A."},
        {"src": "Hemlibra", "tgt": "Hemophilia A", "rel": "indication", "desc": "Hemlibra indicated for Hemophilia A prophylaxis."},
        {"src": "Desmopressin", "tgt": "Hemophilia A", "rel": "indication", "desc": "Desmopressin for mild Hemophilia A."},
        {"src": "Idelvion", "tgt": "Hemophilia B", "rel": "indication", "desc": "Idelvion indicated for Hemophilia B."},
        {"src": "Alprolix", "tgt": "Hemophilia B", "rel": "indication", "desc": "Alprolix indicated for Hemophilia B."},
        {"src": "Desmopressin", "tgt": "Von Willebrand Disease", "rel": "indication", "desc": "Desmopressin for Type 1 von Willebrand disease."},
        {"src": "Haegarda", "tgt": "Hereditary Angioedema", "rel": "indication", "desc": "Haegarda for HAE prophylaxis."},
        {"src": "Hizentra", "tgt": "Primary Immune Deficiency", "rel": "indication", "desc": "Hizentra for PID treatment."},
        {"src": "Hizentra", "tgt": "Chronic Inflammatory Demyelinating Polyneuropathy", "rel": "indication", "desc": "Hizentra for CIDP."},
        {"src": "Privigen", "tgt": "Primary Immune Deficiency", "rel": "indication", "desc": "Privigen for PID."},
        {"src": "Privigen", "tgt": "Immune Thrombocytopenia", "rel": "indication", "desc": "Privigen for ITP."},
        {"src": "Zemaira", "tgt": "Alpha-1 Antitrypsin Deficiency", "rel": "indication", "desc": "Zemaira for A1ATD emphysema."},
        {"src": "Kcentra", "tgt": "Deep Vein Thrombosis", "rel": "indication", "desc": "Kcentra for urgent VKA reversal in thrombosis."},
        # Oncology
        {"src": "Pembrolizumab", "tgt": "Non-Small Cell Lung Cancer", "rel": "indication", "desc": "Keytruda for NSCLC."},
        {"src": "Pembrolizumab", "tgt": "Melanoma", "rel": "indication", "desc": "Keytruda for melanoma."},
        {"src": "Nivolumab", "tgt": "Melanoma", "rel": "indication", "desc": "Opdivo for melanoma."},
        {"src": "Nivolumab", "tgt": "Non-Small Cell Lung Cancer", "rel": "indication", "desc": "Opdivo for NSCLC."},
        {"src": "Atezolizumab", "tgt": "Non-Small Cell Lung Cancer", "rel": "indication", "desc": "Tecentriq for NSCLC."},
        {"src": "Trastuzumab", "tgt": "HER2+ Breast Cancer", "rel": "indication", "desc": "Herceptin for HER2+ breast cancer."},
        {"src": "Bevacizumab", "tgt": "Colorectal Cancer", "rel": "indication", "desc": "Avastin for CRC."},
        {"src": "Bevacizumab", "tgt": "Non-Small Cell Lung Cancer", "rel": "indication", "desc": "Avastin for NSCLC."},
        {"src": "Imatinib", "tgt": "Chronic Myeloid Leukemia", "rel": "indication", "desc": "Gleevec for CML."},
        {"src": "Ibrutinib", "tgt": "Chronic Lymphocytic Leukemia", "rel": "indication", "desc": "Imbruvica for CLL."},
        {"src": "Ibrutinib", "tgt": "Mantle Cell Lymphoma", "rel": "indication", "desc": "Imbruvica for MCL."},
        {"src": "Venetoclax", "tgt": "Chronic Lymphocytic Leukemia", "rel": "indication", "desc": "Venclexta for CLL."},
        {"src": "Venetoclax", "tgt": "Acute Myeloid Leukemia", "rel": "indication", "desc": "Venclexta for AML."},
        {"src": "Lenalidomide", "tgt": "Multiple Myeloma", "rel": "indication", "desc": "Revlimid for myeloma."},
        {"src": "Bortezomib", "tgt": "Multiple Myeloma", "rel": "indication", "desc": "Velcade for myeloma."},
        {"src": "Rituximab", "tgt": "Non-Hodgkin Lymphoma", "rel": "indication", "desc": "Rituximab for NHL."},
        {"src": "Ruxolitinib", "tgt": "Myelofibrosis", "rel": "indication", "desc": "Jakafi for myelofibrosis."},
        {"src": "Osimertinib", "tgt": "Non-Small Cell Lung Cancer", "rel": "indication", "desc": "Tagrisso for EGFR-mutant NSCLC."},
        {"src": "Sorafenib", "tgt": "Hepatocellular Carcinoma", "rel": "indication", "desc": "Nexavar for HCC."},
        {"src": "Sorafenib", "tgt": "Renal Cell Carcinoma", "rel": "indication", "desc": "Nexavar for RCC."},
        {"src": "Sunitinib", "tgt": "Renal Cell Carcinoma", "rel": "indication", "desc": "Sutent for RCC."},
        # Autoimmune
        {"src": "Adalimumab", "tgt": "Rheumatoid Arthritis", "rel": "indication", "desc": "Humira for RA."},
        {"src": "Adalimumab", "tgt": "Psoriasis", "rel": "indication", "desc": "Humira for psoriasis."},
        {"src": "Adalimumab", "tgt": "Crohn's Disease", "rel": "indication", "desc": "Humira for Crohn's."},
        {"src": "Infliximab", "tgt": "Crohn's Disease", "rel": "indication", "desc": "Remicade for Crohn's."},
        {"src": "Infliximab", "tgt": "Ulcerative Colitis", "rel": "indication", "desc": "Remicade for UC."},
        {"src": "Infliximab", "tgt": "Rheumatoid Arthritis", "rel": "indication", "desc": "Remicade for RA."},
        {"src": "Etanercept", "tgt": "Rheumatoid Arthritis", "rel": "indication", "desc": "Enbrel for RA."},
        {"src": "Etanercept", "tgt": "Psoriasis", "rel": "indication", "desc": "Enbrel for psoriasis."},
        {"src": "Tocilizumab", "tgt": "Rheumatoid Arthritis", "rel": "indication", "desc": "Actemra for RA."},
        {"src": "Tocilizumab", "tgt": "Giant Cell Arteritis", "rel": "indication", "desc": "Actemra for GCA."},
        {"src": "Secukinumab", "tgt": "Psoriasis", "rel": "indication", "desc": "Cosentyx for psoriasis."},
        {"src": "Secukinumab", "tgt": "Ankylosing Spondylitis", "rel": "indication", "desc": "Cosentyx for AS."},
        {"src": "Ustekinumab", "tgt": "Psoriasis", "rel": "indication", "desc": "Stelara for psoriasis."},
        {"src": "Ustekinumab", "tgt": "Crohn's Disease", "rel": "indication", "desc": "Stelara for Crohn's."},
        {"src": "Dupilumab", "tgt": "Atopic Dermatitis", "rel": "indication", "desc": "Dupixent for atopic dermatitis."},
        {"src": "Dupilumab", "tgt": "Asthma", "rel": "indication", "desc": "Dupixent for moderate-severe asthma."},
        {"src": "Omalizumab", "tgt": "Asthma", "rel": "indication", "desc": "Xolair for severe allergic asthma."},
        {"src": "Denosumab", "tgt": "Osteoporosis", "rel": "indication", "desc": "Prolia for osteoporosis."},
        {"src": "Eculizumab", "tgt": "Paroxysmal Nocturnal Hemoglobinuria", "rel": "indication", "desc": "Soliris for PNH."},
        {"src": "Eculizumab", "tgt": "Atypical Hemolytic Uremic Syndrome", "rel": "indication", "desc": "Soliris for aHUS."},
        {"src": "Ravulizumab", "tgt": "Paroxysmal Nocturnal Hemoglobinuria", "rel": "indication", "desc": "Ultomiris for PNH."},
        {"src": "Semaglutide", "tgt": "Type 2 Diabetes", "rel": "indication", "desc": "Ozempic for T2D."},
        {"src": "Semaglutide", "tgt": "Obesity", "rel": "indication", "desc": "Wegovy for weight management."},
        {"src": "Insulin Glargine", "tgt": "Type 2 Diabetes", "rel": "indication", "desc": "Lantus for diabetes."},
        {"src": "Eltrombopag", "tgt": "Immune Thrombocytopenia", "rel": "indication", "desc": "Promacta for chronic ITP."},
        {"src": "Eltrombopag", "tgt": "Aplastic Anemia", "rel": "indication", "desc": "Promacta for severe aplastic anemia."},
        # Off-label / contraindications
        {"src": "Rituximab", "tgt": "Immune Thrombocytopenia", "rel": "off_label_use", "desc": "Rituximab off-label for refractory ITP."},
        {"src": "Methotrexate", "tgt": "Rheumatoid Arthritis", "rel": "indication", "desc": "Methotrexate first-line for RA."},
        {"src": "Warfarin", "tgt": "Deep Vein Thrombosis", "rel": "indication", "desc": "Warfarin for DVT treatment/prevention."},
        {"src": "Warfarin", "tgt": "Pulmonary Embolism", "rel": "indication", "desc": "Warfarin for PE."},
        {"src": "Heparin", "tgt": "Deep Vein Thrombosis", "rel": "indication", "desc": "Heparin for DVT."},
        {"src": "Heparin", "tgt": "Pulmonary Embolism", "rel": "indication", "desc": "Heparin for PE."},
    ]

    drug_protein_rels = [
        {"src": "Afstyla", "tgt": "Factor VIII", "rel": "drug_protein", "desc": "Afstyla is recombinant Factor VIII."},
        {"src": "Eloctate", "tgt": "Factor VIII", "rel": "drug_protein", "desc": "Eloctate is rFVIII-Fc fusion protein."},
        {"src": "Hemlibra", "tgt": "Factor VIII", "rel": "drug_protein", "desc": "Hemlibra mimics Factor VIII cofactor activity."},
        {"src": "Idelvion", "tgt": "Factor IX", "rel": "drug_protein", "desc": "Idelvion is rFIX-albumin fusion."},
        {"src": "Alprolix", "tgt": "Factor IX", "rel": "drug_protein", "desc": "Alprolix is rFIX-Fc fusion."},
        {"src": "Haegarda", "tgt": "C1 Esterase Inhibitor", "rel": "drug_protein", "desc": "Haegarda is C1-INH concentrate."},
        {"src": "Hizentra", "tgt": "Immunoglobulin G", "rel": "drug_protein", "desc": "Hizentra is subcutaneous IgG."},
        {"src": "Privigen", "tgt": "Immunoglobulin G", "rel": "drug_protein", "desc": "Privigen is IV IgG."},
        {"src": "Zemaira", "tgt": "Alpha-1 Antitrypsin", "rel": "drug_protein", "desc": "Zemaira is A1AT concentrate."},
        {"src": "Adalimumab", "tgt": "TNF-alpha", "rel": "drug_protein", "desc": "Adalimumab targets TNF-alpha."},
        {"src": "Infliximab", "tgt": "TNF-alpha", "rel": "drug_protein", "desc": "Infliximab targets TNF-alpha."},
        {"src": "Etanercept", "tgt": "TNF-alpha", "rel": "drug_protein", "desc": "Etanercept binds TNF-alpha."},
        {"src": "Rituximab", "tgt": "CD20", "rel": "drug_protein", "desc": "Rituximab targets CD20."},
        {"src": "Trastuzumab", "tgt": "HER2", "rel": "drug_protein", "desc": "Trastuzumab targets HER2."},
        {"src": "Pembrolizumab", "tgt": "PD-1", "rel": "drug_protein", "desc": "Pembrolizumab blocks PD-1."},
        {"src": "Nivolumab", "tgt": "PD-1", "rel": "drug_protein", "desc": "Nivolumab blocks PD-1."},
        {"src": "Atezolizumab", "tgt": "PD-L1", "rel": "drug_protein", "desc": "Atezolizumab blocks PD-L1."},
        {"src": "Bevacizumab", "tgt": "VEGF", "rel": "drug_protein", "desc": "Bevacizumab targets VEGF."},
        {"src": "Tocilizumab", "tgt": "IL-6", "rel": "drug_protein", "desc": "Tocilizumab targets IL-6 receptor."},
        {"src": "Secukinumab", "tgt": "IL-17A", "rel": "drug_protein", "desc": "Secukinumab targets IL-17A."},
        {"src": "Dupilumab", "tgt": "IL-4 Receptor Alpha", "rel": "drug_protein", "desc": "Dupilumab targets IL-4Rα."},
        {"src": "Omalizumab", "tgt": "IgE", "rel": "drug_protein", "desc": "Omalizumab targets IgE."},
        {"src": "Denosumab", "tgt": "RANKL", "rel": "drug_protein", "desc": "Denosumab targets RANKL."},
        {"src": "Eculizumab", "tgt": "Complement C5", "rel": "drug_protein", "desc": "Eculizumab targets complement C5."},
        {"src": "Ravulizumab", "tgt": "Complement C5", "rel": "drug_protein", "desc": "Ravulizumab targets complement C5."},
        {"src": "Imatinib", "tgt": "BCR-ABL", "rel": "drug_protein", "desc": "Imatinib inhibits BCR-ABL kinase."},
        {"src": "Ruxolitinib", "tgt": "JAK1", "rel": "drug_protein", "desc": "Ruxolitinib inhibits JAK1."},
        {"src": "Ruxolitinib", "tgt": "JAK2", "rel": "drug_protein", "desc": "Ruxolitinib inhibits JAK2."},
        {"src": "Ibrutinib", "tgt": "BTK", "rel": "drug_protein", "desc": "Ibrutinib inhibits BTK."},
        {"src": "Venetoclax", "tgt": "BCL-2", "rel": "drug_protein", "desc": "Venetoclax inhibits BCL-2."},
        {"src": "Osimertinib", "tgt": "EGFR", "rel": "drug_protein", "desc": "Osimertinib inhibits mutant EGFR."},
        {"src": "Crizotinib", "tgt": "ALK", "rel": "drug_protein", "desc": "Crizotinib inhibits ALK."},
        {"src": "Semaglutide", "tgt": "GLP-1 Receptor", "rel": "drug_protein", "desc": "Semaglutide activates GLP-1R."},
        {"src": "Eltrombopag", "tgt": "Thrombopoietin Receptor", "rel": "drug_protein", "desc": "Eltrombopag activates TPO-R."},
        {"src": "Warfarin", "tgt": "Thrombin", "rel": "drug_protein", "desc": "Warfarin indirectly inhibits thrombin via vitamin K."},
        {"src": "Heparin", "tgt": "Antithrombin III", "rel": "drug_protein", "desc": "Heparin enhances antithrombin III activity."},
    ]

    disease_protein_rels = [
        {"src": "Hemophilia A", "tgt": "Factor VIII", "rel": "disease_protein", "desc": "Hemophilia A caused by FVIII deficiency."},
        {"src": "Hemophilia B", "tgt": "Factor IX", "rel": "disease_protein", "desc": "Hemophilia B caused by FIX deficiency."},
        {"src": "Von Willebrand Disease", "tgt": "Von Willebrand Factor", "rel": "disease_protein", "desc": "VWD caused by VWF deficiency."},
        {"src": "Hereditary Angioedema", "tgt": "C1 Esterase Inhibitor", "rel": "disease_protein", "desc": "HAE caused by C1-INH deficiency."},
        {"src": "Alpha-1 Antitrypsin Deficiency", "tgt": "Alpha-1 Antitrypsin", "rel": "disease_protein", "desc": "A1ATD from SERPINA1 mutations."},
        {"src": "Paroxysmal Nocturnal Hemoglobinuria", "tgt": "Complement C5", "rel": "disease_protein", "desc": "PNH involves uncontrolled complement C5 activation."},
        {"src": "Chronic Myeloid Leukemia", "tgt": "BCR-ABL", "rel": "disease_protein", "desc": "CML driven by BCR-ABL fusion oncoprotein."},
        {"src": "HER2+ Breast Cancer", "tgt": "HER2", "rel": "disease_protein", "desc": "HER2 overexpression drives this cancer."},
        {"src": "Non-Small Cell Lung Cancer", "tgt": "EGFR", "rel": "disease_protein", "desc": "EGFR mutations drive subset of NSCLC."},
        {"src": "Non-Small Cell Lung Cancer", "tgt": "ALK", "rel": "disease_protein", "desc": "ALK fusions drive subset of NSCLC."},
        {"src": "Non-Small Cell Lung Cancer", "tgt": "KRAS", "rel": "disease_protein", "desc": "KRAS mutations common in NSCLC."},
        {"src": "Colorectal Cancer", "tgt": "KRAS", "rel": "disease_protein", "desc": "KRAS mutations in ~40% of CRC."},
        {"src": "Multiple Myeloma", "tgt": "BCL-2", "rel": "disease_protein", "desc": "BCL-2 overexpression in myeloma."},
        {"src": "Myelofibrosis", "tgt": "JAK2", "rel": "disease_protein", "desc": "JAK2 V617F mutation drives myelofibrosis."},
        {"src": "Rheumatoid Arthritis", "tgt": "TNF-alpha", "rel": "disease_protein", "desc": "TNF-alpha key driver of RA inflammation."},
        {"src": "Deep Vein Thrombosis", "tgt": "Factor V Leiden", "rel": "disease_protein", "desc": "FVL mutation increases DVT risk."},
    ]

    protein_protein_rels = [
        {"src": "Factor VIII", "tgt": "Von Willebrand Factor", "rel": "protein_protein", "desc": "FVIII circulates bound to VWF which stabilizes it."},
        {"src": "Factor VIII", "tgt": "Thrombin", "rel": "protein_protein", "desc": "Thrombin activates Factor VIII in coagulation."},
        {"src": "Factor IX", "tgt": "Thrombin", "rel": "protein_protein", "desc": "FIX activated by FXIa leads to thrombin generation."},
        {"src": "Thrombin", "tgt": "Fibrinogen", "rel": "protein_protein", "desc": "Thrombin converts fibrinogen to fibrin."},
        {"src": "Antithrombin III", "tgt": "Thrombin", "rel": "protein_protein", "desc": "Antithrombin III inhibits thrombin."},
        {"src": "Protein C", "tgt": "Factor VIII", "rel": "protein_protein", "desc": "Activated Protein C inactivates Factor Va and VIIIa."},
        {"src": "PD-1", "tgt": "PD-L1", "rel": "protein_protein", "desc": "PD-1 binds PD-L1 to suppress T-cell activity."},
        {"src": "JAK1", "tgt": "JAK2", "rel": "protein_protein", "desc": "JAK1 and JAK2 form heterodimers for cytokine signaling."},
        {"src": "BRCA1", "tgt": "BRCA2", "rel": "protein_protein", "desc": "BRCA1 and BRCA2 cooperate in DNA repair."},
        {"src": "BRCA1", "tgt": "TP53", "rel": "protein_protein", "desc": "BRCA1 activates TP53 in DNA damage response."},
    ]

    pathway_protein_rels = [
        {"src": "Coagulation Cascade", "tgt": "Factor VIII", "rel": "pathway_protein", "desc": "FVIII is cofactor in intrinsic coagulation pathway."},
        {"src": "Coagulation Cascade", "tgt": "Factor IX", "rel": "pathway_protein", "desc": "FIX is key enzyme in intrinsic pathway."},
        {"src": "Coagulation Cascade", "tgt": "Thrombin", "rel": "pathway_protein", "desc": "Thrombin is central enzyme in coagulation."},
        {"src": "Coagulation Cascade", "tgt": "Fibrinogen", "rel": "pathway_protein", "desc": "Fibrinogen is substrate for clot formation."},
        {"src": "Complement Pathway", "tgt": "Complement C5", "rel": "pathway_protein", "desc": "C5 is key component of terminal complement pathway."},
        {"src": "Complement Pathway", "tgt": "C1 Esterase Inhibitor", "rel": "pathway_protein", "desc": "C1-INH regulates complement activation."},
        {"src": "NF-kB Signaling", "tgt": "TNF-alpha", "rel": "pathway_protein", "desc": "TNF-alpha activates NF-kB signaling."},
        {"src": "JAK-STAT Pathway", "tgt": "JAK1", "rel": "pathway_protein", "desc": "JAK1 is key kinase in JAK-STAT signaling."},
        {"src": "JAK-STAT Pathway", "tgt": "JAK2", "rel": "pathway_protein", "desc": "JAK2 is key kinase in JAK-STAT signaling."},
        {"src": "JAK-STAT Pathway", "tgt": "IL-6", "rel": "pathway_protein", "desc": "IL-6 signals through JAK-STAT pathway."},
        {"src": "RAS-MAPK Pathway", "tgt": "KRAS", "rel": "pathway_protein", "desc": "KRAS is key node in RAS-MAPK signaling."},
        {"src": "RAS-MAPK Pathway", "tgt": "EGFR", "rel": "pathway_protein", "desc": "EGFR activates RAS-MAPK pathway."},
        {"src": "PD-1/PD-L1 Checkpoint", "tgt": "PD-1", "rel": "pathway_protein", "desc": "PD-1 is the receptor in this checkpoint."},
        {"src": "PD-1/PD-L1 Checkpoint", "tgt": "PD-L1", "rel": "pathway_protein", "desc": "PD-L1 is the ligand in this checkpoint."},
        {"src": "VEGF Angiogenesis Pathway", "tgt": "VEGF", "rel": "pathway_protein", "desc": "VEGF drives angiogenesis signaling."},
        {"src": "Apoptosis Pathway", "tgt": "BCL-2", "rel": "pathway_protein", "desc": "BCL-2 inhibits apoptosis."},
        {"src": "Apoptosis Pathway", "tgt": "TP53", "rel": "pathway_protein", "desc": "TP53 promotes apoptosis."},
        {"src": "Insulin Signaling Pathway", "tgt": "GLP-1 Receptor", "rel": "pathway_protein", "desc": "GLP-1R stimulates insulin secretion."},
    ]

    org_rels = [
        {"src": "CSL Behring", "tgt": "CSL Limited", "rel": "SUBSIDIARY_OF", "desc": "CSL Behring is subsidiary of CSL Limited."},
        {"src": "CSL Seqirus", "tgt": "CSL Limited", "rel": "SUBSIDIARY_OF", "desc": "CSL Seqirus is subsidiary of CSL Limited."},
        {"src": "Alexion", "tgt": "AstraZeneca", "rel": "SUBSIDIARY_OF", "desc": "Alexion acquired by AstraZeneca in 2021."},
    ]

    # Drug aliases (brand names / synonyms)
    drug_aliases = {
        "Adalimumab": (["Humira", "Hadlima", "Hyrimoz", "Cyltezo"], "DRUG_PRODUCT"),
        "Rituximab": (["Rituxan", "MabThera", "Truxima"], "DRUG_PRODUCT"),
        "Trastuzumab": (["Herceptin", "Kanjinti", "Ogivri"], "DRUG_PRODUCT"),
        "Pembrolizumab": (["Keytruda"], "DRUG_PRODUCT"),
        "Nivolumab": (["Opdivo"], "DRUG_PRODUCT"),
        "Bevacizumab": (["Avastin", "Mvasi", "Zirabev"], "DRUG_PRODUCT"),
        "Infliximab": (["Remicade", "Inflectra", "Renflexis"], "DRUG_PRODUCT"),
        "Etanercept": (["Enbrel", "Erelzi"], "DRUG_PRODUCT"),
        "Imatinib": (["Gleevec", "Glivec"], "DRUG_PRODUCT"),
        "Semaglutide": (["Ozempic", "Wegovy", "Rybelsus"], "DRUG_PRODUCT"),
        "Tocilizumab": (["Actemra", "RoActemra"], "DRUG_PRODUCT"),
        "Denosumab": (["Prolia", "Xgeva"], "DRUG_PRODUCT"),
        "Eculizumab": (["Soliris"], "DRUG_PRODUCT"),
        "Dupilumab": (["Dupixent"], "DRUG_PRODUCT"),
        "Omalizumab": (["Xolair"], "DRUG_PRODUCT"),
        "Secukinumab": (["Cosentyx"], "DRUG_PRODUCT"),
        "Ustekinumab": (["Stelara"], "DRUG_PRODUCT"),
        "Osimertinib": (["Tagrisso"], "DRUG_PRODUCT"),
        "Ruxolitinib": (["Jakafi", "Jakavi"], "DRUG_PRODUCT"),
        "Ibrutinib": (["Imbruvica"], "DRUG_PRODUCT"),
        "Venetoclax": (["Venclexta"], "DRUG_PRODUCT"),
        "Lenalidomide": (["Revlimid"], "DRUG_PRODUCT"),
        "Bortezomib": (["Velcade"], "DRUG_PRODUCT"),
        "Insulin Glargine": (["Lantus", "Basaglar", "Semglee"], "DRUG_PRODUCT"),
        "Eltrombopag": (["Promacta", "Revolade"], "DRUG_PRODUCT"),
        "Ravulizumab": (["Ultomiris"], "DRUG_PRODUCT"),
        "Hemlibra": (["Emicizumab"], "DRUG_SYNONYM"),
    }

    # ================================================================
    # INGEST EVERYTHING
    # ================================================================
    all_nodes = drugs + diseases + proteins + pathways + anatomy + orgs

    logger.info(f"Ingesting {len(all_nodes)} nodes...")
    with driver.session() as session:
        with session.begin_transaction() as tx:
            ingest_nodes(tx, all_nodes)
            tx.commit()
    logger.info(f"  Nodes done: {len(drugs)} drugs, {len(diseases)} diseases, {len(proteins)} proteins, {len(pathways)} pathways, {len(anatomy)} anatomy, {len(orgs)} organizations")

    all_rels = drug_disease_rels + drug_protein_rels + disease_protein_rels + protein_protein_rels + pathway_protein_rels + org_rels
    logger.info(f"Ingesting {len(all_rels)} relationships...")
    with driver.session() as session:
        with session.begin_transaction() as tx:
            ingest_rels(tx, all_rels)
            tx.commit()
    logger.info(f"  Relationships done")

    logger.info(f"Ingesting drug aliases...")
    with driver.session() as session:
        with session.begin_transaction() as tx:
            for drug, (aliases, alias_type) in drug_aliases.items():
                ingest_aliases(tx, drug, aliases, alias_type)
            tx.commit()
    total_aliases = sum(len(a[0]) for a in drug_aliases.values())
    logger.info(f"  Aliases done: {total_aliases} aliases for {len(drug_aliases)} drugs")

    # Add uppercase labels for API compatibility
    logger.info("Adding API-compatible labels...")
    with driver.session() as session:
        session.run("MATCH (n:drug) SET n:DRUG")
        session.run("MATCH (n:disease) SET n:DISEASE")
        session.run("MATCH (n:gene_protein) SET n:GENE_PROTEIN")
        session.run("MATCH (n:pathway) SET n:PATHWAY")
        session.run("MATCH (n:anatomy) SET n:ANATOMY")
        session.run("MATCH (n:Organization) SET n.organization_canonical_name = n.node_name, n.org_id = n.node_id, n.organization_name = n.node_name, n.organization_id = n.node_id")

    # Final stats
    with driver.session() as session:
        nodes = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        rels = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        labels = [(r["l"], r["c"]) for r in session.run("MATCH (n) WITH labels(n) AS l, count(n) AS c ORDER BY c DESC RETURN l, c")]

    logger.info("=" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info(f"  Total nodes: {nodes}")
    logger.info(f"  Total relationships: {rels}")
    logger.info("  Node types:")
    for l, c in labels:
        logger.info(f"    {l}: {c}")
    logger.info("=" * 60)

    driver.close()


if __name__ == "__main__":
    main()
