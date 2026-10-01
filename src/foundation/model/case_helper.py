def normalize_gene_protein(gene_protein: str) -> str:
    return _normalize_upper(gene_protein)


def normalize_drug_id(id: str) -> str:
    return _normalize_upper(id)


def normalize_clinical_trial_id(id: str) -> str:
    return _normalize_upper(id)


def _normalize_upper(val: str) -> str:
    if val is None:
        return val

    return val.upper()
