from model.drug_feature import DrugFeature
from helper.statement_helper import escape

def build_batch_statement(drug_features: list[DrugFeature], batch_size: int = 100) -> str:
    return  build_apoc_itr_clause(drug_features, batch_size)

def build_with_clause(drug_features: list[DrugFeature]) -> str:
    items = []
    for drug in drug_features:
        items.append(build_with_clause_item(drug))

    return "\n".join(
        [
            "// modify drug metadata",
            "       WITH [",
            ",".join(items),
            "       ] AS drug_nodes",
        ]
    )

def build_with_clause_item(drug: DrugFeature) -> str:
    return f"""
        {{
            node_index: "{drug.node_index}",
            description: "{escape(drug.description)}",
            half_life: "{escape(drug.half_life)}",
            indication: "{escape(drug.indication)}",
            mechanism_of_action: "{escape(drug.mechanism_of_action)}",
            protein_binding: "{escape(drug.protein_binding)}",
            pharmacodynamics: "{escape(drug.pharmacodynamics)}",
            state: "{escape(drug.state)}",
            atc_1: "{escape(drug.atc_1)}",
            atc_2: "{escape(drug.atc_2)}",
            atc_3: "{escape(drug.atc_3)}",
            atc_4: "{escape(drug.atc_4)}",
            category: "{escape(drug.category)}",
            group: "{escape(drug.group)}",
            pathway: "{escape(drug.pathway)}",
            molecular_weight: "{escape(drug.molecular_weight)}",
            tpsa: "{escape(drug.tpsa)}",
            clogp: "{escape(drug.clogp)}"
        }}
    """

def build_apoc_itr_clause(drug_features: list[DrugFeature], batch_size: int = 100) -> str:
    return f"""
CALL apoc.periodic.iterate(
"
{escape(build_with_clause(drug_features=drug_features))}
UNWIND drug_nodes as row
RETURN row
",
"
MATCH (d:drug {{ node_index: row.node_index }})
SET d.description = row.description
SET d.half_life = row.half_life
SET d.indication = row.indication
SET d.mechanism_of_action = row.mechanism_of_action 
SET d.protein_binding = row.protein_binding
SET d.pharmacodynamics = row.pharmacodynamics
SET d.state = row.state 
SET d.atc_1 = row.atc_1
SET d.atc_2 = row.atc_2
SET d.atc_3 = row.atc_3
SET d.atc_4 = row.atc_4
SET d.category = row.category
SET d.group = row.group
SET d.pathway = row.pathway
SET d.molecular_weight = row.molecular_weight
SET d.tpsa = row.tpsa
SET d.clogp = row.clogp
RETURN d
",
{{batchSize: {batch_size}, parallel:true }})
YIELD batches, total, errorMessages
RETURN batches, total, errorMessages
"""

