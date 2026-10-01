from model.disease_feature import DiseaseFeature
from helper.statement_helper import escape

def build_batch_statement(disease_features: list[DiseaseFeature], batch_size: int = 100) -> str:
    return build_apoc_itr_clause(disease_features, batch_size)

def build_with_clause(disease_features: list[DiseaseFeature]) -> str:
    items = []
    for disease in disease_features:
        items.append(build_with_clause_item(disease))

    return "\n".join(
        [
            "// modify disease metadata",
            "       WITH [",
            ",".join(items),
            "       ] AS disease_nodes",
        ]
    )

def build_with_clause_item(disease: DiseaseFeature) -> str:
    return f"""
        {{
            node_index: "{disease.node_index}",
            mondo_id: "{disease.mondo_id}",
            mondo_name: "{escape(disease.mondo_name)}",
            group_id_bert: "{escape(disease.group_id_bert)}",
            group_name_bert: "{escape(disease.group_name_bert)}",
            mondo_definition: "{escape(disease.mondo_definition)}",
            umls_description: "{escape(disease.umls_description)}",
            orphanet_definition: "{escape(disease.orphanet_definition)}",
            orphanet_prevalence: "{escape(disease.orphanet_prevalence)}",
            orphanet_epidemiology: "{escape(disease.orphanet_epidemiology)}",
            orphanet_clinical_description: "{escape(disease.orphanet_clinical_description)}",
            orphanet_management_and_treatment: "{escape(disease.orphanet_management_and_treatment)}",
            mayo_symptoms: "{escape(disease.mayo_symptoms)}",
            mayo_causes: "{escape(disease.mayo_causes)}",
            mayo_risk_factors: "{escape(disease.mayo_risk_factors)}",
            mayo_complications: "{escape(disease.mayo_complications)}",
            mayo_prevention: "{escape(disease.mayo_prevention)}",
            mayo_see_doc: "{escape(disease.mayo_see_doc)}"
        }}
    """

def build_apoc_itr_clause(disease_features: list[DiseaseFeature], batch_size: int = 100) -> str:
    return f"""
CALL apoc.periodic.iterate(
"
{escape(build_with_clause(disease_features=disease_features))}
UNWIND disease_nodes as row
RETURN row
",
" 
MATCH (d:disease {{ node_index: row.node_index }})
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
{{batchSize: {batch_size}, parallel:true }})
YIELD batches, total, errorMessages
RETURN batches, total, errorMessages
"""
