from enum import Enum


class Label(str, Enum):
    anatomy = "anatomy"
    biological_process = "biological_process"
    disease = "disease"
    drug = "drug"
    effect_phenotype = "effect_phenotype"
    exposure = "exposure"
    gene_protein = "gene_protein"
    molecular_function = "molecular_function"
    pathway = "pathway"
