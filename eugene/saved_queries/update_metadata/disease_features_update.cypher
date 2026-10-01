 // modify disease metadata
    WITH [
        {
            node_index: "27165",
            mondo_id: "8019",
            mondo_name: "mullerian aplasia and hyperandrogenism",
            group_id_bert: "",
            group_name_bert: "",
            mondo_definition: "Deficiency of the glycoprotein WNT4, associated with loss of function mutation(s) in the WNT4 gene. The condition in 46,XX individuals is characterized by mild hyperandrogenism, absence of underdevelopment of the uterus, and sometimes absence of underdevelopment of the vagina.",
            umls_description: "Deficiency of the glycoprotein wnt4, associated with loss of function mutation in the wnt4 gene. The condition in 46,xx individuals is characterized by mild hyperandrogenism, absence of underdevelopment of the uterus, and sometimes absence of underdevelopment of the vagina.",
            orphanet_definition: "A rare syndrome with 46,XX disorder of sex development characterized by Müllerian duct hypoplasia or agenesis associated with clinical and biological evidence of hyperandrogenism in 46,XX females. Patients present with hypoplastic or absent uterus, variable abnormalities of other reproductive organs, primary amenorrhea, acne, hirsutism, and sometimes renal anomalies. External genitalia and secondary sexual characteristics are normal. Hormonal analysis shows variably elevated serum levels of androstenedione, dehydroepiandrosterone, and/or total and free testosterone.",
            orphanet_prevalence: "",
            orphanet_epidemiology: "",
            orphanet_clinical_description: "",
            orphanet_management_and_treatment: "",
            mayo_symptoms: "",
            mayo_causes: "",
            mayo_risk_factors: "",
            mayo_complications: "",
            mayo_prevention: "",
            mayo_see_doc: ""
        }
    ] AS disease_nodes
CALL apoc.periodic.iterate(
"
UNWIND $disease_nodes as row
MATCH (d:disease { node_index: row.node_index })
RETURN row, d
",
" 
SET d.mondo_id = row.mondo_id
SET d.mondo_name = row.mondo_name
SET d.group_id_bert = row.group_id_bert
SET d.group_name_bert = row.group_name_bert
SET d.mondo_definition = row.mondo_definition
SET d.umls_description = row.umls_description
SET d.orphanet_definition = row.orphanet_definition
SET d.orphanet_prevalence = row.orphanet_prevalence
SET d.orphanet_epidemiology = row.orphanet_epidemiology
SET d.orphanet_clinical_description = row.orphanet_clinical_description
SET d.orphanet_management_and_treatment = row.orphanet_management_and_treatment
SET d.mayo_symptoms = row.mayo_symptoms
SET d.mayo_causes = row.mayo_causes
SET d.mayo_risk_factors = row.mayo_risk_factors
SET d.mayo_complications = row.mayo_complications
SET d.mayo_prevention = row.mayo_prevention
SET d.mayo_see_doc = row.mayo_see_doc

RETURN d
",
{batchSize: 200, parallel:true, params: { disease_nodes: disease_nodes } })
YIELD batches, total, errorMessages
RETURN batches, total, errorMessages