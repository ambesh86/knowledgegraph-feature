from dataclasses import dataclass


@dataclass(frozen=True, unsafe_hash=True)
class DatabaseStats:
    node_count: str
    relationship_count: str
    drug_count: str
    drug_synonym_count: str
    disease_count: str
    gene_protein_count: str

    uspto_count: str
    uspto_filing_date_min: str
    uspto_filting_date_max: str

    clinical_trial_count: str
    therapeutic_area_count: str
    therapeutic_area_subgroup_count: str

    pubmed_count: str
    pubmed_researcher_count: str

    organization_count: str
    disambiguated_organization_count: str

    @staticmethod
    def format_count(num: int) -> str:
        if num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.1f}b"
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}m"
        if num >= 1_000:
            return f"{num / 1_000:.1f}k"
        return str(num)
