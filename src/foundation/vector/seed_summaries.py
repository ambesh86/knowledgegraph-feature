"""Seed PubMed-style summaries for the Milvus 'pubmed' vector collection.

These curated summaries align with the biomedical entities already loaded into
the local Neo4j graph (emicizumab / hemophilia, Factor VIII, ABL1, sickle cell,
mycophenolate, etc.) so semantic vector search returns relevant, testable hits.

In production this collection is populated from real summary checkpoints via
store_summaries.py; this seed makes the vector store usable locally without
that offline pipeline.
"""

SEED_SUMMARIES: list[dict] = [
    {
        "summary_id": "PMID:34primary",
        "title": "Emicizumab prophylaxis in hemophilia A",
        "summary": "Emicizumab is a bispecific monoclonal antibody that bridges activated "
        "factor IX and factor X to restore the function of missing factor VIII in "
        "hemophilia A. Subcutaneous prophylaxis substantially reduces annualized bleed "
        "rates in patients with and without factor VIII inhibitors.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/?term=emicizumab+hemophilia+A+prophylaxis",
    },
    {
        "summary_id": "PMID:fviii01",
        "title": "Factor VIII replacement therapy in hemophilia A",
        "summary": "Recombinant factor VIII concentrates remain a mainstay for treating "
        "hemophilia A. Reduced or defective factor VIII activity causes prolonged bleeding; "
        "extended half-life products lower infusion frequency.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/?term=factor+VIII+hemophilia+A+replacement",
    },
    {
        "summary_id": "PMID:abl101",
        "title": "ABL1 tyrosine kinase and chronic myeloid leukemia",
        "summary": "The BCR-ABL1 fusion drives chronic myeloid leukemia. ABL1 tyrosine "
        "kinase inhibitors such as imatinib induce durable molecular remissions; resistance "
        "mutations in the ABL1 kinase domain guide later-line therapy choice.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/?term=ABL1+chronic+myeloid+leukemia",
    },
    {
        "summary_id": "PMID:scd01",
        "title": "Sickle cell anemia pathophysiology and acute chest syndrome",
        "summary": "Sickle cell anemia results from a beta-globin mutation producing "
        "hemoglobin S. Polymerization under hypoxia causes vaso-occlusion; acute chest "
        "syndrome is a leading cause of mortality and requires prompt management.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/?term=sickle+cell+anemia+acute+chest+syndrome",
    },
    {
        "summary_id": "PMID:mmf01",
        "title": "Mycophenolate mofetil and IMPDH inhibition",
        "summary": "Mycophenolate mofetil is a prodrug whose active metabolite inhibits "
        "inosine monophosphate dehydrogenase (IMPDH), depleting guanine nucleotides in "
        "lymphocytes. It is widely used as an immunosuppressant in transplantation.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/?term=mycophenolate+mofetil+IMPDH",
    },
    {
        "summary_id": "PMID:vwf01",
        "title": "Von Willebrand factor and factor VIII stabilization",
        "summary": "Von Willebrand factor carries and stabilizes circulating factor VIII. "
        "Impaired binding of factor VIII to VWF shortens factor VIII half-life and "
        "contributes to bleeding phenotypes.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/?term=von+willebrand+factor+VIII",
    },
    {
        "summary_id": "PMID:trial01",
        "title": "Clinical trial design for hemophilia gene therapy",
        "summary": "Adeno-associated virus vector gene therapy for hemophilia aims to "
        "achieve sustained endogenous factor expression. Trial endpoints include factor "
        "activity levels, annualized bleed rate, and durability of expression.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/?term=hemophilia+gene+therapy+trial",
    },
    {
        "summary_id": "PMID:inhibitor01",
        "title": "Management of factor VIII inhibitors in hemophilia A",
        "summary": "Some hemophilia A patients develop neutralizing alloantibodies "
        "(inhibitors) against factor VIII. Bypassing agents and emicizumab provide "
        "hemostatic coverage; immune tolerance induction can eradicate inhibitors.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/?term=factor+VIII+inhibitors+immune+tolerance",
    },
]
